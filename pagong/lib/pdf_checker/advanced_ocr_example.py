"""
고급 한국어 OCR 기능 사용 예시
"""
import os
from ocr_enhancer import OCREnhancer
from accuracy_calculator import AccuracyCalculator
import time


def example_enhanced_ocr():
    """향상된 OCR 처리 예시"""
    print("=" * 60)
    print("고급 한국어 OCR 처리 예시")
    print("=" * 60)
    
    enhancer = OCREnhancer()
    
    # 스캔 PDF 파일 경로
    pdf_path = "/Users/carbon/pagong/pagong/test2.pdf"
    
    if os.path.exists(pdf_path):
        print(f"\n처리 중: {os.path.basename(pdf_path)}")
        print("다양한 전처리 및 OCR 엔진을 사용하여 최적의 결과를 찾습니다...")
        
        start_time = time.time()
        
        try:
            # 향상된 OCR 수행
            results = enhancer.enhance_pdf_ocr(pdf_path, output_detailed=True)
            
            elapsed_time = time.time() - start_time
            
            print(f"\n처리 완료! (소요 시간: {elapsed_time:.1f}초)")
            
            # 최적 결과 출력
            for page_result in results['best_results']:
                print(f"\n[페이지 {page_result['page']}]")
                print(f"최적 방법: {page_result['method']}")
                print(f"추출된 텍스트 (처음 200자):")
                print("-" * 40)
                print(page_result['text'][:200] + "..." if len(page_result['text']) > 200 else page_result['text'])
            
            # 전체 텍스트 저장
            output_file = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_enhanced_ocr.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(results['combined_text'])
            
            print(f"\n✅ 전체 OCR 결과가 '{output_file}'에 저장되었습니다.")
            
            # 상세 결과 분석
            if results['detailed_results']:
                print("\n[상세 분석 결과]")
                for page_data in results['detailed_results']:
                    print(f"\n페이지 {page_data['page']} 방법별 성능:")
                    for method, data in page_data['all_methods'].items():
                        print(f"  - {method}: {data['length']}자, 한국어 비율 {data['korean_ratio']:.1%}")
            
        except Exception as e:
            print(f"오류 발생: {e}")
    else:
        print(f"파일을 찾을 수 없습니다: {pdf_path}")


def example_compare_methods():
    """다양한 OCR 방법 비교 예시"""
    print("\n" + "=" * 60)
    print("OCR 방법별 성능 비교")
    print("=" * 60)
    
    enhancer = OCREnhancer()
    
    # 테스트할 이미지 (PDF에서 추출된 페이지)
    test_images = [
        "/Users/carbon/pagong/pdf_images/page_001.png",
        "/Users/carbon/pagong/pdf_images/page_002.png"
    ]
    
    for img_path in test_images:
        if os.path.exists(img_path):
            print(f"\n분석 중: {os.path.basename(img_path)}")
            
            try:
                comparison = enhancer.compare_ocr_methods(img_path)
                
                print(f"최적 방법: {comparison['best_method']}")
                print("\n방법별 결과:")
                
                for method, result in comparison['all_results'].items():
                    print(f"\n[{method}]")
                    print(f"- 텍스트 길이: {result['length']}자")
                    print(f"- 한국어 비율: {result['korean_ratio']:.1%}")
                    print(f"- 샘플: {result['text'][:100]}..." if result['text'] else "- 샘플: (텍스트 없음)")
                
            except Exception as e:
                print(f"오류 발생: {e}")


def example_post_processing():
    """OCR 후처리 예시"""
    print("\n" + "=" * 60)
    print("한국어 OCR 후처리 예시")
    print("=" * 60)
    
    enhancer = OCREnhancer()
    
    # 일반적인 OCR 오류가 포함된 텍스트 예시
    sample_texts = [
        "매각공고 2ㅇ24년 12월 3ㅇ일",  # 숫자 오인식
        "서울특별시 강남구 테헤란로 1 2 3",  # 띄어쓰기
        "「 공고 」 제2ㅇ24-1ㅇ5호",  # 특수문자 및 숫자
        "부동산  매각  공고 입니다",  # 불필요한 공백
        "가격은 1,ㅇㅇㅇ,ㅇㅇㅇ원 입니다"  # 숫자 오류
    ]
    
    print("원본 텍스트 → 후처리된 텍스트")
    print("-" * 40)
    
    for text in sample_texts:
        processed = enhancer.post_process_korean(text)
        print(f"{text}")
        print(f"→ {processed}\n")


def example_accuracy_with_enhanced_ocr():
    """향상된 OCR과 기존 OCR 정확도 비교"""
    print("\n" + "=" * 60)
    print("향상된 OCR vs 기존 OCR 정확도 비교")
    print("=" * 60)
    
    # 참조 텍스트가 있는 경우에만 실행
    pdf_path = "/Users/carbon/pagong/pagong/test2.pdf"
    reference_path = "test2_reference.txt"
    
    if os.path.exists(pdf_path):
        calculator = AccuracyCalculator()
        enhancer = OCREnhancer()
        
        print("1. 기존 OCR 방식으로 추출...")
        try:
            # 기존 방식 (Tesseract 기본)
            basic_text = calculator.extract_text_ocr(pdf_path)
            print(f"   - 추출된 텍스트 길이: {len(basic_text)}자")
        except:
            basic_text = ""
            print("   - 기존 OCR 실패")
        
        print("\n2. 향상된 OCR 방식으로 추출...")
        # 향상된 방식
        enhanced_results = enhancer.enhance_pdf_ocr(pdf_path)
        enhanced_text = enhanced_results['combined_text']
        print(f"   - 추출된 텍스트 길이: {len(enhanced_text)}자")
        
        # 결과 비교
        print("\n[비교 결과]")
        if len(enhanced_text) > len(basic_text):
            improvement = ((len(enhanced_text) - len(basic_text)) / max(len(basic_text), 1)) * 100
            print(f"✅ 향상된 OCR이 {improvement:.1f}% 더 많은 텍스트를 추출했습니다.")
        else:
            print("⚠️  기존 OCR과 비슷하거나 적은 텍스트를 추출했습니다.")
        
        # 한국어 비율 비교
        basic_korean_ratio = enhancer._calculate_korean_ratio(basic_text)
        enhanced_korean_ratio = enhancer._calculate_korean_ratio(enhanced_text)
        
        print(f"\n한국어 인식률:")
        print(f"- 기존 OCR: {basic_korean_ratio:.1%}")
        print(f"- 향상된 OCR: {enhanced_korean_ratio:.1%}")


if __name__ == "__main__":
    print("고급 한국어 OCR 처리 시스템\n")
    
    # EasyOCR 설치 확인
    try:
        import easyocr
        print("✅ EasyOCR 설치 확인됨")
    except ImportError:
        print("⚠️  EasyOCR이 설치되지 않았습니다.")
        print("설치: pip install easyocr")
        exit(1)
    
    # 예시 실행
    try:
        # 1. 향상된 OCR 처리
        example_enhanced_ocr()
        
        # 2. 방법별 비교
        example_compare_methods()
        
        # 3. 후처리 예시
        example_post_processing()
        
        # 4. 정확도 비교
        example_accuracy_with_enhanced_ocr()
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()