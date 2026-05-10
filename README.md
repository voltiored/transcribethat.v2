# 🎬 TranscribeThat — 100% gratis

Subtítulos automáticos para Reels, TikTok & Shorts.
Sube vídeo → IA transcribe → edita → personaliza estilo → descarga MP4.

## ✨ Funcionalidades

- 🆓 **100% gratis por defecto**: `faster-whisper` corre localmente (sin API, sin coste)
- 🚀 **OpenAI BYOK opcional**: si pegas tu key, usa Whisper-1 + GPT-4o-mini (más rápido / mejor calidad)
- 🎨 **9 presets virales**: MrBeast, Captions, Hormozi Karaoke, Storytelling, Educativo, Comedy, Cinema, TikTok Pop, Karaoke Pink
- 🎤 **Animación karaoke** (palabra-por-palabra resaltada)
- 👁️ **Vista previa en vivo** del estilo aplicado
- 🌐 **Traducción a 11 idiomas** (Google Translate gratis o GPT-4o-mini si tienes key)
- 💧 **Marca de agua** personalizable (texto, posición, color, opacidad)
- 🧠 **Split inteligente** (corta bloques en pausas + puntuación)
- 📤 **Export MP4 / SRT / VTT**

## Stack técnico
- **Streamlit** (UI dark premium)
- **faster-whisper** (CTranslate2) — transcripción local CPU
- **deep-translator** (Google Translate sin key)
- **openai** (opcional, solo si usuario pega su key)
- **FFmpeg** (`-preset ultrafast -crf 24 -threads 2`)
- **Advanced SubStation Alpha (.ass)** generado dinámicamente

## 🚀 Ejecutar localmente
```bash
pip install -r requirements.txt
# Asegúrate de tener ffmpeg en el PATH (mac: brew install ffmpeg)
streamlit run streamlit_app.py
```

No necesitas ninguna API key. Listo.

## ☁️ Desplegar en Streamlit Community Cloud
1. Push del repo a GitHub.
2. En [share.streamlit.io](https://share.streamlit.io) → "New app" → apunta a `streamlit_app.py`.
3. **No necesitas configurar Secrets** — la app funciona sin ninguna key.
4. `packages.txt` instala ffmpeg automáticamente.
5. Recomendado: empieza con modelo `base` (cabe en 1 GB RAM con holgura).

### Si quieres que tu app sea privada (solo tú)
En Streamlit Cloud → Settings → Sharing → "Only specific people". Así no entra cualquiera.

## 💰 Modos de uso

| Modo | Coste | Calidad | Velocidad | Cómo activar |
|---|---|---|---|---|
| **Gratis** | 0 € | Buena (`base`) | Media | Por defecto |
| **OpenAI BYOK** | Lo paga el usuario | Excelente | Rápida | Pegar key en UI |

## 🛠 Reglas críticas implementadas (FFmpeg)
- ✅ Memoria RAM (`-threads 2 -preset ultrafast -crf 24`) → no colapsa servidor 1 GB
- ✅ Rutas FFmpeg con fallback (Mac local + cloud Linux)
- ✅ Filtro ASS pasado vía `-filter_script:v filtro.txt`
- ✅ Conversión Hex → ASS BGR `&HAABBGGRR`
- ✅ Posición Arriba/Abajo con margen real de 350 px
