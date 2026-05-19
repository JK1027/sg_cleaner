import os
import unittest
import openpyxl
from app.services.detector import AnonymizeDetector
from app.services.excel_service import ExcelService
from app.models.detection_model import DetectionItem
from app.utils.path_helper import get_project_root

class TestAnonymizeEngine(unittest.TestCase):
    """
    익명화 탐지 엔진 및 Excel Safe Save 파이프라인 단위 테스트
    """
    def setUp(self):
        self.project_root = get_project_root()
        self.test_dir = self.project_root / "tests" / "temp_test"
        os.makedirs(self.test_dir, exist_ok=True)
        
        # 1. 테스트용 더미 엑셀 파일 생성
        self.test_excel_path = str(self.test_dir / "test_data.xlsx")
        
        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "학급기록"
        
        # 일반 데이터 셀
        ws1["A1"] = "순번"
        ws1["B1"] = "학생 이름"
        ws1["C1"] = "특이사항 및 학교 활동"
        
        ws1["A2"] = 1
        ws1["B2"] = "김민수" # 탐색 대상
        ws1["C2"] = "김민수 학생은 서울중학교 과학 탐구반에서 주도적으로 활동함." # 탐색 대상 (이름, 학교 포함)
        
        # 수식 셀 (스킵되어야 함)
        ws1["A3"] = "=SUM(A2:A2)"
        ws1["B3"] = "이서연" # 탐색 대상
        ws1["C3"] = "이서연 학생은 항상 성실함."
        
        # 병합 셀 구성 (B4:C4 병합)
        ws1.merge_cells("B4:C4")
        ws1["B4"] = "홍길동 학생이 전출 감." # 대표 셀
        
        # 숨김 시트 생성
        ws2 = wb.create_sheet("비공개기록")
        ws2.sheet_state = "hidden" # 숨김 속성 부여
        ws2["A1"] = "비공개"
        ws2["B1"] = "김민수" # 탐지되면 안 됨 (숨김 시트이므로)
        
        wb.save(self.test_excel_path)
        wb.close()

    def tearDown(self):
        # 테스트 임시 파일 및 폴더 삭제 (Clean up)
        if os.path.exists(self.test_excel_path):
            os.remove(self.test_excel_path)
            
        test_out = self.test_dir / "test_data_anonymized.xlsx"
        if os.path.exists(test_out):
            os.remove(test_out)
            
        mapping_out = self.test_dir / "mapping.csv"
        if os.path.exists(mapping_out):
            os.remove(mapping_out)
            
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    def test_detector_scanning(self):
        """규칙 기반 탐지 및 병합 셀/숨김 시트/수식 필터링 검증"""
        detector = AnonymizeDetector(
            student_names=["김민수", "이서연", "홍길동"],
            school_names=["서울중학교"]
        )
        
        results = detector.scan_workbook(self.test_excel_path)
        
        # 1. 탐지 개수 확인
        # 김민수: B2, C2 (2개)
        # 이서연: B3 (1개 - A3 수식 셀은 제외)
        # 홍길동: B4 (1개 - 병합 셀 대표 셀인 B4만 검출되고 C4는 MergedCell이므로 스킵됨)
        # 서울중학교: C2 (1개)
        # 비공개기록 시트는 숨김 시트이므로 탐지 안 됨.
        # 총 기대 탐지 개수: 6개
        self.assertEqual(len(results), 6)
        
        # 2. 매핑 대장 자동 인덱싱 생성 확인
        mapping = detector.get_full_mapping()
        self.assertIn("김민수", mapping)
        self.assertEqual(mapping["김민수"], "학생1")
        self.assertEqual(mapping["이서연"], "학생2")
        self.assertEqual(mapping["홍길동"], "학생3")
        self.assertEqual(mapping["서울중학교"], "학교A")

    def test_safe_save_flow(self):
        """Safe Save 4단계 저장 및 데이터 무결성 검증"""
        detector = AnonymizeDetector(
            student_names=["김민수"],
            school_names=["서울중학교"]
        )
        results = detector.scan_workbook(self.test_excel_path)
        
        excel_service = ExcelService()
        output_dir = str(self.test_dir)
        
        # Safe Save 치환 저장 실행
        final_path = excel_service.apply_replacements_safe(self.test_excel_path, results, output_dir)
        
        self.assertTrue(os.path.exists(final_path))
        self.assertIn("test_data_anonymized.xlsx", final_path)
        
        # 저장본이 다시 제대로 열리고 치환이 반영되었는지 확인
        wb = openpyxl.load_workbook(final_path, data_only=True)
        ws = wb["학급기록"]
        
        # 김민수 -> 학생1로 잘 바뀌었는지 확인
        self.assertEqual(ws["B2"].value, "학생1")
        self.assertEqual(ws["C2"].value, "학생1 학생은 학교A 과학 탐구반에서 주도적으로 활동함.")
        
        wb.close()

    def test_korean_path_handling(self):
        """한글 경로 및 파일명이 포함된 파일 처리 능력 검증"""
        # 한글 및 특수문자 파일 경로 설정
        korean_file_path = str(self.test_dir / "생활기록부_테스트_★데이터.xlsx")
        
        # 임시 파일 복사
        import shutil
        shutil.copy2(self.test_excel_path, korean_file_path)
        
        try:
            detector = AnonymizeDetector(student_names=["김민수"], school_names=[])
            results = detector.scan_workbook(korean_file_path)
            
            # 김민수 2건 검출 확인
            self.assertEqual(len(results), 2)
            
            # Safe Save 변환 적용
            excel_service = ExcelService()
            final_path = excel_service.apply_replacements_safe(korean_file_path, results, str(self.test_dir))
            
            self.assertTrue(os.path.exists(final_path))
            self.assertIn("생활기록부_테스트_★데이터_anonymized.xlsx", final_path)
            
            # 클린업
            if os.path.exists(final_path):
                os.remove(final_path)
        finally:
            if os.path.exists(korean_file_path):
                os.remove(korean_file_path)

    def test_missing_file_handling(self):
        """존재하지 않는 파일 처리 시 예외 롤백 처리 검증"""
        excel_service = ExcelService()
        dummy_item = DetectionItem(
            file_path="non_existent.xlsx",
            sheet_name="Sheet1",
            cell_address="A1",
            original_value="김민수",
            match_value="김민수",
            replacement="학생1",
            approved=True
        )
        
        # FileNotFoundError 예외 발생 확인
        with self.assertRaises(FileNotFoundError):
            excel_service.apply_replacements_safe("non_existent.xlsx", [dummy_item], str(self.test_dir))

if __name__ == "__main__":
    unittest.main()
