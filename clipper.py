"""English Interview Clipper — full pipeline in one module.

Stages: download (1080p-preferred) -> transcribe (faster-whisper) ->
translate (EN->ZH) -> screen -> vocab (CET-4->IELTS) -> compose (1080x1920) ->
covers (3:4 + 4:3).

HARD RULE: the interpreter running the vocab stage MUST have `wordfreq`
installed. extract_vocab() raises RuntimeError if it is missing — the zipf
filter must never be silently skipped.
"""


# ======================================================================
# SECTION: download (from download.py)
# ======================================================================
"""Download stage: fetch a YouTube video (or any URL yt-dlp supports) as mp4."""
import os
import subprocess
import sys

# robust: invoke via the current interpreter so venv installs are found
YTDLP = os.environ.get("YTDLP_BIN", "").split() or [sys.executable, "-m", "yt_dlp"]


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r


def download(url: str, out_dir: str, basename: str = "source",
             max_height: int = 1080, section: str | None = None) -> str:
    """Download url to out_dir/basename.mp4. Returns the file path.

    Tries the default player client first, falls back to the android client
    (works around 'Sign in to confirm you're not a bot' on datacenter IPs).
    section: optional yt-dlp --download-sections value, e.g. "*00:00-02:00"
    (handy for tests).
    """
    os.makedirs(out_dir, exist_ok=True)
    out_tpl = os.path.join(out_dir, basename + ".%(ext)s")
    fmt = f"bv*[height<={max_height}]+ba/b[height<={max_height}]/b"

    attempts = [
        [],
        ["--extractor-args", "youtube:player_client=android"],
        ["--extractor-args", "youtube:player_client=web_embedded"],
    ]
    if os.environ.get("CLIP2VERTICAL_INSECURE_SSL") == "1":
        # sandbox egress proxy does TLS interception with a self-signed cert
        attempts = [[*a, "--no-check-certificate"] for a in attempts]
    last_err = ""
    for extra in attempts:
        cmd = [*YTDLP, *extra, "-f", fmt, "--merge-output-format", "mp4",
               "-o", out_tpl, "--no-playlist"]
        if section:
            cmd += ["--download-sections", section, "--force-keyframes-at-cuts"]
        cmd.append(url)
        r = _run(cmd)
        if r.returncode == 0:
            for ext in ("mp4", "mkv", "webm"):
                p = os.path.join(out_dir, f"{basename}.{ext}")
                if os.path.exists(p):
                    return p
            # merged with different naming; pick newest media file
            cands = [os.path.join(out_dir, f) for f in os.listdir(out_dir)
                     if f.startswith(basename) and f.rsplit(".", 1)[-1] in ("mp4", "mkv", "webm")]
            if cands:
                return max(cands, key=os.path.getmtime)
        last_err = (r.stderr or r.stdout or "")[-500:]
    raise RuntimeError(f"download failed for {url}: {last_err}")


def probe_title(url: str) -> str:
    r = _run([*YTDLP, "--skip-download", "--print", "title",
              "--extractor-args", "youtube:player_client=android", url])
    return (r.stdout or "").strip()


if __name__ == "__main__":
    url = sys.argv[1]
    print("title:", probe_title(url))
    print("file:", download(url, sys.argv[2] if len(sys.argv) > 2 else "/tmp",
                            section=sys.argv[3] if len(sys.argv) > 3 else None))


# ======================================================================
# SECTION: transcribe (from transcribe.py)
# ======================================================================
"""Transcribe stage: faster-whisper -> segments with word timestamps."""
import json
import os
import re
import sys

MODEL = os.environ.get("WHISPER_MODEL", "small")


def _get_model():
    from faster_whisper import WhisperModel
    _patch_av_open()
    # prefer a bundled local model dir (avoids HF download, e.g. behind proxy)
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "models", f"faster-whisper-{MODEL}")
    path = os.path.normpath(local) if os.path.isdir(local) else MODEL
    # models are cached under ~/.cache/huggingface (mount a volume in docker)
    return WhisperModel(path, device="cpu", compute_type="int8")


def _patch_av_open():
    """Compat: faster-whisper 1.2.1 calls av.open(..., metadata_errors='ignore')
    which PyAV 19.0.1 does not accept. Drop the kwarg; default behavior is fine."""
    try:
        import av
        if getattr(av.open, "_cv_patched", False):
            return
        _orig = av.open

        def _open(*a, **k):
            k.pop("metadata_errors", None)
            return _orig(*a, **k)

        _open._cv_patched = True
        av.open = _open
    except Exception:
        pass


def transcribe(media_path: str, language: str = "en") -> list[dict]:
    """Return [{start, end, text, words:[{start,end,word}]}]."""
    model = _get_model()
    segments, _info = model.transcribe(
        media_path, language=language, word_timestamps=True,
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 400},
    )
    out = []
    for s in segments:
        words = [{"start": w.start, "end": w.end, "word": w.word.strip()}
                 for w in (s.words or []) if w.word.strip()]
        out.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                    "words": words})
    return out


