"""
PDF 스캔본 판별기
단일 파일로 실행 가능한 PDF 스캔 문서 판별 클래스

사용법:
    checker = PDFChecker()
    is_scanned = checker.is_scanned("path/to/file.pdf")
"""

import fitz  # PyMuPDF
import os
import warnings
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

# MuPDF 경고 억제
warnings.filterwarnings("ignore")
fitz.TOOLS.mupdf_display_errors(False)


@dataclass
class PDFAnalysisResult:
    """PDF 분석 결과를 담는 데이터 클래스"""
    is_scanned: bool
    confidence: float
    scan_score: int
    reasons: List[str]
    pdf_type: str
    details: Dict


class PDFChecker:
    """PDF 파일이 스캔본인지 판별하는 클래스"""
    
    def __init__(self):
        """초기화"""
        # 스캐너 관련 키워드
        self.scanner_keywords = [
            'scan', 'scanner', 'scanning', 'scanned', 
            'ocr', 'image', 'capture', 'digitiz',
            # 주요 스캐너 브랜드
            'canon', 'epson', 'hp', 'xerox', 'ricoh', 'konica', 'brother',
            'fujitsu', 'sindoh', 'kyocera', 'sharp',
            # 스캔 소프트웨어
            'adobe scan', 'camscanner', 'scansnap', 'paperport',
            'abbyy', 'readiris', 'omnipage',
            # 한국어
            '스캔', '스캐너', '복사기'
        ]
        
        # 문서 생성 소프트웨어 키워드
        self.document_software_keywords = [
            # 오피스
            'microsoft', 'word', 'excel', 'powerpoint', 'office',
            'libreoffice', 'openoffice', 'pages', 'numbers',
            # PDF 생성기
            'acrobat', 'pdfcreator', 'cutepdf', 'primopdf',
            'ghostscript', 'wkhtmltopdf', 'chrome',
            # 한글 오피스
            'hancom', 'hwp', '한글', '한컴',
            # 기타
            'latex', 'tex', 'writer'
        ]
    
    def is_scanned(self, pdf_path: str) -> bool:
        """
        PDF가 스캔본인지 판별하는 메인 메서드
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            bool: 스캔본이면 True, 아니면 False
        """
        try:
            result = self.analyze(pdf_path)
            return result.is_scanned
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            return False
    
    def analyze(self, pdf_path: str) -> PDFAnalysisResult:
        """
        PDF 파일을 상세 분석
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            PDFAnalysisResult: 분석 결과
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        
        try:
            # 1. 메타데이터 분석
            metadata = doc.metadata
            producer_analysis = self._analyze_producer_creator(metadata)
            
            # 2. 페이지 분석
            page_analysis = self._analyze_pages(doc)
            
            # 3. 폰트 분석
            font_analysis = self._analyze_fonts(doc)
            
            # 4. 스캔 점수 계산
            scan_score, reasons, is_scanned = self._calculate_scan_score(
                producer_analysis, page_analysis, font_analysis
            )
            
            # 5. PDF 타입 결정
            pdf_type = self._determine_pdf_type(
                page_analysis, font_analysis, is_scanned
            )
            
            # 6. 신뢰도 계산
            confidence = min(scan_score / 100.0, 1.0)
            
            # 결과 생성
            result = PDFAnalysisResult(
                is_scanned=is_scanned,
                confidence=confidence,
                scan_score=scan_score,
                reasons=reasons,
                pdf_type=pdf_type,
                details={
                    'producer': producer_analysis.get('producer', ''),
                    'creator': producer_analysis.get('creator', ''),
                    'total_pages': page_analysis['total_pages'],
                    'text_pages': page_analysis['text_pages'],
                    'image_pages': page_analysis['image_only_pages'],
                    'has_fonts': font_analysis['has_fonts'],
                    'font_count': font_analysis['unique_font_count']
                }
            )
            
            return result
            
        finally:
            doc.close()
    
    def _analyze_producer_creator(self, metadata: Dict) -> Dict:
        """Producer/Creator 분석"""
        producer = metadata.get('producer', '').lower()
        creator = metadata.get('creator', '').lower()
        
        analysis = {
            'producer': metadata.get('producer', ''),
            'creator': metadata.get('creator', ''),
            'has_scanner_keywords': False,
            'has_document_keywords': False,
            'producer_type': 'unknown'
        }
        
        # 스캐너 키워드 검색
        for keyword in self.scanner_keywords:
            if keyword in producer or keyword in creator:
                analysis['has_scanner_keywords'] = True
                break
        
        # 문서 소프트웨어 키워드 검색
        for keyword in self.document_software_keywords:
            if keyword in producer or keyword in creator:
                analysis['has_document_keywords'] = True
                break
        
        # Producer 유형 판단
        if analysis['has_scanner_keywords']:
            analysis['producer_type'] = 'scanner'
        elif analysis['has_document_keywords']:
            analysis['producer_type'] = 'document_software'
        elif producer or creator:
            analysis['producer_type'] = 'other'
        
        return analysis
    
    def _analyze_pages(self, doc: fitz.Document) -> Dict:
        """페이지 분석"""
        total_pages = len(doc)
        text_pages = 0
        image_only_pages = 0
        total_images = 0
        total_text_length = 0
        
        for page in doc:
            # 텍스트 추출
            text = page.get_text()
            text_length = len(text.strip())
            
            # 이미지 정보
            images = page.get_images()
            
            if text_length > 10:
                text_pages += 1
            
            if images and text_length < 10:
                image_only_pages += 1
            
            total_images += len(images)
            total_text_length += text_length
        
        return {
            'total_pages': total_pages,
            'text_pages': text_pages,
            'image_only_pages': image_only_pages,
            'total_images': total_images,
            'avg_text_per_page': total_text_length / total_pages if total_pages > 0 else 0,
            'image_only_ratio': image_only_pages / total_pages if total_pages > 0 else 0
        }
    
    def _analyze_fonts(self, doc: fitz.Document) -> Dict:
        """폰트 분석"""
        all_fonts = []
        
        for page in doc:
            fonts = page.get_fonts()
            for font in fonts:
                if len(font) >= 4:
                    font_name = font[3]
                    all_fonts.append(font_name)
        
        return {
            'total_font_count': len(all_fonts),
            'unique_font_count': len(set(all_fonts)),
            'has_fonts': len(all_fonts) > 0,
            'font_names': list(set(all_fonts))[:5]  # 처음 5개만
        }
    
    def _calculate_scan_score(self, producer_analysis: Dict, 
                             page_analysis: Dict, font_analysis: Dict) -> Tuple[int, List[str], bool]:
        """스캔 점수 계산"""
        score = 0
        reasons = []
        is_scanned = False
        
        # 핵심 스캔 지표 - 하나라도 만족하면 스캔본
        
        # 1. Producer가 스캐너 장치면 즉시 100점
        if producer_analysis['producer_type'] == 'scanner':
            score = 100
            is_scanned = True
            reasons.append(f"스캐너 장치로 생성됨: {producer_analysis['producer']}")
        
        # 2. Creator가 스캔 소프트웨어면 즉시 100점
        elif producer_analysis['has_scanner_keywords'] and producer_analysis.get('creator'):
            score = 100
            is_scanned = True
            reasons.append(f"스캔 소프트웨어로 생성됨: {producer_analysis['creator']}")
        
        # 3. 폰트 정보 없음 + 이미지 있음 = 95점
        elif not font_analysis['has_fonts'] and page_analysis.get('total_images', 0) > 0:
            score = 100
            is_scanned = True
            reasons.append("폰트 정보 없음 + 이미지 존재 (스캔 문서)")
        
        # 4. 모든 페이지가 이미지로만 구성 = 95점
        elif page_analysis.get('image_only_ratio', 0) == 1.0:
            score = 100
            is_scanned = True
            reasons.append("모든 페이지가 이미지로만 구성")
        
        # 5. 텍스트가 거의 없음 (페이지당 10자 미만) + 이미지 있음 = 90점
        elif page_analysis.get('avg_text_per_page', 0) < 10 and page_analysis.get('total_images', 0) > 0:
            score = 100
            is_scanned = True
            reasons.append(f"텍스트 거의 없음 ({page_analysis.get('avg_text_per_page', 0):.0f}자/페이지)")
        
        # 스캔본이 아닌 경우
        else:
            if producer_analysis['producer_type'] == 'document_software':
                score = 0
                reasons.append(f"문서 편집 소프트웨어로 생성")
            elif font_analysis['unique_font_count'] > 0:
                score = 0
                reasons.append(f"폰트 정보 포함 ({font_analysis['unique_font_count']}개)")
            else:
                score = 0
                reasons.append("명확한 스캔 지표 없음")
        
        return score, reasons, is_scanned
    
    def _determine_pdf_type(self, page_analysis: Dict, font_analysis: Dict, is_scanned: bool) -> str:
        """PDF 타입 결정"""
        if is_scanned:
            if page_analysis['text_pages'] == 0:
                return "순수 스캔본 (Pure Scanned)"
            else:
                return "OCR 처리된 스캔본 (OCR-processed Scan)"
        else:
            if page_analysis['image_only_pages'] > 0:
                return "혼합형 (Mixed)"
            else:
                return "디지털 원본 (Digital Native)"


def main():
    """테스트 메인 함수"""
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python pdf_checker.py [PDF파일경로]")
        print("\n예제:")
        print("  python pdf_checker.py document.pdf")
        return
    
    pdf_path = sys.argv[1]
    checker = PDFChecker()
    
    # 간단한 True/False 결과
    is_scanned = checker.is_scanned(pdf_path)
    print(f"\n스캔본 여부: {is_scanned}")
    
    # 상세 분석 결과
    result = checker.analyze(pdf_path)
    print(f"\nPDF 타입: {result.pdf_type}")
    print(f"신뢰도: {result.confidence:.0%}")
    print(f"스캔 점수: {result.scan_score}/100")
    print("\n판단 근거:")
    for reason in result.reasons:
        print(f"  - {reason}")
    
    print("\n상세 정보:")
    for key, value in result.details.items():
        print(f"  - {key}: {value}")


if __name__ == "__main__":
    main()