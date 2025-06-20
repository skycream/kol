"""
PDF Extractor 테스트 스크립트
"""

from pdf_extractor import PDFExtractor
import os

def test_extraction():
    """PDF 추출 테스트"""
    
    # 테스트할 PDF 파일들
    test_files = [
        "12345;회사명;파산신청서.pdf",
        "67890;다른회사;매각공고.pdf",
        "일반문서.pdf"  # 세미콜론 없는 경우
    ]
    
    extractor = PDFExtractor()
    
    for pdf_file in test_files:
        if os.path.exists(pdf_file):
            print(f"\n{'='*60}")
            print(f"테스트: {pdf_file}")
            print('='*60)
            
            result = extractor.extract(pdf_file)
            
            if result['success']:
                print(f"\n✅ 성공!")
                print(f"- 출력 위치: {result['output_dir']}")
                print(f"- 추출된 이미지: {result['image_count']}개")
                print(f"- 추출된 텍스트 페이지: {result['text_page_count']}개")
            else:
                print(f"\n❌ 실패: {result.get('error')}")
        else:
            print(f"\n⚠️  파일을 찾을 수 없습니다: {pdf_file}")
    
    # 실제 존재하는 PDF 파일로 테스트
    print(f"\n{'='*60}")
    print("실제 파일 테스트")
    print('='*60)
    
    # lib/pdf_checker 폴더의 test2.pdf로 테스트
    test_pdf = "lib/pdf_checker/test2.pdf"
    if os.path.exists(test_pdf):
        # 테스트를 위해 세미콜론이 있는 파일명으로 복사
        test_copy = "29121;테스트회사;테스트문서.pdf"
        import shutil
        shutil.copy(test_pdf, test_copy)
        
        result = extractor.extract(test_copy)
        
        # 테스트 파일 삭제
        os.remove(test_copy)
        
        if result['success']:
            print(f"\n✅ 테스트 성공!")
            print(f"- 파일명에서 추출한 ID: 29121")
            print(f"- 생성된 폴더 구조: data/29121/")
            print(f"  - data/29121/img/")
            print(f"  - data/29121/text/")
            
            # 폴더 구조 확인
            if os.path.exists("data/29121"):
                print(f"\n📁 폴더 구조 확인:")
                for root, dirs, files in os.walk("data/29121"):
                    level = root.replace("data/29121", "").count(os.sep)
                    indent = " " * 2 * level
                    print(f"{indent}{os.path.basename(root)}/")
                    subindent = " " * 2 * (level + 1)
                    for file in files[:5]:  # 처음 5개만 표시
                        print(f"{subindent}{file}")
                    if len(files) > 5:
                        print(f"{subindent}... 그 외 {len(files)-5}개 파일")

if __name__ == "__main__":
    test_extraction()