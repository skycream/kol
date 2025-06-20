"""
한국어 OCR 인식률 향상을 위한 고급 처리 모듈
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import re
from pdf2image import convert_from_path
import easyocr


class OCREnhancer:
    """한국어 OCR 인식률을 향상시키는 클래스"""
    
    def __init__(self):
        # EasyOCR 초기화 (한국어 + 영어)
        self.reader = easyocr.Reader(['ko', 'en'], gpu=False)
        
        # 한국어 특수 패턴
        self.korean_patterns = {
            'common_errors': {
                '0': ['ㅇ', 'o', 'O'],
                '8': ['ㅂ', 'B'],
                '6': ['b', 'ㅎ'],
                '1': ['l', 'I', '|'],
                '2': ['ㄱ', 'z'],
                '3': ['ㅈ', 'ㅊ'],
                '4': ['ㅅ', 'A'],
                '5': ['s', 'S'],
                '7': ['ㄱ', '1'],
                '9': ['g', 'q'],
            },
            'korean_jamo_errors': {
                'ㅐ': ['H', 'H|'],
                'ㅔ': ['H', 'H|'],
                'ㅚ': ['H', 'H.'],
                'ㅟ': ['T', 'T|'],
                'ㅢ': ['=', '-|'],
            }
        }
    
    def preprocess_image(self, image: np.ndarray, enhancement_level: str = 'high') -> np.ndarray:
        """
        이미지 전처리를 통한 OCR 인식률 향상
        
        Args:
            image: 입력 이미지
            enhancement_level: 'low', 'medium', 'high'
        """
        # 그레이스케일 변환
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        if enhancement_level == 'high':
            # 1. 노이즈 제거
            denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
            
            # 2. 적응형 히스토그램 균등화
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # 3. 샤프닝
            kernel = np.array([[-1,-1,-1],
                              [-1, 9,-1],
                              [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)
            
            # 4. 이진화 (Otsu's method)
            _, binary = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 5. 모폴로지 연산으로 텍스트 개선
            kernel = np.ones((2,2), np.uint8)
            morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # 6. 기울기 보정
            corrected = self._correct_skew(morph)
            
            return corrected
            
        elif enhancement_level == 'medium':
            # 중간 수준 처리
            denoised = cv2.medianBlur(gray, 3)
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
            
        else:  # low
            # 기본 처리
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
    
    def _correct_skew(self, image: np.ndarray) -> np.ndarray:
        """이미지 기울기 자동 보정"""
        # 엣지 검출
        edges = cv2.Canny(image, 50, 150, apertureSize=3)
        
        # 허프 변환으로 선 검출
        lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
        
        if lines is not None:
            angles = []
            for rho, theta in lines[:, 0]:
                angle = np.degrees(theta) - 90
                if -45 < angle < 45:
                    angles.append(angle)
            
            if angles:
                # 중앙값으로 기울기 결정
                median_angle = np.median(angles)
                
                # 회전 보정
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                rotated = cv2.warpAffine(image, M, (w, h), 
                                       flags=cv2.INTER_CUBIC,
                                       borderMode=cv2.BORDER_REPLICATE)
                return rotated
        
        return image
    
    def multi_engine_ocr(self, image: np.ndarray, lang: str = 'kor+eng') -> Dict[str, str]:
        """
        여러 OCR 엔진을 사용한 텍스트 추출
        
        Returns:
            각 엔진별 추출 결과
        """
        results = {}
        
        # 1. Tesseract OCR
        try:
            # 기본 설정
            tess_config = '--oem 3 --psm 6'
            results['tesseract_default'] = pytesseract.image_to_string(
                image, lang=lang, config=tess_config
            )
            
            # LSTM 모드
            tess_config_lstm = '--oem 1 --psm 6'
            results['tesseract_lstm'] = pytesseract.image_to_string(
                image, lang=lang, config=tess_config_lstm
            )
            
            # 단일 블록 모드 (문서 구조가 단순한 경우)
            tess_config_single = '--oem 3 --psm 11'
            results['tesseract_single'] = pytesseract.image_to_string(
                image, lang=lang, config=tess_config_single
            )
        except Exception as e:
            print(f"Tesseract 오류: {e}")
        
        # 2. EasyOCR
        try:
            easy_result = self.reader.readtext(image, detail=0, paragraph=True)
            results['easyocr'] = '\n'.join(easy_result)
        except Exception as e:
            print(f"EasyOCR 오류: {e}")
        
        return results
    
    def enhance_pdf_ocr(self, pdf_path: str, output_detailed: bool = False) -> Dict[str, any]:
        """
        PDF 파일의 OCR 인식률 향상
        
        Args:
            pdf_path: PDF 파일 경로
            output_detailed: 상세 결과 출력 여부
        """
        # PDF를 이미지로 변환
        images = convert_from_path(pdf_path, dpi=300)  # 고해상도로 변환
        
        all_results = []
        best_results = []
        
        for page_num, image in enumerate(images):
            print(f"페이지 {page_num + 1} 처리 중...")
            
            # PIL Image를 numpy 배열로 변환
            img_array = np.array(image)
            
            # 다양한 전처리 수준 적용
            page_results = {}
            
            for level in ['low', 'medium', 'high']:
                preprocessed = self.preprocess_image(img_array, level)
                
                # 여러 엔진으로 OCR 수행
                ocr_results = self.multi_engine_ocr(preprocessed)
                
                for engine, text in ocr_results.items():
                    key = f"{level}_{engine}"
                    page_results[key] = {
                        'text': text,
                        'length': len(text),
                        'korean_ratio': self._calculate_korean_ratio(text)
                    }
            
            # 최적의 결과 선택 (한국어 비율과 텍스트 길이 기준)
            best_result = max(page_results.items(), 
                            key=lambda x: x[1]['length'] * x[1]['korean_ratio'])
            
            best_results.append({
                'page': page_num + 1,
                'method': best_result[0],
                'text': best_result[1]['text']
            })
            
            if output_detailed:
                all_results.append({
                    'page': page_num + 1,
                    'all_methods': page_results
                })
        
        return {
            'best_results': best_results,
            'detailed_results': all_results if output_detailed else None,
            'combined_text': '\n\n'.join([r['text'] for r in best_results])
        }
    
    def _calculate_korean_ratio(self, text: str) -> float:
        """텍스트 내 한국어 비율 계산"""
        if not text:
            return 0.0
        
        korean_chars = len(re.findall(r'[가-힣ㄱ-ㅎㅏ-ㅣ]', text))
        total_chars = len(re.findall(r'\S', text))  # 공백 제외
        
        return korean_chars / total_chars if total_chars > 0 else 0.0
    
    def post_process_korean(self, text: str) -> str:
        """한국어 OCR 결과 후처리"""
        processed = text
        
        # 1. 일반적인 OCR 오류 수정
        for correct, errors in self.korean_patterns['common_errors'].items():
            for error in errors:
                # 숫자 주변의 잘못된 인식 수정
                processed = re.sub(f'(?<=[0-9]){re.escape(error)}(?=[0-9])', correct, processed)
                processed = re.sub(f'(?<=[0-9]){re.escape(error)}(?=\\s)', correct, processed)
                processed = re.sub(f'(?<=\\s){re.escape(error)}(?=[0-9])', correct, processed)
        
        # 2. 한글 자모 오류 수정
        for correct, errors in self.korean_patterns['korean_jamo_errors'].items():
            for error in errors:
                processed = processed.replace(error, correct)
        
        # 3. 띄어쓰기 개선
        # 조사 앞 불필요한 공백 제거
        josa_pattern = r'\s+([은는이가을를에서도만까지부터라고니까네요예요이에요])'
        processed = re.sub(josa_pattern, r'\1', processed)
        
        # 4. 괄호 및 특수문자 정리
        processed = re.sub(r'（', '(', processed)
        processed = re.sub(r'）', ')', processed)
        processed = re.sub(r'」', '"', processed)
        processed = re.sub(r'「', '"', processed)
        
        # 5. 연속된 공백 제거
        processed = re.sub(r'\s+', ' ', processed)
        
        return processed.strip()
    
    def compare_ocr_methods(self, image_path: str) -> Dict[str, any]:
        """
        다양한 OCR 방법의 성능 비교
        """
        # 이미지 로드
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"이미지를 로드할 수 없습니다: {image_path}")
        
        results = {}
        
        # 다양한 전처리 및 OCR 조합 테스트
        preprocessing_methods = {
            'original': lambda img: img,
            'grayscale': lambda img: cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img,
            'enhanced_low': lambda img: self.preprocess_image(img, 'low'),
            'enhanced_medium': lambda img: self.preprocess_image(img, 'medium'),
            'enhanced_high': lambda img: self.preprocess_image(img, 'high')
        }
        
        for prep_name, prep_func in preprocessing_methods.items():
            preprocessed = prep_func(image)
            
            # Tesseract 테스트
            try:
                tess_text = pytesseract.image_to_string(preprocessed, lang='kor+eng')
                results[f'{prep_name}_tesseract'] = {
                    'text': tess_text,
                    'length': len(tess_text),
                    'korean_ratio': self._calculate_korean_ratio(tess_text)
                }
            except:
                pass
            
            # EasyOCR 테스트
            try:
                if len(preprocessed.shape) == 2:  # 그레이스케일인 경우
                    easy_text = '\n'.join(self.reader.readtext(preprocessed, detail=0))
                    results[f'{prep_name}_easyocr'] = {
                        'text': easy_text,
                        'length': len(easy_text),
                        'korean_ratio': self._calculate_korean_ratio(easy_text)
                    }
            except:
                pass
        
        # 최적 방법 찾기
        best_method = max(results.items(), 
                         key=lambda x: x[1]['length'] * x[1]['korean_ratio'])
        
        return {
            'all_results': results,
            'best_method': best_method[0],
            'best_text': best_method[1]['text']
        }