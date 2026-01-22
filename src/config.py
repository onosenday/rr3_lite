# Configuración del bot

# Nombre del paquete del juego
PACKAGE_NAME = "com.ea.games.r3_row"

# Rutas de las
# Configuración ADB y Rutas
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
COIN_ICON_TEMPLATE = "coin_icon.png"
AD_CONFIRM_TEMPLATE = "ad_confirm_button.png"
AD_CLOSE_TEMPLATE = "ad_close_button.png"
AD_RESUME_TEMPLATE = "seguir_viendo.png"
AD_FAST_FORWARD_TEMPLATE = "ad_fast_forward.png"
NO_MORE_GOLD_TEMPLATE = "no_more_gold_icon.png"
INTERMEDIATE_TEMPLATE = "intermediate_screen.png"
SEARCH_ICON_TEMPLATE = "search_icon.png"
SEARCH_ICON_TEMPLATE = "search_icon.png"
WEB_BAR_CLOSE_TEMPLATE = "web_bar_close_v2.png"
# Lista de botones de cierre de recompensa (para manejar variantes con cursor, etc.)
# Lista de botones de cierre de recompensa (para manejar variantes con cursor, etc.)
REWARD_CLOSE_TEMPLATES = ["reward_close.png", "reward_close_cursor.png"]

# Nuevos Assets para identificar Lobby (Robustez)
LOBBY_TEMPLATE_1 = "lobby_asset_1.png"
LOBBY_TEMPLATE_2 = "lobby_asset_2.png"

# Calibración de Pantalla (Desktop Mapping)
# REMOVED: Ya no usamos desktop_tap, usamos ADB directo.
# DESKTOP_CALIBRATION = {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "enabled": False}

# Zonas Horarias - Configuración completa para Day/Night
ZONE_NIUE = {
    "name": "NIUE",
    "tz_id": "Pacific/Niue",
    "search_input": "Niue",
    "ocr_match": "Niue",
    "needs_city": False,
}

ZONE_MADRID = {
    "name": "MADRID",
    "tz_id": "Europe/Madrid",
    "search_input": "Espa",
    "ocr_match": "España",
    "needs_city": True,
    "city_search": "Madrid",
    "city_match": "Madrid",
}

ZONE_KIRITIMATI = {
    "name": "KIRITIMATI",
    "tz_id": "Pacific/Kiritimati",
    "search_input": "Kiribati",
    "ocr_match": "Kiribati",
    "needs_city": True,
    "city_search": "Kiritimati",
    "city_match": "Kiritimati",
}

ALL_ZONES = [ZONE_NIUE, ZONE_MADRID, ZONE_KIRITIMATI]

# Turnos - Day/Night
SHIFT_NIGHT = {"name": "NIGHT", "start": 0, "end": 12, "home": ZONE_NIUE, "recharge": ZONE_MADRID}
SHIFT_DAY = {"name": "DAY", "start": 12, "end": 0, "home": ZONE_MADRID, "recharge": ZONE_KIRITIMATI}

SHIFTS = [SHIFT_NIGHT, SHIFT_DAY]

# Umbral de confianza para la detección de imágenes (0 a 1)
MATCH_THRESHOLD = 0.8


# Versión y Actualizaciones
BOT_VERSION = "1.3.1"
VERSION_CHECK_URL = "https://raw.githubusercontent.com/onosenday/rr3_lite/main/CHANGELOG.md"
