from PySide6.QtCore import QObject, Signal, Slot
from app.models.app_state import AppState
from app.services.worker import DetectionWorker, AnonymizeWorker
from app.utils.logger import logger

class AppController(QObject):
    """
    UI와 비즈니스 로직(Services)을 분리(SoC)하기 위한 중앙 제어기.
    백그라운드 비동기 스레드(QThread)를 시작하고 그 경과를 상태 객체(AppState)에 반영합니다.
    """
    # 상태 변경 알림 시그널 (UI 리렌더링 트리거)
    state_changed = Signal()
    # 진행률 업데이트 시그널 (수치 %, 메시지)
    progress_changed = Signal(int, str)
    # 작업 마무리 리포트 시그널 (성공여부, 안내 메시지)
    process_finished = Signal(bool, str)

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._detection_worker = None
        self._anonymize_worker = None
        logger.info("AppController가 초기화 및 실제 연동 모드로 전환되었습니다.")

    def set_selected_files(self, file_paths: list[str]) -> None:
        """스캔할 대상 Excel 파일 목록을 갱신합니다."""
        self.state.selected_files = file_paths
        # 파일이 변경되면 기존 탐지 결과도 안전하게 초기화합니다.
        self.state.detection_results = []
        logger.info(f"선택 파일 리스트 업데이트: {len(file_paths)}개 등록됨.")
        self.state_changed.emit()

    def update_input_patterns(self, students: list[str], schools: list[str], delete_keywords: list[str]) -> None:
        """사용자가 화면에서 수정한 대상 이름/학교명/삭제 단어 패턴을 갱신합니다."""
        # 공백 제거 및 필터링
        self.state.student_names = [name.strip() for name in students if name.strip()]
        self.state.school_names = [school.strip() for school in schools if school.strip()]
        self.state.delete_keywords = [word.strip() for word in delete_keywords if word.strip()]
        logger.info(f"탐지 키워드 갱신 - 학생: {len(self.state.student_names)}명, 학교: {len(self.state.school_names)}개, 삭제: {len(self.state.delete_keywords)}개")
        self.state_changed.emit()

    def update_save_options(self, save_mapping: bool, mapping_format: str) -> None:
        """대장 매핑 저장 처리 옵션을 상태에 저장합니다."""
        self.state.save_mapping = save_mapping
        self.state.mapping_format = mapping_format
        logger.info(f"대장 저장 옵션 변경: 저장={save_mapping}, 형식={mapping_format}")
        self.state_changed.emit()

    def update_detection_approval(self, index: int, approved: bool) -> None:
        """개별 검수 항목의 활성화(체크박스) 여부를 토글합니다."""
        if 0 <= index < len(self.state.detection_results):
            self.state.detection_results[index].approved = approved
            logger.debug(f"항목 #{index} 승인 상태 변경 -> {approved}")
            self.state_changed.emit()

    def update_replacement_text(self, index: int, new_text: str) -> None:
        """개별 검수 항목의 변경 예정 이름을 업데이트합니다."""
        if 0 <= index < len(self.state.detection_results):
            old_text = self.state.detection_results[index].replacement
            self.state.detection_results[index].replacement = new_text
            logger.info(f"항목 #{index} 치환명 수정: {old_text} -> {new_text}")
            self.state_changed.emit()

    def update_delete_replacement(self, replacement: str) -> None:
        """삭제 대체 텍스트를 업데이트합니다."""
        self.state.delete_replacement = replacement
        logger.info(f"삭제 대체 텍스트 변경: '{replacement}'")
        self.state_changed.emit()

    # --- 비동기 작업 기동 슬롯 ---
    def run_detection(self) -> None:
        """백그라운드 스레드를 실행하여 Excel 내 키워드 탐지를 고속으로 수행합니다."""
        if self.state.is_processing:
            logger.warning("현재 이미 처리 중인 백그라운드 작업이 존재합니다.")
            return

        self.state.is_processing = True
        self.state.progress_percentage = 0
        self.state.status_message = "작업 시작 중..."
        self.state_changed.emit()

        # Detection 스레드 생성
        self._detection_worker = DetectionWorker(
            file_paths=self.state.selected_files,
            student_names=self.state.student_names,
            school_names=self.state.school_names,
            delete_keywords=self.state.delete_keywords,
            delete_replacement=self.state.delete_replacement
        )


        # 시그널 연동
        self._detection_worker.progress_changed.connect(self._on_worker_progress)
        self._detection_worker.finished.connect(self._on_detection_finished)
        self._detection_worker.error_occurred.connect(self._on_detection_error)
        
        # 스레드 소멸 관리
        self._detection_worker.finished.connect(self._detection_worker.deleteLater)
        self._detection_worker.error_occurred.connect(self._detection_worker.deleteLater)

        logger.info("비동기 Excel 탐지 Worker 스레드 구동 시작.")
        self._detection_worker.start()

    def execute_anonymization(self, output_dir: str) -> None:
        """승인된 항목들의 치환을 반영하고 Safe Save 방식으로 저장하는 스레드를 기동합니다."""
        if self.state.is_processing:
            logger.warning("현재 처리 중인 작업이 있어 저장을 실행할 수 없습니다.")
            return

        self.state.is_processing = True
        self.state.progress_percentage = 0
        self.state.status_message = "익명화 파일 생성 중..."
        self.state_changed.emit()

        # Anonymize 스레드 생성
        self._anonymize_worker = AnonymizeWorker(
            selected_files=self.state.selected_files,
            replacements=self.state.detection_results,
            output_dir=output_dir,
            save_mapping=self.state.save_mapping,
            mapping_format=self.state.mapping_format
        )

        # 시그널 연동
        self._anonymize_worker.progress_changed.connect(self._on_worker_progress)
        self._anonymize_worker.finished.connect(self._on_anonymize_finished)
        
        # 소멸 관리
        self._anonymize_worker.finished.connect(self._anonymize_worker.deleteLater)

        logger.info("비동기 Safe Save 익명화 Worker 스레드 구동 시작.")
        self._anonymize_worker.start()

    # --- Worker 시그널 콜백 슬롯 ---
    @Slot(int, str)
    def _on_worker_progress(self, percentage: int, message: str):
        """백그라운드 스레드의 진행 정보를 UI로 릴레이 및 컨트롤러 상태 갱신"""
        self.state.progress_percentage = percentage
        self.state.status_message = message
        self.progress_changed.emit(percentage, message)

    @Slot(list)
    def _on_detection_finished(self, results: list):
        """탐지 완료 슬롯"""
        self.state.detection_results = results
        self.state.is_processing = False
        self.state.progress_percentage = 100
        self.state.status_message = f"탐지 완료 (검출 건수: {len(results)}건)"
        
        self.progress_changed.emit(100, self.state.status_message)
        self.state_changed.emit()
        logger.info(f"비동기 탐지 성공 종료. 검출 데이터: {len(results)}개")

    @Slot(str)
    def _on_detection_error(self, err_msg: str):
        """탐색 에러 슬롯"""
        self.state.is_processing = False
        self.state.progress_percentage = 0
        self.state.status_message = "오류 발생으로 스캔 중단"
        
        self.state_changed.emit()
        self.process_finished.emit(False, err_msg)
        logger.error(f"비동기 탐색 작업 실패: {err_msg}")

    @Slot(bool, str)
    def _on_anonymize_finished(self, success: bool, msg: str):
        """익명화 변환 완료 슬롯"""
        self.state.is_processing = False
        self.state.progress_percentage = 100 if success else 0
        self.state.status_message = "작업 완료" if success else "에러로 처리 실패"
        
        self.state_changed.emit()
        self.process_finished.emit(success, msg)
        logger.info(f"비동기 익명화 완료 슬롯 수신: 성공여부={success}")
