#!/bin/bash

echo "PDF Checker 필수 라이브러리 설치 중..."
echo "=================================="

# 필수 라이브러리 설치
pip install PyMuPDF
pip install pytesseract
pip install opencv-python
pip install numpy
pip install Pillow
pip install python-Levenshtein

echo ""
echo "설치 완료!"
echo "이제 다음 명령어로 실행하세요:"
echo "python simple_pdf_checker.py test2.pdf"