def merge_short(segments: list[dict], min_dur: float = 1.6,
                max_chars: int = 90) -> list[dict]:
    """Merge very short segments into the next one for readable subtitles."""
    merged: list[dict] = []
    buf = None
    for s in merged_input(segments):
        if buf is None:
            buf = s
            continue
        if (buf["end"] - buf["start"] < min_dur
                and len(buf["text"]) + len(s["text"]) < max_chars):
            buf = {"start": buf["start"], "end": s["end"],
                   "text": (buf["text"] + " " + s["text"]).strip(),
                   "words": buf["words"] + s["words"]}
        else:
            merged.append(buf)
            buf = s
    if buf:
        merged.append(buf)
    return merged


def _words_text(words):
    # word surfaces may or may not carry leading spaces (varies by run);
    # join robustly and tidy spacing before punctuation.
    t = " ".join(w["word"].strip() for w in words)
    t = re.sub(r"\s+([.,!?;:'\"\)\]])", r"\1", t)
    t = re.sub(r"([(\[])\s+", r"\1", t)
    return t.strip()


def _make_seg(buf, src):
    return {"start": round(buf[0]["start"], 2), "end": round(buf[-1]["end"], 2),
            "text": _words_text(buf), "words": buf}


_SENT_END = re.compile(r"[.!?][\"']?$")
_CLAUSE_END = re.compile(r"[,;:][\"']?$")


def split_sentences(segments: list[dict], max_chars: int = 110) -> list[dict]:
    """Split segments into one-sentence subtitle events.

    Cuts on sentence-ending punctuation using word timestamps for exact
    boundaries; over-long sentences are further cut on clause punctuation
    or hard-split by word count. Tiny tails are merged into the previous
    piece. Each output is [{start, end, text, words}].
    """
    out = []
    for s in segments:
        words = s.get("words") or []
        if not words:  # no word timings: regex fallback, proportional timing
            parts = re.split(r"(?<=[.!?])\s+", s["text"])
            dur = max(s["end"] - s["start"], 0.1)
            total = sum(len(p) for p in parts) or 1
            t = s["start"]
            for p in parts:
                d = dur * len(p) / total
                out.append({"start": round(t, 2), "end": round(t + d, 2),
                            "text": p.strip(), "words": []})
                t += d
            continue
        buf = []
        for w in words:
            buf.append(w)
            txt = _words_text(buf)
            surf = w["word"].strip()
            if _SENT_END.search(surf) and len(txt) >= 20:
                out.append(_make_seg(buf, s))
                buf = []
            elif len(txt) > max_chars and _CLAUSE_END.search(surf):
                out.append(_make_seg(buf, s))
                buf = []
            elif len(txt) > int(max_chars * 1.5):
                out.append(_make_seg(buf, s))
                buf = []
        if buf:
            if out and len(_words_text(buf)) < 15 and \
                    out[-1]["end"] >= buf[0]["start"] - 2.0:
                prev = out[-1]
                prev["words"] = prev.get("words", []) + buf
                prev["end"] = round(buf[-1]["end"], 2)
                prev["text"] = _words_text(prev["words"])
            else:
                out.append(_make_seg(buf, s))
    return out


def merged_input(segments):
    return segments


def save(segments: list[dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=1)


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    segs = transcribe(sys.argv[1])
    segs = merge_short(segs)
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/transcript.json"
    save(segs, out)
    print(f"{len(segs)} segments -> {out}")
    for s in segs[:5]:
        print(f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}")


# ======================================================================
# SECTION: translate (from translate.py)
# ======================================================================
"""Translate stage: English -> Simplified Chinese.

Provider order:
1. OpenAI-compatible API (env TRANSLATE_BASE_URL / TRANSLATE_API_KEY /
   TRANSLATE_MODEL) - best quality, configured in the management UI.
2. Argos Translate offline (argos-translate + en->zh model) - zero-config fallback.
"""
import json
import os
import urllib.request

BASE_URL = os.environ.get("TRANSLATE_BASE_URL", "").rstrip("/")
API_KEY = os.environ.get("TRANSLATE_API_KEY", "")
MODEL = os.environ.get("TRANSLATE_MODEL", "gpt-4o-mini")


def configure(base_url: str = "", api_key: str = "", model: str = ""):
    """Runtime reconfiguration (e.g. from management UI settings)."""
    global BASE_URL, API_KEY, MODEL
    if base_url is not None:
        BASE_URL = base_url.rstrip("/")
    if api_key:
        API_KEY = api_key
    if model:
        MODEL = model

SYSTEM_PROMPT = (
    "You translate English interview subtitles into Simplified Chinese. "
    "Rules: one line per input line, same order, no numbering, no explanations. "
    "Keep it concise and spoken-style, like video subtitles. "
    "Translate 'you' as '你'."
)


def _openai_translate(texts: list[str]) -> list[str]:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "\n".join(texts)},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        BASE_URL + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {API_KEY}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    content = data["choices"][0]["message"]["content"].strip()
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    if len(lines) != len(texts):
        # fall back to 1:1 best effort rather than misaligning subtitles
        raise RuntimeError(
            f"translate line-count mismatch: {len(lines)} vs {len(texts)}")
    return lines


