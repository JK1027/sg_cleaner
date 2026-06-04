import os
from app.services.base_processor import BaseProcessor, ExtractedTextItem
from app.models.detection_model import DetectionItem
from app.utils.logger import logger

class HwpProcessor(BaseProcessor):
    """
    HWP (한글 바이너리 OLE) 문서의 데이터 스캔을 처리하는 구체 프로세서 클래스.
    보안 및 서식 손상 리스크 방지 정책에 따라, 스캔(텍스트 추출)만 지원하고
    물리적인 수정 쓰기는 PoC(개념 검증) 검토 단계로 제한하여 차단합니다.
    """

    def extract_texts(self, file_path: str) -> list[ExtractedTextItem]:
        """
        win32com을 사용하여 한글 프로그램을 백그라운드로 실행하고 GetText API로 문맥 데이터를 추출합니다.
        """
        extracted_items = []
        hwp = None
        
        try:
            import win32com.client
        except ImportError as e:
            logger.error("win32com 라이브러리가 설치되지 않았습니다. pip install pywin32가 필요합니다.")
            raise RuntimeError("한글(.hwp) 처리를 위해 pywin32 라이브러리가 필요합니다.") from e

        try:
            logger.info(f"HWP COM 객체 구동 시도: {file_path}")
            # HWP OLE 연결 (백그라운드 실행)
            hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
            
            # 파일 오픈 (대화상자 생략 및 강제 열기)
            # forceopen:true는 다른 프로세스가 사용 중이거나 복구 메시지를 무시하고 열기 시도
            opened = hwp.Open(file_path, "HWP", "forceopen:true")
            if not opened:
                raise IOError(f"한글 프로그램에서 파일을 열 수 없습니다: {file_path}")

            # 텍스트 추출 순회 초기화
            hwp.InitScan()
            
            text_block_idx = 1
            while True:
                # GetText는 (결과코드, 텍스트) 튜플을 반환함
                result_code, text = hwp.GetText()
                
                # 결과코드 1: 문서 끝 도달
                if result_code == 1:
                    break
                
                # 텍스트가 유효한 경우 수집
                if text:
                    text_str = text.strip()
                    if text_str:
                        extracted_items.append(ExtractedTextItem(
                            text=text,
                            location_context="본문 및 개체 영역",
                            location_detail=f"블록 {text_block_idx}"
                        ))
                        text_block_idx += 1
                        
            hwp.ReleaseScan()
            logger.info(f"HWP 텍스트 추출 성공: {file_path} (블록 개수: {len(extracted_items)}개)")
            
        except Exception as e:
            logger.error(f"HWP COM 제어 중 오류 발생: {str(e)}", exc_info=True)
            raise e
        finally:
            if hwp is not None:
                try:
                    hwp.Quit()
                    logger.debug("HWP COM 객체 자원 해제 완료.")
                except Exception as close_err:
                    logger.warning(f"HWP COM 프로세스 종료 중 경고: {str(close_err)}")
                # 참조 해제를 확실히 하여 메모리 누수 방지
                del hwp

        return extracted_items

    def apply_replacements(self, file_path: str, replacements: list[DetectionItem], temp_path: str) -> None:
        """
        [PoC 가드 적용] HWP 직접 치환 기능은 아키텍처 안정화 전까지 차단하고 예외 메시지를 띄웁니다.
        """
        logger.warning(f"HWP 직접 치환 시도 차단됨: {file_path}")
        raise NotImplementedError(
            "HWP 직접 치환 기능은 서식 보존 안정성 검증을 위한 PoC(개념 검증) 단계로 분류되어 "
            "현재 쓰기 기능이 제한되어 있습니다. 안전한 치환을 위해 HWPX 포맷으로 저장 후 다시 시도해 주십시오."
        )
