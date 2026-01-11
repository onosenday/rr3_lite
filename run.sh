#!/bin/bash
# ============================================
#  RR3 Bot Lite - Linux Run Script
# ============================================

cd "$(dirname "$0")/src"

# Activar venv si existe
if [ -d "../venv" ]; then
    source ../venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Ejecutar GUI
python gui.py "$@"
