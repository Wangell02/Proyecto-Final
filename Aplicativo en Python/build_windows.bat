@echo off
setlocal
cd /d %~dp0

echo ================================================
echo PEA-Scraper - Construccion para Windows
echo ================================================

echo.
echo [1/4] Comprobando Python...
python --version
if errorlevel 1 (
    echo ERROR: Python no esta disponible en PATH.
    echo Instala Python 3.8 o superior para construir el ejecutable.
    exit /b 1
)

echo.
echo [2/4] Instalando/actualizando PyInstaller...
python -m pip install -U pyinstaller
if errorlevel 1 (
    echo ERROR: No se pudo instalar PyInstaller.
    exit /b 1
)

echo.
echo [3/4] Construyendo PEA-i.exe...
python -m PyInstaller --clean --noconfirm PEA-Scraper.spec
if errorlevel 1 (
    echo ERROR: PyInstaller no pudo construir el ejecutable.
    exit /b 1
)

echo.
echo [4/4] Resultado:
echo %~dp0dist\PEA-i.exe
if not exist "%~dp0dist\PEA-i.exe" (
    echo ERROR: No se encontro el ejecutable esperado.
    exit /b 1
)

echo.
echo Construccion completada correctamente.
echo Para C++ coloca el ejecutable como:
echo   PEA-i\scraper\PEA-i.exe

echo El C++ actual ya contempla esa ruta.
endlocal
