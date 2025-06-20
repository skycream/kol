"""
PDF OCR 필요성 판단 클래스
PDF 파일이 텍스트 추출 가능한지, OCR이 필요한지 정확히 판단
"""
import fitz  # PyMuPDF
import os
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
import re
from datetime import datetime
import warnings

# MuPDF 경고 및 에러 메시지 억제
warnings.filterwarnings("ignore")
fitz.TOOLS.mupdf_display_errors(False)


@dataclass
class PDFAnalysisResult:
    """PDF 분석 결과를 담는 데이터 클래스"""
    needs_ocr: bool
    pdf_type: str  # 'text', 'scanned', 'mixed', 'form', 'secured'
    confidence: float  # 판단 신뢰도 (0.0 ~ 1.0)
    total_pages: int
    text_pages: int
    image_pages: int
    metadata: Dict
    reasons: List[str]
    recommendations: List[str]


class PDFOCRDetector:
    """PDF 파일의 OCR 필요성을 정확히 판단하는 클래스"""
    
    def __init__(self):
        self.min_text_length = 10  # 페이지당 최소 텍스트 길이
        self.min_text_ratio = 0.1  # 이미지 대비 텍스트 비율
        
    def analyze(self, pdf_path: str) -> PDFAnalysisResult:
        """PDF 파일을 분석하여 OCR 필요성 판단"""
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        
        # 1. 메타데이터 분석
        metadata = self._analyze_metadata(doc)
        
        # 2. 페이지별 분석
        page_analysis = self._analyze_pages(doc)
        
        # 3. 폰트 정보 분석
        font_info = self._analyze_fonts(doc)
        
        # 4. 종합 판단
        result = self._make_decision(metadata, page_analysis, font_info, len(doc))
        
        doc.close()
        
        return result
    
    def _analyze_metadata(self, doc: fitz.Document) -> Dict:
        """PDF 메타데이터 분석"""
        metadata = doc.metadata
        
        analysis = {
            'producer': metadata.get('producer', ''),
            'creator': metadata.get('creator', ''),
            'creation_date': metadata.get('creationDate', ''),
            'mod_date': metadata.get('modDate', ''),
            'format': metadata.get('format', ''),
            'encryption': metadata.get('encryption', ''),
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
        }
        
        # 스캔 관련 키워드 검색
        scan_keywords = ['scan', 'scanner', 'scanning', 'scanned', 'ocr', 'image']
        text_keywords = ['word', 'excel', 'powerpoint', 'libreoffice', 'pages', 'latex', 'tex']
        
        all_metadata_text = ' '.join(str(v).lower() for v in analysis.values() if v)
        
        analysis['has_scan_keywords'] = any(keyword in all_metadata_text for keyword in scan_keywords)
        analysis['has_text_keywords'] = any(keyword in all_metadata_text for keyword in text_keywords)
        analysis['is_tagged'] = doc.is_pdf  # Tagged PDF는 보통 접근성을 위한 텍스트 구조 포함
        
        return analysis
    
    def _analyze_pages(self, doc: fitz.Document) -> Dict:
        """각 페이지의 텍스트와 이미지 분석"""
        
        total_pages = len(doc)
        text_pages = 0
        image_pages = 0
        pure_text_pages = 0
        pure_image_pages = 0
        mixed_pages = 0
        
        page_details = []
        total_text_length = 0
        total_images = 0
        
        for page_num in range(total_pages):
            page = doc[page_num]
            
            # 텍스트 추출
            text = page.get_text()
            text_length = len(text.strip())
            
            # 이미지 정보
            image_list = page.get_images()
            image_count = len(image_list)
            
            # 텍스트 블록 분석
            blocks = page.get_text("dict")
            text_blocks = [b for b in blocks["blocks"] if b["type"] == 0]  # type 0 = text
            
            # 폰트 크기 분석 (렌더링된 텍스트인지 확인)
            font_sizes = []
            for block in text_blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if "size" in span:
                            font_sizes.append(span["size"])
            
            has_meaningful_text = text_length > self.min_text_length
            has_images = image_count > 0
            
            # 페이지 유형 판단
            if has_meaningful_text and not has_images:
                pure_text_pages += 1
                text_pages += 1
            elif has_images and not has_meaningful_text:
                pure_image_pages += 1
                image_pages += 1
            elif has_meaningful_text and has_images:
                mixed_pages += 1
                text_pages += 1
                image_pages += 1
            
            # 이미지가 페이지 전체를 차지하는지 확인
            page_rect = page.rect
            page_area = page_rect.width * page_rect.height
            
            image_coverage = 0.0
            for img in image_list:
                try:
                    # 이미지 위치 정보 가져오기
                    img_rect = page.get_image_bbox(img)
                    if img_rect:
                        img_area = img_rect.width * img_rect.height
                        image_coverage = max(image_coverage, img_area / page_area)
                except:
                    pass
            
            page_details.append({
                'page_num': page_num + 1,
                'text_length': text_length,
                'image_count': image_count,
                'has_text': has_meaningful_text,
                'has_images': has_images,
                'font_sizes': font_sizes,
                'text_block_count': len(text_blocks),
                'image_coverage': image_coverage
            })
            
            total_text_length += text_length
            total_images += image_count
        
        return {
            'total_pages': total_pages,
            'text_pages': text_pages,
            'image_pages': image_pages,
            'pure_text_pages': pure_text_pages,
            'pure_image_pages': pure_image_pages,
            'mixed_pages': mixed_pages,
            'total_text_length': total_text_length,
            'total_images': total_images,
            'avg_text_per_page': total_text_length / total_pages if total_pages > 0 else 0,
            'page_details': page_details
        }
    
    def _analyze_fonts(self, doc: fitz.Document) -> Dict:
        """폰트 정보 분석 - 임베디드 폰트는 보통 실제 텍스트를 의미"""
        
        font_list = []
        try:
            # 각 페이지의 폰트 정보 수집
            for page_num in range(len(doc)):
                page = doc[page_num]
                fonts = page.get_fonts()
                font_list.extend(fonts)
        except:
            pass
        
        # 고유 폰트 이름 추출
        unique_fonts = set()
        embedded_fonts = 0
        system_fonts = 0
        
        for font in font_list:
            if len(font) >= 4:
                font_name = font[3]  # 폰트 이름
                unique_fonts.add(font_name)
                
                # 임베디드 폰트 확인 (보통 '+' 기호로 시작)
                if font_name.startswith('+'):
                    embedded_fonts += 1
                else:
                    system_fonts += 1
        
        return {
            'total_fonts': len(font_list),
            'unique_fonts': len(unique_fonts),
            'embedded_fonts': embedded_fonts,
            'system_fonts': system_fonts,
            'font_names': list(unique_fonts)[:10]  # 처음 10개만
        }
    
    def _make_decision(self, metadata: Dict, page_analysis: Dict, 
                      font_info: Dict, total_pages: int) -> PDFAnalysisResult:
        """종합적인 OCR 필요성 판단"""
        
        needs_ocr = False
        pdf_type = "unknown"
        confidence = 0.0
        reasons = []
        recommendations = []
        
        # 스캔본 판별 핵심 기준 (하나라도 만족하면 스캔본)
        scan_indicators = []
        
        # 1. Producer가 스캐너 장치인지 확인
        scanner_brands = ['sindoh', 'canon', 'hp', 'xerox', 'epson', 'ricoh', 
                         'konica', 'brother', 'fujitsu', 'kyocera', 'sharp']
        producer_lower = metadata.get('producer', '').lower()
        
        for brand in scanner_brands:
            if brand in producer_lower:
                scan_indicators.append(f"스캐너 장치로 생성됨: {metadata['producer']}")
                needs_ocr = True
                pdf_type = "scanned"
                break
        
        # 2. Creator가 스캔 소프트웨어인지 확인
        scan_software = ['adobe scan', 'camscanner', 'scansnap', 'paperport',
                        'abbyy', 'readiris', 'omnipage', 'pdf scanner']
        creator_lower = metadata.get('creator', '').lower()
        
        for software in scan_software:
            if software in creator_lower:
                scan_indicators.append(f"스캔 소프트웨어로 생성됨: {metadata['creator']}")
                needs_ocr = True
                pdf_type = "scanned"
                break
        
        # 3. 폰트 정보가 없는지 확인
        if font_info['total_fonts'] == 0 and page_analysis.get('total_images', 0) > 0:
            scan_indicators.append("폰트 정보 없음 + 이미지 존재 (스캔 문서)")
            needs_ocr = True
            pdf_type = "scanned"
        
        # 4. 페이지가 100% 이미지인지 확인
        if page_analysis['pure_image_pages'] == total_pages and total_pages > 0:
            scan_indicators.append("모든 페이지가 이미지로만 구성")
            needs_ocr = True
            pdf_type = "scanned"
        
        # 5. 텍스트가 거의 없는지 확인 (페이지당 10자 미만)
        if page_analysis['avg_text_per_page'] < 10 and page_analysis.get('total_images', 0) > 0:
            scan_indicators.append(f"텍스트 거의 없음 ({page_analysis['avg_text_per_page']:.0f}자/페이지)")
            needs_ocr = True
            pdf_type = "scanned"
        
        # 스캔본이 아닌 경우 추가 판단
        if not needs_ocr:
            # 텍스트 기반 PDF 확인
            if page_analysis['pure_text_pages'] == total_pages:
                pdf_type = "text"
                reasons.append("모든 페이지가 텍스트로만 구성")
                confidence = 0.9
            elif page_analysis['avg_text_per_page'] > 500:
                pdf_type = "text"
                reasons.append(f"페이지당 충분한 텍스트 포함 ({page_analysis['avg_text_per_page']:.0f}자)")
                confidence = 0.8
            elif page_analysis['text_pages'] > 0 and page_analysis['image_pages'] > 0:
                pdf_type = "mixed"
                reasons.append("텍스트와 이미지가 혼합된 문서")
                confidence = 0.7
            else:
                pdf_type = "text"
                confidence = 0.5
        else:
            # 스캔본인 경우
            reasons = scan_indicators
            confidence = 0.9 if len(scan_indicators) >= 2 else 0.8
        
        # 권장사항 생성
        if needs_ocr:
            recommendations.append("OCR 처리가 필요합니다")
            if page_analysis['total_images'] > 0:
                recommendations.append("고품질 OCR을 위해 300 DPI 이상 권장")
            if 'scanner' in metadata.get('producer', '').lower():
                recommendations.append("스캐너 설정에서 텍스트 레이어 옵션 활성화 검토")
        else:
            recommendations.append("텍스트 직접 추출 가능")
            if pdf_type == "mixed":
                recommendations.append("일부 이미지는 별도 OCR 처리 필요할 수 있음")
        
        return PDFAnalysisResult(
            needs_ocr=needs_ocr,
            pdf_type=pdf_type,
            confidence=confidence,
            total_pages=total_pages,
            text_pages=page_analysis['text_pages'],
            image_pages=page_analysis['image_pages'],
            metadata=metadata,
            reasons=reasons,
            recommendations=recommendations
        )
    
    def quick_check(self, pdf_path: str) -> bool:
        """빠른 OCR 필요성 체크 (True/False만 반환)"""
        try:
            result = self.analyze(pdf_path)
            return result.needs_ocr
        except:
            return True  # 오류 시 OCR 필요로 가정


