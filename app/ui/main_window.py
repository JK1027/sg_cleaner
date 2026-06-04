import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QListWidget, QPlainTextEdit, QCheckBox,
    QComboBox, QFileDialog, QProgressBar, QMessageBox, QGroupBox, QSplitter,
    QLineEdit
)
from PySide6.QtCore import Qt, Slot
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
        
        pattern_layout.addWidget(QLabel("학생 이름 목록 (가명화):"), 0, 0)
        self.txt_students = QPlainTextEdit()
        self.txt_students.setPlaceholderText("예: 김민수, 이서연, 박철수")
        pattern_layout.addWidget(self.txt_students, 1, 0)
        
        pattern_layout.addWidget(QLabel("학교명 목록 (가명화):"), 0, 1)
        self.txt_schools = QPlainTextEdit()
        self.txt_schools.setPlaceholderText("예: 서울중학교, 한국중학교")
        pattern_layout.addWidget(self.txt_schools, 1, 1)

        pattern_layout.addWidget(QLabel("삭제할 단어 목록 (제거):"), 0, 2)
        self.txt_delete_keywords = QPlainTextEdit()
        self.txt_delete_keywords.setPlaceholderText("예: 삭제할단어1, 삭제할단어2")
        pattern_layout.addWidget(self.txt_delete_keywords, 1, 2)
        
        # 삭제 대체 텍스트 입력부
        delete_rep_layout = QHBoxLayout()
        delete_rep_layout.addWidget(QLabel("삭제 대체 텍스트:"))
        self.txt_delete_replacement = QLineEdit()
        self.txt_delete_replacement.setPlaceholderText("기본값: 공백")
        self.txt_delete_replacement.setText("")
        delete_rep_layout.addWidget(self.txt_delete_replacement)
        pattern_layout.addLayout(delete_rep_layout, 2, 2)
        
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
        pattern_layout.addLayout(opt_layout, 3, 0, 1, 3)
        
        # 탐지 실행 버튼 (QSS 커스텀 스타일 연동을 위한 objectName 설정)
        self.btn_run_detection = QPushButton("개인정보 자동 탐지 실행")
        self.btn_run_detection.setObjectName("btn_run_detection")
        pattern_layout.addWidget(self.btn_run_detection, 4, 0, 1, 3)
        
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
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "대상 문서 파일 선택", 
            "", 
            "All Supported Files (*.xlsx *.hwp *.hwpx);;Excel Files (*.xlsx);;Hangul Files (*.hwp *.hwpx)"
        )
        if files:
            # 파일 병합 로직은 Controller에 위임 (SoC 경계 유지)
            self.controller.add_files(files)

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
            
    def closeEvent(self, event):
        """창을 닫을 때 백그라운드 스레드가 실행 중이면 안전하게 취소 요청을 보냅니다."""
        if self.controller.state.is_processing:
            self.controller.cancel_processing()
            logger.info("창 닫기 감지: 실행 중인 작업을 정상 취소 완료했습니다.")
        event.accept()
