# English Interview Clipper

Turn any YouTube interview (tech leaders, etc.) into a vertical 1080x1920
learning video for mainland-China English learners: sentence-by-sentence
Chinese/English subtitles, a scrolling vocabulary panel tuned for CET-4 →
IELTS learners, auto-generated covers, and publishing to Douyin.

## When to use

- The user gives you a YouTube (or any yt-dlp-supported) interview URL and
  wants a bilingual learning clip published to Douyin / TikTok.

## Setup (one time)

- Install: `pip install -r requirements.txt` (yt-dlp, faster-whisper,
  wordfreq, argostranslate, Pillow).
- Install ffmpeg (system package) and a CJK font (Noto Sans CJK).
- Build the exam word lists once: `python run.py --build-exam-words`
  (downloads ECDICT ~66MB, writes `exam_words.json`). The pipeline refuses
  to run the vocab stage without this file.
- Translation needs either an OpenAI-compatible API
  (`TRANSLATE_BASE_URL` / `TRANSLATE_API_KEY` / `TRANSLATE_MODEL`) or the
  offline Argos en→zh model (`argospm install translate-en_zh`).

## Pipeline (run in order, do not skip steps)

### 1. Download — resolution first

- Use `clipper.download()`. Format must prefer 1080p and never go below
  720p: `bv*[height<=1080]+ba/b[height<=1080]/b`, merged to mp4.
- If YouTube shows a bot check, retry with
  `--extractor-args youtube:player_client=android`, then `web_embedded`.
- Verify the downloaded file: `ffprobe` height must be ≥ 720.

### 2. Trim the opening — logos and fades

- Extract frames at t=0, 0.1, 0.5, 1, 2, 3, 4, 5s and look at them.
- Broadcaster logo animations at the start (e.g. the first ~4s) must be
  cut. After cutting, re-check t=0 / 0.1 / 0.15: logo fade-outs often leave
  a residual ghost on the first frames — trim further until frame 0 is
  clean interview footage. Shift every subtitle timestamp by the trimmed
  amount (clamp at 0).
- This is the user's explicit copyright requirement: no third-party
  logos or idents in the first second.

### 3. Blur burned-in corner logos

- If the source has a burned-in logo (e.g. top-right 170x125 at x=910),
  blur it in the compose filter chain:
  `[v]crop=170:125:910:0,boxblur=12` overlaid back at the same position.
- Never cover it with opaque boxes; a blur keeps the frame natural.

### 4. Transcribe

- `clipper.transcribe()`: faster-whisper with `word_timestamps=True` and
  VAD. Then `merge_short()` and `split_sentences()` so every subtitle
  event is exactly one sentence — this is a hard requirement, never show
  two sentences in one subtitle card.

### 5. Translate

- `clipper.translate_batch()`: English → Simplified Chinese, one line per
  segment, spoken subtitle style. Review the output; fix any mistranslated
  key terms by hand before composing.

### 6. Content screening — mandatory

- Read every segment. If any segment contains negative remarks about
  China (or other politically sensitive content unsuitable for a mainland
  audience), cut that segment's time range from both video and subtitles
  before composing. When in doubt, cut it. Record what was cut and why.

### 7. Vocabulary extraction — the core value

Audience: learners who passed CET-4 and are preparing for IELTS.
`clipper.extract_vocab()` implements this; the rules below are the
product spec, do not weaken them:

- Build/use `exam_words.json`: CET-4 set (3849 words), IELTS set
  (5040 words), inflection→lemma map — derived from ECDICT tags.
- Drop: stopwords, the BASIC common-word list, proper nouns (words
  capitalized mid-sentence), brand/product names.
- Drop: any word whose lemma is in the CET-4 set (already known).
- Drop: any word with `wordfreq.zipf_frequency > 4.6` (known to any
  CET-4 learner even if untagged).
- **Hard rule: the Python running this stage MUST have `wordfreq`
  installed. If the import fails, abort loudly — never silently skip the
  zipf filter.** (A silent skip once shipped a whole video of trivial
  words; this check exists because of that incident.)
- Tier 0 = IELTS-tagged words (the exam sweet spot), tier 1 = everything
  else unfamiliar. Within a tier, rank by occurrences in the video,
  most frequent first. Take the top N (default 108).
