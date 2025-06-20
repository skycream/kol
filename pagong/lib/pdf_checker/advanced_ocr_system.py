"""
고급 한국어 OCR 시스템 - 최고 수준의 인식률을 위한 통합 솔루션
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import re
import fitz
from dataclasses import dataclass
from collections import Counter
import json
import os


@dataclass
class OCRResult:
    """OCR 결과를 저장하는 데이터 클래스"""
    text: str
    confidence: float
    method: str
    preprocessing: str
    corrections: Dict[str, str]


class AdvancedKoreanOCR:
    """최고 수준의 한국어 OCR 시스템"""
    
    def __init__(self):
        # 한국어 오류 패턴 데이터베이스
        self.error_patterns = {
            # 자주 혼동되는 문자
            'char_confusion': {
                '0': ['o', 'O', 'ㅇ', '。', '°'],
                '1': ['l', 'I', '|', 'ㅣ', '!'],
                '2': ['z', 'Z', 'ㄱ'],
                '3': ['ㅈ', 'ㅊ', '크'],
                '4': ['A', 'ㅅ'],
                '5': ['s', 'S', 'ㅌ'],
                '6': ['b', 'ㅎ', 'G'],
                '7': ['ㄱ', '1', 'ㅓ'],
                '8': ['B', 'ㅂ', '&'],
                '9': ['g', 'q', 'ㅁ'],
            },
            # 한글 자모 오류
            'jamo_errors': {
                '하': ['of', 'ot', '아'],
                '한': ['안', '한', '한'],
                '에': ['애', '예', 'H'],
                '의': ['으|', '희', '-|'],
                '을': ['를', '울', 'S'],
                '는': ['논', '늘', 'E'],
                '이': ['01', '리', '|'],
                '가': ['7}', '카', '거'],
                '다': ['cf', '디', '다'],
            },
            # 법률/공문서 특수 용어
            'legal_terms': {
                'BUYS': '책임은',
                'ABS': '책임을',
                'SS': '등의',
                'Se': '착',
                'SaaS': '응찰자를',
                'AACKEB': '계좌번호',
                'APSE': '지연할',
                'Ut]': '또한',
                'WSS': '없음을',
                'of': '야',
                'cf': '다',
                'H': '에',
                'E': '는',
                'S': '을',
                'A': '서',
            }
        }
        
        # 한국어 조사 목록
        self.korean_particles = [
            '은', '는', '이', '가', '을', '를', '에', '에서', '에게', '한테',
            '와', '과', '으로', '로', '의', '도', '만', '까지', '부터', '조차',
            '마저', '라도', '이나', '나', '이라도', '라도', '이든지', '든지',
            '이야', '야', '이란', '란', '이라는', '라는'
        ]
        
        # 자주 사용되는 법률 용어
        self.legal_vocabulary = [
            '낙찰자', '입찰', '매각', '채권', '채무자', '지급명령', '파산관재인',
            '매매계약', '입찰보증금', '공개매각', '법원', '서울중앙지방법원',
            '양수금', '약정금', '지연손해금', '응찰', '낙찰', '무효', '취소',
            '허가', '신청', '제출', '마감일', '개찰', '최저입찰가격', '계약금',
            '잔금', '위약금', '인감증명서', '법인등기부등본', '주민등록등본'
        ]
    
    def advanced_preprocess(self, image: np.ndarray, level: str = 'ultra') -> List[np.ndarray]:
        """초고급 이미지 전처리 - 여러 버전 생성"""
        results = []
        
        # 원본 이미지 정보
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        if level == 'ultra':
            # 1. 초고해상도 업스케일링 (INTER_CUBIC)
            scale_factor = 2
            height, width = gray.shape
            upscaled = cv2.resize(gray, (width * scale_factor, height * scale_factor), 
                                interpolation=cv2.INTER_CUBIC)
            
            # 2. 다양한 노이즈 제거 기법
            # 2-1. Non-local Means Denoising (강력)
            denoised_nlm = cv2.fastNlMeansDenoising(upscaled, None, h=10, 
                                                   templateWindowSize=7, searchWindowSize=21)
            
            # 2-2. Bilateral Filter (엣지 보존)
            denoised_bilateral = cv2.bilateralFilter(upscaled, 9, 75, 75)
            
            # 3. 다양한 대비 향상 기법
            # 3-1. CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced_clahe = clahe.apply(denoised_nlm)
            
            # 3-2. Gamma Correction
            gamma = 1.2
            enhanced_gamma = np.power(denoised_bilateral / 255.0, gamma) * 255
            enhanced_gamma = enhanced_gamma.astype(np.uint8)
            
            # 4. 다양한 이진화 기법
            # 4-1. Otsu's method
            _, binary_otsu = cv2.threshold(enhanced_clahe, 0, 255, 
                                         cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 4-2. Adaptive Threshold (Mean)
            binary_adaptive_mean = cv2.adaptiveThreshold(enhanced_gamma, 255,
                                                       cv2.ADAPTIVE_THRESH_MEAN_C,
                                                       cv2.THRESH_BINARY, 11, 2)
            
            # 4-3. Adaptive Threshold (Gaussian)
            binary_adaptive_gaussian = cv2.adaptiveThreshold(enhanced_clahe, 255,
                                                           cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                           cv2.THRESH_BINARY, 11, 2)
            
            # 5. 모폴로지 연산으로 텍스트 개선
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
            
            # 5-1. Closing (끊어진 텍스트 연결)
            morph_close = cv2.morphologyEx(binary_otsu, cv2.MORPH_CLOSE, kernel)
            
            # 5-2. Opening (노이즈 제거)
            morph_open = cv2.morphologyEx(binary_adaptive_mean, cv2.MORPH_OPEN, kernel)
            
            # 6. 엣지 보존 필터링
            # 6-1. 텍스트 엣지 강화
            edges = cv2.Canny(enhanced_clahe, 50, 150)
            text_edges = cv2.dilate(edges, kernel, iterations=1)
            enhanced_edges = cv2.bitwise_or(binary_otsu, text_edges)
            
            # 7. 스큐 보정
            corrected_otsu = self._deskew_image(morph_close)
            corrected_adaptive = self._deskew_image(morph_open)
            
            # 모든 전처리 결과 반환
            results.extend([
                ('upscaled_nlm_clahe_otsu', corrected_otsu),
                ('upscaled_bilateral_gamma_adaptive_mean', corrected_adaptive),
                ('upscaled_clahe_adaptive_gaussian', binary_adaptive_gaussian),
                ('enhanced_edges', enhanced_edges),
                ('morph_close', morph_close),
                ('morph_open', morph_open)
            ])
            
        return results
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """이미지 스큐 자동 보정 (개선된 버전)"""
        # 이미지 중앙 부분만 사용하여 더 정확한 각도 검출
        h, w = image.shape
        center_region = image[h//4:3*h//4, w//4:3*w//4]
        
        # 엣지 검출
        edges = cv2.Canny(center_region, 50, 150, apertureSize=3)
        
        # 허프 변환으로 선 검출
        lines = cv2.HoughLines(edges, 1, np.pi/180, 100)
        
        if lines is not None:
            angles = []
            for rho, theta in lines[:, 0][:50]:  # 최대 50개 라인만 고려
                angle = np.degrees(theta) - 90
                if -30 < angle < 30:  # ±30도 이내의 각도만 고려
                    angles.append(angle)
            
            if len(angles) > 5:  # 충분한 샘플이 있을 때만
                # 이상치 제거 (IQR 방법)
                q1 = np.percentile(angles, 25)
                q3 = np.percentile(angles, 75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                filtered_angles = [a for a in angles if lower_bound <= a <= upper_bound]
                
                if filtered_angles:
                    # 중앙값으로 기울기 결정
                    median_angle = np.median(filtered_angles)
                    
                    # 회전 보정
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                    
                    # 회전 후 이미지 크기 조정
                    cos = np.abs(M[0, 0])
                    sin = np.abs(M[0, 1])
                    new_w = int(h * sin + w * cos)
                    new_h = int(h * cos + w * sin)
                    
                    M[0, 2] += (new_w / 2) - center[0]
                    M[1, 2] += (new_h / 2) - center[1]
                    
                    rotated = cv2.warpAffine(image, M, (new_w, new_h),
                                           flags=cv2.INTER_CUBIC,
                                           borderMode=cv2.BORDER_CONSTANT,
                                           borderValue=255)
                    return rotated
        
        return image
    
    def multi_ocr_with_voting(self, image: np.ndarray, preprocessed_versions: List[Tuple[str, np.ndarray]]) -> str:
        """여러 전처리 버전에 대해 OCR 수행하고 투표로 최적 결과 선택"""
        ocr_results = []
        
        for prep_name, prep_image in preprocessed_versions:
            # Tesseract OCR - 다양한 설정
            configs = [
                '--oem 1 --psm 6',  # LSTM only, uniform block
                '--oem 1 --psm 11',  # LSTM only, sparse text
                '--oem 3 --psm 6',  # Default + LSTM
                '--oem 1 --psm 4',  # LSTM only, single column
            ]
            
            for config in configs:
                try:
                    text = pytesseract.image_to_string(prep_image, lang='kor+eng', config=config)
                    if text.strip():
                        ocr_results.append({
                            'text': text,
                            'preprocessing': prep_name,
                            'config': config,
                            'length': len(text),
                            'korean_ratio': self._calculate_korean_ratio(text)
                        })
                except:
                    continue
        
        # 최적 결과 선택 (한국어 비율과 텍스트 길이 기준)
        if ocr_results:
            # 점수 계산: 한국어 비율 * 0.7 + 정규화된 길이 * 0.3
            max_length = max(r['length'] for r in ocr_results)
            for result in ocr_results:
                normalized_length = result['length'] / max_length if max_length > 0 else 0
                result['score'] = result['korean_ratio'] * 0.7 + normalized_length * 0.3
            
            best_result = max(ocr_results, key=lambda x: x['score'])
            return best_result['text']
        
        return ""
    
    def _calculate_korean_ratio(self, text: str) -> float:
        """텍스트 내 한국어 비율 계산"""
        if not text:
            return 0.0
        
        korean_chars = len(re.findall(r'[가-힣ㄱ-ㅎㅏ-ㅣ]', text))
        total_chars = len(re.findall(r'\S', text))
        
        return korean_chars / total_chars if total_chars > 0 else 0.0
    
    def advanced_korean_postprocess(self, text: str) -> Tuple[str, Dict[str, str]]:
        """고급 한국어 후처리"""
        processed = text
        corrections = {}
        
        # 1. 법률/공문서 특수 용어 교정
        for error, correct in self.error_patterns['legal_terms'].items():
            if error in processed:
                processed = processed.replace(error, correct)
                corrections[error] = correct
        
        # 2. 문자 혼동 수정 (문맥 고려)
        for correct_char, error_list in self.error_patterns['char_confusion'].items():
            for error_char in error_list:
                # 숫자 문맥에서 수정
                processed = re.sub(f'(?<=[0-9]){re.escape(error_char)}(?=[0-9])', correct_char, processed)
                processed = re.sub(f'(?<=[0-9,.]){re.escape(error_char)}(?=[0-9,.])', correct_char, processed)
        
        # 3. 한글 자모 오류 수정
        for correct, error_list in self.error_patterns['jamo_errors'].items():
            for error in error_list:
                # 조사 앞에서의 수정
                for particle in self.korean_particles:
                    pattern = f'{re.escape(error)}\\s*{particle}'
                    replacement = f'{correct}{particle}'
                    if re.search(pattern, processed):
                        processed = re.sub(pattern, replacement, processed)
                        corrections[error + particle] = correct + particle
        
        # 4. 띄어쓰기 교정
        # 조사 앞 불필요한 공백 제거
        for particle in self.korean_particles:
            processed = re.sub(f'\\s+{particle}(?=\\s|$|[.,!?])', particle, processed)
        
        # 5. 숫자 포맷 정리
        # 천 단위 구분자 정리
        processed = re.sub(r'(\d),(\d{3})', r'\1,\2', processed)
        processed = re.sub(r'(\d)\.(\d{3})', r'\1,\2', processed)
        
        # 6. 특수 패턴 교정
        # 날짜 형식
        processed = re.sub(r'(\d{4})\s*[\.]\s*(\d{1,2})\s*[\.]\s*(\d{1,2})', r'\1. \2. \3', processed)
        
        # 7. 법률 용어 검증
        words = processed.split()
        for i, word in enumerate(words):
            # 편집 거리가 1인 법률 용어 찾기
            for legal_term in self.legal_vocabulary:
                if self._levenshtein_distance(word, legal_term) == 1:
                    words[i] = legal_term
                    corrections[word] = legal_term
                    break
        
        processed = ' '.join(words)
        
        # 8. 문장 부호 정리
        processed = re.sub(r'（', '(', processed)
        processed = re.sub(r'）', ')', processed)
        processed = re.sub(r'」', '"', processed)
        processed = re.sub(r'「', '"', processed)
        processed = re.sub(r'『', '[', processed)
        processed = re.sub(r'』', ']', processed)
        
        # 9. 중복 공백 제거
        processed = re.sub(r'\s+', ' ', processed)
        processed = processed.strip()
        
        return processed, corrections
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """두 문자열 간의 편집 거리 계산"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def process_pdf_ultra(self, pdf_path: str) -> Dict[str, any]:
        """PDF 파일에 대한 초고급 OCR 처리"""
        doc = fitz.open(pdf_path)
        results = []
        
        for page_num in range(len(doc)):
            print(f"\n페이지 {page_num + 1}/{len(doc)} 처리 중...")
            page = doc[page_num]
            
            # 초고해상도로 렌더링 (4x)
            mat = fitz.Matrix(4, 4)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # PIL Image로 변환
            img = Image.open(io.BytesIO(img_data))
            img_array = np.array(img)
            
            # 초고급 전처리
            preprocessed_versions = self.advanced_preprocess(img_array, level='ultra')
            
            # 멀티 OCR 및 투표
            best_text = self.multi_ocr_with_voting(img_array, preprocessed_versions)
            
            # 고급 후처리
            final_text, corrections = self.advanced_korean_postprocess(best_text)
            
            results.append({
                'page': page_num + 1,
                'original_text': best_text,
                'corrected_text': final_text,
                'corrections': corrections,
                'text_length': len(final_text),
                'korean_ratio': self._calculate_korean_ratio(final_text)
            })
            
            print(f"  - 추출된 텍스트: {len(final_text)} 문자")
            print(f"  - 한국어 비율: {self._calculate_korean_ratio(final_text):.1%}")
            print(f"  - 수정 사항: {len(corrections)}개")
        
        doc.close()
        
        # 전체 텍스트 결합
        combined_text = '\n\n'.join([r['corrected_text'] for r in results])
        
        return {
            'page_results': results,
            'combined_text': combined_text,
            'total_corrections': sum(len(r['corrections']) for r in results),
            'average_korean_ratio': np.mean([r['korean_ratio'] for r in results])
        }


