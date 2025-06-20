"""
PDF 이미지 추출 도구
PDF 파일에서 모든 이미지를 추출하여 PNG, JPEG 등으로 저장
"""
import fitz  # PyMuPDF
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from PIL import Image
import io


class PDFImageExtractor:
    """PDF에서 이미지를 추출하는 클래스"""
    
    def __init__(self, output_dir: str = None):
        """
        Args:
            output_dir: 이미지를 저장할 디렉토리 (None이면 PDF와 같은 위치에 폴더 생성)
        """
        self.output_dir = output_dir
        self.extracted_images = []
        
    def extract_images_from_pdf(self, pdf_path: str, save_format: str = "png") -> List[Dict]:
        """
        PDF에서 모든 이미지 추출
        
        Args:
            pdf_path: PDF 파일 경로
            save_format: 저장 형식 (png, jpeg, jpg)
            
        Returns:
            추출된 이미지 정보 리스트
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        
        # 출력 디렉토리 설정
        pdf_name = Path(pdf_path).stem
        if self.output_dir:
            output_folder = Path(self.output_dir) / f"{pdf_name}_images"
        else:
            output_folder = Path(pdf_path).parent / f"{pdf_name}_images"
        
        # 출력 폴더 생성
        output_folder.mkdir(exist_ok=True)
        
        print(f"\n📄 PDF 이미지 추출: {os.path.basename(pdf_path)}")
        print(f"📁 저장 폴더: {output_folder}")
        print("=" * 60)
        
        # PDF 열기
        doc = fitz.open(pdf_path)
        total_images = 0
        extracted_count = 0
        
        # 각 페이지 처리
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            if not image_list:
                continue
                
            print(f"\n📄 페이지 {page_num + 1}: {len(image_list)}개 이미지 발견")
            
            # 페이지의 각 이미지 처리
            for img_index, img_info in enumerate(image_list):
                total_images += 1
                img_data = {}  # 초기화
                
                try:
                    # 이미지 추출
                    xref = img_info[0]  # XREF
                    pix = fitz.Pixmap(doc, xref)
                    
                    # 이미지 정보
                    img_data = {
                        'page': page_num + 1,
                        'index': img_index + 1,
                        'width': pix.width,
                        'height': pix.height,
                        'size': len(pix.pil_tobytes()),
                        'colorspace': pix.colorspace.name if pix.colorspace else 'unknown'
                    }
                    
                    # 파일명 생성
                    filename = f"page{page_num + 1:03d}_img{img_index + 1:03d}"
                    
                    # 이미지 저장
                    if pix.n - pix.alpha < 4:  # GRAY 또는 RGB
                        # 직접 저장
                        if save_format.lower() in ['jpg', 'jpeg']:
                            # JPEG는 RGB로 변환 필요
                            pix1 = fitz.Pixmap(fitz.csRGB, pix)
                            output_path = output_folder / f"{filename}.{save_format}"
                            pix1.save(str(output_path))
                            pix1 = None
                        else:
                            output_path = output_folder / f"{filename}.{save_format}"
                            pix.save(str(output_path))
                    else:  # CMYK 등 다른 색공간
                        # PIL을 통해 변환
                        img = Image.open(io.BytesIO(pix.pil_tobytes()))
                        if save_format.lower() in ['jpg', 'jpeg']:
                            # JPEG는 RGB 모드 필요
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                        output_path = output_folder / f"{filename}.{save_format}"
                        img.save(str(output_path))
                    
                    pix = None  # 메모리 해제
                    
                    img_data['filename'] = output_path.name
                    img_data['filepath'] = str(output_path)
                    img_data['saved'] = True
                    
                    self.extracted_images.append(img_data)
                    extracted_count += 1
                    
                    print(f"  ✅ {filename}.{save_format} ({img_data['width']}x{img_data['height']})")
                    
                except Exception as e:
                    print(f"  ❌ 이미지 {img_index + 1} 추출 실패: {str(e)}")
                    img_data['saved'] = False
                    img_data['error'] = str(e)
                    self.extracted_images.append(img_data)
        
        doc.close()
        
        # 결과 요약
        print(f"\n📊 추출 결과:")
        print(f"  - 발견된 이미지: {total_images}개")
        print(f"  - 추출 성공: {extracted_count}개")
        print(f"  - 추출 실패: {total_images - extracted_count}개")
        print(f"  - 저장 위치: {output_folder}")
        
        return self.extracted_images
    
    def extract_page_as_image(self, pdf_path: str, page_nums: List[int] = None, 
                            dpi: int = 150, save_format: str = "png") -> List[str]:
        """
        PDF 페이지를 이미지로 변환하여 저장
        
        Args:
            pdf_path: PDF 파일 경로
            page_nums: 추출할 페이지 번호 리스트 (None이면 모든 페이지)
            dpi: 해상도 (기본 150)
            save_format: 저장 형식
            
        Returns:
            저장된 이미지 파일 경로 리스트
        """
        doc = fitz.open(pdf_path)
        pdf_name = Path(pdf_path).stem
        
        # 출력 디렉토리 설정
        if self.output_dir:
            output_folder = Path(self.output_dir) / f"{pdf_name}_pages"
        else:
            output_folder = Path(pdf_path).parent / f"{pdf_name}_pages"
        
        output_folder.mkdir(exist_ok=True)
        
        print(f"\n📄 PDF 페이지를 이미지로 변환: {os.path.basename(pdf_path)}")
        print(f"📁 저장 폴더: {output_folder}")
        print(f"🎯 해상도: {dpi} DPI")
        print("=" * 60)
        
        # 페이지 번호 설정
        if page_nums is None:
            page_nums = list(range(len(doc)))
        else:
            # 1-based를 0-based로 변환
            page_nums = [p - 1 for p in page_nums if 0 <= p - 1 < len(doc)]
        
        saved_files = []
        
        # 각 페이지 변환
        for page_num in page_nums:
            try:
                page = doc[page_num]
                
                # DPI에 따른 확대 비율 계산
                zoom = dpi / 72.0  # 72 DPI가 기본
                mat = fitz.Matrix(zoom, zoom)
                
                # 페이지를 이미지로 렌더링
                pix = page.get_pixmap(matrix=mat)
                
                # 파일명 생성
                filename = f"{pdf_name}_page{page_num + 1:03d}.{save_format}"
                output_path = output_folder / filename
                
                # 이미지 저장
                if save_format.lower() in ['jpg', 'jpeg']:
                    # JPEG는 RGB 필요
                    pix1 = fitz.Pixmap(fitz.csRGB, pix)
                    pix1.save(str(output_path))
                    pix1 = None
                else:
                    pix.save(str(output_path))
                
                pix = None
                
                saved_files.append(str(output_path))
                print(f"  ✅ 페이지 {page_num + 1} → {filename}")
                
            except Exception as e:
                print(f"  ❌ 페이지 {page_num + 1} 변환 실패: {str(e)}")
        
        doc.close()
        
        print(f"\n✅ 총 {len(saved_files)}개 페이지가 이미지로 저장되었습니다.")
        
        return saved_files
    
    def get_image_info(self, pdf_path: str) -> Dict:
        """PDF 내 이미지 정보만 분석 (추출하지 않음)"""
        doc = fitz.open(pdf_path)
        
        info = {
            'total_pages': len(doc),
            'pages_with_images': 0,
            'total_images': 0,
            'image_details': []
        }
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            if image_list:
                info['pages_with_images'] += 1
                info['total_images'] += len(image_list)
                
                for img_index, img_info in enumerate(image_list):
                    try:
                        xref = img_info[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        detail = {
                            'page': page_num + 1,
                            'index': img_index + 1,
                            'width': pix.width,
                            'height': pix.height,
                            'colorspace': pix.colorspace.name if pix.colorspace else 'unknown',
                            'size_estimate': pix.width * pix.height * (pix.n - pix.alpha)
                        }
                        
                        info['image_details'].append(detail)
                        pix = None
                        
                    except:
                        pass
        
        doc.close()
        return info


def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python extract_pdf_images.py [PDF파일] [옵션]")
        print("\n옵션:")
        print("  --format [png/jpg/jpeg]  : 저장 형식 (기본: png)")
        print("  --pages                  : 페이지를 이미지로 변환")
        print("  --dpi [숫자]            : 페이지 변환 시 해상도 (기본: 150)")
        print("  --info                   : 이미지 정보만 표시")
        print("\n예시:")
        print("  python extract_pdf_images.py test.pdf")
        print("  python extract_pdf_images.py test.pdf --format jpg")
        print("  python extract_pdf_images.py test.pdf --pages --dpi 300")
        print("  python extract_pdf_images.py test.pdf --info")
        return
    
    pdf_path = sys.argv[1]
    
    # 옵션 파싱
    save_format = "png"
    extract_pages = False
    dpi = 150
    info_only = False
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--format" and i + 1 < len(sys.argv):
            save_format = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--pages":
            extract_pages = True
            i += 1
        elif sys.argv[i] == "--dpi" and i + 1 < len(sys.argv):
            dpi = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--info":
            info_only = True
            i += 1
        else:
            i += 1
    
    # 추출기 생성
    extractor = PDFImageExtractor()
    
    try:
        if info_only:
            # 정보만 표시
            info = extractor.get_image_info(pdf_path)
            print(f"\n📄 PDF 이미지 정보: {os.path.basename(pdf_path)}")
            print("=" * 60)
            print(f"📊 총 페이지: {info['total_pages']}페이지")
            print(f"🖼️  이미지 포함 페이지: {info['pages_with_images']}페이지")
            print(f"📷 총 이미지 수: {info['total_images']}개")
            
            if info['image_details']:
                print("\n상세 정보 (처음 5개):")
                for detail in info['image_details'][:5]:
                    print(f"  - 페이지 {detail['page']}: "
                          f"{detail['width']}x{detail['height']} "
                          f"({detail['colorspace']})")
        
        elif extract_pages:
            # 페이지를 이미지로 변환
            saved_files = extractor.extract_page_as_image(
                pdf_path, 
                dpi=dpi, 
                save_format=save_format
            )
        
        else:
            # PDF 내 이미지 추출
            images = extractor.extract_images_from_pdf(
                pdf_path, 
                save_format=save_format
            )
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")


if __name__ == "__main__":
    main()