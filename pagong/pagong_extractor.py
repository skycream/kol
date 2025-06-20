"""
Pagong Extractor - 일괄 PDF 처리 스크립트
data 폴더 내의 모든 ID 폴더를 순회하며 PDF 파일을 자동으로 처리

동작 방식:
1. data 폴더 내의 모든 ID 폴더를 숫자 역순으로 정렬
2. 각 ID 폴더에서:
   - pdf 폴더가 있고, img/text 폴더가 없으면
   - pdf 폴더 내의 PDF 파일을 pdf_extractor로 처리
   - 결과를 해당 ID 폴더에 저장
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import re
from pdf_extractor import PDFExtractor


class PagongExtractor:
    """data 폴더의 PDF들을 일괄 처리하는 클래스"""
    
    def __init__(self, data_dir: str = "data"):
        """
        초기화
        
        Args:
            data_dir: data 폴더 경로 (기본값: "data")
        """
        self.data_dir = data_dir
        self.pdf_extractor = PDFExtractor()
        self.processed_count = 0
        self.skipped_count = 0
        self.error_count = 0
        
    def run(self):
        """메인 실행 함수"""
        print("🚀 Pagong Extractor 시작")
        print(f"📁 data 폴더 경로: {self.data_dir}")
        print("="*60)
        
        # data 폴더 존재 확인
        if not os.path.exists(self.data_dir):
            print(f"❌ data 폴더를 찾을 수 없습니다: {self.data_dir}")
            return
        
        # ID 폴더들 찾기 및 정렬
        id_folders = self._get_sorted_id_folders()
        
        if not id_folders:
            print("⚠️  처리할 ID 폴더가 없습니다.")
            return
        
        print(f"📊 발견된 ID 폴더: {len(id_folders)}개")
        print(f"📋 처리 순서 (숫자 높은 순): {id_folders[:5]}{'...' if len(id_folders) > 5 else ''}")
        print("="*60)
        
        # 각 ID 폴더 처리
        for idx, id_folder in enumerate(id_folders, 1):
            print(f"\n[{idx}/{len(id_folders)}] ID: {id_folder}")
            
            # 이미 처리된 폴더인지 확인
            id_path = os.path.join(self.data_dir, id_folder)
            img_dir = os.path.join(id_path, "img")
            text_dir = os.path.join(id_path, "text")
            
            if os.path.exists(img_dir) or os.path.exists(text_dir):
                print(f"  🛑 img/text 폴더가 이미 존재 - 여기서 정지")
                print(f"     (이미 처리된 데이터로 판단)")
                self.skipped_count += 1
                break
            
            # 폴더 처리
            self._process_id_folder(id_folder)
        
        # 최종 결과 출력
        self._print_summary()
    
    def _get_sorted_id_folders(self) -> List[str]:
        """
        data 폴더 내의 ID 폴더들을 찾아서 숫자 높은 순으로 정렬
        
        Returns:
            정렬된 ID 폴더명 리스트
        """
        id_folders = []
        
        for item in os.listdir(self.data_dir):
            item_path = os.path.join(self.data_dir, item)
            if os.path.isdir(item_path):
                # 폴더명에서 숫자 추출 시도
                match = re.match(r'^(\d+)', item)
                if match:
                    id_num = int(match.group(1))
                    id_folders.append((id_num, item))
        
        # 숫자 기준 내림차순 정렬
        id_folders.sort(key=lambda x: x[0], reverse=True)
        
        # 폴더명만 반환
        return [folder_name for _, folder_name in id_folders]
    
    def _process_id_folder(self, id_folder: str):
        """
        개별 ID 폴더 처리
        
        Args:
            id_folder: ID 폴더명
        """
        id_path = os.path.join(self.data_dir, id_folder)
        
        # 하위 폴더 확인
        pdf_dir = os.path.join(id_path, "pdf")
        img_dir = os.path.join(id_path, "img")
        text_dir = os.path.join(id_path, "text")
        
        # pdf 폴더가 있는지 확인
        if not os.path.exists(pdf_dir):
            print(f"  ⏭️  pdf 폴더 없음 - 건너뜀")
            self.skipped_count += 1
            return
        
        
        # pdf 폴더 내의 PDF 파일 찾기
        pdf_files = self._find_pdf_files(pdf_dir)
        
        if not pdf_files:
            print(f"  ⚠️  pdf 폴더에 PDF 파일 없음")
            self.skipped_count += 1
            return
        
        # 첫 번째 PDF 파일 처리 (보통 하나만 있을 것으로 예상)
        pdf_file = pdf_files[0]
        print(f"  📄 PDF 파일 발견: {os.path.basename(pdf_file)}")
        
        try:
            # PDF 추출 실행 - 출력 디렉토리를 ID 폴더로 직접 지정
            print(f"  🔄 추출 시작...")
            print(f"     - PDF 경로: {pdf_file}")
            print(f"     - 출력 경로: {id_path}")
            
            result = self.pdf_extractor.extract(pdf_file, output_dir=id_path)
            
            if result['success']:
                print(f"  ✅ 추출 성공!")
                print(f"     - 이미지: {result['image_count']}개")
                print(f"     - 텍스트 페이지: {result['text_page_count']}개")
                print(f"     - 스캔본 여부: {result.get('is_scanned_doc', False)}")
                if result.get('has_scan_folder'):
                    print(f"     - 📋 scan 폴더 생성됨")
                
                # 생성된 폴더 확인
                created_dirs = []
                if os.path.exists(os.path.join(id_path, "img")):
                    created_dirs.append("img")
                if os.path.exists(os.path.join(id_path, "text")):
                    created_dirs.append("text")
                if os.path.exists(os.path.join(id_path, "scan")):
                    created_dirs.append("scan")
                print(f"     - 생성된 폴더: {', '.join(created_dirs)}")
                
                self.processed_count += 1
            else:
                print(f"  ❌ 추출 실패: {result.get('error', 'Unknown error')}")
                self.error_count += 1
                
        except Exception as e:
            print(f"  ❌ 오류 발생: {str(e)}")
            self.error_count += 1
    
    def _find_pdf_files(self, pdf_dir: str) -> List[str]:
        """
        디렉토리에서 PDF 파일 찾기
        
        Args:
            pdf_dir: PDF 디렉토리 경로
            
        Returns:
            PDF 파일 경로 리스트
        """
        pdf_files = []
        
        for file in os.listdir(pdf_dir):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(pdf_dir, file))
        
        return pdf_files
    
    def _print_summary(self):
        """처리 결과 요약 출력"""
        print("\n" + "="*60)
        print("📊 처리 결과 요약")
        print("="*60)
        print(f"✅ 성공적으로 처리: {self.processed_count}개")
        print(f"⏭️  건너뛴 폴더: {self.skipped_count}개")
        print(f"❌ 오류 발생: {self.error_count}개")
        print(f"📁 전체: {self.processed_count + self.skipped_count + self.error_count}개")
        print("="*60)
        print("✨ Pagong Extractor 완료!")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="data 폴더의 PDF들을 일괄 처리합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python pagong_extractor.py              # 기본 data 폴더 처리
  python pagong_extractor.py --data-dir custom_data  # 커스텀 폴더 처리
  python pagong_extractor.py --dry-run    # 실제 처리하지 않고 확인만
        """
    )
    
    parser.add_argument(
        "--data-dir", 
        default="data",
        help="처리할 data 폴더 경로 (기본값: data)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 처리하지 않고 처리 대상만 확인"
    )
    
    args = parser.parse_args()
    
    # Dry run 모드
    if args.dry_run:
        print("🔍 DRY RUN 모드 - 실제 처리하지 않고 대상만 확인합니다.")
        extractor = PagongExtractor(args.data_dir)
        id_folders = extractor._get_sorted_id_folders()
        
        print(f"📁 data 폴더: {args.data_dir}")
        print(f"📊 발견된 ID 폴더: {len(id_folders)}개")
        print("\n처리 대상 ID 폴더 목록:")
        
        for idx, id_folder in enumerate(id_folders, 1):
            id_path = os.path.join(args.data_dir, id_folder)
            pdf_dir = os.path.join(id_path, "pdf")
            img_dir = os.path.join(id_path, "img")
            text_dir = os.path.join(id_path, "text")
            
            status = "⏭️ 건너뜀"
            reason = ""
            
            # 이미 처리된 폴더면 여기서 중단
            if os.path.exists(img_dir) or os.path.exists(text_dir):
                print(f"{idx:4d}. {id_folder:20s} 🛑 정지 (img/text 이미 존재)")
                print("\n⚠️  이미 처리된 폴더를 만나 여기서 중단됩니다.")
                break
            
            if not os.path.exists(pdf_dir):
                reason = "(pdf 폴더 없음)"
            else:
                pdf_files = []
                if os.path.exists(pdf_dir):
                    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
                if pdf_files:
                    status = "✅ 처리 대상"
                    reason = f"(PDF: {pdf_files[0]})"
                else:
                    reason = "(PDF 파일 없음)"
            
            print(f"{idx:4d}. {id_folder:20s} {status} {reason}")
        
        return
    
    # 실제 실행
    extractor = PagongExtractor(args.data_dir)
    extractor.run()


if __name__ == "__main__":
    main()