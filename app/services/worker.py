import os
from PySide6.QtCore import QThread, Signal
from app.services.detector import AnonymizeDetector
from app.services.excel_service import ExcelService, PROCESSORS
from app.models.detection_model import DetectionItem
from app.services.post_processor import PostProcessPipeline
from app.utils.logger import logger
from app.utils.notification_helper import NotificationHelper

class DetectionWorker(QThread):
    """
    다양한 문서 파일들을 순차적으로 열어 개인정보를 자동 스캔하는 백그라운드 스레드.
    스캔율(0~100) 및 최종 수집 리스트를 메인 스레드(UI)에 전달합니다.
    """
    # (진행률 %, 상태 메시지)
    progress_changed = Signal(int, str)
    # (탐지된 DetectionItem 목록)
    finished = Signal(list)
    # (에러 메시지)
    error_occurred = Signal(str)

    def __init__(self, file_paths: list[str], student_names: list[str], school_names: list[str],
                 delete_keywords: list[str] = None, delete_replacement: str = ""):
        super().__init__()
        self.file_paths = file_paths
        self.student_names = student_names
        self.school_names = school_names
        self.delete_keywords = delete_keywords or []
        self.delete_replacement = delete_replacement
        self._is_canceled = False

    def cancel(self):
        """작업 취소 플래그를 설정합니다."""
        self._is_canceled = True

    def run(self):
        logger.info("백그라운드 탐색 스레드 시작.")
        detected_items = []
        total_files = len(self.file_paths)
        
        if total_files == 0:
            self.finished.emit([])
            return

        try:
            # 1단계 탐지용 디텍터 인스턴스 초기화 (이름/학교명/삭제 단어 패턴 등록 및 익명화 옵션 반영)
            detector = AnonymizeDetector(
                student_names=self.student_names,
                school_names=self.school_names,
                delete_keywords=self.delete_keywords,
                delete_replacement=self.delete_replacement
            )
            
            for index, file_path in enumerate(self.file_paths):
                if self._is_canceled:
                    logger.info("백그라운드 탐색 작업이 사용자에 의해 취소되었습니다.")
                    self.error_occurred.emit("사용자가 작업을 취소했습니다.")
                    return
                # 개별 파일 처리 전 진행률 알림
                percentage_before = int((index / total_files) * 100)
                file_name = os.path.basename(file_path)
                self.progress_changed.emit(percentage_before, f"{file_name} 탐색 중...")
                
                # 확장자 파악 및 프로세서 라우팅
                ext = os.path.splitext(file_path)[1].lower()
                processor_cls = PROCESSORS.get(ext)
                if not processor_cls:
                    raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")
                
                processor = processor_cls()
                
                # 텍스트 추출 및 매칭 스캔 수행
                extracted_texts = processor.extract_texts(file_path)
                file_results = detector.scan_text_items(extracted_texts, file_path)
                detected_items.extend(file_results)
                
                # 개별 파일 처리 완료 후 진행률 및 메시지 알림
                percentage_after = int(((index + 1) / total_files) * 100)
                self.progress_changed.emit(percentage_after, f"{file_name} 탐색 완료")
                
            # 완료 알림
            self.progress_changed.emit(100, "탐색 완료")
            NotificationHelper.show_notification(
                "개인정보 탐색 완료",
                f"총 {len(detected_items)}건의 개인정보가 탐색되었습니다. 테이블에서 확인해 주세요."
            )
            self.finished.emit(detected_items)
            
        except Exception as e:
            logger.error(f"백그라운드 스캔 중 오류 발생: {str(e)}", exc_info=True)
            NotificationHelper.show_notification(
                "개인정보 탐색 오류",
                f"스캔 도중 오류가 발생했습니다: {str(e)}",
                is_error=True
            )
            self.error_occurred.emit(f"스캔 오류: {str(e)}")


