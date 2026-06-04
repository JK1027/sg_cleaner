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
                # 기본 정보 수준의 빈 아이콘 지정 (시스템 기본값 사용)
                cls._tray_icon.setIcon(QIcon())
                cls._tray_icon.show()
        return cls._tray_icon

    @classmethod
    def show_notification(cls, title: str, message: str, is_error: bool = False):
        """
        백그라운드 스레드에서 안전하게 호출 가능하도록 메인 이벤트 루프에 알림 송출 작업을 예약합니다.
        """
        icon_type = QSystemTrayIcon.MessageIcon.Critical if is_error else QSystemTrayIcon.MessageIcon.Information
        
        def _execute_notification():
            try:
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
