from app.models.detection_model import DetectionItem
from app.services.base_processor import ExtractedTextItem
from app.utils.logger import logger

def _make_school_label(n: int) -> str:
    """
    1 → 'A', 2 → 'B', ..., 26 → 'Z', 27 → 'AA', ...
    알파벳 레이블을 순차 생성합니다.
    """
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result

class AnonymizeDetector:
    """
    사용자가 입력한 학생 이름/학교명 패턴 목록에 근거하여 
    추출된 텍스트 리스트에서 개인정보를 탐색 및 매칭하는 비즈니스 엔진 클래스.
    """
    def __init__(self, student_names: list[str], school_names: list[str],
                 delete_keywords: list[str] = None, delete_replacement: str = ""):
        import re
        self.raw_student_names = list(dict.fromkeys([name.strip() for name in student_names if name.strip()]))
        self.raw_school_names = list(dict.fromkeys([school.strip() for school in school_names if school.strip()]))
        self.delete_keywords = list(dict.fromkeys([word.strip() for word in (delete_keywords or []) if word.strip()]))
        self.delete_replacement = delete_replacement
        
        self.student_names = []
        self.custom_student_replacements = {}
        self.school_names = []
        self.custom_school_replacements = {}
        
        self._build_student_mapping()
        self._build_school_mapping()
        
        # 가명화 대체 이름 맵
        self.student_mapping = {}
        self.school_mapping = {}
        self.delete_mapping = {}

    def _build_student_mapping(self) -> None:
        """
        학생 명렬표 데이터를 정밀 파싱하여 학번 기반 또는 사용자 정의 가명 맵을 빌드합니다.
        - 형식 A: '이름:변경예정' (예: '홍길동:대표학생') -> 사용자 정의 매핑
        - 형식 B: '1101 홍길동' -> 학번 기반 매핑 (학생1101)
        - 형식 C: '홍길동' -> 일반 이름
        """
        import re
        student_pattern = re.compile(r"^(\d{3,6})\s*([가-힣]{2,5})$")
        
        for raw_name in self.raw_student_names:
            if ":" in raw_name:
                parts = raw_name.split(":", 1)
                name = parts[0].strip()
                replacement = parts[1].strip()
                if name:
                    if name in self.custom_student_replacements:
                        logger.warning(
                            f"동명이인 매핑 충돌 감지: '{name}'은(는) 이미 '{self.custom_student_replacements[name]}'로 매핑되어 있습니다. "
                            f"새로운 매핑 '{replacement}'(으)로 덮어씌워집니다."
                        )
                    self.student_names.append(name)
                    self.custom_student_replacements[name] = replacement
                continue

            match = student_pattern.match(raw_name)
            if match:
                num = match.group(1)
                name = match.group(2)
                
                # 동명이인 매핑 충돌 방지 경고 로그 출력
                if name in self.custom_student_replacements:
                    logger.warning(
                        f"동명이인 매핑 충돌 감지: '{name}'은(는) 이미 '{self.custom_student_replacements[name]}'로 매핑되어 있습니다. "
                        f"새로운 매핑 '학생{num}'(으)로 덮어씌워집니다."
                    )
                
                self.student_names.append(name)
                self.custom_student_replacements[name] = f"학생{num}"
            else:
                self.student_names.append(raw_name)
                
        # 최종 리스트 중복 제거
        self.student_names = list(dict.fromkeys(self.student_names))

    def _build_school_mapping(self) -> None:
        """
        학교명 데이터를 파싱하여 사용자 정의 가명 맵을 빌드합니다.
        - 형식 A: '학교명:변경예정' (예: '서울중학교:S중') -> 사용자 정의 매핑
        - 형식 B: '서울중학교' -> 일반 학교명
        """
        for raw_school in self.raw_school_names:
            if ":" in raw_school:
                parts = raw_school.split(":", 1)
                school = parts[0].strip()
                replacement = parts[1].strip()
                if school:
                    self.school_names.append(school)
                    self.custom_school_replacements[school] = replacement
            else:
                self.school_names.append(raw_school)
        self.school_names = list(dict.fromkeys(self.school_names))

    def scan_text_items(self, text_items: list[ExtractedTextItem], file_path: str) -> list[DetectionItem]:
        """
        추출된 문서의 텍스트 아이템 리스트를 전달받아 패턴 매칭을 수행하고 DetectionItem 목록을 반환합니다.
        """
        results = []
        student_count = len(self.student_mapping) + 1
        school_count = len(self.school_mapping) + 1

        for text_item in text_items:
            cell_text = text_item.text
            
            # 패턴 구성 및 정렬 (길이 역순)
            patterns = []
            for name in self.student_names:
                patterns.append((name, "student"))
            for school in self.school_names:
                patterns.append((school, "school"))
            for word in self.delete_keywords:
                patterns.append((word, "delete"))
                
            patterns.sort(key=lambda x: len(x[0]), reverse=True)
            
            matched_intervals = [] # list of (start_idx, end_idx)
            
            for pattern, pat_type in patterns:
                start_find = 0
                while True:
                    idx = cell_text.find(pattern, start_find)
                    if idx == -1:
                        break
                    
                    pat_len = len(pattern)
                    end_idx = idx + pat_len
                    
                    # 기존 매칭 영역과 오버랩 여부 체크
                    overlap = False
                    for m_start, m_end in matched_intervals:
                        if not (end_idx <= m_start or idx >= m_end):
                            overlap = True
                            break
                            
                    if not overlap:
                        matched_intervals.append((idx, end_idx))
                        
                        # 문맥 미리보기 추출 (앞뒤 약 45자씩 충분한 길이 확보)
                        start_preview = max(0, idx - 45)
                        end_preview = min(len(cell_text), idx + pat_len + 45)
                        preview_text = cell_text[start_preview:end_preview]
                        if start_preview > 0:
                            preview_text = "..." + preview_text
                        if end_preview < len(cell_text):
                            preview_text = preview_text + "..."

                        if pat_type == "student":
                            if pattern not in self.student_mapping:
                                # ⚠️ TODO: 향후 사용자 옵션에 따라 "학생1101" 외에 "1학년1반1번" 등 출력 포맷 커스터마이징 대응
                                # ⚠️ TODO: 문서 상에 "1101 홍길동" 형태로 학번과 이름이 붙어 있는 에지케이스 감지 및 전체 일괄 치환 가드 추가 검토
                                if pattern in self.custom_student_replacements:
                                    self.student_mapping[pattern] = self.custom_student_replacements[pattern]
                                else:
                                    self.student_mapping[pattern] = f"학생{student_count}"
                                    student_count += 1
                            item = DetectionItem(
                                file_path=file_path,
                                location_context=text_item.location_context,
                                location_detail=text_item.location_detail,
                                context_preview=preview_text,
                                original_value=cell_text,
                                match_value=pattern,
                                replacement=self.student_mapping[pattern],
                                approved=True
                            )
                            results.append(item)
                            
                        elif pat_type == "school":
                            if pattern not in self.school_mapping:
                                if pattern in self.custom_school_replacements:
                                    self.school_mapping[pattern] = self.custom_school_replacements[pattern]
                                else:
                                    self.school_mapping[pattern] = f"학교{_make_school_label(school_count)}"
                                    school_count += 1
                            item = DetectionItem(
                                file_path=file_path,
                                location_context=text_item.location_context,
                                location_detail=text_item.location_detail,
                                context_preview=preview_text,
                                original_value=cell_text,
                                match_value=pattern,
                                replacement=self.school_mapping[pattern],
                                approved=True
                            )
                            results.append(item)
                            
                        elif pat_type == "delete":
                            if pattern not in self.delete_mapping:
                                self.delete_mapping[pattern] = self.delete_replacement
                            item = DetectionItem(
                                file_path=file_path,
                                location_context=text_item.location_context,
                                location_detail=text_item.location_detail,
                                context_preview=preview_text,
                                original_value=cell_text,
                                match_value=pattern,
                                replacement=self.delete_mapping[pattern],
                                approved=True
                            )
                            results.append(item)
                            
                    start_find = idx + 1

        logger.info(f"패턴 매칭 완료: {file_path} (매칭 건수: {len(results)}건)")
        return results

    def get_full_mapping(self) -> dict[str, str]:
        """학생, 학교 및 삭제 키워드의 전체 누적 치환 매핑 대장을 병합하여 반환합니다."""
        full_map = {}
        full_map.update(self.student_mapping)
        full_map.update(self.school_mapping)
        full_map.update(self.delete_mapping)
        return full_map
