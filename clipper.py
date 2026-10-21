"""English Interview Clipper — full pipeline in one module.

Stages: download (1080p-preferred) -> transcribe (faster-whisper) ->
translate (EN->ZH) -> screen -> vocab (beyond high-school level) -> compose
(1080x1920) -> covers (3:4 + 4:3).

HARD RULE: the interpreter running the vocab stage MUST have `wordfreq`
installed. extract() raises RuntimeError if it is missing — the noise
check must never be silently skipped.
"""


# ======================================================================
# SECTION: download (from download.py)
# ======================================================================
"""Download stage: fetch a YouTube video (or any URL yt-dlp supports) as mp4."""
import os
import subprocess
import sys
import string as _string

# punctuation stripped from Whisper word timestamps before vocab lookup
_PUNCT = _string.punctuation

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
TRANSLATE_MODEL = os.environ.get("TRANSLATE_MODEL", "gpt-4o-mini")


def configure(base_url: str = "", api_key: str = "", model: str = ""):
    """Runtime reconfiguration (e.g. from management UI settings)."""
    global BASE_URL, API_KEY, TRANSLATE_MODEL
    if base_url is not None:
        BASE_URL = base_url.rstrip("/")
    if api_key:
        API_KEY = api_key
    if model:
        TRANSLATE_MODEL = model

SYSTEM_PROMPT = (
    "You translate English interview subtitles into Simplified Chinese. "
    "Rules: one line per input line, same order, no numbering, no explanations. "
    "Keep it concise and spoken-style, like video subtitles. "
    "Translate 'you' as '你'."
)


def _openai_translate(texts: list[str]) -> list[str]:
    payload = {
        "model": TRANSLATE_MODEL,
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
        return f"openai-compatible ({TRANSLATE_MODEL})"
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
    """Load exam word sets + inflection->lemma map (ECDICT-derived).

    Sets: gk （高中/高考）, zk （初中/中考）, cet4, cet6, ielts. The
    "already known" baseline is zk ∪ gk (everything up to high school).
    """
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "exam_words.json")
    if not os.path.exists(path):
        raise RuntimeError(
            "exam_words.json not found. Run one-time setup first: "
            "`python run.py --build-exam-words` (downloads ECDICT and "
            "builds the exam word lists).")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return (set(d["gk"]), set(d["zk"]), set(d["cet4"]), set(d["cet6"]),
            set(d["ielts"]), d["lemma"])


_GK, _ZK, _CET4, _CET6, _IELTS, _LEMMA = _load_exam_words()

# "already known" baseline (user rule, 2026-10-21): anything at or below
# high-school level is NOT a new word. zk ∪ gk ≈ 3.7k words.
_BASE_KNOWN = _GK | _ZK


def _load_exemptions():
    """Hard-word exemptions (user rule, 2026-10-21): words that sit in the
    school baseline lists yet are genuinely beyond a high-school graduate
    (e.g. autonomous, breakthrough) still count as new words. The list is
    curated in vocab_exemptions.json and grows through the §7 audit."""
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "vocab_exemptions.json")
    if not os.path.exists(path):
        raise RuntimeError(
            "vocab_exemptions.json not found next to clipper.py — the "
            "hard-word exemption list ships with the skill; restore it.")
    with open(path, encoding="utf-8") as f:
        return set(json.load(f)["exempt"])


_EXEMPT = _load_exemptions()


