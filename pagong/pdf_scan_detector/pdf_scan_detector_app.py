"""
PDF 스캔본 판별기 - macOS 데스크톱 앱
드래그 앤 드롭으로 PDF의 스캔 여부를 판별합니다.
"""
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QFileDialog,
                            QTextEdit, QGroupBox, QGridLayout, QProgressBar,
                            QListWidget, QListWidgetItem, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QPalette, QColor, QIcon
import fitz
import warnings

# pdf_checker 모듈 import
from pdf_checker.if_ocr import PDFOCRDetector
from pdf_checker.pdf_metadata_analyzer import PDFMetadataAnalyzer

# MuPDF 경고 억제
warnings.filterwarnings("ignore")
fitz.TOOLS.mupdf_display_errors(False)


class PDFAnalyzerThread(QThread):
    """PDF 분석을 별도 스레드에서 수행"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, pdf_path):
        super().__init__()
        self.pdf_path = pdf_path
        self.ocr_detector = PDFOCRDetector()
        self.metadata_analyzer = PDFMetadataAnalyzer()
    
    def run(self):
        try:
            self.progress.emit("PDF 파일을 열고 있습니다...")
            
            # OCR 필요성 판별
            self.progress.emit("OCR 필요성을 분석하고 있습니다...")
            ocr_result = self.ocr_detector.analyze(self.pdf_path)
            
            # 메타데이터 분석
            self.progress.emit("메타데이터를 분석하고 있습니다...")
            metadata_result = self.metadata_analyzer.analyze_metadata(self.pdf_path)
            
            # 결과 정리
            result = {
                'success': True,
                'filename': os.path.basename(self.pdf_path),
                'filepath': self.pdf_path,
                'needs_ocr': ocr_result.needs_ocr,
                'pdf_type': ocr_result.pdf_type,
                'confidence': ocr_result.confidence,
                'scan_score': metadata_result['scan_score']['total_score'],
                'is_scanned': metadata_result['is_likely_scanned'],
                
                # 상세 정보
                'total_pages': ocr_result.total_pages,
                'text_pages': ocr_result.text_pages,
                'image_pages': ocr_result.image_pages,
                
                # Producer 정보
                'producer': metadata_result['producer_analysis']['producer'] or '없음',
                'creator': metadata_result['producer_analysis']['creator'] or '없음',
                'producer_type': metadata_result['producer_analysis']['producer_type'],
                
                # 판단 근거
                'reasons': ocr_result.reasons,
                'recommendations': ocr_result.recommendations,
                
                # 폰트 정보
                'has_fonts': metadata_result['font_analysis']['has_fonts'],
                'font_count': metadata_result['font_analysis']['unique_font_count'],
                
                # 텍스트 정보
                'avg_text_per_page': int(metadata_result['page_analysis']['avg_text_per_page'])
            }
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class DropArea(QLabel):
    """드래그 앤 드롭 영역"""
    fileDropped = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 3px dashed #aaa;
                border-radius: 20px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 18px;
                padding: 40px;
            }
            QLabel:hover {
                border-color: #667eea;
                background-color: #f0f4ff;
            }
        """)
        self.setText("PDF 파일을 여기에 드래그하세요\n또는 클릭하여 선택")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def mousePressEvent(self, event):
        """클릭 시 파일 선택 다이얼로그"""
        if event.button() == Qt.MouseButton.LeftButton:
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "PDF 파일 선택", 
                "", 
                "PDF Files (*.pdf)"
            )
            if file_path:
                self.fileDropped.emit(file_path)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    border: 3px dashed #667eea;
                    border-radius: 20px;
                    background-color: #e6f0ff;
                    color: #667eea;
                    font-size: 18px;
                    padding: 40px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                border: 3px dashed #aaa;
                border-radius: 20px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 18px;
                padding: 40px;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files and files[0].lower().endswith('.pdf'):
            self.fileDropped.emit(files[0])
        self.dragLeaveEvent(event)


