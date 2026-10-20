#!/usr/bin/env python3
"""English Interview Clipper — guided CLI.

    python run.py --build-exam-words     one-time setup
    python run.py --url <youtube-url>     full pipeline guided run

The CLI walks through every mandatory gate from SKILL.md. Steps that need
human eyes (opening-logo frames, sample frames, content screening, final
review, publishing) pause and ask — the agent running this must not skip
them.
"""
import argparse
import json
import os
import subprocess
import sys

import clipper

WORK = os.environ.get("CLIPPER_WORKDIR", os.path.join(os.getcwd(), "work"))


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r


def check_env():
    problems = []
    for bin_ in ("ffmpeg", "ffprobe"):
        if sh(["which", bin_]).returncode != 0:
            problems.append(f"missing system binary: {bin_}")
    try:
        import wordfreq  # noqa: F401
    except ImportError:
        problems.append("wordfreq not installed (pip install wordfreq) — "
                        "vocab stage will refuse to run without it")
    for mod in ("yt_dlp", "faster_whisper", "PIL"):
        try:
            __import__(mod)
        except ImportError:
            problems.append(f"python module missing: {mod} "
                            f"(pip install -r requirements.txt)")
    if not os.path.exists("exam_words.json"):
        problems.append("exam_words.json missing — run --build-exam-words")
    return problems


def cmd_build_exam_words(_a):
    clipper.build_exam_words("exam_words.json")
    print("setup step done.")