def main():
    """테스트 및 사용 예시"""
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python if_ocr.py [PDF파일경로]")
        print("\n예시:")
        print("  python if_ocr.py test.pdf")
        return
    
    pdf_path = sys.argv[1]
    
    # OCR 필요성 검사
    detector = PDFOCRDetector()
    
    try:
        # 상세 분석
        result = detector.analyze(pdf_path)
        
        print(f"\n📄 PDF 분석 결과: {os.path.basename(pdf_path)}")
        print("=" * 60)
        
        # 핵심 판단
        ocr_status = "⭕ 필요" if result.needs_ocr else "❌ 불필요"
        print(f"🔍 OCR 필요성: {ocr_status}")
        print(f"📊 PDF 유형: {result.pdf_type}")
        print(f"🎯 판단 신뢰도: {result.confidence:.0%}")
        
        # 페이지 정보
        print(f"\n📄 페이지 정보:")
        print(f"  - 전체: {result.total_pages}페이지")
        print(f"  - 텍스트 포함: {result.text_pages}페이지")
        print(f"  - 이미지 포함: {result.image_pages}페이지")
        
        # 판단 근거
        print(f"\n💭 판단 근거:")
        for reason in result.reasons:
            print(f"  • {reason}")
        
        # 메타데이터 일부
        print(f"\n📋 메타데이터:")
        if result.metadata.get('producer'):
            print(f"  - 생성 프로그램: {result.metadata['producer']}")
        if result.metadata.get('creator'):
            print(f"  - 작성 프로그램: {result.metadata['creator']}")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        for rec in result.recommendations:
            print(f"  • {rec}")
        
        # 빠른 체크 예시
        print(f"\n⚡ 빠른 체크 결과: OCR {'필요' if detector.quick_check(pdf_path) else '불필요'}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()