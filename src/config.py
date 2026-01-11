# Configuración del bot

# Nombre del paquete del juego
PACKAGE_NAME = "com.ea.games.r3_row"

# Rutas de las
# Configuración ADB y Rutas
ASSETS_DIR = "assets"
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

# Zonas Horarias
# Nota: Estas son para referencia o logs, ya que el cambio se hará por UI.
TIMEZONE_KIRITIMATI = "Pacific/Kiritimati" # UTC+14
TIMEZONE_MADRID = "Europe/Madrid"     # UTC+1/UTC+2

# Horario de ejecución (Hora local del PC)
START_HOUR = 12 # 12 pm
END_HOUR = 24   # 12 am (00:00 del día siguiente)

# Umbral de confianza para la detección de imágenes (0 a 1)
MATCH_THRESHOLD = 0.8
