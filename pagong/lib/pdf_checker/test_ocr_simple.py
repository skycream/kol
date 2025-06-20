"""
간단한 OCR 테스트 (Tesseract만 사용)
"""
import os
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import numpy as np
import cv2


def extract_text_from_pdf_image(pdf_path):
    """PDF를 이미지로 변환하고 OCR 수행 (PyMuPDF 사용)"""
    
    doc = fitz.open(pdf_path)
    full_text = ""
    
    print(f"총 {len(doc)} 페이지 처리 중...")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"\n페이지 {page_num + 1} 처리 중...")
        
        # 페이지를 이미지로 변환 (높은 해상도)
        mat = fitz.Matrix(3, 3)  # 3x 확대
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # PIL Image로 변환
        img = Image.open(io.BytesIO(img_data))
        
        # numpy 배열로 변환
        img_array = np.array(img)
        
        # 그레이스케일 변환
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # 이미지 전처리
        # 1. 노이즈 제거
        denoised = cv2.medianBlur(gray, 3)
        
        # 2. 대비 향상
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # 3. 이진화
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Tesseract OCR 수행
        try:
            # 한국어 + 영어 인식
            text = pytesseract.image_to_string(binary, lang='kor+eng', config='--oem 3 --psm 6')
            
            print(f"추출된 텍스트 길이: {len(text)} 문자")
            print("샘플 (처음 100자):")
            print(text[:100] + "..." if len(text) > 100 else text)
            
            full_text += f"\n=== 페이지 {page_num + 1} ===\n"
            full_text += text
            
        except Exception as e:
            print(f"OCR 오류: {e}")
    
    doc.close()
    
    return full_text


def analyze_ocr_quality(text):
    """OCR 결과 품질 분석"""
    # 기본 통계
    total_chars = len(text)
    lines = text.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    
    # 한국어 문자 비율
    import re
    korean_chars = len(re.findall(r'[가-힣ㄱ-ㅎㅏ-ㅣ]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    numbers = len(re.findall(r'[0-9]', text))
    
    print("\n[OCR 결과 분석]")
    print(f"총 문자 수: {total_chars}")
    print(f"총 줄 수: {len(lines)}")
    print(f"비어있지 않은 줄: {len(non_empty_lines)}")
    print(f"\n문자 구성:")
    print(f"- 한글: {korean_chars} ({korean_chars/max(total_chars,1)*100:.1f}%)")
    print(f"- 영문: {english_chars} ({english_chars/max(total_chars,1)*100:.1f}%)")
    print(f"- 숫자: {numbers} ({numbers/max(total_chars,1)*100:.1f}%)")


if __name__ == "__main__":
    import io
    
    pdf_path = "/Users/carbon/pagong/pagong/test2.pdf"
    
    if os.path.exists(pdf_path):
        print(f"PDF 파일 분석: {pdf_path}")
        print("=" * 60)
        
        # PyMuPDF로 기본 정보 확인
        doc = fitz.open(pdf_path)
        print(f"PDF 정보:")
        print(f"- 페이지 수: {len(doc)}")
        
        # 첫 페이지의 텍스트 확인
        first_page_text = doc[0].get_text()
        if first_page_text.strip():
            print(f"- 텍스트 기반 PDF (추출 가능한 텍스트 있음)")
            print(f"- 첫 페이지 텍스트 샘플: {first_page_text[:100]}...")
        else:
            print(f"- 스캔 이미지 PDF (OCR 필요)")
        
        doc.close()
        
        print("\n" + "=" * 60)
        print("OCR 처리 시작...")
        print("=" * 60)
        
        # OCR 수행
        extracted_text = extract_text_from_pdf_image(pdf_path)
        
        # 결과 분석
        analyze_ocr_quality(extracted_text)
        
        # 결과 저장
        output_path = "test2_ocr_result.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        print(f"\n✅ OCR 결과가 '{output_path}'에 저장되었습니다.")
        
    else:
        print(f"파일을 찾을 수 없습니다: {pdf_path}")