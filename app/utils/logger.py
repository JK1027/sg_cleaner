import logging
import os
from datetime import datetime
from app.utils.path_helper import get_project_root

def setup_logger() -> logging.Logger:
    """애플리케이션 전역 로거 설정 및 반환"""
    project_root = get_project_root()
    log_dir = project_root / "logs"
    
    # logs 디렉토리가 없을 시 생성 안전 장치
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = log_dir / "app.log"
    
    logger = logging.getLogger("sg_cleaner")
    logger.setLevel(logging.DEBUG)
    
    # 중복 핸들러 방지
    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # 파일 핸들러 (UTF-8 인코딩)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    return logger

# 전역 로거 인스턴스 제공
logger = setup_logger()
