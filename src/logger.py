import sqlite3
import datetime
import os
import shutil

class GoldLogger:
    def __init__(self, db_path="gold_log.db", legacy_txt_path="gold_diary.txt"):
        self.db_path = db_path
        self._init_db()
        self._migrate_legacy_txt(legacy_txt_path)

    def _init_db(self):
        """Inicializa la base de datos si no existe."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gold_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    amount INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    duration TEXT,
                    gold_earned INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ocr_memory (
                    key TEXT PRIMARY KEY,
                    text TEXT,
                    x INTEGER,
                    y INTEGER,
                    w INTEGER,
                    h INTEGER,
                    threshold INTEGER,
                    updated_at TEXT
                )
            """)

    def save_ocr_memory(self, key, text, x, y, w, h, threshold):
        """Guarda o actualiza una detección OCR exitosa en memoria."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO ocr_memory (key, text, x, y, w, h, threshold, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (key, text, x, y, w, h, threshold, now_str))
            print(f"OCR Memory saved: {key} -> ({x},{y}) @ threshold {threshold}")
        except Exception as e:
            print(f"Error saving OCR memory: {e}")

    def get_ocr_memory(self, key):
        """Recupera la última detección OCR exitosa para una clave dada.
        Retorna dict {text, x, y, w, h, threshold} o None."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT text, x, y, w, h, threshold FROM ocr_memory WHERE key = ?", (key,)
                )
                row = cursor.fetchone()
                if row:
                    return {"text": row[0], "x": row[1], "y": row[2], "w": row[3], "h": row[4], "threshold": row[5]}
        except Exception as e:
            print(f"Error fetching OCR memory: {e}")
        return None


    def _migrate_legacy_txt(self, txt_path):
        """Migra datos del fichero de texto antiguo si existe y lo mueve a zz."""
        if not os.path.exists(txt_path):
            return
            
        print(f"Migrando {txt_path} a SQLite...")
        entries = []
        try:
            with open(txt_path, "r") as f:
                for line in f:
                    if "Gold Won:" in line:
                        # Formato: YYYY-MM-DD HH:MM:SS | Gold Won: N
                        parts = line.split("| Gold Won:")
                        if len(parts) == 2:
                            ts = parts[0].strip()
                            try:
                                amt = int(parts[1].strip())
                                entries.append((ts, amt))
                            except ValueError:
                                pass
                                
            if entries:
                with sqlite3.connect(self.db_path) as conn:
                    # Usamos executemany para eficiencia
                    conn.executemany("INSERT INTO gold_history (timestamp, amount) VALUES (?, ?)", entries)
                print(f"Migradas {len(entries)} entradas correctamente.")
            
            # Mover a zz
            destination_dir = "zz"
            if not os.path.exists(destination_dir):
                os.makedirs(destination_dir)
            
            shutil.move(txt_path, os.path.join(destination_dir, txt_path))
            print(f"Archivo movido a {destination_dir}/{txt_path}")
            
        except Exception as e:
            print(f"Error en migración: {e}")

    def log_gold(self, amount):
        """Registra una ganancia de oro en la BD."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO gold_history (timestamp, amount) VALUES (?, ?)", (now_str, amount))
            print(f"Log saved DB: {amount} Gold at {now_str}")
        except Exception as e:
            print(f"Error escribiendo en DB: {e}")

    def log_session(self, start_dt, end_dt, gold_earned):
        """Registra una sesión de ejecución completa."""
        try:
            date_str = start_dt.strftime("%Y-%m-%d")
            start_str = start_dt.strftime("%H:%M:%S")
            end_str = end_dt.strftime("%H:%M:%S")
            duration_delta = end_dt - start_dt
            # Formato duración H:M:S sin microsegundos
            duration_str = str(duration_delta).split('.')[0] 
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO session_history (date, start_time, end_time, duration, gold_earned)
                    VALUES (?, ?, ?, ?, ?)
                """, (date_str, start_str, end_str, duration_str, gold_earned))
            print(f"Session Logged: {duration_str} - Gold: {gold_earned}")
        except Exception as e:
            print(f"Error logueando sesion: {e}")

    def get_todays_gold(self):
        """Suma el oro ganado hoy (YYYY-MM-DD)."""
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT SUM(amount) FROM gold_history WHERE timestamp LIKE ?", (f"{today_str}%",))
                result = cursor.fetchone()[0]
            return result if result else 0
        except Exception:
            return 0

    def get_all_time_gold(self):
        """Suma TODO el oro histórico."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT SUM(amount) FROM gold_history")
                result = cursor.fetchone()[0]
            return result if result else 0
        except Exception:
            return 0

    def get_daily_history(self, limit=7, offset=0):
        """
        Retorna lista de tuplas (fecha, total_oro) de 'limit' dias, 
        terminando en (Hoy - offset_dias).
        INCLUYE dias vacios (sin actividad) con valor 0.
        Formato fecha: YYYY-MM-DD
        Orden: Ascendente por fecha.
        """
        try:
            today = datetime.datetime.now().date()
            end_date = today - datetime.timedelta(days=offset)
            start_date = end_date - datetime.timedelta(days=limit - 1)
            
            s_str = start_date.strftime("%Y-%m-%d")
            e_str = end_date.strftime("%Y-%m-%d")

            with sqlite3.connect(self.db_path) as conn:
                # Obtener datos existentes en el rango
                query = """
                    SELECT substr(timestamp, 1, 10) as day, SUM(amount)
                    FROM gold_history
                    WHERE day BETWEEN ? AND ?
                    GROUP BY day
                """
                cursor = conn.execute(query, (s_str, e_str))
                raw_results = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Generar todos los dias del rango
            all_days = []
            for i in range(limit - 1, -1, -1):
                day = end_date - datetime.timedelta(days=i)
                day_str = day.strftime("%Y-%m-%d")
                amount = raw_results.get(day_str, 0)
                all_days.append((day_str, amount))
            
            return all_days
        except Exception as e:
            print(f"Error fetching history: {e}")
            return []
