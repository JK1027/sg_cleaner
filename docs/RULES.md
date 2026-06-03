
# RULES.md
# AI 바이브 코딩 운영 매뉴얼 v2.0

## 목적
이 문서는 AI 코딩 에이전트와 협업할 때 일관된 품질, 안정성, 유지보수성을 확보하기 위한 단일 기준 문서이다.

# 1. 의사결정 우선순위

1. 데이터 무결성
2. 기존 기능 보존
3. 안정성
4. 보안
5. 유지보수성
6. 성능
7. 생산성
8. UI 개선

상위 원칙과 충돌하면 하위 원칙을 포기한다.

# 2. AI 작업 절차

## 일반 작업

1. 요구사항 이해
2. 영향 범위 분석
3. 구현
4. 검증
5. 결과 보고

## 구조 변경

1. 현재 구조 분석
2. 문제 정의
3. 개선안 작성
4. 승인
5. 단계별 적용
6. 검증
7. 결과 보고

# 3. 최소 수정 원칙

허용
- 버그 수정
- 기능 구현
- 테스트 보완

금지
- 무관한 리팩토링
- 함수명 대량 변경
- 파일 구조 재편
- 주석 삭제

# 4. 아키텍처 원칙

## SoC

UI → Service → Repository

## 단일 책임

하나의 함수는 하나의 역할만 담당한다.

## 상태 관리

상태 변경은 중앙 관리 구조를 통해 수행한다.

# 5. 프로젝트 시작 체크리스트

□ 저장 구조 확인
□ 외부 API 확인
□ 환경 변수 확인
□ 데이터 흐름 확인
□ 배포 방식 확인

# 6. 위험도 기반 검증

Level 1
- 문구
- 스타일

Level 2
- CRUD
- 상태 관리

Level 3
- 인증
- 저장
- 데이터 구조
- 대규모 리팩토링

Level 3는 롤백 계획 필수.

# 7. Recovery 표준

필수
- Backup
- Safe Save
- Logging
- Fallback

절차
감지 → 백업 → 복구 → 대체 동작 → 사용자 안내

# 8. Git 운영

커밋 유형

feat:
fix:
refactor:
docs:
chore:

원칙
- 기능 단위 커밋
- 한글 설명 권장
- Release는 요청 시에만

# 9. Python 표준

- 타입 힌트 사용
- dataclass 권장
- Pydantic 권장
- with 문 사용
- app.log 유지
- 가상환경 사용

배포
- sys._MEIPASS 활용

# 10. Electron 표준

- Main / Renderer 분리
- IPC 최소화
- userData 사용
- Atomic Save 적용

HWP 자동화
- 단일 작업 큐
- COM 정리
- Timeout 적용

# 11. GAS 표준

운영 순서

git commit
→ git push
→ clasp push

원칙
- LockService 사용
- Batch 처리
- schema_version 유지
- app_state 사용

# 12. 보안

금지
- API Key 하드코딩
- 비밀번호 하드코딩
- 민감정보 저장

권장
- .env
- config.json

# 13. 완료 보고 형식

수정 파일
변경 내용
영향 범위
검증 결과
남은 위험 요소

# 14. 작업 완료 알림

30초 이상 작업

필수
- 완료 알림
- 오류 알림

Windows
- PowerShell Toast 우선
- MessageBox 대체

# 15. 하지 말아야 할 것

- 추측으로 수정
- 원인 확인 없이 리팩토링
- 테스트 없이 완료 선언
- 사용자 승인 없는 구조 변경

# 16. 최종 원칙

빠른 개발보다 오래 유지되는 개발을 선택한다.
