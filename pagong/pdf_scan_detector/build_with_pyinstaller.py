"""
PyInstaller를 사용한 macOS 앱 빌드 스크립트
"""
import PyInstaller.__main__
import os
import shutil

# 앱 정보
APP_NAME = "PDF 스캔본 판별기"
MAIN_SCRIPT = "pdf_scan_detector_app.py"

# 이전 빌드 정리
if os.path.exists("build"):
    shutil.rmtree("build")
if os.path.exists("dist"):
    shutil.rmtree("dist")

# PyInstaller 옵션
args = [
    MAIN_SCRIPT,
    '--name', APP_NAME,
    '--windowed',  # GUI 앱
    '--onefile',   # 단일 실행 파일
    '--clean',     # 클린 빌드
    '--noconfirm', # 확인 없이 진행
    
    # 아이콘 (있는 경우)
    # '--icon', 'icon.icns',
    
    # 포함할 모듈
    '--hidden-import', 'PyQt6',
    '--hidden-import', 'PyQt6.QtCore',
    '--hidden-import', 'PyQt6.QtGui',
    '--hidden-import', 'PyQt6.QtWidgets',
    '--hidden-import', 'PyQt6.sip',
    '--hidden-import', 'fitz',
    '--hidden-import', 'PyMuPDF',
    '--hidden-import', 'pdf_checker',
    '--hidden-import', 'pdf_checker.if_ocr',
    '--hidden-import', 'pdf_checker.pdf_metadata_analyzer',
    '--hidden-import', 'Levenshtein',
    
    # 추가 경로
    '--paths', '.',
    '--paths', 'pdf_checker',
    
    # macOS 특정 옵션
    '--osx-bundle-identifier', 'com.pagong.pdfscandetector',
    
    # 콘솔 로그 비활성화
    '--log-level', 'WARN',
]

print("🔧 PyInstaller로 PDF 스캔본 판별기 빌드 중...")
print("")

# PyInstaller 실행
PyInstaller.__main__.run(args)

print("")
print("✅ 빌드 완료!")
print(f"📍 실행 파일 위치: dist/{APP_NAME}")
print("")
print("🚀 실행하려면:")
print(f"   open dist/{APP_NAME}.app")