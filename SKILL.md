# English Interview Clipper

Turn any YouTube interview (tech leaders, etc.) into a vertical 1080x1920
learning video for mainland-China English learners: sentence-by-sentence
Chinese/English subtitles, a scrolling vocabulary panel of every word
beyond high-school level (CET-4 / CET-6 / IELTS and beyond), auto-generated
covers, and publishing to Douyin.

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
- **Verify frame 0 on the RENDERED file, not the source** (2026-10-20
  lesson): ffmpeg input seeking (`-ss` before `-i`) can land ~0.25s
  EARLIER than requested, so a start point verified clean in the source
  can still open on the tail of a title card / ident. After EVERY
  render, extract the literal frames t=0, 0.1, 0.3 from the output and
  confirm zero residue of any previous scene; when cutting right after
  an ident, leave safety margin past it (the scene's first clean frame
  + ~0.3s) rather than cutting at the exact transition.
- End cards / logo outros (e.g. "THE KOREA SOCIETY / Watch more like
  this") must be cut too: find where the end card starts and trim the
  source there. Drop or clamp any subtitle segments beyond the cut point.
- This is the user's explicit copyright requirement: no third-party
  logos or idents in the first OR last seconds.
- **Re-extract vocab after any trim** (2026-10-17 user rule): if the video
  start/end changes (e.g. trimming the opening), re-run vocab extraction on
  the new segment range and drop words that no longer appear. Do not ship a
  vocab panel containing words from cut footage.

### 3. Burned-in logos — KEEP by default (2026-10-20 user rule,
supersedes the 2026-10-17 per-video stance)

- DEFAULT: keep the source video's burned-in logo/watermark VISIBLE.
  Do NOT AI-erase, inpaint, or blur it — altering the original creator's
  mark raises copyright problems.
- Exception: if the logo appears only RARELY/briefly, it may be removed
  (crop or inpaint). If it is present throughout the video, leave it
  exactly as-is.
- Cropping the frame itself (for layout, not logo removal) is still
  possible, but NEVER cut off speakers' heads (§9).
- `clipper.compose()` does not blur anything by default.

### 3a. Source card — CANCELLED (2026-10-16 user decision)

- User cancelled the 2-second source/usage intro card. Videos now open
  directly with the main content (no intro card). Do NOT generate or
  prepend it. Final structure: main video + 4 s fan-group outro (§14).

### 4. Transcribe

- `clipper.transcribe()`: faster-whisper with `word_timestamps=True` and
  VAD. Then `merge_short()` and `split_sentences()` so every subtitle
  event is exactly one sentence — this is a hard requirement, never show
  two sentences in one subtitle card.
- **Filter non-speech segments** (2026-10-17 user rule): remove segments
  that are not human speech — sound effects ("Heat. Heat."), music beats,
  pure countdown numbers ("4 3 2 1"), lone filler words ("like") with no
  content. These clutter the learning experience. Delete them before
  translating (reindex after removal).

### 5. Translate

- `clipper.translate_batch()`: English → Simplified Chinese, one line per
  segment, spoken subtitle style. Review the output; fix any mistranslated
  key terms by hand before composing.
- **Accuracy first** (2026-10-17 user rule): "尽量让用户看着不累，但要保证
  中英文翻译正确" — translation accuracy outranks brevity. Do NOT hard-truncate
  Chinese to a character limit at the cost of meaning. Keep translations
  natural and complete; the 24-char guideline is a comfort target, not a
  hard ceiling.
- **Proactive self-check** (2026-10-17 user rule "举一反三"): when the user
  points out one translation error, audit ALL segments for the same class of
  error (misalignment, dropped content, wrong segment assignment) and fix
  them in one batch — do not make the user hunt for more.
- **Faithful translation, no paraphrasing** (2026-10-17 user rule, for
  educational use): translate what the English SAYS, not what you think it
  should say. Rules:
  - No added content (e.g. don't insert "工程师" if English doesn't say it)
  - No dropped content (e.g. keep "incredible" if English says it)
  - No invented meaning for fragments — translate fragments literally,
    don't fabricate complete sentences from them
  - If Chinese is slightly stiff but accurate, prefer accuracy over fluency
  - Students use these videos to learn; every mismatch erodes trust
