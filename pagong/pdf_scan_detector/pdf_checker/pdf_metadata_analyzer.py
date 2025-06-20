"""
PDF 메타데이터 상세 분석 도구
스캔본 구별을 위한 메타데이터 패턴 분석
"""
import fitz
import os
import sys
from datetime import datetime
from typing import Dict, List
import json
from pathlib import Path

# MuPDF 에러 억제
fitz.TOOLS.mupdf_display_errors(False)


class PDFMetadataAnalyzer:
    """PDF 메타데이터를 상세히 분석하는 클래스"""
    
    def __init__(self):
        # 스캐너 관련 키워드
        self.scanner_keywords = [
            'scan', 'scanner', 'scanning', 'scanned', 
            'ocr', 'image', 'capture', 'digitiz',
            # 주요 스캐너 브랜드
            'canon', 'epson', 'hp', 'xerox', 'ricoh', 'konica', 'brother',
            'fujitsu', 'sindoh', 'kyocera',
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
        
    def analyze_metadata(self, pdf_path: str) -> Dict:
        """PDF 메타데이터 상세 분석"""
        
        doc = fitz.open(pdf_path)
        
        # 1. 기본 메타데이터
        metadata = doc.metadata
        
        # 2. 확장 메타데이터
        extended_info = {
            'filename': os.path.basename(pdf_path),
            'file_size': os.path.getsize(pdf_path),
            'page_count': len(doc),
            'is_encrypted': doc.is_encrypted,
            'is_form_pdf': doc.is_form_pdf,
            'is_reflowable': doc.is_reflowable,
            'is_repaired': doc.is_repaired,
            'permissions': doc.permissions,
        }
        
        # 3. 생성/수정 날짜 파싱
        dates = self._parse_dates(metadata)
        
        # 4. Producer/Creator 분석
        producer_analysis = self._analyze_producer_creator(metadata)
        
        # 5. 페이지별 특성 분석
        page_analysis = self._analyze_pages(doc)
        
        # 6. 폰트 분석
        font_analysis = self._analyze_fonts(doc)
        
        # 7. 스캔 판별 점수
        scan_score = self._calculate_scan_score(
            metadata, producer_analysis, page_analysis, font_analysis
        )
        
        doc.close()
        
        return {
            'basic_metadata': metadata,
            'extended_info': extended_info,
            'dates': dates,
            'producer_analysis': producer_analysis,
            'page_analysis': page_analysis,
            'font_analysis': font_analysis,
            'scan_score': scan_score,
            'is_likely_scanned': scan_score['is_likely_scanned']
        }
    
    def _parse_dates(self, metadata: Dict) -> Dict:
        """날짜 정보 파싱"""
        dates = {}
        
        for key in ['creationDate', 'modDate']:
            if key in metadata and metadata[key]:
                try:
                    # PDF 날짜 형식: D:20231225123456+09'00'
                    date_str = metadata[key]
                    if date_str.startswith('D:'):
                        date_str = date_str[2:]
                    # 간단한 파싱 (년월일시분초만)
                    year = date_str[0:4]
                    month = date_str[4:6]
                    day = date_str[6:8]
                    hour = date_str[8:10] if len(date_str) > 8 else '00'
                    minute = date_str[10:12] if len(date_str) > 10 else '00'
                    
                    dates[key] = f"{year}-{month}-{day} {hour}:{minute}"
                except:
                    dates[key] = metadata[key]
        
        return dates
    
    def _analyze_producer_creator(self, metadata: Dict) -> Dict:
        """Producer/Creator 분석"""
        producer = metadata.get('producer', '').lower()
        creator = metadata.get('creator', '').lower()
        
        analysis = {
            'producer': metadata.get('producer', ''),
            'creator': metadata.get('creator', ''),
            'has_scanner_keywords': False,
            'has_document_keywords': False,
            'scanner_matches': [],
            'document_matches': [],
            'producer_type': 'unknown'
        }
        
        # 스캐너 키워드 검색
        for keyword in self.scanner_keywords:
            if keyword in producer or keyword in creator:
                analysis['has_scanner_keywords'] = True
                analysis['scanner_matches'].append(keyword)
        
        # 문서 소프트웨어 키워드 검색
        for keyword in self.document_software_keywords:
            if keyword in producer or keyword in creator:
                analysis['has_document_keywords'] = True
                analysis['document_matches'].append(keyword)
        
        # Producer 유형 판단
        if analysis['has_scanner_keywords']:
            analysis['producer_type'] = 'scanner'
        elif analysis['has_document_keywords']:
            analysis['producer_type'] = 'document_software'
        elif producer or creator:
            analysis['producer_type'] = 'other'
        
        return analysis
    
    def _analyze_pages(self, doc: fitz.Document) -> Dict:
        """페이지 특성 분석"""
        total_text_length = 0
        pages_with_text = 0
        pages_with_images = 0
        pages_with_only_images = 0
        image_coverage_ratios = []
        
        for page in doc:
            text = page.get_text()
            text_length = len(text.strip())
            images = page.get_images()
            
            if text_length > 10:
                pages_with_text += 1
            
            if images:
                pages_with_images += 1
                
            if images and text_length < 10:
                pages_with_only_images += 1
            
            # 이미지 커버리지 계산
            if images:
                page_area = page.rect.width * page.rect.height
                total_image_area = 0
                
                for img in images:
                    try:
                        bbox = page.get_image_bbox(img)
                        if bbox:
                            img_area = bbox.width * bbox.height
                            total_image_area += img_area
                    except:
                        pass
                
                if page_area > 0:
                    coverage = total_image_area / page_area
                    image_coverage_ratios.append(coverage)
            
            total_text_length += text_length
        
        return {
            'total_pages': len(doc),
            'pages_with_text': pages_with_text,
            'pages_with_images': pages_with_images,
            'pages_with_only_images': pages_with_only_images,
            'avg_text_per_page': total_text_length / len(doc) if len(doc) > 0 else 0,
            'text_page_ratio': pages_with_text / len(doc) if len(doc) > 0 else 0,
            'image_only_ratio': pages_with_only_images / len(doc) if len(doc) > 0 else 0,
            'avg_image_coverage': sum(image_coverage_ratios) / len(image_coverage_ratios) if image_coverage_ratios else 0
        }
    
    def _analyze_fonts(self, doc: fitz.Document) -> Dict:
        """폰트 정보 분석"""
        all_fonts = []
        embedded_fonts = set()
        system_fonts = set()
        
        for page in doc:
            fonts = page.get_fonts()
            for font in fonts:
                if len(font) >= 4:
                    font_name = font[3]
                    all_fonts.append(font_name)
                    
                    if font_name.startswith('+'):
                        embedded_fonts.add(font_name)
                    else:
                        system_fonts.add(font_name)
        
        return {
            'total_font_count': len(all_fonts),
            'unique_font_count': len(set(all_fonts)),
            'embedded_font_count': len(embedded_fonts),
            'system_font_count': len(system_fonts),
            'has_fonts': len(all_fonts) > 0,
            'font_names': list(set(all_fonts))[:10]  # 처음 10개만
        }
    
    def _calculate_scan_score(self, metadata: Dict, producer_analysis: Dict, 
                            page_analysis: Dict, font_analysis: Dict) -> Dict:
        """스캔 문서 판별 점수 계산 (0-100)"""
        score = 0
        reasons = []
        is_scanned = False
        
        # 핵심 스캔 지표 - 하나라도 만족하면 높은 점수
        
        # 1. Producer가 스캐너 장치면 즉시 100점
        if producer_analysis['producer_type'] == 'scanner':
            score = 100
            is_scanned = True
            reasons.append(f"스캐너 장치로 생성됨: {producer_analysis['producer']}")
        
        # 2. Creator가 스캔 소프트웨어면 즉시 100점
        elif producer_analysis['has_scanner_keywords'] and 'creator' in producer_analysis:
            score = 100
            is_scanned = True
            reasons.append(f"스캔 소프트웨어로 생성됨: {producer_analysis['creator']}")
        
        # 3. 폰트 정보 없음 + 이미지 있음 = 95점
        elif not font_analysis['has_fonts'] and page_analysis.get('total_images', 0) > 0:
            score = 95
            is_scanned = True
            reasons.append("폰트 정보 없음 + 이미지 존재 (스캔 문서)")
        
        # 4. 모든 페이지가 이미지로만 구성 = 95점
        elif page_analysis.get('image_only_ratio', 0) == 1.0:
            score = 95
            is_scanned = True
            reasons.append("모든 페이지가 이미지로만 구성")
        
        # 5. 텍스트가 거의 없음 (페이지당 10자 미만) + 이미지 있음 = 90점
        elif page_analysis.get('avg_text_per_page', 0) < 10 and page_analysis.get('total_images', 0) > 0:
            score = 90
            is_scanned = True
            reasons.append(f"텍스트 거의 없음 ({page_analysis.get('avg_text_per_page', 0):.0f}자/페이지)")
        
        # 스캔본이 아닌 경우 추가 분석
        if not is_scanned:
            # 문서 소프트웨어로 생성된 경우
            if producer_analysis['producer_type'] == 'document_software':
                score = 5
                reasons.append(f"문서 편집 소프트웨어로 생성: {producer_analysis['document_matches']}")
            
            # 충분한 텍스트가 있는 경우
            elif page_analysis['avg_text_per_page'] > 500:
                score = 5
                reasons.append(f"페이지당 충분한 텍스트 ({page_analysis['avg_text_per_page']:.0f}자)")
            
            # 폰트 정보가 풍부한 경우
            elif font_analysis['embedded_font_count'] > 0:
                score = 10
                reasons.append(f"임베디드 폰트 {font_analysis['embedded_font_count']}개 포함")
            
            # 기본값
            else:
                score = 20
                reasons.append("명확한 스캔 지표 없음")
        
        return {
            'total_score': score,
            'reasons': reasons,
            'is_likely_scanned': score >= 70,
            'confidence': 'high' if score >= 90 else 'medium' if score >= 70 else 'low'
        }
    
    def print_analysis(self, analysis: Dict):
        """분석 결과 출력"""
        print("\n" + "="*80)
        print("📋 PDF 메타데이터 상세 분석")
        print("="*80)
        
        # 기본 메타데이터
        print("\n📌 기본 메타데이터:")
        for key, value in analysis['basic_metadata'].items():
            if value:
                print(f"  - {key}: {value}")
        
        # Producer/Creator 분석
        print(f"\n🔍 Producer/Creator 분석:")
        prod = analysis['producer_analysis']
        print(f"  - Producer: {prod['producer'] or '없음'}")
        print(f"  - Creator: {prod['creator'] or '없음'}")
        print(f"  - 유형: {prod['producer_type']}")
        if prod['scanner_matches']:
            print(f"  - 스캐너 키워드: {', '.join(prod['scanner_matches'])}")
        if prod['document_matches']:
            print(f"  - 문서 SW 키워드: {', '.join(prod['document_matches'])}")
        
        # 페이지 분석
        print(f"\n📄 페이지 분석:")
        page = analysis['page_analysis']
        print(f"  - 총 페이지: {page['total_pages']}")
        print(f"  - 텍스트 있는 페이지: {page['pages_with_text']} ({page['text_page_ratio']:.0%})")
        print(f"  - 이미지만 있는 페이지: {page['pages_with_only_images']} ({page['image_only_ratio']:.0%})")
        print(f"  - 평균 텍스트/페이지: {page['avg_text_per_page']:.0f}자")
        print(f"  - 평균 이미지 커버리지: {page['avg_image_coverage']:.0%}")
        
        # 폰트 분석
        print(f"\n🔤 폰트 분석:")
        font = analysis['font_analysis']
        print(f"  - 폰트 존재: {'예' if font['has_fonts'] else '아니오'}")
        if font['has_fonts']:
            print(f"  - 고유 폰트 수: {font['unique_font_count']}")
            print(f"  - 임베디드 폰트: {font['embedded_font_count']}")
            print(f"  - 시스템 폰트: {font['system_font_count']}")
        
        # 스캔 판별 결과
        print(f"\n🎯 스캔 문서 판별:")
        scan = analysis['scan_score']
        print(f"  - 스캔 점수: {scan['total_score']}/100")
        print(f"  - 판정: {'스캔 문서' if analysis['is_likely_scanned'] else '디지털 문서'}")
        print(f"  - 판별 근거:")
        for reason in scan['reasons']:
            print(f"    • {reason}")


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python pdf_metadata_analyzer.py [PDF파일]")
        return
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"파일을 찾을 수 없습니다: {pdf_path}")
        return
    
    analyzer = PDFMetadataAnalyzer()
    
    try:
        # 분석 실행
        analysis = analyzer.analyze_metadata(pdf_path)
        
        # 결과 출력
        analyzer.print_analysis(analysis)
        
        # JSON으로 저장 옵션
        if len(sys.argv) > 2 and sys.argv[2] == '--save':
            output_file = Path(pdf_path).stem + '_metadata.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n💾 분석 결과가 '{output_file}'에 저장되었습니다.")
            
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")


if __name__ == "__main__":
    main()