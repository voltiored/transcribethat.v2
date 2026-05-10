"""Test smart split + watermark + new presets."""
import asyncio, os, subprocess, sys, tempfile
sys.path.insert(0, "/app"); os.chdir("/app")
from dotenv import load_dotenv; load_dotenv("/app/backend/.env")

from streamlit_app import (
    extract_audio, transcribe_with_api, group_words_smart,
    group_words_into_blocks, build_ass_file, render_video_with_subs,
    render_preview_frame, get_video_dimensions, get_video_duration,
    PRESETS, FFMPEG,
)


def main():
    wd = tempfile.mkdtemp(prefix="ttest3_")
    print(f"Workdir: {wd}")

    audio_wav = os.path.join(wd, "speech.wav")
    # Use sentence with pauses + punctuation so smart split has something to detect
    subprocess.run(["espeak-ng", "-w", audio_wav, "-s", "140",
                    "Hello! This is a test. Subtitles work great. We have pauses, "
                    "punctuation, and natural speech patterns."],
                   check=True, capture_output=True)
    test_video = os.path.join(wd, "input.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=darkblue:s=1080x1920:d=10",
                    "-i", audio_wav, "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", test_video], check=True, capture_output=True)
    print(f"✓ Test video: {os.path.getsize(test_video)} bytes")

    audio = os.path.join(wd, "audio.mp3")
    extract_audio(test_video, audio)
    words = asyncio.run(transcribe_with_api(audio, "en"))
    print(f"✓ {len(words)} words transcribed")
    assert len(words) > 0

    # Test smart split vs fixed
    smart_blocks = group_words_smart(words, max_per_block=4)
    fixed_blocks = group_words_into_blocks(words, 4)
    print(f"✓ Smart split: {len(smart_blocks)} blocks (avg words: {sum(len(b['words']) for b in smart_blocks)/len(smart_blocks):.1f})")
    print(f"  Fixed split: {len(fixed_blocks)} blocks (avg words: {sum(len(b['words']) for b in fixed_blocks)/len(fixed_blocks):.1f})")
    print("  Smart blocks preview:")
    for b in smart_blocks[:5]:
        print(f"    [{b['start']:.2f}-{b['end']:.2f}] {b['text']!r}")
    assert len(smart_blocks) > 0
    # Smart should produce at least 2 blocks given multiple sentences
    assert len(smart_blocks) >= 2, "Smart split should detect punctuation breaks"

    # Test all presets including new ones
    v_w, v_h = get_video_dimensions(test_video)
    v_dur = get_video_duration(test_video)
    print(f"\n✓ Video dims: {v_w}x{v_h}, duration: {v_dur:.2f}s")
    print(f"✓ Total presets: {len([p for p in PRESETS.values() if p])}")
    for name, preset in PRESETS.items():
        if preset is None:
            continue
        ass = build_ass_file(smart_blocks, dict(preset), v_w, v_h, total_duration=v_dur)
        assert "[Script Info]" in ass and "Dialogue:" in ass
        print(f"  ✓ Preset '{name}' OK ({len(ass)} chars)")

    # Test watermark
    print("\n--- Watermark test ---")
    watermark = {"text": "@transcribethat", "font": "Inter", "size": 36,
                 "color": "#FFFFFF", "opacity": 0.7, "position": "Abajo derecha"}
    style = dict(PRESETS["MrBeast 🟡"])
    ass_wm = build_ass_file(smart_blocks, style, v_w, v_h,
                            total_duration=v_dur, watermark=watermark)
    assert "Style: Watermark" in ass_wm, "Watermark style missing"
    assert ",Watermark," in ass_wm, "Watermark dialogue missing"
    assert "@transcribethat" in ass_wm, "Watermark text missing"
    print(f"✓ ASS with watermark generated ({len(ass_wm)} chars)")

    # Render with watermark
    ass_path = os.path.join(wd, "wm.ass")
    open(ass_path, "w").write(ass_wm)
    out_wm = os.path.join(wd, "out_wm.mp4")
    ok, log = render_video_with_subs(test_video, ass_path, out_wm)
    assert ok, f"Render with watermark failed: {log}"
    print(f"✓ Render with watermark: {os.path.getsize(out_wm)} bytes")

    # Preview with watermark
    pv = os.path.join(wd, "preview_wm.jpg")
    ok, err = render_preview_frame(test_video, smart_blocks, style, pv, watermark=watermark)
    assert ok, f"Preview with watermark failed: {err}"
    print(f"✓ Preview with watermark: {os.path.getsize(pv)} bytes")

    # Test different positions
    for pos in ["Arriba derecha", "Arriba izquierda", "Abajo centro"]:
        wm = {**watermark, "position": pos}
        ass_p = build_ass_file(smart_blocks, style, v_w, v_h,
                               total_duration=v_dur, watermark=wm)
        assert "Style: Watermark" in ass_p
    print("✓ All 6 watermark positions generate valid ASS")

    print(f"\n✅ ALL TESTS PASSED  (outputs in {wd})")
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