- **Use the most capable model for translation** (2026-10-17 user rule):
  do not use a weak/fast model to save time. Translation quality is the
  core value for students. After machine translation, do a full human
  review pass checking for: missed translations (EN content absent in ZH),
  wrong translations (ZH meaning ≠ EN meaning), and over-paraphrasing.
  Fix all before composing.
- **Final AI review of all subtitles** (2026-10-20 user rule): after EN
  proofreading and ZH translation are both done, run one more full
  review pass with the most capable AI model available. The reviewer
  does two jobs in one pass:
  (a) Quality — check every segment pair for: EN transcription errors
  missed in proofreading (names, terms, numbers, homophones); ZH
  fidelity — no added words, no dropped words, no paraphrasing,
  literal fragments kept literal; EN-ZH alignment — every EN segment
  has exactly one matching ZH line, no misalignment or swapped
  segments. Fix all quality issues found.
  (b) Political flags — the AI reviewer reads every segment IN CONTEXT
  (not keyword matching) and separately lists every segment involving:
  foreign political figures by name (e.g. Trump, Biden); US domestic
  politics; international political commentary (e.g. US-China tech
  rivalry framing, "communists" rhetoric) — regardless of sentiment,
  positive or negative. Keywords are only for locating candidates;
  the AI judges by meaning and context whether a segment truly carries
  political risk. (Anti-China remarks are auto-cut per the rule
  above; anything the earlier pass missed gets cut here too.) For the
  non-anti-China political flags, do NOT auto-cut; present the list
  with timestamps and a one-line reason per flag to the user and ask
  whether to cut or publish as-is.
  Only proceed to vocab extraction and composing after quality fixes
  are done AND the user has decided on every political flag.

### 5b. Proofread the English transcription — mandatory (2026-10-17)

- YouTube auto-transcription has systematic errors. Before translating,
  proofread the FULL English text and fix:
  - Proper nouns: names (Franz not Fron), places, brands
  - Technical terms: "Mach diamonds" not "mock diamonds", "yoke" not "yolk",
    "carbon overwrapped" not "carbon overlay"
  - Homophones in context: "coy" not "koi", "Roadster" not "roster",
    "top speed" not "tough speed"
  - Numbers: "0.81 seconds" not "081 seconds"
- When uncertain, flag the segment for the user to verify against the audio.
  Never guess silently on educational content.
- **Re-extract vocab AFTER fixing English** (2026-10-17): vocab extracted
  from uncorrected transcription will contain ghost words (e.g. "mock",
  "yolk") that don't exist in the real speech. Always run vocab extraction
  on the CORRECTED English text.
- **Vocab count must match cover** (2026-10-17): if the final vocab count
  differs from the number on the cover (e.g. 63 vs 64), update the cover
  text. Never ship a mismatch.

### 5a. Fix subtitle overlaps — mandatory (2026-10-17)

- YouTube auto-subs frequently have `end > next start`, causing two
  subtitles to display simultaneously (user sees duplicate overlapping
  translations).
- Run `clipper.fix_overlaps(segments)` after loading segments and before
  composing. This clamps each segment's end to the next segment's start,
  so each translation displays exactly once.

### 6. Content screening — mandatory

- Read every segment. If any segment contains negative remarks about
  China, cut that segment's time range from both video and subtitles
  before composing. When in doubt, cut it. Record what was cut and why.
  (Anti-China auto-cut stays as-is per 2026-10-20 user rule.)
- **Source & person background check** (2026-10-20 user rule): review is
  not limited to dialogue content. Before producing, the AI researches
  (not keyword matching — read actual reporting and context):
  (a) the source media/outlet — does it have a history of anti-China
  reporting or has it been officially criticized by mainland
  authorities;
  (b) every identifiable person in the video (host, guest, callers) —
  has mainland China explicitly opposed, sanctioned, or condemned them;
  (c) the same persons' track record in OTHER programs/episodes —
  problematic statements elsewhere (e.g. advocating bans on Chinese
  models, hostile China rhetoric in other episodes) count the same as
  if said in this video, because platform review judges the person,
  not the episode. Distinguish what the person said IN THIS video from
  what they said ELSEWHERE when reporting.
  If any hits, report to the user with specifics and do NOT proceed
  until they approve.
