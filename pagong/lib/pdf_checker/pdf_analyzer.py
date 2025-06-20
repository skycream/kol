"""
PDF 파일 분석 및 품질 평가
"""
import fitz  # PyMuPDF
from typing import Dict, List, Tuple, Optional
import numpy as np
from PIL import Image
import io
import cv2


class PDFAnalyzer:
    """PDF 파일의 품질과 특성을 분석"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
    
    def analyze_pdf_type(self) -> Dict[str, any]:
        """
        PDF 유형 분석 (스캔본 vs 텍스트 기반)
        """
        total_pages = len(self.doc)
        pages_with_text = 0
        pages_with_images = 0
        text_char_count = 0
        image_count = 0
        
        for page_num in range(total_pages):
            page = self.doc[page_num]
            
            # 텍스트 추출
            text = page.get_text()
            if text.strip():
                pages_with_text += 1
                text_char_count += len(text)
            
            # 이미지 확인
            image_list = page.get_images()
            if image_list:
                pages_with_images += 1
                image_count += len(image_list)
        
        # PDF 유형 판단
        is_scanned = pages_with_text == 0 or (pages_with_images == total_pages and text_char_count < 100)
        is_searchable = pages_with_text > 0 and text_char_count > 100
        is_mixed = pages_with_text > 0 and pages_with_images > 0
        
        return {
            "pdf_type": "scanned" if is_scanned else ("searchable" if is_searchable else "mixed"),
            "total_pages": total_pages,
            "pages_with_text": pages_with_text,
            "pages_with_images": pages_with_images,
            "total_text_characters": text_char_count,
            "total_images": image_count,
            "is_ocr_needed": is_scanned or (is_mixed and text_char_count < 500)
        }
    
    def analyze_image_quality(self, page_num: int = 0) -> Dict[str, float]:
        """
        PDF 내 이미지 품질 분석 (스캔 품질 평가)
        """
        page = self.doc[page_num]
        
        # 페이지를 이미지로 변환
        mat = fitz.Matrix(2, 2)  # 2x 확대
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
        
        # 품질 메트릭 계산
        
        # 1. 선명도 (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(laplacian_var / 100, 100)  # 정규화
        
        # 2. 대비 (Contrast)
        contrast = gray.std()
        contrast_score = min(contrast / 50, 100)  # 정규화
        
        # 3. 노이즈 레벨
        # 가우시안 필터 적용 후 차이 계산
        denoised = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = np.abs(gray.astype(np.float32) - denoised.astype(np.float32))
        noise_level = np.mean(noise)
        noise_score = max(100 - noise_level, 0)
        
        # 4. 기울어짐 감지 (Skew detection)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
        
        skew_angle = 0
        if lines is not None:
            angles = []
            for rho, theta in lines[:, 0]:
                angle = np.degrees(theta) - 90
                if -45 < angle < 45:
                    angles.append(angle)
            if angles:
                skew_angle = np.median(angles)
        
        skew_score = max(100 - abs(skew_angle) * 10, 0)
        
        # 5. 해상도 평가
        dpi = page.get_pixmap().xres
        resolution_score = min(dpi / 3, 100)  # 300 DPI를 100점 기준
        
        return {
            "sharpness_score": sharpness_score,
            "contrast_score": contrast_score,
            "noise_score": noise_score,
            "skew_score": skew_score,
            "skew_angle": skew_angle,
            "resolution_score": resolution_score,
            "dpi": dpi,
            "overall_quality_score": np.mean([
                sharpness_score, contrast_score, noise_score, 
                skew_score, resolution_score
            ])
        }
    
    def analyze_text_extraction_confidence(self) -> Dict[str, any]:
        """
        텍스트 추출 신뢰도 분석
        """
        confidence_scores = []
        problematic_pages = []
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            
            # 텍스트 블록 분석
            blocks = page.get_text("dict")
            
            page_confidence = 100  # 기본값
            issues = []
            
            for block in blocks["blocks"]:
                if block["type"] == 0:  # 텍스트 블록
                    for line in block["lines"]:
                        for span in line["spans"]:
                            # 폰트 크기 이상 감지
                            if span["size"] < 6 or span["size"] > 72:
                                page_confidence -= 5
                                issues.append("abnormal_font_size")
                            
                            # 특수 문자 비율 확인
                            text = span["text"]
                            if text:
                                special_char_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text)
                                if special_char_ratio > 0.3:
                                    page_confidence -= 10
                                    issues.append("high_special_char_ratio")
            
            confidence_scores.append(page_confidence)
            if page_confidence < 80:
                problematic_pages.append({
                    "page": page_num + 1,
                    "confidence": page_confidence,
                    "issues": list(set(issues))
                })
        
        return {
            "average_confidence": np.mean(confidence_scores),
            "min_confidence": min(confidence_scores),
            "max_confidence": max(confidence_scores),
            "problematic_pages": problematic_pages,
            "confidence_by_page": confidence_scores
        }
    
    def get_comprehensive_analysis(self) -> Dict[str, any]:
        """
        종합적인 PDF 분석 결과
        """
        pdf_type = self.analyze_pdf_type()
        
        # 이미지 품질은 첫 페이지만 샘플로 분석
        image_quality = None
        if pdf_type["pages_with_images"] > 0:
            image_quality = self.analyze_image_quality(0)
        
        text_confidence = self.analyze_text_extraction_confidence()
        
        # 전체 품질 점수 계산
        overall_score = text_confidence["average_confidence"]
        if image_quality:
            overall_score = (overall_score + image_quality["overall_quality_score"]) / 2
        
        return {
            "pdf_type_analysis": pdf_type,
            "image_quality_analysis": image_quality,
            "text_confidence_analysis": text_confidence,
            "overall_quality_score": overall_score,
            "recommendations": self._generate_recommendations(pdf_type, image_quality, text_confidence)
        }
    
    def _generate_recommendations(self, pdf_type: Dict, image_quality: Optional[Dict], 
                                 text_confidence: Dict) -> List[str]:
        """
        분석 결과를 바탕으로 개선 권장사항 생성
        """
        recommendations = []
        
        if pdf_type["is_ocr_needed"]:
            recommendations.append("OCR 처리가 필요한 스캔 문서입니다.")
        
        if image_quality:
            if image_quality["sharpness_score"] < 50:
                recommendations.append("이미지 선명도가 낮습니다. 고해상도로 다시 스캔하는 것을 권장합니다.")
            
            if image_quality["skew_angle"] > 2:
                recommendations.append(f"문서가 {image_quality['skew_angle']:.1f}도 기울어져 있습니다. 스큐 보정이 필요합니다.")
            
            if image_quality["dpi"] < 200:
                recommendations.append(f"해상도가 {image_quality['dpi']} DPI로 낮습니다. 300 DPI 이상을 권장합니다.")
        
        if text_confidence["average_confidence"] < 80:
            recommendations.append("텍스트 추출 신뢰도가 낮습니다. 문서 품질 개선이 필요합니다.")
        
        if not recommendations:
            recommendations.append("문서 품질이 양호합니다.")
        
        return recommendations
    
    def close(self):
        """문서 닫기"""
        self.doc.close()