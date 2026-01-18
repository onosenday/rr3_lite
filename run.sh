#!/bin/bash
# ============================================
#  RR3 Bot Lite - Linux Run Script
# ============================================
#  Versión independiente y autocontenida
# ============================================

# Obtener el directorio donde está este script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Verificar y activar venv local
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "[WARN] venv no encontrado. Creando entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
    echo "[INFO] Instalando dependencias..."
    pip install -r requirements.txt
fi

# Ejecutar GUI
cd src
python gui.py "$@"
