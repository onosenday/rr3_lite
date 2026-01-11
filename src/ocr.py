import pytesseract
from PIL import Image
import cv2
import numpy as np
import re

class OCR:
    def __init__(self):
        # Si tesseract no está en el PATH, descomentar y ajustar ruta:
        # pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
        pass

    def preprocess_image(self, cv2_image):
        """Mejora la imagen para OCR (skala de grises, umbralización)."""
        gray = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
        # Aplicar umbralización para resaltar texto negro/blanco
        # Ajustar si el texto es blanco sobre fondo oscuro o al revés.
        # En RR3 suele ser texto blanco.
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV) 
        return thresh

    def read_text(self, cv2_image):
        """Lee texto genérico de una imagen."""
        if cv2_image is None:
            return ""
        
        # Pytesseract espera PIL Image o numpy array
        # Convertir BGR a RGB para PIL si fuera necesario, pero pytesseract maneja numpy.
        text = pytesseract.image_to_string(cv2_image)
        return text.strip()

    def extract_gold_amount(self, cv2_image):
        """Intenta extraer la cantidad de oro de la pantalla de recompensa."""
        # Se asume que le pasamos toda la pantalla o un recorte grande.
        # Buscamos patrones como "X de oro" o números grandes aislados.
        
        # Preprocesar
        # processed = self.preprocess_image(cv2_image) # A veces raw funciona mejor si hay buen contraste
        
        # Configuración para buscar solo números o texto específico podría ayudar
        # psm 6: Assume a single uniform block of text.
        text = pytesseract.image_to_string(cv2_image, config='--psm 6')
        
        # Buscar patrón numérico cerca de keywords "Gold", "Oro", "GC", "R$" (si fuera dinero, pero buscamos oro)
        # RR3 dice algo como "5 Gold" o solo el numero grande.
        # Vamos a buscar dígitos simples primero.
        
        # print(f"DEBUG OCR RAW: {text}") # Para depurar
        
        # Regex para encontrar números
        # Buscamos números que aparezcan en la imagen
        numbers = re.findall(r'\d+', text)
        
        # Filtrado simple: El oro suele ser 1, 2, 5, etc.
        # Si hay varios números, habría que ver cuál es el correcto por contexto o posición.
        # Por ahora devolvemos el primer número encontrado o lógica más compleja si tenemos ejemplos.
        if numbers:
            return int(numbers[0])
        
        return 0

    def find_text(self, cv2_image, search_text, exact_match=False, case_sensitive=False):
        """Busca texto en la imagen y devuelve coordenadas (x, y) del centro. Multi-pass."""
        if cv2_image is None: return None
        
        # Estrategia Multi-pass:
        gray = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
        _, thresh_inv = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        _, thresh_norm = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        images_to_try = [thresh_inv, gray, thresh_norm]
        
        # Palabras clave de búsqueda
        if case_sensitive:
             # Respetar casing original
             search_words = [w for w in search_text.split() if len(w) > 3]
             if not search_words: search_words = [w for w in search_text.split()]
        else:
             search_words = [w.lower() for w in search_text.split() if len(w) > 3]
             if not search_words: search_words = [w.lower() for w in search_text.split()]
        
        for idx, img_pass in enumerate(images_to_try):
            if len(img_pass.shape) == 2:
                img_rgb = cv2.cvtColor(img_pass, cv2.COLOR_GRAY2RGB)
            else:
                img_rgb = img_pass

            data = pytesseract.image_to_data(img_rgb, output_type=pytesseract.Output.DICT)
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                raw_text = data['text'][i].strip()
                if not raw_text: continue
                
                if case_sensitive:
                     text_to_check = raw_text
                     target_text = search_text
                else:
                     text_to_check = raw_text.lower()
                     target_text = search_text.lower()
                
                match = False
                if exact_match:
                    if text_to_check == target_text:
                        match = True
                else:
                    for sw in search_words:
                        if sw in text_to_check or text_to_check in sw:
                            match = True
                            break
                        
                if match:
                    # Encontramos match
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    return (x + w // 2, y + h // 2)
                    
        return None

    def find_phrase(self, cv2_image, phrase, case_sensitive=False):
        """Busca una frase exacta (secuencia de palabras en la misma línea). Devuelve centro (x,y)."""
        if cv2_image is None: return None
        
        target_words = phrase.split()
        if not target_words: return None
        if not case_sensitive:
            target_words = [w.lower() for w in target_words]
            
        gray = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
        # Probamos par de umbrales por robustez
        _, thresh_inv = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        _, thresh_norm = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        for img_pass in [thresh_inv, gray, thresh_norm]:
             if len(img_pass.shape) == 2:
                 img_rgb = cv2.cvtColor(img_pass, cv2.COLOR_GRAY2RGB)
             else:
                 img_rgb = img_pass
                 
             data = pytesseract.image_to_data(img_rgb, output_type=pytesseract.Output.DICT)
             n_boxes = len(data['text'])
             
             # Recorremos buscando la primera palabra
             for i in range(n_boxes):
                 word = data['text'][i].strip()
                 if not word: continue
                 
                 curr_word = word if case_sensitive else word.lower()
                 
                 # Chequeo primera palabra match
                 if curr_word == target_words[0]:
                     # Candidato encontrado. Verificar resto de palabras
                     match_full = True
                     combined_w = data['width'][i]
                     
                     current_idx = i
                     for j in range(1, len(target_words)):
                         next_idx = current_idx + 1
                         if next_idx >= n_boxes:
                             match_full = False
                             break
                             
                         # Verificar que sigamos en la misma linea y bloque (aproximado)
                         # Tesseract usa line_num
                         if data['line_num'][next_idx] != data['line_num'][current_idx]:
                             match_full = False
                             break
                             
                         next_word_raw = data['text'][next_idx].strip()
                         next_word = next_word_raw if case_sensitive else next_word_raw.lower()
                         
                         if next_word != target_words[j]:
                             match_full = False
                             break
                             
                         # Acumular ancho para el centro final
                         # Asumimos que están adyacentes horizontalmente
                         # Distancia entre palabras?
                         dist = data['left'][next_idx] - (data['left'][current_idx] + data['width'][current_idx])
                         if dist > 100: # Si están muy lejos, no es frase
                             match_full = False
                             break
                             
                         combined_w = (data['left'][next_idx] + data['width'][next_idx]) - data['left'][i]
                         current_idx = next_idx
                         
                     if match_full:
                         # Calcular centro de TODA la frase
                         x = data['left'][i]
                         y = data['top'][i] # Usamos top del primero
                         h = data['height'][i] # Altura del primero
                         
                         return (x + combined_w // 2, y + h // 2)
                         
        return None

    def get_screen_texts(self, cv2_image, min_y=0):
        """Devuelve lista de (texto, x, y, w, h) de toda la pantalla.
           Usa estrategia Multi-pass para asegurar que no se pierden textos."""
        if cv2_image is None: return []

        # Estrategia Multi-pass idéntica a find_text
        gray = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
        _, thresh_inv = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        _, thresh_norm = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        # Pass 4: Otsu (Dynamic Thresholding)
        _, thresh_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Probar Invertido (mejor contraste), luego Gray (suave), luego Normal, luego Otsu
        images_to_try = [thresh_inv, gray, thresh_norm, thresh_otsu]
        
        results_set = set() # Evitar duplicados (usaremos key: "text_x_y")
        results_list = []
        
        for img_pass in images_to_try:
            # Pytesseract espera imagen (el wrapper lo gestiona o lo pasamos como RGB)
            if len(img_pass.shape) == 2:
                img_rgb = cv2.cvtColor(img_pass, cv2.COLOR_GRAY2RGB)
            else:
                img_rgb = img_pass

            # psm 11: Sparse text. Busca tanto texto como sea posible sin asumir orden.
            # default (3) a veces falla en listas dispersas. Probar config default primero.
            data = pytesseract.image_to_data(img_rgb, output_type=pytesseract.Output.DICT)
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                text = data['text'][i].strip()
                if not text: continue
                if len(text) < 2: continue # Bajamos a 2 para no perder "AM", "PM", "24"
                
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                cy = y + h // 2
                
                # Check min_y
                if cy < min_y: continue
                
                # Deduplication key based on rough proximity to combine passes
                # Usamos una clave laxa para evitar el mismo texto en exacto mismo sitio
                # (Texto, X//10, Y//10)
                key = (text, x // 20, y // 20)
                
                if key not in results_set:
                    results_set.add(key)
                    results_list.append((text, x, y, w, h))
                
        # Ordenar por verticalidad (arriba a abajo)
        return sorted(results_list, key=lambda tx: tx[2])

    def get_lines(self, cv2_image):
        """Devuelve líneas de texto completas de la imagen."""
        if cv2_image is None: return []
        
        rgb = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
        # psm 6: Assume a single uniform block of text.
        text = pytesseract.image_to_string(rgb, config='--psm 6')
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return lines

    def find_text_adaptive(self, cv2_image, search_text, hint_coords=None, thresholds=None):
        """
        Busca texto con sensibilidad adaptativa.
        1. Si hint_coords (x, y, w, h) se proporciona, primero busca en esa región.
        2. Si no se encuentra, itera por diferentes umbrales de binarización.
        
        Retorna: (x, y, w, h, threshold_used) o None si no se encuentra.
        """
        if cv2_image is None:
            return None
        
        if thresholds is None:
            thresholds = [150, 100, 200, 80, 180, 120]  # Default sensitivity range
        
        search_lower = search_text.lower()
        h_img, w_img = cv2_image.shape[:2]
        
        # --- Paso 1: Buscar en hint_coords si existen ---
        if hint_coords:
            hx, hy, hw, hh = hint_coords
            # Expandir el ROI un poco para tolerancia
            margin = 50
            x1 = max(0, hx - margin)
            y1 = max(0, hy - margin)
            x2 = min(w_img, hx + hw + margin)
            y2 = min(h_img, hy + hh + margin)
            
            roi = cv2_image[y1:y2, x1:x2]
            
            # Probar con el umbral recordado primero (si hint_coords incluye threshold)
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            for thresh_val in thresholds[:2]:  # Solo los primeros 2 en ROI
                _, thresh_img = cv2.threshold(gray_roi, thresh_val, 255, cv2.THRESH_BINARY_INV)
                img_rgb = cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2RGB)
                
                data = pytesseract.image_to_data(img_rgb, output_type=pytesseract.Output.DICT)
                for i in range(len(data['text'])):
                    raw_text = data['text'][i].strip().lower()
                    if not raw_text: continue
                    
                    # Match Logic:
                    # 1. Exact match (insensitive)
                    # 2. Search term inside detected text (e.g. "Madrid" in "Madrid (GMT+1)")
                    # 3. Detected text inside Search term ONLY if detected is long enough (avoid "a" in "Madrid")
                    match = False
                    if search_lower == raw_text:
                        match = True
                    elif search_lower in raw_text:
                        match = True
                    elif len(raw_text) > 3 and raw_text in search_lower:
                        match = True
                        
                    if match:
                        # Encontrado en ROI
                        lx, ly, lw, lh = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                        # Ajustar coordenadas al marco completo
                        abs_x = x1 + lx
                        abs_y = y1 + ly
                        print(f"OCR Adaptive: Encontrado '{search_text}' en hint ROI @ ({abs_x},{abs_y}) thresh={thresh_val}")
                        return (abs_x, abs_y, lw, lh, thresh_val)
        
        # --- Paso 2: Búsqueda completa con umbral variable ---
        gray = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
        
        for thresh_val in thresholds:
            _, thresh_img = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
            img_rgb = cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2RGB)
            
            data = pytesseract.image_to_data(img_rgb, output_type=pytesseract.Output.DICT)
            for i in range(len(data['text'])):
                # Filter bad confidence (blocks)
                if 'conf' in data:
                    try:
                        conf = int(data['conf'][i])
                        if conf == -1: continue
                    except:
                        pass

                raw_text = data['text'][i].strip().lower()
                if not raw_text: continue
                
                match = False
                if search_lower == raw_text:
                    match = True
                elif search_lower in raw_text:
                    match = True
                elif len(raw_text) > 3 and raw_text in search_lower:
                    match = True
                    
                if match:
                    lx, ly, lw, lh = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    print(f"OCR Adaptive: Encontrado '{search_text}' (Raw: '{raw_text}') @ ({lx},{ly}) thresh={thresh_val}")
                    return (lx, ly, lw, lh, thresh_val)
        
        # Paso 3: Probar también con OTSU y normal
        _, thresh_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        for img_pass in [thresh_otsu, gray]:
            if len(img_pass.shape) == 2:
                img_rgb = cv2.cvtColor(img_pass, cv2.COLOR_GRAY2RGB)
            else:
                img_rgb = img_pass
            
            data = pytesseract.image_to_data(img_rgb, output_type=pytesseract.Output.DICT)
            for i in range(len(data['text'])):
                if 'conf' in data:
                    try:
                        conf = int(data['conf'][i])
                        if conf == -1: continue
                    except:
                        pass
                
                raw_text = data['text'][i].strip().lower()
                if not raw_text: continue
                
                match = False
                if search_lower == raw_text:
                    match = True
                elif search_lower in raw_text:
                    match = True
                elif len(raw_text) > 3 and raw_text in search_lower:
                    match = True

                if match:
                    lx, ly, lw, lh = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    print(f"OCR Adaptive: Encontrado '{search_text}' (Raw: '{raw_text}') @ ({lx},{ly}) (OTSU/Gray pass)")
                    return (lx, ly, lw, lh, -1)  # -1 indica pass especial
        
        print(f"OCR Adaptive: No encontrado '{search_text}' tras todos los intentos.")
        return None

