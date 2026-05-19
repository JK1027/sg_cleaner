# DEV LOG

이 문서는 생기부 개인정보 익명화 도구의 **개발 변경 이력 및 회고**를 기록하는 개발 일지입니다.

---

## [2026-05-19] 프로젝트 설계 및 기본 문서화 단계

### 1. 요구사항 및 아키텍처 수립
- **작업 내용**:
  - `prd.md` 제품 요구사항 문서 분석을 통해 Excel 탐지, 미리보기 검수 테이블 및 Safe Save 방식 정의.
  - `rules.md`를 통한 AI 협업 개발 지침 확인: 원본 보존, `UI → Controller → State → Service` 제어 흐름 준수.
  - **관심사 분리(SoC)**를 기반으로 한 레이어 설계 및 파일 책임 명세화.
  - 중앙 집중형 상태 관리를 위한 `AppState` 및 `AppController` 인터페이스 설계.
  - ExcelService, AnonymizeDetector, DetectionWorker 등의 클래스 및 비동기 스레드 연동 흐름 설계.

### 2. 프로젝트 기본 문서 생성
- `ARCHITECTURE.md`: 시스템 물리 구조, 클래스/메서드 수준 인터페이스 명세서.
- `CURRENT_STATUS.md`: 4단계 개발 로드맵 기준 상태 관리판.
- `DEV_LOG.md`: 본 개발 로그 문서.
- `BUGS.md`: 잠재 위험 및 예외 케이스 관리 대장.

### 3. 1단계: 뼈대 세우기 완료
- **작업 내용**:
  - `requirements.txt`에 필요한 패키지(`PySide6`, `openpyxl`, `pandas`, `pyinstaller`) 지정 및 생성.
  - SoC 레이아웃에 맞추어 `app/` 하위 디렉토리(`ui/widgets`, `controllers`, `models`, `services`, `utils`, `resources`) 일괄 구성.
  - `app/utils/path_helper.py` 및 `app/utils/logger.py` 핵심 유틸리티 뼈대 구현.
  - `app/models/detection_model.py` (`DetectionItem`) 및 `app/models/app_state.py` (`AppState`) 데이터 레이어 구성.
  - UI 이벤트 및 데이터 바인딩을 위한 `app/controllers/app_controller.py` 설계 완료 및 뼈대 코드 작성.
  - `app/ui/widgets/preview_table.py`에 검수 테이블 레이아웃 및 셀 이벤트 중계 로직 작성.
  - `app/ui/main_window.py`에 파일 추가/삭제, 패턴 설정, 테이블 연동 및 제어 영역 레이아웃 및 슬롯 배치 완료.
  - `app/main.py` 진입점에 앱 상태 및 메인 윈도우 인스턴스를 시작하는 실행 루프 작성.

### 4. 2단계: 내용 채우기 완료
- **작업 내용**:
  - Python 3.11 가상환경 `.venv` 생성 및 `pip install -r requirements.txt` 패키지 설치 완료.
  - `app/services/excel_service.py` 내 **Safe Save** 알고리즘 4단계 파이프라인(복제본 생성 ➡️ 스타일 유지 셀 데이터 치환 ➡️ 저장 검증 및 오픈 테스트 ➡️ 최종 파일 이동) 구현 완료. 수식 셀 치환 방지 적용.
  - `app/services/detector.py` 내 규칙 기반 탐지 구현 완료. `MergedCell` 대표 셀만 추출하는 예외 스킵 처리 및 숨김 시트 필터링 로직 구현 완료.
  - `app/services/worker.py` 내 PySide6 `QThread` 상속 백그라운드 스레드 구현 (`DetectionWorker`, `AnonymizeWorker`) 완료. 진행도 및 결과를 컨트롤러에 중계하는 시그널 바인딩 적용.
  - `app/controllers/app_controller.py`에 스레드 시작, 수명 소멸 관리(`deleteLater`), 시그널 바인딩 연동 적용.
  - 정적 문법 검증(`py_compile`) 완료 및 `tests/test_engine.py` 테스트 코드를 통해 스캔 엔진과 Safe Save 로직 무결성 검증 (2개 단위 테스트 100% 통과 확인).

### 5. 3단계: 디자인 적용 완료
- **작업 내용**:
  - `app/resources/style.qss`에 모던하고 깨끗한 화이트 테마 및 세련된 블루/틸 포인트 컬러 중심의 프리미엄 스타일시트 구축.
  - 가상 리소스 로딩에 대한 예외 처리가 가미된 QSS 파일 로드 파이프라인을 `app/main.py`에 적용.
  - `app/ui/main_window.py` 내의 각 중요 액션 버튼에 `setObjectName`을 바인딩하여 호버(hover), 선택(selected), 클릭(pressed) 상태 피드백을 가시적으로 맵핑.
  - 탐지/저장 등 비동기 스레드 작업이 진행 중일 때, 사용자의 오동작(더블 클릭이나 설정 수정 등)을 원천 방지하기 위해 폼 필드와 제어 버튼을 동적으로 Lock/Unlock 하는 입력 제어(Disable/Enable) 로직 보강.
  - 테이블 위젯의 헤더 스타일링, 교차 열 색상, 간격 및 체크박스 커스텀 렌더링 반영.

### 6. 4단계: 마무리 점검 완료
- **작업 내용**:
  - `tests/test_engine.py` 파일 내에 한글 및 특수문자가 포함된 파일 이름 처리 검증을 위한 `test_korean_path_handling`과 누락된 파일 스캔 시 예외 및 롤백 처리를 검증하는 `test_missing_file_handling` 단위 테스트 추가 및 전체 통과 검증 완료.
  - PyInstaller를 사용하여 `dist/main.exe` 단일 독립 파일 생성 완료 (콘솔 숨김 `--noconsole` 및 단일 파일 배포 `--onefile` 파라미터 적용).
  - 스타일시트(`style.qss`)를 실행 바이너리 내에 안전하게 포장하기 위해 `--add-data "app/resources/style.qss;resources"` 옵션 적용 및 `sys._MEIPASS` 경로 파싱 유효성 검증 완료.

---

## 남은 이슈 및 다음 작업 예정 (향후 유지보수)
- [ ] 실사용자 업무 환경 배포 및 피드백 대응
- [ ] PRD 외 요구사항 발생 시 v0.2.0 마일스톤 업데이트 계획 수립




