"""
env.example.py - Plantilla de configuración para whisper-macos-multitrack

Para personalizar los parámetros:
1. Copia este archivo como 'env.py':
   cp env.example.py env.py
2. Modifica los valores según tus necesidades.
"""

# Número máximo de pistas de audio a procesar en archivos multipista (.mka).
# Ejemplo:
#   MAX_TRACKS = 2    -> Procesa pistas 1 y 2 (Entrada 1 y Entrada 2)
#   MAX_TRACKS = 3    -> Procesa pistas 1, 2 y 3 (Entrada 1, Entrada 2 y Audio auxiliar)
#   MAX_TRACKS = None -> Procesa todas las pistas disponibles
MAX_TRACKS = 3

# Organización: Crear una subcarpeta con el nombre del audio para agrupar
# todas las pistas y transcripciones generadas (.md y .mp3).
USE_OUTPUT_SUBDIRECTORIES = True

# --- EXPORTACIÓN DE AUDIOS LIGEROS (.mp3) ---
# Extrae y comprime las pistas de audio para archivo histórico o edición:
EXPORT_AUDIOS = True

# Pistas 1 y 2 combinadas en un único archivo de audio mono equilibrado (histórico):
BITRATE_CONVERSACION = "128k"

# Pista 3 de alta fidelidad para archivo independiente o edición (audio auxiliar/sistema):
BITRATE_PISTA3 = "192k"

# --- TRANSCRIPCIONES ---
# Generar transcripción combinada de las pistas 1 y 2 en orden cronológico
# (<nombre>_pista1_y_pista2_combinados.md)
GENERATE_COMBINED_CHAT = True

# Modelo de Whisper predeterminado (optimizado para Apple Silicon Metal)
# Opciones populares:
#   "mlx-community/whisper-large-v3-mlx"   (Máxima calidad, recomendado para M1 Pro 16GB)
#   "mlx-community/whisper-large-v3-turbo" (Ultra rápido, muy buena calidad)
DEFAULT_MODEL = "mlx-community/whisper-large-v3-mlx"

# Idioma predeterminado ('es' para español)
DEFAULT_LANGUAGE = "es"

# Directorio por defecto con los archivos a transcribir
AUDIO_DIR = "audios"

# Umbral de silencio en segundos para descartar alucinaciones en pausas
HALLUCINATION_SILENCE_THRESHOLD = 2.0
