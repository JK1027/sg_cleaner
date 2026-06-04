from dataclasses import dataclass, field
from typing import List
from app.models.detection_model import DetectionItem

@dataclass
class AppState:
    """
    애플리케이션 전역 상태 관리 모델.
    컬렉션 및 상태 변수들의 수정 통제를 위해 내부 캡슐화 메서드를 경유하도록 강제합니다.
    """
    selected_files: List[str] = field(default_factory=list)      # 선택된 대상 파일 경로 목록
    student_names: List[str] = field(default_factory=list)       # 사용자가 입력한 학생 이름 목록
    school_names: List[str] = field(default_factory=list)        # 학교명 목록
    delete_keywords: List[str] = field(default_factory=list)     # 삭제할 단어 목록
    
    detection_results: List[DetectionItem] = field(default_factory=list) # 스캔/탐지된 개인정보 결과 리스트
    
    # 저장 설정
    save_mapping: bool = False
    mapping_format: str = "CSV"
    
    # 비동기 및 처리 진행 상태
    is_processing: bool = False
    progress_percentage: int = 0
    status_message: str = "대기 중"
    
    delete_replacement: str = ""

    # --- 컬렉션 및 상태 캡슐화 제어 메서드 ---

    def update_selected_files(self, file_paths: list[str]) -> None:
        """선택된 파일 목록을 교체합니다."""
        self.selected_files = file_paths

    def set_processing_state(self, is_processing: bool, status_message: str = "대기 중", progress: int = 0) -> None:
        """비동기 연산 중의 처리 상태 및 진행률 정보를 업데이트합니다."""
        self.is_processing = is_processing
        self.status_message = status_message
        self.progress_percentage = progress

    def clear_detection_results(self) -> None:
        """탐지 결과 리스트를 초기화합니다."""
        self.detection_results.clear()

    def add_detection_result(self, item: DetectionItem) -> None:
        """탐지 결과를 하나 추가합니다."""
        self.detection_results.append(item)

    def extend_detection_results(self, items: list[DetectionItem]) -> None:
        """탐지 결과 목록을 병합 추가합니다."""
        self.detection_results.extend(items)

    def update_replacement_text(self, item_id: str, new_text: str) -> bool:
        """고유 ID에 해당하는 탐색 항목의 변경 예정 이름을 업데이트합니다."""
        for item in self.detection_results:
            if item.item_id == item_id:
                item.replacement = new_text
                return True
        return False

    def update_detection_approval(self, item_id: str, approved: bool) -> bool:
        """고유 ID에 해당하는 탐색 항목의 적용 체크 여부를 토글합니다."""
        for item in self.detection_results:
            if item.item_id == item_id:
                item.approved = approved
                return True
        return False
