"""
TranscribeThat — Streamlit + faster-whisper (local, free) / OpenAI Whisper API (BYOK) + FFmpeg
Optimized for Streamlit Community Cloud (1GB RAM) and Emergent preview.

Default: 100% FREE (faster-whisper local + Google Translate via deep-translator).
Optional: user pastes their OpenAI key → uses Whisper-1 API + GPT-4o-mini for higher quality.
"""
import os
import re
import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Tuple

import streamlit as st
from dotenv import load_dotenv

# Load env (Emergent path first, then root) — only used as last-resort fallback
for env_path in [Path(__file__).parent / "backend" / ".env",
                 Path(__file__).parent / ".env"]:
    if env_path.exists():
        load_dotenv(env_path)
        break

# ──────────────────────────────────────────────────────────────────────────────
#  PAGE CONFIG + CUSTOM DARK THEME
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TranscribeThat — Subtítulos AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
    --bg-0: #0E1117; --bg-1: #161B22; --bg-2: #1C2230;
    --border: #2A3140; --text: #E6EDF3; --text-dim: #8B949E;
    --accent: #8A2BE2; --accent-hov: #9D4BFF; --accent-soft: rgba(138, 43, 226, 0.12);
    --success: #2EA043; --danger: #F85149;
}

html, body, [class*="css"], .stApp {
    background: var(--bg-0) !important;
    color: var(--text) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}
.block-container { padding-top: 1.5rem !important; padding-bottom: 4rem !important; max-width: 1500px !important; }

.tt-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 22px 28px; margin-bottom: 28px;
    background: linear-gradient(135deg, #161B22 0%, #1A1230 100%);
    border: 1px solid var(--border); border-radius: 18px;
    position: relative; overflow: hidden;
}
.tt-header::before {
    content: ''; position: absolute; top: -40%; right: -10%;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(138,43,226,0.35) 0%, transparent 70%);
    filter: blur(20px);
}
.tt-logo { display: flex; align-items: center; gap: 14px; z-index: 1; }
.tt-logo-mark {
    width: 44px; height: 44px; border-radius: 12px;
    background: linear-gradient(135deg, var(--accent) 0%, #4A1A8A 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 22px; font-weight: 800; color: white;
    box-shadow: 0 6px 20px rgba(138,43,226,0.4);
}
.tt-title { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; color: var(--text); margin: 0; }
.tt-subtitle { font-size: 13px; color: var(--text-dim); margin: 0; }
.tt-badge {
    z-index: 1; padding: 6px 14px; border-radius: 100px;
    background: var(--accent-soft); border: 1px solid var(--accent);
    color: var(--accent-hov); font-size: 12px; font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}

.tt-card-title {
    font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: var(--text-dim);
    margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
}
.tt-card-title::before {
    content: ''; width: 14px; height: 2px; background: var(--accent); border-radius: 2px;
}
.tt-step {
    display: inline-block; width: 22px; height: 22px; border-radius: 6px;
    background: var(--accent); color: white; font-size: 12px; font-weight: 700;
    text-align: center; line-height: 22px; margin-right: 8px;
}

.tt-card {
    background: var(--bg-1); border: 1px solid var(--border);
    border-radius: 16px; padding: 22px; margin-bottom: 18px;
}

.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stSelectbox > div > div, [data-baseweb="select"] > div {
    background: var(--bg-2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 10px !important;
}
.stTextArea textarea { font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }
label, .stSelectbox label, .stTextInput label, .stTextArea label, .stNumberInput label,
.stSlider label, .stColorPicker label, .stRadio label, .stFileUploader label {
    color: var(--text) !important; font-weight: 600 !important; font-size: 13px !important;
}

.stSlider [role="slider"] { background: var(--accent) !important; border-color: var(--accent) !important; }
.stSlider > div > div > div > div { background: var(--accent) !important; }

.stRadio > div { gap: 6px !important; }
.stRadio label { padding: 8px 14px !important; border-radius: 10px !important;
    background: var(--bg-2) !important; border: 1px solid var(--border) !important;
    cursor: pointer !important; transition: all 0.15s ease !important; }
.stRadio label:hover { border-color: var(--accent) !important; }

.stButton > button, .stDownloadButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, #6A1FB8 100%) !important;
    color: white !important; border: none !important;
    padding: 12px 22px !important; border-radius: 10px !important;
    font-weight: 700 !important; font-size: 14px !important;
    letter-spacing: 0.3px !important;
    box-shadow: 0 4px 14px rgba(138,43,226,0.3) !important;
    transition: transform 0.12s ease, box-shadow 0.12s ease !important;
    width: 100%;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(138,43,226,0.45) !important;
}
.stButton > button[kind="secondary"] {
    background: var(--bg-2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    box-shadow: none !important;
}

[data-testid="stFileUploader"] section {
    background: var(--bg-2) !important;
    border: 2px dashed var(--border) !important;
    border-radius: 12px !important; padding: 24px !important;
    transition: all 0.15s ease;
}
[data-testid="stFileUploader"] section:hover { border-color: var(--accent) !important; }
[data-testid="stFileUploader"] section button {
    background: var(--accent) !important; color: white !important; border: none !important;
}

.stColorPicker > div > div { background: var(--bg-2) !important; border: 1px solid var(--border) !important; border-radius: 10px !important; }

.streamlit-expanderHeader, [data-testid="stExpander"] details summary {
    background: var(--bg-2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important; color: var(--text) !important;
    font-weight: 600 !important;
}

/* Cajitas — bordered containers wrapping label + control */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--bg-1) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 12px 14px !important;
    margin-bottom: 12px !important;
    transition: border-color 0.15s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(138, 43, 226, 0.35) !important;
}
.tt-cajita-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 10px;
    display: flex; align-items: center; gap: 8px;
}
.tt-cajita-label::before {
    content: ''; width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 8px rgba(138, 43, 226, 0.6);
}

/* Centered preview frame */
.tt-preview-wrap {
    display: flex; flex-direction: column; align-items: center;
    background: var(--bg-1);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 18px;
    position: relative;
    overflow: hidden;
}
.tt-preview-wrap::before {
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(circle at 50% 0%, rgba(138,43,226,0.08), transparent 60%);
    pointer-events: none;
}
.tt-preview-empty {
    width: 100%; min-height: 360px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: linear-gradient(180deg, var(--bg-2) 0%, var(--bg-0) 100%);
    border: 2px dashed var(--border);
    border-radius: 12px;
    color: var(--text-dim);
    text-align: center; padding: 30px;
    z-index: 1;
}
.tt-preview-empty-icon {
    font-size: 44px; margin-bottom: 14px; opacity: 0.7;
}
.tt-preview-empty-title {
    font-size: 16px; font-weight: 700; color: var(--text); margin-bottom: 6px;
}

.tt-time { font-family: 'JetBrains Mono', monospace; font-size: 11px;
    color: var(--accent-hov); font-weight: 600; }

.tt-preset-grid {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 14px;
}

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
[data-testid="stToolbar"] { display: none !important; }

.stProgress > div > div > div { background: var(--accent) !important; }
.stProgress > div > div { background: var(--bg-2) !important; }

.stAlert { background: var(--bg-2) !important; border: 1px solid var(--border) !important;
    border-radius: 10px !important; color: var(--text) !important; }

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-0); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

