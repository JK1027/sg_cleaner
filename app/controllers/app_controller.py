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
        self._item_map = {} # O(1) 조회를 위한 UUID 매핑 딕셔너리
        logger.info("AppController가 초기화 및 실제 연동 모드로 전환되었습니다.")

    def set_selected_files(self, file_paths: list[str]) -> None:
        """스캔할 대상 파일 목록을 갱신합니다."""
        self.state.update_selected_files(file_paths)
        # 파일이 변경되면 기존 탐지 결과도 안전하게 초기화합니다.
        self.state.clear_detection_results()
        self._item_map = {}
        logger.info(f"선택 파일 리스트 업데이트: {len(file_paths)}개 등록됨.")
        self.state_changed.emit()

    def add_files(self, new_file_paths: list[str]) -> None:
        """기존 파일 목록에 새 파일을 중복 없이 추가합니다.

        UI가 state.selected_files를 직접 읽어 병합하는 대신
        이 메서드가 병합 로직을 담당하여 SoC 경계를 유지합니다.
        """
        merged = list(dict.fromkeys(self.state.selected_files + new_file_paths))
        self.set_selected_files(merged)

    def has_files(self) -> bool:
        """처리 대상 파일이 1개 이상 등록되어 있는지 반환합니다."""
        return bool(self.state.selected_files)

    def can_run_detection(self) -> bool:
        """탐지 실행 가능 여부를 반환합니다. (파일 및 키워드 유효성 검사)

        UI의 유효성 검사 로직을 Controller로 위임하여 SoC 경계를 유지합니다.
        """
        has_files = bool(self.state.selected_files)
        has_keywords = bool(
            self.state.student_names
            or self.state.school_names
            or self.state.delete_keywords
        )
        return has_files and has_keywords

    def can_save(self) -> bool:
        """저장 실행 가능 여부를 반환합니다. (탐지 결과 존재 여부 검사)

        UI의 유효성 검사 로직을 Controller로 위임하여 SoC 경계를 유지합니다.
        """
        return bool(self.state.detection_results)

    def update_input_patterns(self, students: list[str], schools: list[str], delete_keywords: list[str]) -> None:
        """사용자가 화면에서 수정한 대상 이름/학교명/삭제 단어 패턴을 갱신합니다."""
        # 공백 제거 및 각 목록 개별 중복 제거 (순서 보존)
        raw_students = list(dict.fromkeys([name.strip() for name in students if name.strip()]))
        raw_schools = list(dict.fromkeys([school.strip() for school in schools if school.strip()]))
        raw_deletes = list(dict.fromkeys([word.strip() for word in delete_keywords if word.strip()]))
        
        # 우선순위: 학생명 > 학교명 > 삭제어
        # 1. 학생명은 그대로 유지
        self.state.student_names = raw_students
        student_set = set(raw_students)
        
        # 2. 학교명에서 학생명과 겹치는 부분 제거
        filtered_schools = []
        for school in raw_schools:
            if school in student_set:
                logger.warning(f"키워드 충돌 감지: '{school}'은(는) 학생명 목록에 이미 존재하므로 학교명 목록에서 제외됩니다.")
            else:
                filtered_schools.append(school)
        self.state.school_names = filtered_schools
        school_set = set(filtered_schools)
        
        # 3. 삭제어에서 학생명 및 학교명과 겹치는 부분 제거
        filtered_deletes = []
        for word in raw_deletes:
            if word in student_set:
                logger.warning(f"키워드 충돌 감지: '{word}'은(는) 학생명 목록에 이미 존재하므로 삭제 단어 목록에서 제외됩니다.")
            elif word in school_set:
                logger.warning(f"키워드 충돌 감지: '{word}'은(는) 학교명 목록에 이미 존재하므로 삭제 단어 목록에서 제외됩니다.")
            else:
                filtered_deletes.append(word)
        self.state.delete_keywords = filtered_deletes
        
        logger.info(f"탐지 키워드 갱신 - 학생: {len(self.state.student_names)}명, 학교: {len(self.state.school_names)}개, 삭제: {len(self.state.delete_keywords)}개")
        self.state_changed.emit()

    def update_save_options(self, save_mapping: bool, mapping_format: str) -> None:
        """대장 매핑 저장 처리 옵션을 상태에 저장합니다."""
        self.state.save_mapping = save_mapping
        self.state.mapping_format = mapping_format
        logger.info(f"대장 저장 옵션 변경: 저장={save_mapping}, 형식={mapping_format}")
        self.state_changed.emit()

    def update_detection_approval(self, item_id: str, approved: bool) -> None:
        """개별 검수 항목의 활성화(체크박스) 여부를 토글합니다.

        ※ 테이블은 사용자가 체크박스를 조작한 시점에 이미 시각적으로 올바른 상태이므로
           state_changed 시그널을 방출하지 않습니다. (전체 테이블 재렌더링 방지)
        """
        if self.state.update_detection_approval(item_id, approved):
            logger.debug(f"항목 {item_id} 승인 상태 변경 -> {approved}")

    def update_replacement_text(self, item_id: str, new_text: str) -> None:
        """개별 검수 항목의 변경 예정 이름을 업데이트합니다.

        ※ 테이블 셀은 사용자가 직접 편집한 시점에 이미 시각적으로 올바른 상태이므로
           state_changed 시그널을 방출하지 않습니다. (전체 테이블 재렌더링 방지)
        """
        if self.state.update_replacement_text(item_id, new_text):
            logger.info(f"항목 {item_id} 치환명 수정: {new_text}")

    def update_delete_replacement(self, replacement: str) -> None:
        """삭제 대체 텍스트를 업데이트합니다."""
        self.state.delete_replacement = replacement
        logger.info(f"삭제 대체 텍스트 변경: '{replacement}'")
        self.state_changed.emit()

    def cancel_processing(self) -> None:
        """현재 진행 중인 백그라운드 작업을 중단(취소) 요청합니다."""
        if not self.state.is_processing:
            return
            
        logger.info("사용자에 의한 백그라운드 작업 취소 요청 접수.")
        self.state.set_processing_state(True, "취소 중... 잠시만 기다려주세요.", self.state.progress_percentage)
        self.state_changed.emit()
        
        if self._detection_worker and self._detection_worker.isRunning():
            self._detection_worker.cancel()
        if self._anonymize_worker and self._anonymize_worker.isRunning():
            self._anonymize_worker.cancel()

    # --- 비동기 작업 기동 슬롯 ---
    def run_detection(self) -> None:
        """백그라운드 스레드를 실행하여 Excel 내 키워드 탐지를 고속으로 수행합니다."""
        if self.state.is_processing:
            logger.warning("현재 이미 처리 중인 백그라운드 작업이 존재합니다.")
            return

        self.state.set_processing_state(True, "작업 시작 중...", 0)
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

        self.state.set_processing_state(True, "익명화 파일 생성 중...", 0)
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
        self.state.set_processing_state(self.state.is_processing, message, percentage)
        self.progress_changed.emit(percentage, message)

    @Slot(list)
    def _on_detection_finished(self, results: list):
        """탐지 완료 슬롯"""
        self.state.clear_detection_results()
        self.state.extend_detection_results(results)
        self._item_map = {item.item_id: item for item in results} # O(1) 딕셔너리 매핑 빌드
        self.state.set_processing_state(False, f"탐지 완료 (검출 건수: {len(results)}건)", 100)
        
        self.progress_changed.emit(100, self.state.status_message)
        self.state_changed.emit()
        logger.info(f"비동기 탐지 성공 종료. 검출 데이터: {len(results)}개")

    @Slot(str)
    def _on_detection_error(self, err_msg: str):
        """탐색 에러 슬롯"""
        self.state.set_processing_state(False, "오류 발생으로 스캔 중단", 0)
        
        self.state_changed.emit()
        self.process_finished.emit(False, err_msg)
        logger.error(f"비동기 탐색 작업 실패: {err_msg}")

    @Slot(bool, str)
    def _on_anonymize_finished(self, success: bool, msg: str):
        """익명화 변환 완료 슬롯"""
        self.state.set_processing_state(False, "작업 완료" if success else "에러로 처리 실패", 100 if success else 0)
        
        self.state_changed.emit()
        self.process_finished.emit(success, msg)
        logger.info(f"비동기 익명화 완료 슬롯 수신: 성공여부={success}")
