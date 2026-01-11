# RR3 Bot Lite

Bot de automatización para Real Racing 3 **sin componentes de Machine Learning**.

## Estructura

```
RR3-lite/
├── build.bat          # Compilar para Windows
├── run.sh             # Ejecutar en Linux
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
    ├── requirements.txt
    ├── assets/        # Templates visuales
    └── lang/          # Archivos de idioma
```

## Requisitos

- Python 3.10+
- ADB (Android Debug Bridge)
- Tesseract OCR
- Dispositivo Android conectado

## Instalación (Linux)

```bash
cd src
python -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
```

## Uso

### Linux
```bash
./run.sh
```

### Windows (desarrollo)
```cmd
cd src
python gui.py
```

### Compilar EXE (Windows)
```cmd
build.bat
```

El ejecutable se genera en `dist/RR3BotLite/RR3BotLite.exe`

## Características

- ✅ Monitorización automática de anuncios
- ✅ Detección de botones y elementos de interfaz
- ✅ Cambio automático de zona horaria
- ✅ GUI con estadísticas en tiempo real
- ✅ Registro histórico de oro obtenido
- ❌ Sin ML/AI (versión lite)
