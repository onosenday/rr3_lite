@echo off
REM ============================================
REM  RR3 Bot Lite - Windows Build Script
REM ============================================
REM  Version independiente y autocontenida
REM  Requiere: Python 3.10+, PyInstaller
REM ============================================

echo.
echo ========================================
echo   RR3 Bot Lite - Compilador Windows
echo ========================================
echo.

REM Obtener directorio del script
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.10+
    pause
    exit /b 1
)

REM Crear venv si no existe
if not exist "venv" (
    echo [INFO] Creando entorno virtual...
    python -m venv venv
)

REM Activar venv
call venv\Scripts\activate.bat

REM Verificar PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando PyInstaller...
    pip install pyinstaller
)

REM Instalar dependencias
echo [INFO] Instalando dependencias...
pip install -r requirements.txt

REM Crear directorio de salida
if not exist "dist" mkdir dist

REM Compilar
echo.
echo [INFO] Compilando aplicacion...
echo.

REM NOTA: Para usar icono, convertir app_logo.png a app_logo.ico
REM       PyInstaller en Windows requiere formato .ico
REM       Herramienta online: https://convertio.co/png-ico/

pyinstaller --noconfirm --onedir --windowed ^
    --name "RR3BotLite" ^
    --add-data "src\assets;assets" ^
    --add-data "src\lang;lang" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "i18n" ^
    --collect-all "adbutils" ^
    src\gui.py

if errorlevel 1 (
    echo.
    echo [ERROR] La compilacion fallo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Compilacion completada!
echo ========================================
echo.
echo   Ejecutable en: dist\RR3BotLite\RR3BotLite.exe
echo.
pause