def extract(segments: list[dict], top_n: int | None = None,
            min_len: int = 3) -> list[dict]:
    """Vocab extraction — baseline: high school (user rule, 2026-10-21).

    A word counts as a NEW word iff it is beyond high-school vocabulary:
    CET-4, CET-6 and IELTS words all count, and so do words that appear
    in no exam list at all. Only words at/below high-school level are
    excluded.
    - lemma-aware: getting->get, daughters->daughter (via ECDICT exchange map)
    - excludes: stopwords, BASIC list, proper nouns, brands, contractions /
      possessives (tokens with an apostrophe), and any word whose lemma is
      in the zk ∪ gk baseline sets
    - NO zipf ceiling: corpus frequency cannot separate high-school-known
      words from CET-4 words (their zipf bands overlap completely), so
      the word lists alone draw the line; the final list is still audited
      word by word before composing (see SKILL.md §7)
    - tier 0: IELTS-tagged, tier 1: CET-4/CET-6-tagged, tier 2: off-list
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
                    or "'" in w  # contractions / possessives are never vocab
                    or w.replace("-", "").replace("'", "").isdigit()):
                continue
            counts[w] += 1
    scored = []
    for w, c in counts.items():
        lemma = _LEMMA.get(w, w)
        if lemma in _BASE_KNOWN and lemma not in _EXEMPT:
            continue  # at/below high-school level — already known
            # (unless exempted as a genuinely hard word, e.g. autonomous)
        z = max(zipf_frequency(w, "en"), zipf_frequency(lemma, "en"))
        if z == 0.0 and c < 3:
            continue  # likely transcription noise
        if lemma in _IELTS:
            tier = 0
        elif lemma in _CET4 or lemma in _CET6:
            tier = 1
        else:
            tier = 2  # in no exam list at all — still counts (user rule)
        scored.append((tier, -c, w))
    scored.sort()
    # No count cap by default (user, 2026-10-20): every word passing the
    # filters is kept. top_n stays available as an explicit override only.
    if top_n is not None:
        scored = scored[:top_n]
    return [{"word": w, "count": -negc} for tier, negc, w in scored]


def gloss(vocab: list[dict], translate_fn) -> list[dict]:
    """Add Chinese gloss to each vocab item via translate_fn(texts)->texts."""
    words = [v["word"] for v in vocab]
    glosses = translate_fn([f"{w} (as a vocabulary word, give only the Chinese meaning) "
                            for w in words])
    for v, g in zip(vocab, glosses):
        v["gloss"] = g.strip()
    return vocab


def add_phonetics(vocab: list[dict], phon_path: str | None = None) -> list[dict]:
    """Add IPA phonetic symbols to vocab entries from phonetics.json.

    Phonetics help learners pronounce correctly.
    Words without a phonetic entry get an empty string (panel skips it).
    """
    import json as _json
    import os as _os
    if phon_path is None:
        phon_path = _os.path.join(_os.path.dirname(__file__), "phonetics.json")
    try:
        with open(phon_path, encoding="utf-8") as f:
            phon = _json.load(f)
    except FileNotFoundError:
        phon = {}
    for v in vocab:
        v["phonetic"] = phon.get(v["word"].lower(), "")
    return vocab


def extract_phrases(segments: list[dict], idiom_path: str | None = None,
                    min_count: int = 1) -> list[dict]:
    """Extract idiomatic phrases (not just single words) from the transcript.

    Phrases like "punch above your weight" and
    "a walk in the park" are high-value for learners. Matches against a
    curated idiom list (idioms.txt). Returns [{word, count, is_phrase=True}].
    """
    import os as _os
    import re as _re
    if idiom_path is None:
        idiom_path = _os.path.join(_os.path.dirname(__file__), "idioms.txt")
    try:
        with open(idiom_path, encoding="utf-8") as f:
            idioms = [l.strip().lower() for l in f if l.strip()]
    except FileNotFoundError:
        return []
    text = " ".join(s["text"] for s in segments).lower()
    found = []
    for idiom in idioms:
        pat = r"\b" + _re.escape(idiom) + r"\b"
        cnt = len(_re.findall(pat, text))
        if cnt >= min_count:
            found.append({"word": idiom, "count": cnt, "is_phrase": True})
    found.sort(key=lambda x: -x["count"])
    return found


def to_traditional(text: str) -> str:
    """Convert Simplified Chinese to Traditional Chinese (for TikTok version).

    Uses OpenCC s2t. The TikTok audience (Taiwan/HK/overseas) reads Traditional.
    """
    try:
        from opencc import OpenCC
    except ImportError:
        raise RuntimeError("opencc-python-reimplemented not installed; "
                           "pip install opencc-python-reimplemented")
    _cc = getattr(to_traditional, "_cc", None)
    if _cc is None:
        _cc = OpenCC("s2t")
        to_traditional._cc = _cc
    return _cc.convert(text)


def vocab_to_traditional(vocab: list[dict]) -> list[dict]:
    """Convert all Chinese glosses in vocab to Traditional Chinese."""
    for v in vocab:
        if v.get("gloss"):
            v["gloss"] = to_traditional(v["gloss"])
    return vocab


def segments_to_traditional(segments: list[dict]) -> list[dict]:
    """Convert all Chinese subtitles (zh) to Traditional Chinese."""
    for s in segments:
        if s.get("zh"):
            s["zh"] = to_traditional(s["zh"])
    return segments


def save(vocab: list[dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(vocab, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    segs = json.load(open(sys.argv[1], encoding="utf-8"))
    vocab = extract(segs, top_n=int(sys.argv[2]) if len(sys.argv) > 2 else None)
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
VID_Y = 656          # video top edge: centered (960-304)
PANEL_Y = 180        # vocab panel top: below iPhone status bar/Dynamic Island (~177px safe)
PANEL_H = 400        # 4 rows
PANEL_L = 290        # vocab text left (centered: (290+790)/2=540)
PANEL_R = 790        # xn right (centered)
ROW_H = 100          # row height for 4 rows
SUB_EN_Y = 1330
SUB_ZH_Y = 1430      # gap 100
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
                # strip ALL surrounding punctuation: Whisper word timestamps
                # often include trailing periods/commas ("optimism."), which
                # would otherwise fail the vocab lookup and leave the word
                # permanently out of the panel progress (e.g. 72/108).
                wl = w["word"].lower().strip(_PUNCT)
                if wl in vocab_index:
                    v = vocab_index[wl]
                    occs.append({"word": v["word"], "gloss": v.get("gloss", ""),
                                 "count": v["count"], "start": w["start"],
                                 "phonetic": v.get("phonetic", ""),
                                 "is_phrase": v.get("is_phrase", False)})
        else:
            for v in _words_in(s["text"], vocab_index):
                occs.append({"word": v["word"], "gloss": v.get("gloss", ""),
                             "count": v["count"], "start": s["start"],
                             "phonetic": v.get("phonetic", ""),
                             "is_phrase": v.get("is_phrase", False)})
    # drop consecutive duplicates of the same word (stutter in timestamps)
    dedup = []
    for o in occs:
        if dedup and dedup[-1]["word"] == o["word"] \
                and o["start"] - dedup[-1]["start"] < 1.0:
            continue
        dedup.append(o)
    # add phrase occurrences: match multi-word phrases against segment text
    # (phrases don't have word-level timestamps, use segment start)
    import re as _re2
    phrases = [v for v in vocab_index.values() if v.get("is_phrase")]
    for s in segments:
        text_low = s["text"].lower()
        for p in phrases:
            pat = r"\b" + _re2.escape(p["word"].lower()) + r"\b"
            if _re2.search(pat, text_low):
                dedup.append({"word": p["word"], "gloss": p.get("gloss", ""),
                              "count": p["count"], "start": s["start"],
                              "is_phrase": True, "phonetic": ""})
    # re-sort by start time (phrases were appended out of order)
    dedup.sort(key=lambda o: o["start"])
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


def _strip_ass_tags(text: str) -> str:
    """Remove ASS override tags {...} for width measurement."""
    return re.sub(r"\{[^}]*\}", "", text)


def _dwidth_char(ch: str) -> float:
    """Display width: CJK full-width = 1.0, ASCII half-width = 0.5."""
    o = ord(ch)
    # CJK Unified Ideographs, CJK punctuation, fullwidth forms
    if (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF or
            0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF):
        return 1.0
    return 0.5


def _text_dwidth(text: str) -> float:
    """Total display width in full-width units (tags excluded)."""
    return sum(_dwidth_char(c) for c in _strip_ass_tags(text))


# Punctuation after which a Chinese line may break (break AFTER these)
_ZH_BREAK_AFTER = "，。！？；：、）】」』…·—～"


def _wrap_zh(text: str, max_units: float = 17.0) -> list[str]:
    """Wrap Chinese subtitle into lines.

    Movie convention: break after punctuation, balance line lengths,
    never break a character, NEVER truncate. Prefers 2 lines; uses 3
    for very long text rather than dropping characters. If a single
    "sentence" needs 3+ lines, the source segment is too long and
    should be split upstream (but we never drop text here).
    """
    text = text.strip()
    if not text or _text_dwidth(text) <= max_units:
        return [text]

    def _split_once(t: str) -> list[str]:
        """Split into 2 at the best punctuation boundary."""
        total = _text_dwidth(t)
        cands = []
        w = 0.0
        for i, ch in enumerate(t):
            w += _dwidth_char(ch)
            if ch in _ZH_BREAK_AFTER and 0 < w < total:
                cands.append((i + 1, w))
        if cands:
            half = total / 2
            best_pos, _ = min(cands, key=lambda p: abs(p[1] - half))
            return [t[:best_pos].strip(), t[best_pos:].strip()]
        # Fallback: balanced character split
        w = 0.0
        half = total / 2
        best_i, best_d = 1, float("inf")
        for i in range(1, len(t)):
            w += _dwidth_char(t[i - 1])
            d = abs(w - half)
            if d < best_d:
                best_d, best_i = d, i
        return [t[:best_i].strip(), t[best_i:].strip()]

    lines = [text]
    # Recursively split the longest line until all fit (max 4 iterations)
    for _ in range(4):
        # Find the longest line
        idx = max(range(len(lines)), key=lambda i: _text_dwidth(lines[i]))
        if _text_dwidth(lines[idx]) <= max_units:
            break
        parts = _split_once(lines[idx])
        lines = lines[:idx] + parts + lines[idx + 1:]
    return [l for l in lines if l]


def _wrap_en(text: str, max_units: float = 30.0) -> list[str]:
    """Wrap English subtitle into at most 2 lines at word boundaries.

    Never breaks a word, NEVER truncates. Balances the two lines.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text or _text_dwidth(text) <= max_units:
        return [text]
    words = text.split(" ")
    # Try every split point, pick the most balanced one where
    # both lines fit within max_units
    total = _text_dwidth(text)
    best = None
    best_d = float("inf")
    for i in range(1, len(words)):
        l1 = " ".join(words[:i])
        l2 = " ".join(words[i:])
        w1, w2 = _text_dwidth(l1), _text_dwidth(l2)
        if w1 <= max_units and w2 <= max_units:
            d = abs(w1 - w2)
            # Prefer splits near the middle and not too lopsided
            if d < best_d:
                best_d, best = d, (l1, l2)
    if best:
        return list(best)
    # Fallback: greedy fill line 1 (should be rare)
    l1_words, w = [], 0.0
    for wd in words:
        ww = _text_dwidth(wd) + (0.5 if l1_words else 0)
        if w + ww <= max_units:
            l1_words.append(wd)
            w += ww
        else:
            break
    if not l1_words:
        l1_words = [words[0]]
    rest = words[len(l1_words):]
    # If rest still too long, hard-split remaining words across (never drop)
    lines = [" ".join(l1_words)]
    cur, cw = [], 0.0
    for wd in rest:
        ww = _text_dwidth(wd) + (0.5 if cur else 0)
        if cw + ww <= max_units:
            cur.append(wd)
            cw += ww
        else:
            lines.append(" ".join(cur))
            cur, cw = [wd], _text_dwidth(wd)
    if cur:
        lines.append(" ".join(cur))
    return lines


