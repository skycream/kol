#!/usr/bin/env python3
"""
텔레그램 포워딩 봇 API 서버
FastAPI를 사용한 RESTful API 서버
"""

import asyncio
import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7948096537:AAFeuf-Km1xV_Z7eG8el7GMLrTthlF-M34o')

# 전역 변수로 봇 인스턴스 관리
forwarder_instance = None

# Pydantic 모델들
class ChannelConfig(BaseModel):
    source_channels: List[str]
    target_channel: str

class FilterConfig(BaseModel):
    exclude_words: Optional[List[str]] = None
    add_words: Optional[List[str]] = None
    remove_words: Optional[List[str]] = None

class StatusResponse(BaseModel):
    status: str
    is_running: bool
    stats: Dict[str, int]
    channels: Dict[str, Any]
    uptime: Optional[str] = None

class MessageFilter:
    def __init__(self):
        # 제외할 단어들 (기본값)
        self.exclude_words = [
            '에어드랍', '파트너', '당첨', '후기', '체커', '공개', 'AMA', 'ama', '원문', '예정',
            'TGE', '소식', '클레임', '링크', '트위터', '이벤트', '지급', '출시', '켠페인',
            '추천', '채굴', '인터뷰', '파밍', '밋업', '콘테스트', '#kol'
        ]
        
        # 한글 패턴
        self.korean_pattern = re.compile(r'[가-힣]')
    
    def has_korean(self, text: str) -> bool:
        """텍스트에 한글이 포함되어 있는지 확인"""
        return bool(self.korean_pattern.search(text))
    
    def should_forward(self, message_text: str) -> bool:
        """메시지를 포워딩할지 판단"""
        if not message_text:
            return False
        
        # 1. 한글이 없으면 제외
        if not self.has_korean(message_text):
            return False
        
        # 2. 특정 단어가 포함되면 제외
        text_lower = message_text.lower()
        for word in self.exclude_words:
            if word.lower() in text_lower:
                return False
        
        return True
    
    def update_exclude_words(self, words: List[str]):
        """제외 단어 목록 업데이트"""
        self.exclude_words = words
    
    def add_exclude_words(self, words: List[str]):
        """제외 단어 추가"""
        for word in words:
            if word not in self.exclude_words:
                self.exclude_words.append(word)
    
    def remove_exclude_words(self, words: List[str]):
        """제외 단어 제거"""
        for word in words:
            if word in self.exclude_words:
                self.exclude_words.remove(word)