def cmd_run(a):
    problems = check_env()
    if problems:
        print("Environment problems — fix these first:")
        for p in problems:
            print("  -", p)
        sys.exit(2)
    os.makedirs(WORK, exist_ok=True)

    print("[0/10] redistribution check (mandatory gate)...")
    chk = clipper.check_redistribution(a.url)
    if not chk["ok"]:
        print("       REFUSED: source explicitly prohibits rebroadcasting.")
        for f in chk["flags"]:
            print("       -", f)
        print("       Stopping. Tell the user and ask how to proceed.")
        sys.exit(3)
    if chk["flags"]:
        print("       note:", chk["flags"], "(metadata unavailable — user decides)")
    else:
        print("       no explicit prohibition found.")

    print("[1/10] downloading (1080p preferred, min 720p)...")
    src = clipper.download(a.url, WORK)
    h = json.loads(sh(["ffprobe", "-v", "error", "-select_streams", "v:0",
                       "-show_entries", "stream=height", "-of", "json",
                       src]).stdout)["streams"][0]["height"]
    assert int(h) >= 720, f"source height {h} < 720p, refusing"
    print("       source:", src, f"{h}p")

    print("[2/10] opening-logo + ending inspection — frames in", WORK)
    frames = clipper.extract_first_frames(src, WORK)
    for f in frames:
        print("       ", f)
    print("       Also inspect the LAST 15 s for end cards/logos:")
    for t in ("end-15", "end-10", "end-5", "end-1"):
        print("       ", f"ffmpeg -ss {t} -i {src} -frames:v 1 ...")
    trim_in = input("       Look at head_0/0.1/0.15: any logo ident or fade ghost? "
                    "If yes, enter seconds to trim (e.g. 4.3), else 0: ").strip()
    # NOTE: the agent must actually look at the frames before answering.
    trim_s = float(trim_in or 0)
    end_trim_in = input("       End card/logo start time in seconds (e.g. 1616), "
                        "else 0 to keep to the end: ").strip()
    end_trim_s = float(end_trim_in or 0)
    print("[3/9] transcribing (faster-whisper, word timestamps)...")
    segs = None
    if trim_s > 0:
        print(f"       trimming {trim_s}s opening...")
        trimmed = os.path.join(WORK, "source_trimmed.mp4")
        # trim the video first, then transcribe: no timestamp shifting needed
        clipper.trim_opening(src, trim_s, [], trimmed)
        src = trimmed
    print("[3/9] transcribing (faster-whisper, word timestamps)...")
    segs = clipper.transcribe(src)
    segs = clipper.merge_short(segs)
    segs = clipper.split_sentences(segs)
    json.dump(segs, open(os.path.join(WORK, "segments_raw.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"       {len(segs)} sentence segments")

    print("[4/9] translating EN->ZH...")
    texts = [s["text"] for s in segs]
    zh = clipper.translate_batch(texts)
    subs = {str(i): z for i, z in enumerate(zh)}
    json.dump(subs, open(os.path.join(WORK, "subs.json"), "w"),
              ensure_ascii=False, indent=1)

    print("[5/9] CONTENT SCREENING (mandatory) — read every segment.")
    hits = clipper.flag_sensitive(segs)
    if hits:
        print("       keyword hits at segment indexes:", hits)
    print("       segments file:", os.path.join(WORK, "segments_raw.json"))
    print("       If any segment has negative remarks about China, cut it")
    print("       with clipper.cut_ranges() before continuing.")
    input("       Press Enter when screening is done...")

    print("[6/9] extracting vocab (CET-4 -> IELTS, no cap)...")
    vocab = clipper.extract(segs)
    print(f"       {len(vocab)} words, e.g.",
          ", ".join(v["word"] for v in vocab[:8]))
    vocab = clipper.gloss(vocab, clipper.translate_batch)
    clipper.save(vocab, os.path.join(WORK, "vocab.json"))

    print("[7/9] SAMPLE FRAMES — render 3 quick samples, get approval.")
    print("       (agent: compose short previews, show the user, wait)")
    input("       Press Enter when the user approved the layout...")

    print("[8/10] composing full 1080x1920 video (this takes a while)...")
    for i, s in enumerate(segs):
        s["zh"] = subs.get(str(i), "")
    if end_trim_s > 0:
        segs = [s for s in segs if s["start"] < end_trim_s]
        for s in segs:
            s["end"] = min(s["end"], end_trim_s)
        print(f"       trimmed ending at {end_trim_s}s, {len(segs)} segments kept")
    out = os.path.join(WORK, "final.mp4")
    clipper.compose(src, segs, vocab, out,
                    total=end_trim_s if end_trim_s > 0 else None)
    print("       FINAL:", out)

    print("[9/10] fan-group assets (§13/§14) + 2s source card (§3a)...")
    title = input("       Video publish title (used for {title}.xlsx): "
                  ).strip() or "video"
    src_name = input("       Source name for 2s card [e.g. Korea Society]: "
                     ).strip() or "YouTube"
    intro = os.path.join(WORK, "source_intro.mp4")
    clipper.make_source_intro(src_name, intro)
    print("       2s source card:", intro)
    xlsx = clipper.make_vocab_excel(vocab, title, WORK)
    print("       xlsx:", xlsx)
    dur = float(sh(["ffprobe", "-v", "error", "-show_entries",
                    "format=duration", "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    out]).stdout.strip())
    if dur + 4.0 > 3600:
        print(f"       video is {dur:.0f}s: too long for a single episode — "
              "§12 requires episode splitting first (split_episodes + "
              "per-episode vocab/outro/covers). Skipping auto outro; "
              "handle episodes manually per SKILL.md.")
    else:
        badge = (input("       Account badge for outro card "
                       "[RealTalk英语精选]: ").strip() or "RealTalk英语精选")
        outro = os.path.join(WORK, "outro.mp4")
        clipper.make_outro(len(vocab), outro, badge)
        final_out = os.path.join(WORK, "final_with_cards.mp4")
        clipper.concat_mp4s([intro, out, outro], final_out)
        print("       FINAL (2s source card + main + 4s outro):", final_out)
        out = final_out

    print("[10/10] covers (3:4 + 4:3)...")
    frame = os.path.join(WORK, "cover_src.png")
    sh(["ffmpeg", "-y", "-v", "error", "-ss", "60", "-i", out,
        "-frames:v", "1", "-vf", "scale=1280:720", frame])
    print("       pick a clean frame if needed, then:")
    print("       clipper.make_covers(frame, [line1, line2], kicker,")
    print("                           'N个生词 · 中英逐句精讲', badge, WORK)")
    print()
    print("Done. Publishing to Douyin is a separate user-confirmed step.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-exam-words", action="store_true")
    ap.add_argument("--url")
    a = ap.parse_args()
    if a.build_exam_words:
        cmd_build_exam_words(a)
    elif a.url:
        cmd_run(a)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