_argos = None


def _argos_translate(texts: list[str]) -> list[str]:
    global _argos
    if _argos is None:
        try:
            import argostranslate.translate as T
        except ImportError:  # very old forks used an underscore name
            import argos_translate.translate as T
        installed = T.get_installed_languages()
        src = next((l for l in installed if l.code == "en"), None)
        if src is None:
            raise RuntimeError("argos en->zh model not installed")
        dst = next(l for l in src.translations if l.to_lang.code == "zh")
        _argos = dst
    return [_argos.translate(t) for t in texts]


def provider_name() -> str:
    if BASE_URL and API_KEY:
        return f"openai-compatible ({MODEL})"
    return "argos-offline"


def translate_batch(texts: list[str], batch_size: int = 20) -> list[str]:
    """Translate a list of English strings to Simplified Chinese, order kept."""
    if not texts:
        return []
    out: list[str] = []
    use_openai = bool(BASE_URL and API_KEY)
    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i + batch_size]
        try:
            out.extend(_openai_translate(chunk) if use_openai
                       else _argos_translate(chunk))
        except Exception as e:
            if use_openai:
                # one retry via argos before giving up on the chunk
                out.extend(_argos_translate(chunk))
            else:
                raise RuntimeError(f"translation failed: {e}")
    return out


if __name__ == "__main__":
    import sys
    print("provider:", provider_name())
    print(translate_batch(sys.argv[1:]))


# ======================================================================
# SECTION: vocab (from vocab.py)
# ======================================================================
"""Vocab stage: extract learning-worthy words with frequency counts.

Mirrors the reference format: word + Chinese gloss + xN count.
Filters out stopwords and very common words so the list has learning value.
"""
import json
import re
import sys
from collections import Counter

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z\-']*[a-zA-Z]|[a-zA-Z]")


def _dwidth(s: str) -> int:
    """Display width: CJK counts as 2, Latin as 1."""
    return sum(2 if ord(c) > 0x2E7F else 1 for c in s)


def _pad(s: str, width: int) -> str:
    """Pad to fixed display width so columns align across rows."""
    return s + " " * max(0, width - _dwidth(s))

STOPWORDS = set("""
a about above after again against all am an and any are as at be because been
before being below between both but by can cannot could did do does doing don
down during each few for from further had has have having he her here hers
herself him himself his how i if in into is it its itself me more most my
myself no nor not now of off on once only or other ought our ours ourselves
out over own same she should so some such than that the their theirs them
themselves then there these they this those through to too under until up
very was we were what when where which while who whom why with would you
your yours yourself yourselves it's i'm we're you're they're we've they'll
that's there's let's isn't aren't wasn't weren't don't doesn't didn't won't
wouldn't can't couldn't shouldn't hasn't have't gonna wanna just really
also even ever never always often much many get got going go goes went
make made take took come came see saw know knew think thought look looked
like liked want wanted need needed use used work worked way thing things
one two three first new good great big small old young high low long short
much right left well much still yet already also even back much
""".split())

# very common words not worth listing for learners (beyond stopwords)
BASIC = set("""
time year people day man world life hand part child eye woman place week
case point company number group problem fact money story young area money
able sure enough able ago almost along already also although among amount
another anyone around away become became become behind better body book
business call change children city close country course cut different
door early earth end enough every example face father feel few field
figure fire five follow force four free friend front full game gave given
government great green ground group grow half happen hard hear heard heart
hour house however hundred husband idea ii iii keep kind knew known land
large last late later laugh learn least leave left less let letter light
live local long look lose lot love low machine major maybe mean means
measure men might mile million mind minute miss money month morning
mother move music must name nation near nearly need never night none
north nothing notice number often oil order other others outside owner
page paper part party peace person phone picture piece place plane plant
play point police power press price produce product pull push put question
quick quite race radio raise range rate rather reach ready real room
round rule run school science sea second seem serve seven shall shape
share short since six size skill sleep small smile song soon sound south
space speak speed spend spoke stand start state stay step still stood
stop store story street strong study stuff style such sure table taken
talk teach team tell ten test thank third those though thought three
today together told took top total touch town trade train travel tree
trouble true try turn twice type understand until upon value various
visit voice wait walk wall watch water white whole whose wife will
window wish without woman women wonder wood word work world worth
would write written wrong wrote yard yeah yes yesterday young
car guy job done seen anything anybody everybody everyone everything
anyone someone something nothing build built needs kept keeps hold
holding open ai
""".split())

SKIP = STOPWORDS | BASIC

# brand/company/product names that often appear lowercase in transcripts
BRANDS = set("""
anthropic openai chatgpt claude gemini grok llama mistral qwen deepseek
nvidia tesla google apple microsoft meta amazon intel amd tiktok douyin
youtube twitter xAI spacex
""".split())
SKIP = SKIP | BRANDS

_SENT_END = re.compile(r"[.!?]\s*$")


def _proper_nouns(segments: list[dict]) -> set[str]:
    """Words capitalized mid-sentence are probably proper nouns (names, brands)."""
    proper = set()
    for s in segments:
        text = s["text"]
        # sentence starts: beginning or after . ! ?
        for m in re.finditer(r"[A-Za-z][a-zA-Z\-']*", text):
            w = m.group(0)
            if not w[0].isupper():
                continue
            prev = text[:m.start()].rstrip()
            at_start = (not prev) or prev[-1] in ".!?"
            if not at_start and len(w) > 1:
                proper.add(w.lower())
    return proper


def _load_exam_words():
    """Load CET-4 / IELTS word sets + inflection->lemma map (ECDICT-derived)."""
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "exam_words.json")
    if not os.path.exists(path):
        raise RuntimeError(
            "exam_words.json not found. Run one-time setup first: "
            "`python run.py --build-exam-words` (downloads ECDICT and "
            "builds the CET-4/IELTS word lists).")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return set(d["cet4"]), set(d["ielts"]), d["lemma"]


_CET4, _IELTS, _LEMMA = _load_exam_words()

# words this frequent are known to any CET-4 learner even if untagged
TOO_EASY_ZIPF = 4.6


def extract(segments: list[dict], top_n: int = 150,
            min_len: int = 3) -> list[dict]:
    """CET-4 -> IELTS oriented vocab extraction.

    Audience: passed CET-4, preparing for IELTS.
    - lemma-aware: getting->get, daughters->daughter (via ECDICT exchange map)
    - excludes anything a CET-4 learner already knows: stopwords, BASIC list,
      proper nouns, brands, CET-4-tagged words, or zipf > 5.0
    - tier 0: IELTS-tagged words (the exam sweet spot)
    - tier 1: other unfamiliar words (CET-6/TOEFL/GRE level etc.)
    - within a tier, more frequent in the video ranks higher
    - keeps unfamiliar words even at count == 1 (never miss a hard word)
    Returns [{word, count}].
    """
    try:
        from wordfreq import zipf_frequency
    except ImportError:
        raise RuntimeError(
            "wordfreq is NOT installed in this Python environment. "
            "The zipf-frequency filter is mandatory for vocab quality; "
            "install it (pip install wordfreq) and re-run. "
            "Refusing to continue with the filter silently disabled.")
    proper = _proper_nouns(segments)
    counts: Counter = Counter()
    for s in segments:
        for w in WORD_RE.findall(s["text"]):
            w = w.lower().strip("-'")
            if (len(w) < min_len or w in SKIP or w in proper
                    or w.replace("-", "").replace("'", "").isdigit()):
                continue
            counts[w] += 1
    scored = []
    for w, c in counts.items():
        lemma = _LEMMA.get(w, w)
        if lemma in _CET4:
            continue
        z = max(zipf_frequency(w, "en"), zipf_frequency(lemma, "en"))
        if z == 0.0 and c < 3:
            continue  # likely transcription noise
        if z > TOO_EASY_ZIPF:
            continue  # known to any CET-4 learner
        tier = 0 if lemma in _IELTS else 1
        scored.append((tier, -c, w))
    scored.sort()
    return [{"word": w, "count": -negc} for tier, negc, w in scored[:top_n]]


def gloss(vocab: list[dict], translate_fn) -> list[dict]:
    """Add Chinese gloss to each vocab item via translate_fn(texts)->texts."""
    words = [v["word"] for v in vocab]
    glosses = translate_fn([f"{w} (as a vocabulary word, give only the Chinese meaning) "
                            for w in words])
    for v, g in zip(vocab, glosses):
        v["gloss"] = g.strip()
    return vocab