class TelegramForwarderBot:
    def __init__(self):
        self.bot_client = None
        self.user_client = None
        self.source_channels = ["@korean_alpha", "@JoshuaDeukKOR"]
        self.target_channel = "@ktradingalpha"
        self.filter = MessageFilter()
        self.is_running = False
        self.start_time = None
        self.stats = {
            'total': 0,
            'forwarded': 0,
            'filtered': 0,
            'errors': 0
        }
        self.event_handlers = []
    
    async def connect(self):
        """클라이언트 연결"""
        try:
            # 봇 클라이언트
            self.bot_client = TelegramClient('bot_session', API_ID, API_HASH)
            await self.bot_client.start(bot_token=BOT_TOKEN)
            
            # 사용자 클라이언트 - 기존 세션 사용
            self.user_client = TelegramClient('test_session', API_ID, API_HASH)
            await self.user_client.start()
            
            logger.info("✅ 텔레그램 클라이언트 연결 성공")
            return True
        except Exception as e:
            logger.error(f"❌ 연결 실패: {e}")
            return False
    
    async def forward_message(self, message, channel_name: str):
        """메시지 포워딩"""
        try:
            self.stats['total'] += 1
            
            if message.text:
                if self.filter.should_forward(message.text):
                    # 포워딩
                    await self.bot_client.send_message(
                        self.target_channel,
                        message.text,
                        parse_mode=None
                    )
                    
                    self.stats['forwarded'] += 1
                    logger.info(f"✅ 포워딩: {channel_name} - #{self.stats['forwarded']}")
                else:
                    self.stats['filtered'] += 1
                    logger.info(f"🚫 필터링 차단: {channel_name} - 차단 #{self.stats['filtered']}")
                    
        except FloodWaitError as e:
            logger.warning(f"⏳ 속도 제한: {e.seconds}초 대기")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"❌ 포워딩 실패: {e}")
    
    async def start_forwarding(self):
        """포워딩 시작"""
        if self.is_running:
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        
        logger.info("🚀 포워딩 봇 시작")
        
        # 이벤트 핸들러 등록 - 모든 채널을 한번에
        @self.user_client.on(events.NewMessage(chats=self.source_channels))
        async def handle_new_message(event):
            if not self.is_running:
                return
                
            try:
                channel_entity = await event.get_chat()
                channel_name = f"@{channel_entity.username}" if channel_entity.username else channel_entity.title
            except:
                channel_name = "Unknown"
            
            logger.info(f"🔔 새 메시지 감지: {channel_name} ID {event.message.id}")
            await self.forward_message(event.message, channel_name)
        
        # 핸들러 저장
        self.event_handlers.append(handle_new_message)
        
        logger.info("✅ 이벤트 핸들러 등록 완료")
        
        # 채널 접근 확인
        for channel in self.source_channels:
            try:
                entity = await self.user_client.get_entity(channel)
                logger.info(f"✅ {channel} 접근 가능 - {entity.title}")
            except Exception as e:
                logger.error(f"❌ {channel} 접근 실패: {e}")
        
        # 실행 유지를 위한 무한 루프
        while self.is_running:
            await asyncio.sleep(1)
    
    async def stop_forwarding(self):
        """포워딩 중지"""
        self.is_running = False
        
        # 이벤트 핸들러 제거
        for handler in self.event_handlers:
            self.user_client.remove_event_handler(handler)
        
        self.event_handlers.clear()
        logger.info("🛑 포워딩 봇 중지")
    
    async def disconnect(self):
        """연결 종료"""
        await self.stop_forwarding()
        
        if self.bot_client:
            await self.bot_client.disconnect()
        if self.user_client:
            await self.user_client.disconnect()
        
        logger.info("✅ 연결 종료")
    
    def get_status(self):
        """현재 상태 반환"""
        uptime = None
        if self.start_time:
            uptime = str(datetime.now() - self.start_time)
        
        return {
            'is_running': self.is_running,
            'stats': self.stats,
            'channels': {
                'source': self.source_channels,
                'target': self.target_channel
            },
            'uptime': uptime,
            'filter_words_count': len(self.filter.exclude_words)
        }

