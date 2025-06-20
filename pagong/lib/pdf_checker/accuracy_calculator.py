"""
PDF 텍스트 추출 정확도 계산
"""
import os
from typing import Dict, Optional, Tuple, List
import json
from datetime import datetime
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from metrics import TextMetrics
from pdf_analyzer import PDFAnalyzer


class AccuracyCalculator:
    """PDF 텍스트 추출 정확도를 계산하는 메인 클래스"""
    
    def __init__(self):
        self.metrics = TextMetrics()
    
    def extract_text_pymupdf(self, pdf_path: str) -> str:
        """PyMuPDF를 사용한 텍스트 추출"""
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    
    def extract_text_ocr(self, pdf_path: str, lang: str = 'kor+eng') -> str:
        """OCR을 사용한 텍스트 추출"""
        images = convert_from_path(pdf_path)
        text = ""
        
        for i, image in enumerate(images):
            # Tesseract OCR 수행
            page_text = pytesseract.image_to_string(image, lang=lang)
            text += page_text + "\n"
        
        return text
    
    def compare_extraction_methods(self, pdf_path: str, ground_truth: Optional[str] = None) -> Dict[str, any]:
        """
        여러 추출 방법의 정확도 비교
        
        Args:
            pdf_path: PDF 파일 경로
            ground_truth: 정답 텍스트 (없으면 OCR 결과를 기준으로 함)
        """
        # PDF 분석
        analyzer = PDFAnalyzer(pdf_path)
        pdf_analysis = analyzer.get_comprehensive_analysis()
        analyzer.close()
        
        # 텍스트 추출
        pymupdf_text = self.extract_text_pymupdf(pdf_path)
        
        # 스캔본이거나 텍스트가 거의 없는 경우 OCR 수행
        ocr_text = ""
        if pdf_analysis["pdf_type_analysis"]["is_ocr_needed"] or len(pymupdf_text.strip()) < 100:
            print("OCR 처리 중...")
            ocr_text = self.extract_text_ocr(pdf_path)
        
        # Ground truth 설정
        if ground_truth is None:
            # Ground truth가 없으면 더 많은 텍스트를 추출한 것을 기준으로 함
            ground_truth = ocr_text if len(ocr_text) > len(pymupdf_text) else pymupdf_text
        
        # 메트릭 계산
        results = {
            "pdf_analysis": pdf_analysis,
            "extraction_results": {
                "pymupdf": {
                    "text_length": len(pymupdf_text),
                    "text_preview": pymupdf_text[:200] + "..." if len(pymupdf_text) > 200 else pymupdf_text
                }
            }
        }
        
        # PyMuPDF 메트릭
        if ground_truth and pymupdf_text:
            results["extraction_results"]["pymupdf"]["metrics"] = self.metrics.detailed_metrics(
                ground_truth, pymupdf_text
            )
            results["extraction_results"]["pymupdf"]["error_analysis"] = self.metrics.analyze_errors(
                ground_truth, pymupdf_text
            )
        
        # OCR 메트릭 (수행된 경우)
        if ocr_text:
            results["extraction_results"]["ocr"] = {
                "text_length": len(ocr_text),
                "text_preview": ocr_text[:200] + "..." if len(ocr_text) > 200 else ocr_text
            }
            
            if ground_truth:
                results["extraction_results"]["ocr"]["metrics"] = self.metrics.detailed_metrics(
                    ground_truth, ocr_text
                )
                results["extraction_results"]["ocr"]["error_analysis"] = self.metrics.analyze_errors(
                    ground_truth, ocr_text
                )
        
        # 최종 권장사항
        results["final_recommendation"] = self._generate_final_recommendation(results)
        
        return results
    
    def _generate_final_recommendation(self, results: Dict) -> str:
        """분석 결과를 바탕으로 최종 권장사항 생성"""
        pdf_type = results["pdf_analysis"]["pdf_type_analysis"]["pdf_type"]
        
        if pdf_type == "scanned":
            return "스캔 문서입니다. OCR 처리가 필수적입니다."
        elif pdf_type == "searchable":
            pymupdf_accuracy = results["extraction_results"]["pymupdf"].get("metrics", {}).get("accuracy_score", 0)
            if pymupdf_accuracy > 95:
                return "텍스트 기반 PDF입니다. PyMuPDF 추출이 충분히 정확합니다."
            else:
                return "텍스트 기반 PDF이지만 추출 정확도가 낮습니다. 문서 구조 확인이 필요합니다."
        else:  # mixed
            return "혼합형 문서입니다. 텍스트 부분은 직접 추출, 이미지 부분은 OCR 처리를 권장합니다."
    
    def calculate_accuracy_with_reference(self, pdf_path: str, reference_text_path: str) -> Dict[str, any]:
        """
        참조 텍스트 파일과 비교하여 정확도 계산
        
        Args:
            pdf_path: PDF 파일 경로
            reference_text_path: 정답 텍스트 파일 경로
        """
        # 참조 텍스트 읽기
        with open(reference_text_path, 'r', encoding='utf-8') as f:
            reference_text = f.read()
        
        # 정확도 계산
        results = self.compare_extraction_methods(pdf_path, reference_text)
        
        # 구조적 정확도 추가
        for method in results["extraction_results"]:
            if "metrics" in results["extraction_results"][method]:
                extracted_text = self.extract_text_pymupdf(pdf_path) if method == "pymupdf" else self.extract_text_ocr(pdf_path)
                structural_metrics = self.metrics.structural_accuracy(reference_text, extracted_text)
                results["extraction_results"][method]["structural_metrics"] = structural_metrics
        
        return results
    
    def batch_analyze(self, pdf_folder: str, output_file: str = None) -> List[Dict]:
        """
        폴더 내 모든 PDF 파일 일괄 분석
        
        Args:
            pdf_folder: PDF 파일들이 있는 폴더 경로
            output_file: 결과를 저장할 JSON 파일 경로
        """
        results = []
        
        for filename in os.listdir(pdf_folder):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(pdf_folder, filename)
                print(f"분석 중: {filename}")
                
                try:
                    result = self.compare_extraction_methods(pdf_path)
                    result["filename"] = filename
                    result["timestamp"] = datetime.now().isoformat()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "filename": filename,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
        
        # 결과 저장
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"결과가 {output_file}에 저장되었습니다.")
        
        return results
    
    def generate_report(self, analysis_results: Dict) -> str:
        """
        분석 결과를 읽기 쉬운 보고서 형식으로 변환
        """
        report = []
        report.append("=" * 60)
        report.append("PDF 텍스트 인식률 분석 보고서")
        report.append("=" * 60)
        
        # PDF 유형 정보
        pdf_info = analysis_results["pdf_analysis"]["pdf_type_analysis"]
        report.append(f"\n[PDF 정보]")
        report.append(f"- 문서 유형: {pdf_info['pdf_type']}")
        report.append(f"- 전체 페이지: {pdf_info['total_pages']}")
        report.append(f"- 텍스트 포함 페이지: {pdf_info['pages_with_text']}")
        report.append(f"- 이미지 포함 페이지: {pdf_info['pages_with_images']}")
        
        # 이미지 품질 (있는 경우)
        if analysis_results["pdf_analysis"]["image_quality_analysis"]:
            img_quality = analysis_results["pdf_analysis"]["image_quality_analysis"]
            report.append(f"\n[이미지 품질 분석]")
            report.append(f"- 전반적 품질 점수: {img_quality['overall_quality_score']:.1f}/100")
            report.append(f"- 선명도: {img_quality['sharpness_score']:.1f}/100")
            report.append(f"- 대비: {img_quality['contrast_score']:.1f}/100")
            report.append(f"- 해상도: {img_quality['dpi']} DPI")
            if abs(img_quality['skew_angle']) > 0.5:
                report.append(f"- 기울어짐: {img_quality['skew_angle']:.1f}도")
        
        # 텍스트 추출 결과
        report.append(f"\n[텍스트 추출 결과]")
        for method, data in analysis_results["extraction_results"].items():
            report.append(f"\n{method.upper()} 방식:")
            report.append(f"- 추출된 텍스트 길이: {data['text_length']} 문자")
            
            if "metrics" in data:
                metrics = data["metrics"]
                report.append(f"- 정확도 점수: {metrics['accuracy_score']:.1f}%")
                report.append(f"- 문자 정확도: {metrics['character_accuracy']:.1f}%")
                report.append(f"- 단어 정확도: {metrics['word_accuracy']:.1f}%")
                
                if "error_analysis" in data:
                    errors = data["error_analysis"]
                    report.append(f"- 총 오류 수: {errors['total_errors']}")
                    report.append(f"  - 대체: {errors['substitutions']}")
                    report.append(f"  - 삭제: {errors['deletions']}")
                    report.append(f"  - 삽입: {errors['insertions']}")
        
        # 권장사항
        report.append(f"\n[권장사항]")
        for rec in analysis_results["pdf_analysis"]["recommendations"]:
            report.append(f"- {rec}")
        
        report.append(f"\n[최종 권장사항]")
        report.append(f"- {analysis_results['final_recommendation']}")
        
        return "\n".join(report)