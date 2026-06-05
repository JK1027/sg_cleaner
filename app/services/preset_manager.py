import os
import json
import uuid
from datetime import datetime
from PySide6.QtCore import QStandardPaths
from app.utils.logger import logger

class PresetManager:
    """
    사용자 로컬 AppData 디렉토리 내 presets 폴더에서 프리셋(JSON)의 CRUD를 담당하고
    임시 입력 유실을 방지하는 draft.json 자동 저장을 처리하는 서비스 클래스입니다.
    """
    
    @staticmethod
    def get_presets_dir() -> str:
        """프리셋이 저장되는 AppData 디렉토리 경로를 반환합니다. 디렉토리가 없으면 자동 생성합니다."""
        app_data = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if not app_data:
            # Fallback to user home directory
            app_data = os.path.join(os.path.expanduser("~"), ".sg_cleaner")
        
        # QStandardPaths가 앱 명칭을 포함하지 않는 경우를 대비해 확실히 sg_cleaner 폴더 분리
        if "sg_cleaner" not in app_data.lower() and "sgcleaner" not in app_data.lower():
            app_data = os.path.join(app_data, "SgCleaner")
            
        presets_dir = os.path.join(app_data, "presets")
        os.makedirs(presets_dir, exist_ok=True)
        return presets_dir

    @classmethod
    def get_presets_info(cls) -> dict[str, dict]:
        """
        저장된 모든 프리셋 파일(preset_*.json)을 스캔하여
        { file_id: { "name": ..., "updated_at": ..., "created_at": ... } } 형식으로 반환합니다.
        수정일(updated_at) 내림차순(최신순)으로 정렬해 반환합니다.
        """
        presets_dir = cls.get_presets_dir()
        presets_info = {}
        
        if not os.path.exists(presets_dir):
            return presets_info
            
        for filename in os.listdir(presets_dir):
            if filename.startswith("preset_") and filename.endswith(".json"):
                file_path = os.path.join(presets_dir, filename)
                file_id = filename[7:-5] # "preset_"과 ".json" 제외
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        presets_info[file_id] = {
                            "name": data.get("name", "이름 없음"),
                            "created_at": data.get("created_at", ""),
                            "updated_at": data.get("updated_at", ""),
                            "file_path": file_path
                        }
                except Exception as e:
                    logger.error(f"프리셋 파일 읽기 실패 ({filename}): {str(e)}")
                    
        # updated_at을 기준으로 정렬하여 딕셔너리 재구성
        sorted_presets = sorted(
            presets_info.items(),
            key=lambda x: x[1].get("updated_at", ""),
            reverse=True
        )
        return dict(sorted_presets)

    @classmethod
    def load_preset(cls, file_id: str) -> dict:
        """지정한 file_id의 프리셋 데이터를 파일로부터 읽어와 딕셔너리로 반환합니다."""
        presets_dir = cls.get_presets_dir()
        file_path = os.path.join(presets_dir, f"preset_{file_id}.json")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"프리셋 파일을 찾을 수 없습니다: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def create_preset(cls, display_name: str, payload: dict) -> str:
        """
        새로운 고유 UUID 기반의 프리셋을 생성하고 저장합니다.
        생성된 file_id를 반환합니다.
        """
        file_id = uuid.uuid4().hex
        presets_dir = cls.get_presets_dir()
        file_path = os.path.join(presets_dir, f"preset_{file_id}.json")
        
        now = datetime.now().isoformat()
        
        preset_data = {
            "version": "1.0",
            "name": display_name,
            "created_at": now,
            "updated_at": now,
            "students": payload.get("students", []),
            "schools": payload.get("schools", []),
            "delete_keywords": payload.get("delete_keywords", []),
            "delete_replacement": payload.get("delete_replacement", "")
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(preset_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"새 프리셋 생성 성공: {display_name} ({file_path})")
        return file_id

    @classmethod
    def save_preset(cls, file_id: str, display_name: str, payload: dict) -> None:
        """기존 프리셋 정보를 덮어쓰기 저장합니다."""
        presets_dir = cls.get_presets_dir()
        file_path = os.path.join(presets_dir, f"preset_{file_id}.json")
        
        # 기존 데이터 로드하여 created_at 보존 시도
        created_at = datetime.now().isoformat()
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    created_at = old_data.get("created_at", created_at)
            except Exception:
                pass
                
        now = datetime.now().isoformat()
        
        preset_data = {
            "version": "1.0",
            "name": display_name,
            "created_at": created_at,
            "updated_at": now,
            "students": payload.get("students", []),
            "schools": payload.get("schools", []),
            "delete_keywords": payload.get("delete_keywords", []),
            "delete_replacement": payload.get("delete_replacement", "")
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(preset_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"프리셋 저장 완료: {display_name} ({file_path})")

    @classmethod
    def delete_preset(cls, file_id: str) -> None:
        """지정한 프리셋 파일을 물리 삭제합니다."""
        presets_dir = cls.get_presets_dir()
        file_path = os.path.join(presets_dir, f"preset_{file_id}.json")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"프리셋 파일 삭제 완료: {file_path}")
        else:
            logger.warning(f"삭제하려는 프리셋 파일이 존재하지 않습니다: {file_path}")

    @classmethod
    def save_draft(cls, payload: dict) -> None:
        """현재 입력 폼의 상태를 draft.json으로 임시 저장합니다."""
        app_data = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if not app_data:
            app_data = os.path.join(os.path.expanduser("~"), ".sg_cleaner")
            
        if "sg_cleaner" not in app_data.lower() and "sgcleaner" not in app_data.lower():
            app_data = os.path.join(app_data, "SgCleaner")
            
        os.makedirs(app_data, exist_ok=True)
        draft_path = os.path.join(app_data, "draft.json")
        
        try:
            with open(draft_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            # 디버그 수준 로그만 출력 (너무 빈번한 로깅 차단)
            logger.debug(f"임시 드래프트 자동 저장 성공: {draft_path}")
        except Exception as e:
            logger.error(f"임시 드래프트 저장 실패: {str(e)}")

    @classmethod
    def load_draft(cls) -> dict | None:
        """임시 저장된 draft.json을 읽어와 반환합니다. 없으면 None을 반환합니다."""
        app_data = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if not app_data:
            app_data = os.path.join(os.path.expanduser("~"), ".sg_cleaner")
            
        if "sg_cleaner" not in app_data.lower() and "sgcleaner" not in app_data.lower():
            app_data = os.path.join(app_data, "SgCleaner")
            
        draft_path = os.path.join(app_data, "draft.json")
        
        if os.path.exists(draft_path):
            try:
                with open(draft_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"임시 드래프트 로드 중 오류 발생: {str(e)}")
                return None
        return None
