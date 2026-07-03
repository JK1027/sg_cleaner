import os
import sys
from pathlib import Path

def get_resource_path(relative_path: str) -> str:
    """
    PyInstaller 패키징 대응 리소스 절대 경로 획득 함수.
    로컬 실행 시와 빌드(exe) 실행 시의 리소스 폴더 위치를 통합 관리합니다.
    """
    try:
        # PyInstaller가 임시 폴더를 생성하고 해당 경로를 sys._MEIPASS에 저장함
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # 일반 개발 환경 실행
        base_path = Path(__file__).resolve().parent.parent

    resolved_path = base_path / relative_path
    return str(resolved_path)

def get_project_root() -> Path:
    """
    프로젝트 루트 폴더 경로를 획득합니다.
    PyInstaller 빌드(frozen) 시에는 실행파일(.exe)이 있는 폴더를 반환합니다.
    """
    import sys
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent
