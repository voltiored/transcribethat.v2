"""Test the new HYBRID engine: faster-whisper local + Google Translate (free) + OpenAI BYOK."""
import os, subprocess, sys, tempfile
sys.path.insert(0, "/app"); os.chdir("/app")

# Important: ensure no env keys interfere with local-only test
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("EMERGENT_LLM_KEY", None)

from streamlit_app import (
    extract_audio, transcribe_local, group_words_smart,
    build_ass_file, render_video_with_subs, get_video_dimensions, get_video_duration,
    translate_blocks_google, translate_blocks_dispatch,
    PRESETS, FFMPEG,
)


def main():
    wd = tempfile.mkdtemp(prefix="ttest_hyb_")
    print(f"Workdir: {wd}")

    audio_wav = os.path.join(wd, "speech.wav")
    subprocess.run(["espeak-ng", "-w", audio_wav, "-s", "140",
                    "Hello! This is a test. Subtitles work great today. "
                    "We have multiple sentences here."],
                   check=True, capture_output=True)
    test_video = os.path.join(wd, "input.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=darkblue:s=1080x1920:d=10",
                    "-i", audio_wav, "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", test_video], check=True, capture_output=True)
    print(f"✓ Video: {os.path.getsize(test_video)} bytes")

    audio = os.path.join(wd, "audio.mp3")
    extract_audio(test_video, audio)

    # ─── Test LOCAL transcription with faster-whisper ───────────────────────
    print("\n=== LOCAL transcription (faster-whisper tiny) ===")
    print("Loading model & transcribing...")
    words = transcribe_local(audio, language="en", model_size="tiny")
    print(f"✓ {len(words)} words transcribed locally:")
    for w in words[:8]:
        print(f"   [{w['start']:.2f}-{w['end']:.2f}] {w['word']!r}")
    assert len(words) > 0, "Local transcription returned empty"
    blocks = group_words_smart(words, max_per_block=4)
    print(f"✓ {len(blocks)} blocks (smart split)")

    # ─── Test FREE Google Translate (no key) ────────────────────────────────
    print("\n=== FREE Google Translate (deep-translator) ===")
    translated = translate_blocks_google(blocks, "Spanish")
    print(f"✓ {len(translated)} blocks translated EN→ES (FREE):")
    for o, t in zip(blocks[:3], translated[:3]):
        print(f"   EN: {o['text']!r}")
        print(f"   ES: {t['text']!r}")
    changed = sum(1 for o, t in zip(blocks, translated) if o["text"] != t["text"])
    print(f"   {changed}/{len(blocks)} blocks changed")
    assert changed >= len(blocks) // 2, "Translation didn't change most blocks"

    # ─── Test dispatcher (no key → google) ──────────────────────────────────
    print("\n=== Dispatcher: no key → falls back to Google ===")
    via_dispatch = translate_blocks_dispatch(blocks, "French", api_key=None)
    print("FR sample:", via_dispatch[0]["text"])
    assert via_dispatch[0]["text"] != blocks[0]["text"], "Dispatcher fallback failed"
    print("✓ Dispatcher correctly used Google Translate (no key)")

    # ─── Render with translated text + preset ───────────────────────────────
    v_w, v_h = get_video_dimensions(test_video)
    v_dur = get_video_duration(test_video)
    style = dict(PRESETS["MrBeast 🟡"])
    ass_content = build_ass_file(translated, style, v_w, v_h, total_duration=v_dur)
    ass_path = os.path.join(wd, "subs.ass")
    open(ass_path, "w", encoding="utf-8").write(ass_content)
    out_path = os.path.join(wd, "out.mp4")
    ok, log = render_video_with_subs(test_video, ass_path, out_path)
    assert ok, f"Render failed: {log}"
    print(f"\n✓ Final render OK: {os.path.getsize(out_path)} bytes")

    print(f"\n✅ ALL HYBRID TESTS PASSED — 100% FREE pipeline works")
    print(f"Outputs: {wd}")
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
