"""
Módulo de internacionalización (i18n) para RR3 Bot.
Gestiona la carga de traducciones y detección de idioma del sistema.
"""

import json
import os
import locale

# Directorio base donde se encuentra este módulo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LANG_DIR = os.path.join(BASE_DIR, "lang")

# Idiomas soportados
SUPPORTED_LANGUAGES = ["es", "en", "fr", "de", "it"]
DEFAULT_LANGUAGE = "es"

# Estado global del módulo
_current_language = DEFAULT_LANGUAGE
_translations = {}
_language_change_callbacks = []


def _load_language(lang_code: str) -> dict:
    """Carga un fichero de idioma JSON."""
    lang_file = os.path.join(LANG_DIR, f"{lang_code}.json")
    try:
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[i18n] Fichero de idioma no encontrado: {lang_file}")
        return {}
    except json.JSONDecodeError as e:
        print(f"[i18n] Error parseando {lang_file}: {e}")
        return {}


def _detect_system_language() -> str:
    """Detecta el idioma del sistema operativo."""
    try:
        # Obtener locale del sistema
        system_locale = locale.getdefaultlocale()[0]
        
        if system_locale:
            # Extraer código de idioma (primeros 2 caracteres)
            lang_code = system_locale[:2].lower()
            
            if lang_code in SUPPORTED_LANGUAGES:
                print(f"[i18n] Idioma del sistema detectado: {lang_code}")
                return lang_code
            else:
                print(f"[i18n] Idioma del sistema '{lang_code}' no soportado, usando '{DEFAULT_LANGUAGE}'")
    except Exception as e:
        print(f"[i18n] Error detectando idioma del sistema: {e}")
    
    return DEFAULT_LANGUAGE


def _load_saved_preference() -> str | None:
    """Carga la preferencia de idioma guardada."""
    pref_file = os.path.join(BASE_DIR, ".lang_preference")
    try:
        if os.path.exists(pref_file):
            with open(pref_file, "r") as f:
                lang = f.read().strip()
                if lang in SUPPORTED_LANGUAGES:
                    return lang
    except Exception:
        pass
    return None


def _save_preference(lang_code: str):
    """Guarda la preferencia de idioma."""
    pref_file = os.path.join(BASE_DIR, ".lang_preference")
    try:
        with open(pref_file, "w") as f:
            f.write(lang_code)
    except Exception as e:
        print(f"[i18n] Error guardando preferencia: {e}")


def init():
    """Inicializa el sistema de internacionalización."""
    global _current_language, _translations
    
    # Prioridad: 1. Preferencia guardada, 2. Idioma del sistema, 3. Por defecto
    saved_lang = _load_saved_preference()
    if saved_lang:
        _current_language = saved_lang
        print(f"[i18n] Usando idioma guardado: {_current_language}")
    else:
        _current_language = _detect_system_language()
    
    # Cargar traducciones
    _translations = _load_language(_current_language)
    
    # Si falla, cargar idioma por defecto
    if not _translations and _current_language != DEFAULT_LANGUAGE:
        print(f"[i18n] Fallback a idioma por defecto: {DEFAULT_LANGUAGE}")
        _current_language = DEFAULT_LANGUAGE
        _translations = _load_language(DEFAULT_LANGUAGE)


def get_current_language() -> str:
    """Retorna el código del idioma actual."""
    return _current_language


def get_supported_languages() -> list:
    """Retorna lista de idiomas soportados."""
    return SUPPORTED_LANGUAGES.copy()


def set_language(lang_code: str, save: bool = True) -> bool:
    """
    Cambia el idioma de la aplicación.
    
    Args:
        lang_code: Código del idioma (es, en, fr, de, it)
        save: Si True, guarda la preferencia para futuras sesiones
    
    Returns:
        True si el cambio fue exitoso
    """
    global _current_language, _translations
    
    if lang_code not in SUPPORTED_LANGUAGES:
        print(f"[i18n] Idioma no soportado: {lang_code}")
        return False
    
    new_translations = _load_language(lang_code)
    if not new_translations:
        return False
    
    _current_language = lang_code
    _translations = new_translations
    
    if save:
        _save_preference(lang_code)
    
    # Notificar a los callbacks registrados
    for callback in _language_change_callbacks:
        try:
            callback(lang_code)
        except Exception as e:
            print(f"[i18n] Error en callback de cambio de idioma: {e}")
    
    print(f"[i18n] Idioma cambiado a: {lang_code}")
    return True


def register_language_change_callback(callback):
    """Registra un callback que será llamado cuando cambie el idioma."""
    if callback not in _language_change_callbacks:
        _language_change_callbacks.append(callback)


def unregister_language_change_callback(callback):
    """Elimina un callback registrado."""
    if callback in _language_change_callbacks:
        _language_change_callbacks.remove(callback)


def t(key: str, **kwargs) -> str:
    """
    Obtiene una traducción por su clave.
    
    Args:
        key: Clave de la traducción (ej: "btn_start")
        **kwargs: Variables para formatear (ej: count=5, accuracy=95.5)
    
    Returns:
        Texto traducido o la clave si no existe
    """
    if not _translations:
        init()
    
    value = _translations.get(key, key)
    
    # Si el valor es una lista o diccionario, devolverlo directamente
    if isinstance(value, (list, dict)):
        return value
    
    # Formatear con variables si se proporcionan
    if kwargs and isinstance(value, str):
        try:
            value = value.format(**kwargs)
        except KeyError:
            pass  # Ignorar variables faltantes
    
    return value


def get_language_name(lang_code: str) -> str:
    """Obtiene el nombre nativo de un idioma."""
    names = t("language_names")
    if isinstance(names, dict):
        return names.get(lang_code, lang_code)
    return lang_code


# Auto-inicializar al importar
init()
