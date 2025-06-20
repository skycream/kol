"""
PDF Checker 사용 예시
"""
from accuracy_calculator import AccuracyCalculator
from pdf_analyzer import PDFAnalyzer
import os


def example_basic_analysis():
    """기본 PDF 분석 예시"""
    print("=" * 60)
    print("1. 기본 PDF 분석")
    print("=" * 60)
    
    pdf_path = "../../test.pdf"  # 실제 PDF 파일 경로로 변경
    
    # PDF 분석
    analyzer = PDFAnalyzer(pdf_path)
    analysis = analyzer.get_comprehensive_analysis()
    
    print(f"PDF 유형: {analysis['pdf_type_analysis']['pdf_type']}")
    print(f"전체 품질 점수: {analysis['overall_quality_score']:.1f}/100")
    print("\n권장사항:")
    for rec in analysis['recommendations']:
        print(f"- {rec}")
    
    analyzer.close()


def example_accuracy_comparison():
    """텍스트 추출 정확도 비교 예시"""
    print("\n" + "=" * 60)
    print("2. 텍스트 추출 정확도 비교")
    print("=" * 60)
    
    pdf_path = "../../test.pdf"
    
    calculator = AccuracyCalculator()
    results = calculator.compare_extraction_methods(pdf_path)
    
    # 보고서 생성
    report = calculator.generate_report(results)
    print(report)


def example_reference_comparison():
    """참조 텍스트와 비교 예시"""
    print("\n" + "=" * 60)
    print("3. 참조 텍스트와 정확도 비교")
    print("=" * 60)
    
    pdf_path = "sample.pdf"
    reference_path = "sample_reference.txt"
    
    # 참조 파일이 있는 경우에만 실행
    if os.path.exists(pdf_path) and os.path.exists(reference_path):
        calculator = AccuracyCalculator()
        results = calculator.calculate_accuracy_with_reference(pdf_path, reference_path)
        
        # 보고서 생성
        report = calculator.generate_report(results)
        print(report)
    else:
        print("참조 파일이 없습니다. 실제 PDF와 참조 텍스트 파일을 준비해주세요.")


def example_batch_analysis():
    """여러 PDF 일괄 분석 예시"""
    print("\n" + "=" * 60)
    print("4. 여러 PDF 파일 일괄 분석")
    print("=" * 60)
    
    pdf_folder = "../../pdfs"  # PDF 파일들이 있는 폴더
    
    if os.path.exists(pdf_folder):
        calculator = AccuracyCalculator()
        results = calculator.batch_analyze(pdf_folder, "batch_analysis_results.json")
        
        print(f"\n총 {len(results)}개 파일 분석 완료")
        
        # 요약 통계
        successful = [r for r in results if "error" not in r]
        failed = [r for r in results if "error" in r]
        
        print(f"- 성공: {len(successful)}개")
        print(f"- 실패: {len(failed)}개")
        
        if successful:
            avg_quality = sum(r["pdf_analysis"]["overall_quality_score"] for r in successful) / len(successful)
            print(f"- 평균 품질 점수: {avg_quality:.1f}/100")
    else:
        print(f"폴더 {pdf_folder}가 존재하지 않습니다.")


def example_scanned_pdf_analysis():
    """스캔된 PDF 분석 예시"""
    print("\n" + "=" * 60)
    print("5. 스캔된 PDF 특별 분석")
    print("=" * 60)
    
    # 스캔된 PDF로 알려진 파일 사용
    scanned_pdfs = ["../../매각공고.pdf", "../../매각공고2.pdf"]
    
    for pdf_path in scanned_pdfs:
        if os.path.exists(pdf_path):
            print(f"\n분석 중: {os.path.basename(pdf_path)}")
            
            analyzer = PDFAnalyzer(pdf_path)
            analysis = analyzer.get_comprehensive_analysis()
            
            if analysis["pdf_type_analysis"]["is_ocr_needed"]:
                print("→ OCR이 필요한 스캔 문서입니다.")
                
                if analysis["image_quality_analysis"]:
                    img_quality = analysis["image_quality_analysis"]
                    print(f"  - 이미지 품질: {img_quality['overall_quality_score']:.1f}/100")
                    print(f"  - 해상도: {img_quality['dpi']} DPI")
                    print(f"  - 선명도: {img_quality['sharpness_score']:.1f}/100")
                    
                    if img_quality['skew_angle'] > 1:
                        print(f"  - ⚠️ 문서가 {img_quality['skew_angle']:.1f}도 기울어져 있습니다.")
            
            analyzer.close()


if __name__ == "__main__":
    print("PDF Checker 사용 예시\n")
    
    try:
        # 기본 분석
        example_basic_analysis()
        
        # 정확도 비교
        example_accuracy_comparison()
        
        # 참조 텍스트와 비교 (파일이 있는 경우)
        example_reference_comparison()
        
        # 일괄 분석 (폴더가 있는 경우)
        example_batch_analysis()
        
        # 스캔 PDF 분석
        example_scanned_pdf_analysis()
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        print("필요한 라이브러리가 설치되어 있는지 확인해주세요.")
        print("pip install -r requirements.txt")