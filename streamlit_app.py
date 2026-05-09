"""
TranscribeThat — Streamlit + OpenAI Whisper API + FFmpeg
Optimized for Streamlit Community Cloud (1GB RAM) and Emergent preview.

Features:
- Whisper-1 transcription with word-level timestamps
- Block editor (2/3/4 words per subtitle)
- Visual customization (font, size, color, bg, position, alignment, outline, shadow)
- Viral presets (MrBeast / Captions / Hormozi Karaoke)
- Karaoke word-by-word animation (\\K tags in ASS)
- Live preview on a real video frame
- Auto-translation via GPT-4o-mini
- Export MP4 (hardcoded subs), SRT and VTT
"""
import os
import re
import json
import shutil
import asyncio
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Tuple

import streamlit as st
from dotenv import load_dotenv

# Load env (Emergent path first, then root)
for env_path in [Path(__file__).parent / "backend" / ".env",
                 Path(__file__).parent / ".env"]:
    if env_path.exists():
        load_dotenv(env_path)
        break

EMERGENT_LLM_KEY = (os.environ.get("EMERGENT_LLM_KEY")
                    or os.environ.get("OPENAI_API_KEY")
                    or st.secrets.get("EMERGENT_LLM_KEY", None) if hasattr(st, "secrets") else None)

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
            <p class="tt-subtitle">Subtítulos automáticos · Karaoke · Traducción · Presets virales</p>
        </div>
    </div>
    <div class="tt-badge">whisper-1 · gpt-4o-mini · ffmpeg</div>
</div>
""", unsafe_allow_html=True)

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


async def transcribe_with_api(audio_path: str, language: str = None) -> List[Dict]:
    """Whisper-1 with word timestamps."""
    from emergentintegrations.llm.openai import OpenAISpeechToText
    stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
    kwargs = {
        "model": "whisper-1",
        "response_format": "verbose_json",
        "timestamp_granularities": ["word"],
        "temperature": 0.0,
    }
    if language and language != "auto":
        kwargs["language"] = language
    with open(audio_path, "rb") as f:
        kwargs["file"] = f
        response = await stt.transcribe(**kwargs)
    words = []
    raw_words = getattr(response, "words", None) or []
    for w in raw_words:
        words.append({
            "word": (getattr(w, "word", None) or w.get("word", "")).strip(),
            "start": float(getattr(w, "start", None) or w.get("start", 0.0)),
            "end": float(getattr(w, "end", None) or w.get("end", 0.0)),
        })
    if not words:
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


async def translate_blocks(blocks: List[Dict], target_lang_name: str) -> List[Dict]:
    """Translate block texts via emergentintegrations chat (gpt-4o-mini)."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"translate-{uuid.uuid4()}",
        system_message=(
            f"You are a professional subtitle translator. Translate to {target_lang_name}. "
            "Keep translations short and punchy (these are short-video subtitles). "
            "Return ONLY a valid JSON array of strings, same length as input, no extra text."
        ),
    ).with_model("openai", "gpt-4o-mini")

    src_texts = [b["text"] for b in blocks]
    payload = json.dumps(src_texts, ensure_ascii=False)
    msg = UserMessage(text=f"Translate this JSON array of subtitle lines:\n{payload}")
    response = await chat.send_message(msg)
    raw = str(response).strip()
    # Robust JSON extraction
    m = re.search(r"\[[\s\S]*\]", raw)
    if not m:
        raise ValueError(f"No JSON array found in response: {raw[:200]}")
    arr = json.loads(m.group(0))
    if len(arr) != len(blocks):
        # Best-effort: pad/truncate
        arr = (arr + src_texts)[:len(blocks)]

    out = []
    for b, new_text in zip(blocks, arr):
        new_text = str(new_text).strip()
        # Re-distribute word timings proportionally over the new tokens
        toks = new_text.split() or [new_text]
        dur = max(0.001, b["end"] - b["start"])
        per = dur / len(toks)
        new_words = [{"word": t, "start": b["start"] + i * per, "end": b["start"] + (i + 1) * per}
                     for i, t in enumerate(toks)]
        out.append({**b, "text": new_text, "words": new_words})
    return out


def _alignment_code(align: str, position: str) -> int:
    m = {("Izquierda", "Abajo"): 1, ("Centro", "Abajo"): 2, ("Derecha", "Abajo"): 3,
         ("Izquierda", "Centro"): 4, ("Centro", "Centro"): 5, ("Derecha", "Centro"): 6,
         ("Izquierda", "Arriba"): 7, ("Centro", "Arriba"): 8, ("Derecha", "Arriba"): 9}
    return m.get((align, position), 2)


