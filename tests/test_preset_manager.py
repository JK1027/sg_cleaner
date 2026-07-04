import os
import unittest
from app.services.preset_manager import PresetManager

class TestPresetManager(unittest.TestCase):
    """
    PresetManager 프리셋 CRUD 및 드래프트 자동 저장 기능 테스트
    """
    def setUp(self):
        self.presets_dir = PresetManager.get_presets_dir()
        self.created_ids = []
        self.created_excel_paths = []

    def tearDown(self):
        # 테스트 도중 생성한 파일들 정리
        for file_id in self.created_ids:
            try:
                PresetManager.delete_preset(file_id)
            except Exception:
                pass
        
        # 임시 엑셀 파일들 정리
        for excel_path in self.created_excel_paths:
            if os.path.exists(excel_path):
                try:
                    os.remove(excel_path)
                except Exception:
                    pass
        
        # 임시 draft 파일 정리
        app_data = os.path.dirname(self.presets_dir)
        draft_path = os.path.join(app_data, "draft.json")
        if os.path.exists(draft_path):
            try:
                os.remove(draft_path)
            except Exception:
                pass

    def test_preset_crud_flow(self):
        """프리셋의 생성, 스캔, 로드, 수정, 삭제 일련의 수명주기 동작 테스트"""
        payload = {
            "students": ["홍길동", "임꺽정"],
            "schools": ["활빈학교"],
            "delete_keywords": ["도적"],
            "delete_replacement": "의적"
        }
        display_name = "테스트학급"
        
        # 1. 새 프리셋 생성
        file_id = PresetManager.create_preset(display_name, payload)
        self.assertTrue(len(file_id) > 0)
        self.created_ids.append(file_id)
        
        # 2. 프리셋 정보 목록 스캔
        presets_info = PresetManager.get_presets_info()
        self.assertIn(file_id, presets_info)
        self.assertEqual(presets_info[file_id]["name"], display_name)
        
        # 3. 프리셋 데이터 파일 로드
        loaded = PresetManager.load_preset(file_id)
        self.assertEqual(loaded["name"], display_name)
        self.assertEqual(loaded["students"], ["홍길동", "임꺽정"])
        self.assertEqual(loaded["schools"], ["활빈학교"])
        self.assertEqual(loaded["delete_keywords"], ["도적"])
        self.assertEqual(loaded["delete_replacement"], "의적")
        
        # 4. 수정 및 덮어쓰기 저장
        payload["students"] = ["홍길동", "임꺽정", "신돌석"]
        PresetManager.save_preset(file_id, display_name, payload)
        
        loaded_after_edit = PresetManager.load_preset(file_id)
        self.assertEqual(loaded_after_edit["students"], ["홍길동", "임꺽정", "신돌석"])
        
        # 5. 프리셋 삭제
        PresetManager.delete_preset(file_id)
        self.created_ids.remove(file_id)
        
        presets_info_after_delete = PresetManager.get_presets_info()
        self.assertNotIn(file_id, presets_info_after_delete)

    def test_empty_preset_handling(self):
        """빈 데이터를 가진 템플릿용 프리셋도 올바르게 저장 및 로드되는지 검증"""
        empty_payload = {
            "students": [],
            "schools": [],
            "delete_keywords": [],
            "delete_replacement": ""
        }
        
        file_id = PresetManager.create_preset("빈템플릿", empty_payload)
        self.created_ids.append(file_id)
        
        loaded = PresetManager.load_preset(file_id)
        self.assertEqual(loaded["name"], "빈템플릿")
        self.assertEqual(loaded["students"], [])
        self.assertEqual(loaded["schools"], [])
        self.assertEqual(loaded["delete_keywords"], [])
        self.assertEqual(loaded["delete_replacement"], "")

    def test_draft_saving_and_restoring(self):
        """작성 중인 데이터 자동 백업용 draft.json의 저장 및 로드 기능 검증"""
        payload = {
            "students": ["입력중학생"],
            "schools": ["입력중학교"],
            "delete_keywords": ["삭제중단어"],
            "delete_replacement": "기본"
        }
        
        # 드래프트 임시 저장
        PresetManager.save_draft(payload)
        
        # 복구 로드
        loaded_draft = PresetManager.load_draft()
        self.assertIsNotNone(loaded_draft)
        self.assertEqual(loaded_draft["students"], ["입력중학생"])
        self.assertEqual(loaded_draft["schools"], ["입력중학교"])
        self.assertEqual(loaded_draft["delete_keywords"], ["삭제중단어"])
        self.assertEqual(loaded_draft["delete_replacement"], "기본")

    def test_excel_preset_export_and_import(self):
        """엑셀 프리셋의 export 및 import 통합 기능 검증"""
        payload = {
            "students": ["1101 홍길동", "1102 임꺽정"],
            "schools": ["서울중학교", "한국중학교"],
            "delete_keywords": ["삭제키워드1"],
            "delete_replacement": "대체어"
        }
        
        temp_excel = os.path.join(os.path.dirname(self.presets_dir), "temp_preset_test.xlsx")
        self.created_excel_paths.append(temp_excel)
        
        # 1. 엑셀 내보내기 수행
        PresetManager.export_preset_to_excel(payload, temp_excel)
        self.assertTrue(os.path.exists(temp_excel))
        
        # 2. 엑셀 다시 읽어오기 수행
        imported = PresetManager.import_preset_from_excel(temp_excel)
        
        # 데이터 원형 일치 여부 확인
        self.assertEqual(imported["students"], ["1101 홍길동", "1102 임꺽정"])
        self.assertEqual(imported["schools"], ["서울중학교", "한국중학교"])
        self.assertEqual(imported["delete_keywords"], ["삭제키워드1"])
        self.assertEqual(imported["delete_replacement"], "대체어")

    def test_excel_preset_header_order_and_empty_rows(self):
        """엑셀 업로드 시 열의 순서가 무작위이거나 빈 셀(행)이 존재할 때의 안전성 검증"""
        import openpyxl
        
        temp_excel = os.path.join(os.path.dirname(self.presets_dir), "temp_preset_irregular.xlsx")
        self.created_excel_paths.append(temp_excel)
        
        # 1. 수동으로 열이 뒤섞이고 빈 행이 존재하는 openpyxl 워크북 생성
        wb = openpyxl.Workbook()
        ws = wb.active
        # 헤더 순서 섞기 (학교명 -> 삭제 대체 텍스트 -> 학생 이름 -> 삭제할 단어)
        ws.append(["학교명", "삭제 대체 텍스트", "학생 이름", "삭제할 단어"])
        
        # 첫 번째 데이터 행
        ws.append(["서울중", "기본대체", "1101 홍길동", "지울단어1"])
        # 두 번째 데이터 행
        ws.append(["경기중", "", "1102 김영희", ""])
        # 세 번째 데이터 행 (학생 이름만 있고 나머지는 빈 값)
        ws.append(["", "", "1103 이철수", ""])
        
        wb.save(temp_excel)
        wb.close()
        
        # 2. 유연한 헤더 정상화 및 안전한 빈 행 무시 기능이 탑재된 import 실행
        imported = PresetManager.import_preset_from_excel(temp_excel)
        
        # 3. 데이터 검증
        self.assertEqual(imported["students"], ["1101 홍길동", "1102 김영희", "1103 이철수"])
        self.assertEqual(imported["schools"], ["서울중", "경기중"])
        self.assertEqual(imported["delete_keywords"], ["지울단어1"])
        self.assertEqual(imported["delete_replacement"], "기본대체")

if __name__ == "__main__":
    unittest.main()
