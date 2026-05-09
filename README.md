# 🎬 TranscribeThat

Subtítulos automáticos para Reels, TikToks & Shorts. Sube vídeo → IA transcribe → edita → personaliza estilo → descarga MP4.

## Stack
- **Streamlit** (UI dark premium con CSS personalizado)
- **OpenAI Whisper-1 API** (vía Emergent LLM Key — sin RAM, gratis)
- **FFmpeg** (render con `-preset ultrafast -crf 24 -threads 2`)
- **Advanced SubStation Alpha (.ass)** generado dinámicamente

## Ejecutar localmente
```bash
pip install -r requirements.txt
# Asegúrate de tener ffmpeg en el PATH (mac: brew install ffmpeg)
export EMERGENT_LLM_KEY=sk-emergent-XXXX
streamlit run streamlit_app.py
```

## Desplegar en Streamlit Community Cloud
1. Pushea este repo a GitHub.
2. En [share.streamlit.io](https://share.streamlit.io) crea una nueva app apuntando a `streamlit_app.py`.
3. En **Secrets**, añade:
   ```toml
   EMERGENT_LLM_KEY = "sk-emergent-XXXX"
   ```
4. ¡Listo! `packages.txt` instala ffmpeg automáticamente.

## Reglas críticas implementadas
- ✅ Memoria RAM (`-threads 2 -preset ultrafast -crf 24`) → no colapsa el servidor de 1GB
- ✅ Rutas FFmpeg con fallback (Mac local + cloud Linux)
- ✅ Filtro ASS pasado vía `-filter_script:v filtro.txt` (evita errores de parseo)
- ✅ Conversión Hex → ASS BGR `&HAABBGGRR`
- ✅ Posición Arriba/Abajo con margen real de 350 px
