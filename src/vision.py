import cv2
import numpy as np

class Vision:
    def __init__(self):
        pass

    def find_template(self, screen_image, template_path, threshold=0.8, check_negative=False):
        """
        Busca una imagen plantilla dentro de la captura de pantalla.
        Devuelve (x, y, w, h) si se encuentra, o None si no.
        check_negative: Si True, busca también con la plantilla invertida (blanco<->negro).
        """
        if screen_image is None:
            return None

        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            print(f"Error: No se pudo cargar la imagen plantilla: {template_path}")
            return None
            
        # Verify sizes
        t_h, t_w = template.shape[:2]
        s_h, s_w = screen_image.shape[:2]
        
        if s_h < t_h or s_w < t_w:
            # print(f"⚠ Warning: Imagen de pantalla ({s_w}x{s_h}) más pequeña que template ({t_w}x{t_h}). Saltando.")
            return None

        # 1. Match Normal
        result = cv2.matchTemplate(screen_image, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        best_val = max_val
        best_loc = max_loc
        best_w, best_h = t_w, t_h

        # 2. Match Negativo (si solicitado)
        if check_negative:
             template_inv = cv2.bitwise_not(template)
             result_inv = cv2.matchTemplate(screen_image, template_inv, cv2.TM_CCOEFF_NORMED)
             min_val_i, max_val_i, min_loc_i, max_loc_i = cv2.minMaxLoc(result_inv)
             
             if max_val_i > best_val:
                 # print(f"Found better match with NEGATIVE template: {max_val_i}")
                 best_val = max_val_i
                 best_loc = max_loc_i

        if best_val >= threshold:
            center_x = best_loc[0] + best_w // 2
            center_y = best_loc[1] + best_h // 2
            return (center_x, center_y, best_w, best_h)
        
        return None

    def find_template_adaptive(self, screen_image, template_path, hint_coords=None, threshold=0.8, thresholds=None):
        """
        Busca una imagen plantilla con memoria adaptativa.
        1. Si hint_coords (x, y, w, h) existe, primero busca en esa región.
        2. Si no encuentra, busca en toda la imagen.
        
        Retorna: (center_x, center_y, w, h) o None.
        """
        if screen_image is None:
            return None
        
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            print(f"Error: No se pudo cargar la imagen plantilla: {template_path}")
            return None
        
        t_h, t_w = template.shape[:2]
        s_h, s_w = screen_image.shape[:2]
        
        if s_h < t_h or s_w < t_w:
            return None
        
        # --- Paso 1: Buscar en hint_coords si existen ---
        if hint_coords:
            hx, hy, hw, hh = hint_coords
            # Expandir el ROI para tolerancia
            margin = max(50, t_w, t_h)
            x1 = max(0, hx - margin)
            y1 = max(0, hy - margin)
            x2 = min(s_w, hx + hw + margin)
            y2 = min(s_h, hy + hh + margin)
            
            roi = screen_image[y1:y2, x1:x2]
            
            if roi.shape[0] >= t_h and roi.shape[1] >= t_w:
                result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                if max_val >= threshold:
                    abs_x = x1 + max_loc[0] + t_w // 2
                    abs_y = y1 + max_loc[1] + t_h // 2
                    print(f"Template Adaptive: Encontrado en hint ROI @ ({abs_x},{abs_y}) conf={max_val:.2f}")
                    return (abs_x, abs_y, t_w, t_h)
        
        # --- Paso 2: Búsqueda completa ---
        result = cv2.matchTemplate(screen_image, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            center_x = max_loc[0] + t_w // 2
            center_y = max_loc[1] + t_h // 2
            print(f"Template Adaptive: Encontrado en full scan @ ({center_x},{center_y}) conf={max_val:.2f}")
            return (center_x, center_y, t_w, t_h)
        
        return None


    def generate_x_templates(self):
        """Genera plantillas de 'X' en memoria para no depender de archivos."""
        templates = []
        
        # 1. X Simple (Blanca sobre negro / Negra sobre blanco)
        for thickness in [2, 4, 6]:
            for size in [30, 40, 50]:
                img = np.zeros((size, size), dtype=np.uint8)
                # Dibujar X blanca
                cv2.line(img, (5, 5), (size-5, size-5), 255, thickness)
                cv2.line(img, (size-5, 5), (5, size-5), 255, thickness)
                templates.append((f"gen_x_{size}_{thickness}", img))
                
                # Invertir (X negra)
                img_inv = cv2.bitwise_not(img)
                templates.append((f"gen_x_inv_{size}_{thickness}", img_inv))

        return templates

    def generate_ff_templates(self):
        """
        Genera plantillas de Fast Forward en memoria.
        Incluye múltiples variantes:
        - >> simple (sin barra)
        - >>| con barra vertical
        - Versiones filled y outline
        - Distintos grosores
        - Inversiones (blanco/negro)
        """
        templates = []
        
        # Tamaños típicos
        for size in range(20, 71, 10):
            margin = max(3, size // 10)
            mid_y = size // 2
            x_start = margin
            x_mid = size // 2
            x_end = size - margin
            
            # ========== VARIANTE 1: >> simple (sin barra) ==========
            img_simple = np.zeros((size, size), dtype=np.uint8)
            
            # Triángulo izquierdo
            pt1 = (x_start, margin)
            pt2 = (x_start, size - margin)
            pt3 = (x_mid - 2, mid_y)
            triangle1 = np.array([pt1, pt2, pt3])
            cv2.drawContours(img_simple, [triangle1], 0, 255, -1)
            
            # Triángulo derecho
            pt4 = (x_mid - 2, margin)
            pt5 = (x_mid - 2, size - margin)
            pt6 = (x_end, mid_y)
            triangle2 = np.array([pt4, pt5, pt6])
            cv2.drawContours(img_simple, [triangle2], 0, 255, -1)
            
            templates.append((f"gen_ff_simple_{size}", img_simple))
            templates.append((f"gen_ff_simple_inv_{size}", cv2.bitwise_not(img_simple)))
            
            # ========== VARIANTE 2: >>| con barra vertical ==========
            img_bar = img_simple.copy()
            line_w = max(2, size // 12)
            cv2.rectangle(img_bar, (x_end, margin), (x_end + line_w, size - margin), 255, -1)
            
            templates.append((f"gen_ff_bar_{size}", img_bar))
            templates.append((f"gen_ff_bar_inv_{size}", cv2.bitwise_not(img_bar)))
            
            # ========== VARIANTE 3: >> outline (solo contorno) ==========
            for thickness in [1, 2, 3]:
                img_outline = np.zeros((size, size), dtype=np.uint8)
                
                # Triángulo 1 outline
                cv2.drawContours(img_outline, [triangle1], 0, 255, thickness)
                # Triángulo 2 outline
                cv2.drawContours(img_outline, [triangle2], 0, 255, thickness)
                
                templates.append((f"gen_ff_outline_{size}_t{thickness}", img_outline))
                templates.append((f"gen_ff_outline_inv_{size}_t{thickness}", cv2.bitwise_not(img_outline)))
            
            # ========== VARIANTE 4: >>| outline con barra ==========
            for thickness in [1, 2]:
                img_outline_bar = np.zeros((size, size), dtype=np.uint8)
                cv2.drawContours(img_outline_bar, [triangle1], 0, 255, thickness)
                cv2.drawContours(img_outline_bar, [triangle2], 0, 255, thickness)
                # Barra vertical
                cv2.line(img_outline_bar, (x_end + 2, margin), (x_end + 2, size - margin), 255, thickness)
                
                templates.append((f"gen_ff_outline_bar_{size}_t{thickness}", img_outline_bar))
                templates.append((f"gen_ff_outline_bar_inv_{size}_t{thickness}", cv2.bitwise_not(img_outline_bar)))
        
        return templates

    def find_fast_forward_button(self, image):
        """
        Busca el botón de Fast Forward (>>) usando MULTIPLES assets (ff_button*.png)
        y lógica fall-back generativa.
        """
        import glob
        import os
        
        # Buscar todos los patrones
        # Usar ruta absoluta basada en la ubicación de este script (src/vision.py)
        # Los assets están en src/assets, es decir, en el mismo directorio padre 'src' + 'assets'
        base_dir = os.path.dirname(os.path.abspath(__file__)) # .../src
        assets_dir = os.path.join(base_dir, "assets")       # .../src/assets
        asset_pattern = os.path.join(assets_dir, "ff_button*.png")
        files = glob.glob(asset_pattern)
        
        if not files:
            # print("⚠ Ningún asset ff_button*.png encontrado. Usando lógica generativa...")
            pass # Seguirá al final

        height, width = image.shape[:2]
        # ROIs: Esquinas (RESTRINGIDAS al 15% ancho, 10% alto para evitar Falsos Positivos)
        roi_size_w = int(width * 0.15)
        roi_size_h = int(height * 0.10)
        
        rois = [
            ("top_left", 0, 0, roi_size_w, roi_size_h),
            ("top_right", width - roi_size_w, 0, width, roi_size_h),
            ("bottom_left", 0, height - roi_size_h, roi_size_w, height),
            ("bottom_right", width - roi_size_w, height - roi_size_h, width, height)
        ]

        # 1. Iterar sobre todos los archivos encontrados
        for f_path in files:
            template = cv2.imread(f_path, cv2.IMREAD_UNCHANGED)
            if template is None: continue

            # Usar BGR directo
            tmpl_bgr = template[:, :, :3] if template.shape[2] == 4 else template
            
            for roi_name, x1, y1, x2, y2 in rois:
                roi_img = image[y1:y2, x1:x2]
                res = cv2.matchTemplate(roi_img, tmpl_bgr, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                
                if max_val > 0.60:  # Threshold reducido (persistencia 3 frames compensa)
                    h, w = tmpl_bgr.shape[:2]
                    global_x = x1 + max_loc[0] + w // 2
                    global_y = y1 + max_loc[1] + h // 2
                    # print(f"Match FF con archivo '{os.path.basename(f_path)}': {max_val:.2f}")
                    return (global_x, global_y, w, h)

        # Fallback: Generative logic (The shape user described: >>|)
        # print("ℹ Usando lógica generativa para Fast Forward (>>|)...")
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Generar plantillas dinámicas
        gen_templates = self.generate_ff_templates()
        
        for roi_name, x1, y1, x2, y2 in rois:
            roi_img = gray_image[y1:y2, x1:x2]
            
            for name, tmpl in gen_templates:
                res = cv2.matchTemplate(roi_img, tmpl, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                
                if max_val > 0.60:  # Threshold reducido (persistencia 3 frames compensa)
                    h, w = tmpl.shape[:2]
                    global_x = x1 + max_loc[0] + w // 2
                    global_y = y1 + max_loc[1] + h // 2
                    # print(f"Match generativo FF ({name}): {max_val} en {global_x},{global_y}")
                    return (global_x, global_y, w, h)
                    
        return None

    def detect_corner_changes(self, prev_image, curr_image, threshold=0.15):
        """
        Detecta cambios significativos en las esquinas SUPERIORES entre dos frames.
        Útil para detectar cuando aparece un botón (FF/X) que antes no estaba.
        
        Args:
            prev_image: Frame anterior (BGR)
            curr_image: Frame actual (BGR)
            threshold: Umbral de cambio (0-1, default 0.15 = 15% de diferencia)
        
        Returns:
            Lista de esquinas con cambio significativo: ["top_left", "top_right"]
        """
        if prev_image is None or curr_image is None:
            return []
        
        if prev_image.shape != curr_image.shape:
            return []
        
        height, width = curr_image.shape[:2]
        
        # ROIs: Solo esquinas SUPERIORES (15% ancho x 15% alto)
        roi_size_w = int(width * 0.15)
        roi_size_h = int(height * 0.15)
        
        rois = [
            ("top_left", 0, 0, roi_size_w, roi_size_h),
            ("top_right", width - roi_size_w, 0, width, roi_size_h),
        ]
        
        changed_corners = []
        
        # Convertir a escala de grises para comparación
        prev_gray = cv2.cvtColor(prev_image, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr_image, cv2.COLOR_BGR2GRAY)
        
        for roi_name, x1, y1, x2, y2 in rois:
            prev_roi = prev_gray[y1:y2, x1:x2]
            curr_roi = curr_gray[y1:y2, x1:x2]
            
            # Calcular diferencia absoluta normalizada
            diff = cv2.absdiff(prev_roi, curr_roi)
            mean_diff = np.mean(diff) / 255.0  # Normalizar a 0-1
            
            if mean_diff > threshold:
                changed_corners.append(roi_name)
        
        return changed_corners

    def find_close_button_dynamic(self, image, ignored_zones=None):
        """
        Busca botones de cerrar (X) escaneando las esquinas y usando formas genéricas.
        ignored_zones: Lista de tuplas (x, y, radio) para ignorar.
        """
        height, width = image.shape[:2]
        
        # Definir regiones de interés (ROIs): Las 4 esquinas (15% del tamaño)
        roi_size_w = int(width * 0.15)
        roi_size_h = int(height * 0.15)
        
        rois = [
            ("top_left", 0, 0, roi_size_w, roi_size_h),
            ("top_right", width - roi_size_w, 0, width, roi_size_h),
            # Algunos ads tienen la X abajo, aunque es raro en RR3
            # ("bottom_left", 0, height - roi_size_h, roi_size_w, height),
            # ("bottom_right", width - roi_size_w, height - roi_size_h, width, height)
        ]
        
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 1. Búsqueda con templates generados
        generated_templates = self.generate_x_templates()
        
        for roi_name, x1, y1, x2, y2 in rois:
            roi_img = gray_image[y1:y2, x1:x2]
            
            for name, tmpl in generated_templates:
                # Usar un threshold un poco más bajo para formas genéricas
                res = cv2.matchTemplate(roi_img, tmpl, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                
                if max_val > 0.65: # Threshold tolerante para formas
                    h, w = tmpl.shape[:2]
                    # Ajustar coordenadas globales
                    global_x = x1 + max_loc[0] + w // 2
                    global_y = y1 + max_loc[1] + h // 2
                    
                    # Verificar si está en zona ignorada
                    if ignored_zones:
                        is_ignored = False
                        for (ix, iy, ir) in ignored_zones:
                            dist = np.sqrt((global_x - ix)**2 + (global_y - iy)**2)
                            if dist < ir:
                                is_ignored = True
                                break
                        if is_ignored:
                            continue

                    return (global_x, global_y, w, h)

        return None
