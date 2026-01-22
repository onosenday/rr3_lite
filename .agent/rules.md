---
description: Rules for the RR3 Bot Lite project
---

# RR3 Bot Lite - AGENTS & RULES

## 🤖 Contexto del Proyecto
Bot de automatización para **Real Racing 3** en Android para **farmear oro** viendo anuncios.
Esta es la versión **Lite**, que prescinde de módulos de Machine Learning pesados, enfocándose en eficiencia y portabilidad.

### 🚧 Desafío Crítico (Xiaomi/Android 11+)
**Solución**: Pure ADB con 'Robust Taps' (`input swipe x y x y 100`).

---

## 📂 Arquitectura del Código (Lite)

Los archivos fuente se encuentran en el directorio `src/`.

| Archivo | Función |
|:--------|:--------|
| `gui.py` | Control, Live View, Métricas, Gráfico 7 días |
| `main.py` | Máquina de Estados Reactiva |
| `vision.py` | Template Matching con `find_template_adaptive` |
| `ocr.py` | Tesseract con `find_text_adaptive` |
| `logger.py` | SQLite: oro + memoria OCR/Template |

---

## 🎮 Máquina de Estados Principal

| Estado | Descripción | Transiciones |
|:-------|:------------|:-------------|
| `UNKNOWN` | Inicial/Recuperación | → `GAME_LOBBY` |
| `GAME_LOBBY` | Busca moneda/intermedia/no más oro | → `AD_INTERMEDIATE`, `REWARD_SCREEN`, `TZ_INIT` |
| `AD_INTERMEDIATE` | Confirmación de anuncio | → `AD_WATCHING` |
| `AD_WATCHING` | Monitoreo (150s timeout, X, FF, Web, Encuesta) | → `REWARD_SCREEN`, `GAME_LOBBY`, `STUCK_AD` |
| `STUCK_AD` | Atrapado en anuncio, intentando escapar (HOME + juego) | → `GAME_LOBBY` |
| `REWARD_SCREEN` | OCR oro, cierra ventana | → `GAME_LOBBY` |
| `TZ_*` | Sub-máquina Timezone | → `GAME_LOBBY` |

---

## 🌍 Sub-Máquina: Timezone Switch

| Estado | Acción | Memoria Guardada |
|:-------|:-------|:-----------------|
| `TZ_OPEN_SETTINGS` | `am start DATE_SETTINGS` | - |
| `TZ_SEARCH_REGION` | OCR "Region"/"Seleccionar" | `ocr_tz_region`, `ocr_tz_seleccionar` |
| `TZ_INPUT_SEARCH` | Lupa + escribir término | `tmpl_search_icon` |
| `TZ_SELECT_COUNTRY` | OCR país + click | `ocr_tz_pais_kiribati`, `ocr_tz_pais_espa` |
| `TZ_SELECT_CITY` | OCR ciudad (sin fallback) | `tz_city_kiritimati`, `tz_city_madrid` |
| `TZ_RETURN_GAME` | `am start` juego | - |

---

## 🧠 Sistema de Memoria Adaptativa

Guarda última posición exitosa para acelerar futuras búsquedas.

### Elementos con Memoria:

| # | Tipo | Elemento | Memory Key |
|:--|:-----|:---------|:-----------|
| 1 | Template | Moneda de Oro | `tmpl_coin_icon` |
| 2 | Template | Pantalla Intermedia | `tmpl_intermediate` |
| 3 | Template | Botón Confirmar | `tmpl_ad_confirm` |
| 4 | Template | No Más Oro | `tmpl_no_more_gold` |
| 5 | Template | Cerrar Recompensa | `tmpl_reward_close_*` |
| 6 | Template | Lupa Búsqueda | `tmpl_search_icon` |
| 7 | OCR | Region | `ocr_tz_region` |
| 8 | OCR | Seleccionar | `ocr_tz_seleccionar` |
| 9 | OCR | País Kiribati | `ocr_tz_pais_kiribati` |
| 10 | OCR | País España | `ocr_tz_pais_espa` |
| 11 | OCR | Ciudad Madrid | `tz_city_madrid` |
| 12 | OCR | Ciudad Kiritimati | `tz_city_kiritimati` |

---

## ⚠️ INFORMACIÓN CRÍTICA: Ubicación de Botones en Anuncios

**REGLA FUNDAMENTAL** que NUNCA debe olvidarse:

| Botón | Ubicaciones Típicas | Ubicaciones MENOS FRECUENTES |
|:------|:--------------------|:------------------------|
| **Cerrar (X)** | Esquina SUPERIOR IZQUIERDA o SUPERIOR DERECHA | Esquinas inferiores |
| **Fast Forward (>>)** | Esquina SUPERIOR IZQUIERDA o SUPERIOR DERECHA | Esquinas inferiores |

**Notas:**
- Ambos botones aparecen en las **esquinas SUPERIORES** de la pantalla
- Las esquinas inferiores **NUNCA** contienen estos botones en anuncios normales
- Al buscar estos elementos, restringir ROI a las dos esquinas superiores únicamente
- Esta información es específica de los anuncios mostrados en Real Racing 3

---

## 🚨 Reglas para Agentes AI

### ANTES de hacer commit
1. Actualizar README.md, CHANGELOG.md
2. **IMPORTANTE**: Verificar que `BOT_VERSION` en `src/config.py` coincida con la última versión de `CHANGELOG.md`.

### Ficheros Protegidos por `.gitignore`
1.  Eliminar temporalmente la línea en `.gitignore`
2.  Editar el fichero
3.  Restaurar `.gitignore` inmediatamente

### Pruebas y Debugging
*   Usar carpeta separada: `_debug_tmp/`
*   Borrar al finalizar
*   **Prohibido** mezclar basura con código fuente

NUNCA subas el directorio .agent/ ni el archivo .agent/rules.md a GitHub
---
**Ejecución:** `./run.sh`
