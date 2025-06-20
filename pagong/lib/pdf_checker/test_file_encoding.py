"""
파일 인코딩 문제 테스트 스크립트
문제가 되는 파일들의 인코딩을 확인합니다.
"""
import os
from pathlib import Path
import unicodedata

def analyze_filename(filename):
    """파일명의 문자 분석"""
    print(f"\n파일명: {filename[:50]}...")
    print(f"길이: {len(filename)}")
    
    # 문제가 되는 위치 확인
    try:
        filename.encode('utf-8')
        print("✓ UTF-8 인코딩 성공")
    except UnicodeEncodeError as e:
        print(f"✗ UTF-8 인코딩 실패: {e}")
        print(f"문제 위치: {e.start}-{e.end}")
        
        # 문제 문자 분석
        for i in range(max(0, e.start-5), min(len(filename), e.end+5)):
            char = filename[i]
            try:
                char.encode('utf-8')
                status = "OK"
            except:
                status = "ERROR"
            
            print(f"  [{i}] '{char}' (U+{ord(char):04X}) - {status}")
    
    # 정규화 시도
    print("\n정규화 시도:")
    for form in ['NFC', 'NFD', 'NFKC', 'NFKD']:
        try:
            normalized = unicodedata.normalize(form, filename)
            normalized.encode('utf-8')
            print(f"  {form}: 성공")
        except:
            print(f"  {form}: 실패")

def main():
    # 문제가 되는 파일명들
    problem_files = [
        "28628_명인컴퍼니(2024하합171) - 특허권매각공고문.pdf",
        "28865_엔씨씨 - 특허권매각공고문.pdf",
        "28627_명인컴퍼니(2024하합171) - 출자증권 매가공고문.pdf",
        "28659_(4부)액트테라퓨틱스(2024하합556) - 특허권매각공고문.pdf",
        "28892_인터마인즈 - 매출채권, 선급금 매각공고문.pdf"
    ]
    
    for filename in problem_files[:1]:  # 첫 번째 파일만 테스트
        analyze_filename(filename)

if __name__ == "__main__":
    main()