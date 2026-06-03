# PROJECT GUIDE & ARCHITECTURE

이 문서는 **생기부 개인정보 익명화 도구**의 시스템 물리적 구조, 관심사 분리(SoC) 설계 및 각 클래스별 역할과 상세 데이터 흐름을 명세합니다. 신규 개발자나 AI가 아키텍처를 이해하는 가이드 역할을 담당합니다.

---

## 1. 디렉토리 구조 및 역할

프로젝트 폴더 구조는 아래와 같이 관심사 분리(SoC) 정책에 의거하여 설계되어 있습니다.

```text
sg_cleaner/
│
├── app/                        # 애플리케이션 핵심 로직 및 코드
│   ├── main.py                 # 진입점 (실행 루프 기동 및 QSS 스타일 적용)
│   │
│   ├── ui/                     # UI 레이어 (PySide6)
│   │   ├── main_window.py      # 메인 레이아웃 구성 및 이벤트 바인딩
│   │   └── widgets/
│   │       └── preview_table.py # 검수용 테이블 위젯
│   │
│   ├── controllers/            # 제어 레이어 (UI 이벤트 ➡️ 비즈니스 연결)
│   │   └── app_controller.py   # 중앙 상태 및 백그라운드 스레드 조율기
│   │
│   ├── models/                 # 모델 레이어 (데이터 규격 및 상태)
│   │   ├── app_state.py        # 중앙 상태 저장 모델 (dataclass)
│   │   └── detection_model.py  # 탐지된 매칭 아이템 규격 (DetectionItem)
│   │
│   ├── services/               # 비즈니스 서비스 레이어
│   │   ├── excel_service.py    # Excel 가공 및 Safe Save 엔진
│   │   ├── detector.py         # 키워드 기반 Excel 고속 탐지 스캐너
│   │   └── worker.py           # 비동기 실행 스레드 (QThread 구현체)
│   │
│   └── utils/                  # 공통 유틸리티
│       ├── path_helper.py      # 가상 리소스 매핑 래퍼 (sys._MEIPASS 대응)
│       └── logger.py           # logs/app.log 저장 기록 로거
│
├── logs/                       # 로그 파일 보관 디렉토리
├── temp/                       # Safe Save 파이프라인 임시 디렉토리
├── output/                     # 기본 결과물 저장소
├── tests/                      # unittest 기반 단위 테스트 폴더
└── requirements.txt            # 의존성 패키지 명세
```

---

## 2. 관심사 분리(SoC) 세부 책임 가이드

| 레이어 | 담당 업무 | 설계 제약 및 제한 사항 |
| :--- | :--- | :--- |
| **UI 레이어** (`app/ui/`) | 화면 구성 및 위젯 배치, 사용자 입력 접수, 비동기 시그널 렌더링. | Excel 직접 접근 금지, 탐지/매칭 로직 탑재 불가, 파일 저장 행위 금지. |
| **컨트롤러 레이어** (`app/controllers/`) | UI 신호를 가로채서 백그라운드 Worker 스레드를 구동하며 `AppState`를 업데이트함. | UI 위젯 인스턴스를 직접 가지고 조작하는 행위 금지. |
| **모델 레이어** (`app/models/`) | `AppState` 전역 상태 및 `DetectionItem` 규격 정의. | 비즈니스 로직 및 I/O 연산 배치 금지. |
| **서비스 레이어** (`app/services/`) | openpyxl을 이용한 파일 제어, 키워드 탐색, Safe Save 알고리즘 및 파일 출력. | UI에 대한 참조나 컴포넌트 호출 절대 금지. |

---

## 3. 상태 관리 및 제어 흐름 설계

중앙 집중식 상태 관리를 위해 다음과 같은 순환 데이터 흐름을 준수합니다.

```text
[UI View (main_window)] ──(사용자 입력 이벤트)──> [AppController]
        ▲                                                │
   (시그널 감지 및 리렌더)                            (Worker 구동 및 State 업데이트)
        │                                                ▼
   [AppState] <───────────────────────────────────── [AppState 갱신 및 완료 반환]
```

### 상태 데이터 규격 (`AppState`)
* `selected_files`: 스캔할 대상 파일 목록 (`List[str]`)
* `student_names`: 탐색할 학생명 목록 (`List[str]`)
* `school_names`: 탐색할 학교명 목록 (`List[str]`)
* `delete_keywords`: 탐색할 완전 삭제 단어 목록 (`List[str]`)
* `delete_replacement`: 삭제어 대체 텍스트 (`str`)
* `detection_results`: 검출되어 하단 테이블에 로드되는 항목 목록 (`List[DetectionItem]`)
* `is_processing`: 백그라운드 연산 여부 (UI 입력 필드 락 트리거)

---

## 4. 백그라운드 비동기 멀티스레드 설계

UI 프리징 현상 방지를 위해 대용량 처리는 PySide6의 `QThread`를 상속한 Worker 객체에 일임합니다.

* **`DetectionWorker`**: `AnonymizeDetector`를 기동하여 선택된 파일들을 탐색하고 진행률을 시그널(`progress_changed`)로 릴레이합니다. 완료 시 `finished` 시그널로 검출 목록을 컨트롤러로 보냅니다.
* **`AnonymizeWorker`**: `ExcelService`를 기동하여 Safe Save 알고리즘을 적용한 후 최종 파일 저장 및 매핑 대장 저장을 백그라운드에서 실행합니다.
