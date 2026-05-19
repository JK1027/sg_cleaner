import openpyxl
from app.models.detection_model import DetectionItem
from app.utils.logger import logger

class AnonymizeDetector:
    """
    사용자가 입력한 학생 이름/학교명 패턴 목록에 근거하여 Excel 셀의 텍스트 데이터를 검색 및 탐지하는 엔진.
    """
    def __init__(self, student_names: list[str], school_names: list[str]):
        # 공백 제거 및 중복 제거 처리
        self.student_names = list(set([name.strip() for name in student_names if name.strip()]))
        self.school_names = list(set([school.strip() for school in school_names if school.strip()]))
        
        # 탐색 과정 중 고유한 익명화 대체 이름(예: 학생1, 학교A)을 관리하기 위한 매핑 저장소
        self.student_mapping = {} # {'김민수': '학생1'}
        self.school_mapping = {}   # {'서울중학교': '학교A'}

    def scan_workbook(self, file_path: str) -> list[DetectionItem]:
        """
        주어진 Excel 통합 문서를 읽고, 모든 활성 시트의 셀을 탐색하여 매칭 결과를 수집합니다.
        
        :param file_path: 탐색 대상 Excel 파일 경로
        :return: DetectionItem 객체 목록
        """
        results = []
        try:
            # 스캔 시에는 수식 분석이 아닌 최종 표시 텍스트를 기준으로 탐색해야 하므로
            # data_only=True로 로드합니다. (수정 시에는 data_only=False 사용)
            wb = openpyxl.load_workbook(file_path, data_only=True, read_only=False)
        except Exception as e:
            logger.error(f"Excel 파일 로드 실패 ({file_path}): {str(e)}")
            raise e

        # 매핑 카운터
        student_count = len(self.student_mapping) + 1
        school_count = len(self.school_mapping) + 1

        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            
            # ⚠️ 숨김 시트 스킵 처리
            if getattr(sheet, "sheet_state", "visible") != "visible":
                logger.info(f"숨김 시트 스킵됨: {sheet_name}")
                continue
                
            logger.info(f"시트 스캔 중: {sheet_name} ({file_path})")
            
            # 행과 열을 순회하며 데이터 탐색
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value is None:
                        continue
                        
                    # ⚠️ 병합 셀 예외 처리:
                    # openpyxl에서 대표 셀이 아닌 하위 병합 셀들은 MergedCell 타입으로 분류됨.
                    # MergedCell은 수정 및 데이터 조회가 불가능하므로 스킵 처리.
                    if type(cell).__name__ == "MergedCell":
                        continue
                        
                    cell_text = str(cell.value)
                    
                    # ⚠️ 수식은 탐지 및 수정 대상에서 제외
                    if cell_text.startswith("="):
                        continue
                        
                    # 1. 학생 이름 매칭 (정합 검색 및 치환 관계 구성)
                    for name in self.student_names:
                        if name in cell_text:
                            # 이 이름에 대한 익명화 매핑이 아직 없으면 새로 생성
                            if name not in self.student_mapping:
                                self.student_mapping[name] = f"학생{student_count}"
                                student_count += 1
                                
                            item = DetectionItem(
                                file_path=file_path,
                                sheet_name=sheet_name,
                                cell_address=cell.coordinate,
                                original_value=cell_text,
                                match_value=name,
                                replacement=self.student_mapping[name],
                                approved=True
                            )
                            results.append(item)
                            logger.debug(f"이름 탐지: {cell.coordinate} -> {name}")

                    # 2. 학교명 매칭
                    for school in self.school_names:
                        if school in cell_text:
                            if school not in self.school_mapping:
                                # A, B, C... 순으로 알파벳 변환 부여
                                self.school_mapping[school] = f"학교{chr(64 + school_count)}"
                                school_count += 1
                                
                            item = DetectionItem(
                                file_path=file_path,
                                sheet_name=sheet_name,
                                cell_address=cell.coordinate,
                                original_value=cell_text,
                                match_value=school,
                                replacement=self.school_mapping[school],
                                approved=True
                            )
                            results.append(item)
                            logger.debug(f"학교명 탐지: {cell.coordinate} -> {school}")

        wb.close()
        logger.info(f"스캔 완료: {file_path} (탐색 개수: {len(results)}개)")
        return results

    def get_full_mapping(self) -> dict[str, str]:
        """학생 및 학교의 전체 누적 치환 매핑 대장을 병합하여 반환합니다."""
        full_map = {}
        full_map.update(self.student_mapping)
        full_map.update(self.school_mapping)
        return full_map