def save(vocab: list[dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(vocab, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    segs = json.load(open(sys.argv[1], encoding="utf-8"))
    vocab = extract(segs, top_n=int(sys.argv[2]) if len(sys.argv) > 2 else 120)
    print(f"{len(vocab)} words")
    for v in vocab[:20]:
        print(f"{v['word']:20s} x{v['count']}")


# ======================================================================
# SECTION: compose (from compose.py)
# ======================================================================
"""Compose stage: build the 1080x1920 vertical video.

Layout (1080x1920) — clean and simple:
  y 0-470     vocab panel (header + 5 scrolling rows, follows speech)
  y 500-1108  source interview video (16:9 fitted, centered)
  y ~1150+    subtitles: EN (white, vocab words in yellow bold) close above
              ZH translation (gold), one segment at a time

Text is rendered with libass from a generated .ass file; the vocab panel
background is a static PNG overlay (looped input, like subtitles).
"""
import json
import os
import re
import subprocess
import sys

W, H = 1080, 1920
VID_H = 608
VID_Y = 610          # video top edge (below vocab panel)
PANEL_Y = 170        # vocab panel top (below iPhone Dynamic Island / notch safe area)
PANEL_H = 400
SUB_EN_Y = 1300
SUB_ZH_Y = 1440
FONT = "Noto Sans CJK SC"

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z\-']*[a-zA-Z]|[a-zA-Z]")


def _ass_time(s: float) -> str:
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def _words_in(text: str, vocab_index: dict) -> list[dict]:
    seen, out = set(), []
    for w in WORD_RE.findall(text):
        wl = w.lower().strip("-'")
        if wl in vocab_index and wl not in seen:
            seen.add(wl)
            out.append(vocab_index[wl])
    return out


def _occurrences(segments: list[dict], vocab_index: dict) -> list[dict]:
    """Flatten vocab-word occurrences in speaking order with timestamps.

    Uses word-level timestamps when available, else the segment start.
    Returns [{word, gloss, count, start}].
    """
    occs = []
    for s in segments:
        words = s.get("words") or []
        if words:
            for w in words:
                wl = w["word"].lower().strip("-'")
                if wl in vocab_index:
                    v = vocab_index[wl]
                    occs.append({"word": v["word"], "gloss": v.get("gloss", ""),
                                 "count": v["count"], "start": w["start"]})
        else:
            for v in _words_in(s["text"], vocab_index):
                occs.append({"word": v["word"], "gloss": v.get("gloss", ""),
                             "count": v["count"], "start": s["start"]})
    # drop consecutive duplicates of the same word (stutter in timestamps)
    dedup = []
    for o in occs:
        if dedup and dedup[-1]["word"] == o["word"] \
                and o["start"] - dedup[-1]["start"] < 1.0:
            continue
        dedup.append(o)
    return dedup


def _highlight_vocab(text: str, vocab_words: list[str]) -> str:
    """Wrap vocab words in the EN subtitle with yellow-bold ASS overrides.

    Longest words first so e.g. 'chips' matches before 'chip'.
    Original casing is preserved.
    """
    if not vocab_words:
        return text
    pat = re.compile(
        r"\b(" + "|".join(
            re.escape(w) for w in sorted(vocab_words, key=len, reverse=True)
        ) + r")\b",
        re.IGNORECASE,
    )

    def _rep(m):
        return "{\\1c&H0000FFFF&\\b1}" + m.group(1) + \
            "{\\1c&H00FFFFFF&\\b0}"

    return pat.sub(_rep, text)


def build_ass(segments: list[dict], vocab: list[dict], total: float,
              out_path: str, max_rows: int = 5):
    """ASS with: EN/ZH subtitles (explicit positions) + scrolling vocab panel.

    The vocab panel follows the speech: for each vocab-word occurrence
    (word-level timestamps), the panel shows a 5-row window around the
    current word, highlighted gold; header shows progress i/N.
    """
    vocab_index = {v["word"]: v for v in vocab}
    vocab_words = [v["word"] for v in vocab]
    L = []
    L.append("[Script Info]")
    L.append("ScriptType: v4.00+")
    L.append(f"PlayResX: {W}")
    L.append(f"PlayResY: {H}")
    L.append("WrapStyle: 0")
    L.append("ScaledBorderAndShadow: yes")
    L.append("")
    L.append("[V4+ Styles]")
    L.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
             "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
             "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
             "Alignment, MarginL, MarginR, MarginV, Encoding")
    L.append(f"Style: EN,{FONT},58,&H00FFFFFF,&H000019FF,&H00000000,&H80000000,"
             "-1,0,0,0,100,100,0,0,1,3,0,5,60,60,40,1")
    L.append(f"Style: ZH,{FONT},54,&H007BD6F5,&H000019FF,&H00000000,&H80000000,"
             "-1,0,0,0,100,100,0,0,1,3,0,5,60,60,40,1")
    L.append(f"Style: VH,{FONT},40,&H00FFFFFF,&H000019FF,&H00000000,&H80000000,"
             "-1,0,0,0,100,100,0,0,1,2,0,7,40,40,20,1")
    L.append(f"Style: VW,{FONT},44,&H00E0E0E0,&H000019FF,&H00000000,&H80000000,"
             "0,0,0,0,100,100,0,0,1,2,0,7,60,60,20,1")
    L.append(f"Style: VWcur,{FONT},46,&H007BD6F5,&H000019FF,&H00000000,&H80000000,"
             "-1,0,0,0,100,100,0,0,1,2,0,7,60,60,20,1")
    L.append("")
    L.append("[Events]")
    L.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
             "Effect, Text")

    # ---- subtitles: one segment at a time, EN close above ZH ----
    for s in segments:
        a, b = _ass_time(s["start"]), _ass_time(s["end"])
        en = _highlight_vocab(s["text"].replace("\n", " "), vocab_words)
        zh = s.get("zh", "").replace("\n", " ")
        L.append(f"Dialogue: 0,{a},{b},EN,,0,0,0,,{{\\pos(540,{SUB_EN_Y})}}{en}")
        if zh:
            L.append(f"Dialogue: 0,{a},{b},ZH,,0,0,0,,{{\\pos(540,{SUB_ZH_Y})}}{zh}")

    # ---- vocab panel: scrolling window around the current word ----
    occs = _occurrences(segments, vocab_index)
    n = len(vocab)
    if occs:
        # event boundaries: window i lasts from its word start
        # (first window also covers t=0 .. first word) until next word starts
        seen_total = set()
        for i, o in enumerate(occs):
            a = _ass_time(o["start"] if i > 0 else 0.0)
            b = _ass_time(occs[i + 1]["start"] if i + 1 < len(occs) else total)
            seen_total.add(o["word"])
            # unique-word window: current + up to 2 unique before/after
            before, _seen_b = [], set()
            for w in reversed(occs[:i]):
                if w["word"] != o["word"] and w["word"] not in _seen_b:
                    _seen_b.add(w["word"])
                    before.append(w)
                    if len(before) == 2:
                        break
            before.reverse()
            after, _seen_a = [], set()
            for w in occs[i + 1:]:
                if w["word"] != o["word"] and w["word"] not in _seen_a:
                    _seen_a.add(w["word"])
                    after.append(w)
                    if len(after) == 2:
                        break
            win = before + [o] + after
            cur_j = len(before)
            L.append(f"Dialogue: 0,{a},{b},VH,,0,0,0,,"
                     f"{{\\pos(540,{PANEL_Y + 28})}}本集生词 {n} 个  "
                     f"{len(seen_total)}/{n}")
            for j, w in enumerate(win):
                y = PANEL_Y + 88 + j * 72
                style = "VWcur" if j == cur_j else "VW"
                txt = (f"{_pad(w['word'], 18)}  "
                         f"{w.get('gloss', '')}  \u00d7{w['count']}")
                L.append(f"Dialogue: 0,{a},{b},{style},,0,0,0,,"
                         f"{{\\pos(540,{y})}}{txt}")
    else:
        L.append(f"Dialogue: 0,{_ass_time(0)},{_ass_time(total)},VH,,0,0,0,,"
                 f"{{\\pos(540,{PANEL_Y + 28})}}本集生词 {n} 个")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def make_panel_bg(out_path: str):
    from PIL import Image
    img = Image.new("RGBA", (W, PANEL_H), (10, 12, 18, 200))
    img.save(out_path)


def compose(source: str, segments: list[dict], vocab: list[dict],
            out_path: str, total: float | None = None,
            preset: str | None = None):
    """Assemble the final vertical video. segments need 'zh' keys."""
    preset = preset or os.environ.get("CLIP2VERTICAL_PRESET", "medium")
    missing = sum(1 for v in vocab if not v.get("gloss"))
    if missing:
        raise RuntimeError(
            f"{missing}/{len(vocab)} vocab words have no Chinese gloss. "
            "The vocab panel must be bilingual (word + Chinese gloss + "
            "count). Fill the glosses with gloss_vocab() before composing; "
            "refusing to render an English-only panel.")
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", source],
        capture_output=True, text=True)
    src_dur = float(r.stdout.strip())
    total = total or src_dur

    workdir = os.path.dirname(out_path)
    ass_path = os.path.join(workdir, "_compose.ass")
    panel_path = os.path.join(workdir, "_panel.png")
    build_ass(segments, vocab, total, ass_path)
    make_panel_bg(panel_path)

    vf = (
        "[0:v]scale=1080:608:force_original_aspect_ratio=increase,"
        "crop=1080:608,setsar=1,fps=30,split[v0][v1];"
        "[v1]crop=170:125:910:0,boxblur=12[lg];"
        "[v0][lg]overlay=910:0[v];"
        f"[v]pad=1080:1920:0:{VID_Y}:color=black[vp];"
        "[vp][1:v]overlay=0:170[v2];"
        f"[v2]subtitles={ass_path}:fontsdir=/usr/share/fonts,format=yuv420p[out]"
    )
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-i", source,
           "-loop", "1", "-t", f"{total:.3f}", "-i", panel_path,
           "-filter_complex", vf,
           "-map", "[out]", "-map", "0:a?",
           "-c:v", "libx264", "-preset", preset, "-crf", "20",
           "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "128k",
           "-t", f"{total:.3f}", "-movflags", "+faststart", out_path]
    subprocess.run(cmd, check=True)
    return out_path


