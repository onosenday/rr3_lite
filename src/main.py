import time
import os
import subprocess
import datetime
import random
import cv2
# pyautogui removed
from config import (PACKAGE_NAME, ASSETS_DIR, COIN_ICON_TEMPLATE, AD_CONFIRM_TEMPLATE,
                    AD_CLOSE_TEMPLATE, AD_RESUME_TEMPLATE, AD_FAST_FORWARD_TEMPLATE,
                    NO_MORE_GOLD_TEMPLATE, INTERMEDIATE_TEMPLATE, SEARCH_ICON_TEMPLATE,
                    WEB_BAR_CLOSE_TEMPLATE, REWARD_CLOSE_TEMPLATES, LOBBY_TEMPLATE_1,
                    LOBBY_TEMPLATE_2, MATCH_THRESHOLD, ALL_ZONES, SHIFTS,
                    ZONE_NIUE, ZONE_MADRID, ZONE_KIRITIMATI)
from adb_wrapper import ADBWrapper
from vision import Vision
from ocr import OCR
from logger import GoldLogger
from i18n import t
from enum import Enum, auto

class BotState(Enum):
    UNKNOWN = auto()
    GAME_LOBBY = auto()
    AD_INTERMEDIATE = auto()
    AD_WATCHING = auto()
    REWARD_SCREEN = auto()
    STUCK_AD = auto()  # Nuevo: Atrapado en anuncio, intentando escapar
    
    TZ_INIT = auto()
    TZ_OPEN_SETTINGS = auto()
    TZ_SEARCH_REGION = auto()
    TZ_INPUT_SEARCH = auto()
    TZ_SELECT_COUNTRY = auto()
    TZ_SELECT_CITY = auto()
    TZ_RETURN_GAME = auto()


class Action(Enum):
    """Acciones discretas que puede tomar el bot."""
    WAIT = 0
    CLICK_COIN = 1
    CLICK_AD_CONFIRM = 2
    CLICK_CLOSE_X = 3
    CLICK_FAST_FORWARD = 4
    CLICK_REWARD_CLOSE = 5
    PRESS_BACK = 6
    # Timezone actions
    CLICK_REGION = 10
    CLICK_SELECCIONAR = 11
    CLICK_SEARCH_FIELD = 12
    CLICK_COUNTRY = 13
    CLICK_CITY = 14
    PRESS_HOME = 15
    # Rescue actions
    CLICK_WEB_CLOSE = 20
    CLICK_SURVEY_SKIP = 21
    # No action / Unknown
    NONE = 99