def build_ass(segments: list[dict], vocab: list[dict], total: float,
              out_path: str, max_rows: int = 4, traditional: bool = False):
    """ASS with: EN/ZH subtitles (explicit positions) + scrolling vocab panel.

    The vocab panel follows the speech: for each vocab-word occurrence
    (word-level timestamps), the panel shows a 4-row window around the
    current word. EN and ZH same size (52). Selected: EN+ZH+xn all gold,
    no background highlight bar. Header shows progress i/N.
    """
    # v13.1: surface-form-aware index — a vocab word must also match its
    # inflected forms actually spoken (predictions, disrupted, fabs...),
    # otherwise the panel progress stalls and subtitle highlights miss.
    # Forms are derived from the segments text itself (no blind stemming).
    _fulltext = " ".join(s.get("text", "") for s in segments).lower()
    vocab_index = {}
    _forms = []  # surface forms for subtitle highlighting (longest first)
    for v in vocab:
        w = v["word"].lower()
        vocab_index[w] = v
        _forms.append(v["word"])
        for m in set(re.findall(r"\b" + re.escape(w) + r"(?:s|es|d|ed|ing)?\b",
                                _fulltext)):
            if m != w:
                vocab_index.setdefault(m, v)
                _forms.append(m)
    vocab_words = sorted(set(_forms), key=len, reverse=True)
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
    L.append(f"Style: EN,{FONT},64,&H00FFFFFF,&H000019FF,&H00000000,&H80000000,"
             "-1,0,0,0,100,100,0,0,1,3,0,5,60,60,40,1")
    L.append(f"Style: ZH,{FONT},60,&H007BD6F5,&H000019FF,&H00000000,&H80000000,"
             "-1,0,0,0,100,100,0,0,1,3,0,5,60,60,40,1")
    L.append(f"Style: VH,{FONT},44,&H00FFFFFF,&H000019FF,&H00000000,&H80000000,"
             "-1,0,0,0,100,100,0,0,1,2,0,7,40,40,20,1")
    # v12: EN/ZH same size 52, selected = gold bold, no background bar
    L.append(f"Style: VE,{FONT},44,&H00FFFFFF,&H000019FF,&H00000000,&H80000000,"
             "0,0,0,0,100,100,0,0,1,2,0,1,60,60,20,1")
    L.append(f"Style: VEC,{FONT},52,&H007BD6F5,&H000019FF,&H00000000,&H80000000,"
             "-1,0,0,0,100,100,0,0,1,2,0,1,60,60,20,1")
    L.append(f"Style: VWzh,{FONT},44,&H00FFFFFF,&H000019FF,&H00000000,&H80000000,"
             "0,0,0,0,100,100,0,0,1,2,0,1,60,60,20,1")
    L.append(f"Style: VWzhCur,{FONT},52,&H007BD6F5,&H000019FF,&H00000000,&H80000000,"
             "-1,0,0,0,100,100,0,0,1,2,0,1,60,60,20,1")
    L.append(f"Style: VWct,{FONT},40,&H00A0A0A0,&H000019FF,&H00000000,&H80000000,"
             "0,0,0,0,100,100,0,0,1,2,0,3,60,60,20,1")
    L.append(f"Style: VWctCur,{FONT},44,&H007BD6F5,&H000019FF,&H00000000,&H80000000,"
             "-1,0,0,0,100,100,0,0,1,2,0,3,60,60,20,1")
    L.append("")
    L.append("[Events]")
    L.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
             "Effect, Text")

    # ---- subtitles: one segment at a time, EN close above ZH ----
    # Movie convention (2026-10-17): try one line per language; if a line
    # overflows, wrap to 2 lines at natural boundaries (punctuation for ZH,
    # word boundaries for EN). NEVER truncate/drop characters. When a
    # language wraps to 2 lines, shift the block to keep EN/ZH from touching
    # (四不接触) and from touching the video.
    for s in segments:
        a, b = _ass_time(s["start"]), _ass_time(s["end"])
        en_plain = re.sub(r"\s+", " ", s["text"]).strip()
        zh_plain = re.sub(r"\s+", " ", s.get("zh", "")).strip()
        en_lines = _wrap_en(en_plain)
        zh_lines = _wrap_zh(zh_plain) if zh_plain else []
        # Highlight vocab on EN (tags don't affect \N line breaks)
        en_tagged = _highlight_vocab(r"\N".join(en_lines), vocab_words)
        zh_tagged = r"\N".join(zh_lines)
        n_en, n_zh = len(en_lines), len(zh_lines)
        # Vertical layout: keep EN above ZH, no touching (四不接触).
        # Each extra line shifts the block center by half a line height.
        # EN line height ~80px (64pt), ZH line height ~75px (60pt).
        en_y = SUB_EN_Y - (n_en - 1) * 40
        zh_y = SUB_ZH_Y + (n_zh - 1) * 38
        # If both are multi-line, add extra separation to avoid EN/ZH touching
        if n_en > 1 and n_zh > 1:
            en_y -= 20
            zh_y += 20
        L.append(f"Dialogue: 0,{a},{b},EN,,0,0,0,,{{\\pos(540,{en_y})}}{en_tagged}")
        if zh_tagged:
            L.append(f"Dialogue: 0,{a},{b},ZH,,0,0,0,,{{\\pos(540,{zh_y})}}{zh_tagged}")

    # ---- vocab panel: 4-row window, EN+ZH two lines, no highlight bar ----
    occs = _occurrences(segments, vocab_index)
    n = len(vocab)
    if occs:
        # Panel visible from the FIRST FRAME (user, 2026-10-20 — overrides
        # the v13.2 "appears when first word is spoken" behavior): before
        # the first occurrence, show the first window of upcoming words
        # with progress 0/N and the FIRST word pre-selected (gold) — it
        # stays selected until it is actually spoken, where the regular
        # occurrence window takes over with the same word still selected.
        if occs[0]["start"] > 0.01:
            a0, b0 = _ass_time(0), _ass_time(occs[0]["start"])
            hdr0 = "本集生詞" if traditional else "本集生词"
            unit0 = "個" if traditional else "个"
            L.append(f"Dialogue: 0,{a0},{b0},VH,,0,0,0,,"
                     f"{{\\pos({PANEL_L},{PANEL_Y + 20})\\an1}}{hdr0} {n} {unit0}  "
                     f"0/{n}")
            _init_win, _init_seen = [], set()
            for w in occs:
                if w["word"] not in _init_seen:
                    _init_seen.add(w["word"])
                    _init_win.append(w)
                    if len(_init_win) == max_rows:
                        break
            for j, w in enumerate(_init_win):
                y_en = PANEL_Y + 60 + j * ROW_H
                y_zh = y_en + 42
                phon = w.get("phonetic", "")
                gloss = w.get("gloss", "")
                is_phrase = w.get("is_phrase", False)
                st_en0 = "VEC" if j == 0 else "VE"
                st_ct0 = "VWctCur" if j == 0 else "VWct"
                st_zh0 = "VWzhCur" if j == 0 else "VWzh"
                L.append(f"Dialogue: 0,{a0},{b0},{st_en0},,0,0,0,,"
                         f"{{\\pos({PANEL_L},{y_en})\\an1}}{w['word']}")
                L.append(f"Dialogue: 0,{a0},{b0},{st_ct0},,0,0,0,,"
                         f"{{\\pos({PANEL_R},{y_en})\\an3}}×{w['count']}")
                phon_str = f" /{phon}/" if phon and not is_phrase else ""
                L.append(f"Dialogue: 0,{a0},{b0},{st_zh0},,0,0,0,,"
                         f"{{\\pos({PANEL_L},{y_zh})\\an1}}{gloss}{phon_str}")
        seen_total = set()
        for i, o in enumerate(occs):
            # Each occurrence window starts exactly when its word is spoken.
            a = _ass_time(o["start"])
            b = _ass_time(occs[i + 1]["start"] if i + 1 < len(occs) else total)
            seen_total.add(o["word"])
            # 4-row window: 2 before + current + 1 after
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
                    if len(after) == 1:
                        break
            win = before + [o] + after
            cur_j = len(before)
            hdr_txt = "本集生詞" if traditional else "本集生词"
            unit_txt = "個" if traditional else "个"
            L.append(f"Dialogue: 0,{a},{b},VH,,0,0,0,,"
                     f"{{\\pos({PANEL_L},{PANEL_Y + 20})\\an1}}{hdr_txt} {n} {unit_txt}  "
                     f"{len(seen_total)}/{n}")
            for j, w in enumerate(win):
                is_cur = (j == cur_j)
                y_en = PANEL_Y + 60 + j * ROW_H
                y_zh = y_en + 42
                word = w["word"]
                phon = w.get("phonetic", "")
                gloss = w.get("gloss", "")
                count = w["count"]
                is_phrase = w.get("is_phrase", False)
                # EN line: word only (phonetic moved to ZH line per 2026-10-17 user request)
                st_en = "VEC" if is_cur else "VE"
                L.append(f"Dialogue: 0,{a},{b},{st_en},,0,0,0,,"
                         f"{{\\pos({PANEL_L},{y_en})\\an1}}{word}")
                # xn (right)
                st_ct = "VWctCur" if is_cur else "VWct"
                L.append(f"Dialogue: 0,{a},{b},{st_ct},,0,0,0,,"
                         f"{{\\pos({PANEL_R},{y_en})\\an3}}×{count}")
                # ZH line: gloss + phonetic (so long phonetics don't overlap ×N)
                phon_str = f" /{phon}/" if phon and not is_phrase else ""
                st_zh = "VWzhCur" if is_cur else "VWzh"
                L.append(f"Dialogue: 0,{a},{b},{st_zh},,0,0,0,,"
                         f"{{\\pos({PANEL_L},{y_zh})\\an1}}{gloss}{phon_str}")
    else:
        hdr_txt = "本集生詞" if traditional else "本集生词"
        unit_txt = "個" if traditional else "个"
        L.append(f"Dialogue: 0,{_ass_time(0)},{_ass_time(total)},VH,,0,0,0,,"
                 f"{{\\pos(500,{PANEL_Y + 28})}}{hdr_txt} {n} {unit_txt}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def audit_ass_coverage(ass_path: str, total: float, thresh: float = 0.3):
    """Full-duration coverage audit (SKILL.md §7, 2026-10-20 user rule).

    Returns (panel_gaps, subtitle_gaps): lists of (start, end) spans in
    [0, total] with NO vocab-panel event / NO EN subtitle event. Any panel
    gap is a defect. Subtitle gaps are normal between sentences; review
    any that overlap speech. Run on every episode ASS before composing,
    and also scan the rendered file's panel band — ASS alone once let a
    19.7s head gap ship."""
    def _sec(t):
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    panel, subs = [], []
    for line in open(ass_path, encoding="utf-8"):
        if not line.startswith("Dialogue:"):
            continue
        p = line.split(",", 9)
        a, b, style = _sec(p[1]), _sec(p[2]), p[3]
        if style in ("VH", "VE", "VEC", "VWzh", "VWzhCur", "VWct", "VWctCur"):
            panel.append((a, b))
        elif style == "EN":
            subs.append((a, b))

    def _gaps(ivs):
        out, cur = [], 0.0
        for a, b in sorted(ivs):
            if a - cur > thresh:
                out.append((round(cur, 2), round(a, 2)))
            cur = max(cur, b)
        if total - cur > thresh:
            out.append((round(cur, 2), round(total, 2)))
        return out
    return _gaps(panel), _gaps(subs)


def make_panel_bg(out_path: str):
    from PIL import Image
    img = Image.new("RGBA", (W, PANEL_H), (10, 12, 18, 200))
    img.save(out_path)


def prepare_source(source: str, out_path: str, logo_box: tuple = (1110, 10, 1280, 180),
                   name_end: float = 20.0, crop: tuple = (150, 0, 980, 551)) -> str:
    """Prepare source with two-part logo removal (SKILL.md 9b).

    0..name_end (name titles visible): NO crop, logo removed via OpenCV
    inpainting (TELEA). Names stay fully visible.
    After name_end: symmetric crop to exclude logo.
    Both parts scaled to 1080x608 and concatenated.
    logo_box: (x1,y1,x2,y2) of burned-in logo in 1280x720 source.
    crop: (x,y,w,h) in 1280x720 space. y=0 keeps heads fully visible
    (2026-10-17 fix: y=85 was cutting off speakers' heads).
    Input is normalized to 1280x720 first so logo_box/crop stay valid
    regardless of source resolution (2026-10-17 fix).
    Returns out_path.
    """
    import cv2
    import numpy as np
    import tempfile
    workdir = os.path.abspath(os.path.dirname(out_path) or ".")
    out_path = os.path.abspath(out_path)
    # Normalize input to 1280x720: logo_box and crop are defined in this
    # coordinate space. Without this, a 1920x1080 source breaks
    # cv2.inpaint (mask size mismatch) and shifts the crop.
    _norm = None
    cap0 = cv2.VideoCapture(source)
    _iw = int(cap0.get(cv2.CAP_PROP_FRAME_WIDTH))
    _ih = int(cap0.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap0.release()
    if (_iw, _ih) != (1280, 720):
        _norm = os.path.join(workdir, "_src_norm.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", source,
                        "-vf", "scale=1280:720,setsar=1",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                        "-c:a", "aac", _norm], check=True)
        source = _norm
    # Use workdir for temp files (not /tmp which is a small tmpfs)
    part1 = os.path.join(workdir, "_src_part1.mp4")
    part2 = os.path.join(workdir, "_src_part2.mp4")
    cap = cv2.VideoCapture(source)
    fps = cap.get(cv2.CAP_PROP_FPS)
    x1, y1, x2, y2 = logo_box
    mask = np.zeros((720, 1280), dtype=np.uint8)
    mask[y1:y2, x1:x2] = 255
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    tmp1 = os.path.join(workdir, "_src_part1_raw.mp4")
    out1 = cv2.VideoWriter(tmp1, fourcc, fps, (1280, 720))
    for _ in range(int(fps * name_end)):
        ret, frame = cap.read()
        if not ret:
            break
        out1.write(cv2.inpaint(frame, mask, 3, cv2.INPAINT_TELEA))
    cap.release()
    out1.release()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp1,
                    "-i", source, "-t", str(name_end),
                    "-map", "0:v", "-map", "1:a",
                    "-vf", "scale=1080:608,setsar=1",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-c:a", "aac", part1], check=True)
    os.remove(tmp1)
    cx, cy, cw, ch = crop
    subprocess.run(["ffmpeg", "-y", "-v", "error",
                    "-ss", str(name_end), "-i", source,
                    "-vf", f"crop={cw}:{ch}:{cx}:{cy},scale=1080:608,setsar=1",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-c:a", "aac", part2], check=True)
    lst = os.path.join(workdir, "_src_list.txt")
    with open(lst, "w") as f:
        f.write(f"file '{part1}'\nfile '{part2}'\n")
    # Use concat filter (not demuxer) to fix timestamps correctly
    subprocess.run(["ffmpeg", "-y", "-v", "error",
                    "-i", part1, "-i", part2,
                    "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]",
                    "-map", "[outv]", "-map", "[outa]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-c:a", "aac", out_path], check=True)
    for p in (part1, part2, lst):
        if os.path.exists(p):
            os.remove(p)
    if _norm and os.path.exists(_norm):
        os.remove(_norm)
    return out_path


def fix_overlaps(segments: list[dict]) -> list[dict]:
    """Clamp overlapping subtitle time ranges.

    YouTube auto-subs often have end > next start, causing two subtitles
    to display simultaneously. This sets each segment's end to the next
    segment's start, so each translation shows exactly once.
    (Added 2026-10-17: user reported duplicate overlapping subtitles.)
    """
    for i in range(len(segments) - 1):
        if segments[i]["end"] > segments[i + 1]["start"]:
            segments[i]["end"] = segments[i + 1]["start"]
    return segments


def compose(source: str, segments: list[dict], vocab: list[dict],
            out_path: str, total: float | None = None,
            preset: str | None = None, traditional: bool = False,
            pre_cropped: bool = False):
    """Assemble the final vertical video. segments need 'zh' keys.

    pre_cropped: source already 1080x608 (via prepare_source()); skip
    the internal symmetric crop.
    NOTE: burned-in logos are removed via prepare_source() (inpainting
    for name segment, symmetric crop after) -- NOT blurred. See 9a/9b.
    """
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
    build_ass(segments, vocab, total, ass_path, traditional=traditional)
    # v12: no panel background (user: 生词界面不要有背景底色)

    # v12: symmetric crop (150px each side) unless pre_cropped via prepare_source()
    _crop = "" if pre_cropped else "crop=980:551:150:85,"
    vf = (
        f"[0:v]{_crop}scale=1080:608,setsar=1,fps=30[v];"
        f"[v]pad=1080:1920:0:{VID_Y}:color=black[vp];"
        f"[vp]subtitles={ass_path}:fontsdir=/usr/share/fonts,format=yuv420p[out]"
    )
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-i", source,
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

    Rule (user, 2026-10-20 — SKILL.md section 12): decide the episode
    COUNT first, then divide the total duration EVENLY. Never fill the
    early episodes to the cap and leave a stub at the end.

    - n = ceil(total / ep_len); if n == 1: returns [(0, total)].
    - Per-episode target = total / n. Cuts snap to subtitle segment
      boundaries — never mid-sentence: each cut is the segment end
      nearest the cumulative target (target, 2*target, ...).
      Example: 121 min -> n = 3 -> about 40.3 min per episode.
    - These cuts are STARTING POINTS only: the agent must read the
      transcript around each cut and delay it (guide: <= ~60 s) to where
      the speaker's topic/answer actually completes (SKILL.md section 12,
      smooth cuts). Never chop a speaker off mid-thought.
    Returns [(start_sec, end_sec), ...].
    """
    import math as _math
    n = _math.ceil(total / ep_len)
    if n <= 1:
        return [(0.0, total)]
    step = total / n
    bounds = [0.0]
    for k in range(1, n):
        cut = _nearest_end(segments, k * step)
        if cut <= bounds[-1]:  # no valid cut ahead; force to target
            cut = k * step
        bounds.append(cut)
    bounds.append(total)
    return [(bounds[i], bounds[i + 1]) for i in range(n)]


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
    # v13: no corner blur - source already clean (symmetric crop removed logo)
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

ECDICT tags used: 'gk' (high-school/高考 baseline), 'cet4', 'cet6',
'ielts'. Also builds inflection->lemma map from the 'exchange' field
(~50k).
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
    gk, zk, cet4, cet6, ielts = set(), set(), set(), set(), set()
    down, up = {}, {}  # down: inflection->lemma (from base entries)
    # up: inflection->lemma (from the inflected entry's own "0:" pointer)
    with open(tmp, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            w = (row.get("word") or "").strip().lower()
            if not w:
                continue
            tags = set((row.get("tag") or "").lower().split())
            if "gk" in tags:
                gk.add(w)
            if "zk" in tags:
                zk.add(w)
            if "cet4" in tags:
                cet4.add(w)
            if "cet6" in tags:
                cet6.add(w)
            if "ielts" in tags:
                ielts.add(w)
            # ECDICT exchange semantics: "0:X" on entry w means w is an
            # inflected form whose lemma is X; "k:Y" (k in p/d/i/3/s/r/t)
            # on entry w means Y is an inflection OF w. (An earlier build
            # had these directions mixed, producing base->inflection junk.)
            for ex in (row.get("exchange") or "").split("/"):
                if ":" not in ex:
                    continue
                kind, form = ex.split(":", 1)
                form = form.strip().lower()
                if not form:
                    continue
                if kind == "0":
                    up[w] = form
                else:
                    down.setdefault(form, w)
    lemma = {**down, **up}  # explicit "0:" pointers win
    lemma = {k: v for k, v in lemma.items() if k != v}
    json.dump({"gk": sorted(gk), "zk": sorted(zk), "cet4": sorted(cet4),
               "cet6": sorted(cet6), "ielts": sorted(ielts), "lemma": lemma},
              open(out_path, "w", encoding="utf-8"))
    print(f"wrote {out_path}: gk={len(gk)} zk={len(zk)} cet4={len(cet4)} "
          f"cet6={len(cet6)} ielts={len(ielts)} lemma={len(lemma)}",
          flush=True)
    return out_path

# ======================================================================
# SECTION: excel + outro — fan-group vocab Excel and 4s end card
# ======================================================================
"""Excel vocab list (named after the video title) for the fan group,
and a 4-second end card inviting viewers to join the group to get it.

Episode rule: content <= 55 min per episode + 4 s outro, total < 59 min.
"""


def sanitize_filename(s: str) -> str:
    import re
    s = re.sub(r'[\\\\/:*?"<>|]', "_", s).strip().rstrip(".")
    return s[:80] or "video"


def make_vocab_excel(vocab: list, title: str, out_dir: str) -> str:
    """Write {sanitized title}.xlsx — 序号 | 单词 | 中文释义 | 出现次数."""
    import os
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, sanitize_filename(title) + ".xlsx")
    wb = Workbook()
    ws = wb.active
    ws.title = "生词清单"
    ws.append(["序号", "单词", "中文释义", "出现次数"])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF", size=12)
        cell.fill = PatternFill("solid", fgColor="1F3864")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for i, v in enumerate(vocab, 1):
        ws.append([i, v["word"], v.get("gloss", ""), v["count"]])
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 32
    ws.column_dimensions["D"].width = 12
    ws.row_dimensions[1].height = 24
    for row in ws.iter_rows(min_row=2, max_col=4):
        row[0].alignment = Alignment(horizontal="center")
        row[3].alignment = Alignment(horizontal="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)
    return path


def make_outro_card(vocab_count: int, out_png: str, badge: str = "",
                    W: int = 1080, H: int = 1920,
                    traditional: bool = False):
    """4-second end card: join the fan group to get the vocab Excel."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    fb = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    fr = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    img = Image.new("RGB", (W, H), (8, 14, 38))
    d = ImageDraw.Draw(img)
    for y in range(H):
        r = int(8 + (26 - 8) * y / H); g = int(14 + (44 - 14) * y / H)
        b = int(38 + (96 - 38) * y / H)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    # gold speech bubble icon (brand echo)
    d = ImageDraw.Draw(img, "RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([340, 380, 740, 700], fill=(255, 200, 70, 30))
    img = Image.alpha_composite(img.convert("RGBA"),
                                glow.filter(ImageFilter.GaussianBlur(40))
                                ).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([390, 480, 690, 660], radius=45, fill=(255, 200, 70))
    d.polygon([(470, 650), (440, 720), (530, 650)], fill=(255, 200, 70))
    f = ImageFont.truetype(fb, 64)
    bb = d.textbbox((0, 0), "群", font=f)
    d.text(((W - (bb[2] - bb[0])) / 2, 530), "群", font=f, fill=(12, 18, 44))

    def tc(y, s, size, fill, fp=fb):
        f2 = ImageFont.truetype(fp, size)
        bb2 = d.textbbox((0, 0), s, font=f2)
        d.text(((W - (bb2[2] - bb2[0])) / 2, y), s, font=f2, fill=fill)
    if traditional:
        tc(800, "加入粉絲群", 110, (255, 200, 70))
        tc(960, "領取本集生詞清單", 72, (255, 255, 255))
        tc(1070, f"{vocab_count} 個生詞 · 中英對照 Excel", 48,
           (255, 200, 70), fr)
    else:
        tc(800, "加入粉丝群", 110, (255, 200, 70))
        tc(960, "领取本集生词清单", 72, (255, 255, 255))
        tc(1070, f"{vocab_count} 个生词 · 中英对照 Excel", 48,
           (255, 200, 70), fr)
    if badge:
        tc(H - 220, badge, 52, (255, 255, 255), fr)
    img.save(out_png)
    return out_png


def make_outro(vocab_count: int, out_mp4: str, badge: str = "",
               duration: float = 4.0, fps: int = 30,
               traditional: bool = False) -> str:
    """Render the 4 s end card to mp4 (with silent audio for concat)."""
    import subprocess
    png = out_mp4 + ".card.png"
    make_outro_card(vocab_count, png, badge, traditional=traditional)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(fps),
         "-i", png, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-r", str(fps), "-c:a", "aac", "-shortest", out_mp4],
        check=True)
    return out_mp4


def append_outro(main_mp4: str, outro_mp4: str, out_mp4: str) -> str:
    """Concatenate main video + 4 s outro. Returns out_mp4."""
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", main_mp4, "-i", outro_mp4,
         "-filter_complex",
         "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]",
         "-map", "[outv]", "-map", "[outa]", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "20", "-c:a", "aac",
         "-movflags", "+faststart", out_mp4],
        check=True)
    return out_mp4


