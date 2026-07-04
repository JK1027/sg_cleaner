import unittest
from app.services.detector import AnonymizeDetector
from app.services.base_processor import ExtractedTextItem

class TestHomonymResolution(unittest.TestCase):
    """
    동명이인 익명화 혼선 해결을 위한 다중 필터 기반 후보 추천 알고리즘 및 
    DetectionItem 내 후보군(candidates), 신뢰도(confidence) 누적 무결성 테스트
    """

    def test_homonym_resolution_by_filename(self):
        """
        1. 파일명에 학급 정보가 명시된 경우 동명이인 중 해당 학급에 맞는 가명이
        최적 후보로 추천되고 신뢰도가 높게 유지되는지 검증
        """
        # 프리셋 설정: 홍길동이 1학년 1반(1105)과 1학년 2반(1205)에 동명이인으로 존재
        student_names = ["1105 홍길동", "1205 홍길동"]
        
        # 파일명에 '1-1'이 들어있는 시나리오
        file_path_1 = "C:/School/1학년 1반_학생부.xlsx"
        detector = AnonymizeDetector(student_names=student_names, school_names=[])
        
        # 가상의 본문 텍스트 추출물
        text_items = [
            ExtractedTextItem(
                location_context="학적현황",
                location_detail="A1",
                text="우수학생 홍길동 상장 수여"
            )
        ]
        
        results = detector.scan_text_items(text_items, file_path_1)
        self.assertEqual(len(results), 1)
        
        item = results[0]
        self.assertTrue(item.is_ambiguous)
        # 1-1반 홍길동의 대체 가명인 '학생1105'가 선택되어야 함.
        self.assertEqual(item.replacement, "학생1105")
        self.assertIn("파일명", item.ambiguity_reason)
        # 파일명 매칭 가산점으로 인해 높은 신뢰도 획득
        self.assertGreater(item.confidence, 0.8)
        
        # 후보자 리스트에 두 후보 모두 포함되어야 함
        # 포맷: "가명:학반정보" -> "학생1105:1-1반 5번", "학생1205:1-2반 5번"
        self.assertEqual(len(item.candidates), 2)
        self.assertTrue(any("학생1105" in c for c in item.candidates))
        self.assertTrue(any("학생1205" in c for c in item.candidates))

    def test_homonym_resolution_by_sheetname(self):
        """
        2. 시트명에 학급 정보가 명시된 경우 동명이인 최적 매칭 검증
        """
        student_names = ["1105 홍길동", "1205 홍길동"]
        file_path = "C:/School/전교생명렬표.xlsx" # 파일명엔 단서 없음
        
        detector = AnonymizeDetector(student_names=student_names, school_names=[])
        
        # 시트명(location_context)에 '1-2'가 들어있는 시나리오
        text_items = [
            ExtractedTextItem(
                location_context="1학년 2반 기록",
                location_detail="C10",
                text="홍길동 행동특성 관찰기록"
            )
        ]
        
        results = detector.scan_text_items(text_items, file_path)
        self.assertEqual(len(results), 1)
        
        item = results[0]
        self.assertTrue(item.is_ambiguous)
        self.assertEqual(item.replacement, "학생1205")
        self.assertIn("시트명/구역", item.ambiguity_reason)
        self.assertGreater(item.confidence, 0.8)

    def test_homonym_resolution_by_voting(self):
        """
        3. 주변 학생 이름 분포(Voting)를 고려한 최적 매칭 검증
        """
        # 주변 학생으로 등록될 김민수(1-1반 1번)가 있다고 가정
        student_names = ["1105 홍길동", "1205 홍길동", "1101 김민수"]
        file_path = "C:/School/일반기록.xlsx" # 파일명/시트명 단서 없음
        
        detector = AnonymizeDetector(student_names=student_names, school_names=[])
        
        # 홍길동 근처에 '김민수'가 배치됨
        # text_items 순서대로 스캔되므로 앞뒤 5개 내외를 묶어서 분석함
        text_items = [
            ExtractedTextItem(location_context="본문", location_detail="1", text="김민수 학생은 급식 지도를 잘 따름."),
            ExtractedTextItem(location_context="본문", location_detail="2", text="홍길동 학생도 함께 참여함.")
        ]
        
        results = detector.scan_text_items(text_items, file_path)
        
        # 김민수와 홍길동이 모두 검출되어야 함 (총 2건)
        self.assertEqual(len(results), 2)
        
        # 홍길동(is_ambiguous=True) 결과 분석
        hong_item = next(it for it in results if it.match_value == "홍길동")
        self.assertTrue(hong_item.is_ambiguous)
        # 주변 학생 김민수(1-1반)가 1-1반 소속이므로 1-1반 홍길동(학생1105)으로 매칭되어야 함.
        self.assertEqual(hong_item.replacement, "학생1105")
        self.assertIn("주변 학생", hong_item.ambiguity_reason)
        self.assertGreater(hong_item.confidence, 0.8)

    def test_homonym_resolution_fallback(self):
        """
        4. 아무런 단서가 없을 때의 폴백 매칭 검증 (is_ambiguous=True, 낮은 신뢰도)
        """
        student_names = ["1105 홍길동", "1205 홍길동"]
        file_path = "C:/School/일반기록.xlsx"
        
        detector = AnonymizeDetector(student_names=student_names, school_names=[])
        
        text_items = [
            ExtractedTextItem(location_context="본문", location_detail="1", text="홍길동 학생의 우수한 성적")
        ]
        
        results = detector.scan_text_items(text_items, file_path)
        self.assertEqual(len(results), 1)
        
        item = results[0]
        self.assertTrue(item.is_ambiguous)
        # 단서가 없으면 첫 번째 후보(학생1105)를 제안하되 신뢰도는 낮아야 함
        self.assertEqual(item.replacement, "학생1105")
        self.assertIn("단서 없음", item.ambiguity_reason)
        # 후보가 2명이므로 신뢰도는 1/2 = 0.5 수준이어야 함
        self.assertLessEqual(item.confidence, 0.5)

if __name__ == "__main__":
    unittest.main()
