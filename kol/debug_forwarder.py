#!/usr/bin/env python3
"""
디버깅용 포워더 - 실시간 포워딩 문제 해결
"""

import asyncio
import os
from datetime import datetime
from telethon import TelegramClient, events
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def main():
    # 봇 클라이언트
    bot = TelegramClient('debug_bot_session', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    # 사용자 클라이언트
    user = TelegramClient('debug_user_session', API_ID, API_HASH)
    await user.start()
    
    print(f"✅ 연결 완료 - {datetime.now()}")
    
    # 봇 정보
    bot_me = await bot.get_me()
    print(f"🤖 봇: @{bot_me.username}")
    
    # 사용자 정보
    user_me = await user.get_me()
    print(f"👤 사용자: {user_me.first_name}")
    
    # 채널 확인
    channels = ["@korean_alpha", "@JoshuaDeukKOR"]
    target = "@jjukjjuk"
    
    print(f"\n📡 모니터링 채널: {channels}")
    print(f"📢 대상 채널: {target}")
    
    # 채널 접근 테스트
    for ch in channels:
        try:
            entity = await user.get_entity(ch)
            print(f"✅ {ch} - {entity.title}")
        except Exception as e:
            print(f"❌ {ch} - {e}")
    
    # 이벤트 핸들러
    @user.on(events.NewMessage(chats=channels))
    async def handler(event):
        print(f"\n🔔 새 메시지! - {datetime.now()}")
        
        try:
            chat = await event.get_chat()
            print(f"📢 채널: {chat.title}")
            print(f"📝 ID: {event.message.id}")
            print(f"📄 텍스트: {event.message.text[:100] if event.message.text else '[미디어]'}")
            
            # 봇으로 포워딩
            if event.message.text:
                await bot.send_message(target, event.message.text)
                print(f"✅ 포워딩 완료!")
            
        except Exception as e:
            print(f"❌ 오류: {e}")
    
    print("\n🔄 실시간 모니터링 시작...")
    print("새 메시지를 기다리는 중... (Ctrl+C로 종료)")
    
    # 실행 유지
    await user.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())