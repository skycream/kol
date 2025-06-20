"""
OCR 인식률 계산 방법 상세 설명 및 시연
"""
import re
from typing import Dict, Tuple, List
import Levenshtein
from difflib import SequenceMatcher


class OCRAccuracyExplained:
    """OCR 정확도 계산 방법을 설명하고 시연하는 클래스"""
    
    def explain_accuracy_methods(self):
        """정확도 계산 방법들을 설명"""
        
        print("=" * 60)
        print("OCR 인식률 계산 방법 설명")
        print("=" * 60)
        
        # 1. 참조 텍스트가 있는 경우
        print("\n1. 참조 텍스트(Ground Truth)가 있는 경우")
        print("-" * 40)
        
        # 예시 데이터
        reference = "서울중앙지방법원 2015차전357726"
        ocr_result1 = "서울중앙지방법원 2015차전357726"  # 완벽
        ocr_result2 = "서울중앙지방법원 2이5차전357726"  # 숫자 오류
        ocr_result3 = "서을중앙지방법원 20l5차전35772G"  # 여러 오류
        
        print(f"참조 텍스트: '{reference}'")
        print(f"OCR 결과 1: '{ocr_result1}'")
        print(f"OCR 결과 2: '{ocr_result2}'")
        print(f"OCR 결과 3: '{ocr_result3}'")
        
        # 문자 수준 정확도 (CER - Character Error Rate)
        print("\n[문자 수준 정확도 계산]")
        for i, ocr in enumerate([ocr_result1, ocr_result2, ocr_result3], 1):
            distance = Levenshtein.distance(reference, ocr)
            cer = distance / len(reference)
            accuracy = (1 - cer) * 100
            print(f"OCR {i}: 편집거리={distance}, CER={cer:.3f}, 정확도={accuracy:.1f}%")
        
        # 단어 수준 정확도 (WER - Word Error Rate)
        print("\n[단어 수준 정확도 계산]")
        ref_words = reference.split()
        for i, ocr in enumerate([ocr_result1, ocr_result2, ocr_result3], 1):
            ocr_words = ocr.split()
            distance = Levenshtein.distance(ref_words, ocr_words)
            wer = distance / len(ref_words) if ref_words else 0
            accuracy = (1 - wer) * 100
            print(f"OCR {i}: 단어 오류={distance}, WER={wer:.3f}, 정확도={accuracy:.1f}%")
    
    def explain_korean_ratio_calculation(self):
        """한국어 비율 계산 방법 설명"""
        print("\n\n2. 한국어 비율 계산 방법")
        print("-" * 40)
        
        sample_texts = [
            "채권(지급명령) 매각공고",
            "AAA FBS) vA2Z-sa",
            "서울중앙지방법원 2015차전357726",
            "BUYS ABS 책임은 WSS"
        ]
        
        for text in sample_texts:
            # 한글 문자 개수
            korean_chars = len(re.findall(r'[가-힣ㄱ-ㅎㅏ-ㅣ]', text))
            # 전체 문자 개수 (공백 제외)
            total_chars = len(re.findall(r'\S', text))
            # 비율 계산
            ratio = korean_chars / total_chars if total_chars > 0 else 0
            
            print(f"\n텍스트: '{text}'")
            print(f"한글 문자: {korean_chars}개")
            print(f"전체 문자: {total_chars}개")
            print(f"한국어 비율: {ratio:.1%}")
    
    def explain_without_reference(self):
        """참조 텍스트 없이 품질 평가하는 방법"""
        print("\n\n3. 참조 텍스트 없이 품질 평가")
        print("-" * 40)
        
        ocr_text = """
        서울중앙지방법원 2이5차전357726
        BUYS 책임은 ABS 충족하지 WSS
        입찰보중금은 2025. 3. 31까지
        """
        
        print(f"OCR 텍스트:\n{ocr_text}")
        
        # 평가 지표들
        metrics = {}
        
        # 1. 한국어 비율
        korean_chars = len(re.findall(r'[가-힣]', ocr_text))
        total_chars = len(re.findall(r'\S', ocr_text))
        metrics['korean_ratio'] = korean_chars / total_chars if total_chars > 0 else 0
        
        # 2. 알 수 없는 문자/단어 비율
        unknown_patterns = len(re.findall(r'[A-Z]{3,}', ocr_text))  # 연속된 대문자
        words = ocr_text.split()
        metrics['unknown_word_ratio'] = unknown_patterns / len(words) if words else 0
        
        # 3. 문서 구조 점수
        structure_score = 1.0
        if not re.search(r'\d{4}차전\d+', ocr_text):  # 사건번호 패턴
            structure_score -= 0.2
        if not re.search(r'\d{4}\.\s*\d{1,2}\.\s*\d{1,2}', ocr_text):  # 날짜 패턴
            structure_score -= 0.2
        metrics['structure_score'] = structure_score
        
        # 4. 특수 패턴 감지
        error_patterns = ['BUYS', 'ABS', 'WSS', '이5', '보중금']
        errors_found = sum(1 for pattern in error_patterns if pattern in ocr_text)
        metrics['error_pattern_count'] = errors_found
        
        print("\n[품질 평가 지표]")
        print(f"한국어 비율: {metrics['korean_ratio']:.1%}")
        print(f"알 수 없는 단어 비율: {metrics['unknown_word_ratio']:.1%}")
        print(f"문서 구조 점수: {metrics['structure_score']:.1f}")
        print(f"오류 패턴 발견: {metrics['error_pattern_count']}개")
        
        # 종합 품질 점수 (가중 평균)
        quality_score = (
            metrics['korean_ratio'] * 0.4 +
            (1 - metrics['unknown_word_ratio']) * 0.2 +
            metrics['structure_score'] * 0.3 +
            (1 - metrics['error_pattern_count']/10) * 0.1
        ) * 100
        
        print(f"\n종합 품질 점수: {quality_score:.1f}/100")
    
    def demonstrate_real_accuracy_test(self):
        """실제 정확도 테스트 시연"""
        print("\n\n4. 실제 정확도 테스트 시연")
        print("-" * 40)
        
        # 가상의 참조 텍스트와 OCR 결과
        reference = """채권(지급명령) 매각공고
1. 매각대상 채권 내역
서울중앙지방법원 2015차전357726
약정금 지급명령 채권
1,060,438,982원"""
        
        ocr_result = """채권(지급명령) 매각공고
1. 매각대상 채권 내역
서울중앙지방법원 2이5차전357726
약정금 지급명령 채권
1,060,438,982원"""
        
        print("참조 텍스트:")
        print(reference)
        print("\nOCR 결과:")
        print(ocr_result)
        
        # 상세 분석
        print("\n[상세 정확도 분석]")
        
        # 1. 전체 텍스트 유사도
        similarity = SequenceMatcher(None, reference, ocr_result).ratio()
        print(f"전체 텍스트 유사도: {similarity:.1%}")
        
        # 2. 줄별 정확도
        ref_lines = reference.split('\n')
        ocr_lines = ocr_result.split('\n')
        
        print("\n줄별 정확도:")
        for i, (ref_line, ocr_line) in enumerate(zip(ref_lines, ocr_lines)):
            if ref_line.strip():
                line_similarity = SequenceMatcher(None, ref_line, ocr_line).ratio()
                print(f"  {i+1}번째 줄: {line_similarity:.1%}")
                if line_similarity < 1.0:
                    print(f"    참조: '{ref_line}'")
                    print(f"    OCR: '{ocr_line}'")
        
        # 3. 중요 정보 추출 정확도
        print("\n중요 정보 추출 정확도:")
        
        # 사건번호
        ref_case = re.search(r'(\d{4}차전\d+)', reference)
        ocr_case = re.search(r'(\d+차전\d+)', ocr_result)
        if ref_case and ocr_case:
            case_accuracy = SequenceMatcher(None, ref_case.group(1), ocr_case.group(1)).ratio()
            print(f"  사건번호: {case_accuracy:.1%} ('{ref_case.group(1)}' vs '{ocr_case.group(1)}')")
        
        # 금액
        ref_amount = re.search(r'([\d,]+원)', reference)
        ocr_amount = re.search(r'([\d,]+원)', ocr_result)
        if ref_amount and ocr_amount:
            amount_accuracy = 1.0 if ref_amount.group(1) == ocr_amount.group(1) else 0.0
            print(f"  금액: {amount_accuracy:.1%} ('{ref_amount.group(1)}' vs '{ocr_amount.group(1)}')")
    
    def explain_limitations(self):
        """정확도 측정의 한계점 설명"""
        print("\n\n5. OCR 정확도 측정의 한계점")
        print("-" * 40)
        
        print("""
1. 참조 텍스트(Ground Truth) 없이는 절대적 정확도 측정 불가
   - 한국어 비율, 오류 패턴 등은 간접적 지표일 뿐
   - 실제 정확도는 원본과 비교해야만 알 수 있음

2. 문서 유형별 특성 고려 필요
   - 법률 문서: 전문 용어, 정형화된 패턴
   - 일반 문서: 다양한 어휘, 자유로운 형식
   
3. OCR 오류의 다양성
   - 문자 대체: 0→O, 1→l
   - 문자 누락/추가
   - 단어 분리/결합 오류
   
4. 언어별 특성
   - 한글: 자모 결합, 조사 처리
   - 숫자: 형식 다양성 (천 단위, 소수점 등)
   - 특수문자: 괄호, 하이픈 등
        """)


