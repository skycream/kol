"""
OCR 정확도 테스트 - test2.pdf
"""
import os
import re
from typing import Dict, Tuple, List
import json
from metrics import TextMetrics
from fast_advanced_ocr import FastAdvancedOCR
import fitz
from difflib import SequenceMatcher


class OCRAccuracyTester:
    """OCR 정확도를 테스트하고 분석하는 클래스"""
    
    def __init__(self):
        self.metrics = TextMetrics()
        self.ocr = FastAdvancedOCR()
        
        # test2.pdf의 실제 텍스트 (일부 샘플)
        # 실제 문서를 보고 정확한 텍스트를 입력
        self.ground_truth_samples = {
            1: {
                'title': '채권(지급명령) 매각공고',
                'sample': '서울중앙지방법원',
                'numbers': ['2015차전357726', '1,060,438,982', '2013. 11. 22'],
                'legal_terms': ['약정금', '지급명령', '채권', '지연손해금']
            },
            2: {
                'title': '최저 입찰가격',
                'sample': '회차',
                'numbers': ['125,000,000'],
                'legal_terms': ['입찰보증금', '제출', '마감일', '개찰일']
            },
            3: {
                'title': '입찰서 제출 마감일 및 장소',
                'sample': '대우송도개발주 파산관재인 변호사 김민회',
                'numbers': ['06596', '287', '401'],
                'legal_terms': ['개찰일시', '일반경쟁입찰', '낙찰자']
            }
        }
    
    def extract_specific_elements(self, text: str) -> Dict[str, List[str]]:
        """텍스트에서 특정 요소들을 추출"""
        elements = {
            'numbers': re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', text),
            'dates': re.findall(r'\d{4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}', text),
            'legal_terms': [],
            'korean_words': re.findall(r'[가-힣]+', text)
        }
        
        # 법률 용어 찾기
        legal_vocabulary = [
            '채권', '지급명령', '매각', '입찰', '낙찰자', '파산관재인',
            '매매계약', '입찰보증금', '약정금', '양수금', '지연손해금',
            '서울중앙지방법원', '개찰', '응찰', '채무자'
        ]
        
        for term in legal_vocabulary:
            if term in text:
                elements['legal_terms'].append(term)
        
        return elements
    
    def calculate_element_accuracy(self, ocr_elements: Dict, truth_elements: Dict) -> Dict[str, float]:
        """요소별 정확도 계산"""
        accuracies = {}
        
        for element_type in ['numbers', 'dates', 'legal_terms']:
            if element_type in truth_elements and truth_elements[element_type]:
                found = 0
                for item in truth_elements[element_type]:
                    # OCR 결과에서 유사한 항목 찾기
                    for ocr_item in ocr_elements.get(element_type, []):
                        similarity = SequenceMatcher(None, item, ocr_item).ratio()
                        if similarity > 0.8:  # 80% 이상 유사하면 찾은 것으로 간주
                            found += 1
                            break
                
                accuracies[element_type] = found / len(truth_elements[element_type])
            else:
                accuracies[element_type] = 0.0
        
        return accuracies
    
    def test_ocr_accuracy(self, pdf_path: str) -> Dict[str, any]:
        """OCR 정확도 종합 테스트"""
        print("OCR 정확도 테스트 시작...")
        print("=" * 60)
        
        # 1. OCR 수행
        ocr_results = self.ocr.process_pdf(pdf_path)
        
        # 2. 페이지별 분석
        page_analyses = []
        
        for page_result in ocr_results['page_results']:
            page_num = page_result['page']
            ocr_text = page_result['text']
            
            # 요소 추출
            ocr_elements = self.extract_specific_elements(ocr_text)
            
            # 샘플 기준 텍스트가 있는 경우 정확도 계산
            if page_num in self.ground_truth_samples:
                truth = self.ground_truth_samples[page_num]
                
                # 제목 찾기
                title_found = truth['title'] in ocr_text
                
                # 샘플 텍스트 찾기
                sample_found = truth['sample'] in ocr_text
                
                # 요소별 정확도
                element_accuracy = self.calculate_element_accuracy(
                    ocr_elements,
                    {
                        'numbers': truth.get('numbers', []),
                        'legal_terms': truth.get('legal_terms', [])
                    }
                )
                
                page_analysis = {
                    'page': page_num,
                    'title_found': title_found,
                    'sample_found': sample_found,
                    'element_accuracy': element_accuracy,
                    'korean_ratio': page_result['korean_ratio'],
                    'total_korean_words': len(ocr_elements['korean_words']),
                    'legal_terms_found': ocr_elements['legal_terms']
                }
            else:
                page_analysis = {
                    'page': page_num,
                    'korean_ratio': page_result['korean_ratio'],
                    'total_korean_words': len(ocr_elements['korean_words']),
                    'legal_terms_found': ocr_elements['legal_terms'],
                    'numbers_found': len(ocr_elements['numbers']),
                    'dates_found': len(ocr_elements['dates'])
                }
            
            page_analyses.append(page_analysis)
        
        # 3. 전체 텍스트 품질 분석
        full_text = ocr_results['combined_text']
        
        # 문자 수준 통계
        total_chars = len(re.findall(r'\S', full_text))
        korean_chars = len(re.findall(r'[가-힣]', full_text))
        number_chars = len(re.findall(r'\d', full_text))
        english_chars = len(re.findall(r'[a-zA-Z]', full_text))
        
        # 단어 수준 통계
        words = full_text.split()
        korean_words = [w for w in words if re.search(r'[가-힣]', w)]
        
        # 품질 점수 계산
        quality_scores = {
            'korean_recognition': korean_chars / max(total_chars, 1),
            'word_completeness': len([w for w in korean_words if len(w) > 1]) / max(len(korean_words), 1),
            'legal_term_coverage': len(set(sum([p['legal_terms_found'] for p in page_analyses], []))) / 15,  # 15개 주요 법률용어 기준
            'structural_integrity': self._evaluate_structure(full_text)
        }
        
        # 종합 점수
        overall_score = sum(quality_scores.values()) / len(quality_scores) * 100
        
        return {
            'overall_score': overall_score,
            'quality_scores': quality_scores,
            'character_stats': {
                'total': total_chars,
                'korean': korean_chars,
                'numbers': number_chars,
                'english': english_chars,
                'korean_ratio': korean_chars / max(total_chars, 1)
            },
            'word_stats': {
                'total_words': len(words),
                'korean_words': len(korean_words),
                'average_word_length': sum(len(w) for w in korean_words) / max(len(korean_words), 1)
            },
            'page_analyses': page_analyses,
            'ocr_results': ocr_results
        }
    
    def _evaluate_structure(self, text: str) -> float:
        """텍스트 구조 평가"""
        score = 1.0
        
        # 페이지 구분자 확인
        if '===' not in text:
            score -= 0.2
        
        # 번호 매기기 패턴 확인
        if not re.search(r'\d+\s*[.)]\s*[가-힣]', text):
            score -= 0.2
        
        # 제목 패턴 확인
        if not re.search(r'[가-힣]+\s*공고', text):
            score -= 0.1
        
        # 법률 문서 구조 확인
        if '제출' not in text or '마감' not in text:
            score -= 0.1
        
        return max(score, 0.0)
    
    def generate_accuracy_report(self, test_results: Dict) -> str:
        """정확도 테스트 보고서 생성"""
        report = []
        report.append("=" * 60)
        report.append("OCR 정확도 테스트 보고서")
        report.append("=" * 60)
        
        # 종합 점수
        report.append(f"\n[종합 정확도 점수: {test_results['overall_score']:.1f}/100]")
        
        # 품질 점수 상세
        report.append("\n[품질 점수 상세]")
        scores = test_results['quality_scores']
        report.append(f"- 한국어 인식률: {scores['korean_recognition']:.1%}")
        report.append(f"- 단어 완성도: {scores['word_completeness']:.1%}")
        report.append(f"- 법률용어 인식률: {scores['legal_term_coverage']:.1%}")
        report.append(f"- 문서구조 보존도: {scores['structural_integrity']:.1%}")
        
        # 문자 통계
        report.append("\n[문자 수준 분석]")
        stats = test_results['character_stats']
        report.append(f"- 전체 문자: {stats['total']:,}")
        report.append(f"- 한글: {stats['korean']:,} ({stats['korean_ratio']:.1%})")
        report.append(f"- 숫자: {stats['numbers']:,}")
        report.append(f"- 영문: {stats['english']:,}")
        
        # 페이지별 분석
        report.append("\n[페이지별 분석]")
        for page in test_results['page_analyses']:
            report.append(f"\n페이지 {page['page']}:")
            report.append(f"- 한국어 비율: {page['korean_ratio']:.1%}")
            report.append(f"- 한글 단어 수: {page['total_korean_words']}")
            
            if 'title_found' in page:
                report.append(f"- 제목 인식: {'✓' if page['title_found'] else '✗'}")
                report.append(f"- 샘플 텍스트 인식: {'✓' if page['sample_found'] else '✗'}")
                
                if 'element_accuracy' in page:
                    report.append("- 요소별 정확도:")
                    for elem, acc in page['element_accuracy'].items():
                        report.append(f"  - {elem}: {acc:.1%}")
            
            if page['legal_terms_found']:
                report.append(f"- 인식된 법률용어: {', '.join(page['legal_terms_found'][:5])}")
        
        # 개선 권장사항
        report.append("\n[개선 권장사항]")
        if test_results['overall_score'] < 70:
            report.append("- 문서 스캔 품질 개선 필요 (300 DPI 이상)")
            report.append("- 이미지 전처리 강화 권장")
            report.append("- 상용 OCR API 사용 검토")
        elif test_results['overall_score'] < 85:
            report.append("- 추가적인 후처리 규칙 적용")
            report.append("- 문서별 맞춤형 사전 구축")
        else:
            report.append("- 현재 OCR 품질이 양호함")
            report.append("- 지속적인 모니터링 권장")
        
        return "\n".join(report)


if __name__ == "__main__":
    print("test2.pdf OCR 정확도 테스트")
    print("=" * 60)
    
    pdf_path = "/Users/carbon/pagong/pagong/test2.pdf"
    
    if os.path.exists(pdf_path):
        tester = OCRAccuracyTester()
        
        # 정확도 테스트 수행
        test_results = tester.test_ocr_accuracy(pdf_path)
        
        # 보고서 생성
        report = tester.generate_accuracy_report(test_results)
        print(report)
        
        # 결과 저장
        with open("test2_accuracy_report.txt", 'w', encoding='utf-8') as f:
            f.write(report)
        
        # 상세 결과 JSON 저장
        with open("test2_accuracy_details.json", 'w', encoding='utf-8') as f:
            json.dump(test_results, f, ensure_ascii=False, indent=2)
        
        print("\n✅ 정확도 보고서가 'test2_accuracy_report.txt'에 저장되었습니다.")
        print("✅ 상세 분석이 'test2_accuracy_details.json'에 저장되었습니다.")
        
    else:
        print(f"파일을 찾을 수 없습니다: {pdf_path}")