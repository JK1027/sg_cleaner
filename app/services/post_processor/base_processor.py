from abc import ABC, abstractmethod

class BaseProcessor(ABC):
    """
    모든 후처리(Post-Process) 파이프라인 모듈의 공통 인터페이스입니다.
    """
    # 각 프로세서의 고유 ID (app_state 설정 딕셔너리의 키와 매칭됨)
    id: str = "base"
    
    # UI 화면에 표시될 체크박스 이름
    name: str = "Base Processor"
    
    # UI 화면에 표시될 부가 설명
    description: str = "Base description"

    @abstractmethod
    def process(self, file_path: str) -> str:
        """
        입력 엑셀 파일을 전달받아 후처리 연산을 수행한 후, 
        처리된 파일의 경로(보통 동일한 경로 덮어쓰기)를 반환합니다.
        
        Args:
            file_path (str): 입력 파일의 절대 또는 상대 경로
            
        Returns:
            str: 처리 완료된 파일의 경로
        """
        pass
