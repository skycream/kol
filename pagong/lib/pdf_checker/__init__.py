"""
PDF Checker - PDF 텍스트 인식률 측정 도구

이 모듈은 PDF 파일의 텍스트 추출 품질을 평가하고 
OCR 인식률을 정량적으로 측정합니다.
"""

from accuracy_calculator import AccuracyCalculator
from pdf_analyzer import PDFAnalyzer
from metrics import TextMetrics

__version__ = "0.1.0"
__all__ = ["AccuracyCalculator", "PDFAnalyzer", "TextMetrics"]