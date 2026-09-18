#!/usr/bin/env python3
"""
transcribe.py - Transcripción local de alta calidad para Apple Silicon (MacBook M1 Pro)
Utiliza MLX-Whisper (Metal GPU), detecta pistas múltiples en archivos .mka (OBS),
organiza salidas en subdirectorios, combina pistas 1 y 2 en audio y markdown,
y exporta pistas seleccionadas para producción.
"""

import sys
import os
from pathlib import Path

# Auto-reinvocación dentro del entorno virtual si existe
VENV_DIR = Path(__file__).resolve().parent / ".venv"
if VENV_DIR.exists():
    venv_python = VENV_DIR / "bin" / "python"
    try:
        if Path(sys.prefix).resolve() != VENV_DIR.resolve() and venv_python.exists():
            os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    except Exception:
        pass

# Asegurar volcado inmediato de salida en terminal y logs
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)


# Metadatos de autoría y proyecto
__author__ = "Raúl Caro Pastorino (@raupulus)"
__email__ = "public@raupulus.dev"
__website__ = "https://raupulus.dev"

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from typing import Any

# Extensiones de audio / vídeo admitidas
AUDIO_EXTENSIONS = {
    ".mka", ".mkv", ".mp4", ".m4a", ".mp3",
    ".wav", ".aac", ".flac", ".ogg", ".opus", ".webm"
}

# Carga de configuración opcional desde env.py
try:
    import env
except ImportError:
    env = None

DEFAULT_MODEL = getattr(env, "DEFAULT_MODEL", "mlx-community/whisper-large-v3-mlx")
DEFAULT_LANGUAGE = getattr(env, "DEFAULT_LANGUAGE", "es")
DEFAULT_PROMPT = getattr(env, "DEFAULT_PROMPT", None)
DEFAULT_AUDIO_DIR = getattr(env, "AUDIO_DIR", "audios")
DEFAULT_MAX_TRACKS = getattr(env, "MAX_TRACKS", 3)
DEFAULT_SILENCE_THRESHOLD = getattr(env, "HALLUCINATION_SILENCE_THRESHOLD", 2.0)
DEFAULT_USE_SUBDIRS = getattr(env, "USE_OUTPUT_SUBDIRECTORIES", True)
DEFAULT_EXPORT_AUDIOS = getattr(env, "EXPORT_AUDIOS", True)
DEFAULT_BITRATE_CONV = getattr(env, "BITRATE_CONVERSACION", "128k")
DEFAULT_BITRATE_P3 = getattr(env, "BITRATE_PISTA3", "192k")
DEFAULT_COMBINED_CHAT = getattr(env, "GENERATE_COMBINED_CHAT", True)


def format_timestamp(seconds: float) -> str:
    """Convierte segundos a formato HH:MM:SS."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def check_dependencies() -> None:
    """Verifica que ffmpeg y ffprobe estén instalados en el sistema."""
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            sys.exit(f"Error: No se encontró '{tool}' en el sistema. Instálalo con 'brew install ffmpeg'.")


def get_audio_streams(file_path: Path) -> list[dict[str, Any]]:
    """Obtiene información sobre los streams de audio del archivo mediante ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index,codec_name:stream_tags=title",
        "-of", "json",
        str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [!] Error al inspeccionar pistas en {file_path.name}: {result.stderr.strip()}")
        return []
    try:
        data = json.loads(result.stdout)
        return data.get("streams", [])
    except json.JSONDecodeError:
        return []


def extract_audio_stream(input_file: Path, stream_index: int | None, output_wav: Path) -> None:
    """Extrae un stream específico (o el stream principal) a WAV mono de 16kHz."""
    cmd = ["ffmpeg", "-y", "-i", str(input_file)]
    if stream_index is not None:
        cmd.extend(["-map", f"0:a:{stream_index}"])
    else:
        cmd.extend(["-vn"])

    cmd.extend([
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_wav)
    ])

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Error al extraer audio con ffmpeg: {result.stderr.strip()}")


