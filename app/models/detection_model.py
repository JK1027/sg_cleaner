import uuid
from dataclasses import dataclass, field

@dataclass
class DetectionItem:
    """
    탐지된 개인정보(이름, 학교명 등)의 개별 정보 모델
    """
    file_path: str        # 원본 파일 경로
    location_context: str # 문서 내 대영역 (Excel: 시트명, HWP: '본문', '표:표이름', '머리말' 등)
    location_detail: str  # 상세 주소 (Excel: 셀 주소, HWP: '3행 2열', '5번째 문단' 등)
    context_preview: str  # 탐지된 키워드 주변 문맥 정보 (앞뒤 40~60자 내외)
    original_value: str   # 원본 텍스트
    match_value: str      # 실제 매칭되어 탐지된 패턴 (예: '김민수')
    replacement: str      # 변경 예정 텍스트 (예: '학생1')
    approved: bool = True # 익명화 적용 승인 여부 (검수 체크박스 연동)
    is_ambiguous: bool = False # 동명이인 여부
    confidence: float = 1.0 # 판정 신뢰도 (0.0 ~ 1.0)
    ambiguity_reason: str = "" # 판정 근거
    candidates: list[str] = field(default_factory=list) # 선택 가능한 가명 후보 리스트 (예: ["학생1105 (1-1반)"])
    item_id: str = field(default_factory=lambda: uuid.uuid4().hex)