.tt-export-row { display: flex; gap: 8px; margin-top: 10px; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown("""
<div class="tt-header">
    <div class="tt-logo">
        <div class="tt-logo-mark">TT</div>
        <div>
            <p class="tt-title">TranscribeThat</p>
            <p class="tt-subtitle">Subtítulos automáticos · 100% gratis · Karaoke · Traducción · Presets virales</p>
        </div>
    </div>
    <div class="tt-badge" id="engine-badge">{ENGINE_BADGE}</div>
</div>
""".replace("{ENGINE_BADGE}", "OpenAI · whisper-1" if st.session_state.get("user_openai_key") else "faster-whisper · local · free"), unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────────────────────
FFMPEG_CANDIDATES = ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg", "ffmpeg"]
FFPROBE_CANDIDATES = ["/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe", "/usr/bin/ffprobe", "ffprobe"]


def find_binary(candidates: List[str]) -> str:
    for path in candidates:
        if path == os.path.basename(path):
            found = shutil.which(path)
            if found:
                return found
        elif os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return candidates[-1]


FFMPEG = find_binary(FFMPEG_CANDIDATES)
FFPROBE = find_binary(FFPROBE_CANDIDATES)


def hex_to_ass_color(hex_color: str, alpha: str = "00") -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha}{b}{g}{r}".upper()


def seconds_to_ass_time(t: float) -> str:
    if t < 0:
        t = 0
    hours = int(t // 3600)
    minutes = int((t % 3600) // 60)
    seconds = t % 60
    return f"{hours}:{minutes:02d}:{seconds:05.2f}"


def seconds_to_srt_time(t: float) -> str:
    if t < 0:
        t = 0
    hours = int(t // 3600)
    minutes = int((t % 3600) // 60)
    seconds = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def seconds_to_vtt_time(t: float) -> str:
    return seconds_to_srt_time(t).replace(",", ".")


def extract_audio(video_path: str, audio_path: str) -> bool:
    cmd = [FFMPEG, "-y", "-i", video_path, "-vn",
           "-ac", "1", "-ar", "16000", "-b:a", "64k", audio_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0


def get_video_duration(video_path: str) -> float:
    cmd = [FFPROBE, "-v", "quiet", "-print_format", "csv=p=0",
           "-show_entries", "format=duration", video_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def get_video_dimensions(video_path: str) -> Tuple[int, int]:
    cmd = [FFPROBE, "-v", "quiet", "-print_format", "csv=p=0",
           "-show_entries", "stream=width,height", "-select_streams", "v:0", video_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        w, h = res.stdout.strip().split(",")
        return int(w), int(h)
    except Exception:
        return 1080, 1920


async def transcribe_with_api(audio_path: str, language: str = None,
                              api_key: str = None) -> List[Dict]:
    """[Legacy compatibility wrapper] Whisper-1 via OpenAI direct API."""
    return transcribe_openai(audio_path, language, api_key)


def transcribe_openai(audio_path: str, language: str = None, api_key: str = None) -> List[Dict]:
    """Transcribe via OpenAI Whisper-1 API (requires user-provided key)."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    kwargs = {
        "model": "whisper-1",
        "response_format": "verbose_json",
        "timestamp_granularities": ["word"],
        "temperature": 0.0,
    }
    if language and language != "auto":
        kwargs["language"] = language
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(file=f, **kwargs)

    words = []
    raw_words = getattr(response, "words", None) or []
    for w in raw_words:
        words.append({
            "word": (getattr(w, "word", None) or w.get("word", "")).strip(),
            "start": float(getattr(w, "start", None) or w.get("start", 0.0)),
            "end": float(getattr(w, "end", None) or w.get("end", 0.0)),
        })
    if not words:
        # Fallback: segment-level → distribute timings
        segs = getattr(response, "segments", None) or []
        for s in segs:
            text = (getattr(s, "text", None) or s.get("text", "")).strip()
            start = float(getattr(s, "start", None) or s.get("start", 0.0))
            end = float(getattr(s, "end", None) or s.get("end", start + 1))
            tokens = text.split()
            if not tokens:
                continue
            dur = (end - start) / len(tokens)
            for i, tok in enumerate(tokens):
                words.append({"word": tok, "start": start + i * dur, "end": start + (i + 1) * dur})
    return words


@st.cache_resource(show_spinner=False)
def _load_whisper_local(model_size: str):
    """Lazy-load and cache faster-whisper model."""
    from faster_whisper import WhisperModel
    return WhisperModel(model_size, device="cpu", compute_type="int8")


def transcribe_local(audio_path: str, language: str = None,
                     model_size: str = "base") -> List[Dict]:
    """Transcribe locally with faster-whisper. 100% free, runs on CPU."""
    model = _load_whisper_local(model_size)
    lang = language if language and language != "auto" else None
    segments, _info = model.transcribe(
        audio_path,
        language=lang,
        word_timestamps=True,
        vad_filter=True,
        beam_size=1,
    )
    words = []
    for seg in segments:
        if not getattr(seg, "words", None):
            # Fallback: synthesize word timings
            text = (seg.text or "").strip()
            tokens = text.split()
            if not tokens:
                continue
            dur = (seg.end - seg.start) / len(tokens)
            for i, tok in enumerate(tokens):
                words.append({"word": tok, "start": seg.start + i * dur,
                              "end": seg.start + (i + 1) * dur})
        else:
            for w in seg.words:
                token = (w.word or "").strip()
                if not token:
                    continue
                words.append({"word": token, "start": float(w.start), "end": float(w.end)})
    return words


def group_words_into_blocks(words: List[Dict], n: int) -> List[Dict]:
    blocks = []
    for i in range(0, len(words), n):
        chunk = words[i:i + n]
        if not chunk:
            continue
        text = " ".join(w["word"] for w in chunk).strip()
        if not text:
            continue
        blocks.append({
            "id": str(uuid.uuid4())[:8],
            "start": chunk[0]["start"],
            "end": chunk[-1]["end"],
            "text": text,
            "words": [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in chunk],
        })
    return blocks


def group_words_smart(words: List[Dict], max_per_block: int = 4,
                     pause_threshold: float = 0.35) -> List[Dict]:
    """Smart splitter: breaks on pauses (>threshold), strong punctuation, or max length.

    More natural pacing than fixed-N chunks: speaker pauses → new block.
    """
    blocks: List[Dict] = []
    current: List[Dict] = []
    for i, w in enumerate(words):
        current.append(w)
        next_w = words[i + 1] if i + 1 < len(words) else None
        gap = (next_w["start"] - w["end"]) if next_w else 999
        token = w["word"].strip()
        ends_strong = bool(token) and token[-1] in ".!?"
        ends_soft = bool(token) and token[-1] in ",;:"
        should_split = (
            len(current) >= max_per_block
            or next_w is None
            or gap >= pause_threshold
            or (ends_strong and len(current) >= 1)
            or (ends_soft and len(current) >= 2)
        )
        if should_split and current:
            text = " ".join(x["word"] for x in current).strip()
            if text:
                blocks.append({
                    "id": str(uuid.uuid4())[:8],
                    "start": current[0]["start"],
                    "end": current[-1]["end"],
                    "text": text,
                    "words": [{"word": x["word"], "start": x["start"], "end": x["end"]}
                              for x in current],
                })
            current = []
    return blocks


async def translate_blocks(blocks: List[Dict], target_lang_name: str,
                           api_key: str = None) -> List[Dict]:
    """[Legacy wrapper] Dispatches to OpenAI (BYOK) or Google Translate (free)."""
    return translate_blocks_dispatch(blocks, target_lang_name, api_key)


# Map verbose language → Google Translate code (deep-translator uses ISO codes)
GTRANS_LANG_MAP = {
    "English": "en", "Spanish": "es", "Portuguese (Brazilian)": "pt",
    "French": "fr", "German": "de", "Italian": "it",
    "Japanese": "ja", "Chinese (Simplified)": "zh-CN",
    "Korean": "ko", "Hindi": "hi", "Arabic": "ar",
}


def translate_blocks_google(blocks: List[Dict], target_lang_name: str) -> List[Dict]:
    """Free, no-key translation via deep-translator (Google Translate web)."""
    from deep_translator import GoogleTranslator
    code = GTRANS_LANG_MAP.get(target_lang_name, "en")
    translator = GoogleTranslator(source="auto", target=code)
    src_texts = [b["text"] for b in blocks]
    try:
        translated = translator.translate_batch(src_texts)
    except Exception:
        # Fallback per-line if batch fails (rate limit, etc.)
        translated = [translator.translate(t) or t for t in src_texts]
    return _redistribute_timings(blocks, [str(t).strip() if t else b["text"]
                                          for t, b in zip(translated, blocks)])


def translate_blocks_openai(blocks: List[Dict], target_lang_name: str,
                            api_key: str) -> List[Dict]:
    """High-quality translation via user-provided OpenAI key (gpt-4o-mini)."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    src_texts = [b["text"] for b in blocks]
    payload = json.dumps(src_texts, ensure_ascii=False)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role": "system",
             "content": (f"You are a professional subtitle translator. Translate to {target_lang_name}. "
                         "Keep translations short and punchy (these are short-video subtitles). "
                         "Return ONLY a valid JSON array of strings, same length as input, no extra text.")},
            {"role": "user",
             "content": f"Translate this JSON array of subtitle lines:\n{payload}"},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    m = re.search(r"\[[\s\S]*\]", raw)
    if not m:
        raise ValueError(f"No JSON array found: {raw[:200]}")
    arr = json.loads(m.group(0))
    if len(arr) != len(blocks):
        arr = (arr + src_texts)[:len(blocks)]
    return _redistribute_timings(blocks, [str(x).strip() for x in arr])


def translate_blocks_dispatch(blocks: List[Dict], target_lang_name: str,
                              api_key: str = None) -> List[Dict]:
    """Dispatcher: use OpenAI if key provided, else Google Translate (free)."""
    if api_key:
        return translate_blocks_openai(blocks, target_lang_name, api_key)
    return translate_blocks_google(blocks, target_lang_name)


def _redistribute_timings(blocks: List[Dict], new_texts: List[str]) -> List[Dict]:
    """Given new translated texts, redistribute word timings proportionally."""
    out = []
    for b, new_text in zip(blocks, new_texts):
        new_text = new_text or b["text"]
        toks = new_text.split() or [new_text]
        dur = max(0.001, b["end"] - b["start"])
        per = dur / len(toks)
        new_words = [{"word": t, "start": b["start"] + i * per, "end": b["start"] + (i + 1) * per}
                     for i, t in enumerate(toks)]
        out.append({**b, "text": new_text, "words": new_words})
    return out


# ──────────────────────────────────────────────────────────────────────────────
#  EMPHASIS DETECTION (Hormozi PRO style: highlight key words bigger + colored)
# ──────────────────────────────────────────────────────────────────────────────
# Multilingual hardcoded "impact words" used as FREE fallback when no Claude key
IMPACT_WORDS = {
    # ES
    "dinero", "secreto", "verdad", "nunca", "siempre", "importante", "increíble",
    "brutal", "millones", "millón", "mejor", "peor", "perfecto", "imposible",
    "gratis", "ahora", "rápido", "fácil", "garantizado", "exclusivo", "secretos",
    "trampa", "truco", "trucos", "error", "errores", "fracaso", "éxito", "ganar",
    "perder", "increible", "loco", "viral", "épico",
    # EN
    "money", "secret", "secrets", "truth", "never", "always", "important", "amazing",
    "incredible", "millions", "million", "best", "worst", "perfect", "impossible",
    "free", "now", "fast", "easy", "guaranteed", "exclusive", "trick", "tricks",
    "hack", "hacks", "mistake", "mistakes", "failure", "success", "win", "lose",
    "insane", "crazy", "viral", "epic", "shocking", "exposed", "revealed",
    # PT
    "dinheiro", "segredo", "verdade", "nunca", "sempre", "importante", "incrível",
    "milhões", "melhor", "pior", "perfeito", "grátis", "agora", "rápido", "fácil",
    # FR
    "argent", "secret", "vérité", "jamais", "toujours", "important", "incroyable",
    "millions", "meilleur", "pire", "parfait", "gratuit", "maintenant",
}

# Long-but-meaningless words to exclude from "long word" detection
STOPWORDS_LONG = {
    # ES
    "porque", "cuando", "donde", "todos", "todas", "siendo", "estaba", "estuvo",
    "estado", "tenemos", "tenían", "habían", "tienes", "nuestra", "nuestro",
    "vosotros", "ustedes", "después", "antes", "durante", "mediante", "respecto",
    "aunque", "mientras", "entonces", "también", "tampoco", "siguiente", "anterior",
    # EN
    "because", "should", "would", "could", "people", "really", "actually",
    "everyone", "anything", "something", "without", "between", "through",
    "another", "around", "before", "however", "itself", "themselves", "whatever",
    "whenever", "wherever", "different", "anyway", "literally", "basically",
    # PT
    "porque", "quando", "depois", "antes", "durante", "mediante", "embora",
    # FR
    "parce", "lorsque", "pendant", "puisque", "toutefois", "cependant",
}


def detect_emphasis_free(blocks: List[Dict],
                        target_ratio: float = 0.15,
                        min_distance: int = 3,
                        long_word_min_len: int = 7) -> List[Dict]:
    """Free emphasis detection (no API key required).

    Strategy:
      • Score every word: IMPACT_WORDS = 100, numbers = 80, long words = 50.
      • Pick top ~15% of words by priority (rounded UP for short text).
      • Enforce minimum distance (default 3 words apart) so emphasis is spread,
        not clustered → "de vez en cuando" effect.
    """
    import string
    import math

    # Flatten all words
    all_words = []
    for b in blocks:
        for w in b.get("words", []):
            w["is_emphasis"] = False  # reset
            all_words.append(w)

    if not all_words:
        return blocks

    PUNCT = string.punctuation + "¿¡«»…—–“”"
    candidates = []  # (priority, index)
    for idx, w in enumerate(all_words):
        token = w["word"]
        clean = token.lower().strip(PUNCT)
        priority = 0
        # Top priority: hand-curated impact words
        if clean in IMPACT_WORDS:
            priority = 100
        # High priority: contains digits (numbers, $100, 5x, etc.)
        elif any(c.isdigit() for c in token):
            priority = 80
        # Medium priority: long words that aren't stopwords
        elif len(clean) >= long_word_min_len and clean not in STOPWORDS_LONG:
            priority = 50
        # Bonus: ALL CAPS words (likely emphasis already)
        if token.isupper() and len(clean) > 2:
            priority = max(priority, 70)
        if priority > 0:
            candidates.append((priority, idx))

    # Sort by priority desc, then by position (stable for ties)
    candidates.sort(key=lambda x: (-x[0], x[1]))

    # Pick with distance constraint
    target = max(1, math.ceil(len(all_words) * target_ratio))
    selected = set()
    for _prio, idx in candidates:
        if len(selected) >= target:
            break
        if any(abs(idx - s) < min_distance for s in selected):
            continue
        selected.add(idx)

    # Apply emphasis flags
    for idx in selected:
        all_words[idx]["is_emphasis"] = True

    return blocks


def detect_emphasis_claude(blocks: List[Dict], api_key: str,
                           model: str = "claude-haiku-4-5") -> List[Dict]:
    """Use Claude to identify the 3-5 most impactful words across the whole script.

    Returns blocks with words[i].is_emphasis = True for chosen words.
    """
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    # Build a flat numbered list of all words: "[0] Hello [1] this [2] is..."
    numbered = []
    flat_words = []
    idx = 0
    for b in blocks:
        for w in b.get("words", []):
            numbered.append(f"[{idx}] {w['word']}")
            flat_words.append((b, w))
            idx += 1

    if not flat_words:
        return blocks

    target_n = max(3, min(8, len(flat_words) // 8))  # ~12% of words emphasized

    prompt = (
        "You are a viral video editor. Below is a transcript of a short video, "
        "with each word numbered. Your job: pick the "
        f"{target_n} MOST IMPACTFUL words to visually emphasize "
        "(money, surprise, key claims, emotional peaks, numbers, names of products/people). "
        "These will be highlighted bigger and in a different color in the subtitles, Hormozi-style.\n\n"
        "RULES:\n"
        "- Pick standalone impactful words ONLY (nouns, verbs, adjectives — never articles or prepositions)\n"
        "- Spread them across the video (not all clustered together)\n"
        "- Return ONLY a JSON array of integer indices. No explanation.\n\n"
        f"TRANSCRIPT:\n{' '.join(numbered)}\n\n"
        "JSON array of indices to emphasize:"
    )

    msg = client.messages.create(
        model=model,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    m = re.search(r"\[[\s\S]*?\]", raw)
    if not m:
        # Fallback to free detection
        return detect_emphasis_free(blocks)
    try:
        indices = set(int(x) for x in json.loads(m.group(0)))
    except Exception:
        return detect_emphasis_free(blocks)

    for i, (_b, w) in enumerate(flat_words):
        w["is_emphasis"] = i in indices
    return blocks


def clear_emphasis(blocks: List[Dict]) -> List[Dict]:
    for b in blocks:
        for w in b.get("words", []):
            w["is_emphasis"] = False
    return blocks


def split_emphasis_to_solo(blocks: List[Dict]) -> List[Dict]:
    """For each emphasis word, make it a standalone block (more visual impact).

    Splits blocks containing emphasis words into chunks:
      • non-emphasis words → grouped together as before
      • each emphasis word → its own standalone block

    Example:
      "I made a million dollars with this incredible secret"  (million, incredible emphasis)
      → "I made a" | "million" | "dollars with this" | "incredible" | "secret"
    """
    def _make_block(words_chunk: List[Dict]) -> Dict:
        text = " ".join(w["word"] for w in words_chunk).strip()
        return {
            "id": str(uuid.uuid4())[:8],
            "start": words_chunk[0]["start"],
            "end": words_chunk[-1]["end"],
            "text": text,
            "words": [{"word": w["word"], "start": w["start"], "end": w["end"],
                       "is_emphasis": w.get("is_emphasis", False)} for w in words_chunk],
        }

    new_blocks: List[Dict] = []
    for b in blocks:
        words = b.get("words", [])
        if not words:
            new_blocks.append(b)
            continue
        chunk: List[Dict] = []
        for w in words:
            if w.get("is_emphasis"):
                if chunk:
                    new_blocks.append(_make_block(chunk))
                    chunk = []
                new_blocks.append(_make_block([w]))
            else:
                chunk.append(w)
        if chunk:
            new_blocks.append(_make_block(chunk))
    return new_blocks


def _alignment_code(align: str, position: str) -> int:
    pos = "Abajo" if position == "Personalizada 🎯" else position
    m = {("Izquierda", "Abajo"): 1, ("Centro", "Abajo"): 2, ("Derecha", "Abajo"): 3,
         ("Izquierda", "Centro"): 4, ("Centro", "Centro"): 5, ("Derecha", "Centro"): 6,
         ("Izquierda", "Arriba"): 7, ("Centro", "Arriba"): 8, ("Derecha", "Arriba"): 9}
    return m.get((align, pos), 2)


def build_ass_file(blocks: List[Dict], style: Dict, video_w: int = 1080, video_h: int = 1920,
                   total_duration: float = 0.0, watermark: Dict = None) -> str:
    """Generate ASS. If style['karaoke'] → use \\K tags + secondary color for unspoken words.
    Optional watermark dict: {text, font, size, color, opacity (0-1), position}.
    """
    alignment = _alignment_code(style["align"], style["position"])
    primary = hex_to_ass_color(style["color"])
    secondary = hex_to_ass_color(style.get("karaoke_unspoken_color", "#9CA3AF"))
    outline_c = hex_to_ass_color(style["outline_color"])

    if style["bg_mode"] == "Transparente":
        border_style = 1
        back_color = "&H00000000"
    elif style["bg_mode"] == "Caja negra":
        border_style = 3
        back_color = hex_to_ass_color("#000000", alpha="40")
    else:
        border_style = 3
        back_color = hex_to_ass_color(style["bg_color"], alpha="40")

    margin_v = 350 if style["position"] in ("Arriba", "Abajo") else 0
    bold = -1 if style["bold"] else 0

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['font']},{style['size']},{primary},{secondary},{outline_c},{back_color},{bold},0,0,0,100,100,0,0,{border_style},{style['outline_w']},{style['shadow']},{alignment},40,40,{margin_v},1
"""
    # Optional watermark style (alpha-blended via PrimaryAlpha)
    if watermark and watermark.get("text"):
        wm_align_map = {"Arriba izquierda": 7, "Arriba derecha": 9,
                        "Abajo izquierda": 1, "Abajo derecha": 3,
                        "Arriba centro": 8, "Abajo centro": 2}
        wm_alignment = wm_align_map.get(watermark.get("position", "Abajo derecha"), 3)
        # Convert opacity 0-1 → ASS alpha hex (00 = opaque, FF = transparent)
        op = max(0.05, min(1.0, float(watermark.get("opacity", 0.7))))
        alpha = f"{int((1 - op) * 255):02X}"
        wm_color = hex_to_ass_color(watermark.get("color", "#FFFFFF"), alpha=alpha)
        header += (f"Style: Watermark,{watermark.get('font', 'Inter')},{int(watermark.get('size', 36))},"
                   f"{wm_color},&H00000000,&H{alpha}000000,&H00000000,"
                   f"-1,0,0,0,100,100,0,0,1,1.0,0.0,{wm_alignment},25,25,25,1\n")

    header += """
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for blk in blocks:
        if not blk["text"].strip():
            continue
        if style.get("karaoke") and blk.get("words"):
            # Karaoke: each word advances primary color via \K (secondary = unspoken color).
            # If a word has is_emphasis=True → also scale up + emphasis color.
            emphasis_color = hex_to_ass_color(style.get("karaoke_emphasis_color", "#FFD700"))
            emphasis_scale = int(style.get("karaoke_emphasis_scale", 130))
            uppercase = bool(style.get("uppercase"))

            # ── Special case: SOLO emphasis word block → bouncy pop-in animation ──
            if len(blk["words"]) == 1 and blk["words"][0].get("is_emphasis"):
                w = blk["words"][0]
                token = w["word"].replace("{", "(").replace("}", ")")
                if uppercase:
                    token = token.upper()
                # Bouncy pop-in: 50% → 160% (overshoot) → 92% → 100% in 380ms
                text = (
                    "{\\1c%s\\fscx50\\fscy50"
                    "\\t(0,140,\\fscx160\\fscy160)"
                    "\\t(140,260,\\fscx92\\fscy92)"
                    "\\t(260,380,\\fscx100\\fscy100)"
                    "}%s"
                ) % (emphasis_color, token)
            else:
                parts = [r"{\1c" + secondary + "}"]
                for w in blk["words"]:
                    cs = max(1, int(round((w["end"] - w["start"]) * 100)))
                    token = w["word"].replace("{", "(").replace("}", ")")
                    if uppercase:
                        token = token.upper()
                    if w.get("is_emphasis"):
                        # Bigger + emphasis color, then reset
                        parts.append("{\\k%d\\1c%s\\fscx%d\\fscy%d}%s {\\fscx100\\fscy100\\1c%s}"
                                     % (cs, emphasis_color, emphasis_scale, emphasis_scale,
                                        token, secondary))
                    else:
                        parts.append("{\\k%d\\1c%s}%s {\\1c%s}" % (cs, primary, token, secondary))
                text = "".join(parts).rstrip(" ").rstrip("{\\1c" + secondary + "}")
        elif blk.get("words") and any(w.get("is_emphasis") for w in blk["words"]):
            # Non-karaoke mode with emphasis words: highlight them in color + bigger scale
            emphasis_color = hex_to_ass_color(style.get("karaoke_emphasis_color", "#FFD700"))
            emphasis_scale = int(style.get("karaoke_emphasis_scale", 130))
            uppercase = bool(style.get("uppercase"))
            parts = []
            for w in blk["words"]:
                token = w["word"].replace("{", "(").replace("}", ")")
                if uppercase:
                    token = token.upper()
                if w.get("is_emphasis"):
                    parts.append("{\\1c%s\\fscx%d\\fscy%d}%s{\\fscx100\\fscy100\\1c%s}"
                                 % (emphasis_color, emphasis_scale, emphasis_scale,
                                    token, primary))
                else:
                    parts.append(token)
            text = " ".join(parts)
        else:
            raw = blk["text"]
            if style.get("uppercase"):
                raw = raw.upper()
            text = raw.replace("\n", "\\N").replace("{", "(").replace("}", ")")
        line = f"Dialogue: 0,{seconds_to_ass_time(blk['start'])},{seconds_to_ass_time(blk['end'])},Default,,0,0,0,,{text}"
        events.append(line)

    # Watermark dialogue line spanning the whole video
    if watermark and watermark.get("text"):
        wm_text = str(watermark["text"]).replace("\n", " ").replace("{", "(").replace("}", ")")
        end_t = total_duration if total_duration > 0 else (
            blocks[-1]["end"] + 5 if blocks else 9999)
        events.append(
            f"Dialogue: 0,{seconds_to_ass_time(0.0)},{seconds_to_ass_time(end_t)},Watermark,,0,0,0,,{wm_text}"
        )
    return header + "\n".join(events) + "\n"


def build_srt(blocks: List[Dict]) -> str:
    out = []
    for i, b in enumerate(blocks, 1):
        out.append(str(i))
        out.append(f"{seconds_to_srt_time(b['start'])} --> {seconds_to_srt_time(b['end'])}")
        out.append(b["text"])
        out.append("")
    return "\n".join(out)


def build_vtt(blocks: List[Dict]) -> str:
    out = ["WEBVTT", ""]
    for b in blocks:
        out.append(f"{seconds_to_vtt_time(b['start'])} --> {seconds_to_vtt_time(b['end'])}")
        out.append(b["text"])
        out.append("")
    return "\n".join(out)


def render_video_with_subs(video_path: str, ass_path: str, output_path: str,
                           progress_cb=None) -> Tuple[bool, str]:
    work_dir = Path(ass_path).parent
    filter_txt = work_dir / "filtro.txt"
    filter_txt.write_text(f"ass=filename={Path(ass_path).name}", encoding="utf-8")

    cmd = [
        FFMPEG, "-y",
        "-i", str(Path(video_path).resolve()),
        "-filter_script:v", filter_txt.name,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
        "-threads", "2",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(Path(output_path).resolve()),
    ]
    proc = subprocess.Popen(cmd, cwd=str(work_dir),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    stderr_lines = []
    duration = get_video_duration(video_path) or 1.0
    time_re = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
    for line in proc.stdout:
        stderr_lines.append(line)
        m = time_re.search(line)
        if m and progress_cb:
            h, mm, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            cur = h * 3600 + mm * 60 + s
            progress_cb(min(cur / duration, 0.99))
    proc.wait()
    if progress_cb:
        progress_cb(1.0)
    return proc.returncode == 0, "".join(stderr_lines[-30:])


def render_preview_frame(video_path: str, blocks: List[Dict], style: Dict,
                         out_image: str, watermark: Dict = None) -> Tuple[bool, str]:
    """Extract a single frame from the middle of a meaningful subtitle block, with subs burned in."""
    if not blocks:
        return False, "No blocks"
    # Pick a block roughly in the middle of the video
    blk = blocks[len(blocks) // 2]
    target_t = blk["start"] + max(0.05, (blk["end"] - blk["start"]) * 0.4)
    v_w, v_h = get_video_dimensions(video_path)

    work_dir = Path(out_image).parent
    ass_path = work_dir / f"_preview_{uuid.uuid4().hex[:6]}.ass"
    # Generate ASS containing ONLY this block, but shifted to start at 0
    shifted = dict(blk)
    delta = blk["start"]
    shifted["start"] = 0.0
    shifted["end"] = blk["end"] - delta
    if blk.get("words"):
        shifted["words"] = [{"word": w["word"],
                             "start": w["start"] - delta,
                             "end": w["end"] - delta} for w in blk["words"]]
    ass_content = build_ass_file([shifted], style, v_w, v_h,
                                 total_duration=1.0, watermark=watermark)
    ass_path.write_text(ass_content, encoding="utf-8")

    filter_txt = work_dir / f"_preview_{uuid.uuid4().hex[:6]}.txt"
    filter_txt.write_text(f"ass=filename={ass_path.name}", encoding="utf-8")

    # Seek to target_t in original video, take 1 frame, but apply subs (which are at t=0 in ass).
    # Use a 2-step: extract frame at target_t to PNG, then re-apply subs starting at t=0 of a 0.1s loop.
    # Simpler: extract frame, then overlay using ass on a single image converted to 0.1s video.
    raw_frame = work_dir / f"_raw_{uuid.uuid4().hex[:6]}.png"
    cmd1 = [FFMPEG, "-y", "-ss", f"{target_t:.2f}", "-i", str(Path(video_path).resolve()),
            "-vframes", "1", "-q:v", "3", str(raw_frame)]
    r1 = subprocess.run(cmd1, capture_output=True, text=True)
    if r1.returncode != 0 or not raw_frame.exists():
        return False, r1.stderr[-500:]

    # Apply subtitles from ASS at t=0.5s of a 1s loop, then output single frame
    cmd2 = [FFMPEG, "-y",
            "-loop", "1", "-t", "1", "-i", str(raw_frame),
            "-filter_script:v", filter_txt.name,
            "-ss", "0.5", "-vframes", "1", "-q:v", "3",
            str(Path(out_image).resolve())]
    r2 = subprocess.run(cmd2, cwd=str(work_dir), capture_output=True, text=True)
    if r2.returncode != 0:
        return False, r2.stderr[-500:]
    return True, ""


# ──────────────────────────────────────────────────────────────────────────────
#  PRESETS
# ──────────────────────────────────────────────────────────────────────────────
PRESETS = {
    "Personalizado": None,
    "MrBeast 🟡": {
        "font": "Impact", "size": 90, "color": "#FFEA00", "outline_color": "#000000",
        "bg_mode": "Transparente", "bg_color": "#000000",
        "position": "Centro", "align": "Centro",
        "outline_w": 5.0, "shadow": 2.0, "bold": True, "karaoke": False,
        "uppercase": True,
    },
    "Captions ⬛": {
        "font": "Montserrat", "size": 64, "color": "#FFFFFF", "outline_color": "#000000",
        "bg_mode": "Caja negra", "bg_color": "#000000",
        "position": "Abajo", "align": "Centro",
        "outline_w": 0.0, "shadow": 0.0, "bold": True, "karaoke": False,
    },
    "Hormozi Karaoke 🎤": {
        "font": "Bebas Neue", "size": 88, "color": "#00E676", "outline_color": "#000000",
        "karaoke_unspoken_color": "#FFFFFF",
        "bg_mode": "Transparente", "bg_color": "#000000",
        "position": "Centro", "align": "Centro",
        "outline_w": 4.0, "shadow": 2.0, "bold": True, "karaoke": True,
    },
    "TikTok Pop 💜": {
        "font": "Poppins", "size": 70, "color": "#FFFFFF", "outline_color": "#8A2BE2",
        "bg_mode": "Color personalizado", "bg_color": "#8A2BE2",
        "position": "Abajo", "align": "Centro",
        "outline_w": 2.0, "shadow": 1.0, "bold": True, "karaoke": False,
    },
    "Storytelling 📖": {
        "font": "Inter", "size": 56, "color": "#FFFFFF", "outline_color": "#000000",
        "bg_mode": "Transparente", "bg_color": "#000000",
        "position": "Abajo", "align": "Centro",
        "outline_w": 1.5, "shadow": 1.5, "bold": False, "karaoke": False,
    },
    "Educativo 📚": {
        "font": "Roboto", "size": 60, "color": "#FFFFFF", "outline_color": "#0B3954",
        "bg_mode": "Color personalizado", "bg_color": "#0B3954",
        "position": "Abajo", "align": "Centro",
        "outline_w": 1.0, "shadow": 0.0, "bold": True, "karaoke": False,
    },
    "Comedy 😂": {
        "font": "Impact", "size": 96, "color": "#FFEA00", "outline_color": "#D9001B",
        "bg_mode": "Transparente", "bg_color": "#000000",
        "position": "Centro", "align": "Centro",
        "outline_w": 6.0, "shadow": 3.0, "bold": True, "karaoke": False,
    },
    "Cinema 🎞️": {
        "font": "Verdana", "size": 50, "color": "#F5F5F5", "outline_color": "#000000",
        "bg_mode": "Transparente", "bg_color": "#000000",
        "position": "Abajo", "align": "Centro",
        "outline_w": 0.0, "shadow": 2.5, "bold": False, "karaoke": False,
    },
    "Hormozi PRO 🎤✨": {
        "font": "Bebas Neue", "size": 92, "color": "#FFFFFF", "outline_color": "#000000",
        "karaoke_unspoken_color": "#FFFFFF",
        "karaoke_emphasis_color": "#FFD700",
        "karaoke_emphasis_scale": 135,
        "bg_mode": "Transparente", "bg_color": "#000000",
        "position": "Centro", "align": "Centro",
        "outline_w": 5.0, "shadow": 2.5, "bold": True, "karaoke": True,
        "uppercase": True,
    },
    "Karaoke Pink 🎶": {
        "font": "Bebas Neue", "size": 86, "color": "#FF1F8F", "outline_color": "#000000",
        "karaoke_unspoken_color": "#00E5FF",
        "bg_mode": "Transparente", "bg_color": "#000000",
        "position": "Centro", "align": "Centro",
        "outline_w": 4.0, "shadow": 2.0, "bold": True, "karaoke": True,
    },
}

# ──────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ──────────────────────────────────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("blocks", [])
ss.setdefault("video_path", None)
ss.setdefault("video_name", None)
ss.setdefault("video_size", None)
ss.setdefault("output_path", None)
ss.setdefault("preview_path", None)
ss.setdefault("transcribed", False)
ss.setdefault("workdir", None)
ss.setdefault("preset_applied", "Personalizado")
ss.setdefault("user_openai_key", "")
ss.setdefault("user_anthropic_key", "")
ss.setdefault("emphasis_detected", False)


def get_workdir() -> str:
    if not ss.workdir or not os.path.isdir(ss.workdir):
        ss.workdir = tempfile.mkdtemp(prefix="transcribe_")
    return ss.workdir


# ──────────────────────────────────────────────────────────────────────────────
#  3-COLUMN LAYOUT
# ──────────────────────────────────────────────────────────────────────────────
col_input, col_editor, col_style = st.columns([1.0, 1.55, 1.05], gap="large")

# ─── COLUMN 1: INPUT & TRANSCRIPTION ──────────────────────────────────────────
with col_input:
    st.markdown('<div class="tt-card-title"><span class="tt-step">1</span>Vídeo &amp; Transcripción</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Sube tu vídeo vertical",
        type=["mp4", "mov", "mkv", "webm"],
        help="Reels, TikToks, Shorts. Máx ≈ 150 MB recomendado.",
        key="uploader",
    )

    if uploaded is not None:
        size_mb = uploaded.size / (1024 * 1024)
        if (ss.video_name != uploaded.name) or (ss.video_size != uploaded.size):
            wd = get_workdir()
            video_path = os.path.join(wd, f"input_{uuid.uuid4().hex[:8]}{Path(uploaded.name).suffix}")
            with open(video_path, "wb") as f:
                f.write(uploaded.getbuffer())
            ss.video_path = video_path
            ss.video_name = uploaded.name
            ss.video_size = uploaded.size
            ss.blocks = []
            ss.transcribed = False
            ss.output_path = None
            ss.preview_path = None

        st.markdown(
            f"""<div class="tt-card" style="margin-top:10px;padding:14px 18px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="font-weight:600;font-size:13px;color:var(--text);" data-testid="video-filename">📹 {uploaded.name}</div>
                        <div style="font-size:11px;color:var(--text-dim);font-family:'JetBrains Mono',monospace;">{size_mb:.1f} MB</div>
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("&nbsp;", unsafe_allow_html=True)

    words_per_block = st.selectbox(
        "Palabras por subtítulo",
        options=[2, 3, 4],
        index=1,
        help="Bloques cortos = más retención. (Se usa como límite máximo; el split inteligente "
             "corta antes en pausas y signos de puntuación.)",
    )

    # Split inteligente siempre activo
    smart_split = True

    LANG_OPTS = [("auto", "Detectar automáticamente"), ("es", "Español"), ("en", "English"),
                 ("pt", "Português"), ("fr", "Français"), ("de", "Deutsch"),
                 ("it", "Italiano"), ("ja", "日本語"), ("zh", "中文")]
    language = st.selectbox("Idioma del audio", options=LANG_OPTS,
                            format_func=lambda x: x[1], index=0)

    # ─── Engine selector ───────────────────────────────────────────────────
    use_openai = bool(ss.get("user_openai_key"))

    if not use_openai:
        local_model = st.selectbox(
            "🆓 Modelo local (gratis)",
            ["tiny", "base", "small"],
            index=1,
            help=(
                "tiny → ultra rápido, calidad básica (~150 MB)\n"
                "base → recomendado, buena calidad (~250 MB)\n"
                "small → más lento, mejor calidad (~500 MB)\n\n"
                "Primera vez descarga el modelo (puede tardar 30-60s)."
            ),
            key="local_model_size",
        )
    else:
        local_model = "base"
        st.info("🚀 Usando OpenAI Whisper-1 API (con tu key personal)", icon="✓")

    with st.expander("🔑  OpenAI API Key (opcional, para más velocidad/calidad)"):
        st.caption(
            "Si pegas tu propia key, la app usará Whisper-1 API (más rápido) y "
            "GPT-4o-mini para traducir (mejor calidad). **Tu key nunca se guarda en disco**, "
            "solo en la sesión del navegador."
        )
        new_key = st.text_input(
            "Tu OpenAI API Key (sk-...)",
            value=ss.get("user_openai_key", ""),
            type="password",
            placeholder="sk-...",
            key="openai_key_input",
            help="Obtén una en platform.openai.com/api-keys",
        )
        if new_key != ss.get("user_openai_key", ""):
            ss.user_openai_key = new_key.strip()
            st.rerun()
        if ss.get("user_openai_key"):
            if st.button("Quitar OpenAI key", type="secondary",
                         use_container_width=True, key="btn-clear-key"):
                ss.user_openai_key = ""
                st.rerun()

    with st.expander("🤖  Claude API Key (opcional, para detección PRO)"):
        st.caption(
            "Pegando tu Claude key, la app usa **Claude Haiku 4.5** para "
            "auto-detectar palabras impactantes (Hormozi PRO), traducciones "
            "más naturales y futuras features. Coste por vídeo: ~$0.0002. "
            "**Tu key nunca se guarda en disco**."
        )
        new_anthro = st.text_input(
            "Tu Anthropic API Key (sk-ant-...)",
            value=ss.get("user_anthropic_key", ""),
            type="password",
            placeholder="sk-ant-...",
            key="anthropic_key_input",
            help="Obtén una en console.anthropic.com/settings/keys",
        )
        if new_anthro != ss.get("user_anthropic_key", ""):
            ss.user_anthropic_key = new_anthro.strip()
            st.rerun()
        if ss.get("user_anthropic_key"):
            if st.button("Quitar Claude key", type="secondary",
                         use_container_width=True, key="btn-clear-anthro"):
                ss.user_anthropic_key = ""
                st.rerun()

    transcribe_disabled = ss.video_path is None
    if st.button("🎙️  Transcribir", disabled=transcribe_disabled, type="primary",
                 use_container_width=True, key="btn-transcribe"):
        wd = get_workdir()
        audio_path = os.path.join(wd, "audio.mp3")
        with st.spinner("Extrayendo audio..."):
            ok = extract_audio(ss.video_path, audio_path)
        if not ok:
            st.error("Error al extraer audio con FFmpeg.")
        else:
            try:
                if use_openai:
                    with st.spinner("Transcribiendo con OpenAI Whisper-1..."):
                        words = transcribe_openai(audio_path, language[0],
                                                  api_key=ss.user_openai_key)
                else:
                    with st.spinner(f"Cargando modelo `{local_model}` (primera vez tarda)..."):
                        _load_whisper_local(local_model)
                    with st.spinner(f"Transcribiendo con faster-whisper `{local_model}`..."):
                        words = transcribe_local(audio_path, language[0], model_size=local_model)
                if not words:
                    st.error("No se detectó audio inteligible en el vídeo.")
                else:
                    if smart_split:
                        ss.blocks = group_words_smart(words, max_per_block=words_per_block)
                    else:
                        ss.blocks = group_words_into_blocks(words, words_per_block)
                    ss.transcribed = True
                    ss.output_path = None
                    ss.preview_path = None
                    st.success(f"✅  {len(ss.blocks)} bloques generados.")
                    st.rerun()
            except Exception as e:
                st.error(f"Error al transcribir: {e}")

    if ss.transcribed and ss.blocks:
        if st.button("🔁  Reagrupar bloques", type="secondary",
                     use_container_width=True, key="btn-regroup"):
            flat = []
            for b in ss.blocks:
                if b.get("words"):
                    flat.extend(b["words"])
                else:
                    tokens = b["text"].split()
                    if not tokens:
                        continue
                    dur = (b["end"] - b["start"]) / len(tokens)
                    for i, t in enumerate(tokens):
                        flat.append({"word": t, "start": b["start"] + i * dur,
                                     "end": b["start"] + (i + 1) * dur})
            ss.blocks = group_words_smart(flat, max_per_block=words_per_block) if smart_split \
                else group_words_into_blocks(flat, words_per_block)
            st.rerun()

        # ─── PRO: Auto-detectar palabras clave (emphasis) ──────────────────
        st.markdown("---")
        st.markdown('<div class="tt-card-title" style="margin-bottom:8px;">✨ Palabras clave PRO</div>',
                    unsafe_allow_html=True)
        emp_engine = ("Claude Haiku 4.5 (tu key)"
                      if ss.get("user_anthropic_key") else "Keywords libres (gratis)")
        st.caption(f"Motor: **{emp_engine}** · Resalta palabras impactantes en estilo Hormozi.")
        empc1, empc2 = st.columns(2)
        with empc1:
            if st.button("✨  Detectar", type="secondary",
                         use_container_width=True, key="btn-emphasis"):
                try:
                    with st.spinner("Detectando palabras clave..."):
                        if ss.get("user_anthropic_key"):
                            ss.blocks = detect_emphasis_claude(
                                ss.blocks, ss.user_anthropic_key)
                        else:
                            ss.blocks = detect_emphasis_free(ss.blocks)
                        # Split: each emphasis word becomes its own block
                        ss.blocks = split_emphasis_to_solo(ss.blocks)
                    ss.emphasis_detected = True
                    ss.preview_path = None
                    n_emp = sum(1 for b in ss.blocks for w in b.get("words", []) if w.get("is_emphasis"))
                    st.success(f"✅  {n_emp} palabras destacadas en su propio bloque.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        with empc2:
            if st.button("🗑  Limpiar", type="secondary",
                         use_container_width=True, key="btn-clear-emphasis",
                         disabled=not ss.emphasis_detected):
                ss.blocks = clear_emphasis(ss.blocks)
                ss.emphasis_detected = False
                ss.preview_path = None
                st.rerun()

        # ─── Translation ────────────────────────────────────────────────
        st.markdown("---")
        st.markdown('<div class="tt-card-title" style="margin-bottom:8px;">🌐 Traducir subtítulos</div>',
                    unsafe_allow_html=True)
        TRANSLATE_OPTS = [
            ("English", "Inglés 🇬🇧"), ("Spanish", "Español 🇪🇸"),
            ("Portuguese (Brazilian)", "Portugués 🇧🇷"), ("French", "Francés 🇫🇷"),
            ("German", "Alemán 🇩🇪"), ("Italian", "Italiano 🇮🇹"),
            ("Japanese", "Japonés 🇯🇵"), ("Chinese (Simplified)", "Chino 🇨🇳"),
            ("Korean", "Coreano 🇰🇷"), ("Hindi", "Hindi 🇮🇳"),
            ("Arabic", "Árabe 🇸🇦"),
        ]
        tlang = st.selectbox("Idioma destino", options=TRANSLATE_OPTS,
                             format_func=lambda x: x[1], key="translate_lang", index=0)
        engine_label = ("GPT-4o-mini (tu OpenAI key)"
                        if ss.get("user_openai_key") else "Google Translate (gratis)")
        st.caption(f"Motor: **{engine_label}**")
        if st.button("✨  Traducir", type="secondary", use_container_width=True,
                     key="btn-translate"):
            try:
                with st.spinner(f"Traduciendo {len(ss.blocks)} bloques..."):
                    ss.blocks = translate_blocks_dispatch(
                        ss.blocks, tlang[0], api_key=ss.get("user_openai_key") or None
                    )
                ss.preview_path = None
                ss.output_path = None
                st.success("✅  Subtítulos traducidos.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al traducir: {e}")


# ─── COLUMN 3: STYLE & RENDER (renders BEFORE col_editor so style is computed) ─
with col_style:
    st.markdown('<div class="tt-card-title"><span class="tt-step">3</span>Estilo &amp; Render</div>', unsafe_allow_html=True)

    # Preset selector
    preset_name = st.selectbox(
        "🎨 Preset viral",
        options=list(PRESETS.keys()),
        index=list(PRESETS.keys()).index(ss.preset_applied) if ss.preset_applied in PRESETS else 0,
        help="Aplica un look listo para usar. Cambia a 'Personalizado' para ajustar manualmente.",
        key="preset_select",
    )

    # Apply preset → seed defaults (only when changed)
    if preset_name != ss.preset_applied:
        ss.preset_applied = preset_name
        if PRESETS[preset_name]:
            for k, v in PRESETS[preset_name].items():
                ss[f"_pre_{k}"] = v
        ss.preview_path = None
        # If switching to/from Hormozi PRO, hint about emphasis detection
        if preset_name == "Hormozi PRO 🎤✨" and not ss.get("emphasis_detected"):
            st.toast("💡 Pulsa 'Detectar palabras clave PRO' en la columna 1 para el efecto Hormozi completo")

    def get_default(k, fallback):
        return ss.get(f"_pre_{k}", fallback)

    FONTS = ["Inter", "Montserrat", "Arial", "Impact", "Bebas Neue", "Poppins",
             "Roboto", "Helvetica", "Verdana", "Tahoma"]
    with st.expander("🔤  Tipografía & tamaño", expanded=False):
        font = st.selectbox(
            "Tipografía", FONTS,
            index=FONTS.index(get_default("font", "Impact"))
            if get_default("font", "Impact") in FONTS else 3,
        )
        size = st.slider("Tamaño de fuente", 24, 120, get_default("size", 72), step=2)
        bold = st.checkbox("Negrita", value=get_default("bold", True))
        uppercase = st.checkbox(
            "TODO MAYÚSCULAS", value=get_default("uppercase", False),
            help="Convierte todo el texto a mayúsculas (efecto MrBeast/Hormozi).",
        )

    cc1, cc2 = st.columns(2)
    with cc1:
        color = st.color_picker("Color de texto", get_default("color", "#FFFFFF"))
    with cc2:
        outline_color = st.color_picker("Color contorno", get_default("outline_color", "#000000"))
    # Inject live color preview badges next to each picker label
    st.markdown(f"""
    <style>
    /* Color de texto swatch */
    div[data-testid="stColorPicker"]:nth-of-type(1) label::after {{
        content: '';
        display: inline-block;
        width: 14px; height: 14px;
        background: {color};
        border-radius: 4px;
        border: 1px solid rgba(255,255,255,0.25);
        margin-left: 8px;
        vertical-align: middle;
        box-shadow: 0 0 6px {color}88;
    }}
    /* Color contorno swatch */
    div[data-testid="stColorPicker"]:nth-of-type(2) label::after {{
        content: '';
        display: inline-block;
        width: 14px; height: 14px;
        background: {outline_color};
        border-radius: 4px;
        border: 1px solid rgba(255,255,255,0.25);
        margin-left: 8px;
        vertical-align: middle;
        box-shadow: 0 0 6px {outline_color}88;
    }}
    </style>
    """, unsafe_allow_html=True)

    BG_OPTS = ["Transparente", "Caja negra", "Color personalizado"]
    bg_default = get_default("bg_mode", "Transparente")
    bg_mode = st.selectbox(
        "Fondo del texto", BG_OPTS,
        index=BG_OPTS.index(bg_default) if bg_default in BG_OPTS else 0,
    )
    bg_color = "#000000"
    if bg_mode == "Color personalizado":
        bg_color = st.color_picker("Color de fondo",
                                   get_default("bg_color", "#8A2BE2"))

    POS_OPTS = ["Arriba", "Centro", "Abajo", "Personalizada 🎯"]
    pos_default = get_default("position", "Abajo")
    position = st.selectbox(
        "Posición vertical", POS_OPTS,
        index=POS_OPTS.index(pos_default) if pos_default in POS_OPTS else 2,
    )
    custom_margin_v = int(get_default("custom_margin_v", 80))
    if position == "Personalizada 🎯":
        custom_margin_v = st.slider(
            "Margen vertical (px)", 0, 900, custom_margin_v, step=10,
            help="0 = pegado al borde inferior, valores altos suben el texto. "
                 "Para vídeo 1080×1920: ~80 es muy abajo, ~900 es muy arriba.",
        )
        ss["_pre_custom_margin_v"] = custom_margin_v

    AL_OPTS = ["Izquierda", "Centro", "Derecha"]
    al_default = get_default("align", "Centro")
    align = st.selectbox(
        "Alineación", AL_OPTS,
        index=AL_OPTS.index(al_default) if al_default in AL_OPTS else 1,
    )

    # Karaoke
    karaoke = st.checkbox("🎤  Animación karaoke (palabra-por-palabra)",
                          value=get_default("karaoke", False),
                          help="Resalta cada palabra a medida que se pronuncia. Estilo Hormozi.")
    karaoke_unspoken_color = "#9CA3AF"
    karaoke_emphasis_color = get_default("karaoke_emphasis_color", "#FFD700")
    karaoke_emphasis_scale = int(get_default("karaoke_emphasis_scale", 130))

    # Show emphasis controls whenever karaoke is on OR emphasis has been detected
    show_emphasis_controls = karaoke or ss.get("emphasis_detected", False)
    if show_emphasis_controls:
        if karaoke:
            kc1, kc2 = st.columns(2)
            with kc1:
                karaoke_unspoken_color = st.color_picker(
                    "Color sin hablar",
                    get_default("karaoke_unspoken_color", "#FFFFFF"),
                    help="Color de palabras que aún no se han pronunciado.",
                )
            with kc2:
                karaoke_emphasis_color = st.color_picker(
                    "Color énfasis ✨",
                    karaoke_emphasis_color,
                    help="Color de palabras destacadas con 'Detectar palabras clave PRO'.",
                )
        else:
            st.caption("✨ **Palabras clave detectadas** — ajusta cómo se resaltan:")
            ec1, ec2 = st.columns(2)
            with ec1:
                karaoke_emphasis_color = st.color_picker(
                    "Color énfasis ✨",
                    karaoke_emphasis_color,
                    help="Color de las palabras clave resaltadas.",
                )
            with ec2:
                karaoke_emphasis_scale = st.slider(
                    "Tamaño énfasis %", 100, 200, karaoke_emphasis_scale, step=5,
                    help="Escala de las palabras clave (100 = igual que el resto).",
                )

    with st.expander("⚙️  Efectos avanzados"):
        outline_w = st.slider("Grosor del contorno", 0.0, 6.0,
                              float(get_default("outline_w", 2.5)), step=0.5)
        shadow = st.slider("Sombra paralela", 0.0, 6.0,
                           float(get_default("shadow", 1.0)), step=0.5)

    # ─── Watermark ─────────────────────────────────────────────────────────
    with st.expander("💧  Marca de agua (watermark)"):
        wm_enabled = st.checkbox("Añadir marca de agua", value=False, key="wm_enabled")
        wm_text = st.text_input("Texto", value="@tu_usuario",
                                disabled=not wm_enabled, key="wm_text")
        wm_pos = st.selectbox(
            "Posición",
            ["Arriba derecha", "Arriba izquierda", "Arriba centro",
             "Abajo derecha", "Abajo izquierda", "Abajo centro"],
            index=3, disabled=not wm_enabled, key="wm_pos",
        )
        wcol1, wcol2 = st.columns(2)
        with wcol1:
            wm_size = st.slider("Tamaño", 18, 80, 36, step=2,
                                disabled=not wm_enabled, key="wm_size")
        with wcol2:
            wm_color = st.color_picker("Color", "#FFFFFF",
                                       disabled=not wm_enabled, key="wm_color")
        wm_opacity = st.slider("Opacidad", 0.1, 1.0, 0.7, step=0.05,
                               disabled=not wm_enabled, key="wm_opacity")
        wm_font = st.selectbox("Fuente", FONTS,
                               index=FONTS.index("Inter"),
                               disabled=not wm_enabled, key="wm_font")

    watermark = None
    if wm_enabled and wm_text.strip():
        watermark = {
            "text": wm_text.strip(), "font": wm_font, "size": wm_size,
            "color": wm_color, "opacity": wm_opacity, "position": wm_pos,
        }

    style = {
        "font": font, "size": size, "color": color, "outline_color": outline_color,
        "bg_mode": bg_mode, "bg_color": bg_color, "position": position, "align": align,
        "outline_w": outline_w, "shadow": shadow, "bold": bold, "uppercase": uppercase,
        "karaoke": karaoke, "karaoke_unspoken_color": karaoke_unspoken_color,
        "karaoke_emphasis_color": karaoke_emphasis_color,
        "karaoke_emphasis_scale": karaoke_emphasis_scale,
        "custom_margin_v": custom_margin_v,
    }

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # ─── Render ────────────────────────────────────────────────────────────
    render_disabled = not (ss.video_path and ss.blocks)
    if st.button("🎬  Renderizar vídeo final", disabled=render_disabled,
                 type="primary", use_container_width=True, key="btn-render"):
        wd = get_workdir()
        v_w, v_h = get_video_dimensions(ss.video_path)
        v_dur = get_video_duration(ss.video_path)
        ass_content = build_ass_file(ss.blocks, style, v_w, v_h,
                                     total_duration=v_dur, watermark=watermark)
        ass_path = os.path.join(wd, "subs.ass")
        Path(ass_path).write_text(ass_content, encoding="utf-8")

        out_path = os.path.join(wd, f"output_{uuid.uuid4().hex[:6]}.mp4")
        progress = st.progress(0.0, text="Renderizando con FFmpeg...")
        ok, log_tail = render_video_with_subs(
            ss.video_path, ass_path, out_path,
            progress_cb=lambda p: progress.progress(p, text=f"Renderizando... {int(p * 100)}%"),
        )
        progress.empty()
        if ok and os.path.exists(out_path):
            ss.output_path = out_path
            st.success("✅  Vídeo renderizado.")
        else:
            st.error("Error en FFmpeg al renderizar.")
            with st.expander("Ver log de FFmpeg"):
                st.code(log_tail or "(sin log)")

    if ss.output_path and os.path.exists(ss.output_path):
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.video(ss.output_path)
        with open(ss.output_path, "rb") as f:
            st.download_button(
                "⬇️  Descargar MP4",
                f.read(),
                file_name=f"transcribethat_{Path(ss.video_name or 'video').stem}.mp4",
                mime="video/mp4",
                use_container_width=True,
                key="btn-download",
            )


# ─── COLUMN 2 (renders LAST so we can use computed style/watermark) ──────────
with col_editor:
    st.markdown('<div class="tt-card-title"><span class="tt-step">2</span>Preview &amp; Editor</div>',
                unsafe_allow_html=True)

    # ─── Live Preview (centered, always visible) ────────────────────────────
    st.markdown('<div class="tt-preview-wrap">', unsafe_allow_html=True)

    if not ss.video_path:
        st.markdown("""
        <div class="tt-preview-empty tt-drop-zone" id="tt-drop-zone"
             ondragover="event.preventDefault(); this.classList.add('tt-drop-active');"
             ondragleave="this.classList.remove('tt-drop-active');"
             ondrop="
               event.preventDefault();
               this.classList.remove('tt-drop-active');
               var files = event.dataTransfer.files;
               if (files.length > 0) {
                 var inp = window.parent.document.querySelector('[data-testid=stFileUploaderDropzoneInput]');
                 if (!inp) inp = window.parent.document.querySelector('input[type=file]');
                 if (inp) {
                   var dt = new DataTransfer();
                   dt.items.add(files[0]);
                   inp.files = dt.files;
                   inp.dispatchEvent(new Event('change', {bubbles:true}));
                 }
               }
             ">
            <div class="tt-preview-empty-icon">🎬</div>
            <div class="tt-preview-empty-title">Sube un vídeo para empezar</div>
            <div style="font-size:13px;margin-bottom:10px;">Arrastra tu vídeo aquí o usa el botón de la izquierda</div>
            <div style="font-size:11px;color:var(--text-dim);font-family:'JetBrains Mono',monospace;">MP4 · MOV · MKV · WEBM</div>
        </div>
        <style>
        .tt-drop-zone { cursor: pointer; transition: border-color 0.2s ease, background 0.2s ease; }
        .tt-drop-active { border-color: var(--accent) !important; background: rgba(138,43,226,0.10) !important; }
        .tt-drop-active .tt-preview-empty-icon { transform: scale(1.15); }
        </style>
        """, unsafe_allow_html=True)
    elif not ss.blocks:
        st.markdown("""
        <div class="tt-preview-empty">
            <div class="tt-preview-empty-icon">⏳</div>
            <div class="tt-preview-empty-title">Vídeo cargado</div>
            <div style="font-size:13px;">Pulsa <b>Transcribir</b> en la columna izquierda para generar los subtítulos.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Auto-generate preview if not yet generated
        if not ss.preview_path or not os.path.exists(ss.preview_path):
            try:
                wd = get_workdir()
                out_img = os.path.join(wd, f"preview_{uuid.uuid4().hex[:6]}.jpg")
                with st.spinner("Generando preview..."):
                    ok, _err = render_preview_frame(ss.video_path, ss.blocks, style,
                                                    out_img, watermark=watermark)
                if ok:
                    ss.preview_path = out_img
            except Exception:
                pass

        if ss.preview_path and os.path.exists(ss.preview_path):
            pcol_l, pcol_c, pcol_r = st.columns([1, 2.2, 1])
            with pcol_c:
                st.image(ss.preview_path, use_container_width=True)
            if st.button("🔄  Actualizar preview con el estilo actual",
                         type="secondary", use_container_width=True, key="btn-refresh-preview"):
                wd = get_workdir()
                out_img = os.path.join(wd, f"preview_{uuid.uuid4().hex[:6]}.jpg")
                with st.spinner("Regenerando preview..."):
                    ok, err = render_preview_frame(ss.video_path, ss.blocks, style,
                                                   out_img, watermark=watermark)
                if ok:
                    ss.preview_path = out_img
                    st.rerun()
                else:
                    st.error(f"Error: {err[:200]}")
        else:
            st.markdown("""
            <div class="tt-preview-empty">
                <div class="tt-preview-empty-icon">⚠️</div>
                <div class="tt-preview-empty-title">No se pudo generar el preview</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ─── Editor de subtítulos ─────────────────────────────────────────────
    st.markdown('<div class="tt-card-title" style="margin-top:18px;">✏️ Editor de subtítulos</div>',
                unsafe_allow_html=True)
    if not ss.blocks:
        st.markdown("""
        <div class="tt-card" style="text-align:center;padding:30px 20px;">
            <div style="color:var(--text-dim);font-size:13px;">Aún no hay subtítulos. Transcribe primero.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption(f"📝 {len(ss.blocks)} bloques · edita el texto si hay errores")
        st.markdown('<div style="max-height:380px; overflow-y:auto; padding-right:6px;">',
                    unsafe_allow_html=True)
        for idx, blk in enumerate(ss.blocks):
            tcol1, tcol2 = st.columns([2, 1])
            with tcol1:
                st.markdown(
                    f'<div class="tt-time">▸ {seconds_to_ass_time(blk["start"])} → {seconds_to_ass_time(blk["end"])}</div>',
                    unsafe_allow_html=True,
                )
            with tcol2:
                st.markdown(
                    f'<div class="tt-time" style="text-align:right;color:var(--text-dim);">#{idx + 1}</div>',
                    unsafe_allow_html=True,
                )
            new_text = st.text_input(f"block_{blk['id']}", value=blk["text"],
                                     label_visibility="collapsed", key=f"txt_{blk['id']}")
            if new_text != blk["text"]:
                ss.blocks[idx]["text"] = new_text
                toks = new_text.split() or [new_text]
                dur = max(0.001, blk["end"] - blk["start"])
                per = dur / len(toks)
                ss.blocks[idx]["words"] = [{"word": t, "start": blk["start"] + i * per,
                                            "end": blk["start"] + (i + 1) * per}
                                           for i, t in enumerate(toks)]
                ss.preview_path = None  # invalidate so next refresh regenerates
        st.markdown("</div>", unsafe_allow_html=True)

        # ─── Export SRT/VTT ─────────────────────────────────────────────────
        st.markdown("---")
        st.markdown('<div class="tt-card-title" style="margin-bottom:8px;">📤 Exportar subtítulos</div>',
                    unsafe_allow_html=True)
        ec1, ec2 = st.columns(2)
        with ec1:
            st.download_button(
                "⬇️  SRT", data=build_srt(ss.blocks),
                file_name=f"{Path(ss.video_name or 'subs').stem}.srt",
                mime="application/x-subrip",
                use_container_width=True, key="dl-srt",
            )
        with ec2:
            st.download_button(
                "⬇️  VTT", data=build_vtt(ss.blocks),
                file_name=f"{Path(ss.video_name or 'subs').stem}.vtt",
                mime="text/vtt",
                use_container_width=True, key="dl-vtt",
            )
