from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QCheckBox, QHBoxLayout, QWidget, QComboBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
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
        self.setColumnWidth(4, 220) # 변경 예정
        self.setColumnWidth(5, 80)  # 적용 여부
        
        # 행 높이 설정 (콤보박스 수직 잘림 방지 및 여유 공간 확보)
        self.verticalHeader().setDefaultSectionSize(34)
        
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
            
            # 행별 배경색 지정 (동명이인 중 신뢰도 낮은 경우 연한 노란색)
            is_warning = item.is_ambiguous and item.confidence < 0.8
            row_color = QColor(255, 253, 220) if is_warning else None
            
            # 1. 구역/시트명 (수정 불가)
            context_item = QTableWidgetItem(item.location_context)
            context_item.setFlags(context_item.flags() & ~Qt.ItemIsEditable)
            context_item.setData(Qt.UserRole, item.item_id) # 고유 ID 바인딩
            if row_color:
                context_item.setBackground(row_color)
            self.setItem(idx, 0, context_item)
            
            # 2. 상세 위치 (수정 불가)
            detail_item = QTableWidgetItem(item.location_detail)
            detail_item.setFlags(detail_item.flags() & ~Qt.ItemIsEditable)
            if row_color:
                detail_item.setBackground(row_color)
            self.setItem(idx, 1, detail_item)
            
            # 3. 문맥 미리보기 (수정 불가)
            preview_item = QTableWidgetItem(item.context_preview)
            preview_item.setFlags(preview_item.flags() & ~Qt.ItemIsEditable)
            preview_item.setToolTip(item.context_preview)
            if row_color:
                preview_item.setBackground(row_color)
            self.setItem(idx, 2, preview_item)
            
            # 4. 원본 내용 (수정 불가)
            orig_text = item.original_value
            if is_warning:
                orig_text = f"⚠ {orig_text}"
            orig_item = QTableWidgetItem(orig_text)
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemIsEditable)
            
            tooltip_text = item.original_value
            if item.is_ambiguous:
                tooltip_text = f"[동명이인 경고]\n신뢰도: {item.confidence * 100:.0f}%\n근거: {item.ambiguity_reason}\n\n{item.original_value}"
            orig_item.setToolTip(tooltip_text)
            
            if row_color:
                orig_item.setBackground(row_color)
            self.setItem(idx, 3, orig_item)
            
            # 5. 대체될 텍스트 (동명이인이면 QComboBox, 아니면 일반 에디터)
            if item.is_ambiguous:
                combo = QComboBox()
                current_index = 0
                for c_idx, candidate in enumerate(item.candidates):
                    if ":" in candidate:
                        rep, info = candidate.split(":", 1)
                    else:
                        rep, info = candidate, "정보 없음"
                    
                    display_text = f"{rep} ({info})"
                    combo.addItem(display_text, rep)
                    
                    if rep == item.replacement:
                        current_index = c_idx
                
                combo.setCurrentIndex(current_index)
                
                # 콤보박스 변경 시그널 연결 (수정 즉시 모델에 반영)
                combo.currentIndexChanged.connect(
                    lambda _, c=combo, i_id=item.item_id: self.on_combo_changed(i_id, c)
                )
                
                self.setCellWidget(idx, 4, combo)
                # 콤보박스 뒤에 QTableWidgetItem을 덧대어 배경색 처리 지원
                dummy_item = QTableWidgetItem()
                dummy_item.setFlags(dummy_item.flags() & ~Qt.ItemIsEditable)
                if row_color:
                    dummy_item.setBackground(row_color)
                self.setItem(idx, 4, dummy_item)
            else:
                rep_item = QTableWidgetItem(item.replacement)
                rep_item.setFlags(rep_item.flags() | Qt.ItemIsEditable)
                if row_color:
                    rep_item.setBackground(row_color)
                self.setItem(idx, 4, rep_item)
            
            # 6. 적용 여부 체크박스 (레이아웃 중앙 배치)
            checkbox = QCheckBox()
            checkbox.setChecked(item.approved)
            checkbox.setProperty("item_id", item.item_id) # 고유 ID 바인딩
            checkbox.toggled.connect(self.on_checkbox_widget_toggled)
            
            cell_widget = QWidget()
            if row_color:
                cell_widget.setStyleSheet(f"background-color: rgb({row_color.red()}, {row_color.green()}, {row_color.blue()});")
            layout = QHBoxLayout(cell_widget)
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            cell_widget.setLayout(layout)
            
            self.setCellWidget(idx, 5, cell_widget)
            
        self.blockSignals(False)
 
    def sync_replacement(self, item_id: str, new_rep: str):
        """특정 아이템의 가명 변경 사항을 테이블에 즉시 동기화 (시그널 루프 방지)"""
        for row in range(self.rowCount()):
            context_item = self.item(row, 0)
            if context_item and context_item.data(Qt.UserRole) == item_id:
                cell_widget = self.cellWidget(row, 4)
                if isinstance(cell_widget, QComboBox):
                    cell_widget.blockSignals(True)
                    current_index = 0
                    for c_idx in range(cell_widget.count()):
                        if cell_widget.itemData(c_idx) == new_rep:
                            current_index = c_idx
                            break
                    cell_widget.setCurrentIndex(current_index)
                    cell_widget.blockSignals(False)
                else:
                    rep_item = self.item(row, 4)
                    if rep_item:
                        self.blockSignals(True)
                        rep_item.setText(new_rep)
                        self.blockSignals(False)
                break

    def on_combo_changed(self, item_id: str, combo: QComboBox):
        """콤보박스 선택 변경 시 모델 갱신 시그널 발행"""
        selected_val = combo.currentData()
        self.item_edited.emit(item_id, "replacement", selected_val)
        logger.debug(f"테이블 콤보박스 수정 반영 요청 - ID {item_id}: {selected_val}")

    def on_cell_changed(self, item: QTableWidgetItem):
        """테이블 셀 텍스트가 수동 수정되었을 때 실행"""
        row = item.row()
        col = item.column()
        
        if col == 4: # '변경 예정' 컬럼 수정 시
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
