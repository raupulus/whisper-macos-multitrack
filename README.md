# whisper-macos-multitrack 🎙️ (Apple Silicon Edition)

Herramienta CLI de transcripción local de audio de alta fidelidad, diseñada y optimizada específicamente para **Apple Silicon (MacBook M1 Pro, 16 GB RAM)** con aceleración GPU Metal nativa mediante el framework **MLX** (`mlx-whisper`).

Diseñada para transcribir tanto notas de voz rápidas (`.m4a`, `.mp3`, etc.) como grabaciones multipista de reuniones de trabajo, conferencias o sesiones de larga duración (1-5h) grabadas con OBS, DAW o suites de videoconferencia (`.mka`).

---

## 👤 Autoría y Contacto

* **Autor:** Raúl Caro Pastorino ([@raupulus](https://github.com/raupulus))
* **Sitio Web:** [https://raupulus.dev](https://raupulus.dev)
* **Correo Público:** [public@raupulus.dev](mailto:public@raupulus.dev)

---

## ✨ Características Principales

* 🔒 **100% Local y Privado:** Todo el procesamiento ocurre íntegramente en tu máquina local. Ningún fragmento de audio, dato ni texto sale jamás a servidores externos o APIs de terceros.
* ⚡ **Aceleración Metal Nativa (MLX):** Aprovecha la GPU integrada y los 200 GB/s de ancho de banda de memoria unificada del chip M1 Pro mediante el framework de Apple `mlx-whisper`.
* 🎯 **Máxima Calidad en Español (`large-v3`):** Configurado por defecto con el modelo completo **`whisper-large-v3`**, optimizado para capturar vocabulario, acentos y puntuación cuidada en español de España.
* 👥 **Diarización Natural Multipista (.mka):**
  * Detecta automáticamente las pistas independientes de audio del contenedor multimedia.
  * Procesa cada pista de forma aislada para evitar solapamientos acústicos:
    * `_pista1.md`: Fuente de entrada 1 (Micrófono principal / Presentador).
    * `_pista2.md`: Fuente de entrada 2 (Participantes remotos / Llamada).
    * `_pista3.md`: Fuente de entrada 3 (Audio auxiliar / Presentación / Sistema).
  * **Transcripción entrelazada:** Genera `<nombre>_pista1_y_pista2_combinados.md` ordenando cronológicamente el diálogo de las dos fuentes principales segundo a segundo.
* 🔇 **Protección Antihalucinación en Silencios:**
  * Configurado con `condition_on_previous_text=False`, `word_timestamps=True` y `hallucination_silence_threshold=2.0`.
  * Evita los bucles infinitos típicos de Whisper (como repetir frases aleatorias durante minutos de silencio o pausas largas).
* 📁 **Organización Automática en Subdirectorios:** Cada archivo analizado agrupa todas sus salidas (`.md` y `.mp3`) dentro de una subcarpeta con su propio nombre base.
* 🎵 **Exportación Inteligente de Audios Ligeros:**
  * **Audio histórico combinado (Pistas 1 + 2):** Mezclado en mono equilibrado (`amix`) a **128 kbps** para archivar la conversación ahorrando hasta un 70% de espacio en disco.
  * **Audio independiente de alta fidelidad (Pista 3):** Exportado en estéreo a **192 kbps** para archivo o edición auxiliar.
* 🛡️ **Preservación Absoluta:** Los archivos originales (`.mka`, `.m4a`, etc.) **NUNCA se borran ni modifican**.
* ⚡ **Idempotencia:** Si los archivos generados ya existen, se omiten al instante para ahorrar batería y ciclos de GPU (usa `--force` para rehacerlos).

---

## 📋 Requisitos del Sistema

1. **Equipo:** Mac con procesador Apple Silicon (optimizado para M1 Pro con 16 GB de RAM).
2. **FFmpeg y FFprobe:**
   ```bash
   brew install ffmpeg
   ```
3. **Python 3.12:**
   ```bash
   brew install python@3.12
   ```

---

## 🚀 Instalación y Puesta en Marcha

1. Clona el repositorio e ingresa en él:
   ```bash
   git clone <url-del-repositorio> whisper-macos-multitrack
   cd whisper-macos-multitrack
   ```

2. Crea el entorno virtual aislado con Python 3.12:
   ```bash
   /opt/homebrew/bin/python3.12 -m venv .venv
   ```

3. Instala las dependencias necesarias:
   ```bash
   ./.venv/bin/python -m pip install --no-user -r requirements.txt
   ```
   *(Nota: Se utiliza `--no-user` para respetar el aislamiento del entorno virtual).*

4. Otorga permisos de ejecución al script:
   ```bash
   chmod +x transcribe.py
   ```

5. *(Opcional)* Copia la plantilla de configuración:
   ```bash
   cp env.example.py env.py
   ```

---

## ⚙️ Configuración (`env.py`)

El archivo `env.py` (ignorado por Git para proteger tus preferencias personales) permite ajustar todos los parámetros del flujo:

```python
# Número máximo de pistas a procesar en archivos multipista (.mka)
# 2 = solo entradas 1 y 2, 3 = incluye pista auxiliar/sistema, None = todas
MAX_TRACKS = 3

# Organización: agrupar salidas en una subcarpeta con el nombre del audio
USE_OUTPUT_SUBDIRECTORIES = True

# Exportación de audios comprimidos ligeros (.mp3)
EXPORT_AUDIOS = True
BITRATE_CONVERSACION = "128k"       # Pistas 1 y 2 mezcladas en mono
BITRATE_PISTA3 = "192k"             # Pista 3 de alta fidelidad

# Generar transcripción combinada de diálogo entrelazado
GENERATE_COMBINED_CHAT = True

# Modelo Whisper (máxima fidelidad)
DEFAULT_MODEL = "mlx-community/whisper-large-v3-mlx"

# Idioma predeterminado
DEFAULT_LANGUAGE = "es"

# Umbral en segundos para descartar alucinaciones en silencio
HALLUCINATION_SILENCE_THRESHOLD = 2.0
```

---

## 💻 Modo de Uso

### 1. Flujo Estándar (Carpeta `audios/`)

1. Coloca tus audios o grabaciones en la carpeta `audios/`:
   ```
   audios/
   ├── nota_voz.m4a
   └── reunion_proyecto_0600.mka
   ```

2. Ejecuta el comando principal (se reinvoca automáticamente en `.venv`):
   ```bash
   ./transcribe.py
   ```

3. Se generarán automáticamente las subcarpetas con todos los contenidos:
   ```
   audios/
   ├── nota_voz.m4a
   ├── nota_voz/
   │   └── nota_voz.md
   ├── reunion_proyecto_0600.mka                                    # Original intacto
   └── reunion_proyecto_0600/
       ├── reunion_proyecto_0600_pista1.md                         # Transcripción Pista 1 (Fuente de entrada 1)
       ├── reunion_proyecto_0600_pista2.md                         # Transcripción Pista 2 (Fuente de entrada 2)
       ├── reunion_proyecto_0600_pista3.md                         # Transcripción Pista 3 (Audio auxiliar)
       ├── reunion_proyecto_0600_pista1_y_pista2_combinados.md     # Diálogo entrelazado Tú + Otros participantes
       ├── reunion_proyecto_0600_pista1_y_pista2_combinados.mp3    # Audio histórico mono a 128 kbps
       └── reunion_proyecto_0600_pista3.mp3                        # Audio auxiliar independiente a 192 kbps
   ```

### 2. Procesar una Ruta Específica

Puedes pasar como argumento cualquier archivo o directorio externo:

```bash
# Procesar un archivo individual
./transcribe.py ~/Desktop/grabacion.mka

# Procesar una carpeta personalizada
./transcribe.py /Volumes/DiscoExterno/Grabaciones/
```

### 3. Opciones del CLI

| Argumento | Descripción |
| :--- | :--- |
| `path` | Ruta a la carpeta o archivo a transcribir (por defecto: `audios`) |
| `-t`, `--max-tracks` | Límite de pistas a procesar (ej. `-t 2` o `-t 3`) |
| `-m`, `--model` | Modelo de HuggingFace/MLX (ej. `mlx-community/whisper-large-v3-turbo`) |
| `-l`, `--language` | Código de idioma ISO (por defecto: `es`) |
| `-p`, `--prompt` | Prompt inicial para guiar vocabulario o puntuación específica |
| `--silence-threshold`| Segundos de silencio para cortar alucinaciones (por defecto: `2.0`) |
| `--no-export-audios` | Desactiva la exportación de pistas MP3 |
| `--no-combined-chat` | Desactiva la generación del markdown entrelazado |
| `-f`, `--force` | Fuerza la re-transcripción y re-exportación omitiendo la caché |

---

## 📄 Formato de los Archivos Generados

### Transcripción Combinada (`..._pista1_y_pista2_combinados.md`):

```markdown
# Conversación Combinada: reunion_proyecto_0600.mka

- **Archivo original:** `reunion_proyecto_0600.mka`
- **Pista 1 (Tú):** Pista 1: Micrófono principal (Presentador)
- **Pista 2 (Otros participantes):** Pista 2: Participantes remotos (Llamada)
- **Audio de referencia:** `reunion_proyecto_0600_pista1_y_pista2_combinados.mp3`
- **Fecha:** 2026-10-01 06:00:00

---

## Diálogo

**[00:00:05 -> 00:00:09] Tú:** Buenos días a todos, son las seis de la mañana, comenzamos la reunión de seguimiento del proyecto.

**[00:00:10 -> 00:00:14] Otros participantes:** Buenos días, listos para revisar los objetivos y el estado de la entrega.

**[00:00:15 -> 00:00:20] Tú:** Perfecto, comparto la pantalla para repasar los puntos clave del sprint.
```

---

## 🔒 Privacidad y Exclusión de Git

El repositorio cuenta con reglas estrictas en `.gitignore`:
* Ningún archivo de audio (`.mka`, `.mp3`, `.m4a`, etc.) ni transcripción privada se subirá jamás a Git.
* Se ignoran entornos virtuales (`.venv/`), configuraciones locales (`env.py`), cachés de HuggingFace y metadatos de IDEs (`.vscode/`, `.idea/`).
