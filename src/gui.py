import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from PIL import Image, ImageTk
import cv2
import queue
import subprocess
import time
import json
import os
from datetime import datetime, timedelta
from adb_wrapper import ADBWrapper
from logger import GoldLogger
from i18n import t, get_current_language, set_language, get_supported_languages, get_language_name, register_language_change_callback
from config import SHIFTS


# Importamos la clase del bot (que refactorizaremos en breve)
# Importación diferida o asumiendo que main.py estará listo
try:
    from main import RealRacingBot
except ImportError:
    RealRacingBot = None

class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(t("app_title"))
        # Aumentado ancho a 1200 para acomodar las 3 columnas sin cortes
        self.root.geometry("1200x720")
        self.root.configure(bg="#102A43") # Match Theme BG
        
        self.adb_preview = ADBWrapper()
        self.is_bot_running = False
        
        self.bot_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.image_queue = queue.Queue()
        
        self.bot_instance = None
        
        # Stat block title labels for translation updates (must be before _setup_ui)
        self.stat_title_labels = {}
        
        self.logo_photo = None
        try:
            # Robust Path Resolution
            base_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(base_dir, "assets", "app_logo.png")
            print(f"DEBUG: Intentando cargar logo desde: {logo_path}")
            
            if os.path.exists(logo_path):
                # UI Logo (Load Logic)
                pil_img = Image.open(logo_path)
                
                # Window Icon (Use PIL object)
                icon_photo = ImageTk.PhotoImage(pil_img)
                self.root.iconphoto(True, icon_photo)
                
                # Banner Logo (Resize Larger)
                pil_resized = pil_img.resize((100, 100), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(pil_resized)
                print("DEBUG: Logo cargado correctamente.")
            else:
                print(f"DEBUG: Logo NO encontrado en {logo_path}")
        except Exception as e:
            print(f"Error loading logo: {e}")

        self._apply_theme()
        self._setup_ui()
        self._start_queue_processing()
        
        # Hilo de preview constante
        self.preview_thread = threading.Thread(target=self._run_idle_preview, daemon=True)
        self.preview_thread.start()
        
        # Overlay Drawing State
        self.current_pil_image = None
        self.current_photo = None
        self.current_ratio = 1.0
        self.current_x_offset = 0
        self.current_y_offset = 0
        self.bg_image_id = None # ID for persistent background image

        # Session Data
        self.logger = GoldLogger()
        self.session_start_time = None
        self.session_initial_gold = 0
        self.current_session_gold = 0
        
        # Window Handles (Singleton)
        self.chart_window = None
        self.calendar_window = None
        self.chart_offset = 0 # Offset de dias para la grafica
        
        # Refresh functions for real-time updates
        self.refresh_chart_func = None
        self.refresh_calendar_func = None
        
        # Click Visualization
        self.active_clicks = [] # Stores (x, y, timestamp)

    def _schedule_device_status_update(self):
        """Actualiza estado de batería, WiFi y brillo cada 30s."""
        try:
            # Batería
            level = self.adb_preview.get_battery_level()
            if level is not None:
                # 5 Niveles de Color para Batería
                if level < 20: color = "#FC8181"   # Red (Critical)
                elif level < 40: color = "#DD6B20" # Orange (Low)
                elif level < 60: color = "#F6E05E" # Yellow (Mid)
                elif level < 80: color = "#68D391" # Light Green (Good)
                else: color = "#38A169"            # Green (Full)
                
                self.lbl_battery.config(text=f"{level}%", fg=color)
            
            # WiFi
            wifi_status = self.adb_preview.is_wifi_enabled()
            if wifi_status is True:
                self.lbl_wifi.config(text="ON", fg="#68D391")  # Green
            elif wifi_status is False:
                self.lbl_wifi.config(text="OFF", fg="#FC8181")  # Red
            else:
                self.lbl_wifi.config(text="--", fg="#A0AEC0")
            
            # Brillo
            brightness = self.adb_preview.get_brightness()
            if brightness is not None:
                # Convertir 0-255 a porcentaje
                pct = int((brightness / 255) * 100)
                if pct < 10: color = "#68D391"   # Green (Low = good for battery)
                elif pct < 50: color = "#F6E05E" # Yellow
                else: color = "#FC8181"          # Red (High = draining battery)
                
                self.lbl_brightness.config(text=f"{pct}%", fg=color)
        except:
            pass
        self.root.after(30000, self._schedule_device_status_update)

    def _update_shift_indicator(self):
        """Actualiza el indicador de turno DAY/NIGHT cada 60s."""
        try:
            hour = datetime.now().hour
            for shift in SHIFTS:
                start = shift["start"]
                end = shift["end"]
                
                if end == 0:
                    if hour >= start:
                        shift_name = shift["name"]
                        home_name = shift["home"]["name"]
                        break
                else:
                    if start <= hour < end:
                        shift_name = shift["name"]
                        home_name = shift["home"]["name"]
                        break
            else:
                shift_name = "?"
                home_name = "?"
            
            # Color según turno
            if shift_name == "NIGHT":
                color = "#9F7AEA"  # Purple for night
                icon = "🌙"
            else:
                color = "#F6E05E"  # Yellow for day
                icon = "☀️"
            
            self.lbl_shift.config(text=f"{icon} {shift_name} ({home_name})", fg=color)
        except:
            pass
        self.root.after(60000, self._update_shift_indicator)

    def _apply_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Paleta "Night Blue"
        BG_MAIN = "#102A43"   # Deep Navy
        BG_PANEL = "#1E3246"  # Sidebar / Panel
        BG_CARD = "#243B53"   # Cards
        FG_TEXT = "#D9E2EC"   # Text
        ACCENT = "#334E68"
        BTN_BG = "#2B6CB0"    # Vivid Blue
        BTN_FG = "#FFFFFF"
        BTN_ACTIVE = "#3182CE"

        style.configure(".", background=BG_MAIN, foreground=FG_TEXT, font=("Segoe UI", 10))
        
        # Custom Frames
        style.configure("Main.TFrame", background=BG_MAIN)
        style.configure("Panel.TFrame", background=BG_PANEL)
        
        # Cards
        style.configure("Card.TLabelframe", background=BG_CARD, bordercolor=BG_MAIN, relief="flat")
        style.configure("Card.TLabelframe.Label", background=BG_CARD, foreground="#829AB1", font=("Segoe UI", 9, "bold"))
        
        # Labels
        style.configure("TLabel", background=BG_MAIN, foreground=FG_TEXT)
        style.configure("Panel.TLabel", background=BG_PANEL, foreground=FG_TEXT)
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#627D98", background=BG_PANEL)
        
        style.configure("Stat.TLabel", background=BG_PANEL, foreground="#829AB1", font=("Segoe UI", 8)) 
        style.configure("StatValue.TLabel", background=BG_PANEL, font=("Segoe UI", 14, "bold")) 
        style.configure("Status.TLabel", background=BG_PANEL, foreground="#48BB78", font=("Segoe UI", 11, "bold"))

        # Buttons
        style.configure("Action.TButton", padding=10, relief="flat", background=BTN_BG, foreground=BTN_FG, borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("Action.TButton", background=[('active', BTN_ACTIVE)])
        
        style.configure("Small.TButton", padding=5, relief="flat", background=ACCENT, foreground=FG_TEXT, borderwidth=0, font=("Segoe UI", 8))

        # Combobox (para selector de idioma)
        style.configure("TCombobox",
                        fieldbackground=BG_CARD,
                        background=ACCENT,
                        foreground=FG_TEXT,
                        arrowcolor=FG_TEXT,
                        bordercolor=ACCENT,
                        lightcolor=BG_CARD,
                        darkcolor=BG_CARD,
                        insertcolor=FG_TEXT)
        style.map("TCombobox",
                  fieldbackground=[('readonly', BG_CARD)],
                  foreground=[('readonly', FG_TEXT)],
                  background=[('readonly', ACCENT)])

    def _setup_ui(self):
        # Master Container 3 Columnas
        main_container = ttk.Frame(self.root, style="Main.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # =========================================================================
        # COLUMNA 1: IZQUIERDA (CONTROL) (20%)
        # =========================================================================
        left_panel = ttk.Frame(main_container, style="Panel.TFrame", padding=15)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0,1))
        
        # LOGO / HEADER
        header_frame = tk.Frame(left_panel, bg="#1E3246") # Match Panel BG
        header_frame.pack(anchor=tk.W, pady=(0, 15))
        
        if self.logo_photo:
            tk.Label(header_frame, image=self.logo_photo, bg="#1E3246").pack(side=tk.LEFT, padx=(0, 10))
            
        self.lbl_header = ttk.Label(header_frame, text=t("header_title"), style="Header.TLabel", justify=tk.LEFT)
        self.lbl_header.pack(side=tk.LEFT)
        
        # DEVICE STATUS ROW (Battery, WiFi, Brightness)
        self.status_row = tk.Frame(left_panel, bg="#1E3246")
        self.status_row.pack(anchor=tk.W, pady=(0, 15))
        
        # Battery
        self.lbl_battery_label = tk.Label(self.status_row, text=t("battery_label"), fg="#829AB1", bg="#1E3246", font=("Segoe UI", 9))
        self.lbl_battery_label.pack(side=tk.LEFT)
        self.lbl_battery = tk.Label(self.status_row, text="--%", fg="#A0AEC0", bg="#1E3246", font=("Segoe UI", 9, "bold"))
        self.lbl_battery.pack(side=tk.LEFT)
        
        # Separator
        tk.Label(self.status_row, text="  │  ", fg="#4A5568", bg="#1E3246", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        
        # WiFi
        self.lbl_wifi_label = tk.Label(self.status_row, text=t("wifi_label"), fg="#829AB1", bg="#1E3246", font=("Segoe UI", 9))
        self.lbl_wifi_label.pack(side=tk.LEFT)
        self.lbl_wifi = tk.Label(self.status_row, text="--", fg="#A0AEC0", bg="#1E3246", font=("Segoe UI", 9, "bold"))
        self.lbl_wifi.pack(side=tk.LEFT)
        
        # Separator
        tk.Label(self.status_row, text="  │  ", fg="#4A5568", bg="#1E3246", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        
        # Brightness
        self.lbl_brightness_label = tk.Label(self.status_row, text=t("brightness_label"), fg="#829AB1", bg="#1E3246", font=("Segoe UI", 9))
        self.lbl_brightness_label.pack(side=tk.LEFT)
        self.lbl_brightness = tk.Label(self.status_row, text="--", fg="#A0AEC0", bg="#1E3246", font=("Segoe UI", 9, "bold"))
        self.lbl_brightness.pack(side=tk.LEFT)
        
        self._schedule_device_status_update()
        
        # SHIFT INDICATOR ROW (debajo de batería/wifi/brillo)
        self.shift_row = tk.Frame(left_panel, bg="#1E3246")
        self.shift_row.pack(anchor=tk.W, pady=(0, 15))
        
        self.lbl_shift_label = tk.Label(self.shift_row, text="Turno: ", fg="#829AB1", bg="#1E3246", font=("Segoe UI", 9))
        self.lbl_shift_label.pack(side=tk.LEFT)
        self.lbl_shift = tk.Label(self.shift_row, text="--", fg="#A0AEC0", bg="#1E3246", font=("Segoe UI", 9, "bold"))
        self.lbl_shift.pack(side=tk.LEFT)
        self._update_shift_indicator()

        # LANGUAGE SELECTOR
        self.lang_frame = tk.Frame(left_panel, bg="#1E3246")
        self.lang_frame.pack(anchor=tk.W, pady=(0, 25))
        self.lbl_lang_section = tk.Label(self.lang_frame, text=t("language_section"), fg="#829AB1", bg="#1E3246", font=("Segoe UI", 8))
        self.lbl_lang_section.pack(anchor=tk.W)
        
        # Crear lista de idiomas para el combobox
        lang_names = [get_language_name(code) for code in get_supported_languages()]
        self.lang_combo = ttk.Combobox(self.lang_frame, values=lang_names, state="readonly", width=12)
        
        # Seleccionar idioma actual
        current_lang = get_current_language()
        current_idx = get_supported_languages().index(current_lang) if current_lang in get_supported_languages() else 0
        self.lang_combo.current(current_idx)
        self.lang_combo.pack(anchor=tk.W, pady=(5, 0))
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_language_change)

        # CONTROL PRINCIPAL
        self.lbl_control_section = ttk.Label(left_panel, text=t("control_section"), style="Stat.TLabel")
        self.lbl_control_section.pack(anchor=tk.W, pady=(0,5))
        
        self.btn_start = ttk.Button(left_panel, text=t("btn_start"), command=self.start_bot, style="Action.TButton")
        self.btn_start.pack(fill=tk.X, pady=(0, 8))
        
        self.btn_stop = ttk.Button(left_panel, text=t("btn_stop"), command=self.stop_bot, state=tk.DISABLED, style="Action.TButton")
        self.btn_stop.pack(fill=tk.X, pady=(0, 20))
        
        # STATUS INDICATOR
        self.status_frame = tk.Frame(left_panel, bg="#1E3246")
        self.status_frame.pack(fill=tk.X, pady=(0, 20))
        self.lbl_status_section = tk.Label(self.status_frame, text=t("status_section"), fg="#829AB1", bg="#1E3246", font=("Segoe UI", 8))
        self.lbl_status_section.pack(anchor=tk.W)
        
        self.lbl_status = tk.Label(self.status_frame, text=t("status_inactive"), fg="#A0AEC0", bg="#1E3246", font=("Segoe UI", 12, "bold"))
        self.lbl_status.pack(anchor=tk.W)

        # CAPTURE BUTTON
        self.btn_capture = ttk.Button(left_panel, text=t("btn_capture"), command=self._capture_screen, style="Action.TButton")
        self.btn_capture.pack(fill=tk.X, pady=(0, 20))

        # =========================================================================
        # COLUMNA 2: CENTRO (VISION + LOGS) (55%)
        # =========================================================================
        center_panel = ttk.Frame(main_container, style="Main.TFrame", padding=15)
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # LOGS HEADER
        log_header = tk.Frame(center_panel, bg="#102A43")
        log_header.pack(fill=tk.X, pady=(0, 5))
        self.lbl_log_header = tk.Label(log_header, text=t("log_header"), fg="#627D98", bg="#102A43", font=("Consolas", 10, "bold"))
        self.lbl_log_header.pack(side=tk.LEFT)
        
        # LOG AREA (Arriba)
        self.log_area = scrolledtext.ScrolledText(center_panel, height=12, state=tk.DISABLED, 
                                                  font=("Consolas", 10), 
                                                  bg="#0F2439", fg="#D9E2EC", 
                                                  relief="flat", padx=10, pady=10,
                                                  insertbackground="white")
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        self._configure_log_tags()

        # LIVE VIEW HEADER
        view_header = tk.Frame(center_panel, bg="#102A43")
        view_header.pack(fill=tk.X, pady=(0, 5))
        self.lbl_preview_header = tk.Label(view_header, text=t("preview_header"), fg="#627D98", bg="#102A43", font=("Consolas", 10, "bold"))
        self.lbl_preview_header.pack(side=tk.LEFT)
        
        # PREVIEW CONTAINER (Abajo)
        # Ratio 16:9 for 640px width -> 360px height
        self.preview_frame = tk.Frame(center_panel, bg="#000000", width=640, height=360)
        self.preview_frame.pack(anchor=tk.CENTER)
        self.preview_frame.pack_propagate(False) # Force size
        
        self.canvas = tk.Canvas(self.preview_frame, width=640, height=360, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # =========================================================================
        # COLUMNA 3: DERECHA (METRICAS) (25%)
        # =========================================================================
        right_panel = ttk.Frame(main_container, style="Panel.TFrame", padding=15)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(1,0))
        
        self.lbl_stats_section = ttk.Label(right_panel, text=t("stats_section"), style="Stat.TLabel")
        self.lbl_stats_section.pack(anchor=tk.W, pady=(0,15))
        
        # SESSION TIMER
        self.lbl_runtime = self._create_stat_block(right_panel, t("stat_session_time"), "00:00:00", "#63B3ED", "stat_session_time")
        
        # GOLD SESSION
        self.lbl_gold = self._create_stat_block(right_panel, t("stat_session_gold"), "0", "#F6E05E", "stat_session_gold")
        
        # GOLD RATE
        self.lbl_gold_speed = self._create_stat_block(right_panel, t("stat_gold_rate"), "0", "#F6E05E", "stat_gold_rate")
        
        # ADS RATE
        self.lbl_speed = self._create_stat_block(right_panel, t("stat_ads_rate"), "0.0", "#63B3ED", "stat_ads_rate")
        
        # TOTAL HISTORY
        self.lbl_gold_history = self._create_stat_block(right_panel, t("stat_total_history"), "--", "#CBD5E0", "stat_total_history")
        
        # GRAPHS & CALENDAR
        btn_frame = tk.Frame(right_panel, bg="#1E3246")
        btn_frame.pack(fill=tk.X, pady=20)
        
        self.btn_chart = tk.Button(btn_frame, text=t("btn_chart"), bg="#2D3748", fg="white", bd=0, pady=5, command=self._show_history_chart)
        self.btn_chart.pack(fill=tk.X, pady=2)
        self.btn_calendar = tk.Button(btn_frame, text=t("btn_calendar"), bg="#2D3748", fg="white", bd=0, pady=5, command=self._show_calendar_view)
        self.btn_calendar.pack(fill=tk.X, pady=2)

    def _create_stat_block(self, parent, label, initial, color, translation_key=None):
        frame = tk.Frame(parent, bg="#1E3246")
        frame.pack(fill=tk.X, pady=(0, 15))
        title_lbl = tk.Label(frame, text=label, fg="#829AB1", bg="#1E3246", font=("Segoe UI", 9))
        title_lbl.pack(anchor=tk.W)
        lbl = tk.Label(frame, text=initial, fg=color, bg="#1E3246", font=("Segoe UI", 20, "bold"))
        lbl.pack(anchor=tk.W)
        # Store reference for translation updates
        if translation_key:
            self.stat_title_labels[translation_key] = title_lbl
        return lbl

    def _create_metric_row(self, parent, label, initial, color):
        frame = tk.Frame(parent, bg="#1E3246")
        frame.pack(fill=tk.X, pady=2)
        tk.Label(frame, text=label, fg="#829AB1", bg="#1E3246", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        lbl = tk.Label(frame, text=initial, fg=color, bg="#1E3246", font=("Segoe UI", 9, "bold"))
        lbl.pack(side=tk.RIGHT)
        return lbl

    def _configure_log_tags(self):
        self.log_area.tag_config("gold", foreground="#F6E05E")     # Yellow
        self.log_area.tag_config("error", foreground="#FC8181")    # Red
        self.log_area.tag_config("state", foreground="#63B3ED")    # Blue
        self.log_area.tag_config("success", foreground="#68D391")  # Green
        self.log_area.tag_config("highlight", foreground="#D9E2EC", font=("Consolas", 10, "bold"))


    def log_message(self, msg):
        self.log_queue.put(msg)

    def update_image(self, cv2_image):
        if cv2_image is not None:
            self.image_queue.put(cv2_image)
            
    def update_stats(self, todays_total_gold, total_history=0, ads_per_hour=0, gold_per_hour=0):
        # Programar actualización en el hilo principal
        def _update():
            # Calcular oro de sesión real (Total Hoy - Inicial al empezar sesión)
            # Si no estamos corriendo, mostramos 0 o el último valor
            session_val = 0
            if self.is_bot_running and self.session_initial_gold >= 0:
                session_val = max(0, todays_total_gold - self.session_initial_gold)
            
            self.current_session_gold = session_val # Guardar para logging

            # Use formatting with separators for thousands
            self.lbl_gold.config(text=f"{session_val:,}")
            self.lbl_gold_history.config(text=f"{total_history:,}")
            self.lbl_speed.config(text=f"{ads_per_hour:.1f} /h")
            self.lbl_gold_speed.config(text=f"{int(gold_per_hour):,} /h")
            
            # Auto-refresh graph and calendar if open
            if self.refresh_chart_func:
                try:
                    self.refresh_chart_func()
                except:
                    pass
            if self.refresh_calendar_func:
                try:
                    self.refresh_calendar_func()
                except:
                    pass
        self.root.after(0, _update)

    def _start_queue_processing(self):
        self._process_logs()
        self._process_images()
        
    def _process_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_area.config(state=tk.NORMAL)
            
            # Map icons to tags
            icon_map = {
                "💰": "gold", "🤑": "gold",
                "⚠": "error", "❌": "error", "Error": "error",
                "🔄": "state", 
                "✅": "success", "Listo": "success",
                "👀": "state", "👉": "state", "🔍": "state", "⌨": "state", "🖱": "state"
            }
            
            found_icon = None
            tag_to_use = None
            
            # Find first matching icon
            for icon, tag in icon_map.items():
                if icon in msg:
                    found_icon = icon
                    tag_to_use = tag
                    break
            
            if found_icon:
                parts = msg.split(found_icon, 1)
                self.log_area.insert(tk.END, parts[0]) # Timestamp / Prefix
                self.log_area.insert(tk.END, found_icon, tag_to_use) # Colored Icon
                self.log_area.insert(tk.END, parts[1] + "\n") # Rest of text
            else:
                self.log_area.insert(tk.END, msg + "\n")

            self.log_area.see(tk.END)
            self.log_area.config(state=tk.DISABLED)
            
            # Actualizar status label si el mensaje parece un estado
            if "Estado:" in msg or "CAMBIO ESTADO:" in msg:
                clean_msg = ""
                # Caso 1: Cambio de estado explícito
                if "CAMBIO ESTADO" in msg:
                     # Parsear "CAMBIO ESTADO: X -> Y" => Mostrar "Y"
                     parts = msg.split("->")
                     if len(parts) > 1:
                         new_state = parts[-1].strip()
                         clean_msg = new_state
                # Caso 2: Mensaje de "Estado:" (log directo)
                elif "Estado:" in msg:
                    # Limpiar timestamp y prefijo
                    clean_msg = msg.split("]")[-1].strip()
                    if "Estado:" in clean_msg:
                        clean_msg = clean_msg.split("Estado:")[-1].strip()
                    # Quitar el bullet si lo hubiera
                    clean_msg = clean_msg.replace("•", "").strip()
                
                if clean_msg:
                    self.lbl_status.config(text=clean_msg)

        self.root.after(100, self._process_logs)

    def _process_images(self):
        try:
            # 1. Update Image State if new frame available
            latest_image = None
            while not self.image_queue.empty():
                latest_image = self.image_queue.get_nowait()
            
            if latest_image is not None:
                # Convertir CV2 (BGR) a PIL (RGB)
                rgb_image = cv2.cvtColor(latest_image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_image)
                
                # Resize manteniendo aspect ratio
                target_w, target_h = 640, 360
                ratio = min(target_w / pil_image.width, target_h / pil_image.height)
                new_w = int(pil_image.width * ratio)
                new_h = int(pil_image.height * ratio)
                
                pil_image = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # Store State
                self.current_pil_image = pil_image
                self.current_photo = ImageTk.PhotoImage(pil_image)
                self.current_ratio = ratio
                self.current_x_offset = (target_w - new_w) // 2
                self.current_y_offset = (target_h - new_h) // 2
                
                # Update BG Image Item
                if self.bg_image_id:
                     self.canvas.itemconfig(self.bg_image_id, image=self.current_photo)
                     self.canvas.coords(self.bg_image_id, self.current_x_offset, self.current_y_offset)
                else:
                     self.bg_image_id = self.canvas.create_image(self.current_x_offset, self.current_y_offset, image=self.current_photo, anchor=tk.NW, tags="bg")
                     self.canvas.tag_lower("bg") # Ensure background is always at bottom

            # 2. Update Overlays (Animation Loop)
            if self.current_photo:
                # Clear ONLY overlays
                self.canvas.delete("overlay")
                
                # Draw Active Clicks
                current_time = time.time()
                self.active_clicks = [c for c in self.active_clicks if current_time - c[2] < 1.0]
                
                for (cx, cy, ts) in self.active_clicks:
                    draw_x = self.current_x_offset + (cx * self.current_ratio)
                    draw_y = self.current_y_offset + (cy * self.current_ratio)
                    
                    elapsed = current_time - ts
                    radius_anim = 10 + (elapsed * 20)
                    
                    # Canvas Tags="overlay"
                    self.canvas.create_oval(draw_x-radius_anim, draw_y-radius_anim, draw_x+radius_anim, draw_y+radius_anim, outline="#F56565", width=3, tags="overlay")

        except Exception as e:
            pass
            
        self.root.after(100, self._process_images) # Optimizado a 100ms (10FPS)

    def _run_idle_preview(self):
        """Toma capturas periodicas cuando el bot no está corriendo."""
        while True:
            if not self.is_bot_running:
                try:
                    # Usamos take_screenshot del wrapper (fix SD card ya implementado alli)
                    # Hemos añadido timeout en adb_wrapper para que esto no bloquee
                    img = self.adb_preview.take_screenshot()
                    if img is not None:
                        self.update_image(img)
                except Exception as e:
                    print(f"Error preview idle: {e}")
                    time.sleep(2) # Espera extra si falla
                
                time.sleep(1.5) # 1.5s refresh rate pare idle
            else:
                time.sleep(1) # Dormir mientras el bot corre (él manda las imagenes)

    def visualize_click(self, x, y):
        """Callback para registrar clicks del bot."""
        self.active_clicks.append((x, y, time.time()))

    def _on_language_change(self, event=None):
        """Callback cuando el usuario cambia el idioma en el combobox."""
        selected_idx = self.lang_combo.current()
        lang_codes = get_supported_languages()
        if 0 <= selected_idx < len(lang_codes):
            new_lang = lang_codes[selected_idx]
            if set_language(new_lang):
                self._refresh_all_texts()

    def _refresh_all_texts(self):
        """Actualiza todos los textos de la GUI con el idioma actual."""
        # Título de la ventana
        self.root.title(t("app_title"))
        
        # Panel izquierdo
        self.lbl_header.config(text=t("header_title"))
        self.lbl_battery_label.config(text=t("battery_label"))
        self.lbl_wifi_label.config(text=t("wifi_label"))
        self.lbl_brightness_label.config(text=t("brightness_label"))
        self.lbl_lang_section.config(text=t("language_section"))
        self.lbl_control_section.config(text=t("control_section"))
        self.btn_start.config(text=t("btn_start"))
        self.btn_stop.config(text=t("btn_stop"))
        self.lbl_status_section.config(text=t("status_section"))
        self.btn_capture.config(text=t("btn_capture"))
        
        # Si el status actual no es un estado del bot, actualizarlo
        current_status = self.lbl_status.cget("text")
        if current_status in ["INACTIVO", "INACTIVE", "INACTIF", "INAKTIV", "INATTIVO"]:
            self.lbl_status.config(text=t("status_inactive"))
        elif current_status in ["Detenido", "Stopped", "Arrêté", "Gestoppt", "Fermato"]:
            self.lbl_status.config(text=t("status_stopped"))
        
        # Panel central
        self.lbl_log_header.config(text=t("log_header"))
        self.lbl_preview_header.config(text=t("preview_header"))
        
        # Panel derecho
        self.lbl_stats_section.config(text=t("stats_section"))
        self.btn_chart.config(text=t("btn_chart"))
        self.btn_calendar.config(text=t("btn_calendar"))
        
        # Actualizar labels de título de stats
        for key, label in self.stat_title_labels.items():
            label.config(text=t(key))

    def start_bot(self):
        if self.bot_thread and self.bot_thread.is_alive():
            return
        
        self.is_bot_running = True
        self.stop_event.clear()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.lbl_status.config(text=t("status_starting"), foreground="#63B3ED")
        
        self.bot_thread = threading.Thread(target=self._run_bot_thread, daemon=True)
        self.bot_thread.start()
        
        # Start Session Tracking
        self.session_start_time = datetime.now()
        self.session_initial_gold = self.logger.get_todays_gold() # Snapshot inicio
        self.current_session_gold = 0
        self._update_runtime_timer()

    def _update_runtime_timer(self):
        if self.is_bot_running and self.session_start_time:
            delta = datetime.now() - self.session_start_time
            # Format HH:MM:SS
            total_seconds = int(delta.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            self.lbl_runtime.config(text=time_str)
            
            self.root.after(1000, self._update_runtime_timer)

    def stop_bot(self):
        if self.bot_thread and self.bot_thread.is_alive():
            self.log_message(t("msg_stopping_bot"))
            self.stop_event.set()
            self.lbl_status.config(text=t("status_stopping"), foreground="#FC8181")
            self.btn_stop.config(state=tk.DISABLED)
            # El botón de iniciar se reactivará cuando muera el hilo

    def _run_bot_thread(self):
        try:
            if not RealRacingBot:
                self.log_message(t("msg_bot_class_not_found"))
                return

            self.bot_instance = RealRacingBot(
                stop_event=self.stop_event,
                log_callback=self.log_message,
                image_callback=self.update_image,
                stats_callback=self.update_stats,
                click_callback=self.visualize_click
            )
            self.bot_instance.run()
        except Exception as e:
            self.log_message(t("msg_bot_error", error=str(e)))
        finally:
            # Log Session End
            if self.session_start_time:
                end_time = datetime.now()
                # Log to DB
                self.logger.log_session(self.session_start_time, end_time, self.current_session_gold)
                self.session_start_time = None # Stop timer loop logic check

            self.log_message(t("msg_bot_stopped"))
            self.root.after(0, self._reset_buttons)

    def _capture_screen(self):
        """Captura la pantalla y la guarda en disco."""
        import os
        from datetime import datetime
        
        # Crear directorio si no existe
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshots/capture_{timestamp}.png"
        
        def save_task():
            try:
                # Prioridad: Bot Instance (si corre), sino ADB Preview
                img = None
                if self.is_bot_running and self.bot_instance:
                    img = self.bot_instance.adb.take_screenshot()
                else:
                    img = self.adb_preview.take_screenshot()
                
                if img is not None:
                    # Save using OpenCV
                    cv2.imwrite(filename, img)
                    self.log_message(t("msg_capture_saved", filename=filename))
                else:
                    self.log_message(t("msg_capture_error"))
            except Exception as e:
                self.log_message(t("msg_capture_failed", error=str(e)))
        
        # Ejecutar en hilo para no bloquear GUI
        threading.Thread(target=save_task, daemon=True).start()

    def _show_history_chart(self):
        """Muestra popup con gráfica de barras navegable."""
        if self.chart_window is not None and self.chart_window.winfo_exists():
            self.chart_window.destroy()
            self.chart_window = None
            self.refresh_chart_func = None
            return

        self.chart_offset = 0 # Reset al abrir

        popup = tk.Toplevel(self.root)
        self.chart_window = popup
        popup.title(t("chart_title"))
        popup.geometry("600x450")
        popup.configure(bg="#102A43")
        
        # Cleanup on close
        def on_close():
            self.refresh_chart_func = None
            self.chart_window = None
            popup.destroy()
        popup.protocol("WM_DELETE_WINDOW", on_close)
        
        # Header Navegable
        header = tk.Frame(popup, bg="#102A43")
        header.pack(fill=tk.X, padx=20, pady=10)
        
        btn_prev = tk.Button(header, text="◀", font=("Segoe UI", 12), 
                            bg="#102A43", fg="#4FD1C5", bd=0, cursor="hand2",
                            command=lambda: navigate(7)) # Mas antiguo (+offset)
        btn_prev.pack(side=tk.LEFT)
        
        lbl_range = tk.Label(header, text=t("chart_last_days"), font=("Segoe UI", 16, "bold"), 
                            bg="#102A43", fg="#D9E2EC")
        lbl_range.pack(side=tk.LEFT, expand=True)
        
        btn_next = tk.Button(header, text="▶", font=("Segoe UI", 12), 
                            bg="#102A43", fg="#4FD1C5", bd=0, cursor="hand2",
                            command=lambda: navigate(-7)) # Mas reciente (-offset)
        btn_next.pack(side=tk.RIGHT)
        
        # Canvas
        cw, ch = 550, 320
        canvas = tk.Canvas(popup, width=cw, height=ch, bg="#1E3246", highlightthickness=0)
        canvas.pack(pady=10, padx=20)
        
        def navigate(delta):
            self.chart_offset += delta
            if self.chart_offset < 0: self.chart_offset = 0
            refresh_chart()

        def refresh_chart():
            try:
                if not popup.winfo_exists(): return
            except: return
                
            canvas.delete("all")
            
            # Obtener datos
            import sqlite3
            db_path = self.logger.db_path
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Calcular rango de fechas
            end_date = datetime.now().date() - timedelta(days=self.chart_offset)
            start_date = end_date - timedelta(days=6)
            
            # Query
            cursor.execute("""
                SELECT date(timestamp), SUM(amount) 
                FROM gold_history 
                WHERE date(timestamp) BETWEEN ? AND ?
                GROUP BY date(timestamp)
                ORDER BY date(timestamp)
            """, (start_date.isoformat(), end_date.isoformat()))
            
            raw_data = cursor.fetchall()
            conn.close()
            
            # Create dict for easy lookup
            data_dict = {row[0]: row[1] for row in raw_data}
            
            # Generate all 7 days
            days = []
            values = []
            for i in range(7):
                d = start_date + timedelta(days=i)
                day_str = d.isoformat()
                days.append(d.strftime("%d/%m"))
                values.append(data_dict.get(day_str, 0))
            
            if not values or max(values) == 0:
                canvas.create_text(cw//2, ch//2, text=t("chart_no_data"), fill="#829AB1", font=("Segoe UI", 12))
                return
            
            # Draw
            max_val = max(values) if max(values) > 0 else 1
            bar_w = 50
            gap = (cw - (bar_w * 7)) / 8
            
            for i, (day, val) in enumerate(zip(days, values)):
                x = gap + i * (bar_w + gap)
                h = (val / max_val) * (ch - 80) if max_val > 0 else 0
                y = ch - 40 - h
                
                # Gradient Color
                if val > 0:
                    canvas.create_rectangle(x, y, x+bar_w, ch-40, fill="#4FD1C5", outline="")
                    canvas.create_text(x + bar_w//2, y-10, text=f"{int(val):,}", fill="#F6E05E", font=("Segoe UI", 9, "bold"))
                
                # Day Label
                canvas.create_text(x + bar_w//2, ch-25, text=day, fill="#829AB1", font=("Segoe UI", 9))
        
        refresh_chart()
        self.refresh_chart_func = refresh_chart  # Store for external refresh

    def _show_calendar_view(self):
        """Muestra popup con calendario de actividad."""
        if self.calendar_window is not None and self.calendar_window.winfo_exists():
            self.calendar_window.destroy()
            self.calendar_window = None
            self.refresh_calendar_func = None
            return
            
        popup = tk.Toplevel(self.root)
        self.calendar_window = popup
        popup.title(t("calendar_title"))
        popup.geometry("550x480")
        popup.configure(bg="#102A43")
        
        # Cleanup on close
        def on_close():
            self.refresh_calendar_func = None
            self.calendar_window = None
            popup.destroy()
        popup.protocol("WM_DELETE_WINDOW", on_close)
        
        # State
        today = datetime.now()
        current_date = [today.year, today.month]
        
        # Header
        header = tk.Frame(popup, bg="#102A43")
        header.pack(fill=tk.X, padx=20, pady=10)
        
        btn_prev = tk.Button(header, text="◀", font=("Segoe UI", 12), 
                            bg="#102A43", fg="#4FD1C5", bd=0, cursor="hand2",
                            command=lambda: navigate(-1))
        btn_prev.pack(side=tk.LEFT)
        
        lbl_month = tk.Label(header, text="", font=("Segoe UI", 16, "bold"), 
                            bg="#102A43", fg="#D9E2EC")
        lbl_month.pack(side=tk.LEFT, expand=True)
        
        btn_next = tk.Button(header, text="▶", font=("Segoe UI", 12), 
                            bg="#102A43", fg="#4FD1C5", bd=0, cursor="hand2",
                            command=lambda: navigate(1))
        btn_next.pack(side=tk.RIGHT)
        
        # Calendar Grid Frame
        grid_frame = tk.Frame(popup, bg="#102A43")
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # Legend
        legend = tk.Frame(popup, bg="#102A43")
        legend.pack(fill=tk.X, padx=20, pady=10)
        tk.Label(legend, text="■", fg="#1E3246", bg="#102A43", font=("Segoe UI", 10)).pack(side=tk.LEFT)
        tk.Label(legend, text=t("calendar_no_activity"), fg="#829AB1", bg="#102A43", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(2, 10))
        tk.Label(legend, text="■", fg="#38A169", bg="#102A43", font=("Segoe UI", 10)).pack(side=tk.LEFT)
        tk.Label(legend, text=t("calendar_with_activity"), fg="#829AB1", bg="#102A43", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(2, 0))
        
        def refresh_calendar():
            import calendar
            # Clear Grid
            for w in grid_frame.winfo_children():
                w.destroy()
            
            year, month = current_date
            lbl_month.config(text=f"{calendar.month_name[month]} {year}")
            
            # Configure uniform column widths
            for i in range(7):
                grid_frame.columnconfigure(i, weight=1, uniform="cal_col", minsize=66)
            
            # Weekday Headers - adjusted to match cell width
            days_header = ["L", "M", "X", "J", "V", "S", "D"]
            for i, d in enumerate(days_header):
                lbl = tk.Label(grid_frame, text=d, fg="#627D98", bg="#102A43", font=("Segoe UI", 10, "bold"))
                lbl.grid(row=0, column=i, pady=5, sticky="nsew")
            
            # Get month data
            import sqlite3
            db_path = self.logger.db_path
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get days with activity
            cursor.execute("""
                SELECT date(timestamp), SUM(amount) 
                FROM gold_history 
                WHERE strftime('%Y', timestamp) = ? AND strftime('%m', timestamp) = ?
                GROUP BY date(timestamp)
            """, (str(year), f"{month:02d}"))
            
            activity = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            
            # Calendar
            cal = calendar.monthcalendar(year, month)
            for row_idx, week in enumerate(cal):
                for col_idx, day in enumerate(week):
                    # Empty cell for days outside month
                    if day == 0:
                        empty_cell = tk.Frame(grid_frame, bg="#102A43", height=55)
                        empty_cell.grid(row=row_idx+1, column=col_idx, padx=3, pady=3, sticky="nsew")
                    else:
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        has_gold = date_str in activity
                        gold_amount = activity.get(date_str, 0)
                        
                        # Colors - gradient effect for days with gold
                        if has_gold:
                            bg = "#2F855A"  # Slightly darker green
                            border_color = "#48BB78"  # Lighter green border effect
                            fg = "#FFFFFF"
                        else:
                            bg = "#1E3246"
                            border_color = "#243B53"
                            fg = "#829AB1"
                        
                        # Outer frame (border effect) - use sticky for uniform width
                        outer = tk.Frame(grid_frame, bg=border_color, height=55)
                        outer.grid(row=row_idx+1, column=col_idx, padx=3, pady=3, sticky="nsew")
                        
                        # Inner cell with padding to create border effect
                        cell = tk.Frame(outer, bg=bg)
                        cell.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
                        
                        # Day number (top) - larger, centered
                        tk.Label(cell, text=str(day), bg=bg, fg=fg, 
                                font=("Segoe UI", 12, "bold")).pack(pady=(8, 2))
                        
                        # Gold amount (bottom) - show if has gold
                        if has_gold:
                            # Format: 1.5K for 1500, 12K for 12000, etc.
                            if gold_amount >= 1000:
                                gold_text = f"{gold_amount/1000:.1f}K"
                            else:
                                gold_text = str(int(gold_amount))
                            tk.Label(cell, text=gold_text, bg=bg, fg="#F6E05E", 
                                    font=("Segoe UI", 9, "bold")).pack()
        
        def navigate(delta):
            current_date[1] += delta
            if current_date[1] > 12:
                current_date[1] = 1
                current_date[0] += 1
            elif current_date[1] < 1:
                current_date[1] = 12
                current_date[0] -= 1
            refresh_calendar()
        
        refresh_calendar()
        self.refresh_calendar_func = refresh_calendar  # Store for external refresh

    def _reset_buttons(self):
        self.is_bot_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.lbl_status.config(text=t("status_stopped"), foreground="#A0AEC0")

def main():
    root = tk.Tk()
    app = BotGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
