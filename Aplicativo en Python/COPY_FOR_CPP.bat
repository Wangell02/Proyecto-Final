@echo off
setlocal
cd /d %~dp0
if not exist "dist\PEA-i.exe" (
    echo ERROR: Primero ejecuta build_windows.bat
    exit /b 1
)
if not exist "..\PEA-i" (
    echo No se encontro una carpeta ..\PEA-i.
    echo Copia manualmente dist\PEA-i.exe a la carpeta scraper del programa C++.
    exit /b 0
)
if not exist "..\PEA-i\scraper" mkdir "..\PEA-i\scraper"
copy /Y "dist\PEA-i.exe" "..\PEA-i\scraper\PEA-i.exe"
if errorlevel 1 (
    echo ERROR: No se pudo copiar el ejecutable.
    exit /b 1
)
echo Copiado a ..\PEA-i\scraper\PEA-i.exe
endlocal