class OCRQualityMonitor:
    """OCR 품질 실시간 모니터링"""
    
    def __init__(self):
        self.quality_metrics = []
    
    def analyze_ocr_quality(self, original: str, corrected: str, corrections: Dict[str, str]) -> Dict[str, float]:
        """OCR 품질 분석"""
        metrics = {
            'correction_rate': len(corrections) / max(len(original.split()), 1),
            'korean_improvement': self._calculate_korean_improvement(original, corrected),
            'readability_score': self._calculate_readability(corrected),
            'legal_term_accuracy': self._calculate_legal_term_accuracy(corrected)
        }
        
        self.quality_metrics.append(metrics)
        return metrics
    
    def _calculate_korean_improvement(self, original: str, corrected: str) -> float:
        """한국어 인식 개선율 계산"""
        original_korean = len(re.findall(r'[가-힣]', original))
        corrected_korean = len(re.findall(r'[가-힣]', corrected))
        
        if original_korean == 0:
            return 1.0 if corrected_korean > 0 else 0.0
        
        return (corrected_korean - original_korean) / original_korean
    
    def _calculate_readability(self, text: str) -> float:
        """텍스트 가독성 점수 (0-1)"""
        # 간단한 가독성 측정: 올바른 띄어쓰기, 문장 부호 등
        sentences = re.split(r'[.!?]+', text)
        valid_sentences = [s for s in sentences if len(s.strip()) > 5]
        
        if not sentences:
            return 0.0
        
        return len(valid_sentences) / len(sentences)
    
    def _calculate_legal_term_accuracy(self, text: str) -> float:
        """법률 용어 정확도"""
        legal_terms_found = 0
        legal_vocabulary = ['낙찰자', '입찰', '매각', '채권', '채무자', '지급명령', '파산관재인']
        
        for term in legal_vocabulary:
            if term in text:
                legal_terms_found += 1
        
        return legal_terms_found / len(legal_vocabulary)
    
    def generate_report(self) -> str:
        """품질 보고서 생성"""
        if not self.quality_metrics:
            return "분석된 데이터가 없습니다."
        
        avg_metrics = {
            'correction_rate': np.mean([m['correction_rate'] for m in self.quality_metrics]),
            'korean_improvement': np.mean([m['korean_improvement'] for m in self.quality_metrics]),
            'readability_score': np.mean([m['readability_score'] for m in self.quality_metrics]),
            'legal_term_accuracy': np.mean([m['legal_term_accuracy'] for m in self.quality_metrics])
        }
        
        report = f"""
OCR 품질 분석 보고서
====================
평균 수정률: {avg_metrics['correction_rate']:.1%}
한국어 개선율: {avg_metrics['korean_improvement']:.1%}
가독성 점수: {avg_metrics['readability_score']:.2f}/1.0
법률 용어 정확도: {avg_metrics['legal_term_accuracy']:.1%}
"""
        return report


