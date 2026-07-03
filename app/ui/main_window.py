import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QListWidget, QPlainTextEdit, QCheckBox,
    QComboBox, QFileDialog, QProgressBar, QMessageBox, QGroupBox, QSplitter,
    QLineEdit, QInputDialog
)
from PySide6.QtCore import Qt, Slot, QTimer
from app.controllers.app_controller import AppController
from app.ui.widgets.preview_table import PreviewTable
from app.utils.logger import logger

class MainWindow(QMainWindow):
    """
    생기부 개인정보 익명화 도구의 메인 UI 윈도우.
    UI 요소 배치 및 Controller와의 시그널 연동을 담당합니다.
    """
    def __init__(self, controller: AppController):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("생기부 개인정보 익명화 도구")
        self.resize(1100, 800)
        
        # 스레드 안전 트레이 알림 시그널 브로커 등록
        from app.utils.notification_helper import NotificationHelper
        NotificationHelper.initialize_broker(self)
        
        self.init_ui()
        self.connect_signals()
        
        # 드래프트 저장용 디바운싱 타이머 설정 (1.5초)
        self.draft_timer = QTimer(self)
        self.draft_timer.setSingleShot(True)
        self.draft_timer.timeout.connect(self.execute_draft_save)
        
        # 임시 저장본(draft)이 있다면 복원 시도
        self.controller.load_draft_to_inputs()
        
        # 프리셋 리스트 동기화
        self.update_preset_combo_list()
        
        # 최초 1회 화면 그리기
        self.on_state_changed()

    def init_ui(self):
        """기본 레이아웃 및 위젯 초기 생성 및 스타일 매핑"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃 패딩 최적화
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # 1. 파일 선택 및 옵션 구역 (상단 - 분할형으로 배치)
        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setChildrenCollapsible(False)
        
        # 1-A. 파일 선택 그룹
        file_group = QGroupBox("1. 대상 문서 파일 선택")
        file_layout = QVBoxLayout(file_group)
        file_layout.setContentsMargins(12, 18, 12, 12)
        
        self.file_list = QListWidget()
        
        btn_file_layout = QHBoxLayout()
        self.btn_add_files = QPushButton("파일 추가")
        self.btn_clear_files = QPushButton("전체 삭제")
        btn_file_layout.addWidget(self.btn_add_files)
        btn_file_layout.addWidget(self.btn_clear_files)
        
        file_layout.addWidget(self.file_list)
        file_layout.addLayout(btn_file_layout)
        top_splitter.addWidget(file_group)
        
        # 1-B. 패턴 및 옵션 입력 그룹
        pattern_group = QGroupBox("2. 탐지 키워드 및 대장 저장 옵션")
        pattern_layout = QGridLayout(pattern_group)
        pattern_layout.setContentsMargins(12, 18, 12, 12)
        pattern_layout.setSpacing(8)
        
        # 프리셋 관리 컨트롤 레이아웃 (최상단 배치)
        preset_bar_layout = QHBoxLayout()
        preset_bar_layout.setSpacing(6)
        
        preset_bar_layout.addWidget(QLabel("학생명 세트 (프리셋):"))
        self.combo_presets = QComboBox()
        self.combo_presets.setMinimumWidth(180)
        preset_bar_layout.addWidget(self.combo_presets)
        
        self.btn_new_preset = QPushButton("새 프리셋")
        self.btn_save_preset = QPushButton("저장")
        self.btn_clone_preset = QPushButton("복제")
        self.btn_delete_preset = QPushButton("삭제")
        
        preset_bar_layout.addWidget(self.btn_new_preset)
        preset_bar_layout.addWidget(self.btn_save_preset)
        preset_bar_layout.addWidget(self.btn_clone_preset)
        preset_bar_layout.addWidget(self.btn_delete_preset)
        preset_bar_layout.addStretch()
        
        pattern_layout.addLayout(preset_bar_layout, 0, 0, 1, 3)
        
        # 입력 위젯 및 라벨 (한 줄씩 하향 배치)
        pattern_layout.addWidget(QLabel("학생 이름 목록 (가명화):"), 1, 0)
        self.txt_students = QPlainTextEdit()
        self.txt_students.setPlaceholderText("예: 김민수, 이서연, 박철수")
        pattern_layout.addWidget(self.txt_students, 2, 0)
        
        pattern_layout.addWidget(QLabel("학교명 목록 (가명화):"), 1, 1)
        self.txt_schools = QPlainTextEdit()
        self.txt_schools.setPlaceholderText("예: 서울중학교, 한국중학교")
        pattern_layout.addWidget(self.txt_schools, 2, 1)
 
        pattern_layout.addWidget(QLabel("삭제할 단어 목록 (제거):"), 1, 2)
        self.txt_delete_keywords = QPlainTextEdit()
        self.txt_delete_keywords.setPlaceholderText("예: 삭제할단어1, 삭제할단어2")
        pattern_layout.addWidget(self.txt_delete_keywords, 2, 2)
        
        # 삭제 대체 텍스트 입력부
        delete_rep_layout = QHBoxLayout()
        delete_rep_layout.addWidget(QLabel("삭제 대체 텍스트:"))
        self.txt_delete_replacement = QLineEdit()
        self.txt_delete_replacement.setPlaceholderText("기본값: 공백")
        self.txt_delete_replacement.setText("")
        delete_rep_layout.addWidget(self.txt_delete_replacement)
        pattern_layout.addLayout(delete_rep_layout, 3, 2)
        
        # 옵션 영역
        opt_layout = QHBoxLayout()
        opt_layout.setSpacing(10)
        self.chk_save_mapping = QCheckBox("익명화 매핑 대장 저장")
        
        self.combo_mapping_fmt = QComboBox()
        self.combo_mapping_fmt.addItems(["CSV", "EXCEL"])
        self.combo_mapping_fmt.setEnabled(False)
        
        opt_layout.addWidget(self.chk_save_mapping)
        opt_layout.addWidget(self.combo_mapping_fmt)
        opt_layout.addStretch()
        pattern_layout.addLayout(opt_layout, 4, 0, 1, 3)
        
        # 탐지 실행 버튼 (QSS 커스텀 스타일 연동을 위한 objectName 설정)
        self.btn_run_detection = QPushButton("개인정보 자동 탐지 실행")
        self.btn_run_detection.setObjectName("btn_run_detection")
        pattern_layout.addWidget(self.btn_run_detection, 5, 0, 1, 3)
        
        top_splitter.addWidget(pattern_group)
        main_layout.addWidget(top_splitter, stretch=1)
        
        # 2. 결과 검수 구역 (중단)
        result_group = QGroupBox("3. 탐지 결과 검수 및 편집")
        result_layout = QVBoxLayout(result_group)
        result_layout.setContentsMargins(12, 18, 12, 12)
        
        self.preview_table = PreviewTable()
        result_layout.addWidget(self.preview_table)
        main_layout.addWidget(result_group, stretch=2)
        
        # 3. 제어 및 진행 표시 구역 (하단)
        control_layout = QHBoxLayout()
        control_layout.setSpacing(15)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        
        # 작업 취소 버튼 추가
        self.btn_cancel = QPushButton("작업 취소")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setVisible(False)
        
        # 저장 버튼 (QSS 커스텀 스타일 연동을 위한 objectName 설정)
        self.btn_save = QPushButton("익명화 결과 파일 최종 저장")
        self.btn_save.setObjectName("btn_save")
        
        control_layout.addWidget(self.progress_bar, stretch=1)
        control_layout.addWidget(self.btn_cancel)
        control_layout.addWidget(self.btn_save)
        main_layout.addLayout(control_layout)
        
        # 상태바 설정
        self.statusBar().showMessage("대기 중")

    def connect_signals(self):
        """위젯 액션 및 컨트롤러 시그널 연결"""
        # UI 액션 연결
        self.btn_add_files.clicked.connect(self.on_add_files_clicked)
        self.btn_clear_files.clicked.connect(self.on_clear_files_clicked)
        self.btn_run_detection.clicked.connect(self.on_run_detection_clicked)
        self.btn_save.clicked.connect(self.on_save_clicked)
        self.chk_save_mapping.toggled.connect(self.on_mapping_check_changed)
        self.combo_mapping_fmt.currentTextChanged.connect(self.on_mapping_format_changed)
        
        # 삭제 대체 설정 변경 시그널 연결
        self.txt_delete_replacement.textChanged.connect(self.on_delete_replacement_changed)
        
        # 프리셋 관련 UI 시그널 연결
        self.combo_presets.currentIndexChanged.connect(self.on_preset_selection_changed)
        self.btn_new_preset.clicked.connect(self.on_new_preset_clicked)
        self.btn_save_preset.clicked.connect(self.on_save_preset_clicked)
        self.btn_clone_preset.clicked.connect(self.on_clone_preset_clicked)
        self.btn_delete_preset.clicked.connect(self.on_delete_preset_clicked)
        
        # 임시 자동 저장 (Draft) 연동
        self.txt_students.textChanged.connect(self.trigger_draft_save)
        self.txt_schools.textChanged.connect(self.trigger_draft_save)
        self.txt_delete_keywords.textChanged.connect(self.trigger_draft_save)
        self.txt_delete_replacement.textChanged.connect(self.trigger_draft_save)
        
        # 컨트롤러 프리셋 로드 시그널 연결
        self.controller.preset_loaded.connect(self.on_preset_loaded_from_controller)
        
        # 테이블 내 수동 편집 중계
        self.preview_table.item_edited.connect(self.on_table_item_edited)
        
        # 취소 버튼 연결
        self.btn_cancel.clicked.connect(self.on_cancel_clicked)
        
        # 컨트롤러의 상태 피드백 구독
        self.controller.state_changed.connect(self.on_state_changed)
        self.controller.progress_changed.connect(self.on_progress_changed)
        self.controller.process_finished.connect(self.on_process_finished)

    # --- UI 이벤트 슬롯 ---
    def on_add_files_clicked(self):
        try:
            logger.info("파일 추가 다이얼로그 호출 시작.")
            files, _ = QFileDialog.getOpenFileNames(
                self, 
                "대상 문서 파일 선택", 
                "", 
                "All Supported Files (*.xlsx; *.hwp; *.hwpx);;Excel Files (*.xlsx);;Hangul Files (*.hwp *.hwpx)"
            )
            logger.info(f"파일 추가 다이얼로그 응답 수신 - 선택된 파일 수: {len(files) if files else 0}")
            if files:
                logger.debug(f"추가할 파일 리스트: {files}")
                # 파일 병합 로직은 Controller에 위임 (SoC 경계 유지)
                self.controller.add_files(files)
        except Exception as file_err:
            logger.error("파일 추가 과정 중 예외 발생", exc_info=True)
            QMessageBox.critical(self, "파일 선택 오류", f"파일을 불러오는 과정에서 오류가 발생했습니다:\n{str(file_err)}")

    def on_clear_files_clicked(self):
        self.controller.set_selected_files([])

    def on_mapping_check_changed(self, checked: bool):
        self.combo_mapping_fmt.setEnabled(checked)
        self.controller.update_save_options(checked, self.combo_mapping_fmt.currentText())

    def on_mapping_format_changed(self, format_text: str):
        self.controller.update_save_options(self.chk_save_mapping.isChecked(), format_text)

    def on_delete_replacement_changed(self, text: str):
        self.controller.update_delete_replacement(text)
        
    def on_run_detection_clicked(self):
        # 강제 포커스 해제하여 편집 중인 셀 값 적용 유도
        self.preview_table.clearFocus()
        
        students = self.txt_students.toPlainText().replace("\n", ",").split(",")
        schools = self.txt_schools.toPlainText().replace("\n", ",").split(",")
        delete_keywords = self.txt_delete_keywords.toPlainText().replace("\n", ",").split(",")
        
        self.controller.update_input_patterns(students, schools, delete_keywords)
        
        # 삭제 대체 텍스트 빈 값 경고 처리
        delete_rep = self.txt_delete_replacement.text()
        if self.controller.state.delete_keywords and not delete_rep:
            reply = QMessageBox.question(
                self, 
                "삭제 대체 텍스트 확인",
                "삭제 단어 목록이 입력되었으나 삭제 대체 텍스트가 비어 있습니다.\n"
                "선택한 삭제 단어들이 문서에서 완전히 제거(공백 처리)됩니다. 진행하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self.controller.update_delete_replacement(delete_rep)
        
        # 유효성 검사는 Controller에 위임 (SoC 경계 유지)
        if not self.controller.has_files():
            QMessageBox.warning(self, "입력 부족", "먼저 대상 문서 파일을 추가해주세요.")
            return
        if not self.controller.can_run_detection():
            QMessageBox.warning(self, "입력 부족", "탐지할 이름, 학교명 또는 삭제할 단어를 1개 이상 작성해주세요.")
            return
            
        self.controller.run_detection()

    def on_cancel_clicked(self):
        self.btn_cancel.setEnabled(False)
        self.statusBar().showMessage("취소 중... 잠시만 기다려주세요.")
        self.controller.cancel_processing()

    def on_table_item_edited(self, item_id: str, field_name: str, value: object):
        if field_name == "approved":
            self.controller.update_detection_approval(item_id, bool(value))
            # 전체 테이블 재지정 없이 저장 버튼 활성 상태만 동적으로 실시간 업데이트
            has_approved = any(item.approved for item in self.controller.state.detection_results_list)
            self.btn_save.setEnabled(not self.controller.state.is_processing and has_approved)
        elif field_name == "replacement":
            self.controller.update_replacement_text(item_id, str(value))

    def on_save_clicked(self):
        # 강제 포커스 해제하여 편집 중인 셀 값 적용 유도
        self.preview_table.clearFocus()
        
        # 저장 가능 여부 검사는 Controller에 위임 (SoC 경계 유지)
        if not self.controller.can_save():
            QMessageBox.warning(self, "저장 불가", "탐지된 결과가 없습니다. 먼저 탐지를 실행해주세요.")
            return
            
        # ⚠️ 3차 보완: HWP 직접 치환 건너뜀 및 계속 진행 가이드 제공
        has_hwp = any(f.lower().endswith(".hwp") for f in self.controller.state.selected_files_list)
        if has_hwp:
            reply = QMessageBox.question(
                self,
                "한글(.hwp) 파일 저장 제외 안내",
                "선택된 파일 중 한글(.hwp) 파일이 포함되어 있습니다.\n"
                "현재 한글(.hwp) 파일은 스캔만 지원하며, 안전한 치환 저장은 보류 상태입니다.\n\n"
                "한글(.hwp) 파일 저장은 건너뛰고 엑셀(.xlsx) 및 HWPX(.hwpx) 파일만 익명화하여 저장하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        output_dir = QFileDialog.getExistingDirectory(self, "저장할 대상 폴더 선택")
        if output_dir:
            self.controller.execute_anonymization(output_dir)

    # --- 컨트롤러 수신 슬롯 ---
    @Slot()
    def on_state_changed(self):
        """AppState 데이터 갱신에 따라 UI 컴포넌트 리프레시 및 입력 락 제어"""
        state = self.controller.state
        
        # 파일 리스트 리프레시
        self.file_list.clear()
        for f in state.selected_files_list:
            self.file_list.addItem(os.path.basename(f))
            
        # 테이블 데이터 리프레시 (스크롤 위치 백업 후 복원)
        scroll_val = self.preview_table.verticalScrollBar().value()
        self.preview_table.populate_data(state.detection_results_list)
        self.preview_table.verticalScrollBar().setValue(scroll_val)
        
        # ⚠️ UI 제어 상태 비활성화 제어 (처리 중일 때 입력 락 적용하여 오동작 예방)
        self.preview_table.setEnabled(not state.is_processing)
        self.btn_run_detection.setEnabled(not state.is_processing)
        
        # 저장 버튼 활성화 조건: 처리 중이 아니며, 최소 1개 이상 항목이 승인됨
        has_approved = any(item.approved for item in state.detection_results_list)
        self.btn_save.setEnabled(not state.is_processing and has_approved)
        
        # 진행 상태에 따라 취소 버튼 동적 제어
        self.btn_cancel.setVisible(state.is_processing)
        self.btn_cancel.setEnabled(state.is_processing)
        self.btn_add_files.setEnabled(not state.is_processing)
        self.btn_clear_files.setEnabled(not state.is_processing)
        self.txt_students.setEnabled(not state.is_processing)
        self.txt_schools.setEnabled(not state.is_processing)
        self.txt_delete_keywords.setEnabled(not state.is_processing)
        self.chk_save_mapping.setEnabled(not state.is_processing)
        self.combo_mapping_fmt.setEnabled(not state.is_processing and self.chk_save_mapping.isChecked())
        
        # 프리셋 위젯 동기화 및 제어
        self.update_preset_combo_list()
        self.combo_presets.setEnabled(not state.is_processing)
        self.btn_new_preset.setEnabled(not state.is_processing)
        self.btn_save_preset.setEnabled(not state.is_processing and bool(state.current_preset_id))
        self.btn_clone_preset.setEnabled(not state.is_processing and bool(state.current_preset_id))
        self.btn_delete_preset.setEnabled(not state.is_processing and bool(state.current_preset_id))

        # 신호 차단 후 상태 동기화
        self.txt_delete_replacement.blockSignals(True)
        self.txt_delete_replacement.setText(state.delete_replacement)
        self.txt_delete_replacement.blockSignals(False)
        
        self.txt_delete_replacement.setEnabled(not state.is_processing)

    @Slot(int, str)
    def on_progress_changed(self, percentage: int, message: str):
        """진행 바 및 상태바 메시지 갱신"""
        self.progress_bar.setVisible(percentage < 100)
        self.progress_bar.setValue(percentage)
        self.statusBar().showMessage(message)

    @Slot(bool, str)
    def on_process_finished(self, success: bool, msg: str):
        """최종 처리 완료 메시지 팝업 출력"""
        if success:
            QMessageBox.information(self, "완료", msg)
        else:
            QMessageBox.critical(self, "오류", msg)
            
    # --- 프리셋 관리 UI 이벤트 핸들러 및 슬롯 ---
    
    def update_preset_combo_list(self):
        """AppState의 프리셋 목록 정보를 기반으로 QComboBox 아이템을 실시간 동기화합니다."""
        preset_dict = self.controller.state.preset_dict
        current_id = self.controller.state.current_preset_id
        
        # UI 드롭다운 구성 요소를 사전 체크하여 변경이 필요할 때만 갱신 (무한루프/플리커링 방지)
        combo_items = {}
        for i in range(1, self.combo_presets.count()):
            combo_items[self.combo_presets.itemData(i)] = self.combo_presets.itemText(i)
            
        current_dict_items = {k: v.get("name", "") for k, v in preset_dict.items()}
        
        if combo_items != current_dict_items:
            self.combo_presets.blockSignals(True)
            self.combo_presets.clear()
            self.combo_presets.addItem("— 프리셋 선택 안 함 —", "")
            for file_id, info in preset_dict.items():
                self.combo_presets.addItem(info.get("name", "이름 없음"), file_id)
            self.combo_presets.blockSignals(False)
            
        # 선택 상태 설정
        self.combo_presets.blockSignals(True)
        active_index = 0
        for i in range(self.combo_presets.count()):
            if self.combo_presets.itemData(i) == current_id:
                active_index = i
                break
        self.combo_presets.setCurrentIndex(active_index)
        self.combo_presets.blockSignals(False)

    def on_preset_selection_changed(self, index: int):
        """콤보박스 선택 변경 시 호출되며, 덮어쓰기 여부를 확인한 후 프리셋을 로드합니다."""
        file_id = self.combo_presets.itemData(index)
        
        # 동일한 프리셋 선택 시 무시
        if file_id == self.controller.state.current_preset_id:
            return
            
        # 현재 입력 창에 데이터가 있는 상태에서 프리셋 변경을 하려고 할 때 덮어쓰기 경고 출력
        has_input = (
            self.txt_students.toPlainText().strip()
            or self.txt_schools.toPlainText().strip()
            or self.txt_delete_keywords.toPlainText().strip()
            or self.txt_delete_replacement.text().strip()
        )
        
        if has_input:
            reply = QMessageBox.question(
                self,
                "프리셋 변경 확인",
                "프리셋을 변경하면 현재 작성 중인 입력 내용이 유실됩니다. 계속하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                # 선택을 다시 이전 활성화된 프리셋으로 복원
                self.update_preset_combo_list()
                return
                
        self.controller.load_preset_to_inputs(file_id)

    def on_new_preset_clicked(self):
        """새 프리셋을 이름 중복 확인 후 생성합니다."""
        name, ok = QInputDialog.getText(self, "새 프리셋 생성", "새 프리셋 이름을 입력해 주세요:")
        if not ok or not name.strip():
            return
            
        display_name = name.strip()
        
        # 이름 중복 확인
        preset_dict = self.controller.state.preset_dict
        for file_id, info in preset_dict.items():
            if info.get("name") == display_name:
                QMessageBox.warning(self, "이름 중복", "이미 동일한 이름의 프리셋이 존재합니다.")
                return
                
        # 현재 화면의 입력값을 페이로드로 프리셋 생성
        payload = self._get_current_inputs_payload()
        new_id = self.controller.create_new_preset(display_name, payload)
        if new_id:
            self.statusBar().showMessage(f"새 프리셋 '{display_name}'이(가) 성공적으로 생성되었습니다.")

    def on_save_preset_clicked(self):
        """선택된 프리셋에 현재 입력값을 저장(덮어쓰기)합니다."""
        current_id = self.controller.state.current_preset_id
        if not current_id:
            return
            
        preset_dict = self.controller.state.preset_dict
        display_name = preset_dict.get(current_id, {}).get("name", "프리셋")
        
        payload = self._get_current_inputs_payload()
        self.controller.save_current_preset(current_id, display_name, payload)
        self.statusBar().showMessage(f"프리셋 '{display_name}'에 현재 변경 사항을 저장했습니다.")

    def on_clone_preset_clicked(self):
        """현재 선택된 프리셋을 기반으로 다른 이름을 가진 프리셋을 복제 생성합니다."""
        current_id = self.controller.state.current_preset_id
        if not current_id:
            return
            
        preset_dict = self.controller.state.preset_dict
        current_name = preset_dict.get(current_id, {}).get("name", "프리셋")
        default_suggest = f"{current_name} (복사본)"
        
        name, ok = QInputDialog.getText(
            self, 
            "프리셋 복제", 
            "복제할 새 프리셋 이름을 입력해 주세요:", 
            QLineEdit.Normal, 
            default_suggest
        )
        if not ok or not name.strip():
            return
            
        display_name = name.strip()
        
        # 이름 중복 확인
        for file_id, info in preset_dict.items():
            if info.get("name") == display_name:
                QMessageBox.warning(self, "이름 중복", "이미 동일한 이름의 프리셋이 존재합니다.")
                return
                
        payload = self._get_current_inputs_payload()
        new_id = self.controller.create_new_preset(display_name, payload)
        if new_id:
            self.statusBar().showMessage(f"프리셋 '{current_name}'을(를) '{display_name}'(으)로 복제 생성했습니다.")

    def on_delete_preset_clicked(self):
        """현재 선택된 프리셋을 삭제 승인 팝업 확인 후 물리 삭제합니다."""
        current_id = self.controller.state.current_preset_id
        if not current_id:
            return
            
        preset_dict = self.controller.state.preset_dict
        display_name = preset_dict.get(current_id, {}).get("name", "프리셋")
        
        reply = QMessageBox.question(
            self,
            "프리셋 삭제 확인",
            f"프리셋 '{display_name}'을(를) 정말 삭제하시겠습니까?\n삭제 후에는 데이터를 복구할 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.controller.delete_preset(current_id)
            self.statusBar().showMessage(f"프리셋 '{display_name}'이(가) 삭제되었습니다.")

    @Slot(list, list, list, str)
    def on_preset_loaded_from_controller(self, students: list, schools: list, deletes: list, replacement: str):
        """컨트롤러에서 프리셋 로드 완료 신호가 왔을 때 UI 입력창 값을 바인딩합니다."""
        self.txt_students.blockSignals(True)
        self.txt_schools.blockSignals(True)
        self.txt_delete_keywords.blockSignals(True)
        self.txt_delete_replacement.blockSignals(True)
        
        # 구분자는 , 기호로 조인하여 가독성을 높입니다.
        self.txt_students.setPlainText(", ".join(students))
        self.txt_schools.setPlainText(", ".join(schools))
        self.txt_delete_keywords.setPlainText(", ".join(deletes))
        self.txt_delete_replacement.setText(replacement)
        
        self.txt_students.blockSignals(False)
        self.txt_schools.blockSignals(False)
        self.txt_delete_keywords.blockSignals(False)
        self.txt_delete_replacement.blockSignals(False)
        
        # 빈 프리셋 여부에 따른 사용자 피드백 제공
        if not students and not schools and not deletes:
            self.statusBar().showMessage("안내: 이 프리셋에는 저장된 데이터가 없습니다.")
        else:
            self.statusBar().showMessage("프리셋 로드 완료.")

    def trigger_draft_save(self):
        """임시 자동 저장 타이머를 실행하고 프리셋 변경점(더티 체크)을 함께 업데이트합니다."""
        if self.controller.state.is_processing:
            return
            
        # 1. 프리셋 변경점 실시간 더티 감지 및 콤보박스 텍스트 업데이트
        self.check_and_update_dirty_indicator()
        
        # 2. 타이머 재구동 (1.5초 디바운스)
        self.draft_timer.stop()
        self.draft_timer.start(1500)

    def execute_draft_save(self):
        """디바운스 타이머 타임아웃 시 실제 디스크에 draft.json 쓰기를 수행합니다."""
        if self.controller.state.is_processing:
            return
        payload = self._get_current_inputs_payload()
        self.controller.save_draft(payload)

    def check_and_update_dirty_indicator(self):
        """현재 입력창 값과 활성화된 프리셋의 원본 정규화 데이터를 비교하여 수정 표시(*)를 동기화합니다."""
        current_id = self.controller.state.current_preset_id
        if not current_id:
            return
            
        preset_dict = self.controller.state.preset_dict
        info = preset_dict.get(current_id)
        if not info:
            return
            
        display_name = info.get("name", "")
        is_dirty = self._is_preset_dirty(current_id)
        
        # 콤보박스에 표시할 텍스트 결정
        expected_text = f"{display_name} *" if is_dirty else display_name
        
        # 콤보박스 내 해당 아이템의 텍스트가 다를 경우에만 교체 (플리커링 방지)
        for i in range(self.combo_presets.count()):
            if self.combo_presets.itemData(i) == current_id:
                if self.combo_presets.itemText(i) != expected_text:
                    self.combo_presets.blockSignals(True)
                    self.combo_presets.setItemText(i, expected_text)
                    # 현재 선택된 아이템의 텍스트라면 헤더 표시도 즉시 동기화
                    if self.combo_presets.currentIndex() == i:
                        self.combo_presets.setCurrentIndex(i)
                    self.combo_presets.blockSignals(False)
                break

    def _is_preset_dirty(self, file_id: str) -> bool:
        """
        불러온 프리셋 원본 리스트와 현재 입력창들의 정규화된 텍스트를 대조하여
        실제 변경 내용이 있는지 판단합니다. (앞뒤 공백 및 엔터 빈 줄 무시)
        """
        try:
            from app.services.preset_manager import PresetManager
            original = PresetManager.load_preset(file_id)
        except Exception:
            return False
            
        # 1. 원본 데이터 정규화
        orig_students = sorted([s.strip() for s in original.get("students", []) if s.strip()])
        orig_schools = sorted([s.strip() for s in original.get("schools", []) if s.strip()])
        orig_deletes = sorted([d.strip() for d in original.get("delete_keywords", []) if d.strip()])
        orig_rep = original.get("delete_replacement", "").strip()
        
        # 2. 현재 입력창 데이터 정규화
        curr_payload = self._get_current_inputs_payload()
        curr_students = sorted(curr_payload["students"])
        curr_schools = sorted(curr_payload["schools"])
        curr_deletes = sorted(curr_payload["delete_keywords"])
        curr_rep = curr_payload["delete_replacement"].strip()
        
        # 대소문자 및 리스트 값 비교
        return (
            orig_students != curr_students
            or orig_schools != curr_schools
            or orig_deletes != curr_deletes
            or orig_rep != curr_rep
        )

    def _get_current_inputs_payload(self) -> dict:
        """입력 필드 내용을 구조화된 딕셔너리로 추출합니다."""
        students = self.txt_students.toPlainText().replace("\n", ",").split(",")
        schools = self.txt_schools.toPlainText().replace("\n", ",").split(",")
        deletes = self.txt_delete_keywords.toPlainText().replace("\n", ",").split(",")
        replacement = self.txt_delete_replacement.text()
        
        return {
            "students": [s.strip() for s in students if s.strip()],
            "schools": [s.strip() for s in schools if s.strip()],
            "delete_keywords": [d.strip() for d in deletes if d.strip()],
            "delete_replacement": replacement
        }

    def closeEvent(self, event):
        """창을 닫을 때 백그라운드 스레드가 실행 중이면 안전하게 취소 요청을 보내며, 타이머에 계류된 드래프트를 즉시 강제 플러시합니다."""
        if self.controller.state.is_processing:
            self.controller.cancel_processing()
            logger.info("창 닫기 감지: 실행 중인 작업을 정상 취소 완료했습니다.")
            
        # 타이머가 실행 중이면 강제로 최종 임시 저장 수행
        if hasattr(self, "draft_timer") and self.draft_timer.isActive():
            self.draft_timer.stop()
            try:
                self.execute_draft_save()
                logger.info("창 닫기 감지: 대기 중이던 드래프트를 안전하게 강제 저장했습니다.")
            except Exception as e:
                logger.error(f"창 닫기 드래프트 강제 저장 중 실패 (무시하고 종료): {str(e)}")
                
        event.accept()
