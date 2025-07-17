#!/usr/bin/env python3
"""
간단한 실시간 테스트
"""

import asyncio
import os
from datetime import datetime
from telethon import TelegramClient, events

# 환경 변수
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def main():
    # 클라이언트
    client = TelegramClient('test_session', API_ID, API_HASH)
    bot = TelegramClient('bot_session', API_ID, API_HASH)
    
    await client.start()
    await bot.start(bot_token=BOT_TOKEN)
    
    print(f"✅ 연결 완료 - {datetime.now()}")
    
    # 채널
    channels = ["@korean_alpha", "@JoshuaDeukKOR"]
    target = "@ktradingalpha"
    
    # 채널 확인
    for ch in channels:
        try:
            entity = await client.get_entity(ch)
            print(f"✅ {ch} 접근 가능")
            
            # 최근 메시지 1개
            async for msg in client.iter_messages(entity, limit=1):
                print(f"   최근 메시지: {msg.date}")
        except Exception as e:
            print(f"❌ {ch} - {e}")
    
    # 대상 채널 확인
    try:
        target_entity = await bot.get_entity(target)
        print(f"✅ {target} 접근 가능")
        
        # 테스트 메시지
        await bot.send_message(target, f"🧪 테스트 메시지 - {datetime.now()}")
        print("✅ 테스트 메시지 전송 성공")
    except Exception as e:
        print(f"❌ {target} - {e}")
        print("봇을 채널 관리자로 추가했는지 확인하세요!")
    
    # 이벤트 핸들러
    @client.on(events.NewMessage(chats=channels))
    async def handler(event):
        print(f"\n🔔 새 메시지! - {datetime.now()}")
        chat = await event.get_chat()
        print(f"채널: {chat.title}")
        print(f"텍스트: {event.message.text[:50] if event.message.text else '[미디어]'}")
    
    print("\n🔄 실시간 모니터링 중... (30초)")
    await asyncio.sleep(30)
    
    await client.disconnect()
    await bot.disconnect()

if __name__ == "__main__":
    asyncio.run(main())