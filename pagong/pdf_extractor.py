"""
PDF 이미지/텍스트 추출기
PDF 파일에서 이미지와 텍스트를 추출하여 data/[ID]/img와 data/[ID]/text 폴더에 저장
텍스트가 없는 스캔 문서의 경우 data/[ID]/scan 폴더도 생성하여 이미지 복사

파일명 형식: [ID];[정보1];[정보2].pdf
예: 12345;회사명;문서종류.pdf -> data/12345/ 폴더에 저장

폴더 구조:
- data/[ID]/img/   - 추출된 이미지
- data/[ID]/text/  - 추출된 텍스트
- data/[ID]/scan/  - 텍스트가 없는 경우 img 폴더의 이미지 복사본

사용법:
    extractor = PDFExtractor()
    extractor.extract("12345;회사명;문서종류.pdf")  # data/12345/에 저장
    extractor.extract("document.pdf")  # data/document/에 저장
    
    # 또는 커스텀 출력 디렉토리 지정
    extractor.extract("document.pdf", output_dir="custom_output")
"""

import fitz  # PyMuPDF
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from PIL import Image
import io
from datetime import datetime
from pdf_checker import PDFChecker  # PDF 스캔본 판별기 import


class PDFExtractor:
    """PDF에서 이미지와 텍스트를 추출하는 클래스"""
    
    def __init__(self):
        """초기화"""
        self.supported_image_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']
        self.pdf_checker = PDFChecker()  # PDF 스캔본 판별기 인스턴스 생성
        
    def extract(self, pdf_path: str, output_dir: Optional[str] = None) -> Dict:
        """
        PDF에서 이미지와 텍스트를 추출하여 저장
        
        Args:
            pdf_path: PDF 파일 경로
            output_dir: 출력 디렉토리 (기본값: data/[ID]/)
            
        Returns:
            Dict: 추출 결과 정보
        """
        # 파일 존재 확인
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        
        # 출력 디렉토리 설정
        if output_dir is None:
            # 파일명에서 ID 추출 (세미콜론 앞의 숫자)
            pdf_name = Path(pdf_path).stem
            
            # ID 추출 시도
            if ';' in pdf_name:
                # 첫 번째 세미콜론 앞의 내용을 ID로 사용
                doc_id = pdf_name.split(';')[0].strip()
            else:
                # 세미콜론이 없으면 전체 파일명을 ID로 사용
                doc_id = pdf_name
            
            # data/[ID] 구조로 출력 디렉토리 설정
            output_dir = os.path.join("data", doc_id)
        
        # img와 text 폴더 생성
        img_dir = os.path.join(output_dir, "img")
        text_dir = os.path.join(output_dir, "text")
        scan_dir = os.path.join(output_dir, "scan")  # scan 폴더 추가
        
        # 디렉토리 생성 (exist_ok=True로 기존 디렉토리 유지)
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(text_dir, exist_ok=True)
        # scan 폴더는 나중에 필요시 생성
        
        # PDF 열기
        doc = fitz.open(pdf_path)
        
        # 결과 저장용 변수
        extracted_images = []
        extracted_texts = []
        total_text = ""
        
        try:
            print(f"PDF 처리 시작: {pdf_path}")
            print(f"출력 디렉토리: {output_dir}")
            print(f"총 페이지 수: {len(doc)}")
            
            # PDF 스캔본 여부 먼저 확인
            is_scanned = self.pdf_checker.is_scanned(pdf_path)
            if is_scanned:
                print("📋 스캔본으로 판별됨 - 전체 페이지 이미지만 추출합니다.")
            
            # 페이지별 처리
            for page_num, page in enumerate(doc, start=1):
                print(f"\n페이지 {page_num}/{len(doc)} 처리 중...")
                
                # 1. 텍스트 추출
                page_text = self._extract_text_from_page(page, page_num, text_dir)
                if page_text:
                    extracted_texts.append({
                        'page': page_num,
                        'text_file': f"page_{page_num:03d}.txt",
                        'char_count': len(page_text)
                    })
                    total_text += f"\n\n--- 페이지 {page_num} ---\n{page_text}"
                
                # 2. 이미지 추출 (스캔본 여부에 따라 다르게 처리)
                page_images = self._extract_images_from_page(page, page_num, img_dir, is_scanned)
                extracted_images.extend(page_images)
            
            # 전체 텍스트를 하나의 파일로도 저장
            if total_text.strip():
                all_text_path = os.path.join(text_dir, "all_pages.txt")
                with open(all_text_path, 'w', encoding='utf-8') as f:
                    f.write(total_text.strip())
                print(f"\n전체 텍스트 저장: {all_text_path}")
            
            # 스캔본인 경우 scan 폴더 생성 및 이미지 복사
            if is_scanned:
                print(f"\n📋 PDF 스캔본으로 판별됨 (pdf_checker 결과)")
                print(f"scan 폴더를 생성하고 이미지를 복사합니다...")
                
                # scan 폴더 생성
                os.makedirs(scan_dir, exist_ok=True)
                
                # img 폴더의 모든 이미지를 scan 폴더로 복사
                copied_count = 0
                for img_file in os.listdir(img_dir):
                    if img_file.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif')):
                        src_path = os.path.join(img_dir, img_file)
                        dst_path = os.path.join(scan_dir, img_file)
                        shutil.copy2(src_path, dst_path)
                        copied_count += 1
                
                print(f"✅ {copied_count}개 이미지를 scan 폴더로 복사 완료")
            
            # 추출 요약 정보 생성
            summary = self._create_summary(
                pdf_path, output_dir, extracted_images, extracted_texts, len(doc)
            )
            
            # 요약 정보 저장
            summary_path = os.path.join(output_dir, "extraction_summary.txt")
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            print(f"\n추출 완료!")
            print(f"출력 디렉토리: {output_dir}")
            print(f"추출된 이미지: {len(extracted_images)}개")
            print(f"추출된 텍스트 페이지: {len(extracted_texts)}개")
            
            # scan 폴더 존재 여부 확인
            has_scan_folder = os.path.exists(scan_dir)
            
            return {
                'success': True,
                'output_dir': output_dir,
                'image_count': len(extracted_images),
                'text_page_count': len(extracted_texts),
                'total_pages': len(doc),
                'images': extracted_images,
                'texts': extracted_texts,
                'has_scan_folder': has_scan_folder,
                'is_scanned_doc': is_scanned
            }
            
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            doc.close()
    
    def _extract_text_from_page(self, page: fitz.Page, page_num: int, text_dir: str) -> str:
        """페이지에서 텍스트 추출"""
        try:
            # 텍스트 추출
            text = page.get_text()
            
            # 텍스트가 있으면 파일로 저장
            if text.strip():
                text_file = os.path.join(text_dir, f"page_{page_num:03d}.txt")
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"  - 텍스트 저장: page_{page_num:03d}.txt ({len(text)} 문자)")
                return text
            else:
                print(f"  - 페이지 {page_num}: 텍스트 없음")
                return ""
                
        except Exception as e:
            print(f"  - 페이지 {page_num} 텍스트 추출 오류: {str(e)}")
            return ""
    
    def _extract_images_from_page(self, page: fitz.Page, page_num: int, img_dir: str, is_scanned: bool = False) -> List[Dict]:
        """페이지에서 이미지 추출"""
        extracted_images = []
        
        try:
            # 스캔본인 경우 전체 페이지 이미지만 저장
            if is_scanned:
                try:
                    # 페이지를 고해상도 이미지로 변환
                    mat = fitz.Matrix(2, 2)  # 2배 확대
                    pix = page.get_pixmap(matrix=mat)
                    
                    # 전체 페이지 이미지 저장
                    full_page_filename = f"page_{page_num:03d}_full.png"
                    full_page_path = os.path.join(img_dir, full_page_filename)
                    pix.save(full_page_path)
                    
                    img_info = {
                        'page': page_num,
                        'index': 0,
                        'filename': full_page_filename,
                        'width': pix.width,
                        'height': pix.height,
                        'size': os.path.getsize(full_page_path),
                        'type': 'full_page'
                    }
                    extracted_images.append(img_info)
                    
                    print(f"  - 전체 페이지 이미지 저장: {full_page_filename}")
                    
                    pix = None
                    
                except Exception as e:
                    print(f"  - 페이지 {page_num} 전체 이미지 저장 오류: {str(e)}")
                
                return extracted_images
            
            # 스캔본이 아닌 경우 기존대로 개별 이미지 추출
            # 페이지의 이미지 리스트 가져오기
            image_list = page.get_images()
            
            if not image_list:
                print(f"  - 페이지 {page_num}: 이미지 없음")
                return extracted_images
            
            for img_index, img in enumerate(image_list, start=1):
                try:
                    # 이미지 참조 번호
                    xref = img[0]
                    
                    # 이미지 데이터 추출
                    pix = fitz.Pixmap(page.parent, xref)
                    
                    # 이미지 파일명 생성
                    img_filename = f"page_{page_num:03d}_img_{img_index:02d}"
                    
                    # 이미지 저장
                    if pix.n - pix.alpha < 4:  # GRAY 또는 RGB
                        img_path = os.path.join(img_dir, f"{img_filename}.png")
                        pix.save(img_path)
                    else:  # CMYK 등 다른 색상 공간
                        # RGB로 변환
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                        img_path = os.path.join(img_dir, f"{img_filename}.png")
                        pix.save(img_path)
                    
                    # 이미지 정보 저장
                    img_info = {
                        'page': page_num,
                        'index': img_index,
                        'filename': os.path.basename(img_path),
                        'width': pix.width,
                        'height': pix.height,
                        'size': os.path.getsize(img_path)
                    }
                    extracted_images.append(img_info)
                    
                    print(f"  - 이미지 저장: {img_filename}.png ({pix.width}x{pix.height})")
                    
                    # 메모리 해제
                    pix = None
                    
                except Exception as e:
                    print(f"  - 페이지 {page_num} 이미지 {img_index} 추출 오류: {str(e)}")
            
            # 스캔본이 아닌 경우에도 전체 페이지 이미지 저장 (선택사항)
            # 이미지만 있고 텍스트가 없는 페이지의 경우 유용
            if len(image_list) > 0:
                try:
                    # 페이지를 고해상도 이미지로 변환
                    mat = fitz.Matrix(2, 2)  # 2배 확대
                    pix = page.get_pixmap(matrix=mat)
                    
                    # 전체 페이지 이미지 저장
                    full_page_filename = f"page_{page_num:03d}_full.png"
                    full_page_path = os.path.join(img_dir, full_page_filename)
                    pix.save(full_page_path)
                    
                    img_info = {
                        'page': page_num,
                        'index': 0,
                        'filename': full_page_filename,
                        'width': pix.width,
                        'height': pix.height,
                        'size': os.path.getsize(full_page_path),
                        'type': 'full_page'
                    }
                    extracted_images.append(img_info)
                    
                    print(f"  - 전체 페이지 이미지 저장: {full_page_filename}")
                    
                    pix = None
                    
                except Exception as e:
                    print(f"  - 페이지 {page_num} 전체 이미지 저장 오류: {str(e)}")
            
        except Exception as e:
            print(f"  - 페이지 {page_num} 이미지 추출 오류: {str(e)}")
        
        return extracted_images
    
    def _create_summary(self, pdf_path: str, output_dir: str, 
                       images: List[Dict], texts: List[Dict], total_pages: int) -> str:
        """추출 요약 정보 생성"""
        # PDF 스캔본 여부 확인
        is_scanned = self.pdf_checker.is_scanned(pdf_path)
        scan_status = "스캔본" if is_scanned else "디지털 문서"
        
        summary = f"""PDF 추출 요약
====================
생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
PDF 파일: {os.path.basename(pdf_path)}
출력 디렉토리: {output_dir}
문서 유형: {scan_status}

페이지 정보
----------
총 페이지 수: {total_pages}
텍스트가 있는 페이지: {len(texts)}
이미지가 있는 페이지: {len(set(img['page'] for img in images if img.get('type') != 'full_page'))}

추출된 컨텐츠
-----------
총 이미지 수: {len(images)}개
총 텍스트 파일: {len(texts) + 1}개 (개별 페이지 + 전체 텍스트)

이미지 상세
----------
"""
        for img in images:
            if img.get('type') != 'full_page':
                summary += f"- {img['filename']}: {img['width']}x{img['height']} ({img['size']:,} bytes)\n"
        
        summary += "\n텍스트 상세\n----------\n"
        total_chars = 0
        for txt in texts:
            summary += f"- 페이지 {txt['page']}: {txt['char_count']:,}자\n"
            total_chars += txt['char_count']
        
        summary += f"\n총 텍스트 문자 수: {total_chars:,}자"
        
        # scan 폴더 정보 추가
        if is_scanned:
            summary += f"\n\n스캔 문서 처리\n----------\n"
            summary += f"- scan 폴더가 생성되었습니다\n"
            summary += f"- 모든 이미지가 scan 폴더로 복사되었습니다"
        
        return summary


def main():
    """테스트용 메인 함수"""
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python pdf_extractor.py [PDF파일경로] [출력디렉토리(선택)]")
        print("\n예제:")
        print("  python pdf_extractor.py document.pdf")
        print("  python pdf_extractor.py document.pdf my_output")
        return
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 추출기 생성 및 실행
    extractor = PDFExtractor()
    result = extractor.extract(pdf_path, output_dir)
    
    if result['success']:
        print(f"\n✅ 추출 성공!")
        print(f"결과 위치: {result['output_dir']}")
    else:
        print(f"\n❌ 추출 실패: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()