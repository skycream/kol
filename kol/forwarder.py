#!/usr/bin/env python3
"""
필터링 포워딩 봇 v2 - $ 필터링 제거
한글 포함 + 제외 단어만 필터링
"""

import asyncio
import os
import re
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 콘솔 출력
        logging.FileHandler('forwarder.log', encoding='utf-8')  # 파일 저장
    ]
)
logger = logging.getLogger(__name__)

# 환경 변수
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7948096537:AAFeuf-Km1xV_Z7eG8el7GMLrTthlF-M34o')

class MessageFilter:
    def __init__(self):
        # 제외할 단어들 (총 25개)
        self.exclude_words = [
            '에어드랍', '파트너', '당첨', '후기', '체커', '공개', 'AMA', 'ama', '원문', '예정',
            'TGE', '소식', '클레임', '링크', '트위터', '이벤트', '지급', '출시', '켐페인',
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
        text_lower = message_text.lower()  # 대소문자 구분 없이 체크
        for word in self.exclude_words:
            if word.lower() in text_lower:
                return False
        
        return True

class FilteredBotForwarder:
    def __init__(self, source_channels: list, target_channel: str):
        self.bot_client = None
        self.user_client = None
        self.source_channels = source_channels
        self.target_channel = target_channel
        self.filter = MessageFilter()
        self.stats = {
            'total': 0,
            'forwarded': 0,
            'filtered': 0
        }
    
    async def connect(self):
        """봇과 사용자 클라이언트 연결"""
        try:
            # 봇 클라이언트
            self.bot_client = TelegramClient('bot_session', API_ID, API_HASH)
            await self.bot_client.start(bot_token=BOT_TOKEN)
            bot_me = await self.bot_client.get_me()
            logger.info(f"✅ 봇 연결 성공: @{bot_me.username}")
            
            # 사용자 클라이언트 - 기존 세션 사용
            self.user_client = TelegramClient('test_session', API_ID, API_HASH)
            await self.user_client.start()
            logger.info("✅ 사용자 클라이언트 연결 성공")
            
            return True
        except Exception as e:
            logger.error(f"❌ 연결 실패: {e}")
            return False
    
    async def test_bot_permissions(self):
        """봇 권한 테스트"""
        try:
            # 시작 메시지
            await self.bot_client.send_message(
                self.target_channel,
                f"🔍 **필터링 포워딩 v2 시작**\n\n"
                f"📋 필터링 규칙:\n"
                f"✅ 한글 포함 필수\n"
                f"❌ 제외 단어 {len(self.filter.exclude_words)}개\n\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            logger.info("✅ 봇 권한 확인 완료")
            return True
        except Exception as e:
            logger.error(f"❌ 봇 권한 없음: {e}")
            return False
    
    async def forward_message(self, message, channel_name: str):
        """필터링 통과한 메시지만 포워딩"""
        try:
            self.stats['total'] += 1
            
            # 텍스트가 있는 경우만 처리
            if message.text:
                # 필터링 적용
                if self.filter.should_forward(message.text):
                    # 필터링 통과 - 포워딩
                    await self.bot_client.send_message(
                        self.target_channel,
                        message.text,
                        parse_mode=None
                    )
                    
                    self.stats['forwarded'] += 1
                    logger.info(f"✅ 포워딩 완료: {channel_name} - 통과 {self.stats['forwarded']}개")
                else:
                    # 필터링 차단
                    self.stats['filtered'] += 1
                    logger.info(f"🚫 필터링 차단: {channel_name} - 차단 {self.stats['filtered']}개")
            
            # 통계 출력 (10개마다)
            if self.stats['total'] % 10 == 0:
                logger.info(
                    f"📊 통계: 전체 {self.stats['total']} | "
                    f"통과 {self.stats['forwarded']} | "
                    f"차단 {self.stats['filtered']} "
                    f"({self.stats['forwarded']/self.stats['total']*100:.1f}% 통과)"
                )
            
        except FloodWaitError as e:
            logger.warning(f"⏳ 속도 제한: {e.seconds}초 대기")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"❌ 포워딩 실패: {e}")
    
    async def start_forwarding(self):
        """실시간 포워딩 시작"""
        logger.info("🚀 필터링 포워딩 v2 시작")
        logger.info(f"📡 소스 채널: {', '.join(self.source_channels)}")
        logger.info(f"📢 대상: {self.target_channel}")
        logger.info(f"🔍 제외 단어: {len(self.filter.exclude_words)}개")
        logger.info("💡 $ 필터링 제거됨")
        logger.info("="*50)
        
        # 각 채널에 대해 이벤트 핸들러 등록
        @self.user_client.on(events.NewMessage(chats=self.source_channels))
        async def handle_new_message(event):
            # 채널명 추출
            try:
                channel_entity = await event.get_chat()
                channel_name = f"@{channel_entity.username}" if channel_entity.username else channel_entity.title
            except:
                channel_name = "Unknown"
            
            logger.info(f"🔔 새 메시지 감지: {channel_name} ID {event.message.id}")
            await self.forward_message(event.message, channel_name)
        
        logger.info("✅ 이벤트 핸들러 등록 완료")
        
        # 각 채널에서 최근 메시지 테스트
        logger.info("\n📝 각 채널 최근 메시지로 필터링 테스트...")
        for channel in self.source_channels:
            try:
                logger.info(f"\n📡 {channel} 채널 테스트...")
                channel_stats = {'total': 0, 'passed': 0}
                
                async for msg in self.user_client.iter_messages(channel, limit=50):
                    if msg.text:
                        channel_stats['total'] += 1
                        if self.filter.should_forward(msg.text):
                            channel_stats['passed'] += 1
                            await self.forward_message(msg, channel)
                            await asyncio.sleep(1)
                
                logger.info(
                    f"📊 {channel} 결과: "
                    f"{channel_stats['total']}개 중 {channel_stats['passed']}개 통과 "
                    f"({channel_stats['passed']/channel_stats['total']*100:.1f}% 통과율)"
                )
                    
            except Exception as e:
                logger.error(f"❌ {channel} 테스트 실패: {e}")
        
        logger.info(f"\n📊 전체 통계: {self.stats['total']}개 중 {self.stats['forwarded']}개 통과")
        logger.info("\n🔄 실시간 모니터링 중...")
        logger.info("새 메시지를 기다리는 중... (채널에 새 메시지를 보내보세요)")
        
        # 주기적으로 연결 상태 확인
        async def check_connection():
            while True:
                await asyncio.sleep(60)  # 1분마다
                if self.user_client.is_connected():
                    logger.debug("💚 연결 상태 정상")
                else:
                    logger.warning("🔴 연결 끊김 - 재연결 시도")
                    await self.user_client.connect()
        
        # 연결 체크 태스크 시작
        asyncio.create_task(check_connection())
        
        # 계속 실행
        await self.user_client.run_until_disconnected()
    
    async def close(self):
        """연결 종료"""
        if self.bot_client:
            await self.bot_client.disconnect()
        if self.user_client:
            await self.user_client.disconnect()
        logger.info("✅ 연결 종료")

async def main():
    """메인 함수"""
    # 환경 변수 확인
    if not API_ID or not API_HASH:
        logger.error("❌ 텔레그램 API 환경 변수가 설정되지 않았습니다.")
        return
    
    # 설정
    source_channels = ["@korean_alpha", "@JoshuaDeukKOR"]
    target_channel = "@ktradingalpha"
    
    logger.info("🔍 필터링 포워딩 봇 v2")
    logger.info("$ 필터링 제거 - 한글 + 제외 단어만 필터링")
    logger.info(f"📡 모니터링 채널: {len(source_channels)}개")
    logger.info("="*50)
    
    # 포워더 초기화
    forwarder = FilteredBotForwarder(source_channels, target_channel)
    
    try:
        # 연결
        if not await forwarder.connect():
            return
        
        # 봇 권한 테스트
        if not await forwarder.test_bot_permissions():
            return
        
        # 포워딩 시작
        await forwarder.start_forwarding()
        
    except KeyboardInterrupt:
        logger.info("\n🛑 사용자가 중단했습니다.")
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
    finally:
        await forwarder.close()

if __name__ == "__main__":
    asyncio.run(main())