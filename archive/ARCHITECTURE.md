# ARCHITECTURE

이 문서는 **생기부 개인정보 익명화 도구**의 시스템 구조 및 아키텍처 설계를 기술합니다. 관심사 분리(SoC) 원칙과 안전한 Excel 처리를 위한 계층 구조를 정의합니다.

---

## 1. 디렉토리 구조 설계

`rules.md`에 정의된 권장 폴더 구조에 따라 다음과 같이 구성합니다.

```text
sg_cleaner/
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # 애플리케이션 진입점
│   │
│   ├── ui/                     # UI 레이어 (PySide6)
│   │   ├── __init__.py
│   │   ├── main_window.py      # 메인 윈도우
│   │   └── widgets/            # 공통/커스텀 위젯 (테이블 등)
│   │       ├── __init__.py
│   │       └── preview_table.py # 검수 테이블
│   │
│   ├── controllers/            # 제어 레이어 (UI-비즈니스 로직 중재)
│   │   ├── __init__.py
│   │   └── app_controller.py   # 중앙 앱 컨트롤러
│   │
│   ├── models/                 # 데이터 및 상태 모델 레이어
│   │   ├── __init__.py
│   │   ├── app_state.py        # 중앙 애플리케이션 상태 (dataclass)
│   │   └── detection_model.py  # 탐지 결과 데이터 모델
│   │
│   ├── services/               # 비즈니스 서비스 레이어
│   │   ├── __init__.py
│   │   ├── excel_service.py    # Excel 읽기/쓰기 및 Safe Save
│   │   ├── detector.py         # 학생 이름/학교명 탐지 엔진
│   │   └── worker.py           # 비동기 처리를 위한 QThread/QRunnable
│   │
│   ├── utils/                  # 유틸리티 레이어
│   │   ├── __init__.py
│   │   ├── path_helper.py      # 리소스/경로 래퍼 (sys._MEIPASS 대응)
│   │   └── logger.py           # 로그 시스템 구축 (logs/app.log)
│   └── resources/              # 리소스 파일 (아이콘 등)
│
├── logs/                       # 로그 파일 저장소
├── temp/                       # Safe Save용 임시 폴더
├── output/                     # 기본 결과 저장 폴더
├── tests/                      # 테스트 코드 폴더
│
├── prd.md                      # 제품 요구사항 문서
├── rules.md                    # AI 협업 지침
├── ARCHITECTURE.md             # 본 문서 (아키텍처 설계)
├── CURRENT_STATUS.md           # 현재 프로젝트 상태
├── DEV_LOG.md                  # 개발 로그
├── BUGS.md                     # 버그 및 위험 관리 대장
└── requirements.txt            # 의존성 패키지 목록
```

---

## 2. 관심사 분리 (SoC) 및 파일 역할 정의

| 계층 | 주요 역할 | 제한 사항 |
| :--- | :--- | :--- |
| **UI Layer** (`app/ui/`) | - 화면 표시 및 PySide6 위젯 레이아웃 구성<br>- 사용자 입력(텍스트, 파일 선택 등) 접수 및 전달<br>- 비동기 시그널에 따른 UI 변경 렌더링 | - Excel 직접 수정 금지<br>- 파일 저장 로직 포함 금지<br>- 탐지/치환 알고리즘 내장 금지 |
| **Controller Layer** (`app/controllers/`) | - UI의 이벤트를 받아 Service 호출을 제어<br>- 비즈니스 로직 처리 전후로 `AppState`를 안전하게 갱신 | - UI 위젯 객체 직접 참조 및 제어 금지 |
| **Model Layer** (`app/models/`) | - 중앙 상태 객체(`AppState`) 정의<br>- 탐지 결과, 매핑 데이터의 정형적 구조(`DetectionItem` 등) 정의 | - 비즈니스 로직 및 파일 I/O 작업 포함 금지 |
| **Service Layer** (`app/services/`) | - Excel 파일 파싱, 탐지 실행, 익명화 수행 및 안전한 파일 저장<br>- 대용량 비동기 연산을 위한 백그라운드 Worker 구현 | - UI 접근 및 위젯 직접 조작 절대 금지 |
| **Utils Layer** (`app/utils/`) | - 로깅 시스템 초기화 및 파일 기록<br>- PyInstaller 빌드 환경에 따른 경로 매핑 래퍼 제공 | - 비즈니스 상태 관리 및 UI 요소 조작 금지 |

---

## 3. 상태 관리 및 제어 흐름 설계

중앙 집중식 상태 관리를 위해 다음과 같은 흐름을 따릅니다.
```text
[UI View] ──(이벤트/입력)──> [AppController] ──(비즈니스 실행)──> [Services]
   ▲                              │                                 │
   │                        (State 변경)                            │
   │                              ▼                                 │
   └────────(이벤트/시그널)─── [AppState] <────────(결과 피드백)──────┘
```

### `AppState` 및 `AppController` 인터페이스 설계

