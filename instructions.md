# RR3 Bot Lite

Automation bot for Real Racing 3.

## Structure

```
RR3-lite/
├── requirements.txt   # Project dependencies
├── build.bat          # Build for Windows
├── run.sh             # Run on Linux
├── venv/              # Virtual environment (auto-created)
├── README.md
└── src/
    ├── gui.py         # Graphical interface
    ├── main.py        # Bot logic
    ├── config.py      # Configuration
    ├── adb_wrapper.py # ADB Wrapper
    ├── vision.py      # Visual detection
    ├── ocr.py         # Text recognition
    ├── logger.py      # Data logging
    ├── i18n.py        # Internationalization
    ├── assets/        # Visual templates
    └── lang/          # Language files
```

## System Requirements

- Python 3.10+
- ADB (Android Debug Bridge)
- Tesseract OCR
- Connected Android device

## Installation

### Linux (Option 1: Automatic)

Simply run the script and the virtual environment will be created automatically:

```bash
chmod +x run.sh
./run.sh
```

### Linux (Option 2: Manual)

```bash
# Create virtual environment in project root
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
cd src
python gui.py
```

### Windows (Development)

```cmd
REM Create virtual environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

REM Run
cd src
python gui.py
```

### Build EXE (Windows)

```cmd
build.bat
```

The `build.bat` script automatically creates the virtual environment if it doesn't exist.
The executable is generated in `dist\RR3BotLite\RR3BotLite.exe`

## Features

- ✅ Automatic ad monitoring
- ✅ Button and UI element detection
- ✅ Automatic timezone switching
- ✅ GUI with real-time statistics
- ✅ Historical gold earnings log
- ❌ No ML/AI (lite version)
