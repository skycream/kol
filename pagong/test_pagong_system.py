"""
Pagong 시스템 테스트 스크립트
PDF 처리 시스템이 제대로 작동하는지 확인
"""

import os
import shutil
from pdf_extractor import PDFExtractor
from pdf_checker import PDFChecker

def test_pdf_processing():
    """PDF 처리 테스트"""
    
    # 테스트용 PDF 파일
    test_pdf = "lib/pdf_checker/test2.pdf"
    
    if not os.path.exists(test_pdf):
        print(f"❌ 테스트 PDF 파일을 찾을 수 없습니다: {test_pdf}")
        return
    
    # 1. PDF 스캔본 여부 확인
    print("1️⃣ PDF 스캔본 여부 확인")
    checker = PDFChecker()
    is_scanned = checker.is_scanned(test_pdf)
    print(f"   - 스캔본 여부: {is_scanned}")
    
    # 2. 테스트용 data 구조 생성
    print("\n2️⃣ 테스트용 data 구조 생성")
    test_data_dir = "data_test"
    test_id = "99999"
    test_id_dir = os.path.join(test_data_dir, test_id)
    test_pdf_dir = os.path.join(test_id_dir, "pdf")
    
    # 기존 테스트 디렉토리 삭제
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir)
    
    # 디렉토리 생성
    os.makedirs(test_pdf_dir)
    
    # PDF 파일 복사
    test_pdf_copy = os.path.join(test_pdf_dir, f"{test_id};테스트회사;테스트문서.pdf")
    shutil.copy(test_pdf, test_pdf_copy)
    print(f"   - 생성된 구조: {test_data_dir}/{test_id}/pdf/")
    print(f"   - PDF 파일: {os.path.basename(test_pdf_copy)}")
    
    # 3. PDF Extractor로 직접 처리
    print("\n3️⃣ PDF Extractor로 직접 처리")
    extractor = PDFExtractor()
    result = extractor.extract(test_pdf_copy, output_dir=test_id_dir)
    
    if result['success']:
        print("   ✅ 추출 성공!")
        print(f"   - 이미지: {result['image_count']}개")
        print(f"   - 텍스트 페이지: {result['text_page_count']}개")
        print(f"   - 스캔본 여부: {result['is_scanned_doc']}")
        print(f"   - scan 폴더 생성: {result['has_scan_folder']}")
    else:
        print(f"   ❌ 추출 실패: {result.get('error')}")
    
    # 4. 생성된 폴더 구조 확인
    print("\n4️⃣ 생성된 폴더 구조 확인")
    for root, dirs, files in os.walk(test_id_dir):
        level = root.replace(test_id_dir, "").count(os.sep)
        indent = " " * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = " " * 2 * (level + 1)
        for dir in dirs:
            print(f"{subindent}{dir}/")
        for file in files[:3]:
            print(f"{subindent}{file}")
        if len(files) > 3:
            print(f"{subindent}... 그 외 {len(files)-3}개 파일")
    
    # 5. Pagong Extractor 테스트
    print("\n5️⃣ Pagong Extractor 시뮬레이션")
    print("   - pagong_extractor.py는 위와 같은 작업을 data 폴더 전체에 대해 수행")
    print("   - ID 숫자가 높은 순서대로 처리")
    print("   - img/text 폴더가 있는 ID를 만나면 중단")
    
    print("\n✅ 테스트 완료!")
    
    # 테스트 디렉토리 유지 여부 확인
    answer = input("\n테스트 디렉토리를 삭제하시겠습니까? (y/n): ")
    if answer.lower() == 'y':
        shutil.rmtree(test_data_dir)
        print("테스트 디렉토리가 삭제되었습니다.")
    else:
        print(f"테스트 결과는 {test_data_dir}에서 확인할 수 있습니다.")


if __name__ == "__main__":
    test_pdf_processing()