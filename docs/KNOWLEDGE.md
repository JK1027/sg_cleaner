
# KNOWLEDGE.md

## 목적

실패 사례와 해결 경험을 축적한다.
같은 실수를 두 번 하지 않는 것이 목표다.

# 기록 템플릿

제목
프로젝트
발생일
문제
증상
원인
해결
재발 방지
관련 파일

# GitHub Actions

## UnicodeEncodeError

문제
빌드 실패

원인
CP1252 환경에서 한글 출력

해결
ASCII 로그 사용

재발 방지
빌드 스크립트 영문화

---

## shell=False 실행 실패

원인
PATH 탐색 실패

해결
sys.executable 사용

# Electron

## HWP SaveAs 실패

원인
OneDrive 또는 백신 충돌

해결
0.5초 간격 재시도

재발 방지
Atomic Save + Retry

# GAS

## 동시 저장 충돌

원인
LockService 미사용

해결
ScriptLock 적용

# 누적 규칙

새로운 장애 발생 시 반드시 기록한다.
