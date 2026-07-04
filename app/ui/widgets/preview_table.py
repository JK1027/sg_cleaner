from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QCheckBox, QHBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal
from app.models.detection_model import DetectionItem
from app.utils.logger import logger

class PreviewTable(QTableWidget):
    """
    개인정보 자동 탐지 결과를 표시하고 사용자가 검수(승인 토글 및 텍스트 수정)할 수 있는 테이블 위젯.
    """
    # 사용자가 행 데이터 수정 시 발생하는 시그널 (row_index, column_name, new_value)
    item_edited = Signal(str, str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = ["구역/시트", "상세 위치", "문맥 미리보기", "원본 텍스트", "변경 예정", "적용 여부"]
        self.init_ui()

    def init_ui(self):
        """테이블 기본 헤더 및 정렬 속성 설정"""
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        
        # 테이블 행동 규칙 설정
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(False)
        self.setColumnWidth(0, 100) # 구역/시트
        self.setColumnWidth(1, 80)  # 상세 위치
        self.setColumnWidth(2, 280) # 문맥 미리보기
        self.setColumnWidth(3, 200) # 원본 텍스트
        self.setColumnWidth(4, 120) # 변경 예정
        self.setColumnWidth(5, 80)  # 적용 여부
        
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
            
            # 1. 구역/시트명 (수정 불가)
            context_item = QTableWidgetItem(item.location_context)
            context_item.setFlags(context_item.flags() & ~Qt.ItemIsEditable)
            context_item.setData(Qt.UserRole, item.item_id) # 고유 ID 바인딩
            self.setItem(idx, 0, context_item)
            
            # 2. 상세 위치 (수정 불가)
            detail_item = QTableWidgetItem(item.location_detail)
            detail_item.setFlags(detail_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(idx, 1, detail_item)
            
            # 3. 문맥 미리보기 (수정 불가)
            preview_item = QTableWidgetItem(item.context_preview)
            preview_item.setFlags(preview_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(idx, 2, preview_item)
            
            # 4. 원본 내용 (수정 불가)
            orig_item = QTableWidgetItem(item.original_value)
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(idx, 3, orig_item)
            
            # 5. 대체될 텍스트 (사용자 직접 수정 가능)
            rep_item = QTableWidgetItem(item.replacement)
            rep_item.setFlags(rep_item.flags() | Qt.ItemIsEditable)
            self.setItem(idx, 4, rep_item)
            
            # 6. 적용 여부 체크박스 (레이아웃 중앙 배치)
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
            
            self.setCellWidget(idx, 5, cell_widget)
            
        self.blockSignals(False)
 
    def on_cell_changed(self, item: QTableWidgetItem):
        """테이블 셀 텍스트가 수동 수정되었을 때 실행"""
        row = item.row()
        col = item.column()
        
        if col == 4: # '변경 예정' 컬럼 수정 시 (헤더 추가로 인덱스 3 -> 4)
            new_text = item.text()
            # 0번 컬럼 아이템에서 item_id를 읽어옴
            context_item = self.item(row, 0)
            if context_item:
                item_id = context_item.data(Qt.UserRole)
                self.item_edited.emit(item_id, "replacement", new_text)
                logger.debug(f"테이블 수동 수정 반영 요청 - ID {item_id}: {new_text}")
 
    def on_checkbox_widget_toggled(self, checked: bool):
        """적용 여부 체크박스가 토글되었을 때 실행"""
        checkbox = self.sender()
        if checkbox:
            item_id = checkbox.property("item_id")
            self.item_edited.emit(item_id, "approved", checked)
            logger.debug(f"테이블 체크박스 토글 반영 요청 - ID {item_id}: {checked}")
