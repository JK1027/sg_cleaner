from abc import ABC, abstractmethod
from dataclasses import dataclass
from app.models.detection_model import DetectionItem

@dataclass
class ExtractedTextItem:
    """
    문서에서 추출된 단일 텍스트 청크 및 위치 메타데이터 정보 모델
    """
    text: str              # 추출된 원본 문자열 텍스트
    location_context: str  # 대영역 (Excel: 시트명, HWP: '본문', '표:표이름', '머리말' 등)
    location_detail: str   # 상세 주소 (Excel: 셀 좌표, HWP: '3행 2열', '5번째 문단' 등)

class BaseProcessor(ABC):
    """
    파일 형식별로 텍스트 추출 및 개인정보 치환 저장을 전담하는 프로세서들의 추상 베이스 클래스
    """

    @abstractmethod
    def extract_texts(self, file_path: str) -> list[ExtractedTextItem]:
        """
        주어진 파일에서 모든 가명화 대상 텍스트 조각과 그 세부 위치 메타데이터를 추출합니다.
        
        :param file_path: 탐색 대상 파일 경로
        :return: ExtractedTextItem 목록
        """
        pass

    @abstractmethod
    def apply_replacements(self, file_path: str, replacements: list[DetectionItem], temp_path: str) -> None:
        """
        원본 파일을 읽어 변경 목록을 반영하고 임시 경로(temp_path)에 저장합니다.
        
        :param file_path: 원본 파일 경로
        :param replacements: 승인된 치환 규칙 목록
        :param temp_path: 수정 후 저장될 임시 파일 경로
        """
        pass