class PDFScanDetectorApp(QMainWindow):
    """메인 애플리케이션 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.analyzer_thread = None
        self.analysis_history = []
        self.initUI()
        
    def initUI(self):
        """UI 초기화"""
        self.setWindowTitle("PDF 스캔본 판별기")
        self.setGeometry(100, 100, 1000, 700)
        
        # 메인 위젯
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 메인 레이아웃
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 헤더
        header = QLabel("📄 PDF 스캔본 판별기")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #333;
                padding: 10px;
            }
        """)
        layout.addWidget(header)
        
        # 설명
        desc = QLabel("PDF 파일이 스캔된 문서인지 디지털 문서인지 판별합니다")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("font-size: 14px; color: #666; padding-bottom: 10px;")
        layout.addWidget(desc)
        
        # 드롭 영역
        self.drop_area = DropArea()
        self.drop_area.fileDropped.connect(self.analyze_pdf)
        layout.addWidget(self.drop_area)
        
        # 프로그레스 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 프로그레스 라벨
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        
        # Splitter로 결과와 히스토리 분리
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 결과 영역
        self.result_widget = self.create_result_widget()
        self.result_widget.setVisible(False)
        splitter.addWidget(self.result_widget)
        
        # 히스토리 영역
        history_widget = self.create_history_widget()
        splitter.addWidget(history_widget)
        
        # Splitter 비율 설정 (7:3)
        splitter.setSizes([700, 300])
        layout.addWidget(splitter)
        
        # 스타일 적용
        self.setStyleSheet("""
            QMainWindow {
                background-color: #fff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
    
    def create_result_widget(self):
        """결과 표시 위젯 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 판정 결과
        self.verdict_label = QLabel()
        self.verdict_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verdict_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(self.verdict_label)
        
        # 상세 정보 그룹
        details_group = QGroupBox("상세 정보")
        details_layout = QGridLayout()
        
        self.details_labels = {}
        details_items = [
            ('파일명', 'filename'),
            ('PDF 유형', 'pdf_type'),
            ('신뢰도', 'confidence'),
            ('스캔 점수', 'scan_score'),
            ('총 페이지', 'total_pages'),
            ('텍스트 페이지', 'text_pages'),
            ('이미지 페이지', 'image_pages'),
            ('평균 텍스트', 'avg_text_per_page'),
            ('Producer', 'producer'),
            ('Creator', 'creator'),
            ('폰트 존재', 'has_fonts'),
            ('폰트 개수', 'font_count')
        ]
        
        for i, (label, key) in enumerate(details_items):
            row = i // 2
            col = (i % 2) * 2
            
            label_widget = QLabel(f"{label}:")
            label_widget.setStyleSheet("font-weight: normal; color: #666;")
            details_layout.addWidget(label_widget, row, col)
            
            value_widget = QLabel("")
            value_widget.setStyleSheet("font-weight: bold;")
            self.details_labels[key] = value_widget
            details_layout.addWidget(value_widget, row, col + 1)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # 판단 근거
        self.reasons_text = QTextEdit()
        self.reasons_text.setReadOnly(True)
        self.reasons_text.setMaximumHeight(150)
        reasons_group = QGroupBox("판단 근거 및 권장사항")
        reasons_layout = QVBoxLayout()
        reasons_layout.addWidget(self.reasons_text)
        reasons_group.setLayout(reasons_layout)
        layout.addWidget(reasons_group)
        
        return widget
    
    def create_history_widget(self):
        """히스토리 위젯 생성"""
        widget = QGroupBox("분석 기록")
        layout = QVBoxLayout()
        
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e6f0ff;
            }
        """)
        self.history_list.itemClicked.connect(self.on_history_item_clicked)
        
        layout.addWidget(self.history_list)
        
        # 히스토리 클리어 버튼
        clear_btn = QPushButton("기록 지우기")
        clear_btn.clicked.connect(self.clear_history)
        layout.addWidget(clear_btn)
        
        widget.setLayout(layout)
        return widget
    
    def analyze_pdf(self, file_path):
        """PDF 분석 시작"""
        # UI 상태 변경
        self.drop_area.setVisible(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.result_widget.setVisible(False)
        
        # 프로그레스 바 애니메이션
        self.progress_bar.setRange(0, 0)  # 무한 진행
        
        # 분석 스레드 시작
        self.analyzer_thread = PDFAnalyzerThread(file_path)
        self.analyzer_thread.progress.connect(self.update_progress)
        self.analyzer_thread.finished.connect(self.show_results)
        self.analyzer_thread.error.connect(self.show_error)
        self.analyzer_thread.start()
    
    def update_progress(self, message):
        """진행 상태 업데이트"""
        self.progress_label.setText(message)
    
    def show_results(self, result):
        """분석 결과 표시"""
        # UI 복원
        self.drop_area.setVisible(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.result_widget.setVisible(True)
        
        # 판정 결과 표시
        if result['is_scanned']:
            self.verdict_label.setText("📸 스캔된 문서입니다")
            self.verdict_label.setStyleSheet("""
                QLabel {
                    font-size: 24px;
                    font-weight: bold;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 10px;
                    background-color: #fee;
                    color: #c00;
                }
            """)
        else:
            self.verdict_label.setText("💻 디지털 문서입니다")
            self.verdict_label.setStyleSheet("""
                QLabel {
                    font-size: 24px;
                    font-weight: bold;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 10px;
                    background-color: #efe;
                    color: #060;
                }
            """)
        
        # 상세 정보 표시
        self.details_labels['filename'].setText(result['filename'])
        self.details_labels['pdf_type'].setText(result['pdf_type'])
        self.details_labels['confidence'].setText(f"{result['confidence']:.0%}")
        self.details_labels['scan_score'].setText(f"{result['scan_score']}/100")
        self.details_labels['total_pages'].setText(f"{result['total_pages']}페이지")
        self.details_labels['text_pages'].setText(f"{result['text_pages']}페이지")
        self.details_labels['image_pages'].setText(f"{result['image_pages']}페이지")
        self.details_labels['avg_text_per_page'].setText(f"{result['avg_text_per_page']}자")
        self.details_labels['producer'].setText(result['producer'])
        self.details_labels['creator'].setText(result['creator'])
        self.details_labels['has_fonts'].setText("예" if result['has_fonts'] else "아니오")
        self.details_labels['font_count'].setText(f"{result['font_count']}개")
        
        # 판단 근거 표시
        reasons_text = "📌 판단 근거:\n"
        for reason in result['reasons']:
            reasons_text += f"• {reason}\n"
        
        if result['recommendations']:
            reasons_text += "\n💡 권장사항:\n"
            for rec in result['recommendations']:
                reasons_text += f"• {rec}\n"
        
        self.reasons_text.setText(reasons_text)
        
        # 히스토리에 추가
        self.add_to_history(result)
    
    def show_error(self, error_msg):
        """에러 표시"""
        self.drop_area.setVisible(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        # 에러 메시지 표시
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "분석 오류", f"PDF 분석 중 오류가 발생했습니다:\n\n{error_msg}")
    
    def add_to_history(self, result):
        """히스토리에 추가"""
        self.analysis_history.insert(0, result)
        
        # 리스트 위젯에 추가
        item_text = f"{'🔴' if result['is_scanned'] else '🟢'} {result['filename']}"
        item = QListWidgetItem(item_text)
        item.setData(Qt.ItemDataRole.UserRole, result)
        self.history_list.insertItem(0, item)
        
        # 최대 20개까지만 유지
        if self.history_list.count() > 20:
            self.history_list.takeItem(20)
            self.analysis_history.pop()
    
    def on_history_item_clicked(self, item):
        """히스토리 아이템 클릭 시"""
        result = item.data(Qt.ItemDataRole.UserRole)
        if result:
            self.show_results(result)
    
    def clear_history(self):
        """히스토리 초기화"""
        self.history_list.clear()
        self.analysis_history.clear()


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # macOS 다크 모드 지원
    app.setStyle('Fusion')
    
    # 앱 아이콘 설정 (있는 경우)
    # app.setWindowIcon(QIcon('icon.png'))
    
    window = PDFScanDetectorApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()