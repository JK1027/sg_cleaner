from dataclasses import dataclass, field
from typing import List
from app.models.detection_model import DetectionItem

@dataclass
class AppState:
    """
    애플리케이션 전역 상태 관리 모델.
    컬렉션 및 상태 변수들의 수정 통제를 위해 내부 캡슐화 메서드를 경유하도록 강제합니다.
    """
    # 내부 변수용 접두사 처리
    _selected_files: List[str] = field(default_factory=list, init=False)
    _student_names: List[str] = field(default_factory=list, init=False)
    _school_names: List[str] = field(default_factory=list, init=False)
    _delete_keywords: List[str] = field(default_factory=list, init=False)
    _detection_results: List[DetectionItem] = field(default_factory=list, init=False)

    selected_files: List[str] = field(default_factory=list)      # 선택된 대상 파일 경로 목록
    student_names: List[str] = field(default_factory=list)       # 사용자가 입력한 학생 이름 목록
    school_names: List[str] = field(default_factory=list)        # 학교명 목록
    delete_keywords: List[str] = field(default_factory=list)     # 삭제할 단어 목록
    detection_results: List[DetectionItem] = field(default_factory=list) # 스캔/탐지된 개인정보 결과 리스트

    def __post_init__(self):
        # dataclass 초기값 백업
        self._selected_files = list(self.selected_files)
        self._student_names = list(self.student_names)
        self._school_names = list(self.school_names)
        self._delete_keywords = list(self.delete_keywords)
        self._detection_results = list(self.detection_results)

    # 읽기 전용 프로퍼티 정의 (외부에서 직접 덮어쓰기 방지 및 리스트 복사본 반환으로 불변성 유지)
    @property
    def selected_files_list(self) -> List[str]:
        return list(self._selected_files)

    @property
    def student_names_list(self) -> List[str]:
        return list(self._student_names)

    @property
    def school_names_list(self) -> List[str]:
        return list(self._school_names)

    @property
    def delete_keywords_list(self) -> List[str]:
        return list(self._delete_keywords)

    @property
    def detection_results_list(self) -> List[DetectionItem]:
        return list(self._detection_results)
    
    # 프리셋 관련 비공개 필드 및 프로퍼티
    _current_preset_id: str = ""
    _preset_dict: dict = field(default_factory=dict)

    @property
    def current_preset_id(self) -> str:
        return self._current_preset_id

    @property
    def preset_dict(self) -> dict:
        return dict(self._preset_dict)
    
    # 저장 설정
    save_mapping: bool = False
    mapping_format: str = "CSV"
    
    # 비동기 및 처리 진행 상태
    is_processing: bool = False
    progress_percentage: int = 0
    status_message: str = "대기 중"
    
    delete_replacement: str = ""

    # --- 컬렉션 및 상태 캡슐화 제어 메서드 ---

    def update_presets(self, preset_dict: dict) -> None:
        """스캔된 로컬 프리셋 목록을 업데이트합니다."""
        self._preset_dict = dict(preset_dict)

    def set_current_preset_id(self, file_id: str) -> None:
        """현재 선택된 프리셋 ID를 설정합니다."""
        self._current_preset_id = file_id

    def update_selected_files(self, file_paths: list[str]) -> None:
        """선택된 파일 목록을 교체합니다."""
        self._selected_files = list(file_paths)
        self.selected_files = self._selected_files

    def update_input_patterns(self, students: list[str], schools: list[str], delete_keywords: list[str]) -> None:
        """입력 패턴 목록을 교체합니다."""
        self._student_names = list(students)
        self.student_names = self._student_names
        
        self._school_names = list(schools)
        self.school_names = self._school_names
        
        self._delete_keywords = list(delete_keywords)
        self.delete_keywords = self._delete_keywords

    def set_processing_state(self, is_processing: bool, status_message: str = "대기 중", progress: int = 0) -> None:
        """비동기 연산 중의 처리 상태 및 진행률 정보를 업데이트합니다."""
        self.is_processing = is_processing
        self.status_message = status_message
        self.progress_percentage = progress

    def clear_detection_results(self) -> None:
        """탐지 결과 리스트를 초기화합니다."""
        self._detection_results.clear()
        self.detection_results = self._detection_results

    def add_detection_result(self, item: DetectionItem) -> None:
        """탐지 결과를 하나 추가합니다."""
        self._detection_results.append(item)
        self.detection_results = self._detection_results

    def extend_detection_results(self, items: list[DetectionItem]) -> None:
        """탐지 결과 목록을 병합 추가합니다."""
        self._detection_results.extend(items)
        self.detection_results = self._detection_results

    def update_replacement_text(self, item_id: str, new_text: str) -> bool:
        """고유 ID에 해당하는 탐색 항목의 변경 예정 이름을 업데이트합니다."""
        for item in self._detection_results:
            if item.item_id == item_id:
                item.replacement = new_text
                return True
        return False

    def update_detection_approval(self, item_id: str, approved: bool) -> bool:
        """고유 ID에 해당하는 탐색 항목의 적용 체크 여부를 토글합니다."""
        for item in self._detection_results:
            if item.item_id == item_id:
                item.approved = approved
                return True
        return False