def export_combined_conversation_audio(
    input_file: Path,
    output_mp3: Path,
    bitrate: str = "128k",
    p1_idx: int = 0,
    p2_idx: int = 1
) -> None:
    """Mezcla Pista 1 y Pista 2 en audio mono equilibrado a 128 kbps (archivo histórico).

    Nota técnica: Se suministra el archivo dos veces (-i input -i input) para que ffmpeg
    instancie dos demuxers independientes con punteros de lectura separados. Esto evita
    la terminación prematura por desincronización de paquetes/bloques en archivos Matroska (.mka)
    producidos por OBS en grabaciones largas.
    """
    print(f"  [>] Exportando audio combinado (Pista 1 + 2 a {bitrate} mono)...")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-i", str(input_file),
        "-filter_complex", f"[0:a:{p1_idx}][1:a:{p2_idx}]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[aout]",
        "-map", "[aout]",
        "-ac", "1",
        "-c:a", "libmp3lame",
        "-b:a", bitrate,
        str(output_mp3)
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"  [!] Error al exportar audio combinado: {result.stderr.strip()}")
    else:
        print(f"  [OK] Audio guardado: {output_mp3.name}")


def export_track_audio(input_file: Path, stream_idx: int, output_mp3: Path, bitrate: str = "192k", track_label: str = "Pista 3") -> None:
    """Extrae una pista individual a MP3 con el bitrate indicado."""
    print(f"  [>] Exportando audio de {track_label} (a {bitrate})...")
    cmd = [
        "ffmpeg", "-y", "-i", str(input_file),
        "-map", f"0:a:{stream_idx}",
        "-c:a", "libmp3lame",
        "-b:a", bitrate,
        str(output_mp3)
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"  [!] Error al exportar audio de {track_label}: {result.stderr.strip()}")
    else:
        print(f"  [OK] Audio guardado: {output_mp3.name}")


