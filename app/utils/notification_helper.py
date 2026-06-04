from PySide6.QtWidgets import QSystemTrayIcon, QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QObject, Signal
from app.utils.logger import logger

class NotificationSignals(QObject):
    """백그라운드 스레드에서 GUI 메인 스레드로 알림 요청을 중계하기 위한 QObject 시그널 브로커"""
    notification_requested = Signal(str, str, bool)

class NotificationHelper:
    """
    의존성 추가 없이 PySide6 내장 QSystemTrayIcon을 활용하여
    OS 시스템 트레이 알림을 안전하게 송출하는 헬퍼 클래스.
    """
    _tray_icon = None
    # ⚠️ 스레드 안전성 보장을 위한 QObject 시그널 브로커 인스턴스
    signals = NotificationSignals()

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
    def initialize_broker(cls, main_window: QObject):
        """메인 윈도우 초기화 시 시그널을 메인 GUI 스레드 실행용 메서드에 연결합니다."""
        cls.signals.notification_requested.connect(cls._execute_notification_main_thread)
        logger.info("NotificationHelper 스레드 안전 시그널 브로커 초기화 완료.")

    @classmethod
    def show_notification(cls, title: str, message: str, is_error: bool = False):
        """
        비동기 스레드에서 직접 호출해도 안전한 메인 스레드 전달용 인터페이스.
        시그널 방출(emit)을 통하면 Qt가 자동으로 메인 스레드 이벤트 큐로 전달합니다.
        """
        if QApplication.instance():
            cls.signals.notification_requested.emit(title, message, is_error)
        else:
            logger.info(f"[알림 로그 대체] {title}: {message}")

    @classmethod
    def _execute_notification_main_thread(cls, title: str, message: str, is_error: bool):
        """GUI 메인 스레드에서 동작이 보장되는 실제 트레이 알림 표시 실행 메서드"""
        icon_type = QSystemTrayIcon.MessageIcon.Critical if is_error else QSystemTrayIcon.MessageIcon.Information
        try:
            # 시스템 트레이 활성화/가용성 선제 검증
            if not QSystemTrayIcon.isSystemTrayAvailable():
                logger.warning(f"시스템 트레이 미지원 또는 비활성 환경. 상태 알림 대체 출력: [{title}] {message}")
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

