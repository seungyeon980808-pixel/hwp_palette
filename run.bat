@echo off
chcp 65001 > nul
echo 마크다운 변환기를 시작합니다...

python -c "import pyhwpx" 2>nul
if %errorlevel% neq 0 (
    echo pyhwpx 패키지를 설치합니다...
    pip install pyhwpx
)

python "%~dp0main.py"

if %errorlevel% neq 0 (
    echo.
    echo 오류가 발생했습니다.
    echo  1. Python이 설치되어 있는지 확인
    echo  2. 한글(HWP) 프로그램이 실행 중인지 확인
    echo  3. 이 파일과 main.py가 같은 폴더에 있는지 확인
)
pause
