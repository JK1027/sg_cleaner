from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtCore import QObject, Signal, QTimer
from app.utils.logger import logger

class NotificationSignals(QObject):
    """백그라운드 스레드에서 GUI 메인 스레드로 알림 요청을 중계하기 위한 QObject 시그널 브로커"""
    notification_requested = Signal(str, str, bool)

class NotificationHelper:
    """
    QMessageBox를 활용하여 메인 스레드 안전하게 알림을 송출하는 헬퍼 클래스.
    성공 알림은 1초 후 자동 소멸하며, 에러 알림은 확인 버튼을 누를 때까지 유지됩니다.
    """
    signals = NotificationSignals()
    _active_msg_boxes = [] # GC(가비지 컬렉션) 방지용 활성 알림 리스트

    @classmethod
    def initialize_broker(cls, main_window: QObject):
        """메인 윈도우 초기화 시 시그널을 메인 GUI 스레드 실행용 메서드에 연결합니다."""
        cls.signals.notification_requested.connect(cls._execute_notification_main_thread)
        logger.info("NotificationHelper 스레드 안전 시그널 브로커 초기화 완료.")

    @classmethod
    def show_notification(cls, title: str, message: str, is_error: bool = False):
        """
        비동기 스레드에서 직접 호출해도 안전한 메인 스레드 전달용 인터페이스.
        """
        if QApplication.instance():
            cls.signals.notification_requested.emit(title, message, is_error)
        else:
            logger.info(f"[알림 로그 대체] {title}: {message}")

    @classmethod
    def _execute_notification_main_thread(cls, title: str, message: str, is_error: bool):
        """GUI 메인 스레드에서 동작이 보장되는 실제 알림 메시지박스 송출 메서드"""
        try:
            # 메인 윈도우를 부모로 찾아 지정 (창 중앙 배치 유도)
            parent = None
            if QApplication.instance():
                for widget in QApplication.instance().topLevelWidgets():
                    if widget.inherits("QMainWindow"):
                        parent = widget
                        break

            msg_box = QMessageBox(parent)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)

            if is_error:
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.addButton(QMessageBox.StandardButton.Ok)
                msg_box.open()
            else:
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.addButton(QMessageBox.StandardButton.Ok)

                # GC(가비지 컬렉션) 방지를 위해 리스트에 참조 추가
                cls._active_msg_boxes.append(msg_box)

                # 닫힐 때 참조 자동 삭제 연동
                msg_box.finished.connect(lambda: cls._active_msg_boxes.remove(msg_box) if msg_box in cls._active_msg_boxes else None)

                # 1초 후 자동 닫기 타이머 연동
                QTimer.singleShot(1000, msg_box.close)
                msg_box.open()

            logger.info(f"QMessageBox 알림 송출 성공: [{title}] {message}")
        except Exception as e:
            logger.error(f"알림 송출 도중 예외 발생: {str(e)}")
