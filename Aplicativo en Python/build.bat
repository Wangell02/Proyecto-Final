@echo off
setlocal
cd /d %~dp0
python -m PyInstaller --clean --noconfirm PEA-Scraper.spec
if errorlevel 1 (
    echo Error al construir PEA-i.exe
    exit /b 1
)
echo Ejecutable generado en dist\PEA-i.exe
endlocal
