@echo off
cd /d "%~dp0"
if exist "..\.venv\Scripts\activate.bat" (
    call "..\.venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo [!] Virtualenv tidak ditemukan. Buat dengan:  python -m venv ..\.venv  lalu  pip install -r requirements.txt
    pause & exit /b 1
)
if not exist ".env" copy ".env.example" ".env" >nul
python manage.py cek_database
if errorlevel 1 (
    echo.
    echo [!] Database belum tersambung. Perbaiki sesuai SARAN di atas, lalu jalankan file ini lagi.
    pause
    exit /b 1
)
python manage.py migrate --noinput
python manage.py clearsessions
python manage.py runserver 0.0.0.0:8000
pause
