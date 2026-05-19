from dataclasses import dataclass

@dataclass
class DetectionItem:
    """
    탐지된 개인정보(이름, 학교명 등)의 개별 정보 모델
    """
    file_path: str        # 원본 Excel 파일 경로
    sheet_name: str       # 시트 이름
    cell_address: str     # 셀 주소 (예: B12)
    original_value: str   # 원본 셀 텍스트 (예: '김민수 학생이 제출함')
    match_value: str      # 실제 매칭되어 탐지된 패턴 (예: '김민수')
    replacement: str      # 변경 예정 텍스트 (예: '학생1')
    approved: bool = True # 익명화 적용 승인 여부 (검수 체크박스 연동)
