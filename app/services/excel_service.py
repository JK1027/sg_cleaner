import os
import shutil
import uuid
import pandas as pd
from app.models.detection_model import DetectionItem
from app.services.excel_processor import ExcelProcessor
from app.services.hwpx_processor import HwpxProcessor
from app.services.hwp_processor import HwpProcessor
from app.utils.logger import logger
from app.utils.path_helper import get_project_root

# Processor Registry
PROCESSORS = {
    ".xlsx": ExcelProcessor,
    ".hwpx": HwpxProcessor,
    ".hwp": HwpProcessor,
}

class ExcelService:
    """
    다양한 파일 형식에 대해 안전하게 데이터를 치환하고,
    저장 시 파일 손상을 막기 위한 Safe Save 메커니즘을 총괄하는 비즈니스 서비스 클래스.
    """

    @staticmethod
    def cleanup_temp_folder() -> None:
        """
        앱 시작 시 이전 실행에서 잔류한 temp 파일들을 일괄 정리합니다.
        """
        import tempfile
        from pathlib import Path
        temp_dir = Path(tempfile.gettempdir()) / "sg_cleaner_temp"
        if not temp_dir.exists():
            return

        cleaned = 0
        failed = 0
        for entry in temp_dir.iterdir():
            if entry.is_file() and entry.name.startswith("temp_"):
                try:
                    entry.unlink()
                    logger.debug(f"잔류 temp 파일 삭제: {entry.name}")
                    cleaned += 1
                except Exception as e:
                    failed += 1
                    logger.warning(f"잔류 temp 파일 삭제 실패: {entry.name} - {str(e)}")

        if cleaned > 0:
            logger.info(f"앱 시작 시 잔류 temp 파일 {cleaned}개 정리 완료.")
        if failed > 0:
            logger.warning(f"잔류 temp 파일 {failed}개 삭제 실패.")

    def apply_replacements_safe(self, file_path: str, replacements: list[DetectionItem], output_dir: str) -> str:
        """
        [Safe Save 4단계 공통 파이프라인 구현]
        1. 원본 파일을 읽어서 temp/ 경로에 고유 임시 파일 복사본 생성
        2. 확장자 매핑 프로세서를 호출하여 임시 파일 데이터 치환 수행
        3. 프로세서의 텍스트 추출 기능을 호출하여 임시 파일 무결성(Open Test) 검증
        4. 무결성 검증 완료 시, 최종 output_dir로 안전하게 이동 (순차 이름 부여)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        processor_cls = PROCESSORS.get(ext)
        if not processor_cls:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")
            
        processor = processor_cls()

        # 1. 임시 파일명 생성 및 복사
        import tempfile
        from pathlib import Path
        temp_dir = Path(tempfile.gettempdir()) / "sg_cleaner_temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        file_name = os.path.basename(file_path)
        base_name, ext_orig = os.path.splitext(file_name)
        
        temp_file_name = f"temp_{uuid.uuid4().hex}{ext_orig}"
        temp_path = str(temp_dir / temp_file_name)
        
        logger.info(f"[Safe Save 1단계] 임시 복사 파일 생성: {temp_path}")
        shutil.copy2(file_path, temp_path)

        try:
            # 2. 프로세서를 통한 수정 반영
            logger.info(f"[Safe Save 2단계] 치환 반영 중: {file_name}")
            processor.apply_replacements(file_path, replacements, temp_path)
            logger.info("[Safe Save 2단계] 임시 수정 저장 성공.")

            # 3. 임시 파일 무결성 검증 (Open Test)
            logger.info("[Safe Save 3단계] 임시 저장 파일 무결성(Open Test) 검증 시작.")
            try:
                # 프로세서의 extract_texts가 정상 작동하여 오류 없이 결과를 반환하는지 테스트
                processor.extract_texts(temp_path)
                logger.info("[Safe Save 3단계] 임시 파일 손상 없음 확인 (검증 완료).")
            except Exception as test_err:
                logger.critical(f"임시 파일 무결성 검증 실패 (파일 손상 가능성): {str(test_err)}")
                raise IOError(f"수정된 {ext} 임시 파일이 정상적으로 로드되지 않습니다. 저장을 중단합니다.") from test_err

            # 4. 최종 목적지로 이동
            os.makedirs(output_dir, exist_ok=True)
            final_file_name = f"{base_name}_anonymized{ext_orig}"
            final_path = os.path.join(output_dir, final_file_name)
            
            counter = 1
            while os.path.exists(final_path):
                final_file_name = f"{base_name}_anonymized({counter}){ext_orig}"
                final_path = os.path.join(output_dir, final_file_name)
                counter += 1
                
            logger.info(f"[Safe Save 4단계] 임시 파일을 최종 위치로 이동: {final_path}")
            shutil.move(temp_path, final_path)
            logger.info(f"Safe Save 프로세스 정상 완료: {final_path}")
            return final_path

        except Exception as e:
            logger.error(f"익명화 중 예외 발생: {str(e)}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"실패 복구 - 임시 파일 삭제 완료: {temp_path}")
                except Exception as clean_err:
                    logger.error(f"실패 복구 중 임시 파일 삭제 실패: {str(clean_err)}")
            raise e

    def save_mapping_file(self, mapping_data: dict[str, str], output_path: str, format_type: str) -> None:
        """
        익명화된 이름/학교명 매핑 관계를 CSV 또는 Excel로 저장합니다.
        """
        if not mapping_data:
            logger.info("저장할 매핑 데이터가 비어 있습니다.")
            return

        df = pd.DataFrame(list(mapping_data.items()), columns=["원본 값", "익명화 값"])
        
        try:
            if format_type.upper() == "CSV":
                df.to_csv(output_path, index=False, encoding="utf-8-sig")
                logger.info(f"매핑 정보가 CSV 파일로 저장되었습니다: {output_path}")
            elif format_type.upper() == "EXCEL":
                df.to_excel(output_path, index=False)
                logger.info(f"매핑 정보가 Excel 파일로 저장되었습니다: {output_path}")
            else:
                raise ValueError(f"지원하지 않는 파일 포맷 형식: {format_type}")
        except Exception as e:
            logger.error(f"매핑 파일 저장 실패: {str(e)}")
            raise e