if __name__ == "__main__":
    explainer = OCRAccuracyExplained()
    
    # 모든 설명 실행
    explainer.explain_accuracy_methods()
    explainer.explain_korean_ratio_calculation()
    explainer.explain_without_reference()
    explainer.demonstrate_real_accuracy_test()
    explainer.explain_limitations()
    
    print("\n" + "=" * 60)
    print("결론")
    print("=" * 60)
    print("""
OCR 정확도는 다음과 같이 측정합니다:

1. 이상적인 경우 (참조 텍스트 있음):
   - 문자 단위 비교 (Character Error Rate)
   - 단어 단위 비교 (Word Error Rate)
   - 편집 거리 (Levenshtein Distance) 활용

2. 현실적인 경우 (참조 텍스트 없음):
   - 한국어 비율 (전체 문자 중 한글 비율)
   - 오류 패턴 감지 (알려진 OCR 오류)
   - 문서 구조 평가 (예상 패턴 존재 여부)
   - 통계적 추정 (언어 모델 기반)

3. 저희 시스템의 정확도 표시:
   - 주로 한국어 비율과 오류 패턴을 기반으로 추정
   - 실제 정확도가 아닌 '품질 점수'에 가까움
   - 완벽한 측정을 위해서는 human-in-the-loop 필요
    """)