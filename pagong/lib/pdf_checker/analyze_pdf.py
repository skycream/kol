#!/usr/bin/env python3
"""
PDF 분석 실행 스크립트
"""
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from accuracy_calculator import AccuracyCalculator
from pdf_analyzer import PDFAnalyzer


def analyze_pdf(pdf_path):
    """PDF 파일 분석 및 보고서 생성"""
    
    if not os.path.exists(pdf_path):
        print(f"오류: 파일을 찾을 수 없습니다 - {pdf_path}")
        return
    
    print("=" * 60)
    print(f"PDF 분석 중: {os.path.basename(pdf_path)}")
    print("=" * 60)
    
    # 1. PDF 품질 분석
    try:
        analyzer = PDFAnalyzer(pdf_path)
        analysis = analyzer.get_comprehensive_analysis()
        
        print(f"\n[PDF 정보]")
        pdf_info = analysis['pdf_type_analysis']
        print(f"- PDF 유형: {pdf_info['pdf_type']}")
        print(f"- 전체 페이지: {pdf_info['total_pages']}")
        print(f"- 텍스트 포함 페이지: {pdf_info['pages_with_text']}")
        print(f"- 이미지 포함 페이지: {pdf_info['pages_with_images']}")
        print(f"- OCR 필요 여부: {'예' if pdf_info['is_ocr_needed'] else '아니오'}")
        
        # 이미지 품질 정보
        if analysis['image_quality_analysis']:
            img_quality = analysis['image_quality_analysis']
            print(f"\n[이미지 품질 분석]")
            print(f"- 전체 품질 점수: {img_quality['overall_quality_score']:.1f}/100")
            print(f"- 선명도: {img_quality['sharpness_score']:.1f}/100")
            print(f"- 대비: {img_quality['contrast_score']:.1f}/100")
            print(f"- 노이즈 점수: {img_quality['noise_score']:.1f}/100")
            print(f"- 해상도: {img_quality['dpi']} DPI")
            
            if abs(img_quality['skew_angle']) > 0.5:
                print(f"- 기울어짐: {img_quality['skew_angle']:.1f}도")
        
        print(f"\n[종합 평가]")
        print(f"- 전체 품질 점수: {analysis['overall_quality_score']:.1f}/100")
        
        print(f"\n[권장사항]")
        for rec in analysis['recommendations']:
            print(f"- {rec}")
        
        analyzer.close()
        
    except Exception as e:
        print(f"PDF 분석 중 오류 발생: {e}")
        return
    
    # 2. 텍스트 추출 정확도 비교
    print("\n" + "=" * 60)
    print("텍스트 추출 방식 비교")
    print("=" * 60)
    
    try:
        calculator = AccuracyCalculator()
        
        # OCR이 필요한 경우 사용자에게 알림
        if pdf_info['is_ocr_needed']:
            print("\n⚠️  스캔된 문서로 판단됩니다. OCR 처리를 시작합니다...")
            print("(시간이 좀 걸릴 수 있습니다)")
        
        results = calculator.compare_extraction_methods(pdf_path)
        
        # 간단한 결과 출력
        for method, data in results["extraction_results"].items():
            print(f"\n[{method.upper()} 방식]")
            print(f"- 추출된 텍스트 길이: {data['text_length']:,} 문자")
            
            # 텍스트 미리보기
            preview = data['text_preview']
            if preview:
                print(f"- 텍스트 미리보기:")
                preview_lines = preview.split('\n')[:5]  # 처음 5줄만
                for line in preview_lines:
                    if line.strip():
                        print(f"  {line.strip()[:60]}{'...' if len(line.strip()) > 60 else ''}")
        
        print(f"\n[최종 권장사항]")
        print(f"→ {results['final_recommendation']}")
        
        # 상세 보고서를 파일로 저장
        report_filename = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_analysis_report.txt"
        report = calculator.generate_report(results)
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n✅ 상세 분석 보고서가 '{report_filename}'에 저장되었습니다.")
        
    except Exception as e:
        print(f"텍스트 추출 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 명령줄 인자 확인
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # 기본값: 새로 추가된 PDF 파일
        pdf_path = "2024하단104560 부동산 매각공고2.pdf"
    
    analyze_pdf(pdf_path)