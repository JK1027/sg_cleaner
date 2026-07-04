from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class LoadingOverlay(QWidget):
    """
    작업 처리 중 전체 화면을 블로킹하고 로딩 메시지를 표시하는 반투명 오버레이 위젯.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # 레이아웃 구성
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # 메시지 라벨
        self.label_msg = QLabel("처리 중입니다...")
        self.label_msg.setAlignment(Qt.AlignCenter)
        self.label_msg.setStyleSheet("""
            QLabel {
                color: #1E88E5;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        # 서브 메시지
        self.label_sub = QLabel("잠시만 기다려 주세요.")
        self.label_sub.setAlignment(Qt.AlignCenter)
        self.label_sub.setStyleSheet("""
            QLabel {
                color: #64748B;
                font-size: 13px;
                background: transparent;
            }
        """)
        
        layout.addWidget(self.label_msg)
        layout.addWidget(self.label_sub)
        
        # 반투명 백색 배경 적용
        self.setStyleSheet("background-color: rgba(255, 255, 255, 200);")
        self.hide()
