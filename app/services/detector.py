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

    def _parse_class_info(self, replacement: str) -> str:
        """가명 명칭에서 반/번호 정보를 파싱하여 읽기 쉬운 텍스트로 반환합니다."""
        import re
        m = re.search(r"\d+", replacement)
        if m:
            num_str = m.group(0)
            if len(num_str) == 4:
                g = num_str[0]
                c = num_str[1]
                n = int(num_str[2:])
                return f"{g}-{c}반 {n}번"
            elif len(num_str) == 5:
                g = num_str[0]
                c = int(num_str[1:3])
                n = int(num_str[3:])
                return f"{g}-{c}반 {n}번"
            elif len(num_str) == 3:
                g = num_str[0]
                c = num_str[1]
                n = int(num_str[2:])
                return f"{g}-{c}반 {n}번"
        return "사용자 정의"

    def _build_student_mapping(self) -> None:
        """
        학생 명렬표 데이터를 정밀 파싱하여 학번 기반 또는 사용자 정의 가명 맵을 빌드합니다.
        동명이인이 있는 경우 self.student_homonyms 구조에 각 가명 후보군을 누적합니다.
        """
        import re
        student_pattern = re.compile(r"^(\d{3,6})\s*([가-힣]{2,5})$")
        
        self.student_homonyms = {}
        
        def add_candidate(name: str, replacement: str):
            info = self._parse_class_info(replacement)
            if name not in self.student_homonyms:
                self.student_homonyms[name] = []
            else:
                logger.warning(
                    f"동명이인 매핑 충돌 감지: '{name}'은(는) 이미 등록되어 있습니다. "
                    f"새로운 매핑 '{replacement}'(으)로 후보가 추가됩니다."
                )
            if not any(c["replacement"] == replacement for c in self.student_homonyms[name]):
                self.student_homonyms[name].append({
                    "replacement": replacement,
                    "info": info
                })

        for raw_name in self.raw_student_names:
            if ":" in raw_name:
                parts = raw_name.split(":", 1)
                name = parts[0].strip()
                replacement = parts[1].strip()
                if name:
                    self.student_names.append(name)
                    add_candidate(name, replacement)
                continue

            match = student_pattern.match(raw_name)
            if match:
                num = match.group(1)
                name = match.group(2)
                self.student_names.append(name)
                add_candidate(name, f"학생{num}")
            else:
                self.student_names.append(raw_name)
                
        # 최종 리스트 중복 제거
        self.student_names = list(dict.fromkeys(self.student_names))
        
        # 1개 초과의 후보군을 가진 이름들만 동명이인으로 필터링
        self.homonym_names = {name for name, candidates in self.student_homonyms.items() if len(candidates) > 1}
        
        # 기본 매핑 테이블 빌드 (첫 번째 후보를 일단 기본 매핑으로 저장)
        self.custom_student_replacements = {}
        for name, candidates in self.student_homonyms.items():
            if candidates:
                self.custom_student_replacements[name] = candidates[0]["replacement"]

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

    def _resolve_homonym(self, file_path: str, location_context: str, preview_text: str, surround_text: str, name: str) -> tuple[str, float, str, list[str]]:
        """
        동명이인의 대체어 후보군 중 최적 후보를 다중 필터(파일명, 시트명, 주변학생 반 분포)로 결정하고
        (최종가명, 신뢰도점수, 판정근거, candidates리스트) 를 반환합니다.
        """
        import os
        import re
        
        candidates = self.student_homonyms.get(name, [])
        if not candidates:
            return name, 1.0, "단일 매핑", []
            
        file_name = os.path.basename(file_path)
        
        # 후보자별 점수 맵 초기화
        scores = {c["replacement"]: 0.0 for c in candidates}
        reasons = {c["replacement"]: [] for c in candidates}
        
        # 콤보박스에 노출할 candidates 문자열 리스트 (포맷: "가명:학반정보")
        candidate_strings = [f"{c['replacement']}:{c['info']}" for c in candidates]
        
        # 각 후보에 대해 조건 분석
        for c in candidates:
            rep = c["replacement"]
            info = c["info"]
            
            # info에서 학년과 반 정보를 더 유연하게 추출
            grade_match = re.search(r"(\d+)\s*학년|(\d+)-", info)
            ban_match = re.search(r"(\d+)\s*반", info)
            
            grade, ban = None, None
            if grade_match:
                grade = grade_match.group(1) or grade_match.group(2)
            if ban_match:
                ban = ban_match.group(1)
            
            if not grade or not ban:
                # info에서 파싱 실패 시 rep(예: 학생1105)에서 파싱
                m_num = re.search(r"\d+", rep)
                if m_num:
                    num_str = m_num.group(0)
                    if len(num_str) == 4:
                        grade, ban = num_str[0], num_str[1]
                    elif len(num_str) == 5:
                        grade, ban = num_str[0], str(int(num_str[1:3]))
                    elif len(num_str) == 3:
                        grade, ban = num_str[0], num_str[1]
            
            if grade and ban:
                # 1. 파일명 매칭 (Weight: 10.0)
                file_patterns = [
                    f"{grade}-{ban}",
                    f"{grade}학년 {ban}반",
                    f"{grade}학년{ban}반",
                    f"{grade}{int(ban):02d}",
                    f"{grade}{ban}"
                ]
                if any(pat in file_name for pat in file_patterns):
                    scores[rep] += 10.0
                    reasons[rep].append(f"파일명 '{grade}-{ban}' 매칭")
                
                # 2. 시트명 매칭 (Weight: 8.0)
                if any(pat in location_context for pat in file_patterns):
                    scores[rep] += 8.0
                    reasons[rep].append(f"시트명/구역 '{grade}-{ban}' 매칭")
                
                # 3. 주변 텍스트 학급 투표 (Weight: 5.0 * 학생수)
                for other_name in self.student_names:
                    if other_name == name:
                        continue
                    if other_name in surround_text:
                        other_candidates = self.student_homonyms.get(other_name, [])
                        # 동명이인이 아닌 일반 학생의 학반 정보를 활용하여 투표 진행
                        if len(other_candidates) == 1:
                            other_info = other_candidates[0]["info"]
                            if f"{grade}-{ban}반" in other_info:
                                scores[rep] += 5.0
                                reasons[rep].append(f"주변 학생 '{other_name}'")

        # 총합 점수 계산
        total_score = sum(scores.values())
        if total_score == 0:
            best_rep = candidates[0]["replacement"]
            # 4순위 (폴백): 단서가 없을 경우 신뢰도 50% 미만으로 책정하며 보류.
            confidence = min(0.49, round(1.0 / len(candidates), 2))
            reason_summary = "단서 없음 (기본 후보 제안)"
        else:
            best_rep = max(scores, key=scores.get)
            best_score = scores[best_rep]
            confidence = round(best_score / total_score, 2)
            
            matched_reasons = reasons[best_rep]
            if matched_reasons:
                reason_summary = ", ".join(matched_reasons) + " 기반 추천"
            else:
                reason_summary = "근접 매칭 가산 적용"
                
        return best_rep, confidence, reason_summary, candidate_strings

    def scan_text_items(self, text_items: list[ExtractedTextItem], file_path: str) -> list[DetectionItem]:
        """
        추출된 문서의 텍스트 아이템 리스트를 전달받아 패턴 매칭을 수행하고 DetectionItem 목록을 반환합니다.
        """
        results = []
        student_count = len(self.student_mapping) + 1
        school_count = len(self.school_mapping) + 1

        for item_idx, text_item in enumerate(text_items):
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
                            is_homonym = pattern in self.homonym_names
                            
                            if is_homonym:
                                # 동명이인 감지 위치 주변(앞뒤 200자)에 있는 타 학생들의 학급 분포 분석을 위한 surround_text 추출
                                before_part = cell_text[:idx]
                                if len(before_part) < 200:
                                    # 앞방향으로 이전 아이템들을 역순 스캔하며 결합
                                    for idx_s in range(item_idx - 1, -1, -1):
                                        if text_items[idx_s].location_context == text_item.location_context:
                                            before_part = text_items[idx_s].text + " " + before_part
                                            if len(before_part) >= 200:
                                                break
                                before_part = before_part[-200:]
                                
                                after_part = cell_text[idx + pat_len:]
                                if len(after_part) < 200:
                                    # 뒷방향으로 이후 아이템들을 순차 스캔하며 결합
                                    for idx_s in range(item_idx + 1, len(text_items)):
                                        if text_items[idx_s].location_context == text_item.location_context:
                                            after_part = after_part + " " + text_items[idx_s].text
                                            if len(after_part) >= 200:
                                                break
                                after_part = after_part[:200]
                                
                                surround_text = before_part + " " + pattern + " " + after_part
                                
                                best_rep, confidence, reason, candidates = self._resolve_homonym(
                                    file_path, text_item.location_context, preview_text, surround_text, pattern
                                )
                                
                                item = DetectionItem(
                                    file_path=file_path,
                                    location_context=text_item.location_context,
                                    location_detail=text_item.location_detail,
                                    context_preview=preview_text,
                                    original_value=cell_text,
                                    match_value=pattern,
                                    replacement=best_rep,
                                    approved=True,
                                    is_ambiguous=True,
                                    confidence=confidence,
                                    ambiguity_reason=reason,
                                    candidates=candidates
                                )
                            else:
                                if pattern not in self.student_mapping:
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
                                    approved=True,
                                    is_ambiguous=False,
                                    confidence=1.0,
                                    ambiguity_reason=""
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
                                approved=True,
                                is_ambiguous=False,
                                confidence=1.0,
                                ambiguity_reason=""
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
                                approved=True,
                                is_ambiguous=False,
                                confidence=1.0,
                                ambiguity_reason=""
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
