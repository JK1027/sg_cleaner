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

    def tearDown(self):
        # 테스트 도중 생성한 파일들 정리
        for file_id in self.created_ids:
            try:
                PresetManager.delete_preset(file_id)
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

if __name__ == "__main__":
    unittest.main()