def make_source_card(source_name: str, out_png: str,
                     W: int = 1080, H: int = 1920,
                     traditional: bool = False) -> str:
    """2-second full-screen source card: declares the video source AND the
    educational purpose. Shown as a dedicated card, NOT a small overlay."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    fb = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    fr = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    img = Image.new("RGB", (W, H), (8, 14, 38))
    d = ImageDraw.Draw(img)
    for y in range(H):
        r = int(8 + (26 - 8) * y / H); g = int(14 + (44 - 14) * y / H)
        b = int(38 + (96 - 38) * y / H)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    # gold speech bubble icon (brand echo)
    d = ImageDraw.Draw(img, "RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([340, 380, 740, 700], fill=(255, 200, 70, 30))
    img = Image.alpha_composite(img.convert("RGBA"),
                                glow.filter(ImageFilter.GaussianBlur(40))
                                ).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([390, 480, 690, 660], radius=45, fill=(255, 200, 70))
    d.polygon([(470, 650), (440, 720), (530, 650)], fill=(255, 200, 70))

    def tc(y, s, size, fill, fp=fb):
        f2 = ImageFont.truetype(fp, size)
        bb2 = d.textbbox((0, 0), s, font=f2)
        d.text(((W - (bb2[2] - bb2[0])) / 2, y), s, font=f2, fill=fill)
    if traditional:
        tc(800, "視頻來源", 72, (255, 255, 255), fr)
        tc(900, source_name, 96, (255, 200, 70))
        tc(1080, "本視頻僅作英語學習教育用途", 54, (255, 255, 255), fr)
        tc(1180, "中英逐句翻譯 · 生詞精講", 48, (255, 200, 70), fr)
    else:
        tc(800, "视频来源", 72, (255, 255, 255), fr)
        tc(900, source_name, 96, (255, 200, 70))
        tc(1080, "本视频仅作英语学习教育用途", 54, (255, 255, 255), fr)
        tc(1180, "中英逐句翻译 · 生词精讲", 48, (255, 200, 70), fr)
    img.save(out_png)
    return out_png


def make_source_intro(source_name: str, out_mp4: str,
                      duration: float = 2.0, fps: int = 30,
                      traditional: bool = False) -> str:
    """Render the 2 s source card to mp4 (with silent audio for concat)."""
    import subprocess
    png = out_mp4 + ".card.png"
    make_source_card(source_name, png, traditional=traditional)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(fps),
         "-i", png, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-r", str(fps), "-c:a", "aac", "-shortest", out_mp4],
        check=True)
    return out_mp4


def concat_mp4s(parts: list[str], out_mp4: str) -> str:
    """Concatenate N mp4s in order (e.g. source card + main + outro)."""
    import subprocess
    inputs, filt = [], []
    for i, p in enumerate(parts):
        inputs += ["-i", p]
        filt.append(f"[{i}:v][{i}:a]")
    filt.append(f"concat=n={len(parts)}:v=1:a=1[outv][outa]")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error"] + inputs +
        ["-filter_complex", "".join(filt),
         "-map", "[outv]", "-map", "[outa]", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "20", "-c:a", "aac",
         "-movflags", "+faststart", out_mp4],
        check=True)
    return out_mp4


def crop_speaker(source: str, start: float, dur: float,
                 crop_x: int, crop_y: int, crop_w: int = 640,
                 crop_h: int = 360, out_path: str = "",
                 preset: str | None = None) -> str:
    """Extract a tight per-speaker crop from the source video.

    For dynamic speaker switching (§9a): each speaker gets a tight 16:9
    crop that excludes burned-in logos by framing (NOT by blurring).
    Example (1280x720 source, Korea Society):
      Jensen (left):  crop_x=0,   crop_y=200
      Juju (right):   crop_x=640, crop_y=200
    Both are 640x360, scaled to 1080x608 for the vertical layout.
    """
    import subprocess
    preset = preset or os.environ.get("CLIP2VERTICAL_PRESET", "medium")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-ss", str(start), "-i", source, "-t", str(dur),
         "-vf", f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=1080:608",
         "-c:v", "libx264", "-preset", preset, "-crf", "20",
         "-c:a", "aac", "-b:a", "128k", out_path],
        check=True)
    return out_path


def assemble_dynamic(timeline: list[dict], out_path: str) -> str:
    """Assemble dynamic speaker-switching video from a timeline.

    timeline: [{start, dur, crop_x, crop_y, tmp}, ...] — each entry is
    rendered via crop_speaker() then concatenated in order.
    The result switches framing to whoever is speaking (vivid, dynamic).
    """
    import subprocess
    import tempfile
    import os as _os
    parts = []
    tmpdir = tempfile.mkdtemp(prefix="dyn_")
    try:
        for i, seg in enumerate(timeline):
            part = _os.path.join(tmpdir, f"part_{i:04d}.mp4")
            crop_speaker(seg["source"], seg["start"], seg["dur"],
                         seg["crop_x"], seg.get("crop_y", 200),
                         out_path=part)
            parts.append(part)
        return concat_mp4s(parts, out_path)
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def check_redistribution(url: str) -> dict:
    """Check whether the source explicitly prohibits rebroadcasting.

    Fetches video metadata (title/description/license) and scans for
    explicit no-reuse statements. Returns a dict; if result['ok'] is
    False, the caller MUST refuse to generate and notify the user.

    This is a heuristic — it catches explicit prohibitions, not a legal
    clearance. When in doubt, ask the user.
    """
    import subprocess
    import re
    import shutil
    import sys
    result = {"ok": True, "license": "", "flags": [], "title": ""}
    ytdlp = (shutil.which("yt-dlp")
             or os.path.join(os.path.dirname(sys.executable), "yt-dlp"))
    try:
        r = subprocess.run(
            [ytdlp, "--no-warnings", "--dump-json", "--no-download",
             "--extractor-args", "youtube:player_client=android", url],
            capture_output=True, text=True, timeout=90)
        if r.returncode != 0:
            result["flags"].append("metadata_unavailable")
            return result  # cannot verify; caller decides (default: warn)
        import json as _json
        meta = _json.loads(r.stdout)
    except Exception as e:  # noqa: BLE001
        result["flags"].append(f"metadata_error: {e}")
        return result
    result["title"] = meta.get("title", "")
    result["license"] = meta.get("license", "")
    text = f"{meta.get('title', '')}\n{meta.get('description', '')}"
    patterns = [
        r"禁止.{0,6}转[载播]", r"不得转[载播]", r"未经.{0,8}不得",
        r"no\s*re-?upload", r"do\s*not\s*re-?upload",
        r"no\s*re-?broadcast", r"prohibited.*re-?distribut",
        r"all\s*rights\s*reserved.{0,40}no.*use",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result["flags"].append(f"explicit_prohibition: {m.group(0)[:60]}")
    if result["flags"]:
        result["ok"] = False
    return result
