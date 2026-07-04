from typing import Dict, List
from .base_processor import BaseProcessor
from .unmerge_processor import UnmergeProcessor
from app.utils.logger import logger

class PostProcessPipeline:
    """
    여러 후처리 프로세서들을 순차적으로 실행하는 파이프라인 레지스트리입니다.
    """
    def __init__(self, enabled_config: Dict[str, bool]):
        self.enabled_config = enabled_config
        self.processors: List[BaseProcessor] = []
        self._build_pipeline()

    def _build_pipeline(self):
        """
        활성화된 설정에 따라 파이프라인을 조립합니다.
        """
        if self.enabled_config.get("unmerge", False):
            self.processors.append(UnmergeProcessor())
            
        logger.info(f"파이프라인 빌드 완료. 등록된 프로세서: {[p.name for p in self.processors]}")

    def execute(self, file_path: str) -> str:
        """
        주어진 파일 경로에 대해 등록된 모든 프로세서를 순차적으로 적용합니다.
        """
        if not self.processors:
            return file_path
            
        current_file = file_path
        for processor in self.processors:
            logger.info(f"파이프라인 단계 실행: {processor.name} ({current_file})")
            try:
                current_file = processor.process(current_file)
            except Exception as e:
                logger.error(f"파이프라인 '{processor.name}' 실행 중 오류 발생: {e}")
                raise e
                
        return current_file
