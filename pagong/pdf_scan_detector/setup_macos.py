"""
macOS 앱 빌드를 위한 setup.py
py2app을 사용하여 .app 파일 생성
"""
from setuptools import setup, find_packages
import sys

# 앱 정보
APP = ['pdf_scan_detector_app.py']
APP_NAME = "PDF 스캔본 판별기"
VERSION = "1.0.0"

# 데이터 파일
DATA_FILES = []

# 옵션
OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,  # 아이콘 파일이 있으면 여기에 지정
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleGetInfoString': "PDF 스캔본 판별기 - PDF가 스캔 문서인지 확인",
        'CFBundleIdentifier': "com.pagong.pdfscandetector",
        'CFBundleVersion': VERSION,
        'CFBundleShortVersionString': VERSION,
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
        'NSRequiresAquaSystemAppearance': False,  # 다크 모드 지원
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'PDF Document',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': ['com.adobe.pdf'],
                'LSHandlerRank': 'Alternate'
            }
        ]
    },
    'packages': [
        'PyQt6', 
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'fitz',
        'pdf_checker'
    ],
    'includes': [
        'PyQt6.sip',
        'pdf_checker.if_ocr',
        'pdf_checker.pdf_metadata_analyzer'
    ],
    'excludes': [
        'matplotlib',
        'scipy',
        'pandas',
        'notebook',
        'jupyter',
        'pytest',
        'setuptools',
        'pip'
    ],
    'frameworks': [],
    'dylib_excludes': [],
    'semi_standalone': False,
    'site_packages': True,
}

# py2app 설정
setup(
    name=APP_NAME,
    version=VERSION,
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    packages=find_packages(),
)