# FastAPI 앱 생성
@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 함수"""
    global forwarder_instance
    
    # 시작 시
    logger.info("🚀 FastAPI 서버 시작")
    forwarder_instance = TelegramForwarderBot()
    
    if await forwarder_instance.connect():
        logger.info("✅ 텔레그램 연결 성공")
    else:
        logger.error("❌ 텔레그램 연결 실패")
    
    yield
    
    # 종료 시
    logger.info("🛑 FastAPI 서버 종료")
    if forwarder_instance:
        await forwarder_instance.disconnect()

app = FastAPI(
    title="텔레그램 포워딩 봇 API",
    description="필터링된 메시지를 포워딩하는 텔레그램 봇 API",
    version="1.0.0",
    lifespan=lifespan
)

# 라우트들
@app.get("/")
async def root():
    """API 정보"""
    return {
        "name": "Telegram Forwarder Bot API",
        "version": "1.0.0",
        "endpoints": {
            "GET /": "API 정보",
            "GET /status": "봇 상태 조회",
            "POST /start": "포워딩 시작",
            "POST /stop": "포워딩 중지",
            "GET /stats": "통계 조회",
            "POST /channels": "채널 설정 변경",
            "GET /filter": "필터 설정 조회",
            "POST /filter": "필터 설정 변경"
        }
    }

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """봇 상태 조회"""
    if not forwarder_instance:
        raise HTTPException(status_code=503, detail="봇이 초기화되지 않았습니다")
    
    status = forwarder_instance.get_status()
    return StatusResponse(
        status="running" if status['is_running'] else "stopped",
        is_running=status['is_running'],
        stats=status['stats'],
        channels=status['channels'],
        uptime=status['uptime']
    )

@app.post("/start")
async def start_forwarding(background_tasks: BackgroundTasks):
    """포워딩 시작"""
    if not forwarder_instance:
        raise HTTPException(status_code=503, detail="봇이 초기화되지 않았습니다")
    
    if forwarder_instance.is_running:
        return {"message": "이미 실행 중입니다", "status": "already_running"}
    
    # 백그라운드에서 포워딩 시작
    background_tasks.add_task(forwarder_instance.start_forwarding)
    
    return {"message": "포워딩을 시작합니다", "status": "starting"}

@app.post("/stop")
async def stop_forwarding():
    """포워딩 중지"""
    if not forwarder_instance:
        raise HTTPException(status_code=503, detail="봇이 초기화되지 않았습니다")
    
    if not forwarder_instance.is_running:
        return {"message": "실행 중이 아닙니다", "status": "already_stopped"}
    
    await forwarder_instance.stop_forwarding()
    
    return {"message": "포워딩을 중지했습니다", "status": "stopped"}

@app.get("/stats")
async def get_stats():
    """통계 조회"""
    if not forwarder_instance:
        raise HTTPException(status_code=503, detail="봇이 초기화되지 않았습니다")
    
    stats = forwarder_instance.stats
    total = stats['total']
    
    if total > 0:
        pass_rate = (stats['forwarded'] / total) * 100
        filter_rate = (stats['filtered'] / total) * 100
    else:
        pass_rate = filter_rate = 0
    
    return {
        "stats": stats,
        "rates": {
            "pass_rate": f"{pass_rate:.1f}%",
            "filter_rate": f"{filter_rate:.1f}%"
        },
        "is_running": forwarder_instance.is_running
    }

@app.post("/channels")
async def update_channels(config: ChannelConfig):
    """채널 설정 변경"""
    if not forwarder_instance:
        raise HTTPException(status_code=503, detail="봇이 초기화되지 않았습니다")
    
    if forwarder_instance.is_running:
        raise HTTPException(status_code=400, detail="실행 중에는 채널을 변경할 수 없습니다")
    
    forwarder_instance.source_channels = config.source_channels
    forwarder_instance.target_channel = config.target_channel
    
    return {
        "message": "채널 설정이 변경되었습니다",
        "channels": {
            "source": config.source_channels,
            "target": config.target_channel
        }
    }

@app.get("/filter")
async def get_filter():
    """필터 설정 조회"""
    if not forwarder_instance:
        raise HTTPException(status_code=503, detail="봇이 초기화되지 않았습니다")
    
    return {
        "exclude_words": forwarder_instance.filter.exclude_words,
        "count": len(forwarder_instance.filter.exclude_words)
    }

@app.post("/filter")
async def update_filter(config: FilterConfig):
    """필터 설정 변경"""
    if not forwarder_instance:
        raise HTTPException(status_code=503, detail="봇이 초기화되지 않았습니다")
    
    if config.exclude_words is not None:
        forwarder_instance.filter.update_exclude_words(config.exclude_words)
    
    if config.add_words:
        forwarder_instance.filter.add_exclude_words(config.add_words)
    
    if config.remove_words:
        forwarder_instance.filter.remove_exclude_words(config.remove_words)
    
    return {
        "message": "필터 설정이 변경되었습니다",
        "exclude_words": forwarder_instance.filter.exclude_words,
        "count": len(forwarder_instance.filter.exclude_words)
    }

@app.post("/stats/reset")
async def reset_stats():
    """통계 초기화"""
    if not forwarder_instance:
        raise HTTPException(status_code=503, detail="봇이 초기화되지 않았습니다")
    
    forwarder_instance.stats = {
        'total': 0,
        'forwarded': 0,
        'filtered': 0,
        'errors': 0
    }
    
    return {"message": "통계가 초기화되었습니다", "stats": forwarder_instance.stats}

# 에러 핸들러
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    
    # 환경 변수 확인
    if not API_ID or not API_HASH:
        logger.error("❌ 텔레그램 API 환경 변수가 설정되지 않았습니다.")
        exit(1)
    
    # 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )