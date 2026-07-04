import sys
import os
from PySide6.QtWidgets import QApplication
from app.models.app_state import AppState
from app.controllers.app_controller import AppController
from app.ui.main_window import MainWindow
from app.services.excel_service import ExcelService
from app.utils.logger import logger
from app.utils.path_helper import get_resource_path

def load_stylesheet(app: QApplication):
    """QSS 스타일시트를 로드하여 애플리케이션에 적용합니다."""
    qss_path = get_resource_path("resources/style.qss")
    logger.info(f"QSS 스타일시트 로드 시도: {qss_path}")
    
    if os.path.exists(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                style_data = f.read()
                
                # 체크박스 이미지 경로 동적 변환 (절대 경로 대응)
                check_img_path = get_resource_path("resources/check.png").replace("\\", "/")
                style_data = style_data.replace("__CHECK_IMAGE_PATH__", check_img_path)
                
                app.setStyleSheet(style_data)
                logger.info("QSS 스타일시트 적용 성공.")
        except Exception as e:
            logger.error(f"QSS 스타일시트 파일 읽기 중 예외 발생: {str(e)}")
    else:
        logger.warning(f"QSS 스타일시트 파일을 찾을 수 없습니다: {qss_path}")

def main():
    # 전역 미처리 예외 로깅 훅 등록
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("미처리 예외 발생 (애플리케이션)", exc_info=(exc_type, exc_value, exc_traceback))
    sys.excepthook = handle_exception

    logger.info("생기부 개인정보 익명화 도구 실행 시작.")

    # 0. 이전 실행에서 잔류한 temp 파일 정리 (Safe Save 비정상 종료 대비)
    ExcelService.cleanup_temp_folder()

    # 1. Qt application 생성
    app = QApplication(sys.argv)
    
    # 2. 전역 스타일 적용
    load_stylesheet(app)
    
    # 3. 중앙 상태 객체 및 컨트롤러 생성
    state = AppState()
    controller = AppController(state)
    
    # 4. 메인 UI 윈도우 생성 및 컨트롤러 주입
    window = MainWindow(controller)
    window.show()
    
    # 5. 앱 이벤트 루프 진입
    exit_code = app.exec()
    
    logger.info(f"생기부 개인정보 익명화 도구 실행 종료. (Exit Code: {exit_code})")
    sys.exit(exit_code)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"애플리케이션 비정상 종료 예외 발생: {str(e)}", exc_info=True)
        sys.exit(1)
