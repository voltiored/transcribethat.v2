"""End-to-end test of all new features: karaoke, translation, SRT/VTT, preview, presets."""
import asyncio, os, subprocess, sys, tempfile

sys.path.insert(0, "/app"); os.chdir("/app")
from dotenv import load_dotenv; load_dotenv("/app/backend/.env")

from streamlit_app import (
    extract_audio, transcribe_with_api, group_words_into_blocks,
    build_ass_file, render_video_with_subs, render_preview_frame,
    get_video_dimensions, build_srt, build_vtt, translate_blocks,
    PRESETS, FFMPEG, FFPROBE,
)


def main():
    wd = tempfile.mkdtemp(prefix="ttest2_")
    print(f"Workdir: {wd}")

    # 1) Generate test video with TTS
    audio_wav = os.path.join(wd, "speech.wav")
    subprocess.run(["espeak-ng", "-w", audio_wav, "-s", "140",
                    "Hello this is a test of TranscribeThat. Subtitles work great today."],
                   check=True, capture_output=True)
    test_video = os.path.join(wd, "input.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=blue:s=1080x1920:d=7",
                    "-i", audio_wav, "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", test_video], check=True, capture_output=True)
    print(f"✓ Test video: {os.path.getsize(test_video)} bytes")

    # 2) Transcribe
    audio = os.path.join(wd, "audio.mp3")
    extract_audio(test_video, audio)
    words = asyncio.run(transcribe_with_api(audio, "en"))
    print(f"✓ Transcribed {len(words)} words")
    assert len(words) > 0
    blocks = group_words_into_blocks(words, 3)
    print(f"✓ Grouped into {len(blocks)} blocks")
    assert all("words" in b and len(b["words"]) > 0 for b in blocks), "Blocks missing word timings"

    # 3) Test SRT/VTT export
    srt = build_srt(blocks)
    vtt = build_vtt(blocks)
    assert "-->" in srt and srt.startswith("1\n"), f"SRT bad: {srt[:200]}"
    assert vtt.startswith("WEBVTT") and "-->" in vtt, f"VTT bad: {vtt[:200]}"
    print(f"✓ SRT generated ({len(srt)} chars):\n{srt[:200]}")
    print(f"✓ VTT generated ({len(vtt)} chars):\n{vtt[:150]}")

    # 4) Test all 4 presets generate valid ASS
    v_w, v_h = get_video_dimensions(test_video)
    for preset_name, preset in PRESETS.items():
        if preset is None:
            continue
        style = dict(preset)
        ass_content = build_ass_file(blocks, style, v_w, v_h)
        assert "[Script Info]" in ass_content and "Dialogue:" in ass_content
        if style.get("karaoke"):
            assert "\\k" in ass_content, f"Karaoke preset missing \\k tags: {ass_content[:500]}"
        print(f"✓ Preset '{preset_name}' valid ASS ({len(ass_content)} chars, karaoke={style.get('karaoke', False)})")

    # 5) Test karaoke render
    style_kara = dict(PRESETS["Hormozi Karaoke 🎤"])
    ass_path = os.path.join(wd, "kara.ass")
    with open(ass_path, "w") as f:
        f.write(build_ass_file(blocks, style_kara, v_w, v_h))
    out_kara = os.path.join(wd, "out_karaoke.mp4")
    ok, log = render_video_with_subs(test_video, ass_path, out_kara)
    assert ok and os.path.exists(out_kara), f"Karaoke render failed: {log}"
    print(f"✓ Karaoke render OK ({os.path.getsize(out_kara)} bytes)")

    # 6) Test live preview frame
    preview_img = os.path.join(wd, "preview.jpg")
    ok, err = render_preview_frame(test_video, blocks, style_kara, preview_img)
    assert ok and os.path.exists(preview_img), f"Preview failed: {err}"
    print(f"✓ Preview frame OK ({os.path.getsize(preview_img)} bytes)")

    # 7) Test translation
    print("\nTranslating to Spanish...")
    translated = asyncio.run(translate_blocks(blocks, "Spanish"))
    print(f"✓ Translated {len(translated)} blocks:")
    for orig, tr in zip(blocks[:3], translated[:3]):
        print(f"  EN: {orig['text']!r}\n  ES: {tr['text']!r}")
    assert len(translated) == len(blocks)
    # Verify text actually changed
    changed = sum(1 for o, t in zip(blocks, translated) if o["text"] != t["text"])
    print(f"  → {changed}/{len(blocks)} blocks changed")
    assert changed >= len(blocks) // 2, "Translation did not change most blocks"

    # 8) Render with translated blocks (MrBeast preset)
    style_mb = dict(PRESETS["MrBeast 🟡"])
    ass_path2 = os.path.join(wd, "translated.ass")
    with open(ass_path2, "w") as f:
        f.write(build_ass_file(translated, style_mb, v_w, v_h))
    out_tr = os.path.join(wd, "out_translated.mp4")
    ok, log = render_video_with_subs(test_video, ass_path2, out_tr)
    assert ok, f"Translated render failed: {log}"
    print(f"✓ Translated MrBeast render OK ({os.path.getsize(out_tr)} bytes)")

    print("\n✅ ALL FEATURE TESTS PASSED")
    print(f"Outputs in {wd}")
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
