from dataclasses import dataclass, field
from typing import List
from app.models.detection_model import DetectionItem

@dataclass
class AppState:
    """
    애플리케이션 전역 상태 관리
    UI와 비즈니스 로직(서비스) 간의 상태 격리를 수행합니다.
    """
    selected_files: List[str] = field(default_factory=list)      # 선택된 대상 Excel 파일 경로 목록
    student_names: List[str] = field(default_factory=list)       # 사용자가 입력한 학생 이름 검색 목록
    school_names: List[str] = field(default_factory=list)        # 사용자가 입력한 학교명 검색 목록
    
    detection_results: List[DetectionItem] = field(default_factory=list) # 스캔 및 탐지된 개인정보 결과 리스트
    
    # 저장 설정
    save_mapping: bool = False                                   # 익명화 매핑 대장 저장 여부
    mapping_format: str = "CSV"                                  # CSV 또는 EXCEL
    
    # 비동기 및 처리 진행 상태
    is_processing: bool = False                                  # 백그라운드 작업 진행 여부
    progress_percentage: int = 0                                 # 0~100 진행률
    status_message: str = "대기 중"                               # 하단 상태 바 메시지