class AnonymizeWorker(QThread):
    """
    검수 및 승인이 완료된 내역들을 Excel 복사본에 저장하는 백그라운드 스레드.
    매핑 대장 파일 작성 옵션 처리도 병행합니다.
    """
    # (진행률 %, 상태 메시지)
    progress_changed = Signal(int, str)
    # (성공 여부, 완료 메시지)
    finished = Signal(bool, str)

    def __init__(self, selected_files: list[str], replacements: list[DetectionItem], 
                 output_dir: str, save_mapping: bool, mapping_format: str, enabled_post_processors: dict = None):
        super().__init__()
        self.selected_files = selected_files
        self.replacements = replacements
        self.output_dir = output_dir
        self.save_mapping = save_mapping
        self.mapping_format = mapping_format
        self.enabled_post_processors = enabled_post_processors or {}
        self._is_canceled = False

    def cancel(self):
        """작업 취소 플래그를 설정합니다."""
        self._is_canceled = True

    def run(self):
        logger.info("백그라운드 익명화 저장 스레드 시작.")
        excel_service = ExcelService()
        total_files = len(self.selected_files)
        
        if total_files == 0:
            self.finished.emit(False, "익명화 적용 대상 파일이 없습니다.")
            return

        try:
            # 1. 파일별 Safe Save 익명화 진행
            for index, file_path in enumerate(self.selected_files):
                if self._is_canceled:
                    logger.info("백그라운드 익명화 작업이 사용자에 의해 취소되었습니다.")
                    self.finished.emit(False, "사용자가 작업을 취소했습니다.")
                    return
                
                # ⚠️ .hwp 확장자인 경우 Safe Save 익명화 처리 스킵 (선제 경고 승인 하에 실행)
                if file_path.lower().endswith(".hwp"):
                    logger.info(f"한글(.hwp) 치환 건너뜀: {file_path}")
                    continue

                percentage_before = int((index / total_files) * 90) # 매핑 전까지 90% 반영
                file_name = os.path.basename(file_path)
                self.progress_changed.emit(percentage_before, f"{file_name} 익명화 적용 중...")
                
                # Safe Save 파이프라인 수행
                final_saved_path = excel_service.apply_replacements_safe(file_path, self.replacements, self.output_dir)
                
                # 후처리(Post-Process) 파이프라인 수행
                if self.enabled_post_processors and final_saved_path.lower().endswith(".xlsx"):
                    self.progress_changed.emit(percentage_before, f"{file_name} 후처리 병합 해제 등 적용 중...")
                    pipeline = PostProcessPipeline(self.enabled_post_processors)
                    try:
                        pipeline.execute(final_saved_path)
                    except Exception as pipe_err:
                        logger.error(f"후처리 파이프라인 실행 중 오류 발생: {pipe_err}")
                
                percentage_after = int(((index + 1) / total_files) * 90)
                self.progress_changed.emit(percentage_after, f"{file_name} 익명화 적용 완료")

            # 2. 매핑 정보 대장 파일 생성 (필요 시)
            if self.save_mapping:
                self.progress_changed.emit(95, "매핑 파일 대장 쓰는 중...")
                
                # 누적 매핑 상태 구성
                unique_mappings = {}
                for item in self.replacements:
                    if item.approved:
                        unique_mappings[item.match_value] = item.replacement
                
                # 파일 확장자 추가
                mapping_ext = ".csv" if self.mapping_format.upper() == "CSV" else ".xlsx"
                mapping_path = os.path.join(self.output_dir, f"익명화_매핑_대장{mapping_ext}")
                
                excel_service.save_mapping_file(unique_mappings, mapping_path, self.mapping_format)
                
            self.progress_changed.emit(100, "작업 저장 완료")
            self.finished.emit(True, "익명화 및 파일 저장이 안전하게 완료되었습니다.")
            
        except Exception as e:
            logger.error(f"백그라운드 익명화 실행 오류: {str(e)}", exc_info=True)
            self.finished.emit(False, f"익명화 실패: {str(e)}")
