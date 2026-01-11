@echo off
REM ============================================
REM  RR3 Bot Lite - Windows Build Script
REM ============================================
REM  Requiere: Python 3.10+, PyInstaller
REM ============================================

echo.
echo ========================================
echo   RR3 Bot Lite - Compilador Windows
echo ========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.10+
    pause
    exit /b 1
)

REM Verificar PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando PyInstaller...
    pip install pyinstaller
)

REM Instalar dependencias
echo [INFO] Instalando dependencias...
pip install -r src\requirements.txt

REM Crear directorio de salida
if not exist "dist" mkdir dist

REM Compilar
echo.
echo [INFO] Compilando aplicacion...
echo.

pyinstaller --noconfirm --onedir --windowed ^
    --name "RR3BotLite" ^
    --icon "src\assets\app_logo.png" ^
    --add-data "src\assets;assets" ^
    --add-data "src\lang;lang" ^
    --hidden-import "PIL._tkinter_finder" ^
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