if __name__ == "__main__":
    # compose.py source.mp4 segments.json vocab.json out.mp4
    segs = json.load(open(sys.argv[2], encoding="utf-8"))
    vocab = json.load(open(sys.argv[3], encoding="utf-8"))
    print(compose(sys.argv[1], segs, vocab, sys.argv[4]))


# ======================================================================
# SECTION: screen — opening-logo trim helpers + content screening
# ======================================================================
"""Helpers for the two mandatory pre-compose gates.

1. Opening logos: extract_first_frames() dumps frames at t=0/0.1/0.15/0.5/
   1/2/3/4/5 for visual inspection; trim_opening() cuts N seconds and
   shifts segment timestamps.
2. Content screening: flag_sensitive() is a keyword pre-filter only — the
   agent MUST still read every segment and cut anything with negative
   remarks about China (or otherwise unsuitable for a mainland audience).
"""
import subprocess as _sp

SENSITIVE_HINTS = (
    "tiananmen", "taiwan independence", "falun", "uyghur", "xinjiang camp",
)


def extract_first_frames(video: str, out_dir: str,
                         times=(0, 0.1, 0.15, 0.5, 1, 2, 3, 4, 5)):
    """Dump small frames for opening-logo inspection. Returns paths."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for t in times:
        p = os.path.join(out_dir, f"head_{t}.png")
        _sp.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", video,
                 "-frames:v", "1", "-vf", "scale=360:640", p], check=True)
        paths.append(p)
    return paths


def trim_opening(video: str, seconds: float, segments: list, out_video: str):
    """Cut `seconds` off the front; shift segment/word timestamps.

    Returns the shifted segment list. Word timestamps shift too.
    """
    _sp.run(["ffmpeg", "-y", "-v", "error", "-ss", str(seconds), "-i", video,
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-c:a", "aac", out_video], check=True)
    out = []
    for s in segments:
        ns, ne = round(s["start"] - seconds, 2), round(s["end"] - seconds, 2)
        if ne <= 0.05:
            continue
        s2 = dict(s)
        s2["start"], s2["end"] = max(ns, 0), ne
        if s2.get("words"):
            s2["words"] = [dict(w, start=max(round(w["start"] - seconds, 2), 0),
                                end=max(round(w["end"] - seconds, 2), 0))
                           for w in s["words"]]
        out.append(s2)
    return out


def cut_ranges(video: str, segments: list, ranges: list, out_video: str):
    """Cut [(start, end)] ranges (sensitive content) from video + subtitles.

    Ranges must be sorted and non-overlapping. Returns shifted segments.
    """
    if not ranges:
        raise ValueError("no ranges to cut")
    import os
    # build a select filter keeping everything outside the ranges
    cond = "+".join(f"between(t,{a},{b})" for a, b in ranges)
    tmp_v = out_video + ".tmp.mp4"
    _sp.run(["ffmpeg", "-y", "-v", "error", "-i", video,
             "-vf", f"select='not({cond})',setpts=N/FRAME_RATE/TB",
             "-af", f"aselect='not({cond})',asetpts=N/SR/TB",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-c:a", "aac", tmp_v], check=True)
    os.replace(tmp_v, out_video)
    # shift subtitles: subtract total cut time before each segment start
    cuts = sorted(ranges)
    out = []
    for s in segments:
        a, b = s["start"], s["end"]
        if any(ca < b and cb > a for ca, cb in cuts):
            continue  # segment touched a cut range: drop it
        shift = sum(cb - ca for ca, cb in cuts if cb <= a)
        s2 = dict(s)
        s2["start"], s2["end"] = round(a - shift, 2), round(b - shift, 2)
        if s2.get("words"):
            s2["words"] = [dict(w, start=round(w["start"] - shift, 2),
                                end=round(w["end"] - shift, 2))
                           for w in s["words"]]
        out.append(s2)
    return out


def _nearest_end(segments: list, t: float) -> float:
    return min(segments, key=lambda s: abs(s["end"] - t))["end"]


def split_episodes(total: float, segments: list, ep_len: float = 59 * 60,
                   min_last: float = 2 * 60, hard_cap: float = 60 * 60):
    """Split a long video into episode (start, end) ranges in seconds.

    - No split when total <= hard_cap (60 min): returns [(0, total)].
    - Cuts snap to subtitle segment boundaries — never mid-sentence:
      each cut is the segment end nearest to the 59-minute mark.
    - The last episode must be longer than min_last (2 min). If the naive
      split would leave a shorter tail, the cut point moves earlier
      ("cutting" adjustment): the tail is absorbed into the final episode.
      If that would exceed hard_cap, the remainder is split evenly in two
      instead — a < 2-minute orphan episode is never shipped.
    Returns [(start_sec, end_sec), ...].
    """
    if total <= hard_cap:
        return [(0.0, total)]
    bounds = [0.0]
    while True:
        start = bounds[-1]
        remaining = total - start
        if remaining <= hard_cap:
            bounds.append(total)
            break
        cut = _nearest_end(segments, start + ep_len)
        if cut <= start:  # no valid cut ahead; force close
            bounds.append(total)
            break
        if 0 < total - cut < min_last:
            if total - start <= hard_cap:
                bounds.append(total)  # absorb the short tail
            else:
                mid = _nearest_end(segments, (start + total) / 2)
                bounds.append(mid if mid > start else (start + total) / 2)
                bounds.append(total)
            break
        bounds.append(cut)
    return list(zip(bounds[:-1], bounds[1:]))


def flag_sensitive(segments: list) -> list:
    """Keyword pre-filter only. The agent must still read everything."""
    hits = []
    for i, s in enumerate(segments):
        low = s["text"].lower()
        if any(h in low for h in SENSITIVE_HINTS):
            hits.append(i)
    return hits


# ======================================================================
# SECTION: cover — 3:4 + 4:3 cover generation
# ======================================================================
"""Generate both cover ratios from a clean interview frame.

