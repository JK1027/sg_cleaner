import os
import shutil
import zipfile
import xml.etree.ElementTree as ET
from app.services.base_processor import BaseProcessor, ExtractedTextItem
from app.models.detection_model import DetectionItem
from app.utils.logger import logger

# 한글 HWPX 주요 XML 네임스페이스 접두사 강제 보존 등록
ET.register_namespace("hp", "http://www.hancom.co.kr/hwpml/2011/paragraph")
ET.register_namespace("hs", "http://www.hancom.co.kr/hwpml/2011/sentencestructure")
ET.register_namespace("hc", "http://www.hancom.co.kr/hwpml/2011/container")
ET.register_namespace("ha", "http://www.hancom.co.kr/hwpml/2011/app")

class HwpxProcessor(BaseProcessor):
    """
    HWPX (한글 XML 기반 오픈 규격) 문서의 데이터 추출 및 안전 치환을 처리하는 구체 프로세서 클래스.
    무거운 COM 호출 없이 고속 ZIP/XML 조작 방식으로 안전하게 구동됩니다.
    """

    def extract_texts(self, file_path: str) -> list[ExtractedTextItem]:
        """
        HWPX ZIP 아카이브를 열어 Contents/section*.xml 본문 내부의 텍스트 항목을 구조적으로 추출합니다.
        """
        extracted_items = []
        try:
            if not zipfile.is_zipfile(file_path):
                raise ValueError("올바른 ZIP(HWPX) 아카이브 형식이 아닙니다.")
                
            with zipfile.ZipFile(file_path, "r") as z:
                # Contents/section*.xml 파일 목록 수집
                section_files = [
                    name for name in z.namelist() 
                    if name.startswith("Contents/section") and name.endswith(".xml")
                ]
                
                for section_file in section_files:
                    xml_data = z.read(section_file)
                    # XML 파싱
                    root = ET.fromstring(xml_data)
                    
                    # hp:p(문단) 노드 순회하여 위치 맥락 가독성 확보
                    p_elements = [el for el in root.iter() if el.tag.endswith("}p")]
                    for p_idx, p in enumerate(p_elements):
                        t_elements = [el for el in p.iter() if el.tag.endswith("}t")]
                        for t_idx, t in enumerate(t_elements):
                            if t.text:
                                text_val = t.text.strip()
                                if not text_val:
                                    continue
                                extracted_items.append(ExtractedTextItem(
                                    text=t.text,
                                    location_context=section_file, # Contents/section0.xml 명칭 노출
                                    location_detail=f"문단 {p_idx+1}, 텍스트 {t_idx+1}"
                                ))
        except Exception as e:
            logger.error(f"HWPX 텍스트 추출 중 오류 발생 ({file_path}): {str(e)}")
            raise e

        return extracted_items

    def apply_replacements(self, file_path: str, replacements: list[DetectionItem], temp_path: str) -> None:
        """
        임시 복제된 HWPX zip을 파싱하여 텍스트 노드 변경값을 반영하고 덮어씁니다.
        """
        temp_write_path = temp_path + ".new"
        
        try:
            with zipfile.ZipFile(temp_path, "r") as z_in:
                with zipfile.ZipFile(temp_write_path, "w", zipfile.ZIP_DEFLATED) as z_out:
                    
                    # 1. 해당 파일에 적용할 변경 항목들
                    file_replacements = [r for r in replacements if r.file_path == file_path and r.approved]
                    
                    for name in z_in.namelist():
                        # 본문 XML 파일에 대해서만 파싱 및 치환 수정 처리
                        if name.startswith("Contents/section") and name.endswith(".xml"):
                            xml_data = z_in.read(name)
                            root = ET.fromstring(xml_data)
                            
                            section_replacements = [r for r in file_replacements if r.location_context == name]
                            
                            # 문단과 t 노드를 탐색하며 매치 항목 치환
                            p_elements = [el for el in root.iter() if el.tag.endswith("}p")]
                            modified = False
                            for p_idx, p in enumerate(p_elements):
                                t_elements = [el for el in p.iter() if el.tag.endswith("}t")]
                                for t_idx, t in enumerate(t_elements):
                                    if not t.text:
                                        continue
                                    
                                    detail_str = f"문단 {p_idx+1}, 텍스트 {t_idx+1}"
                                    items_to_apply = [r for r in section_replacements if r.location_detail == detail_str]
                                    
                                    if items_to_apply:
                                        current_val = t.text
                                        new_val = current_val
                                        for item in items_to_apply:
                                            new_val = new_val.replace(item.match_value, item.replacement)
                                        t.text = new_val
                                        modified = True
                                        logger.debug(f"HWPX 치환 적용 - {name} ({detail_str}): {current_val} -> {new_val}")
                            
                            # 수정된 XML 저장
                            if modified:
                                new_xml_data = b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="utf-8")
                                z_out.writestr(name, new_xml_data)
                            else:
                                z_out.writestr(name, xml_data)
                        else:
                            # 그 외 메타데이터 및 이미지 파일은 바이너리 그대로 복제 복사
                            z_out.writestr(name, z_in.read(name))
            
            # 원본 임시본 덮어쓰기 완료
            shutil.move(temp_write_path, temp_path)
            logger.info(f"HwpxProcessor: HWPX 치환 저장 성공 ({temp_path})")
            
        except Exception as e:
            logger.error(f"HWPX 치환 수정 파일 생성 실패: {str(e)}")
            if os.path.exists(temp_write_path):
                os.remove(temp_write_path)
            raise e
