import os
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, Slot
from app.models.detection_model import DetectionItem

class HomonymCard(QFrame):
    """
    동명이인 개별 검수 항목을 카드 레이아웃으로 렌더링하는 위젯
    """
    def __init__(self, item: DetectionItem, parent=None, on_changed_callback=None):
        super().__init__(parent)
        self.item = item
        self.on_changed_callback = on_changed_callback
        self.is_checked = False # 검수 완료 여부 플래그
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        # 초기 카드 스타일 적용
        self.update_card_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # 1. ⚠ 아이콘과 원본 이름
        self.name_label = QLabel(f"⚠ <b>{self.item.original_value}</b>")
        self.name_label.setStyleSheet("color: #E65100; font-size: 10pt; font-family: 'Malgun Gothic';")
        layout.addWidget(self.name_label)
        
        # 2. 구역/시트 이름
        self.loc_label = QLabel(f"[{self.item.location_context}]")
        self.loc_label.setStyleSheet("color: #666666; font-size: 8.5pt;")
        self.loc_label.setToolTip(f"상세 위치: {self.item.location_detail}\n\n문맥 미리보기:\n{self.item.context_preview}")
        layout.addWidget(self.loc_label)
        
        # 3. 추천 신뢰도 및 등급 배지 라벨, 정보 아이콘 ⓘ
        conf_layout = QHBoxLayout()
        conf_layout.setContentsMargins(0, 0, 0, 0)
        conf_layout.setSpacing(4)
        
        self.conf_label = QLabel()
        self.conf_label.setStyleSheet("font-size: 8.5pt; font-family: 'Malgun Gothic';")
        conf_layout.addWidget(self.conf_label)
        
        self.info_icon = QLabel("ⓘ")
        self.info_icon.setStyleSheet("color: #757575; font-size: 9pt; font-weight: bold; cursor: help;")
        conf_layout.addWidget(self.info_icon)
        conf_layout.addStretch()
        
        self.update_confidence_ui()
        layout.addLayout(conf_layout)
        
        # 4. 대체 후보 콤보박스
        self.combo = QComboBox()
        self.combo.setMinimumWidth(160)
        self.combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #FFE082;
                border-radius: 4px;
                padding: 1px 5px;
                background-color: #FFFFFF;
                font-size: 9pt;
            }
        """)
        
        current_index = 0
        for c_idx, candidate in enumerate(self.item.candidates):
            if ":" in candidate:
                rep, info = candidate.split(":", 1)
            else:
                rep, info = candidate, "정보 없음"
            
            display_text = f"{rep} ({info})"
            self.combo.addItem(display_text, rep)
            
            if rep == self.item.replacement:
                current_index = c_idx
                
        self.combo.setCurrentIndex(current_index)
        self.combo.currentIndexChanged.connect(self.on_combo_changed)
        layout.addWidget(self.combo)

    def update_card_style(self):
        """검수 완료 상태에 따라 카드의 배경색 및 투명도를 변경합니다."""
        if self.is_checked:
            self.setStyleSheet("""
                HomonymCard {
                    background-color: #F5F5F5;
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                    color: #757575;
                }
            """)
        else:
            self.setStyleSheet("""
                HomonymCard {
                    background-color: #FFFDE6;
                    border: 1px solid #FFE082;
                    border-radius: 8px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)

    def update_confidence_ui(self):
        """추천 신뢰도 수치 및 등급을 계산하여 UI 라벨과 툴팁을 업데이트합니다."""
        confidence_pct = min(99, int(self.item.confidence * 100))
        
        if confidence_pct >= 90:
            rating_text = "🟢 매우 높음"
            rating_color = "#2E7D32"
        elif confidence_pct >= 70:
            rating_text = "🟡 높음"
            rating_color = "#EF6C00"
        else:
            rating_text = "🔴 낮음"
            rating_color = "#C62828"
            
        self.conf_label.setText(
            f"추천 신뢰도: <span style='color: {rating_color}; font-weight: bold;'>{confidence_pct}%</span> "
            f"<span style='color: {rating_color}; font-size: 8.5pt;'>({rating_text})</span>"
        )
        reason = self.item.ambiguity_reason if self.item.ambiguity_reason else "단서 없음"
        self.info_icon.setToolTip(f"추천 판정 근거:\n{reason}")

    def update_value(self, item: DetectionItem):
        """기존 카드 위젯 인스턴스를 유지하며 데이터만 업데이트 (스크롤 점프 방지)"""
        self.item = item
        self.combo.blockSignals(True)
        current_index = 0
        for c_idx in range(self.combo.count()):
            if self.combo.itemData(c_idx) == self.item.replacement:
                current_index = c_idx
                break
        self.combo.setCurrentIndex(current_index)
        self.combo.blockSignals(False)
        
        self.update_confidence_ui()
        self.update_card_style()

    def on_combo_changed(self, index):
        selected_rep = self.combo.itemData(index)
        self.is_checked = True # 콤보박스 조작 시 검수 완료로 마크
        self.update_card_style()
        if self.on_changed_callback:
            self.on_changed_callback(self.item.item_id, selected_rep)