- **Cross-platform precedent check** (2026-10-20 user rule): before
  producing, search both Douyin and Bilibili for the same source video.
  If an identical or near-identical version already exists and survives
  on both platforms, the content has passed their reviews — safer to
  publish. Report what was found (or not found) to the user.

### 6a. Copyright — read before you publish

Reposting an interview with subtitles is reproduction + adaptation of
someone else's copyrighted work. Subtitles and vocab panels do not make it
yours. Practical rules (not legal advice):

- Credit the source in the video title/description; NEVER blur or mosaic
  source logos — crop them out via §9a instead (§3).
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

**Baseline rule (user, 2026-10-21; supersedes the old CET-4 baseline): a
word counts as a NEW word iff it is beyond high-school vocabulary.**
CET-4, CET-6 and IELTS words ALL count, and so do words that appear in
no exam list at all. Only words at/below high-school level are excluded.
`clipper.extract()` implements this; the rules below are the product
spec, do not weaken them:

- Build/use `exam_words.json` — derived from ECDICT tags: zk set
  (1603 words), gk set (3677), CET-4 set (3849), CET-6 set (5407),
  IELTS set (5040), inflection→lemma map. The "already known" baseline
  is zk ∪ gk (≈3726 unique words).
- Drop: stopwords, the BASIC common-word list, proper nouns (words
  capitalized mid-sentence), brand/product names, and any token with an
  apostrophe (contractions/possessives are never vocab).
- Drop: any word whose lemma is in the zk ∪ gk baseline (already known
  by high-school graduation) — UNLESS it is on the hard-word exemption
  list.