class RealRacingBot:
    def __init__(self, stop_event=None, log_callback=None, image_callback=None, stats_callback=None, click_callback=None):
        self.adb = ADBWrapper()
        self.vision = Vision()
        self.ocr = OCR()
        self.logger = GoldLogger()
        self.current_timezone_state = "MADRID" 
        self.last_screen_shape = None # To store (height, width) of the last screenshot
        
        # Session Params for Stats
        self.session_start = time.time()
        self.session_ads = 0
        self.session_gold = 0
        self.last_reward_time = 0 # Debounce for rewards
        
        # State Machine
        self.state = BotState.UNKNOWN
        self.state_data = {} # To store transient state data (e.g. tz search term)
        
        self.current_action = Action.NONE
        self.last_screenshot = None
        
        # Screen Dims (Lazy load or default)
        self.screen_width = 2340 
        self.screen_height = 1080
        try:
             w, h = self.adb.get_screen_dimensions()
             self.screen_width = w
             self.screen_height = h
        except:
             pass

        # UI Callbacks
        self.stop_event = stop_event
        self.log_callback = log_callback
        self.image_callback = image_callback
        self.stats_callback = stats_callback
        self.click_callback = click_callback

        # Lobby Timeout Tracker
        self.lobby_enter_time = None

        # Cargar stats iniciales
        if self.stats_callback:
            t_gold = self.logger.get_todays_gold() or 0
            h_gold = self.logger.get_all_time_gold() or 0
            
            self.stats_callback(
                int(t_gold), 
                int(h_gold),
                0.0,
                0.0,
                self.session_gold
            )

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        print(full_msg)
        if self.log_callback:
            self.log_callback(full_msg)

    def update_live_view(self, image):
        if self.image_callback:
            self.image_callback(image)

    def is_stopped(self):
        if self.stop_event and self.stop_event.is_set():
            return True
        return False

    def is_within_time_window(self):
        now = datetime.datetime.now()
        return START_HOUR <= now.hour < END_HOUR
        
    def device_tap(self, x, y, duration=None):
        """
        Realiza un click directo en las coordenadas del dispositivo usando ADB.
        No requiere conversion ni calibracion si las coordenadas vienen de la screenshot.
        """
        self.log(t("log_adb_tap", x=int(x), y=int(y)))
        
        # Click Visualization Callback
        if self.click_callback:
            self.click_callback(x, y)
            
        if duration and duration > 0.1:
             self.adb.long_tap(x, y, int(duration * 1000))
        else:
             self.adb.tap(x, y)

    def wait_for_package(self, package_snippet, timeout=5.0):
        """
        Espera activa hasta que el paquete actual contenga package_snippet.
        Retorna True si lo encontró, False si hubo timeout.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            current = self.adb.get_current_package()
            if current and package_snippet in current:
                return True
            time.sleep(0.2) # Polling rápido
        return False

    def verify_return_to_settings(self):
        """Helper para verificar que volvimos a la pantalla anterior."""
        self.log(f"Esperando retorno a pantalla Settings...")
        # Polling rapido
        start_wait_return = time.time()
        found_return = False
        while time.time() - start_wait_return < 5.0: # 5s timeout
             scr_check = self.adb.take_screenshot()
             texts = self.ocr.get_screen_texts(scr_check)
             # IMPORTANTE: OCR devuelve palabras sueltas. No buscar frases.
             # Buscamos "Fecha" o "Seleccionar".
             found_return = any("Seleccionar" in t[0] or "Fecha" in t[0] or "Date" in t[0] for t in texts)
             
             if found_return:
                  self.log("✅ Detectada pantalla de ajustes. Cambio confirmado.")
                  return True
             time.sleep(0.3)
        return False
    
    def set_action(self, action):
        """Registra la accion actual para logging."""
        self.current_action = action


    def _find_template_with_memory(self, screenshot, template_name, memory_key):
        """
        Busca un template usando memoria adaptativa.
        Retorna (x, y, w, h) o None.
        """
        template_path = os.path.join(ASSETS_DIR, template_name)
        
        # Recuperar memoria
        memory = self.logger.get_ocr_memory(memory_key)
        hint_coords = None
        if memory:
            hint_coords = (memory["x"], memory["y"], memory["w"], memory["h"])
        
        # Busqueda adaptativa
        result = self.vision.find_template_adaptive(screenshot, template_path, hint_coords=hint_coords)
        
        if result:
            rx, ry, rw, rh = result
            # Guardar en memoria
            self.logger.save_ocr_memory(memory_key, template_name, rx - rw//2, ry - rh//2, rw, rh, 0)
            return result
        
        return None

    def _search_country(self, term):
        """Busca país usando lupa. Retorna True si éxito."""
        self.log(f"🔎 Buscando País '{term}'...")
        # 1. Buscar Lupa
        scr = self.adb.take_screenshot()
        match = self.vision.find_template(scr, os.path.join(ASSETS_DIR, SEARCH_ICON_TEMPLATE))
        
        if match:
            cx, cy, w, h = match
            click_x = cx + w + 50
            self.device_tap(click_x, cy)
            time.sleep(0.5) 
            
            self.adb._run_command(["input", "text", term])
            time.sleep(1.0) 
            
            # Buscar resultado
            scr = self.adb.take_screenshot()
            results = self.ocr.get_screen_texts(scr, min_y=250)
            
            # Exacto
            for text, x, y, w, h in results:
                if text.upper() == term.upper():
                    self.log(f"✅ País Exacto '{text}' ({x},{y}). Click.")
                    self.device_tap(x+w//2, y+h//2)
                    return True
            
            # Parcial
            for text, x, y, w, h in results:
                if term.upper() in text.upper():
                     self.log(f"✅ País Parcial '{text}' ({x},{y}). Click.")
                     self.device_tap(x+w//2, y+h//2)
                     return True
                     
            self.log(f"❌ No encontré país '{term}' en resultados.")
            return False
            
        else:
            self.log("⚠ No veo lupa. Intentando click directo...")
            return self._click_city_direct(term)

    def _click_city_direct(self, name):
        """Busca texto en pantalla (City) y pulsa."""
        self.log(f"Buscando '{name}' en pantalla...")
        scr = self.adb.take_screenshot()
        
        # Exacto (Prioridad)
        coords = self.ocr.find_text(scr, name, exact_match=True)
        if coords:
            self.log(f"✅ Click directo '{name}' {coords}")
            self.device_tap(*coords)
            return True
            
        # Parcial (Fallback, útil para Madrid que puede estar rodeado)
        coords = self.ocr.find_text(scr, name, exact_match=False)
        if coords:
            self.log(f"✅ Click directo parcial '{name}' {coords}")
            self.device_tap(*coords)
            return True
            
        self.log(f"❌ No veo '{name}' en pantalla.")
        return False



    def _wait_click_country_result(self, term):
        """Busca el resultado del pais en OCR con retries cortos."""
        memory_key = f"ocr_tz_pais_{term.lower()}"
        
        for _ in range(10):
            scr = self.adb.take_screenshot()
            results = self.ocr.get_screen_texts(scr, min_y=250)
            
            # Exacto
            for text, x, y, w, h in results:
                if text.upper() == term.upper():
                    cx, cy = x + w//2, y + h//2
                    self.log(f"Pais '{text}' encontrado en ({cx},{cy}) - Guardando en BD")
                    self.logger.save_ocr_memory(memory_key, text, x, y, w, h, 0)
                    self.device_tap(cx, cy)
                    return True
            # Parcial
            for text, x, y, w, h in results:
                if term.upper() in text.upper():
                    cx, cy = x + w//2, y + h//2
                    self.log(f"Pais '{text}' (parcial) en ({cx},{cy}) - Guardando en BD")
                    self.logger.save_ocr_memory(memory_key, text, x, y, w, h, 0)
                    self.device_tap(cx, cy)
                    return True
            time.sleep(0.3)
        return False

    def handle_web_consent(self, screenshot):
        """
        Detección de anuncios tipo Web/Consentimiento (Cookies, Preferencias, etc).
        Retorna True si realizó acción (Click Back).
        """
        # Palabras clave fuertes
        web_keywords = ["cookies", "preferencias", "aviso", "consent"]
        
        # Usar get_lines para scan rápido
        lines = self.ocr.get_lines(screenshot)
        full_text_lower = " ".join(lines).lower()
        
        # Contar palabras (aproximado)
        word_count = len(full_text_lower.split())
        
        found_keyword = next((k for k in web_keywords if k in full_text_lower), None)
        
        if found_keyword and word_count > 50:
            self.log(f"⚠ Detectado anuncio Web/Consentimiento (keyword: '{found_keyword}', words: {word_count}).")
            self.log("👉 Ejecutando acción: BOTÓN ATRÁS (Back).")
            self.adb.input_keyevent(4) # KEYCODE_BACK
            time.sleep(2.0) # Esperar a que el sistema reaccione
            return True
            
        return False

    def handle_google_survey(self, screenshot):
        """
        Maneja la encuesta de Google:
        1. Detectar contexto (Google + Encuesta/Survey/etc).
        2. Click en 'X' (Arriba izquierda).
        3. Refrescar screenshot.
        4. Click en 'Saltar' (si aparece).
        Retorna True si se ejecutó la secuencia.
        """
        # Primero leemos todo el texto para contexto
        text_lines = self.ocr.get_lines(screenshot)
        full_text = " ".join(text_lines).lower()
        
        # --- CRITERIO STRICTO (Anti Falsos Positivos) ---
        # 1. Tiene que mencionar "google" (ej: "tecnología de google", "google play" NO basta solo)
        if "google" not in full_text:
            return False
            
        # 2. Tiene que mencionar explícitamente contenido de encuesta o la footer tecnica
        # Eliminamos 'reward', 'recompensa', 'app' que son comunes en ads de juegos.
        specific_keywords = ["encuesta", "survey", "tecnologia", "technology", "opini"] # opini -> opinión
        
        if not any(k in full_text for k in specific_keywords):
            return False
            
        # Si llegamos aqui, es MUY probable que sea una encuesta de Google.
        self.log(f"Posible Encuesta Google detectada (Contexto: Google + {specific_keywords}).")

        # 1. Buscar Pantalla 1 (Buscamos la X arriba a la izquierda)
        # Intentar buscar la 'X' específicamente
        x_pos = self.ocr.find_text(screenshot, "X", exact_match=True)
        
        if x_pos and x_pos[1] < 200 and x_pos[0] < 300: # X debe estar arriba izquierda
            self.log(f"Encuesta Google: Click en 'X' encontrada por OCR en {x_pos}.")
            self.device_tap(x_pos[0], x_pos[1])
            time.sleep(1) # Esperar transición
            
            # 2. Buscar botón 'Saltar' (Paso 2) - REFRESCO INMEDIATO
            self.log("Encuesta Google: Buscando botón 'Saltar' post-X...")
            new_scr = self.adb.take_screenshot()
            saltar_pos = self.ocr.find_text(new_scr, "Saltar", case_sensitive=True)
            
            if saltar_pos:
                self.log(f"Encuesta Google: Botón 'Saltar' detectado en {saltar_pos}. Click.")
                self.device_tap(saltar_pos[0], saltar_pos[1])
                time.sleep(1)
                return True
            else:
                # Fallback: A veces dice "Skip"
                 skip_pos = self.ocr.find_text(new_scr, "Skip", case_sensitive=True)
                 if skip_pos:
                      self.log(f"Encuesta Google: Botón 'Skip' detectado en {skip_pos}. Click.")
                      self.device_tap(skip_pos[0], skip_pos[1])
                      time.sleep(1)
                      return True
                 
            self.log("Encuesta Google: No se encontró botón Saltar/Skip tras X. Asumiendo cerrado.")
            return True
            
        # Si el contexto es MUY fuerte (ej: "tecnologia de google"), podemos arriesgar click ciego a la X
        if "tecnologia" in full_text or "technology" in full_text:
            self.log("Encuesta Google: Contexto fuerte pero no veo X. Usando click ciego (170, 80).")
            self.device_tap(170, 80)
            time.sleep(1)
            
            # Misma logica de refresco
            self.log("Encuesta Google: Buscando botón 'Saltar' post-click ciego...")
            new_scr = self.adb.take_screenshot()
            saltar_pos = self.ocr.find_text(new_scr, "Saltar", case_sensitive=True)
            if saltar_pos:
                self.device_tap(saltar_pos[0], saltar_pos[1])
                time.sleep(1)
            return True
        
        return False

    def interact_with_coin(self, screenshot, match_coin):
        """
        Lógica de interacción con la moneda de oro.
        """
        cx, cy, w, h = match_coin
        self.log(f"Interactuando con Moneda en ({cx}, {cy})...")
        self.device_tap(cx, cy)
        
        # Guardar tiempo de esta interacción
        self.last_reward_time = time.time()
        
    def check_device_timezone(self):
        """
        Detecta zona horaria usando getprop persist.sys.timezone.
        Itera ALL_ZONES para encontrar coincidencia.
        Retorna: 'NIUE', 'MADRID', 'KIRITIMATI' o 'UNKNOWN'.
        """
        output = self.adb._run_command(["getprop", "persist.sys.timezone"])
        
        if not output:
            return "UNKNOWN"
        
        tz_id = output.strip().upper()
        
        for zone in ALL_ZONES:
            # Extraer nombre clave del tz_id (ej: "NIUE" de "Pacific/Niue")
            zone_key = zone["tz_id"].split("/")[-1].upper()
            if zone_key in tz_id:
                return zone["name"]
        
        return "UNKNOWN"

    def get_current_zones(self):
        """
        Devuelve (home_zone, recharge_zone) para la hora actual.
        Itera SHIFTS comparando hour con start/end.
        """
        hour = datetime.datetime.now().hour
        
        for shift in SHIFTS:
            start = shift["start"]
            end = shift["end"]
            
            # Caso especial: end=0 significa medianoche (hora >= start)
            if end == 0:
                if hour >= start:
                    return (shift["home"], shift["recharge"])
            else:
                if start <= hour < end:
                    return (shift["home"], shift["recharge"])
        
        # Fallback (no debería llegar aquí)
        return (ZONE_MADRID, ZONE_KIRITIMATI)

    def is_in_home_zone(self):
        """
        ¿Estamos en la zona HOME del turno actual?
        Usa .upper() para comparación case-insensitive.
        """
        home, _ = self.get_current_zones()
        return self.current_timezone_state.upper() == home["name"].upper()

    def force_shift_transition(self):
        """
        Fuerza transición al HOME del turno actual.
        Reutiliza el flujo normal de cambio de zona.
        """
        home, _ = self.get_current_zones()
        self.log(f"🔄 Transición de turno: Viajando a {home['name']}")
        self.state_data["target_zone"] = home["name"]
        self.state = BotState.TZ_INIT

    def verify_and_fix_zone(self):
        """
        Verifica zona. Si no estamos en HOME, inicia viaje.
        Retorna True si podemos actuar, False si hay que esperar.
        """
        if self.is_in_home_zone():
            return True
        
        # No estamos en HOME → Forzar viaje
        home, _ = self.get_current_zones()
        self.log(f"⚠ Zona actual '{self.current_timezone_state}' ≠ HOME '{home['name']}'")
        self.force_shift_transition()
        return False

    def ensure_game_context(self):
        """
        Verifica que el juego esté en primer plano. 
        Si está en Ajustes u otra app, intenta restaurar el juego.
        Retorna True si tuvo que corregir el contexto (requiere espera).
        """
        current_pkg = self.adb.get_current_package()
        
        # Caso Ideal
        if current_pkg == PACKAGE_NAME:
            return False 
            
        # Ignorar si es "UNKNOWN" momentáneo (buffer de adb)
        if current_pkg == "UNKNOWN":
            return False

        self.log(f"⚠ Contexto incorrecto detectado: '{current_pkg}'")
        
        # 1. Atrapado en Ajustes (Crash durante cambio de zona)
        if "settings" in current_pkg:
            self.log("Atrapado en Ajustes. Cerrando y volviendo al juego...")
            self.adb.stop_app(current_pkg) # Force stop settings
            self.adb.start_app(PACKAGE_NAME)
            return True
            
        # 2. Launcher o cualquier otra App
        self.log(f"App fuera de foco. Lanzando {PACKAGE_NAME}...")
        self.adb.start_app(PACKAGE_NAME)
        return True

    def run(self):
        self.log(t("log_starting_bot"))
        if not self.adb.connect():
            self.log(t("log_device_not_connected"))
            self.stop_event.set()
            return

        # ===== CONFIGURACIÓN INICIAL DEL DISPOSITIVO =====
        # Activar WiFi si está desactivado
        if self.adb.ensure_wifi_enabled():
            self.log(t("log_wifi_enabled"))
        else:
            self.log(t("log_wifi_already_active"))
        
        # Poner brillo al mínimo para ahorrar batería
        self.log(t("log_brightness_min"))
        self.adb.set_brightness_min()
        # ================================================

        # Verificar si el juego está corriendo
        self.log(t("log_game_verifying", package=PACKAGE_NAME))
        if self.adb.get_current_package() != PACKAGE_NAME:
             self.log(t("log_game_launching"))
             self.adb.start_app(PACKAGE_NAME)
             
             # Esperar a que abra
             game_open = False
             for _ in range(35): # Aumentado a 35s por carga lenta
                 if self.is_stopped(): return
                 time.sleep(1)
                 if self.adb.get_current_package() == PACKAGE_NAME:
                     game_open = True
                     self.log(t("log_game_detected"))
                     break
            
             if not game_open:
                 self.log("⚠ El inicio estándar tardó. Intentando lanzamiento forzado...")
                 # Fallback: am start directo a la actividad principal (intento)
                 # Nota: .MainActivity suele ser el default, pero si falla no pasa nada grave
                 self.adb._run_command(["am", "start", "-n", f"{PACKAGE_NAME}/.MainActivity"])
                 time.sleep(5)
        else:
             self.log(t("log_game_already_open"))
             
        time.sleep(2) # Estabilización
        
        # Inicializar estado de zona horaria
        current_tz = self.check_device_timezone()
        if current_tz != "UNKNOWN":
            self.current_timezone_state = current_tz
        self.log(f"Estado Inicial Zona: {self.current_timezone_state}")
        
        # Verificar turno DAY/NIGHT y zona correcta
        home, recharge = self.get_current_zones()
        self.log(f"🌙 Turno actual: HOME={home['name']}, RECHARGE={recharge['name']}")
        
        if self.current_timezone_state.upper() != home["name"].upper():
            self.log(f"🚀 Arranque: {self.current_timezone_state} ≠ HOME {home['name']}. Forzando viaje.")
            self.state_data["target_zone"] = home["name"]
            self.state_data["zone_config"] = home
            self.state = BotState.TZ_INIT
        else:
            self.log(f"✅ Arranque: Ya en HOME {home['name']}")
            self.state = BotState.UNKNOWN
        
        self.last_state = None
        self.state_data.setdefault("target_zone", None)
        self.state_data.setdefault("zone_config", None)

        last_disconnect_log = 0
        while not self.is_stopped():
            # Check connection
            if not self.adb.is_connected():
                current_time = time.time()
                if current_time - last_disconnect_log > 10:
                    self.log(t("log_device_disconnected"))
                    last_disconnect_log = current_time
                time.sleep(5)
                continue

            self.run_state_machine()
            time.sleep(0.1) # Pequeña pausa para no saturar CPU


    def run_state_machine(self):
        """Dispatcher de la maquina de estados."""
        # Capturar estado ANTES de la accion
        state_before = self.state
        self.current_action = Action.NONE
        
        # --- OPTIMIZATION START ---
        # Single capture per loop cycle. Shared for Logic.
        try:
            self.current_screenshot = self.adb.take_screenshot()
            self.last_screenshot = self.current_screenshot
        except:
            self.current_screenshot = None
            self.last_screenshot = None
        # --- OPTIMIZATION END ---
        
        # Log de transicion visual
        if self.state != self.last_state:
            self.log(t("log_state_change", from_state=self.last_state.name if self.last_state else 'None', to_state=self.state.name))
            
            # --- LOBBY TIMEOUT TRACKER ---
            if self.state == BotState.GAME_LOBBY:
                self.lobby_enter_time = time.time()
            else:
                 self.lobby_enter_time = None
            # -----------------------------

            self.last_state = self.state

        # 0. Chequeo de Contexto Global (Rescue) - Excepto si estamos cambiando zona
        if "TZ_" not in self.state.name:
             if self.ensure_game_context():
                 time.sleep(3)
                 return

        # 1. Dispatch
        if self.state == BotState.UNKNOWN:
            self.handle_unknown()
        elif self.state == BotState.GAME_LOBBY:
            self.handle_game_lobby(self.current_screenshot)
        elif self.state == BotState.AD_INTERMEDIATE:
            self.handle_ad_intermediate(self.current_screenshot)
        elif self.state == BotState.AD_WATCHING:
            self.handle_ad_watching() # Own loop
        elif self.state == BotState.REWARD_SCREEN:
            self.handle_reward_screen_state(self.current_screenshot)
        elif self.state == BotState.STUCK_AD:
            self.handle_stuck_ad()
        elif "TZ_" in self.state.name:
            self.handle_timezone_sequence(self.current_screenshot)


    def handle_unknown(self):
        """Estado inicial o de recuperación."""
        # Por defecto asumimos Lobby si el juego está abierto
        self.log("Estado UNKNOWN -> Asumiendo GAME_LOBBY...")
        self.state = BotState.GAME_LOBBY

    def handle_stuck_ad(self):
        """
        Estado de recuperación cuando el bot se queda atrapado en un anuncio.
        Intenta escapar usando HOME + volver al juego.
        Solo transiciona a GAME_LOBBY si confirma anchors positivamente.
        """
        # Inicializar contador si no existe
        if not hasattr(self, 'stuck_ad_attempts'):
            self.stuck_ad_attempts = 0
        
        self.stuck_ad_attempts += 1
        self.log(f"🔄 STUCK_AD: Intento de escapada {self.stuck_ad_attempts}/5...")
        
        # Secuencia de escapada: HOME + volver al juego
        self.adb.input_keyevent(3)  # HOME
        time.sleep(1.0)
        self.adb.start_app(PACKAGE_NAME)
        time.sleep(3.0)
        
        # Verificar si escapamos
        screenshot = self.adb.take_screenshot()
        self.update_live_view(screenshot)
        
        if self.check_lobby_anchors(screenshot):
            self.log("✅ Escapada exitosa. Volviendo a GAME_LOBBY.")
            self.stuck_ad_attempts = 0  # Reset
            self.state = BotState.GAME_LOBBY
            return
        
        # Verificar máximo intentos
        if self.stuck_ad_attempts >= 5:
            self.log("❌ Máximo intentos de escapada alcanzado. Esperando 30s antes de reintentar...")
            self.stuck_ad_attempts = 0  # Reset para nuevo ciclo
            time.sleep(30)  # Pausa larga antes de reintentar
        else:
            self.log(f"⚠️ Escapada fallida. Reintentando en 5s...")
            time.sleep(5)
        
        # Permanecer en STUCK_AD para seguir intentando

    def handle_game_lobby(self, screenshot):
        """
        Buscando activo (Moneda, Botón Anuncio).
        Transiciones:
        -> AD_WATCHING (Moneda/Cloud click)
        -> TZ_INIT (No ads / Timeout)
        """
        # OPTIMIZATION: Use shared screenshot
        if screenshot is None: return
        self.update_live_view(screenshot)

        # --- CHECK TIMEOUT ---
        if self.lobby_enter_time and (time.time() - self.lobby_enter_time > 120): # 2 minutes
             self.log("TIMEOUT: Mas de 2 minutos en Lobby sin actividad. Reiniciando juego...")
             self.adb.stop_app(PACKAGE_NAME)
             self.state = BotState.UNKNOWN
             return
        # ---------------------

        # 0. Chequeo de Rescate: ¿Estamos viendo ya una Recompensa?
        for t_name in REWARD_CLOSE_TEMPLATES:
             if self.vision.find_template(screenshot, os.path.join(ASSETS_DIR, t_name)):
                  self.log("Detectada Pantalla Recompensa desde Lobby (Recuperación).")
                  self.state = BotState.REWARD_SCREEN
                  return

        # 1. Pantalla Intermedia (Confirmar) - A veces salta directo
        match_inter = self._find_template_with_memory(screenshot, INTERMEDIATE_TEMPLATE, "tmpl_intermediate")
        if match_inter:
            self.log("Detectada Pantalla Intermedia desde Lobby.")
            self.state = BotState.AD_INTERMEDIATE
            return

        # 4. Moneda Normal
        match_coin = self._find_template_with_memory(screenshot, COIN_ICON_TEMPLATE, "tmpl_coin_icon")
        if match_coin:
             # VERIFICACIÓN DAY/NIGHT: ¿Estamos en la zona HOME del turno actual?
             if not self.verify_and_fix_zone():
                  return  # Se inició viaje a HOME, esperar
             
             # Click en moneda
             self.interact_with_coin(screenshot, match_coin)
             time.sleep(1.0)
             # Asumimos que tras moneda viene o Intermedia o el Anuncio directo
             self.state = BotState.AD_INTERMEDIATE
             return

        # 5. Sin Oro / No More Ads
        match_no_gold = self._find_template_with_memory(screenshot, NO_MORE_GOLD_TEMPLATE, "tmpl_no_more_gold")
        if match_no_gold:
            self.log("Detectado 'No hay más anuncios'. Iniciando ciclo Timezone.")
            # Restriccion horaria ELIMINADA para modo experimental 24h
            # El ciclo matutino se gestiona en TZ_INIT
            self.state = BotState.TZ_INIT
            return

        # Nada detectado

    def handle_ad_intermediate(self, screenshot):
        """
        Pantalla de 'Confirmar' (Nube/Video).
        Transition -> AD_WATCHING
        """
        if screenshot is None: return
        self.update_live_view(screenshot)
        
        # Buscar botón confirmar
        # Primero confirmar que seguimos en la pantalla (o si ya saltó al anuncio)
        # A veces el click de moneda fue tan rápido que ya estamos viendo el video
        
        match_inter = self._find_template_with_memory(screenshot, INTERMEDIATE_TEMPLATE, "tmpl_intermediate")
        if match_inter:
             cx, cy, w, h = match_inter
             match_conf = self._find_template_with_memory(screenshot, AD_CONFIRM_TEMPLATE, "tmpl_ad_confirm")
             
             if match_conf:
                 bx, by, bw, bh = match_conf
                 self.device_tap(bx, by)
             else:
                 self.device_tap(cx, cy)
             
             self.log("Confirmación enviada. Esperando anuncio...")
             time.sleep(2.5)
             self.state = BotState.AD_WATCHING
             return
        else:
             # Si no vemos la intermedia, quizás ya se fue o nunca estuvo
             self.log("No veo intermedia. Volviendo a checkear Lobby/Watching.")
             # Fallback a Lobby que redespachará
             self.state = BotState.GAME_LOBBY

    def handle_ad_watching(self):
        """
        Monitorizando anuncio.
        Transitions:
        -> REWARD_SCREEN (X cerrada, >> cerrado)
        -> GAME_LOBBY (Web back, Survey skip)
        -> STUCK_AD (Timeout sin poder salir)
        """
        # La lógica de process_active_ad era bloqueante (while loop).
        # Para la máquina de estados, deberíamos hacerla no bloqueante o mantener el while dentro 
        # (mini-bucle de estado) si queremos mantener la lógica de 'stall detection' continua.
        # Dado que process_active_ad ya es robusta, la llamaremos como "acción de estado" 
        # que retorna cuando termina el anuncio.
        
        # Nota: process_active_ad retorna True si terminó bien (closed), False si falló/timeout
        result = self.run_ad_watching_logic()
        
        if result == "REWARD":
             self.state = BotState.REWARD_SCREEN
        elif result == "LOBBY":
             self.state = BotState.GAME_LOBBY
        elif result == "STUCK_AD":
             self.log("⚠️ Transición a STUCK_AD para intentar recuperación...")
             self.state = BotState.STUCK_AD
        else:
             # Fallback: Si retorna algo inesperado, también ir a STUCK_AD
             self.log(f"Resultado Ad Watching inesperado: {result}. Estado -> STUCK_AD")
             self.state = BotState.STUCK_AD

    def check_lobby_anchors(self, screenshot):
        """
        Verifica si hay elementos inequívocos del Lobby.
        Retorna True si estamos CASI SEGUROS de que es el Lobby.
        Esto actúa como 'Safety Guard' para no detectar anuncios erróneamente.
        """
        # 1. Nuevos Assets de Lobby (Definidos por Usuario)
        # Son la prueba 'fuerte' de que estamos en el menu principal
        if self.vision.find_template(screenshot, os.path.join(ASSETS_DIR, LOBBY_TEMPLATE_1)):
            self.log("⚓ Anchor Detectado: Lobby Asset 1.")
            return True
            
        if self.vision.find_template(screenshot, os.path.join(ASSETS_DIR, LOBBY_TEMPLATE_2)):
            self.log("⚓ Anchor Detectado: Lobby Asset 2.")
            return True

        # 2. Pantalla Intermedia (Nube/Confirmar)
        # Si estamos aquí, NO estamos viendo un video aún.
        if self.vision.find_template(screenshot, os.path.join(ASSETS_DIR, INTERMEDIATE_TEMPLATE)):
            self.log("⚓ Anchor Detectado: Pantalla Intermedia (Pre-Ad).")
            return True

        # El coin_icon solo indica 'Ads Disponibles', pero si lo vemos 
        # tambien es indicativo de que NO es un video de anuncio. 
        # Lo mantenemos como fallback o señal positiva secundaria.
        if self._find_template_with_memory(screenshot, COIN_ICON_TEMPLATE, "tmpl_coin_icon"):
             self.log("⚓ Anchor Detectado: Moneda (Ads Disponibles).")
             return True

        return False

    def run_ad_watching_logic(self):
        """Lógica encapsulada de mirar anuncio."""
        self.log("👀 Estado: WATCHING_AD")
        start_wait = time.time()
        ignored_zones = []
        
        # Variables Loop Seguridad
        last_gray = None
        last_screenshot_for_corners = None  # Para detección de cambio en esquinas
        stall_counter = 0
        black_screen_counter = 0
        
        focus_recovery_attempts = 0
        ff_persistence_counter = 0
        corner_change_boost = False  # Si detectamos cambio en esquinas, buscar más agresivamente
        
        while time.time() - start_wait < 150: # Timeout
            if self.is_stopped(): return "LOBBY"
            
            # 0. CHECK FOCUS FIRST (PRIORIDAD MAXIMA)
            current_pkg = self.adb.get_current_package()
            if current_pkg and current_pkg != PACKAGE_NAME and "settings" not in current_pkg.lower():
                focus_recovery_attempts += 1
                self.log(f"⚠ Perdida de foco durante anuncio: {current_pkg} (intento {focus_recovery_attempts})")
                
                # Si son demasiados intentos, abortar a LOBBY
                if focus_recovery_attempts > 5:
                    self.log("❌ Demasiados intentos de recuperar foco. Abortando a LOBBY.")
                    self.adb.input_keyevent(3)  # Home
                    time.sleep(1)
                    return "LOBBY"
                
                # Primero cerrar la app intrusa con Back
                self.adb.input_keyevent(4)  # Back
                time.sleep(1)
                
                # Traer juego al frente con monkey (mas efectivo)
                self.adb._run_command(["monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])
                time.sleep(2)
                continue
            else:
                focus_recovery_attempts = 0  # Reset counter si estamos bien
            
            screenshot = self.adb.take_screenshot()
            self.update_live_view(screenshot)

            # --- DETECCIÓN DE CAMBIO EN ESQUINAS (1.E) ---
            if last_screenshot_for_corners is not None:
                changed_corners = self.vision.detect_corner_changes(last_screenshot_for_corners, screenshot)
                if changed_corners:
                    self.log(f"🔍 Cambio detectado en esquinas: {changed_corners}. Activando búsqueda intensiva...")
                    corner_change_boost = True
            last_screenshot_for_corners = screenshot.copy() if screenshot is not None else None
            # -----------------------------------------------

            # --- ANCHOR CHECK (LOBBY SAFETY) ---
            if self.check_lobby_anchors(screenshot):
                 self.log("⚠ Lobby detectado por Anchors durante 'WATCHING_AD'. Forzando salida a LOBBY.")
                 return "LOBBY"
            # -----------------------------------

            # 1. Google Survey (Transition -> LOBBY)
            if self.handle_google_survey(screenshot):
                 self.log("Encuesta Google gestionada. Volviendo a Lobby.")
                 return "LOBBY"

            # 2. Web Consent (Transition -> STAY/LOBBY via Back)
            if self.handle_web_consent(screenshot):
                 time.sleep(2)
                 continue 

            # 3. Navegador Interno (Web Bar Close)
            # Transición -> Click -> Esperar X/Cierre (Loop)
            match_web_close = self.vision.find_template(screenshot, os.path.join(ASSETS_DIR, WEB_BAR_CLOSE_TEMPLATE))
            if match_web_close:
                 self.log("Navegador Interno detectado (Bar Close). Click.")
                 self.device_tap(match_web_close[0], match_web_close[1])
                 time.sleep(2)
                 continue

            # 4. Dynamic X (Transition -> REWARD)
            match_dynamic = self.vision.find_close_button_dynamic(screenshot, ignored_zones=ignored_zones)
            if match_dynamic:
                 self.log("X Detectada. Click.")
                 cx, cy, w, h = match_dynamic
                 self.device_tap(cx, cy)
                 time.sleep(2)
                 
                 # --- CHECK FALSO POSITIVO (Resume) ---
                 # A veces la X es para cerrar el anuncio prematuramente y sale "Seguir viento?"
                 check_scr = self.adb.take_screenshot()
                 match_resume = self.vision.find_template(check_scr, os.path.join(ASSETS_DIR, AD_RESUME_TEMPLATE))
                 if match_resume:
                     self.log("⚠ Falso positivo X (Detectado 'Seguir Viendo'). Reanudando...")
                     # Click en "Seguir viendo" (Resume)
                     rx, ry, rw, rh = match_resume
                     self.device_tap(rx, ry)
                     ignored_zones.append((cx, cy, w, h)) # Ignorar esta X en el futuro próximo
                     time.sleep(1)
                     continue
                 # -------------------------------------

                 # Fix: No asumir que el anuncio terminó solo por ver una X.
                 # Podría ser un anuncio multi-stage. Seguir en loop.
                 self.log("X clickeada. Continuando monitoreo (Multi-Stage protection).")
                 continue

            # 5. Reward Close Directo (Check) - PRIORIDAD ALTA
            # Si vemos la X de recompensa, salimos ya, no importa si parece haber un Fast Forward
            for t_name in REWARD_CLOSE_TEMPLATES:
                 if self.vision.find_template(screenshot, os.path.join(ASSETS_DIR, t_name)):
                      self.log("Reward Close detectado directo.")
                      return "REWARD"

            # 6. Fast Forward (Transition -> REWARD)
            match_ff = self.vision.find_fast_forward_button(screenshot)
            if match_ff:
                 ff_persistence_counter += 1
                 
                 # Si detectamos cambio en esquinas, reducir persistencia requerida
                 required_persistence = 2 if corner_change_boost else 3
                 self.log(f"Fast Forward detectado ({ff_persistence_counter}/{required_persistence})...")
                 
                 if ff_persistence_counter >= required_persistence:
                     self.log("Fast Forward CONFIRMADO. Click.")
                     # Usar offset aleatorio pequeño para evitar "píxel muerto" o detección de bot
                     import random
                     ff_x, ff_y, ff_w, ff_h = match_ff
                     
                     # Offset +/- 5px del centro
                     off_x = random.randint(-5, 5)
                     off_y = random.randint(-5, 5)
                     
                     # Click con duración explícita (0.15s) para asegurar registro
                     self.device_tap(ff_x + off_x, ff_y + off_y, duration=0.15)
                     
                     ff_persistence_counter = 0  # Reset
                     corner_change_boost = False  # Reset boost
                     time.sleep(2.0)  # Aumentar espera post-click
                     continue
            else:
                 ff_persistence_counter = 0 # Reset si se pierde un frame
            
            # --- CHEQUEOS DE SEGURIDAD (Stall/Black) ---
            import cv2
            import numpy as np
            gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            
            # Black Screen
            if np.mean(gray) < 10:
                black_screen_counter += 1
                if black_screen_counter > 6: # ~15s
                    self.log("⚠ Pantalla negra persistente. Pulsando HOME dos veces...")
                    self.adb.input_keyevent(3)  # HOME 1
                    time.sleep(0.5)
                    self.adb.input_keyevent(3)  # HOME 2
                    time.sleep(1)
                    black_screen_counter = 0  # Reset counter
                    # El bot detectará pérdida de foco y volverá al juego automáticamente
                    continue
            else:
                black_screen_counter = 0
            
            # Stall Detection (Imagen congelada)
            if last_gray is not None:
                score = cv2.matchTemplate(gray, last_gray, cv2.TM_CCOEFF_NORMED)[0][0]
                if score > 0.98: # Muy similar
                    stall_counter += 1
                else:
                    stall_counter = 0
               
                if stall_counter > 10: # ~20-25s congelado
                    self.log("⚠ Anuncio congelado (Stall). Intentando tap central...")
                    self.device_tap(int(self.screen_width/2), int(self.screen_height/2))
                    stall_counter = 0 # Reset para dar chance
            
            last_gray = gray
            # -------------------------------------------

            time.sleep(1.5)
            
        # ===== SECUENCIA DE ESCAPADA POST-TIMEOUT =====
        self.log("⏰ Timeout viendo anuncio. Iniciando secuencia de escapada...")
        
        # Paso 1: BACK x2
        self.log("Paso 1/3: Intentando BACK x2...")
        self.adb.input_keyevent(4)  # Back 1
        time.sleep(0.5)
        self.adb.input_keyevent(4)  # Back 2
        time.sleep(2.0)
        
        scr = self.adb.take_screenshot()
        self.update_live_view(scr)
        if self.check_lobby_anchors(scr):
             self.log("✅ Escapada exitosa con BACK x2.")
             return "LOBBY"
        
        # Paso 2: HOME + volver al juego
        self.log("Paso 2/3: BACK no funcionó. Intentando HOME + volver al juego...")
        self.adb.input_keyevent(3)  # HOME
        time.sleep(1.0)
        self.adb.start_app(PACKAGE_NAME)
        time.sleep(3.0)
        
        scr = self.adb.take_screenshot()
        self.update_live_view(scr)
        if self.check_lobby_anchors(scr):
             self.log("✅ Escapada exitosa con HOME + juego.")
             return "LOBBY"
        
        # Check for Reward screen (Recovery from direct reward state)
        for t_name in REWARD_CLOSE_TEMPLATES:
            if self.vision.find_template(scr, os.path.join(ASSETS_DIR, t_name)):
                self.log("✅ Escapada exitosa: Pantalla Recompensa detectada.")
                return "REWARD"
        
        # Paso 3: Si aún no estamos en lobby, ir a STUCK_AD
        self.log("❌ No se detectó Lobby tras escapada. Estado -> STUCK_AD")
        return "STUCK_AD"

    def handle_reward_screen(self, screenshot=None):
        """
        Gestiona la pantalla de recompensa:
        1. Lee la cantidad de oro (GoldLogger).
        2. Actualiza estadísticas.
        3. Cierra la ventana.
        """
        self.log("💰 Procesando Recompensa...")
        time.sleep(1) # Estabilizar animación
        
        # Use shared screenshot if provided, otherwise capture (fallback for direct usage)
        if screenshot is None:
            screenshot = self.adb.take_screenshot()
        
        self.update_live_view(screenshot) # Feedback visual
        
        # 1. OCR Lectura
        gold_amount = self.ocr.extract_gold_amount(screenshot)
        if gold_amount > 0:
            self.logger.log_gold(gold_amount)
            
            self.session_gold += gold_amount
            self.session_ads += 1
            self.log(f"🤑 Recompensa Leída: {gold_amount} GC. Total Sesión: {self.session_gold}")
            
            # Callback Stats
            if self.stats_callback:
                t_gold = self.logger.get_todays_gold()
                h_gold = self.logger.get_all_time_gold()
                
                # Calcular tasas
                elapsed = (time.time() - self.session_start) / 3600
                gold_rate = self.session_gold / elapsed if elapsed > 0 else 0
                ads_rate = self.session_ads / elapsed if elapsed > 0 else 0
                
                # gui.py espera: (today_gold, history_gold, ads_per_hour, gold_per_hour)
                self.stats_callback(int(t_gold), int(h_gold), ads_rate, gold_rate, self.session_gold)
        else:
            self.log("⚠ No pude leer la cantidad de oro (o fue 0).")

        # 2. Cerrar Ventana
        # Buscar botones de cierre
        closed = False
        for t_name in REWARD_CLOSE_TEMPLATES:
             memory_key = f"tmpl_reward_close_{t_name.replace('.png', '')}"
             match = self._find_template_with_memory(screenshot, t_name, memory_key)
             if match:
                 cx, cy, w, h = match
                 self.log(f"Cerrando recompensa (Botón: {t_name})...")
                 self.device_tap(cx, cy)
                 closed = True
                 break
        
        if not closed:
            self.log("⚠ No vi botón de cerrar recompensa. Usando Tap en esquina superior derecha (Fallback).")
            # Fallback a coordenadas típicas de cierre
            self.device_tap(self.screen_width - 50, 50) # Top-Right Corner assumption? 
            # Mejor usar un punto seguro, pero si no hay template...
            # Intentar back key?
            # self.adb.input_keyevent(4) 
        
        time.sleep(2) # Esperar a que cierre

    def handle_reward_screen_state(self, screenshot):
        """Lectura de oro y cierre."""
        self.handle_reward_screen(screenshot) 
        self.state = BotState.GAME_LOBBY


    def handle_timezone_sequence(self, screenshot):
        """Sub-máquina para Timezone."""
        if self.state == BotState.TZ_INIT:
             # Refresh timezone real ONLY if needed
             if self.current_timezone_state == "UNKNOWN":
                 real_tz = self.check_device_timezone()
                 if real_tz != "UNKNOWN":
                     self.current_timezone_state = real_tz
             
             # Toggle dinámico basado en turno actual
             home, recharge = self.get_current_zones()
             current = self.current_timezone_state.upper()
             
             if current == home["name"].upper():
                 target = recharge  # Estamos en home, ir a recharge
             else:
                 target = home      # No estamos en home, ir a home
             
             self.state_data["target_zone"] = target["name"]
             self.state_data["zone_config"] = target  # Guardar config completa
             self.log(f"Turno actual: {home['name']}->{recharge['name']}. Viajando a: {target['name']}")

             self.log("Abriendo Configuración de Fecha...")
             self.adb._run_command(["am", "start", "-a", "android.settings.DATE_SETTINGS"])
             
             # OPTIMIZATION: Wait for package instead of sleep
             if self.wait_for_package("settings", timeout=2.0):
                 self.log(f"✅ Ajustes detectados rápido.")
             else:
                 self.log(f"⏳ Espera estándar agotada para Ajustes.")
                 
             self.state = BotState.TZ_SEARCH_REGION
             
        elif self.state == BotState.TZ_SEARCH_REGION:
             self.log("Buscando Region...")
             time.sleep(0.5) # Reduced from 1.0s
             
             # Need fresh screen after opening settings
             scr = self.adb.take_screenshot()
             self.update_live_view(scr)
             
             h_scr, w_scr = scr.shape[:2]
             limit_y = int(h_scr * 0.85)
             all_texts = self.ocr.get_screen_texts(scr)
             
             # Buscar "Region" (prioridad)
             region_found = False
             for text, x, y, w, h in all_texts:
                 if "Region" in text and (y + h//2) < limit_y:
                     cx, cy = x + w//2, y + h//2
                     self.log(f"✅ Region encontrado en ({cx},{cy}) - Guardando en BD")
                     self.logger.save_ocr_memory("ocr_tz_region", text, x, y, w, h, 0)
                     # Fast tap
                     self.device_tap(cx, cy)
                     time.sleep(1.0)
                     self.state = BotState.TZ_INPUT_SEARCH
                     region_found = True
                     break
             
             if not region_found:
                 # Buscar "Seleccionar"
                 for text, x, y, w, h in all_texts:
                     if "Seleccionar" in text and (y + h//2) < limit_y:
                         cx, cy = x + w//2, y + h//2
                         self.log(f"✅ Seleccionar encontrado en ({cx},{cy}) - Guardando en BD")
                         self.logger.save_ocr_memory("ocr_tz_seleccionar", text, x, y, w, h, 0)
                         # Fast tap
                         self.device_tap(cx, cy)
                         time.sleep(1.0)
                         # Permanece en TZ_SEARCH_REGION para buscar Region
                         break
                 else:
                     self.log("❌ No encontre Region ni Seleccionar. Reintentando...")
                     time.sleep(0.5)
                 
        elif self.state == BotState.TZ_INPUT_SEARCH:
             zone_config = self.state_data.get("zone_config")
             if not zone_config:
                 # Fallback: buscar config por nombre
                 target_name = self.state_data["target_zone"]
                 zone_config = next((z for z in ALL_ZONES if z["name"] == target_name), ZONE_MADRID)
                 self.state_data["zone_config"] = zone_config
             
             term = zone_config["search_input"]
             
             self.log(f"Buscando lupa para: {term}")
             time.sleep(0.5) # Reduced from 1.0s
             scr = self.adb.take_screenshot()
             self.update_live_view(scr)
             
             # Buscar LUPA con find_template directo (threshold 0.7, check_negative)
             template_path = os.path.join(ASSETS_DIR, SEARCH_ICON_TEMPLATE)
             match = self.vision.find_template(scr, template_path, threshold=0.7, check_negative=True)
             
             if match:
                 cx, cy, cw, ch = match
                 # Guardar en memoria
                 self.logger.save_ocr_memory("tmpl_search_icon", SEARCH_ICON_TEMPLATE, cx - cw//2, cy - ch//2, cw, ch, 0)
                 # Click a la DERECHA de la lupa (en el campo de texto)
                 click_x = cx + cw + 50
                 click_y = cy
                 self.log(f"🔍 Lupa en ({cx},{cy}). Click en campo ({click_x}, {click_y}).")
                 self.device_tap(click_x, click_y)
             else:
                 self.log("⚠ Lupa no encontrada. Click Fallback (540, 150).")
                 self.device_tap(540, 150) 
                 
             time.sleep(1.5) # Aumentado de 1.0s a 2.0s para dar tiempo a focus
             
             # Borrar texto anterior (20 backspaces)
             self.log("⌨ Limpiando campo de texto...")
             for _ in range(20):
                 self.adb._run_command(["input", "keyevent", "67"])
             
             self.log(f"⌨ Escribiendo texto: {term}")
             self.adb._run_command(["input", "text", term])
             
             # OPTIMIZATION: Polling for results
             self.log("⌨ Esperando resultados (polling)...")
             found_results = False
             for _ in range(6): # Max 3s (6 * 0.5s)
                 time.sleep(0.5)
                 scr_check = self.adb.take_screenshot()
                 # Check if we see text that looks like a result
                 txts = self.ocr.get_screen_texts(scr_check, min_y=250)
                 # Si hay texto en la zona de resultados, asumimos que cargó
                 if len(txts) > 0:
                     self.log(f"✅ Resultados detectados ({len(txts)} items).")
                     found_results = True
                     break
             
             if not found_results:
                 self.log("⚠ Timeout esperando resultados. Continuando a ciegas.")
             
             self.state = BotState.TZ_SELECT_COUNTRY
             
        elif self.state == BotState.TZ_SELECT_COUNTRY:
             zone_config = self.state_data.get("zone_config")
             # Usar search_input (parcial: "Espa") para búsqueda, igual que código original
             term = zone_config["search_input"] if zone_config else "Espa"
             
             if self._wait_click_country_result(term):
                 self.log(f"País {term} seleccionado.")
                 # Si needs_city=False (Niue), saltar directamente a TZ_RETURN_GAME
                 if zone_config and not zone_config.get("needs_city", True):
                     self.log(f"Zona {zone_config['name']} no requiere ciudad. Completado.")
                     self.current_timezone_state = zone_config["name"]
                     self.state = BotState.TZ_RETURN_GAME
                 else:
                     self.state = BotState.TZ_SELECT_CITY
             else:
                 self.log("No encontré país. Reintentando...")
                 self.state = BotState.GAME_LOBBY
                 
        elif self.state == BotState.TZ_SELECT_CITY:
             zone_config = self.state_data.get("zone_config")
             if not zone_config:
                 target_name = self.state_data["target_zone"]
                 zone_config = next((z for z in ALL_ZONES if z["name"] == target_name), ZONE_MADRID)
             
             city = zone_config.get("city_match", "Madrid")
             memory_key = f"tz_city_{city.lower()}"
             
             # Smart Retry Init
             if "city_blacklist" not in self.state_data:
                 self.state_data["city_blacklist"] = []
             
             # OPTIMIZATION: Quick Check with Hint Coords
             memory = self.logger.get_ocr_memory(memory_key)
             hint_coords = None
             
             # VALIDACIÓN MEMORIA
             if memory and memory["w"] > 0 and memory["w"] < 1000: # Sanity check simple
                 mx, my, mw, mh = memory["x"], memory["y"], memory["w"], memory["h"]
                 
                 # Check Blacklist
                 is_blacklisted = False
                 for (bx, by, bw, bh) in self.state_data["city_blacklist"]:
                     if abs((mx+mw//2) - (bx+bw//2)) < 50:
                         is_blacklisted = True
                         break
                 
                 if not is_blacklisted:
                     hint_coords = (mx, my, mw, mh)
                     self.log(f"🧠 Memoria disponible para QuickCheck: {hint_coords}")
                     
                     # Quick Check: Take screenshot and look ONLY at hint region first?
                     # Actually, `find_text_adaptive` takes hint_coords but searches whole if fails.
                     # We can try a super-fast verify:
                     time.sleep(0.5) # Minimal wait for render
                     scr = self.adb.take_screenshot()
                     
                     # Crop region (with margin)
                     margin = 20
                     y1 = max(0, my - margin)
                     y2 = min(scr.shape[0], my + mh + margin)
                     x1 = max(0, mx - margin)
                     x2 = min(scr.shape[1], mx + mw + margin)
                     
                     crop = scr[y1:y2, x1:x2]
                     found_in_crop = self.ocr.find_text(crop, city)
                     
                     if found_in_crop:
                         self.log(f"⚡ QUICK CHECK ÉXITO: '{city}' encontrado en memoria.")
                         # Adjust coords to global
                         cx, cy = found_in_crop
                         final_x = x1 + cx
                         final_y = y1 + cy
                         
                         self.device_tap(final_x, final_y)
                         # Skip to Verification
                         self.current_timezone_state = zone_config["name"]
                         # Refactored verification (removed phantom call wait_return_to_settings)
                         self.logger.save_ocr_memory(memory_key, city, mx, my, mw, mh, 0) # Confirmamos memoria
                         # For now, duplicate logic or let it flow?
                         # Let's just set a flag to skip the heavy search below logic
                         # But easier to just return/break
                         # We need to do the Return Verification here as well.
                         if self.verify_return_to_settings():
                             self.log(f"⚡ Zona cambiada a {city} (Quick).")
                             self.state = BotState.TZ_RETURN_GAME
                             return

             # Si falla Quick Check o no hay memoria, hacemos el Full Scan estándar
             self.log("🐢 QuickCheck falló/no-memoria. Iniciando escaneo completo...")
             time.sleep(1.5) # Wait resto del tiempo (ya esperamos 0.5)
             scr = self.adb.take_screenshot()
             
             # DEBUG: Ver qué texto hay en la lista de ciudades
             # all_texts = self.ocr.get_screen_texts(scr)
             # self.log(f"DEBUG CITY OCR: {[t[0] for t in all_texts]}")
             
             # MASKING: Tachar zonas de la blacklist
             for (bx, by, bw, bh) in self.state_data["city_blacklist"]:
                  cv2.rectangle(scr, (bx, by), (bx+bw, by+bh), (0, 0, 0), -1)

             # Re-Load memory for adaptive search guidance (if valid)
             if hint_coords:
                  self.log(f"🧠 Usando Hint Coords para búsqueda adaptativa global.")
             else:
                  self.log(f"🧠 Buscando full screen (sin memoria).")
             
             # Búsqueda adaptativa
             result = self.ocr.find_text_adaptive(scr, city, hint_coords=hint_coords)
             
             if result:
                 rx, ry, rw, rh, threshold_used = result
                 
                 # MEJORA ROBUSTEZ CLICK:
                 # scr es numpy array (CV2). Usar shape (h, w).
                 screen_h, screen_w = scr.shape[:2]
                 click_x = rx + rw // 2
                 click_y = ry + rh // 2
                 
                 self.log(f"✅ Ciudad '{city}' encontrada. Click ROBUSTO en fila: ({click_x},{click_y}) (Text: {rx},{ry})")
                 
                 # Single Tap Robusto (100ms swipe)
                 self.device_tap(click_x, click_y)
                 time.sleep(0.5)
                 
                 # Guardar en memoria para próxima vez (guardamos rx/ry originales del texto)
                 # SOLO si funciona (lo hacemos tras verificacion), pero aqui guardamos provisionalmente
                 # para validacion. Si falla, borraremos.
                 
                 self.current_timezone_state = zone_config["name"]
                 
                 # VERIFICACIÓN DE RETORNO A "SELECCIONAR ZONA HORARIA"
                 if self.verify_return_to_settings():
                      self.log(f"Zona cambiada a {city}. Volviendo al juego...")
                      self.logger.save_ocr_memory(memory_key, city, rx, ry, rw, rh, threshold_used) # CONFIRMAMOS MEMORIA
                      self.state = BotState.TZ_RETURN_GAME
                 else:
                      self.log(f"❌ Click en '{city}' falló (No volvimos a Settings). Blacklisting zona y reintentando...")
                      # 1. Borrar memoria (era mala)
                      self.logger.save_ocr_memory(memory_key, "", 0, 0, 0, 0, 0)
                      # 2. BLACKLIST
                      self.state_data["city_blacklist"].append((rx, ry, rw, rh))
                      time.sleep(1)

             else:
                 # SIN FALLBACK: Quedarse en el estado para reintentar
                 self.log(f"❌ No se pudo encontrar ciudad '{city}' tras OCR adaptativo (Masked). Reintentando...")
                 
                 # Si la blacklist está llena y no encontramos nada, quizás limpiar blacklist?
                 if len(self.state_data["city_blacklist"]) > 0:
                     self.log("⚠ No encuentro nada y tengo blacklist. Limpiando blacklist por si acaso.")
                     self.state_data["city_blacklist"] = []
                     
                 time.sleep(2)

        elif self.state == BotState.TZ_RETURN_GAME:
             self.log("Resumiendo juego (Bring to Front)...")
             
             # OPTIMIZATION PROACTIVE: 
             # 1. Matar Ajustes para asegurar focus
             self.adb.stop_app("com.android.settings")
             time.sleep(0.5)
             
             # 2. Lanzar juego con Monkey (más robusto que am start directo)
             # 2. Lanzar juego con Monkey (más robusto que am start directo)
             self.adb.start_app(PACKAGE_NAME)
             
             # OPTIMIZATION: Wait for package instead of sleep(4)
             if self.wait_for_package(PACKAGE_NAME, timeout=8.0):
                 self.log("✅ Juego recuperó foco.")
                 time.sleep(1.0) # Estabilización GPU
             else:
                 self.log("⚠ Timeout esperando foco juego. Continuando...")
             self.state_data.clear() # Limpiar objetivo para siguiente ciclo
             self.state = BotState.GAME_LOBBY

if __name__ == "__main__":
    # Modo CLI Legacy
    bot = RealRacingBot()
    bot.run()