class HomonymSummaryPanel(QWidget):
    """
    검수 필요 동명이인을 상단 가로 스크롤 카드 패널 형태로 보여주는 위젯
    """
    item_edited = Signal(str, str, object) # item_id, field_name, value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = {} # item_id -> HomonymCard
        self.init_ui()

    def init_ui(self):
        # 전체 레이아웃 (세로 구성: 타이틀 + 가로 스크롤 영역)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(6)
        
        # 타이틀
        self.title_label = QLabel("⚠ 수동 확인이 필요한 동명이인이 있습니다.")
        self.title_label.setStyleSheet("font-weight: bold; color: #E65100; font-size: 9.5pt;")
        layout.addWidget(self.title_label)
        
        # 가로 스크롤 영역
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setMaximumHeight(110)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QHBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)
        
        # 기본적으로는 가려둠
        self.setVisible(False)

    def populate_data(self, items: list[DetectionItem]):
        """탐지 데이터를 공급받아 동명이인 검수 카드들을 표시/갱신합니다."""
        # 동명이인 리스트 추출 (신뢰도 무관하게 모두 노출)
        homonyms = [item for item in items if item.is_ambiguous]
        
        # 추천 신뢰도가 낮은 순서(오름차순)로 정렬
        homonyms = sorted(homonyms, key=lambda x: x.confidence)
        
        if not homonyms:
            self.setVisible(False)
            # 기존 카드 정리
            for key in list(self.cards.keys()):
                card = self.cards.pop(key)
                self.scroll_layout.removeWidget(card)
                card.deleteLater()
            return
            
        self.setVisible(True)
        self.title_label.setText(f"⚠ 수동 확인이 필요한 동명이인이 총 {len(homonyms)}건 감지되었습니다.")
        
        # 스마트 갱신: 기존 카드 목록과 ID 및 순서가 완전히 동일하면 인스턴스를 유지 (정렬 순서 뒤바뀜 반영)
        current_ids = [item.item_id for item in homonyms]
        existing_ids = list(self.cards.keys())
        
        if current_ids == existing_ids:
            for item in homonyms:
                card = self.cards[item.item_id]
                card.update_value(item)
        else:
            # 싹 비우고 재생성
            while self.scroll_layout.count():
                layout_item = self.scroll_layout.takeAt(0)
                w = layout_item.widget()
                if w:
                    w.deleteLater()
            
            self.cards.clear()
            
            for item in homonyms:
                card = HomonymCard(item, on_changed_callback=self.on_card_changed)
                self.scroll_layout.addWidget(card)
                self.cards[item.item_id] = card
                
            self.scroll_layout.addStretch()

    def sync_replacement(self, item_id: str, new_rep: str):
        """특정 아이템의 가명 변경 사항을 상단 카드에 즉시 동기화 (시그널 루프 방지)"""
        if item_id in self.cards:
            card = self.cards[item_id]
            card.item.replacement = new_rep
            card.combo.blockSignals(True)
            current_index = 0
            for c_idx in range(card.combo.count()):
                if card.combo.itemData(c_idx) == new_rep:
                    current_index = c_idx
                    break
            card.combo.setCurrentIndex(current_index)
            card.combo.blockSignals(False)

    def on_card_changed(self, item_id: str, new_rep: str):
        # 드롭다운 변경 시그널 방출
        self.item_edited.emit(item_id, "replacement", new_rep)
