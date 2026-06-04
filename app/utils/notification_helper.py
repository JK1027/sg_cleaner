from PySide6.QtWidgets import QSystemTrayIcon, QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer
from app.utils.logger import logger

class NotificationHelper:
    """
    의존성 추가 없이 PySide6 내장 QSystemTrayIcon을 활용하여
    OS 시스템 트레이 알림을 안전하게 송출하는 헬퍼 클래스.
    """
    _tray_icon = None

    @classmethod
    def get_tray_icon(cls) -> QSystemTrayIcon:
        if cls._tray_icon is None:
            if QApplication.instance():
                cls._tray_icon = QSystemTrayIcon(QApplication.instance())
                
                # 어플리케이션 기본 윈도우 아이콘 로드 시도
                icon = QApplication.windowIcon()
                if icon.isNull():
                    # 시스템 정보 기본 아이콘으로 Fallback
                    icon = QIcon.fromTheme("dialog-information")
                
                cls._tray_icon.setIcon(icon)
                cls._tray_icon.show()
        return cls._tray_icon

    @classmethod
    def show_notification(cls, title: str, message: str, is_error: bool = False):
        """
        시스템 트레이의 가용 여부를 체크하고, 불가한 환경인 경우 로그를 통해 정합성을 보장합니다.
        메인 GUI 스레드 이벤트 루프를 경유해 스레드 안전하게 호출되도록 통제합니다.
        """
        icon_type = QSystemTrayIcon.MessageIcon.Critical if is_error else QSystemTrayIcon.MessageIcon.Information
        
        def _execute_notification():
            try:
                # ⚠️ 3차 보완: 시스템 트레이 활성화/가용성 선제 검증
                if not QSystemTrayIcon.isSystemTrayAvailable():
                    logger.warning(f"시스템 트레이 미지원 또는 비활성 환경. 상태 알림 대체 출력: [{title}] {message}")
                    # UI 인스턴스가 존재할 경우 상태바 릴레이 피드백 우회
                    app = QApplication.instance()
                    if app:
                        for widget in app.topLevelWidgets():
                            if hasattr(widget, "statusBar"):
                                widget.statusBar().showMessage(f"[{title}] {message}", 5000)
                    return

                tray = cls.get_tray_icon()
                if tray and QSystemTrayIcon.supportsMessages():
                    tray.showMessage(title, message, icon_type, 5000)
                    logger.info(f"시스템 트레이 알림 송출 성공: [{title}] {message}")
                else:
                    logger.warning(f"시스템 트레이 메시지 미지원 환경. 대체 기록: [{title}] {message}")
            except Exception as e:
                logger.error(f"시스템 알림 송출 도중 예외 발생: {str(e)}")

        # QApplication 인스턴스가 존재할 경우 메인 스레드에서 실행 보장
        if QApplication.instance():
            QTimer.singleShot(0, _execute_notification)
        else:
            logger.info(f"[알림 로그 대체] {title}: {message}")
