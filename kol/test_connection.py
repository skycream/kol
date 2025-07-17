#!/usr/bin/env python3
"""
텔레그램 연결 및 채널 테스트
"""

import asyncio
import os
from telethon import TelegramClient, events
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

print(f"API_ID: {API_ID}")
print(f"API_HASH: {API_HASH[:10]}...")

async def test_connection():
    """연결 테스트"""
    client = TelegramClient('test_connection_session', API_ID, API_HASH)
    
    try:
        await client.start()
        print("✅ 텔레그램 연결 성공")
        
        # 나의 정보
        me = await client.get_me()
        print(f"👤 로그인 계정: {me.first_name} (ID: {me.id})")
        
        # 채널 테스트
        channels = ["@korean_alpha", "@JoshuaDeukKOR"]
        
        for channel_name in channels:
            try:
                channel = await client.get_entity(channel_name)
                print(f"\n📢 채널: {channel_name}")
                print(f"   - 제목: {channel.title}")
                print(f"   - ID: {channel.id}")
                print(f"   - 참여자 수: {getattr(channel, 'participants_count', 'N/A')}")
                
                # 최근 메시지 1개 가져오기
                async for msg in client.iter_messages(channel, limit=1):
                    print(f"   - 최근 메시지 ID: {msg.id}")
                    print(f"   - 날짜: {msg.date}")
                    print(f"   - 텍스트 미리보기: {msg.text[:50] if msg.text else '[미디어]'}...")
                    
            except Exception as e:
                print(f"❌ {channel_name} 접근 실패: {e}")
        
        # 실시간 테스트
        print("\n🔄 실시간 메시지 감지 테스트 (30초간)...")
        
        @client.on(events.NewMessage(chats=channels))
        async def handler(event):
            chat = await event.get_chat()
            print(f"🔔 새 메시지 감지!")
            print(f"   - 채널: {chat.title}")
            print(f"   - ID: {event.message.id}")
            print(f"   - 텍스트: {event.message.text[:50] if event.message.text else '[미디어]'}...")
        
        # 30초 대기
        await asyncio.sleep(30)
        print("\n✅ 테스트 완료")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_connection())