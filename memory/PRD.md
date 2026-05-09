# TranscribeThat — PRD

## Problem Statement
Aplicación web "TranscribeThat" para creadores de contenido: subir vídeos verticales (Reels, TikToks, Shorts), transcribir con IA, editar texto, personalizar estilo de subtítulos y exportar MP4 con subtítulos hardcoded.

## Stack
- **Frontend/Backend**: Python + Streamlit (3-column dark UI, accent #8A2BE2)
- **AI Transcripción**: OpenAI Whisper-1 vía Emergent LLM Key (sin RAM, sin coste para el usuario)
- **Render**: FFmpeg (`-preset ultrafast`, `-crf 24`, `-threads 2`) con `-filter_script:v filtro.txt` → `ass=filename=subs.ass`
- **Subtítulos**: Advanced SubStation Alpha (.ass) generado dinámicamente

## User Persona
Creadores de contenido vertical (Reels/TikTok/Shorts) que quieren subtítulos rápidos, estéticos y editables.

## Core Requirements (estáticas)
1. Subida de mp4/mov/mkv/webm
2. Transcripción precisa con timestamps a nivel de palabra (`timestamp_granularities=["word"]`)
3. Bloques cortos elegibles: 2 / 3 / 4 palabras por subtítulo
4. Editor: text inputs + tiempos start/end por bloque
5. Estilo: tipografía, tamaño 24-120, color, fondo (transparente / caja negra / personalizado), posición (Arriba/Centro/Abajo con margen 350px), alineación, contorno, sombra
6. Render hardcoded vía FFmpeg listo para descargar
7. Compatible con Streamlit Community Cloud (1GB RAM) y Emergent preview

## Implemented (2026-01)
- ✅ UI premium dark (gradiente #0E1117 / #161B22, accent #8A2BE2, fuente Inter + JetBrains Mono)
- ✅ 3 columnas: Input/Transcripción · Editor · Estilo/Render
- ✅ Pipeline FFmpeg: extract_audio (mono 16kHz mp3) → transcribe → group → ASS → render
- ✅ Detección automática de FFmpeg (rutas macOS local + global)
- ✅ Flags memory-safe (`-threads 2 -preset ultrafast -crf 24`)
- ✅ Workaround `-filter_script:v filtro.txt` (evita parseo erróneo de ass=)
- ✅ Conversión Hex → ASS BGR (`&HAABBGGRR`)
- ✅ 9 alineaciones (3 verticales × 3 horizontales) + MarginV 350px para Arriba/Abajo
- ✅ BorderStyle: 1 (transparente con outline+shadow) / 3 (caja opaca color personalizable)
- ✅ Reagrupar bloques sin re-transcribir (cambia el N de palabras)
- ✅ Selector de idioma (auto + 8 idiomas) para mayor precisión
- ✅ Barra de progreso real durante render (parsea time= de FFmpeg stderr)
- ✅ Preview del MP4 final + botón de descarga
- ✅ Despliegue dual: corre en Emergent preview (port 3000 vía supervisor/yarn) + Streamlit Community Cloud (`streamlit_app.py` en root, `requirements.txt`, `packages.txt` con ffmpeg, `.streamlit/config.toml`)

## Backlog (P1)
- Preview en vivo del subtítulo sobre frame del vídeo (canvas/ffmpeg thumbnail)
- Traducción automática de subtítulos (multi-idioma con LLM)
- Exportar SRT/VTT además del MP4
- Animaciones de palabra-por-palabra (karaoke-style)

## Backlog (P2)
- Detección automática de pausas para split inteligente (no solo por N palabras)
- Templates de estilo guardables (presets)
- Watermark opcional + branding personalizado

## Architecture Notes
- En Emergent preview, supervisor ejecuta `yarn start` → `package.json` → `streamlit run /app/streamlit_app.py --server.port 3000` (reemplaza el frontend React).
- En Streamlit Community Cloud, el archivo `/app/streamlit_app.py` es el entry point estándar; `packages.txt` instala ffmpeg, `requirements.txt` instala las deps.
- Whisper API es free para el usuario (Emergent LLM Key), no consume RAM local del contenedor.