make_covers(frame_png, title_lines, kicker, subline, badge, out_dir)
writes cover_34.png (1080x1440) and cover_43.png (1200x900).
"""


def _cover_text(draw, W, y, s, size, fill, font_path, stroke=0):
    from PIL import ImageFont
    f = ImageFont.truetype(font_path, size)
    bb = draw.textbbox((0, 0), s, font=f)
    w = bb[2] - bb[0]
    draw.text(((W - w) / 2, y), s, font=f, fill=fill,
              stroke_width=stroke, stroke_fill=(0, 0, 0))


def make_covers(frame_png: str, title_lines: list, kicker: str,
                subline: str, badge: str, out_dir: str,
                font_bold: str = None, font_reg: str = None):
    """Build cover_34.png and cover_43.png. Returns both paths."""
    import os
    from PIL import Image, ImageDraw, ImageFilter
    fb = font_bold or "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    fr = font_reg or "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    src = Image.open(frame_png).convert("RGB")
    # blur any burned-in corner logo before using the frame
    w0, h0 = src.size
    lg = src.crop((w0 - 175, 0, w0, 130)).filter(ImageFilter.GaussianBlur(14))
    src.paste(lg, (w0 - 175, 0))
    os.makedirs(out_dir, exist_ok=True)

    def base(W, H, fg_w, fg_h, fg_y):
        bg = src.resize((W, H), Image.LANCZOS).filter(
            ImageFilter.GaussianBlur(40))
        bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.35)
        img = bg.copy()
        fg = src.resize((fg_w, fg_h), Image.LANCZOS)
        img.paste(fg, ((W - fg_w) // 2, fg_y))
        return img

    # ---- 3:4 ----
    W, H = 1080, 1440
    img = base(W, H, 1080, 608, 560)
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(560):
        d.rectangle([0, y, W, y + 1],
                    fill=(0, 0, 0, int(215 * (1 - y / 560) ** 1.1)))
    for y in range(1168, H):
        d.rectangle([0, y, W, y + 1],
                    fill=(0, 0, 0, int(200 * (y - 1168) / 272)))
    _cover_text(d, W, 110, kicker, 44, (255, 215, 0), fb)
    _cover_text(d, W, 200, title_lines[0], 92, (255, 255, 255), fb, 3)
    if len(title_lines) > 1:
        _cover_text(d, W, 320, title_lines[1], 92, (255, 215, 0), fb, 3)
    _cover_text(d, W, 445, subline, 48, (255, 255, 255), fr)
    _cover_text(d, W, 1300, badge, 52, (255, 255, 255), fr)
    p34 = os.path.join(out_dir, "cover_34.png")
    img.save(p34)

    # ---- 4:3 ----
    W, H = 1200, 900
    img = base(W, H, 1000, 562, 260)
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(260):
        d.rectangle([0, y, W, y + 1],
                    fill=(0, 0, 0, int(215 * (1 - y / 260) ** 1.1)))
    _cover_text(d, W, 40, kicker, 36, (255, 215, 0), fb)
    _cover_text(d, W, 95, "，".join(title_lines), 54,
                (255, 255, 255), fb, 2)
    _cover_text(d, W, 175, subline, 38, (255, 215, 0), fr)
    p43 = os.path.join(out_dir, "cover_43.png")
    img.save(p43)
    return p34, p43


# ======================================================================
# SECTION: build_exam_words — ECDICT -> exam_words.json (one-time setup)
# ======================================================================
"""Download ECDICT and build exam_words.json.

