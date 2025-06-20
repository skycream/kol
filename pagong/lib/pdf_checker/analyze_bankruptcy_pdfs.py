"""
파산자 파일 폴더의 모든 PDF OCR 필요성 분석
다운로드 폴더의 '0파산자 파일' 폴더 내 모든 PDF를 분석합니다.
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import json
import warnings
import fitz  # PyMuPDF

# MuPDF 경고 무시
warnings.filterwarnings("ignore", message=".*ExtGState.*")
# stderr로 출력되는 MuPDF 에러 메시지 억제
fitz.TOOLS.mupdf_display_errors(False)

# if_ocr.py의 클래스들 import
from if_ocr import PDFOCRDetector, PDFAnalysisResult
# pdf_metadata_analyzer.py의 클래스 import
from pdf_metadata_analyzer import PDFMetadataAnalyzer


class BankruptcyPDFAnalyzer:
    """파산자 파일 폴더의 PDF 일괄 분석 클래스"""
    
    def __init__(self):
        self.detector = PDFOCRDetector()
        self.metadata_analyzer = PDFMetadataAnalyzer()
        self.results = []
        
        # 다운로드 폴더 경로 설정
        self.download_path = Path.home() / "Downloads" / "파산자 파일"
    
    def _safe_encode_string(self, text):
        """문자열을 안전하게 인코딩"""
        if not text:
            return ""
        
        # 문자열이 아닌 경우 변환
        if not isinstance(text, str):
            text = str(text)
        
        try:
            # 1차 시도: 그대로 인코딩
            return text.encode('utf-8').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                # 2차 시도: surrogates 제거
                # 잘못된 유니코드 문자 제거
                cleaned = []
                for char in text:
                    try:
                        char.encode('utf-8')
                        cleaned.append(char)
                    except UnicodeEncodeError:
                        cleaned.append('?')
                return ''.join(cleaned)
            except:
                try:
                    # 3차 시도: ASCII로 변환
                    return text.encode('ascii', 'replace').decode('ascii')
                except:
                    # 최종: 빈 문자열
                    return "인코딩_오류"
    
    def _get_safe_path(self, pdf_path):
        """파일 경로를 안전하게 변환"""
        try:
            # 1. Path 객체인 경우
            if isinstance(pdf_path, Path):
                # bytes로 변환 후 다시 문자열로
                try:
                    path_bytes = bytes(pdf_path)
                    return path_bytes.decode('utf-8', 'replace')
                except:
                    pass
                
                # os.fspath 사용
                try:
                    return os.fspath(pdf_path)
                except:
                    pass
            
            # 2. 문자열인 경우
            path_str = str(pdf_path)
            
            # surrogate 문자 처리
            try:
                # surrogatepass로 인코딩하고 replace로 디코딩
                path_bytes = path_str.encode('utf-8', 'surrogatepass')
                path_str = path_bytes.decode('utf-8', 'replace')
            except:
                # latin-1으로 시도
                try:
                    path_bytes = path_str.encode('latin-1', 'replace')
                    path_str = path_bytes.decode('latin-1')
                except:
                    pass
            
            # 경로가 올바른지 확인
            if os.path.exists(path_str):
                return path_str
            
            # 3. 파일명과 디렉토리를 분리해서 처리
            try:
                dir_path = os.path.dirname(path_str)
                file_name = os.path.basename(path_str)
                
                # 파일명만 안전하게 변환
                safe_name = self._safe_encode_string(file_name)
                return os.path.join(dir_path, safe_name)
            except:
                pass
            
            # 4. 최후의 수단
            return path_str.encode('ascii', 'replace').decode('ascii')
            
        except Exception as e:
            print(f"경로 변환 실패: {e}")
            return str(pdf_path)
        
    def analyze_all_pdfs(self) -> List[Dict]:
        """폴더 내 모든 PDF 파일 분석"""
        
        if not self.download_path.exists():
            print(f"❌ 폴더를 찾을 수 없습니다: {self.download_path}")
            return []
        
        # PDF 파일 찾기
        pdf_files = []
        problematic_files = []
        
        try:
            # os.scandir을 사용하여 더 안전하게 파일 찾기
            def scan_directory(path):
                try:
                    with os.scandir(path) as entries:
                        for entry in entries:
                            if entry.is_file() and entry.name.lower().endswith('.pdf'):
                                try:
                                    # DirEntry 객체의 path 속성 사용
                                    pdf_files.append(Path(entry.path))
                                except Exception as e:
                                    problematic_files.append((entry.name[:50], str(e)))
                            elif entry.is_dir():
                                # 재귀적으로 하위 디렉토리 검색
                                scan_directory(entry.path)
                except Exception as e:
                    print(f"디렉토리 스캔 오류: {e}")
            
            scan_directory(str(self.download_path))
            
        except Exception as e:
            print(f"⚠️ 파일 목록 생성 중 오류: {str(e)}")
            # 대체 방법: pathlib 사용
            try:
                for pdf_path in self.download_path.rglob("*.pdf"):
                    pdf_files.append(pdf_path)
            except:
                pass
        
        if problematic_files:
            print(f"\n⚠️ 인코딩 문제로 {len(problematic_files)}개 파일을 건너뜁니다:")
            for name, error in problematic_files[:5]:
                print(f"   - {name}...")
            if len(problematic_files) > 5:
                print(f"   ... 외 {len(problematic_files)-5}개")
        
        if not pdf_files:
            print(f"❌ PDF 파일이 없습니다: {self.download_path}")
            return []
        
        print(f"📁 분석 폴더: {self.download_path}")
        print(f"📄 발견된 PDF 파일: {len(pdf_files)}개")
        print("=" * 80)
        
        # 각 PDF 파일 분석
        for idx, pdf_path in enumerate(pdf_files, 1):
            # 파일명 안전하게 출력
            try:
                safe_name = self._safe_encode_string(pdf_path.name)
            except:
                safe_name = "파일명_읽기_오류.pdf"
            
            print(f"\n[{idx}/{len(pdf_files)}] 분석 중: {safe_name}")
            print("-" * 60)
            
            try:
                # 파일 경로를 안전하게 처리
                safe_path_str = self._get_safe_path(pdf_path)
                
                # 파일이 실제로 열리는지 테스트
                # 여러 방법으로 시도
                file_opened = False
                actual_path = None
                
                # 방법 1: 직접 열기
                try:
                    with open(safe_path_str, 'rb') as f:
                        f.read(1)
                    file_opened = True
                    actual_path = safe_path_str
                except:
                    pass
                
                # 방법 2: Path 객체로 열기
                if not file_opened:
                    try:
                        with pdf_path.open('rb') as f:
                            f.read(1)
                        file_opened = True
                        actual_path = str(pdf_path)
                    except:
                        pass
                
                # 방법 3: os.path.realpath 사용
                if not file_opened:
                    try:
                        real_path = os.path.realpath(safe_path_str)
                        with open(real_path, 'rb') as f:
                            f.read(1)
                        file_opened = True
                        actual_path = real_path
                    except:
                        pass
                
                if not file_opened:
                    raise Exception(f"파일을 열 수 없습니다: 모든 방법 실패")
                
                # 실제로 열린 경로 사용
                safe_path_str = actual_path
                
                # OCR 필요성 분석
                result = self.detector.analyze(safe_path_str)
                
                # 메타데이터 상세 분석
                metadata_analysis = self.metadata_analyzer.analyze_metadata(safe_path_str)
                
                # 결과 저장
                analysis_data = {
                    'file_name': self._safe_encode_string(pdf_path.name),
                    'file_path': self._safe_encode_string(str(pdf_path)),
                    'file_size': pdf_path.stat().st_size,
                    'needs_ocr': result.needs_ocr,
                    'pdf_type': result.pdf_type,
                    'confidence': result.confidence,
                    'total_pages': result.total_pages,
                    'text_pages': result.text_pages,
                    'image_pages': result.image_pages,
                    'reasons': [self._safe_encode_string(r) for r in result.reasons],
                    'recommendations': [self._safe_encode_string(r) for r in result.recommendations],
                    'analysis_time': datetime.now().isoformat(),
                    # 메타데이터 정보 추가
                    'producer': self._safe_encode_string(str(metadata_analysis['producer_analysis']['producer'])),
                    'creator': self._safe_encode_string(str(metadata_analysis['producer_analysis']['creator'])),
                    'producer_type': metadata_analysis['producer_analysis']['producer_type'],
                    'scan_score': metadata_analysis['scan_score']['total_score'],
                    'is_likely_scanned': metadata_analysis['is_likely_scanned'],
                    'has_fonts': metadata_analysis['font_analysis']['has_fonts'],
                    'avg_text_per_page': metadata_analysis['page_analysis']['avg_text_per_page']
                }
                
                self.results.append(analysis_data)
                
                # 결과 출력 (메타데이터 정보 포함)
                self._print_result_with_metadata(result, metadata_analysis, safe_name)
                
            except Exception as e:
                # 에러 타입 확인
                error_type = type(e).__name__
                error_msg = str(e)
                
                # 인코딩 관련 에러인지 확인
                if 'surrogates not allowed' in error_msg or 'codec' in error_msg:
                    print(f"❌ 파일명 인코딩 문제로 건너뜁니다: {safe_name[:50]}...")
                    print(f"   (에러: {error_type})")
                else:
                    print(f"❌ 분석 실패: {error_msg}")
                
                # 파일명 안전하게 처리
                safe_filename = self._safe_encode_string(safe_name)
                safe_filepath = f"인코딩_문제_파일_{idx}"
                
                self.results.append({
                    'file_name': safe_filename,
                    'file_path': safe_filepath,
                    'error': f"{error_type}: {error_msg[:100]}",
                    'analysis_time': datetime.now().isoformat(),
                    'error_type': 'encoding' if 'surrogates' in error_msg else 'other'
                })
        
        return self.results
    
    def _print_result(self, result: PDFAnalysisResult, file_name: str):
        """분석 결과 출력"""
        ocr_status = "⭕ 필요" if result.needs_ocr else "❌ 불필요"
        
        print(f"🔍 OCR 필요성: {ocr_status}")
        print(f"📊 PDF 유형: {result.pdf_type}")
        print(f"🎯 판단 신뢰도: {result.confidence:.0%}")
        print(f"📄 페이지: 전체 {result.total_pages}p (텍스트: {result.text_pages}p, 이미지: {result.image_pages}p)")
        
        # 주요 판단 근거 (최대 2개만)
        if result.reasons:
            print(f"💭 주요 근거: {result.reasons[0]}")
            if len(result.reasons) > 1:
                print(f"            {result.reasons[1]}")
    
    def _print_result_with_metadata(self, result: PDFAnalysisResult, metadata_analysis: Dict, file_name: str):
        """메타데이터 포함 분석 결과 출력"""
        ocr_status = "⭕ 필요" if result.needs_ocr else "❌ 불필요"
        
        print(f"🔍 OCR 필요성: {ocr_status}")
        print(f"📊 PDF 유형: {result.pdf_type}")
        print(f"🎯 판단 신뢰도: {result.confidence:.0%}")
        print(f"📄 페이지: 전체 {result.total_pages}p (텍스트: {result.text_pages}p, 이미지: {result.image_pages}p)")
        
        # 메타데이터 정보
        producer = metadata_analysis['producer_analysis']['producer'] or '없음'
        producer_type = metadata_analysis['producer_analysis']['producer_type']
        scan_score = metadata_analysis['scan_score']['total_score']
        
        print(f"📋 Producer: {producer} (유형: {producer_type})")
        print(f"🎯 스캔 점수: {scan_score}/100")
        
        # 주요 판단 근거 (최대 2개만)
        if result.reasons:
            print(f"💭 주요 근거: {result.reasons[0]}")
            if len(result.reasons) > 1:
                print(f"            {result.reasons[1]}")
    
    def generate_summary(self):
        """전체 분석 결과 요약"""
        if not self.results:
            return
        
        print("\n" + "=" * 80)
        print("📊 전체 분석 결과 요약")
        print("=" * 80)
        
        # 통계 계산
        total_files = len(self.results)
        error_files = [r for r in self.results if 'error' in r]
        success_files = [r for r in self.results if 'error' not in r]
        
        ocr_needed = [r for r in success_files if r['needs_ocr']]
        ocr_not_needed = [r for r in success_files if not r['needs_ocr']]
        
        # PDF 유형별 분류
        pdf_types = {}
        producer_types = {}
        scan_scores = []
        
        for r in success_files:
            pdf_type = r['pdf_type']
            if pdf_type not in pdf_types:
                pdf_types[pdf_type] = []
            pdf_types[pdf_type].append(r)
            
            # Producer 유형별 분류
            if 'producer_type' in r:
                prod_type = r['producer_type']
                if prod_type not in producer_types:
                    producer_types[prod_type] = []
                producer_types[prod_type].append(r)
                
            # 스캔 점수 수집
            if 'scan_score' in r:
                scan_scores.append(r['scan_score'])
        
        # 요약 출력
        print(f"\n📁 총 분석 파일: {total_files}개")
        print(f"  ✅ 성공: {len(success_files)}개")
        print(f"  ❌ 실패: {len(error_files)}개")
        
        print(f"\n🔍 OCR 필요성:")
        print(f"  ⭕ OCR 필요: {len(ocr_needed)}개 ({len(ocr_needed)/len(success_files)*100:.1f}%)")
        print(f"  ❌ OCR 불필요: {len(ocr_not_needed)}개 ({len(ocr_not_needed)/len(success_files)*100:.1f}%)")
        
        print(f"\n📊 PDF 유형별 분포:")
        for pdf_type, files in pdf_types.items():
            print(f"  - {pdf_type}: {len(files)}개")
        
        print(f"\n📋 Producer 유형별 분포:")
        for prod_type, files in producer_types.items():
            print(f"  - {prod_type}: {len(files)}개 ({len(files)/len(success_files)*100:.1f}%)")
        
        if scan_scores:
            avg_scan_score = sum(scan_scores) / len(scan_scores)
            high_scan_score = len([s for s in scan_scores if s >= 70])
            print(f"\n🎯 스캔 점수 분석:")
            print(f"  - 평균 스캔 점수: {avg_scan_score:.0f}/100")
            print(f"  - 높은 스캔 점수 (70+): {high_scan_score}개 ({high_scan_score/len(scan_scores)*100:.1f}%)")
        
        # OCR 필요한 파일 목록
        if ocr_needed:
            print(f"\n⭕ OCR이 필요한 파일 목록:")
            for idx, r in enumerate(ocr_needed[:10], 1):  # 최대 10개만 표시
                print(f"  {idx}. {r['file_name']} ({r['confidence']:.0%} 신뢰도)")
            if len(ocr_needed) > 10:
                print(f"  ... 외 {len(ocr_needed)-10}개")
        
        # 오류 파일 목록
        if error_files:
            print(f"\n❌ 분석 실패 파일:")
            for r in error_files[:5]:  # 최대 5개만 표시
                print(f"  - {r['file_name']}: {r['error']}")
            if len(error_files) > 5:
                print(f"  ... 외 {len(error_files)-5}개")
    
    def save_results(self, output_file: str = "bankruptcy_pdf_analysis.json"):
        """분석 결과를 JSON 파일로 저장"""
        output_path = Path(output_file)
        
        # 요약 정보 추가
        summary = {
            'analysis_date': datetime.now().isoformat(),
            'total_files': len(self.results),
            'ocr_needed': sum(1 for r in self.results if r.get('needs_ocr', False)),
            'ocr_not_needed': sum(1 for r in self.results if not r.get('needs_ocr', False) and 'error' not in r),
            'errors': sum(1 for r in self.results if 'error' in r),
            'folder_path': str(self.download_path)
        }
        
        output_data = {
            'summary': summary,
            'results': self.results
        }
        
        # JSON 데이터를 안전하게 인코딩
        safe_json_str = json.dumps(output_data, ensure_ascii=True, indent=2)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(safe_json_str)
        
        print(f"\n💾 분석 결과가 '{output_path}'에 저장되었습니다.")
        
        # CSV 형태로도 저장 (간단한 요약)
        csv_path = output_path.with_suffix('.csv')
        with open(csv_path, 'w', encoding='utf-8-sig') as f:  # utf-8-sig로 BOM 추가
            f.write("파일명,OCR필요,PDF유형,신뢰도,전체페이지,텍스트페이지,이미지페이지,Producer,Producer유형,스캔점수,평균텍스트\n")
            for r in self.results:
                if 'error' not in r:
                    # 각 필드는 이미 안전하게 인코딩됨
                    f.write(f"{r['file_name']},{r['needs_ocr']},{r['pdf_type']},"
                           f"{r['confidence']:.2f},{r['total_pages']},"
                           f"{r['text_pages']},{r['image_pages']},"
                           f"\"{r.get('producer', '')}\",{r.get('producer_type', '')},"
                           f"{r.get('scan_score', 0)},{r.get('avg_text_per_page', 0):.0f}\n")
                else:
                    f.write(f"{r['file_name']},ERROR,,,,,,,,,\n")
        
        print(f"📊 CSV 요약이 '{csv_path}'에 저장되었습니다.")


def main():
    """메인 실행 함수"""
    print("🔍 파산자 파일 PDF OCR 필요성 분석기")
    print("=" * 80)
    
    # 명령줄 인자로 폴더 경로 받기
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
        analyzer = BankruptcyPDFAnalyzer()
        analyzer.download_path = Path(folder_path)
        print(f"📁 지정된 폴더: {folder_path}")
    else:
        analyzer = BankruptcyPDFAnalyzer()
        print(f"📁 기본 폴더: {analyzer.download_path}")
        
        # 폴더가 없으면 사용자에게 경로 입력 받기
        if not analyzer.download_path.exists():
            print("\n기본 폴더를 찾을 수 없습니다.")
            folder_input = input("분석할 폴더 경로를 입력하세요 (또는 Enter로 현재 폴더 사용): ").strip()
            
            if folder_input:
                analyzer.download_path = Path(folder_input)
            else:
                analyzer.download_path = Path.cwd()
                print(f"현재 폴더를 사용합니다: {analyzer.download_path}")
    
    # 모든 PDF 분석
    results = analyzer.analyze_all_pdfs()
    
    if results:
        # 요약 생성
        analyzer.generate_summary()
        
        # 결과 저장
        analyzer.save_results()
        
        print("\n✅ 분석이 완료되었습니다!")
    else:
        print("\n❌ 분석할 PDF 파일이 없습니다.")


if __name__ == "__main__":
    main()