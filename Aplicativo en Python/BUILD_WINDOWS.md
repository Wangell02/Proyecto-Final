# Construir PEA-i.exe en Windows

1. Instala Python 3.8 o superior.
2. Abre una consola dentro de esta carpeta.
3. Ejecuta `build_windows.bat`.
4. El ejecutable se generara en `dist\\PEA-i.exe`.
5. Para integrarlo con PEA-i, crea junto al ejecutable C++ la carpeta `scraper` y coloca dentro `PEA-i.exe`.

Estructura recomendada:

PEA-i/
    PEA-i.exe
    scraper/
        PEA-i.exe

El C++ que ya tienes busca esa ubicacion y ejecuta `PEA-i.exe --api`.
