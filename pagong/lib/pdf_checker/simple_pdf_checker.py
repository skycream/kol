"""
간단한 PDF OCR 품질 체크 도구
사용법: python simple_pdf_checker.py [PDF파일경로]
"""
import sys
import os
import re
import fitz
import pytesseract
from PIL import Image
import numpy as np
import cv2
import io


class SimplePDFChecker:
    """PDF OCR 품질을 간단히 체크하는 도구"""
    
    def __init__(self):
        self.results = []
    
    def check_pdf(self, pdf_path):
        """PDF 파일 체크"""
        print(f"\n📄 PDF 분석 중: {os.path.basename(pdf_path)}")
        print("=" * 50)
        
        doc = fitz.open(pdf_path)
        
        # 1. 기본 정보
        print(f"📊 기본 정보:")
        print(f"  - 총 페이지: {len(doc)}페이지")
        
        # 2. PDF 유형 확인
        has_text = False
        has_images = False
        
        for page in doc:
            if page.get_text().strip():
                has_text = True
            if page.get_images():
                has_images = True
        
        if has_text and not has_images:
            pdf_type = "텍스트 PDF (OCR 불필요)"
        elif not has_text and has_images:
            pdf_type = "스캔 PDF (OCR 필수)"
        else:
            pdf_type = "혼합형 PDF"
        
        print(f"  - PDF 유형: {pdf_type}")
        
        # 3. 텍스트 추출 시도
        print(f"\n📝 텍스트 추출 테스트:")
        
        # 첫 페이지만 테스트
        first_page = doc[0]
        direct_text = first_page.get_text()
        
        if direct_text.strip():
            print(f"  ✅ 직접 추출 가능 (텍스트 기반 PDF)")
            print(f"  - 추출된 텍스트 길이: {len(direct_text)}자")
            
            # 한국어 비율 체크
            korean_chars = len(re.findall(r'[가-힣]', direct_text))
            total_chars = len(re.findall(r'\S', direct_text))
            korean_ratio = korean_chars / total_chars if total_chars > 0 else 0
            
            print(f"  - 한국어 비율: {korean_ratio:.1%}")
            
            # 전체 텍스트 출력
            print(f"\n  📖 추출된 텍스트 전체:")
            print("  " + "-" * 40)
            # 줄바꿈 처리하여 보기 좋게 출력
            for line in direct_text.split('\n'):
                if line.strip():
                    print(f"  {line.strip()}")
            print("  " + "-" * 40)
            print(f"  [텍스트 끝 - 총 {len(direct_text)}자]")
            
        else:
            print(f"  ❌ 직접 추출 불가 (스캔 이미지)")
            print(f"  🔍 OCR 수행 중...")
            
            # OCR 수행
            mat = fitz.Matrix(2, 2)  # 2x 확대
            pix = first_page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            img = Image.open(io.BytesIO(img_data))
            img_array = np.array(img)
            
            # 간단한 전처리
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
            else:
                gray = img_array
            
            # OCR
            try:
                ocr_text = pytesseract.image_to_string(gray, lang='kor+eng')
                
                if ocr_text.strip():
                    print(f"  ✅ OCR 성공")
                    print(f"  - 추출된 텍스트 길이: {len(ocr_text)}자")
                    
                    # 한국어 비율
                    korean_chars = len(re.findall(r'[가-힣]', ocr_text))
                    total_chars = len(re.findall(r'\S', ocr_text))
                    korean_ratio = korean_chars / total_chars if total_chars > 0 else 0
                    
                    print(f"  - 한국어 비율: {korean_ratio:.1%}")
                    
                    # OCR 품질 지표
                    unknown_chars = len(re.findall(r'[^가-힣a-zA-Z0-9\s.,!?()"-]', ocr_text))
                    quality_score = max(0, 100 - (unknown_chars / max(total_chars, 1) * 100))
                    
                    print(f"  - OCR 품질 점수: {quality_score:.0f}/100")
                    
                    # OCR 전체 텍스트 출력
                    print(f"\n  📖 OCR로 추출된 텍스트 전체:")
                    print("  " + "-" * 40)
                    # 줄바꿈 처리하여 보기 좋게 출력
                    for line in ocr_text.split('\n'):
                        if line.strip():
                            print(f"  {line.strip()}")
                    print("  " + "-" * 40)
                    print(f"  [OCR 텍스트 끝 - 총 {len(ocr_text)}자]")
                    
                    # 텍스트 파일로 저장
                    output_filename = pdf_path.replace('.pdf', '_ocr_result.txt')
                    with open(output_filename, 'w', encoding='utf-8') as f:
                        f.write(ocr_text)
                    print(f"\n  💾 OCR 결과가 '{os.path.basename(output_filename)}'에 저장되었습니다.")
                else:
                    print(f"  ❌ OCR 실패 - 텍스트를 추출할 수 없습니다")
                    
            except Exception as e:
                print(f"  ❌ OCR 오류: {str(e)}")
        
        # 4. 권장사항
        print(f"\n💡 권장사항:")
        if pdf_type == "텍스트 PDF (OCR 불필요)":
            print(f"  - 이미 텍스트 추출이 가능한 PDF입니다")
            print(f"  - OCR이 필요하지 않습니다")
        elif pdf_type == "스캔 PDF (OCR 필수)":
            print(f"  - OCR 처리가 필요한 스캔 문서입니다")
            if 'korean_ratio' in locals() and korean_ratio < 0.3:
                print(f"  - 한국어 인식률이 낮습니다. 다음을 확인하세요:")
                print(f"    • 스캔 품질 (300 DPI 이상 권장)")
                print(f"    • 문서 기울기")
                print(f"    • 이미지 선명도")
        
        doc.close()
        print("\n" + "=" * 50)
    
    def check_all_pdfs(self, folder_path):
        """폴더 내 모든 PDF 체크"""
        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print("PDF 파일이 없습니다.")
            return
        
        print(f"\n🗂️  총 {len(pdf_files)}개의 PDF 파일 발견")
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(folder_path, pdf_file)
            try:
                self.check_pdf(pdf_path)
            except Exception as e:
                print(f"\n❌ {pdf_file} 처리 중 오류: {str(e)}")


def main():
    """메인 함수"""
    print("🔍 간단한 PDF OCR 품질 체크 도구")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        # 특정 파일 지정
        pdf_path = sys.argv[1]
        if os.path.exists(pdf_path):
            checker = SimplePDFChecker()
            checker.check_pdf(pdf_path)
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {pdf_path}")
    else:
        # 사용법 안내
        print("\n사용법:")
        print("1. 특정 PDF 파일 체크:")
        print("   python simple_pdf_checker.py [PDF파일경로]")
        print("\n2. 현재 폴더의 모든 PDF 체크:")
        print("   python simple_pdf_checker.py")
        
        # 현재 폴더 체크
        response = input("\n현재 폴더의 PDF를 체크하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            checker = SimplePDFChecker()
            checker.check_all_pdfs(".")


if __name__ == "__main__":
    main()