```python
# app/models/app_state.py
from dataclasses import dataclass, field
from typing import List, Dict
from app.models.detection_model import DetectionItem

@dataclass
class AppState:
    """애플리케이션의 전역 상태 관리"""
    selected_files: List[str] = field(default_factory=list)      # 선택된 대상 파일 목록
    student_names: List[str] = field(default_factory=list)       # 사용자가 입력한 학생 이름 목록
    school_names: List[str] = field(default_factory=list)        # 사용자가 입력한 학교명 목록
    
    # 탐지 결과 목록
    detection_results: List[DetectionItem] = field(default_factory=list)
    
    # 설정 옵션
    save_mapping: bool = False                                   # 매핑 파일 저장 여부
    mapping_format: str = "csv"                                  # csv 또는 excel
    
    # 진행 상태
    is_processing: bool = False
    progress_percentage: int = 0
    status_message: str = "대기 중"
```

```python
# app/controllers/app_controller.py
from app.models.app_state import AppState

class AppController:
    """UI의 요청을 수용하고 상태를 관리하는 컨트롤러"""
    def __init__(self, state: AppState):
        self.state = state

    def set_selected_files(self, file_paths: list[str]) -> None:
        """대상 파일 목록 설정 및 상태 갱신"""
        pass

    def update_input_patterns(self, students: list[str], schools: list[str]) -> None:
        """탐지할 학생명 및 학교명 목록 업데이트"""
        pass

    def run_detection(self) -> None:
        """비동기 방식으로 탐지 엔진을 호출하여 State의 detection_results 갱신"""
        pass

    def update_detection_approval(self, index: int, approved: bool) -> None:
        """특정 탐지 결과의 적용 여부를 토글"""
        pass

    def update_replacement_text(self, index: int, new_text: str) -> None:
        """사용자가 검수 중 변경안을 수동 수정했을 때 반영"""
        pass

    def execute_anonymization(self, output_dir: str) -> None:
        """승인된 항목에 대해 익명화 서비스를 호출하고 Safe Save 방식으로 저장 실행"""
        pass
```

---

## 4. 인터페이스 설계 (주요 클래스 및 함수)

### A. 탐지 데이터 모델

```python
# app/models/detection_model.py
from dataclasses import dataclass

@dataclass
class DetectionItem:
    """탐지된 개인정보의 개별 세부 정보"""
    file_path: str        # 파일 경로
    sheet_name: str       # 시트명
    cell_address: str     # 셀 주소 (예: 'B12')
    original_value: str   # 탐지된 원본 텍스트
    match_value: str      # 탐지 대상 단어 (예: '김민수')
    replacement: str      # 변경 예정 텍스트 (예: '학생1')
    approved: bool = True # 익명화 적용 승인 여부
```

### B. Excel 처리 및 Safe Save 서비스

```python
# app/services/excel_service.py
from app.models.detection_model import DetectionItem

class ExcelService:
    """Excel 파일 읽기, 쓰기 및 손상 방지를 위한 Safe Save 담당"""
    
    def read_cell_value(self, file_path: str, sheet_name: str, cell_address: str) -> str:
        """특정 셀의 텍스트 값을 안전하게 로드"""
        pass

    def apply_replacements_safe(self, file_path: str, replacements: list[DetectionItem], output_dir: str) -> str:
        """
        [Safe Save 4단계 구현]
        1. 대상 파일을 읽어서 temp/ 경로에 임시 저장본 생성
        2. openpyxl을 통해 서식을 유지하며 cell 단위 값 치환 적용
        3. 임시 저장본 저장 및 무결성 검증 (저장 성공 확인)
        4. 무결성 검증 통과 시 output_dir로 이동 및 최종 저장
        """
        pass

    def save_mapping_file(self, mapping_data: dict[str, str], output_path: str, format_type: str) -> None:
        """익명화 매핑 테이블을 CSV 또는 Excel로 저장"""
        pass
```

### C. 규칙 기반 탐지 엔진

```python
# app/services/detector.py
from app.models.detection_model import DetectionItem

class AnonymizeDetector:
    """사용자가 입력한 패턴을 기반으로 Excel 내 텍스트를 고속으로 검색 및 탐지"""
    
    def __init__(self, student_names: list[str], school_names: list[str]):
        self.student_names = student_names
        self.school_names = school_names

    def scan_workbook(self, file_path: str) -> list[DetectionItem]:
        """
        openpyxl을 사용하여 통합 문서의 모든 시트 및 병합 셀 여부를 확인하며 탐지 대상 스캔.
        병합 셀일 경우 대표 셀 기준으로만 매칭 결과를 생성하여 중복 치환 방지.
        """
        pass
```

---

## 5. 비동기 처리 설계 (UI Freeze 방지)

비동기 작업은 PySide6의 `QThread` 또는 `QThreadPool`을 이용한 Worker 객체로 처리합니다.

```python
# app/services/worker.py
from PySide6.QtCore import QThread, Signal

class DetectionWorker(QThread):
    """Excel 분석 및 탐지 작업을 수행하는 백그라운드 스레드"""
    progress = Signal(int)                   # 진행률 피드백
    finished = Signal(list)                  # 탐지 완료 후 결과 목록 반환
    error = Signal(str)                      # 오류 발생 시 메시지 전달

    def __init__(self, file_paths: list[str], students: list[str], schools: list[str]):
        super().__init__()
        self.file_paths = file_paths
        self.students = students
        self.schools = schools

    def run(self):
        # 스레드 루프 내에서 AnonymizeDetector를 사용해 순차 탐지 진행
        pass
```