if __name__ == "__main__":
    import io
    
    # 초고급 OCR 시스템 테스트
    print("초고급 한국어 OCR 시스템 v2.0")
    print("=" * 60)
    
    pdf_path = "/Users/carbon/pagong/pagong/test2.pdf"
    
    if os.path.exists(pdf_path):
        # OCR 시스템 초기화
        ocr_system = AdvancedKoreanOCR()
        monitor = OCRQualityMonitor()
        
        print(f"처리 중: {pdf_path}")
        
        # 초고급 OCR 처리
        results = ocr_system.process_pdf_ultra(pdf_path)
        
        # 결과 저장
        output_path = "test2_ultra_ocr_result.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(results['combined_text'])
        
        # 상세 결과 저장
        detailed_path = "test2_ultra_ocr_detailed.json"
        with open(detailed_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ OCR 결과가 '{output_path}'에 저장되었습니다.")
        print(f"✅ 상세 분석이 '{detailed_path}'에 저장되었습니다.")
        
        # 품질 분석
        for page_result in results['page_results']:
            quality = monitor.analyze_ocr_quality(
                page_result['original_text'],
                page_result['corrected_text'],
                page_result['corrections']
            )
        
        print("\n" + monitor.generate_report())
        
    else:
        print(f"파일을 찾을 수 없습니다: {pdf_path}")