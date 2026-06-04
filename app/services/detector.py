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
        # 공백 제거 및 중복 제거 처리 (순서 보존)
        self.student_names = list(dict.fromkeys([name.strip() for name in student_names if name.strip()]))
        self.school_names = list(dict.fromkeys([school.strip() for school in school_names if school.strip()]))
        self.delete_keywords = list(dict.fromkeys([word.strip() for word in (delete_keywords or []) if word.strip()]))
        self.delete_replacement = delete_replacement
        
        # 가명화 대체 이름 맵
        self.student_mapping = {}
        self.school_mapping = {}
        self.delete_mapping = {}

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
