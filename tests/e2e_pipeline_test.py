"""Functional end-to-end test of the TranscribeThat pipeline."""
import asyncio
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, "/app")
os.chdir("/app")

# Force-load env
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from streamlit_app import (
    extract_audio, transcribe_with_api, group_words_into_blocks,
    build_ass_file, render_video_with_subs, get_video_dimensions,
    hex_to_ass_color, seconds_to_ass_time, FFMPEG, FFPROBE,
)


def main():
    print(f"FFMPEG: {FFMPEG}")
    print(f"FFPROBE: {FFPROBE}")
    print(f"EMERGENT_LLM_KEY set: {bool(os.environ.get('EMERGENT_LLM_KEY'))}")

    # 1) Create a test video with TTS-like audio
    wd = tempfile.mkdtemp(prefix="ttest_")
    print(f"Workdir: {wd}")

    # Generate a 5-second 1080x1920 video with sine-wave audio
    # We need REAL speech for whisper; fall back: use eSpeak if present, else just test infra
    test_video = os.path.join(wd, "input.mp4")

    # Try to generate speech via espeak-ng if available, else use simple beeps
    espeak_ng = subprocess.run(["which", "espeak-ng"], capture_output=True, text=True).stdout.strip()
    audio_wav = os.path.join(wd, "speech.wav")
    if espeak_ng:
        subprocess.run([espeak_ng, "-w", audio_wav, "-s", "140",
                        "Hello this is a test of TranscribeThat. Subtitles work great."],
                       check=True, capture_output=True)
        print("Generated speech with espeak-ng")
    else:
        print("espeak-ng not available, installing...")
        subprocess.run(["apt-get", "install", "-y", "-q", "espeak-ng"],
                       capture_output=True, check=False)
        espeak_ng = subprocess.run(["which", "espeak-ng"], capture_output=True, text=True).stdout.strip()
        if espeak_ng:
            subprocess.run([espeak_ng, "-w", audio_wav, "-s", "140",
                            "Hello this is a test of TranscribeThat. Subtitles work great."],
                           check=True, capture_output=True)
            print("Generated speech with espeak-ng")
        else:
            print("ERROR: cannot synthesize speech")
            return False

    # Combine into MP4 (1080x1920 vertical, 6s)
    cmd = [FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=blue:s=1080x1920:d=6",
           "-i", audio_wav, "-shortest",
           "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", test_video]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"FFmpeg input gen failed: {res.stderr[-500:]}"
    print(f"Test video created: {test_video} ({os.path.getsize(test_video)} bytes)")

    # 2) Extract audio
    audio_path = os.path.join(wd, "audio.mp3")
    assert extract_audio(test_video, audio_path), "extract_audio failed"
    print(f"Audio extracted: {audio_path} ({os.path.getsize(audio_path)} bytes)")

    # 3) Transcribe
    words = asyncio.run(transcribe_with_api(audio_path, language="en"))
    print(f"Words transcribed: {len(words)}")
    for w in words[:8]:
        print(f"  [{w['start']:.2f}-{w['end']:.2f}] {w['word']}")
    assert len(words) > 0, "No words returned from transcription"

    # 4) Group into blocks
    blocks = group_words_into_blocks(words, 3)
    print(f"Blocks (3 words): {len(blocks)}")
    for b in blocks[:5]:
        print(f"  [{seconds_to_ass_time(b['start'])} - {seconds_to_ass_time(b['end'])}] {b['text']}")
    assert len(blocks) > 0, "No blocks generated"

    # 5) Build ASS
    style = {
        "font": "Impact", "size": 72, "color": "#FFFF00", "outline_color": "#000000",
        "bg_mode": "Transparente", "bg_color": "#000000",
        "position": "Abajo", "align": "Centro",
        "outline_w": 3.0, "shadow": 1.0, "bold": True,
    }
    v_w, v_h = get_video_dimensions(test_video)
    print(f"Video dims: {v_w}x{v_h}")
    ass_content = build_ass_file(blocks, style, v_w, v_h)
    ass_path = os.path.join(wd, "subs.ass")
    with open(ass_path, "w") as f:
        f.write(ass_content)
    print(f"ASS written: {ass_path} ({len(ass_content)} chars)")
    print("ASS preview (first 800 chars):")
    print(ass_content[:800])

    # 6) Test color conversion
    assert hex_to_ass_color("#FFFFFF") == "&H00FFFFFF", f"Color conv: {hex_to_ass_color('#FFFFFF')}"
    assert hex_to_ass_color("#FF0000") == "&H000000FF", f"Red: {hex_to_ass_color('#FF0000')}"
    assert hex_to_ass_color("#00FF00") == "&H0000FF00", f"Green: {hex_to_ass_color('#00FF00')}"
    print("Color conversions OK")

    # 7) Render
    out_path = os.path.join(wd, "output.mp4")
    progress_log = []
    ok, log = render_video_with_subs(test_video, ass_path, out_path,
                                     progress_cb=lambda p: progress_log.append(p))
    print(f"Render OK: {ok}")
    print(f"Progress samples: {progress_log[:3]} ... {progress_log[-3:]}")
    if not ok:
        print(f"Render log:\n{log}")
        return False
    assert os.path.exists(out_path) and os.path.getsize(out_path) > 5000, "Output video too small"
    print(f"Output: {out_path} ({os.path.getsize(out_path)} bytes)")

    # 8) Verify output has burned-in subs (just check stream)
    res = subprocess.run([FFPROBE, "-v", "quiet", "-print_format", "csv",
                          "-show_entries", "stream=codec_type,width,height", out_path],
                         capture_output=True, text=True)
    print(f"Output streams:\n{res.stdout}")

    print("\n✅ ALL TESTS PASSED")
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