- **Hard-word exemptions** (user, 2026-10-21): a few words sit in the
  school lists yet are genuinely beyond a high-school graduate (the
  classic case: autonomous — a 高考 textbook word via "autonomous
  region" — and breakthrough). Those still count as new words. The
  curated list lives in `vocab_exemptions.json` next to clipper.py.
  Growth rule: during the §7 audit, baseline-excluded words with
  zipf ≤ 3.9 are exemption candidates; add the genuinely hard ones to
  the list, mention additions in the delivery summary (the user can
  veto), and commit the updated list with the skill. Everyday words
  that are merely corpus-rare (anyhow, microwave, vocabulary) do NOT
  qualify.
- NO zipf ceiling (removed 2026-10-21): corpus frequency cannot
  separate high-school-known words from CET-4 words — their zipf bands
  overlap completely (e.g. computer 4.97 vs available 5.28) — so the
  word lists alone draw the line. The ECDICT lemma map must be built
  with correct exchange direction ("0:X" = this entry's lemma is X;
  other codes = inflections of this entry); a reversed map once let
  base words slip past the baseline check.
- **STRICT enforcement** (2026-10-17 user audit, standard updated
  2026-10-21): the baseline exclusion must be verified word by word.
  A lax pass once shipped "we'd", "demo", "driver's", "manually" in a
  student-facing video. After extraction, audit the final list: the
  exam lists have tagging gaps (e.g. best/actually/online carry no
  school tag in ECDICT) — if any word is basic enough that a
  high-school graduate surely knows it, remove it. Never ship a vocab
  panel with trivial words.
- **Hard rule: the Python running this stage MUST have `wordfreq`
  installed. If the import fails, abort loudly — never silently skip
  the noise check.** (A silent skip once shipped a whole video of
  trivial words; this check exists because of that incident.)
- Tier 0 = IELTS-tagged words, tier 1 = CET-4/CET-6-tagged words,
  tier 2 = words in no exam list at all. Within a tier, rank by
  occurrences in the video, most frequent first. NO count cap (user,
  2026-10-20): include EVERY word that passes the filters — the old
  "top 108" was inherited from a reference creator's format, never a
  user requirement.
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
- **Progress must reach N** (2026-10-17 user rule): if the panel says
  "本集生词 100 个", all 100 words must actually appear during playback —
  the video must not end with the counter stuck at 90/100. After composing,
  verify the max progress reached equals the vocab size. If any word never
  triggers, fix the occurrence matching before shipping.
- **Panel timing** (2026-10-20 user rule, supersedes the 2026-10-19
  "appears when spoken" rule): the vocab panel is visible from the FIRST
  FRAME to the end. Before the first word is spoken it shows the first
  window of upcoming words with progress 0/N and the first word
  PRE-SELECTED (gold) — it stays selected until it is actually spoken,
  where its occurrence window takes over with the same word still
  selected. Each occurrence window starts exactly when its word is spoken.
- **Full-duration coverage — panel AND subtitles** (2026-10-20 user rule):
  across the WHOLE video there must never be a moment with speech but no
  subtitle, nor a moment with subtitles but no vocab panel. Panel events
  must chain continuously over [0, total] with no gap (>0.3s = defect);
  every speech segment must have its subtitle events. Before delivery,
  audit the episode ASS for panel gaps AND scan the rendered file's panel
  band at fine intervals (head, seams, tail) — a spot check at 3 frames
  is NOT sufficient (a 19.7s panel gap at an episode head once shipped
  unnoticed). Watch the timestamps: per-episode subtitle files may carry
  ABSOLUTE source timestamps (e.g. episode 2 starting at 1922s) — always
  convert to episode-local time (first segment ≈ 0.0) before build_ass;
  feeding absolute times silently yields a head with panel but no
  subtitles.
- **Surface-form matching** (2026-10-19): the panel index and subtitle
  highlight must match inflected forms actually spoken (predictions,
  disrupted, fabs...), not just the dictionary base form — otherwise
  progress stalls and highlights miss. `build_ass()` derives the spoken
  surface forms from the segment text itself (no blind stemming).
  The displayed ×N count must equal the actually matched occurrences.
- Phonetics: every single word gets an IPA phonetic symbol from
  `phonetics.json` (via `clipper.add_phonetics()`), displayed in the
  panel as `中文 /phonetic/` — a SINGLE slash pair AFTER the Chinese
  gloss, never before it (2026-10-17 user rule: `//` double slashes
  banned; phonetic-after-gloss keeps long phonetics from overlapping
  the ×N column).
- Phrases: extract idiomatic multi-word expressions via
  `clipper.extract_phrases()` (matches against `idioms.txt`), e.g.
  "punch above your weight", "a walk in the park". Phrases get Chinese
  glosses but no phonetics. They appear in the panel interleaved with
  words by frequency.

### 8. Sample frames before the full render

### 7b. Vocab panel — two-line format (2026-10-16)

Each vocab item uses TWO lines:
- Line 1: English word (large, left) + ×count (right-aligned in its own
  column at PANEL_R — NEVER inline, fixes the 2026-10-16 ×n cutoff bug)
- Line 2: Chinese gloss + phonetic /.../ (smaller, left)
- Current word: full-width highlight bar behind both lines

Header: `本集生词 N 个` (left) + `i/N` (right). Background stays black
transparent. 5-row scrolling window follows speech. Implemented in
`clipper.build_ass()`.

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
- **Subtitle wrapping, never truncation** (2026-10-17 user rule): long
  subtitles MUST wrap to multiple lines, NEVER be cut off. Follow movie
  subtitle conventions:
  - Chinese: break at punctuation (，。！？；：、), max ~17 full-width units
    per line; if no punctuation, split evenly by character count
  - English: break at word boundaries, balance line lengths
  - Prefer one line per sentence; wrap only when necessary; never drop
    characters to avoid wrapping
  - Adjust Y position for multi-line: EN moves up, ZH moves down, keeping
    the "four no-touches" layout intact
- Interface stays clean and minimal. Only real footage from the source
  interview — never AI-generated visuals or stock filler.
- **Crop must preserve headroom** (2026-10-17 user rule): when cropping
  to remove logos, NEVER cut off speakers' heads. The default symmetric
  crop's top offset must be 0 (not 85px). Verify with frame extraction at
  talking-head timestamps before full render.

### 9a. Logo exclusion — keep by default (2026-10-20 user rule)

- Burned-in logos stay VISIBLE by default — see §3. Removal (crop /
  inpaint) only when the logo appears rarely/briefly; never blur it.
- If cropping is chosen (rare-logo case): keep top offset=0 to preserve
  speakers' heads (2026-10-17 lesson: top=85 cut off heads).

Do NOT use tight per-speaker crops — they don't suit vertical display
(user feedback 2026-10-16: "裁剪的话不适合竖屏显示").
- **Evaluate whether to crop at all** (2026-10-19 user rule): for
  multi-person interviews / talk shows (hosts + guest on couches),
  a fixed center crop inevitably cuts speakers out of frame — sometimes
  the speaker is invisible, sometimes a wide shot becomes a corner.
  Per video, assess: if nobody in frame needs hiding (no anti-China
  individuals, no content requiring removal), prefer NO crop —
  letterbox the full 16:9 frame instead of cropping. Leave any corner
  logo visible (§3); do not blur it.

### 10. QC the render

- Frame 0: no logo, no ident, clean interview picture.
- Spot-check 3 subtitle sync points (beginning / middle / end).
- Audio present, 30fps, yuv420p, `+faststart`.
- **Trim precisely at user-visible cut points** (2026-10-19 lesson):
  NEVER use stream copy (`-c copy`) with `-ss` before `-i` for the
  video start/end — the cut snaps to the nearest keyframe and leaves
  a sub-second residue of the removed footage. For any cut the viewer
  will see, re-encode (`-ss` before `-i` + libx264 is both fast AND
  frame-accurate); reserve `-c copy` for mid-video joins only.
- **Find the TRUE start of a segment to cut** (2026-10-20 lesson):
  when locating a segment for removal, do NOT cut at the first keyword
  hit. The real start is often earlier than the obvious keyword — e.g.
  a phone call begins when the phone rings, not when someone says
  "put him on speaker". After keyword search, walk BACKWARDS through
  the transcript AND spot-check frames to find where the segment
  actually begins, then verify the cut by watching the first
  10 seconds after the junction.

### 11. Covers — two ratios

- `clipper.make_covers()`: from a clean interview frame (person not
  stretched; burned-in logos stay visible, never blurred), produce BOTH
  `cover_34.png` (1080x1440) and `cover_43.png` (1200x900).
- Each carries: kicker line, the headline quote, `N个生词 · 中英逐句精讲`,
  and the account badge. Title text must be large, centered, high
  contrast.

### 12. Episode splitting (content over 59 minutes)

Splitting rule (user, 2026-10-20 — replaces the old "greedy 59-minute
chunks" rule): decide the episode COUNT first, then divide the total
duration EVENLY. Never fill the early episodes to 59 minutes and leave a
stub of a few minutes at the end.

- Per-episode content cap: 59 minutes. The 4 s outro (§14) does NOT count
  toward the cap; it is appended after the content.
- Episode count: `n = ceil(content_seconds / 3540)`. If `n == 1`, single
  episode, no split.
- If `n >= 2`: per-episode target = `content_seconds / n`. Cut at the
  subtitle segment boundaries (never mid-sentence) nearest the cumulative
  targets `target, 2*target, ...`.
  Example: 121 minutes → `n = ceil(121/59) = 3` → 3 episodes of about
  40.3 minutes each (NOT 59 + 59 + 3).
- Smooth cuts (user, 2026-10-20): a segment boundary is necessary but NOT
  sufficient — the speaker must have finished the thought. After picking
  the naive boundary, the agent must READ the transcript around it. If the
  sentence ends but the topic clearly continues (the speaker is mid-answer,
  enumerating, or building an argument), DELAY the cut to the point where
  the topic/answer actually completes. Keep the delay modest — tens of
  seconds, as a guide ≤ ~60 s — and accept slightly uneven episode lengths;
  never chop a speaker off mid-thought, and never let the delay push an
  episode over the 59-minute cap.
- Every published episode then gets the 4 s fan-group outro appended
  (§14). Hard rule: content + outro must stay under 1 hour total.
- Each episode's vocab is computed INDEPENDENTLY from that episode's own
  segments only (re-ranked, no count cap, each with a Chinese gloss) — never
  shared or pooled across episodes. This isolates rework: if one episode
  has a problem, only that episode is re-processed; the others are
  untouched. Count verification per episode (user, 2026-10-20): zero
  ghost words, and every displayed ×N must equal the panel's actual
  matchable occurrences (inflected forms count). Any word that never
  triggers in its episode is dropped before composing.
- Each episode is rendered as its own video (compose per episode range)
  with its own vocab panel. Own covers per episode too.
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
- The 4 s is appended AFTER the episode's content (content length per §12);
  it does not count toward the 59-minute per-episode cap.

### 14a. Final assembly — main + outro (source card cancelled 2026-10-16)

- The finished video is: main video (§9) + 4 s outro (§14), joined with
  `clipper.concat_mp4s([main_mp4, outro_mp4], final_mp4)`.
- Total must stay under the platform limit (§12). If main + 4 s exceeds
  1 h, split into episodes FIRST (§12), then assemble each episode.

### 14b. Traditional Chinese version (for TikTok)

- TikTok audience (Taiwan/HK/overseas) reads Traditional Chinese.
- Generate a second version: convert ALL Chinese text (subtitles `zh`,
  vocab glosses) via `clipper.to_traditional()` (OpenCC s2t) BEFORE
  composing. Use `clipper.vocab_to_traditional(vocab)` and
  `clipper.segments_to_traditional(segments)`.
- Pass `traditional=True` to `clipper.compose()` and `make_outro()`
  for Traditional cards and panel headers. (Source intro cancelled 2026-10-16.)
- The Traditional version goes to TikTok; Simplified goes to Douyin.
- Titles/descriptions/tags should also be in Traditional for TikTok.

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

### 9b. v12 定稿布局（2026-10-16 用户确认，仅适用于该视频）

- 生词栏：4 行（非 5 行），中英同字号 52，选中时中英×n 全部变金色，无背景高亮条；未选中词白色、小一号（44 vs 选中 52）
- 视频居中：横中线在 y=960（VID_Y=656）
- 字幕：EN y=1330，ZH y=1430（间距 100）
- （该视频的 logo 处理方案，用户单独决定：开场 0-20s 姓名条时段用 AI inpainting 去 logo；20s 后对称裁剪去 logo，top offset=0 保头部）
- 无 2 秒来源卡；片尾保留 4 秒进群卡
- 输出 <1GB

### 9c. 长期规则补遗（2026-10-16/17 用户立下，之前漏记）

- **核实截图必须带字幕**：发布前的开始/中间/结束 3 张截图必须含字幕区+生词栏完整界面，无字幕用户无法审批布局
- **插图可放生词界面左侧**：独立于裁剪方案的长期要求
- **不压制画质**：成片在 1GB 上限内用原画质直接发布，不为上传压缩（2026-10-17 用户否决压缩提议）
- **发后不删改重传**：标题、描述、封面、标签发布前一次弄对，发出去就别动——同一视频删掉原样重传会被平台去重机制判"重复/搬运"压推荐，已跑起来的版本删掉等于浪费推荐 momentum（2026-10-18 v13 教训）
- **生词栏标题**（"本集生词 N 个"）：与生词列表左对齐并拉开距离，不得重叠
- **面板位置**：y=180，接近灵动岛但不被覆盖（v13 定版）
- **剪辑范围变化后生词重梳**：重剪后生词表按新范围重新提取
- **封面用户图零修改**：用户提供的封面截图一像素不能改，只能在文字区等背景元素叠加，前景零遮挡

### 9d. MEMORY–SKILL 同步铁律（2026-10-17 教训）

- 用户关于视频制作的任何新要求/取消/修改，**同一 turn 内必须同时更新 MEMORY.md 和 SKILL.md**，做完前者不许开始干活
- SKILL 是唯一执行依据：渲染前对照 SKILL 逐项检查，不凭记忆
- MEMORY 与 SKILL 不一致时，以用户最新指示为准，并立即修正落后的一方

### 9e. Skill 维护规则（2026-10-17 用户立下）

- 用户提新要求时：skill 里已有 → 不动；没有 → 补上；有冲突 → 用最终选择的要求，把冲突的旧条删掉
- 目标：skill 里没有重复、没有冲突的要求

### 9f. 渲染中自核（2026-10-17 用户立下）

- 渲染过程中必须自己核对：抽帧检查声音与字幕是否一致（随机抽 3-5 处，听音频对字幕）
- 发现不一致立即停渲修复，不把问题留给用户发现

### 9g. 要求分类规则（2026-10-17 用户立下）

- 用户每提一条要求，先自行判断是**通用要求**还是**仅适用于该视频**：
  - 通用要求 → 按 §9e 规则更新到 skill（已有→不动，没有→补上，冲突→用最终版删旧条，保证无重复无冲突）
  - 仅适用于该视频 → 不更新到 skill，只在该视频执行
- 本条元规则本身是通用要求，已记入 skill
