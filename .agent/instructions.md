# 🏎️ Real Racing 3 Bot Lite - Instrucciones de Uso

Este bot automatiza el proceso de ver anuncios para farmear oro en Real Racing 3 utilizando ADB.
**Esta es la versión Lite, optimizada y sin dependencias de Machine Learning.**

## 📋 Requisitos Previos

1.  **Android Debug Bridge (ADB)**: Debe estar instalado y configurado en tu sistema.
    *   Ubuntu/Debian: `sudo apt install adb`
2.  **Dispositivo Android**:
    *   Conectado por USB.
    *   Depuración USB activada.
    *   (Opcional pero recomendado) Pantalla configurada para no bloquearse o usar el modo "Stay Awake" en opciones de desarrollador.
    *   **Nota para Xiaomi**: Activar "Depuración USB (Ajustes de seguridad)" para permitir clicks simulados.
3.  **Python 3.10+**.

## 🚀 Instalación y Ejecución

### Opción Automática (Linux)
Simplemente ejecuta el script de lanzamiento, que creará el entorno virtual si no existe:

```bash
./run.sh
```

### Opción Manual

1.  Crear y activar un entorno virtual:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  Instalar dependencias:
    ```bash
    pip install -r requirements.txt
    ```

3.  Ejecutar:
    ```bash
    cd src
    python gui.py
    ```

## ⚙️ Funcionamiento y GUI

1.  **Ventana Principal**:
    *   **Iniciar/Parar**: Control del ciclo del bot.
    *   **Live View**: Muestra lo que el bot está viendo en tiempo real.
    *   **Métricas**: Oro ganado hoy, total histórico y ritmo (Oro/Hora).
2.  **Gráfico de Ganancias**:
    *   Haz click en el icono de gráfico para ver el histórico de los últimos 7 días.
    *   Se actualiza automáticamente cada minuto mientras la ventana esté abierta.
3.  **Ciclo Automático**:
    *   El bot busca la moneda de oro, confirma el anuncio, lo ve y cierra la ventana de recompensa.
    *   **Kiritimati Trick**: Si "No hay más anuncios" aparece, el bot cambiará automáticamente la zona horaria del dispositivo entre Madrid y Kiribati para resetear el límite de anuncios.

## 🛠 Solución de Problemas (Troubleshooting)

### El bot se queda atascado en el cambio de zona horaria
*   **Posible causa**: La lupa de búsqueda en Ajustes de Android ha cambiado de posición.
*   **Solución**: El bot intenta usar OCR para encontrarla, pero si falla, puedes verificar el archivo `src/main.py` -> `handle_timezone_sequence` y ajustar las coordenadas de fallback o los términos de búsqueda ("Kiribati", "Espa").

### El bot no cierra los anuncios
*   **Posible causa**: El botón "X" es muy pequeño o tiene un diseño nuevo.
*   **Solución**: El bot usa detección dinámica de "X". Asegúrate de que el brillo de la pantalla en la captura se vea bien (no negro).

### Errores de ADB
*   Asegúrate de que solo hay un dispositivo conectado o especifica el serial si es necesario.
*   Prueba a reiniciar el servidor: `adb kill-server && adb start-server`.

## ⚠️ Notas Importantes

*   **Horario de Funcionamiento**: Por defecto, el bot solo opera de **12:00 a 00:00** (Configurable en `src/config.py`). Fuera de ese horario entrará en pausa automática.
*   **Logs**: Todos los registros se guardan en `gold_log.db` (SQLite). No lo borres si quieres conservar las estadísticas.
