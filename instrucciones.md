# RR3 Bot Lite

Bot de automatización para Real Racing 3

## Estructura

```
RR3-lite/
├── requirements.txt   # Dependencias del proyecto
├── build.bat          # Compilar para Windows
├── run.sh             # Ejecutar en Linux
├── venv/              # Entorno virtual (se crea automáticamente)
├── README.md
└── src/
    ├── gui.py         # Interfaz gráfica
    ├── main.py        # Lógica del bot
    ├── config.py      # Configuración
    ├── adb_wrapper.py # Wrapper ADB
    ├── vision.py      # Detección visual
    ├── ocr.py         # Reconocimiento de texto
    ├── logger.py      # Registro de datos
    ├── i18n.py        # Internacionalización
    ├── assets/        # Templates visuales
    └── lang/          # Archivos de idioma
```

## Requisitos del Sistema

- Python 3.10+
- ADB (Android Debug Bridge)
- Tesseract OCR
- Dispositivo Android conectado

## Instalación

### Linux (Opción 1: Automática)

Simplemente ejecuta el script y se creará el entorno virtual automáticamente:

```bash
chmod +x run.sh
./run.sh
```

### Linux (Opción 2: Manual)

```bash
# Crear entorno virtual en la raíz del proyecto
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ejecutar
cd src
python gui.py
```

### Windows (Desarrollo)

```cmd
REM Crear entorno virtual
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

REM Ejecutar
cd src
python gui.py
```

### Compilar EXE (Windows)

```cmd
build.bat
```

El script `build.bat` crea automáticamente el entorno virtual si no existe.
El ejecutable se genera en `dist\RR3BotLite\RR3BotLite.exe`

## Características

- ✅ Monitorización automática de anuncios
- ✅ Detección de botones y elementos de interfaz
- ✅ Cambio automático de zona horaria
- ✅ GUI con estadísticas en tiempo real
- ✅ Registro histórico de oro obtenido
- ❌ Sin ML/AI (versión lite)

