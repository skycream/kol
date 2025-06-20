"""
간단한 PyInstaller 빌드 스크립트
"""
import subprocess
import os
import shutil

# 이전 빌드 정리
if os.path.exists("build"):
    shutil.rmtree("build")
if os.path.exists("dist"):
    shutil.rmtree("dist")

# 필요한 모듈만 포함하는 간단한 spec 파일 생성
spec_content = '''# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['pdf_scan_detector_app.py'],
    pathex=['.', 'pdf_checker'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        'fitz',
        'pdf_checker',
        'pdf_checker.if_ocr',
        'pdf_checker.pdf_metadata_analyzer',
        'Levenshtein',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'sklearn',
        'torch',
        'tensorflow',
        'notebook',
        'jupyter',
        'PIL',
        'cv2',
        'sqlite3',
        'IPython',
        'cryptography',
        'PyYAML',
        'yaml',
        'certifi',
        'urllib3',
        'requests',
        'jinja2',
        'flask',
        'django',
        'pytest',
        'setuptools',
        'pip',
        'conda',
        'distributed',
        'h5py',
        'bokeh',
        'tornado',
        'zmq',
        'psutil',
        'cloudpickle',
        'dask',
        'msgpack',
        'fsspec',
        'partd',
        'locket',
        'toolz',
        'cytoolz',
        'numba',
        'llvmlite',
        'fastparquet',
        'pyarrow',
        's3fs',
        'gcsfs',
        'boto3',
        'botocore',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PDF 스캔본 판별기',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDF 스캔본 판별기',
)

app = BUNDLE(
    coll,
    name='PDF 스캔본 판별기.app',
    icon=None,
    bundle_identifier='com.pagong.pdfscandetector',
    info_plist={
        'CFBundleName': 'PDF 스캔본 판별기',
        'CFBundleDisplayName': 'PDF 스캔본 판별기',
        'CFBundleGetInfoString': 'PDF가 스캔 문서인지 확인',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
    },
)
'''

# spec 파일 작성
with open('pdf_scan_detector.spec', 'w') as f:
    f.write(spec_content)

print("🔧 PyInstaller로 PDF 스캔본 판별기 빌드 중...")
print("📝 커스텀 spec 파일 사용")
print("")

# PyInstaller 실행
result = subprocess.run(['pyinstaller', 'pdf_scan_detector.spec', '--clean'], capture_output=True, text=True)

if result.returncode == 0:
    print("✅ 빌드 성공!")
    print("📍 앱 위치: dist/PDF 스캔본 판별기.app")
    print("")
    print("🚀 실행하려면:")
    print("   open dist/PDF\\ 스캔본\\ 판별기.app")
else:
    print("❌ 빌드 실패!")
    print(result.stderr)