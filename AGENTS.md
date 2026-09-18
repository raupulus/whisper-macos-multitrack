# AGENTS.md

Guía operativa y contexto de arquitectura para agentes de IA que interactúen con este repositorio (`whisper-macos-multitrack`).

---

## 1. Visión General del Proyecto

`whisper-macos-multitrack` es una herramienta CLI para transcripción de audio local de alta fidelidad, diseñada y optimizada específicamente para **Apple Silicon (MacBook M1 Pro, 16 GB RAM)** utilizando el framework nativo **MLX** (`mlx-whisper`) con aceleración por GPU Metal.

### Casos de uso principales:
1. **Notas de voz y grabaciones cortas:** Grabaciones tomadas con el teléfono (`.m4a`, `.mp3`, `.wav`, etc.).
2. **Llamadas largas multipista (OBS):** Grabaciones de videollamadas de 1 a 5 horas en formato `.mka` con pistas separadas de audio:
   - Pista 1: Micrófono personal (Tú).
   - Pista 2: Audio del sistema, llamadas o Discord (Colegas).
   - Pista 3: Audio de videojuegos, clips o música.

---

## 2. Reglas Estrictas de Privacidad y Seguridad

> [!CAUTION]
> **REGLAS DE PRIVACIDAD CRÍTICAS:**
> - **NUNCA** incluir, compartir ni commitear direcciones de correo personal/privado ni ningún otro dato personal confidencial del autor.
> - El **ÚNICO** correo público autorizado para metadatos, commits, documentación o contacto es: `public@raupulus.dev`.
> - **Autor:** Raúl Caro Pastorino (`@raupulus`) - [https://raupulus.dev](https://raupulus.dev).
> - **NUNCA** commitear grabaciones de audio (`.mka`, `.mp3`, `.m4a`, etc.) ni transcripciones que contengan conversaciones del usuario. Todo archivo dentro de `audios/` (salvo `.gitkeep`) debe permanecer siempre ignorado por Git.

---

## 3. Arquitectura y Convenciones

### Estructura del repositorio:
```
whisper-macos-multitrack/
├── .venv/               # Entorno virtual Python 3.12 (aislado, ignorado por Git)
├── audios/              # Directorio de entrada y salida de audios y .md (ignorado por Git)
│   └── .gitkeep
├── env.example.py       # Plantilla de configuración versionada
├── env.py               # Configuración local activa (ignorado por Git)
├── transcribe.py        # Script ejecutable principal (CLI con tipado estricto)
├── requirements.txt     # Dependencias del proyecto (mlx-whisper, etc.)
├── AGENTS.md            # Este archivo de instrucciones para agentes
├── README.md            # Documentación de cara al usuario
└── .gitignore           # Exclusiones estrictas para Git
```

### Comportamiento y flujo interno de `transcribe.py`:

1. **Auto-reinvocación en `.venv`:**
   - Si se ejecuta con el python del sistema (ej. `python3 transcribe.py`), detecta la presencia de `.venv/bin/python`.
   - Comprueba `Path(sys.prefix).resolve() != VENV_DIR.resolve()` para evitar bucles infinitos de reinvocación con symlinks de Homebrew.
   - Se reinvoca automáticamente con el intérprete de `.venv` sin requerir `source .venv/bin/activate`.

2. **Detección multipista (`ffprobe`) y títulos de OBS:**
   - Usa `ffprobe` con salida JSON para detectar el número de streams de audio y sus etiquetas de metadatos (`stream_tags=title`).
   - Detecta títulos nativos de OBS como *"Mi voz en off"* o *"Voz de otros participantes"* y los integra en las etiquetas y encabezados.

3. **Organización en subdirectorios:**
   - Crea automáticamente una subcarpeta con el nombre base del archivo (ej. `audios/<nombre_archivo>/`) y guarda allí todas las salidas generadas.

4. **Protección antihalucinación en silencios (CRÍTICO):**
   - En grabaciones de varias horas con silencios largos o ruido de fondo:
     - `condition_on_previous_text=False`: Desacopla ventanas para evitar bucles de retroalimentación infinita de frases alucinadas.
     - `word_timestamps=True`: Habilita la precisión a nivel de palabra para corte de silencios.
     - `hallucination_silence_threshold=2.0`: Descarta silencios superiores a 2 segundos antes de que el decodificador de Whisper intente inventar palabras.
     - `initial_prompt=None` por defecto para no contaminar el decodificador en tramos vacíos.

5. **Mezcla y exportación de audio:**
   - **Pistas 1 y 2:** Se combinan en un único archivo mono equilibrado con filtro `amix=inputs=2:duration=longest:dropout_transition=0:normalize=0` a **128 kbps** (`<nombre>_pista1_y_pista2_combinados.mp3`). Se suministra el archivo dos veces a ffmpeg (`-i input -i input`) para emplear demuxers independientes por pista y evitar bloqueos/cortes prematuros por interleaving irregular en archivos `.mka` de OBS.
   - **Pista 3:** Se extrae de forma independiente a **192 kbps** (`<nombre>_pista3.mp3`) para edición de vídeo o banco de clips.

6. **Transcripción combinada de diálogo:**
   - Transcribe pistas de forma aislada para evitar solapamientos acústicos.
   - Genera `<nombre>_pista1_y_pista2_combinados.md` entrelazando las intervenciones ordenadas por su marca de tiempo (`start`).
   - Implementa `parse_markdown_segments` para recuperar los segmentos de archivos `.md` existentes si la transcripción ya se completó en una ejecución previa.

7. **Preservación estricta:**
   - Los archivos multimedia originales **NUNCA se borran ni modifican**.

8. **Idempotencia completa:**
   - Comprueba individualmente la existencia de cada `.md` y cada `.mp3`. Si ya existen, los omite al instante salvo que se utilice `--force`.

---

## 4. Configuración (`env.py`)

La configuración se gestiona mediante `env.py` (plantilla en `env.example.py`):

* `MAX_TRACKS`: Límite de pistas a procesar (ej. `2` para voz, `3` para incluir juego, `None` para todas).
* `USE_OUTPUT_SUBDIRECTORIES`: `True` para agrupar salidas por carpeta.
* `EXPORT_AUDIOS`: `True` para generar los MP3s comprimidos.
* `BITRATE_CONVERSACION`: `"128k"` para la mezcla de pistas 1 y 2.
* `BITRATE_PISTA3`: `"192k"` para la pista de producción de vídeo.
* `GENERATE_COMBINED_CHAT`: `True` para el diálogo entrelazado.
* `DEFAULT_MODEL`: `"mlx-community/whisper-large-v3-mlx"`.
* `DEFAULT_LANGUAGE`: `"es"`.
* `HALLUCINATION_SILENCE_THRESHOLD`: `2.0`.

---

## 5. Comandos Operativos Clave

* **Ejecutar transcripción sobre `audios/`:**
  ```bash
  ./transcribe.py
  ```
* **Procesar un archivo o carpeta específica:**
  ```bash
  ./transcribe.py /ruta/a/archivo.mka
  ./transcribe.py /ruta/a/directorio/
  ```
* **Forzar re-procesamiento completo:**
  ```bash
  ./transcribe.py --force
  ```
* **Sobrescribir límite de pistas por CLI:**
  ```bash
  ./transcribe.py --max-tracks 2
  ```
* **Instalar dependencias en el entorno virtual:**
  ```bash
  ./.venv/bin/python -m pip install --no-user -r requirements.txt
  ```
* **Verificar aceleración Metal en Python:**
  ```bash
  ./.venv/bin/python -c "import mlx.core as mx; print('Metal GPU:', mx.metal.is_available())"
  ```