- Keep genuinely hard words even at count == 1 — never miss a hard word
  just because it appears once.
- Treat `zipf == 0` with count < 3 as transcription noise and drop it.
- Add a concise Chinese gloss to every word
  (`clipper.gloss_vocab()`).
- HARD RULE: every vocab entry must carry a non-empty Chinese gloss
  BEFORE composing. The vocab panel is bilingual by design — English
  word + Chinese gloss + count, with the English column padded to a
  fixed display width so the Chinese column aligns across rows.
  `clipper.compose()` raises if any gloss is missing; never ship a
  render with an English-only panel.

### 8. Sample frames before the full render

- Before the 20–40 minute full render, compose 3–5 sample frames
  (opening, middle, near end, one with the vocab panel visible) and get
  the user's approval on the layout. This saves the most expensive step.

### 9. Compose — 1080x1920, exact layout

`clipper.compose()` builds the final video. The layout is fixed:

- Vocab panel: top at y=170 — below the iPhone Dynamic Island / notch
  safe area. Header `本集生词 N 个 i/N`, then a 5-row window that scrolls
  to follow the speech, centered at x=540; the word being spoken is
  highlighted gold. Panel background is a dark translucent overlay.
- Interview video: 16:9 fitted to 1080x608, top edge at y=610.
- Subtitles, one segment at a time: English at y=1300 (white; words that
  are in the vocab list highlighted yellow-bold), Chinese at y=1440
  (gold). English and Chinese must never overlap or cover each other.
- Interface stays clean and minimal. Only real footage from the source
  interview — never AI-generated visuals or stock filler.

### 10. QC the render

- Frame 0: no logo, no ident, clean interview picture.
- Spot-check 3 subtitle sync points (beginning / middle / end).
- Audio present, 30fps, yuv420p, `+faststart`.

### 11. Covers — two ratios

- `clipper.make_covers()`: from a clean interview frame (person not
  stretched, burned-in logos blurred), produce BOTH
  `cover_34.png` (1080x1440) and `cover_43.png` (1200x900).
- Each carries: kicker line, the headline quote, `N个生词 · 中英逐句精讲`,
  and the account badge. Title text must be large, centered, high
  contrast.

### 12. Episode splitting (final video over 60 minutes)

- If the finished video is 60 minutes or shorter: single episode, no split.
- If longer: split into episodes of max 59 minutes each, using
  `clipper.split_episodes(total_seconds, segments)`:
  cuts snap to subtitle segment boundaries (never mid-sentence — each cut
  is the segment end nearest the 59-minute mark).
- The last episode must be longer than 2 minutes. If the naive split would
  leave a shorter tail, move the cut point earlier so the tail is absorbed
  into the final episode; if that would exceed the platform's duration cap,
  split the remainder evenly in two instead. Never ship a < 2-minute
  orphan episode.
- Each episode is rendered as its own video (compose per episode range)
  with its own vocab panel: only words occurring in that episode, re-ranked,
  top 108, each with a Chinese gloss. Own covers per episode too.
- Title suffix per episode: （上）/（中）/（下） or 第1集/第2集…,
  e.g. `黄仁勋：AI没有知觉，不比宠物石头更有生命｜英文精听（上）`.
  Tags stay the same on every episode. Publish episodes in order.

### 13. Publish

- Douyin creator platform: upload the mp4, title format
  `《人物：金句｜英文精听》`, add ALL FOUR topic tags
  `#人物 #公司 #AI #英语精听` (verify each one landed — the platform
  sometimes drops tags), visibility 公开, publish immediately.
- Report back the work ID. Deleting/replacing an already-published
  version is a separate user-confirmed step.
- TikTok: same video, separate login — treat as phase 2.

## Workflow with the user

- User sends a URL → run stages 1–7 → sample frames for approval →
  full render → user verifies the finished video → publish only on the
  user's explicit go-ahead.

## Files

- `clipper.py` — the whole pipeline as importable functions + CLI helpers.
- `run.py` — `python run.py --url <youtube-url>`: guided full run;
  `python run.py --build-exam-words`: one-time exam-word build.
- `requirements.txt` — Python dependencies.
