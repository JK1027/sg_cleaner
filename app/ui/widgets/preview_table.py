from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QCheckBox, QHBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal
from app.models.detection_model import DetectionItem
from app.utils.logger import logger

class PreviewTable(QTableWidget):
    """
    개인정보 자동 탐지 결과를 표시하고 사용자가 검수(승인 토글 및 텍스트 수정)할 수 있는 테이블 위젯.
    """
    # 사용자가 행 데이터 수정 시 발생하는 시그널 (row_index, column_name, new_value)
    item_edited = Signal(int, str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = ["시트", "셀 위치", "원본 텍스트", "변경 예정", "적용 여부"]
        self.init_ui()

    def init_ui(self):
        """테이블 기본 헤더 및 정렬 속성 설정"""
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        
        # 테이블 행동 규칙 설정
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(False)
        self.setColumnWidth(0, 100) # 시트
        self.setColumnWidth(1, 80)  # 셀 위치
        self.setColumnWidth(2, 280) # 원본 텍스트
        self.setColumnWidth(3, 120) # 변경 예정
        self.setColumnWidth(4, 80)  # 적용 여부
        
        # 테이블 내 개별 수정 이벤트 연결
        self.itemChanged.connect(self.on_cell_changed)

    def populate_data(self, items: list[DetectionItem]):
        """
        AppState에서 수집한 탐지 데이터 목록을 받아 화면에 로드합니다.
        시그널 루프 방지를 위해 임시로 cell 변경 이벤트를 차단합니다.
        """
        self.blockSignals(True)
        self.setRowCount(0)
        
        for idx, item in enumerate(items):
            self.insertRow(idx)
            
            # 1. 시트명 (수정 불가)
            sheet_item = QTableWidgetItem(item.sheet_name)
            sheet_item.setFlags(sheet_item.flags() & ~Qt.ItemIsEditable)
            sheet_item.setData(Qt.UserRole, item.item_id) # 고유 ID 바인딩
            self.setItem(idx, 0, sheet_item)
            
            # 2. 셀 주소 (수정 불가)
            cell_item = QTableWidgetItem(item.cell_address)
            cell_item.setFlags(cell_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(idx, 1, cell_item)
            
            # 3. 원본 내용 (수정 불가)
            orig_item = QTableWidgetItem(item.original_value)
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(idx, 2, orig_item)
            
            # 4. 대체될 텍스트 (사용자 직접 수정 가능)
            rep_item = QTableWidgetItem(item.replacement)
            rep_item.setFlags(rep_item.flags() | Qt.ItemIsEditable)
            self.setItem(idx, 3, rep_item)
            
            # 5. 적용 여부 체크박스 (레이아웃 중앙 배치)
            checkbox = QCheckBox()
            checkbox.setChecked(item.approved)
            checkbox.setProperty("item_id", item.item_id) # 고유 ID 바인딩
            checkbox.toggled.connect(self.on_checkbox_widget_toggled)
            
            cell_widget = QWidget()
            layout = QHBoxLayout(cell_widget)
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            cell_widget.setLayout(layout)
            
            self.setCellWidget(idx, 4, cell_widget)
            
        self.blockSignals(False)
 
    def on_cell_changed(self, item: QTableWidgetItem):
        """테이블 셀 텍스트가 수동 수정되었을 때 실행"""
        row = item.row()
        col = item.column()
        
        if col == 3: # '변경 예정' 컬럼 수정 시
            new_text = item.text()
            # 0번 컬럼 아이템에서 item_id를 읽어옴
            sheet_item = self.item(row, 0)
            if sheet_item:
                item_id = sheet_item.data(Qt.UserRole)
                self.item_edited.emit(item_id, "replacement", new_text)
                logger.debug(f"테이블 수동 수정 반영 요청 - ID {item_id}: {new_text}")
 
    def on_checkbox_widget_toggled(self, checked: bool):
        """적용 여부 체크박스가 토글되었을 때 실행"""
        checkbox = self.sender()
        if checkbox:
            item_id = checkbox.property("item_id")
            self.item_edited.emit(item_id, "approved", checked)
            logger.debug(f"테이블 체크박스 토글 반영 요청 - ID {item_id}: {checked}")
