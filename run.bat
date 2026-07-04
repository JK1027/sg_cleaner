@echo off
chcp 65001 > nul
echo 생기부 개인정보 익명화 도구(개발 모드)를 실행하는 중...
.venv\Scripts\python -m app.main
pause
