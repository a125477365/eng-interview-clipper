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

### 0. Redistribution check — mandatory gate

- BEFORE downloading, run `clipper.check_redistribution(url)`. It fetches
  the video's title/description/license and scans for explicit
  no-rebroadcast statements (e.g. 禁止转载/转播, no re-upload).
- If it returns `ok: False`: STOP. Do not download, transcribe, or render
  anything. Tell the user which statement was found and ask how to
  proceed. This is a hard gate, not a warning to scroll past.
- If metadata is unavailable (network block), say so explicitly and let
  the user decide — do not silently assume permission.

### 1. Download — resolution first

- Use `clipper.download()`. Format must prefer 1080p and never go below
  720p: `bv*[height<=1080]+ba/b[height<=1080]/b`, merged to mp4.
- If YouTube shows a bot check, retry with
  `--extractor-args youtube:player_client=android`, then `web_embedded`.
- Verify the downloaded file: `ffprobe` height must be ≥ 720.

### 2. Trim the opening AND the ending — logos and fades

- Extract frames at t=0, 0.1, 0.5, 1, 2, 3, 4, 5s AND at the last 15 s
  (t=end-15 … end) and look at them.
- Broadcaster logo animations at the start (e.g. the first ~4s) must be
  cut. After cutting, re-check t=0 / 0.1 / 0.15: logo fade-outs often leave
  a residual ghost on the first frames — trim further until frame 0 is
  clean interview footage. Shift every subtitle timestamp by the trimmed
  amount (clamp at 0).
- End cards / logo outros (e.g. "THE KOREA SOCIETY / Watch more like
  this") must be cut too: find where the end card starts and trim the
  source there. Drop or clamp any subtitle segments beyond the cut point.
- This is the user's explicit copyright requirement: no third-party
  logos or idents in the first OR last seconds.

### 3. Burned-in corner logos — keep them visible

- If the source has a burned-in logo/watermark, LEAVE IT VISIBLE. Do NOT
  blur, cover, or remove it. Obscuring rights-management information can
  aggravate liability and looks like hiding the source; a clear source
  attribution (§3a) is the correct approach. `clipper.compose()` no longer
  blurs anything — this is deliberate.

### 3a. Source card — 2 s full-screen (mandatory)

- Every video OPENS with a dedicated 2-second full-screen card (1080x1920),
  NOT a small overlay line. It declares the source AND the educational
  purpose, e.g.:

  ```
  视频来源
  Korea Society
  本视频仅作英语学习教育用途
  中英逐句翻译 · 生词精讲
  ```

- Build it with `clipper.make_source_card(source_name, out_png)` then
  `clipper.make_source_intro(source_name, out_mp4)` (2 s, silent audio
  for concat). Prepend with `clipper.concat_mp4s([intro, main, outro])`.
  Never ship a video without it.

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

### 6a. Copyright — read before you publish

Reposting an interview with subtitles is reproduction + adaptation of
someone else's copyrighted work. Subtitles and vocab panels do not make it
yours. Practical rules (not legal advice):

- ALWAYS credit the source (§3a, never skipped) and NEVER obscure, blur,
  or remove source logos or watermarks (§3).
- BEFORE downloading, run the redistribution check (§0): if the source
  explicitly prohibits rebroadcasting, STOP and tell the user — do not
  generate the video.
- Full-length re-uploads carry the highest risk. Prefer short excerpts
  (a few minutes) with your own commentary over full reproductions —
  excerpts + genuine commentary are far more defensible than a full
  re-upload with subtitles only.
- Avoid material from rights-aggressive outlets. Nonprofit/educational
  sources (e.g. Korea Society) are lower-risk and sometimes grant
  permission for educational use — ask when in doubt.
- If a takedown or claim arrives, consult a lawyer; do not ignore it.

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
- HARD RULE: the occurrence matcher MUST strip ALL surrounding
  punctuation from Whisper word timestamps before vocab lookup.
  Whisper emits words like `"optimism."` — matching only stripped
  `-`/`'` silently drops such words and the panel progress stalls
  (the 72/108 incident). Verify with `_occurrences()`: unique matched
  words must equal the vocab size.

### 8. Sample frames before the full render

- Before the 20–40 minute full render, compose 3–5 sample frames
  (opening, middle, near end, one with the vocab panel visible) and get
  the user's approval on the layout. This saves the most expensive step.

### 9. Compose — 1080x1920, exact layout

`clipper.compose()` builds the final video. The layout is fixed:

- Vocab panel: top at y=170 — below the iPhone Dynamic Island / notch
  safe area. Header `本集生词 N 个 i/N`, then a 5-row window that scrolls
  to follow the speech, anchored slightly left of center at x=500 (long words must never clip); the word being spoken is
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
  stretched; burned-in logos stay visible, never blurred), produce BOTH
  `cover_34.png` (1080x1440) and `cover_43.png` (1200x900).
- Each carries: kicker line, the headline quote, `N个生词 · 中英逐句精讲`,
  and the account badge. Title text must be large, centered, high
  contrast.

### 12. Episode splitting (final video over 60 minutes)

- If the finished video is 60 minutes or shorter: single episode, no split.
- If longer: split into episodes of about 59 minutes each, using
  `clipper.split_episodes(total_seconds, segments)`:
  cuts snap to subtitle segment boundaries (never mid-sentence — each cut
  is the segment end nearest the 59-minute mark). The 59 minutes is a soft
  target, not a rigid cap.
- Every published episode then gets the 4 s fan-group outro appended
  (§14). Hard rule: content + outro must stay under 1 hour total.
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

### 13. Excel vocab list (for the fan group)

- After the vocab is final, generate `clipper.make_vocab_excel(vocab,
  video_title, out_dir)` → `{video_title}.xlsx` (filename sanitized).
- Columns: 序号 | 单词 | 中文释义 | 出现次数. Header styled, filter on,
  frozen top row. This file is what gets shared in the fan group for
  download — generate it for every video/episode.

### 14. 4-second fan-group outro

- Every published video/episode ends with a 4 s end card:
  `clipper.make_outro(vocab_count, out_mp4, badge)` renders the card to mp4.
- Card design (1080x1920, brand style): gold speech-bubble icon,
  `加入粉丝群` / `领取本集生词清单` / `{N} 个生词 · 中英对照 Excel`,
  account badge at the bottom. Silent audio.
- The 4 s is appended AFTER the 59-minute content: episode = 59:00 + 0:04.

### 14a. Final assembly — always card + main + outro

- The finished video is ALWAYS: 2 s source card (§3a) + main video (§9) +
  4 s outro (§14), joined with
  `clipper.concat_mp4s([intro_mp4, main_mp4, outro_mp4], final_mp4)`.
- Total must stay under the platform limit (§12). If main + 6 s exceeds
  1 h, split into episodes FIRST (§12), then assemble each episode.

### 15. Publish

- Upload the FULL-QUALITY master (the crf-20 `final_with_cards.mp4`,
  ~200 MB) to the platforms — NEVER a recompressed preview. Heavily
  compressed uploads (e.g. crf 28) soften subtitle/vocab text edges;
  platforms re-encode anyway, so give their encoder the best source.
  Compressed copies are for review links only.
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