def build_ass_file(blocks: List[Dict], style: Dict, video_w: int = 1080, video_h: int = 1920) -> str:
    """Generate ASS. If style['karaoke'] → use \\K tags + secondary color for unspoken words."""
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

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for blk in blocks:
        if not blk["text"].strip():
            continue
        if style.get("karaoke") and blk.get("words"):
            # Karaoke: each word advances primary color via \K (secondary = unspoken color).
            # We need to use \1c override per word: swap colors so unspoken=secondary, spoken=primary
            # Simplest reliable trick: start with \1c=secondary, then on each word emit \k<cs>\1c=primary on that word
            parts = [r"{\1c" + secondary + "}"]
            for w in blk["words"]:
                cs = max(1, int(round((w["end"] - w["start"]) * 100)))
                token = w["word"].replace("{", "(").replace("}", ")")
                parts.append("{\\k%d\\1c%s}%s {\\1c%s}" % (cs, primary, token, secondary))
            text = "".join(parts).rstrip(" ").rstrip("{\\1c" + secondary + "}")
        else:
            text = blk["text"].replace("\n", "\\N").replace("{", "(").replace("}", ")")
        line = f"Dialogue: 0,{seconds_to_ass_time(blk['start'])},{seconds_to_ass_time(blk['end'])},Default,,0,0,0,,{text}"
        events.append(line)
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
                         out_image: str) -> Tuple[bool, str]:
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
    ass_content = build_ass_file([shifted], style, v_w, v_h)
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


def get_workdir() -> str:
    if not ss.workdir or not os.path.isdir(ss.workdir):
        ss.workdir = tempfile.mkdtemp(prefix="transcribe_")
    return ss.workdir


# ──────────────────────────────────────────────────────────────────────────────
#  3-COLUMN LAYOUT
# ──────────────────────────────────────────────────────────────────────────────
col_input, col_editor, col_style = st.columns([1.05, 1.25, 1.15], gap="large")

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

    words_per_block = st.radio("Palabras por subtítulo", options=[2, 3, 4],
                               index=1, horizontal=True,
                               help="Bloques cortos = más retención.")

    LANG_OPTS = [("auto", "Detectar automáticamente"), ("es", "Español"), ("en", "English"),
                 ("pt", "Português"), ("fr", "Français"), ("de", "Deutsch"),
                 ("it", "Italiano"), ("ja", "日本語"), ("zh", "中文")]
    language = st.selectbox("Idioma del audio", options=LANG_OPTS,
                            format_func=lambda x: x[1], index=0)

    transcribe_disabled = ss.video_path is None or not EMERGENT_LLM_KEY
    if not EMERGENT_LLM_KEY:
        st.warning("⚠️  Configura `EMERGENT_LLM_KEY` en `.env` o en Streamlit Secrets.")

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
                with st.spinner("Transcribiendo con Whisper..."):
                    words = asyncio.run(transcribe_with_api(audio_path, language[0]))
                if not words:
                    st.error("No se detectó audio inteligible en el vídeo.")
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
            ss.blocks = group_words_into_blocks(flat, words_per_block)
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
        if st.button("✨  Traducir", type="secondary", use_container_width=True,
                     key="btn-translate", disabled=not EMERGENT_LLM_KEY):
            try:
                with st.spinner(f"Traduciendo {len(ss.blocks)} bloques..."):
                    ss.blocks = asyncio.run(translate_blocks(ss.blocks, tlang[0]))
                ss.preview_path = None
                ss.output_path = None
                st.success("✅  Subtítulos traducidos.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al traducir: {e}")


