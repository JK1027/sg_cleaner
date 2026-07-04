from .base_processor import BaseProcessor
from .pipeline import PostProcessPipeline
from .unmerge_processor import UnmergeProcessor

# UI 동적 생성을 위한 사용 가능한 모든 프로세서 인스턴스 목록
AVAILABLE_PROCESSORS = [
    UnmergeProcessor(),
]