def parse_markdown_segments(md_file: Path) -> list[dict[str, Any]]:
    """Extrae marcas de tiempo y texto de un archivo .md ya generado para reutilizarlo."""
    segments = []
    if not md_file.exists():
        return segments
    pattern = re.compile(r"\*\*\[(\d{2}):(\d{2}):(\d{2})\s*->\s*(\d{2}):(\d{2}):(\d{2})\]\*\*\s+(.*)")
    with open(md_file, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                h1, m1, s1, h2, m2, s2, text = match.groups()
                start = int(h1) * 3600 + int(m1) * 60 + int(s1)
                end = int(h2) * 3600 + int(m2) * 60 + int(s2)
                segments.append({"start": float(start), "end": float(end), "text": text})
    return segments


def transcribe_wav(
    wav_path: Path,
    model_name: str,
    language: str,
    initial_prompt: str | None = None,
    silence_threshold: float = DEFAULT_SILENCE_THRESHOLD
) -> dict[str, Any]:

    """Transcribe un archivo WAV utilizando mlx_whisper con protección antihalucinación en silencios."""
    try:
        import mlx_whisper
    except ImportError:
        sys.exit(
            "Error: 'mlx-whisper' no está instalado en este entorno.\n"
            "Ejecuta: ./.venv/bin/python -m pip install -r requirements.txt"
        )

    print(f"    -> Ejecutando Whisper ({model_name}) en GPU Metal (antihalucinación activa)...")
    kwargs = {
        "path_or_hf_repo": model_name,
        "language": language,
        "temperature": 0.0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "hallucination_silence_threshold": silence_threshold,
        "verbose": False
    }
    if initial_prompt:
        kwargs["initial_prompt"] = initial_prompt

    result = mlx_whisper.transcribe(str(wav_path), **kwargs)
    return result


def write_markdown_output(
    output_file: Path,
    source_name: str,
    track_info: str,
    segments: list[dict[str, Any]],
    model_name: str
) -> None:
    """Genera el archivo Markdown individual con metadatos y marcas de tiempo."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"# Transcripción: {source_name}",
        "",
        f"- **Archivo original:** `{source_name}`",
        f"- **Detalle:** {track_info}",
        f"- **Fecha:** {now_str}",
        f"- **Modelo utilizado:** `{model_name}`",
        f"- **Idioma:** Español (`es`)",
        "",
        "---",
        "",
        "## Contenido",
        ""
    ]

    if not segments:
        lines.append("*(No se detectó voz o contenido en este audio)*\n")
    else:
        for seg in segments:
            start = format_timestamp(seg.get("start", 0.0))
            end = format_timestamp(seg.get("end", 0.0))
            text = seg.get("text", "").strip()
            if text:
                lines.append(f"**[{start} -> {end}]** {text}\n")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_combined_conversation_markdown(
    output_file: Path,
    source_name: str,
    p1_label: str,
    p1_segments: list[dict[str, Any]],
    p2_label: str,
    p2_segments: list[dict[str, Any]],
    audio_ref: str | None = None
) -> None:
    """Genera la transcripción combinada de las Pistas 1 y 2 entrelazadas en orden cronológico."""
    tagged = []
    for s in p1_segments:
        tagged.append({
            "speaker": "Entrada 1",
            "start": s.get("start", 0.0),
            "end": s.get("end", 0.0),
            "text": s.get("text", "").strip()
        })
    for s in p2_segments:
        tagged.append({
            "speaker": "Entrada 2",
            "start": s.get("start", 0.0),
            "end": s.get("end", 0.0),
            "text": s.get("text", "").strip()
        })

    tagged.sort(key=lambda x: x["start"])
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"# Conversación Combinada: {source_name}",
        "",
        f"- **Archivo original:** `{source_name}`",
        f"- **Pista 1:** {p1_label}",
        f"- **Pista 2:** {p2_label}",
    ]
    if audio_ref:
        lines.append(f"- **Audio de referencia:** `{audio_ref}`")
    lines.extend([
        f"- **Fecha:** {now_str}",
        "",
        "---",
        "",
        "## Diálogo",
        ""
    ])

    if not tagged:
        lines.append("*(No se detectaron intervenciones)*\n")
    else:
        for item in tagged:
            start = format_timestamp(item["start"])
            end = format_timestamp(item["end"])
            spk = item["speaker"]
            txt = item["text"]
            if txt:
                lines.append(f"**[{start} -> {end}] {spk}:** {txt}\n")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] Transcripción combinada guardada: {output_file.name}")


def process_audio_file(
    file_path: Path,
    model_name: str,
    language: str,
    initial_prompt: str | None,
    force: bool,
    max_tracks: int | None = DEFAULT_MAX_TRACKS,
    silence_threshold: float = DEFAULT_SILENCE_THRESHOLD,
    use_subdirs: bool = DEFAULT_USE_SUBDIRS,
    export_audios: bool = DEFAULT_EXPORT_AUDIOS,
    bitrate_conv: str = DEFAULT_BITRATE_CONV,
    bitrate_p3: str = DEFAULT_BITRATE_P3,
    generate_combined_chat: bool = DEFAULT_COMBINED_CHAT
) -> None:
    """Procesa un archivo de audio/vídeo, gestionando pistas individuales si es multipista."""
    print(f"\n[+] Analizando: {file_path.name}")
    streams = get_audio_streams(file_path)

    if not streams:
        print(f"  [-] No se detectaron pistas de audio en {file_path.name}. Omitiendo.")
        return

    num_streams = len(streams)
    parent_dir = file_path.parent
    base_name = file_path.stem

    # Determinar carpeta de salida
    if use_subdirs:
        out_dir = parent_dir / base_name
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = parent_dir

    # Caso 1: Archivo multipista (ej. .mka de OBS con pista de micro, amigos y juego)
    if num_streams > 1:
        if max_tracks and max_tracks > 0 and max_tracks < num_streams:
            streams_to_process = streams[:max_tracks]
            print(f"  [*] Archivo multipista detectado ({num_streams} pistas). Se procesarán las primeras {len(streams_to_process)} pistas (límite: {max_tracks}).")
        else:
            streams_to_process = streams
            print(f"  [*] Archivo multipista detectado ({num_streams} pistas de audio)")

        track_segments = {}
        track_labels = {}

        # 1. Transcribir cada pista individualmente
        for idx, stream_info in enumerate(streams_to_process):
            track_num = idx + 1
            output_file = out_dir / f"{base_name}_pista{track_num}.md"

            stream_title = stream_info.get("tags", {}).get("title") or stream_info.get("tags", {}).get("TITLE")
            if stream_title:
                track_role = f"Pista {track_num}: {stream_title}"
            else:
                track_role = f"Pista {track_num} (Fuente de entrada {track_num})"

            track_labels[track_num] = track_role

            if output_file.exists() and not force:
                print(f"  [=] Pista {track_num} ya transcrita ({output_file.name}). Omitiendo (usa --force para rehacer).")
                continue

            print(f"  [>] Procesando {track_role}...")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                tmp_wav_path = Path(tmp_wav.name)

            try:
                extract_audio_stream(file_path, idx, tmp_wav_path)
                result = transcribe_wav(tmp_wav_path, model_name, language, initial_prompt, silence_threshold)
                segments = result.get("segments", [])
                track_segments[track_num] = segments
                write_markdown_output(
                    output_file=output_file,
                    source_name=file_path.name,
                    track_info=track_role,
                    segments=segments,
                    model_name=model_name
                )
                print(f"  [OK] Guardado: {output_file.name}")
            finally:
                if tmp_wav_path.exists():
                    tmp_wav_path.unlink()

        # 2. Exportar audio combinado de Pistas 1 y 2 (128 kbps mono)
        combined_audio_filename = None
        if export_audios and num_streams >= 2:
            combined_audio_file = out_dir / f"{base_name}_pista1_y_pista2_combinados.mp3"
            combined_audio_filename = combined_audio_file.name
            if combined_audio_file.exists() and not force:
                print(f"  [=] Audio combinado ya existe ({combined_audio_file.name}). Omitiendo.")
            else:
                export_combined_conversation_audio(file_path, combined_audio_file, bitrate=bitrate_conv)

        # 3. Exportar Pista 3 independiente (192 kbps estéreo para edición/clips)
        if export_audios and num_streams >= 3 and (max_tracks is None or max_tracks >= 3):
            pista3_audio_file = out_dir / f"{base_name}_pista3.mp3"
            if pista3_audio_file.exists() and not force:
                print(f"  [=] Audio de Pista 3 ya existe ({pista3_audio_file.name}). Omitiendo.")
            else:
                export_track_audio(file_path, 2, pista3_audio_file, bitrate=bitrate_p3, track_label="Pista 3")

        # 4. Generar Markdown combinado entrelazado (Pista 1 y Pista 2)
        if generate_combined_chat and num_streams >= 2:
            combined_md_file = out_dir / f"{base_name}_pista1_y_pista2_combinados.md"
            if combined_md_file.exists() and not force:
                print(f"  [=] Transcripción combinada ya existe ({combined_md_file.name}). Omitiendo.")
            else:
                # Si los segmentos no estaban en memoria porque se omitió la transcripción, leerlos del .md
                p1_segs = track_segments.get(1) or parse_markdown_segments(out_dir / f"{base_name}_pista1.md")
                p2_segs = track_segments.get(2) or parse_markdown_segments(out_dir / f"{base_name}_pista2.md")
                p1_lbl = track_labels.get(1, "Pista 1 (Fuente de entrada 1)")
                p2_lbl = track_labels.get(2, "Pista 2 (Fuente de entrada 2)")

                write_combined_conversation_markdown(
                    output_file=combined_md_file,
                    source_name=file_path.name,
                    p1_label=p1_lbl,
                    p1_segments=p1_segs,
                    p2_label=p2_lbl,
                    p2_segments=p2_segs,
                    audio_ref=combined_audio_filename
                )

    # Caso 2: Pista única (ej. notas de voz .m4a, audios de WhatsApp/teléfono, mp3)
    else:
        output_file = out_dir / f"{base_name}.md"
        if output_file.exists() and not force:
            print(f"  [=] Audio ya transcrito ({output_file.name}). Omitiendo (usa --force para rehacer).")
            return

        stream_info = streams[0]
        stream_title = stream_info.get("tags", {}).get("title") or stream_info.get("tags", {}).get("TITLE")
        track_role = f"Pista única ({stream_title})" if stream_title else "Pista única"
        print(f"  [>] Procesando {track_role}...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            tmp_wav_path = Path(tmp_wav.name)

        try:
            extract_audio_stream(file_path, None, tmp_wav_path)
            result = transcribe_wav(tmp_wav_path, model_name, language, initial_prompt, silence_threshold)
            write_markdown_output(
                output_file=output_file,
                source_name=file_path.name,
                track_info=track_role,
                segments=result.get("segments", []),
                model_name=model_name
            )
            print(f"  [OK] Guardado: {output_file.name}")
        finally:
            if tmp_wav_path.exists():
                tmp_wav_path.unlink()


def main() -> None:
    check_dependencies()

    parser = argparse.ArgumentParser(
        description="Transcripción local optimizada para Apple Silicon (MacBook M1 Pro)."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_AUDIO_DIR,
        help=f"Ruta a una carpeta con audios o a un archivo específico (por defecto: '{DEFAULT_AUDIO_DIR}')"
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"Modelo de MLX-Whisper a utilizar (por defecto: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--language", "-l",
        default=DEFAULT_LANGUAGE,
        help=f"Código de idioma (por defecto: {DEFAULT_LANGUAGE})"
    )
    parser.add_argument(
        "--prompt", "-p",
        default=DEFAULT_PROMPT,
        help="Prompt inicial para guiar el estilo y puntuación"
    )
    parser.add_argument(
        "--max-tracks", "-t",
        type=int,
        default=DEFAULT_MAX_TRACKS,
        help=f"Número máximo de pistas a procesar por archivo (por defecto: {DEFAULT_MAX_TRACKS or 'todas'})"
    )
    parser.add_argument(
        "--silence-threshold",
        type=float,
        default=DEFAULT_SILENCE_THRESHOLD,
        help=f"Umbral en segundos para descartar alucinaciones en silencio (por defecto: {DEFAULT_SILENCE_THRESHOLD}s)"
    )
    parser.add_argument(
        "--no-export-audios",
        action="store_true",
        help="Desactiva la exportación de pistas de audio MP3"
    )
    parser.add_argument(
        "--no-combined-chat",
        action="store_true",
        help="Desactiva la generación del markdown combinado de pistas 1 y 2"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Fuerza la re-transcripción y re-exportación aunque ya existan los archivos"
    )

    args = parser.parse_args()
    target_path = Path(args.path)

    if not target_path.exists():
        sys.exit(f"Error: La ruta especificada no existe: {target_path}")

    max_tracks_str = str(args.max_tracks) if args.max_tracks else "Todas"
    export_audios = not args.no_export_audios if args.no_export_audios else DEFAULT_EXPORT_AUDIOS
    combined_chat = not args.no_combined_chat if args.no_combined_chat else DEFAULT_COMBINED_CHAT

    print("=" * 65)
    print("  WHISPER LOCAL - Apple Silicon Metal Edition")
    print(f"  Modelo:           {args.model}")
    print(f"  Idioma:           {args.language}")
    print(f"  Max Pistas:       {max_tracks_str}")
    print(f"  Exportar Audios:  {export_audios}")
    print(f"  Chat Combinado:   {combined_chat}")
    print(f"  Objetivo:         {target_path}")
    print("=" * 65)

    if target_path.is_file():
        if target_path.suffix.lower() in AUDIO_EXTENSIONS:
            process_audio_file(
                file_path=target_path,
                model_name=args.model,
                language=args.language,
                initial_prompt=args.prompt,
                force=args.force,
                max_tracks=args.max_tracks,
                silence_threshold=args.silence_threshold,
                use_subdirs=DEFAULT_USE_SUBDIRS,
                export_audios=export_audios,
                bitrate_conv=DEFAULT_BITRATE_CONV,
                bitrate_p3=DEFAULT_BITRATE_P3,
                generate_combined_chat=combined_chat
            )
        else:
            sys.exit(f"Error: La extensión '{target_path.suffix}' no es compatible.")
    else:
        # Explorar directorio (solo archivos regulares, ignorando subdirectorios de salidas ya creadas)
        audio_files = sorted([
            p for p in target_path.iterdir()
            if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
        ])

        if not audio_files:
            print(f"\nNo se encontraron archivos de audio compatibles en '{target_path}'.")
            print(f"Extensiones soportadas: {', '.join(sorted(AUDIO_EXTENSIONS))}")
            return

        print(f"\nEncontrados {len(audio_files)} archivo(s) para procesar.")
        for audio_file in audio_files:
            process_audio_file(
                file_path=audio_file,
                model_name=args.model,
                language=args.language,
                initial_prompt=args.prompt,
                force=args.force,
                max_tracks=args.max_tracks,
                silence_threshold=args.silence_threshold,
                use_subdirs=DEFAULT_USE_SUBDIRS,
                export_audios=export_audios,
                bitrate_conv=DEFAULT_BITRATE_CONV,
                bitrate_p3=DEFAULT_BITRATE_P3,
                generate_combined_chat=combined_chat
            )

    print("\n[✓] Proceso completado.")


if __name__ == "__main__":
    main()