# ─── COLUMN 2: SEGMENT EDITOR ────────────────────────────────────────────────
with col_editor:
    st.markdown('<div class="tt-card-title"><span class="tt-step">2</span>Editor de subtítulos</div>', unsafe_allow_html=True)

    if not ss.blocks:
        st.markdown("""
        <div class="tt-card" style="text-align:center;padding:50px 20px;">
            <div style="font-size:36px;margin-bottom:12px;">✏️</div>
            <div style="color:var(--text);font-weight:600;margin-bottom:6px;">Aún no hay subtítulos</div>
            <div style="color:var(--text-dim);font-size:13px;">Sube un vídeo y haz clic en <b>Transcribir</b> para empezar.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption(f"📝 {len(ss.blocks)} bloques · edita el texto si hay errores")
        st.markdown('<div style="max-height:560px; overflow-y:auto; padding-right:6px;">', unsafe_allow_html=True)
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
                # Re-distribute word timings if text was edited (keep approximate sync)
                toks = new_text.split() or [new_text]
                dur = max(0.001, blk["end"] - blk["start"])
                per = dur / len(toks)
                ss.blocks[idx]["words"] = [{"word": t, "start": blk["start"] + i * per,
                                            "end": blk["start"] + (i + 1) * per}
                                           for i, t in enumerate(toks)]
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


# ─── COLUMN 3: STYLE & RENDER ────────────────────────────────────────────────
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

    def get_default(k, fallback):
        return ss.get(f"_pre_{k}", fallback)

    FONTS = ["Inter", "Montserrat", "Arial", "Impact", "Bebas Neue", "Poppins",
             "Roboto", "Helvetica", "Verdana", "Tahoma"]
    font = st.selectbox("Tipografía", FONTS,
                        index=FONTS.index(get_default("font", "Impact"))
                        if get_default("font", "Impact") in FONTS else 3)
    size = st.slider("Tamaño de fuente", 24, 120, get_default("size", 72), step=2)

    cc1, cc2 = st.columns(2)
    with cc1:
        color = st.color_picker("Color de texto", get_default("color", "#FFFFFF"))
    with cc2:
        outline_color = st.color_picker("Color contorno", get_default("outline_color", "#000000"))

    bold = st.checkbox("Negrita", value=get_default("bold", True))

    BG_OPTS = ["Transparente", "Caja negra", "Color personalizado"]
    bg_default = get_default("bg_mode", "Transparente")
    bg_mode = st.radio("Fondo del texto", BG_OPTS, horizontal=False,
                       index=BG_OPTS.index(bg_default) if bg_default in BG_OPTS else 0)
    bg_color = "#000000"
    if bg_mode == "Color personalizado":
        bg_color = st.color_picker("Color de fondo", get_default("bg_color", "#8A2BE2"))

    POS_OPTS = ["Arriba", "Centro", "Abajo"]
    pos_default = get_default("position", "Abajo")
    position = st.radio("Posición vertical", POS_OPTS, horizontal=True,
                        index=POS_OPTS.index(pos_default) if pos_default in POS_OPTS else 2)
    AL_OPTS = ["Izquierda", "Centro", "Derecha"]
    al_default = get_default("align", "Centro")
    align = st.radio("Alineación", AL_OPTS, horizontal=True,
                     index=AL_OPTS.index(al_default) if al_default in AL_OPTS else 1)

    # Karaoke
    karaoke = st.checkbox("🎤  Animación karaoke (palabra-por-palabra)",
                          value=get_default("karaoke", False),
                          help="Resalta cada palabra a medida que se pronuncia. Estilo Hormozi.")
    karaoke_unspoken_color = "#9CA3AF"
    if karaoke:
        karaoke_unspoken_color = st.color_picker(
            "Color palabras no habladas",
            get_default("karaoke_unspoken_color", "#FFFFFF"),
            help="Color de las palabras que aún no se han pronunciado.",
        )

    with st.expander("⚙️  Efectos avanzados"):
        outline_w = st.slider("Grosor del contorno", 0.0, 6.0,
                              float(get_default("outline_w", 2.5)), step=0.5)
        shadow = st.slider("Sombra paralela", 0.0, 6.0,
                           float(get_default("shadow", 1.0)), step=0.5)

    style = {
        "font": font, "size": size, "color": color, "outline_color": outline_color,
        "bg_mode": bg_mode, "bg_color": bg_color, "position": position, "align": align,
        "outline_w": outline_w, "shadow": shadow, "bold": bold,
        "karaoke": karaoke, "karaoke_unspoken_color": karaoke_unspoken_color,
    }

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # ─── Live Preview ───────────────────────────────────────────────────────
    preview_disabled = not (ss.video_path and ss.blocks)
    if st.button("👁️  Vista previa del estilo", disabled=preview_disabled,
                 type="secondary", use_container_width=True, key="btn-preview"):
        wd = get_workdir()
        out_img = os.path.join(wd, f"preview_{uuid.uuid4().hex[:6]}.jpg")
        with st.spinner("Generando preview..."):
            ok, err = render_preview_frame(ss.video_path, ss.blocks, style, out_img)
        if ok:
            ss.preview_path = out_img
        else:
            st.error(f"Error al generar preview: {err[:200]}")

    if ss.preview_path and os.path.exists(ss.preview_path):
        st.image(ss.preview_path, caption="Preview con tu estilo aplicado", use_container_width=True)

    # ─── Render ────────────────────────────────────────────────────────────
    render_disabled = not (ss.video_path and ss.blocks)
    if st.button("🎬  Renderizar vídeo final", disabled=render_disabled,
                 type="primary", use_container_width=True, key="btn-render"):
        wd = get_workdir()
        v_w, v_h = get_video_dimensions(ss.video_path)
        ass_content = build_ass_file(ss.blocks, style, v_w, v_h)
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
