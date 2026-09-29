@echo off
setlocal
cd /d "%~dp0"

python -c "import PyInstaller, torch, ultralytics, cv2, numpy"
if errorlevel 1 (
    echo No se encontraron las dependencias de compilacion en el Python activo.
    echo Activa el entorno y sigue README.md para preparar el entorno de compilacion.
    pause
    exit /b 1
)

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC for %%C in (ISCC.exe) do set "ISCC=%%~$PATH:C"
if not defined ISCC (
    echo No se encontro Inno Setup 6. Instala Inno Setup 6 en la computadora de compilacion y vuelve a ejecutar este archivo.
    pause
    exit /b 1
)

python -m PyInstaller --clean --noconfirm "ViabilidadEspermatica.spec"
if errorlevel 1 (
    echo PyInstaller no pudo generar los archivos de la aplicacion.
    pause
    exit /b 1
)

if not exist "dist\ViabilidadEspermatica\ViabilidadEspermatica.exe" (
    echo No se encontro el ejecutable de la aplicacion despues de compilar.
    pause
    exit /b 1
)

copy /y "detect_290926.pt" "dist\ViabilidadEspermatica\detect_290926.pt" >nul
if errorlevel 1 (
    echo No se pudo copiar el modelo al paquete.
    pause
    exit /b 1
)

"%ISCC%" "Instalador_ViabilidadEspermatica.iss"
if errorlevel 1 (
    echo Inno Setup no pudo compilar el instalador.
    pause
    exit /b 1
)

echo.
echo Instalador generado en: %CD%\Output\Instalador_ViabilidadEspermatica.exe
pause