ECDICT tags used: 'cet4' (3849 words), 'ielts' (5040 words).
Also builds inflection->lemma map from the 'exchange' field (~50k).
"""


def build_exam_words(out_path: str = "exam_words.json",
                     ecdict_url: str = "https://github.com/skywind3000/"
                     "ECDICT/raw/master/ecdict.csv"):
    import csv
    import json
    import os
    import urllib.request
    tmp = "/tmp/ecdict.csv"
    if not os.path.exists(tmp):
        print("downloading ECDICT (~66MB)...", flush=True)
        urllib.request.urlretrieve(ecdict_url, tmp)
    cet4, ielts, lemma = set(), set(), {}
    with open(tmp, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            w = (row.get("word") or "").strip().lower()
            if not w:
                continue
            tags = (row.get("tag") or "").lower()
            if "cet4" in tags:
                cet4.add(w)
            if "ielts" in tags:
                ielts.add(w)
            for ex in (row.get("exchange") or "").split("/"):
                if ":" in ex:
                    form, infl = ex.split(":", 1)
                    if infl and form == "0":  # lemma:inflection
                        lemma[infl.lower()] = w
    # also map common inflections explicitly via the exchange pairs
    with open(tmp, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            w = (row.get("word") or "").strip().lower()
            for ex in (row.get("exchange") or "").split("/"):
                if ":" in ex:
                    kind, form = ex.split(":", 1)
                    form = form.lower()
                    if form and form not in lemma:
                        lemma[form] = w
    json.dump({"cet4": sorted(cet4), "ielts": sorted(ielts), "lemma": lemma},
              open(out_path, "w", encoding="utf-8"))
    print(f"wrote {out_path}: cet4={len(cet4)} ielts={len(ielts)} "
          f"lemma={len(lemma)}", flush=True)
    return out_path
