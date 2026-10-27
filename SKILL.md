# English Interview Clipper

Turn any YouTube interview (tech leaders, etc.) into a vertical 1080x1920
(or horizontal 1920x1080, §9L) learning video for mainland-China English
learners: sentence-by-sentence
Chinese/English subtitles, a scrolling vocabulary panel of every word
beyond high-school level (CET-4 / CET-6 / IELTS and beyond), auto-generated
covers, and publishing to Douyin.

## When to use

- The user gives you a YouTube (or any yt-dlp-supported) interview URL and
  wants a bilingual learning clip published to Douyin / TikTok.

## Orientation map — which rules apply where (2026-10-25)

Read this before building anything. The user picks ONE orientation per
video (§9L intro). A value from one orientation must NEVER be carried
into a build of the other. Three buckets only:

### Shared — identical for vertical and horizontal

- §0 redistribution gate + source attribution; §1 download (1080p
  first, never below 720p); §2 opening/ending trims + frame-0 check
  on the RENDERED file; §3/§9a burned-in logos KEEP by default
  (removal only when rare/brief); §3a source card cancelled.
- §4 transcription + non-speech filtering; §5/§5a/§5b translation,
  proofreading, overlap fixing, final AI review, translation-shift
  audit; §6/§6a content screening (Taiwan zero tolerance, three-layer
  check, cross-platform precedent) and copyright.
- §7 vocab EXTRACTION rules: high-school baseline (zk ∪ gk), hard-word
  exemptions, no count cap, strict audit, wordfreq loud fail, progress
  must reach N, surface-form matching, single-slash phonetic AFTER the
  gloss, phrases. Panel TIMING is also shared: panel visible from the
  first frame to the end, first word pre-selected gold, progress
  starts 1/N, full-duration coverage with no panel/subtitle gap.
  (Timing is shared; panel GEOMETRY is not — see below.)
- §8 sample frames before the full render; §10 QC (frame 0, sync
  spot-checks, audio format, frame-accurate cuts, true cut-point
  walk-back, mechanical gates ≠ translation gate, post-render
  political re-scan); §11 covers (both ratios); §12 episode
  splitting; §13 vocab Excel; §14/§14a outro + assembly; §14b
  Traditional version; §15 publish (full-quality master, tags
  verified, publish only on explicit go-ahead); §16 clips (cut from
  the finished master, batch review, every-other-day upload,
  full-video cover, assistant-owned titles/descriptions); §17
  division of labor (assistant vs user actions + reminders).
- §9c shared items: verification screenshots must carry subtitles;
  illustration may sit left of the vocab panel; no quality
  compression for upload; never delete/re-upload after publishing;
  re-extract vocab after any trim; user-supplied cover art is
  pixel-untouchable.
- Meta-rules §9d–§9g and the Workflow estimate rule (re-base every
  round) are shared.

### Vertical only — §9, §7b, §9b, and the vertical items of §9c

- §9 geometry, all of it: canvas 1080x1920; vocab panel top y=170
  (see the y=170 vs y=180 note below); interview video 1080x608
  with top edge y=610; subtitles EN 64 px white bold anchor y=1330,
  ZH 60 px gold anchor y=1430 (100 px apart); picture vertical
  centerline y=960.
- Vertical subtitle constraints, all of them: right-rail safe zone
  x=180..900 (no subtitle pixel past x=900); pixel width cap
  720 px; EN max 2 lines, ZH max 2 lines per card (ZH aims for
  1 line); over-long sentences split into sequential cards at
  clause boundaries with EN/ZH matched per card.
- §7b two-line vocab row format: EN line + right-aligned ×N column,
  ZH gloss + phonetic on line 2, current word turns EN+ZH+×N gold
  together with NO background bar, ~4-row window.
- §9c vertical items: vocab-panel position y=180; the "four
  no-contacts" spacing (panel clear of the notch, panel clear of
  video, video clear of subtitles, EN clear of ZH); header
  "本集生词 N 个" left-aligned with the list and kept apart.
- §9b v12 layout is vertical AND single-video-only: it applies to
  that one video, never as a general vertical rule.

### Horizontal only — §9L, all of it

- §9L geometry, all of it: canvas 1920x1080; person area x=0..1150
  and vocab panel x=1150..1920, BOTH full height y=0..1080; frosted
  panel background (36 px downscale, lutrgb 0.62/0.62/0.70) to
  y=1080; subtitles with NO background, centered on the FULL frame
  (x=960), EN 72 px white bold top y=928, ZH 60 px gold top
  y=1012, 12 px gap; vocab list NEVER enters the subtitle zone
  (last-row dots bottom 908 vs subtitle EN top 928, ≥10 px clear).
- Horizontal subtitle cards are ALWAYS 1 EN line + 1 ZH line —
  2-line blocks are forbidden (they push EN up into the panel
  dots). Any sentence that would wrap is split by clause, never
  wrapped to 2 lines. There is NO right-rail safe zone in
  landscape: the vertical x=180..900 rule does not apply here.
- Horizontal vocab panel: 5 rows, pitch 150 px, EN 48 px green
  #6EC88C / ZH 42 px white, current word gold, dots row, ×N
  right-aligned x=1870. Size order frozen: subtitle EN 72 >
  subtitle ZH 60 > vocab EN 48 > vocab ZH 42.
- Person-zone iron rules (landscape only): aspect ratio never
  changed (cropping + uniform scaling only); strips same output
  size, each person centered in their own strip, equal displayed
  sizes, head TOPS level (not head lengths); per-segment (never
  per-class) calibration; frame-exact splicing against the
  reference timeline; scene-detection values run 1 frame late;
  logo/text intersection patching for every window; no source
  text in any strip; strip-bottom frost fill; speaker-only
  fallback for unlevel bottoms; TRIM-based compose ranges and
  setpts re-zero for pieces; freezedetect on the finished file.
- The landscape logo/text patching above is the landscape-reframe
  application of the shared §3/§9a keep rule — it does not change
  the vertical default-keep rule.

### Easy confusions — check these before every build

- Subtitle EN size: vertical 64 px vs landscape 72 px (ZH is 60 px
  in both — do not "fix" one from the other).
- Vocab rows: vertical ~4 rows, two-line format vs landscape
  5 rows, EN/ZH/dots format.
- Card lines: vertical EN ≤2 / ZH ≤2 vs landscape strictly 1+1.
- Panel top: §9 says y=170, §9c says y=180 (v13 final). This
  discrepancy predates this map and is left UNCHANGED here —
  resolve it with the user before the next vertical build, then
  delete the losing value per §9e.

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
- **Prefer permitted sources** (2026-10-22 user rule): when choosing
  between candidate sources, prefer channels that explicitly allow
  reuse — a stated permission in the channel About page or the video
  description, a Creative Commons licence, or an official open
  policy. The same content from a permitted channel beats the same content
  from a silent or unknown one. This is a preference at selection
  time; it does not override the hard gate above or §6.
- **Attribution in every video** (2026-10-22 user rule): every
  produced video credits its source inside the video itself — the
  outro card carries one added small line beneath the fixed copy
  (the fixed copy itself stays unchanged, §14):
  `原视频：{频道名}《{原标题}》`, rendered through the `source_line`
  parameter of `make_outro()` / `make_outro_landscape()`. The publish
  description carries the same attribution line. Existing burned-in
  logos/watermarks are likewise never stripped (§3).

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
- **译稿错位审计 (2026-10-25 Yahoo v6c lesson — the defect that
  passed every mechanical gate)**: a translation file can be shifted
  by one segment across a whole block: every Chinese line translates
  the NEXT segment's English (v6c: content 1489–1616 s, ~46 segments;
  e.g. EN "can't put themselves at risk." paired with the Chinese
  for the following segment), then silently re-syncs at a later
  segment. Line counts, frame counts and panel geometry all still
  pass — so audit SEMANTIC correspondence, not just card counts,
  before building the ASS: scan that each ZH translates its OWN EN
  (names, numbers and distinctive words must match the same
  segment), and eye-check the head, middle and tail of every long
  block. A run of ≥3 mismatched segments is a shifted block:
  STOP. Do NOT fix it by shifting all ZH lines back by one — the
  block head's correct translation does not exist in the data, and
  mid-block half-sentences interleave, so a mechanical shift leaves
  wrong lines in place. Fix = re-translate the whole block
  segment-by-segment from each segment's own English (back up the
  original file first), rebuild only the intersecting pieces, then
  run the rework junction check on both ends of the block.

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

- **Taiwan — zero tolerance** (2026-10-21 user rule): if the source
  video involves ANY Taiwan-related topic (Taiwan itself, TSMC /
  Taiwan supply chains framed around Taiwan, visiting Taiwan, Taiwan
  politics or society) — regardless of sentiment or how brief the
  mention — do NOT produce the video at all. This is a source-level
  rejection, not a segment cut. Check at selection time (title,
  description, topic list) AND again on the full transcript before
  composing; a transcript hit kills the whole video: report it and
  stop.
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
  window of upcoming words and the first word PRE-SELECTED (gold) — it
  stays selected until it is actually spoken, where its occurrence
  window takes over with the same word still selected. Each occurrence
  window starts exactly when its word is spoken.
- **Initial progress reads 1/N** (2026-10-23 user rule, supersedes the
  2026-10-20 initial 0/N): because the first word is already selected
  from the first frame, the header progress starts at 1/N, not 0/N —
  the counter reflects the currently selected word. Applies to both the
  portrait (build_ass) and landscape (build_ass_landscape) panels.
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

### 7b. Vocab panel — two-line format (2026-10-16, VERTICAL ONLY — see Orientation map)

Each vocab item uses TWO lines:
- Line 1: English word (large, left) + ×count (right-aligned in its own
  column at PANEL_R — NEVER inline, fixes the 2026-10-16 ×n cutoff bug)
- Line 2: Chinese gloss + phonetic /.../ (smaller, left)
- Current word: NO background highlight bar (2026-10-16 standing rule,
  confirmed in code: "no highlight bar") — EN, ZH and ×N all turn gold
  together; color change only, never a bar

Header: `本集生词 N 个` (left) + `i/N` (right). Background stays black
transparent. 5-row scrolling window follows speech. Implemented in
`clipper.build_ass()`.

- Before the 20–40 minute full render, compose 3–5 sample frames
  (opening, middle, near end, one with the vocab panel visible) and get
  the user's approval on the layout. This saves the most expensive step.

### 9. Compose — 1080x1920, exact layout (VERTICAL ONLY — see Orientation map)

`clipper.compose()` builds the final video. The layout is fixed:

- Vocab panel: top at y=170 — below the iPhone Dynamic Island / notch
  safe area. Header `本集生词 N 个 i/N`, then a 5-row window that scrolls
  to follow the speech, anchored slightly left of center at x=500 (long words must never clip); the word being spoken is
  highlighted gold. Panel background is a dark translucent overlay.
- Interview video: 16:9 fitted to 1080x608, top edge at y=610.
- Subtitles, one segment at a time (VERTICAL ONLY — landscape keeps
  its own §9L subtitle spec and has no right-rail constraint):
  English 64 px white bold, anchor y=1330; Chinese 60 px gold, anchor
  y=1430 (anchors 100 apart, the 2026-10-16 spacing rule); words in
  the vocab list highlighted yellow-bold. English and Chinese must
  never overlap or cover each other.
- **Right-rail safe zone — subtitles must NEVER go under Douyin's
  right action bar (2026-10-24 user rule, from a published-video
  screenshot: the comment button covers subtitle text)**. The rail's
  icons start at canvas x≈941 (measured from the in-app screenshot:
  comment-button left edge on a 1125-px-wide phone screen, video fit
  to width). Vertical subtitle safe zone, canvas 1080 wide: x=180..900
  (720 px wide, centered on 540). No subtitle pixel may pass x=900.
  The 41 px margin absorbs phone-model / app-version differences in
  rail position. The left edge 180 mirrors it to keep subtitles
  centered; nothing on the left side sits at subtitle height.
- **Subtitle width and line caps (vertical)**. The width cap is in
  PIXELS, not characters: every rendered line ≤720 px at its font size
  (EN 64 px bold ≈31 px/char typical → ≈23 chars/line; ZH 60 px bold
  = 60 px/char → 12 chars/line). Wrap starting point: EN max 11
  code-units (≈22 chars), ZH max 12 chars; then pixel-check every
  line with the real font and re-split any line over 720 px at an
  earlier word/punctuation boundary. NEVER truncate, NEVER break a
  word (a single overlong word stays whole on its own line — the only
  exception, flagged in QC if it crosses x=900).
- **EN max 2 lines, ZH max 2 lines per card — hard caps (2026-10-22
  user rule: 中文尽量一行、英文最多两行, and EN/ZH must correspond)**.
  ZH aims for 1 line per card (≤12 chars) and never exceeds 2. When a
  sentence exceeds either cap at safe width, SPLIT it into sequential
  cards at clause boundaries (punctuation, conjunctions, relative
  clauses): each card independently satisfies EN ≤2 lines and ZH ≤2
  lines, ZH split at the matching clause boundary so EN and ZH stay
  matched per card, and time split by word timestamps (fall back to
  character proportion when word times are missing). A card is one
  EN+ZH pair shown together; cards never overlap in time. This
  replaces "prefer one line per sentence": long sentences become
  2–3 short cards rather than 3–4-line blocks — the price of clearing
  the rail at readable size (font stays 64/60 px, not shrunk).
- Multi-line shifts (existing behavior, kept): EN block moves up
  40 px per extra EN line, ZH moves down 38 px per extra ZH line;
  when both exceed one line, add 20 px more separation each way, so
  EN/ZH never touch and subtitles never touch the video above.
- QC (vertical): the §8 sample frames and the §10/§15 verification
  frames must include the longest subtitle card; check no subtitle
  pixel crosses x=900 and no card exceeds 2 EN lines. After the first
  video built under this rule, verify once against a real in-app
  phone screenshot before treating the 900 edge as settled.
- Interface stays clean and minimal. Only real footage from the source
  interview — never AI-generated visuals or stock filler.
- **Crop must preserve headroom** (2026-10-17 user rule): when cropping
  to remove logos, NEVER cut off speakers' heads. The default symmetric
  crop's top offset must be 0 (not 85px). Verify with frame extraction at
  talking-head timestamps before full render.

### 9L. Landscape scheme — 1920x1080 (2026-10-21 user rule; full-height layout v6 finalized 2026-10-25, strip + bottom + color/size rules)

The user picks the orientation per video: **竖屏 = §9 as-is （不用修）;
横屏 = this section.** ORIENTATION SEPARATION (user, 2026-10-24):
the vocab panel, subtitles and person-zone geometry are DIFFERENT
between orientations and must NEVER be mixed — §9 is vertical-only,
§9L is landscape-only; do not carry a panel/subtitle value from one
orientation into a build of the other. ONLY the process rules below
are shared across orientations: redistribution
gate (§0), opening/ending trims (§2), burned-in logos (§3/§9a),
transcription + proofread + translation + the mandatory final AI
review (§5), content screening (§6), vocab EXTRACTION rules (§7 —
baseline, exemptions, progress must reach N, full-duration coverage;
panel DISPLAY is §9/§9L, not shared), episode splitting (§12), the
vocab Excel (§13), the 4 s fan-group outro (§14), covers (§11 — same
two ratios for landscape posts too), and publishing (§15). Panel
timing (first-frame panel, first-word pre-selection) happens to hold
in both orientations, but each orientation's geometry below is
specified on its own and must be followed as written.

Functions: `clipper.build_ass_landscape()`,
`clipper.compose_landscape()`, `clipper.make_outro_landscape()`. The
vertical functions are NOT modified for landscape. Coverage audit for
landscape: `audit_ass_coverage(path, total,
panel_styles=clipper._LAND_PANEL_STYLES, sub_style="LEN")`.

Geometry (v6, user-confirmed 2026-10-25 — replaces the 2026-10-21
"fit the whole frame into the left region" scheme, which the user
rejected: speakers came out too small and the panel read as an
overlay; and replaces the v5 1150x864 + bottom-band layout, retired
2026-10-25):

- Canvas 1920x1080. LEFT person area x=0..1150, RIGHT vocab panel
  x=1150..1920 (770 px). BOTH run the FULL height y=0..1080 — there
  is no horizontal band division anymore (user 2026-10-25, per the
  reference frame: right vocab panel, left person, subtitles
  floating over the bottom of both). People appear ONLY in the
  person area; the vocab panel shows ONLY vocab. The reference
  frame's "MJ ENGLISH" corner badge is the reference account's own
  mark and is NEVER reproduced in our videos (our videos carry
  only our own source line/outro).
- Vocab-panel background = FROSTED GLASS, exact production spec
  (user-confirmed 2026-10-24, extended to full height 2026-10-25):
  source = the ORIGINAL frame — NOT the person-zone reframe; it
  plays LIVE on the same timeline as the video (it moves with
  the scene, it is not a still). Chain: downscale the original
  frame to 36 px wide (36x20) then back up to 1920x1080 (bilinear),
  crop the right 770 px (x=1150..1920), `lutrgb` x0.62 / x0.62 /
  x0.70, overlaid at x=1150, y=0 — so the frost covers the panel's
  FULL height y=0..1080. Because the source is the original frame, a blurred outline
  of whoever stands on the right side of the original shot WILL
  show through — the user's explicit tolerance (2026-10-24): a vague
  face-shaped outline is ACCEPTABLE, but facial features must NOT be
  discernible, and NO readable text may survive. (User tuned
  2026-10-24: brighter + lighter frost than the first v4 pass —
  24x11 at x0.52 was too dark and too heavy.)
- Subtitles (user rule 2026-10-25, correcting the same-day
  frosted-band idea — the user said that wording was wrong):
  subtitles have NO background color — the lines float
  TRANSPARENTLY over the person area AND the vocab-panel
  background across the bottom of the frame, centered on the FULL
  frame (center x=960), NOT confined to the person area. EN is the
  BIG line: 72 px white bold, top y=928 (bottom ≈1000). ZH is the
  second line: 60 px gold, top y=1012 (bottom ≈1072). EN/ZH gap
  12 px, never touching.
  This retires the old bottom-band subtitle spec (EN 64 / ZH 52,
  tops y=872/968) and the old solid/frosted band entirely — there
  is no band anymore.
- Person-area placement （横屏）: the person area runs TOP to BOTTOM,
  y=0..1080; strips and CU fill the full 1150x1080 zone (strip
  output sizes 575x1080 each for two-person, 383x1080 each for
  three-person; CU 1150x1080). The subtitle lines float over the
  bottom of the person area; the person area itself has no band
  cut. Separation, landscape values: person area and vocab
  column never overlap (panel text is inset 50 px from the zone
  boundary, see below); subtitle EN and ZH lines never touch
  (12 px gap, see above); the vocab LIST never enters the
  subtitle zone (boundary rule, see panel rows below).
- Person-area BOTTOM rules (user 2026-10-25, from the v6 demo
  frames — the strip bottoms were messy): (1) NO source-video
  TEXT, ever — no lower-third name banners, tickers, captions or
  on-screen graphics text may appear in any strip or CU. Measure
  per segment where the source's text band starts (banners/tickers
  typically sit in the source's bottom rows) and end every crop
  ABOVE that band. (2) NO black gaps at strip bottoms — a strip
  pushed up for head-top alignment must not end in empty black.
  Where a strip's crop cannot reach the zone bottom, fill the
  strip's remaining bottom rows with the SAME frost as the vocab
  panel (same chain, same lutrgb brightness) — frost fill is the
  default for level strips with empty bottoms, decided case by
  case per segment. (3) Speaker-only fallback: if a multi-person
  shot's strips cannot be made level at the bottom (different
  strip aspects/heights leave uneven bottoms), do NOT ship uneven
  strips — show ONLY the current speaker's headshot (CU) for that
  segment instead. Rule priority: exclude source text first, then
  frost-fill level bottoms, then fall back to speaker-only when
  bottoms still cannot be leveled.
- PERSON-ZONE IRON RULE （长短比例铁律， user's own wording
  2026-10-24): a person's ASPECT RATIO must never be changed — no
  stretching, ever, in any crop. Uniform scaling + cropping only.
  The person's SIZE may change freely. User restated 2026-10-24
  （原话： "头长不能变，要不头型都变了，只有截取不能拉缩型状"):
  CROPPING ONLY — never stretch or squash the shape. Verify
  numerically per strip: the x and y scale factors MUST be equal
  (e.g. a 581x1091 crop scaled to 575x1080 is 0.9897 on BOTH axes);
  any mismatch is a defect even if it looks close.
- Person-zone framing is per-shot (shot list from scene detection),
  windows placed from FACE MEASUREMENTS on full-size stills — never
  estimate spans from thumbnails or contact-sheet montages (a v4
  strip estimated from a small montage put the seam through a face).
  Shot classes:
  - CU (one speaker): one window per speaker, face-centered, sized
    to the benchmark the user approved (Yahoo Finance host CU: head +
    hair ≈ 630 px displayed — same absolute size as v5; the zone is
    now 1080 tall so the head reads slightly smaller relative to
    the zone, with more body/room visible; a 1020x958 crop of a
    1080p source scaled to 1150x1080 lands there). Every speaker's
    CU uses the SAME displayed size — a big-head-only framing was
    rejected.
    Window x from the measured face center, y keeps the full hair
    (heads never cut — standing rule) — and the crop's bottom must
    end above the segment's measured source-text band (see bottom
    rules below): if the standard crop height cannot fit above the
    band, narrow the crop (zoom in) or frost-fill the remainder —
    never show the text.
  - MED (1–2 people in one comfortable window): single window,
    face-centered — crop the source's left/right, keep the original
    scene （保留人物原场景）.
  - Wide multi-person shots whose span does not fit the zone aspect:
    one strip per person, spliced left-to-right. STRIP RULES (user,
    2026-10-24, user's own wording: "头要一样大，一样高，每个截取图
    宽度一样宽，每个人在自己所属截取图的中间"): (1) every strip has
    the SAME output size — same width AND same height (e.g. 575x1080
    each; an earlier cut with 589/560 strips was rejected on sight);
    (2) each person sits at the HORIZONTAL CENTER of their own
    strip — people must not crowd the seam, nor sit far from the
    outer frame edges; (3) all people display at the SAME size —
    equalize on the person's real size: measure head height in the
    source (a person seated farther away gets a proportionally
    LARGER strip scale; per-strip scales are expected to differ);
    (4) all people's HEAD TOPS are LEVEL — "高" is defined by the
    user as the head TOP （原话： "高指的是要用人的头顶算"), NOT by
    head length: two heads of equal length at different heights
    still fail. Align tops by shifting the crop window vertically
    (y0): output top = (source head top − y0) × scale; pick y0 per
    strip so all output tops match, anchored on THAT SEGMENT's own
    frame(s) — see per-segment calibration below; seated positions
    are stable within one shot but NOT across segments (different
    segments are different camera setups). (5) Strip BOTTOMS must
    end level at the zone bottom: a strip that cannot reach the
    bottom gets frost fill, and a segment whose strips cannot be
    leveled at all falls back to speaker-only CU — see bottom
    rules below. A strip that shows source text or a black gap at
    its bottom fails verification even if its centering is right.
    Verify all four by arithmetic from source measurements:
    output center = (source head center − x0) × scale must equal
    the strip center; output top and output head height likewise.
    Head-height measurement: average two reads — hair-outline height
    and skin-run face height — hair volume alone misleads (it made
    the middle guest first too small, then too big). NEVER judge
    centering or size from visual-grounding bounding boxes: they
    carry a systematic rightward bias (~20–50 px) in this workflow
    and misdiagnosed two consecutive fixes; trust the arithmetic
    and the rendered sample frame, not the box.
- Broadcast logo / bug inside the person zone: FIRST choice is the
  window — frame it out （直接截取出视频外； dark vignettes / soft
  darkening over a logo are forbidden, user 2026-10-23). Where a
  logo still intersects a window or strip, bake a boxblur patch into
  that shot's chain: patch rect = glyph rect expanded ≥30 source px
  on every side (glyphs must sit in the fully-opaque core), edges
  feathered by an alpha ramp (~22 px) EXCEPT edges that coincide
  with the frame boundary (no feather there — a rim over glyphs at
  the frame edge ghosts through). Readable broadcaster text must
  never survive in the person zone — and since 2026-10-25 this
  extends to ALL source text (lower-thirds, tickers, captions),
  not just logos: see the bottom rules. (This is the
  landscape-reframe application of §3/§9a; the vertical
  default-keep rule is unchanged.)
- Production flow for the person zone: scene-detect shots → classify
  (CU / MED / strips) → measure faces on full-size stills → build the
  per-shot reframe graph → encode the reframed person-zone video as
  FRAGMENTED mp4 (ultrafast intermediate) so partial progress
  survives VM restarts and mid-encode frames can be spot-checked →
  render ONE sample frame per shot class and get the user's OK
  BEFORE the final compose (look approval) PLUS one verification
  frame per (sub-)segment (internal check — a sample per class
  does NOT certify the other segments) → compose (frost base +
  full-height person zone + ASS, veryfast crf20) → outro → Excel →
  coverage audit → 3 verification frames (§10/§15 as usual).
- Per-segment calibration (2026-10-24 Yahoo v5 lesson — the method
  gap behind the v4 strip defect): the strip RULES above existed,
  but the method said "one representative frame per shot class"
  and that one frame's windows were reused for every segment of
  the class. Different segments are different camera setups, and
  the reuse left centering errors of 47–192 px. Rules now:
  (1) A SEGMENT is the calibration unit, never the class: measure
  head centers/tops on EACH segment's own mid-frame and compute
  its own windows (x0/y0 per strip, scales set per class for a
  consistent look, with a per-segment UNIFORM fit factor when the
  taller 1080-zone crop would overflow the source — all strips of
  the segment share the factor, so equal head sizes still hold). (2) Intra-segment cuts: scene-detect EACH
  strip segment at low threshold (0.15) ON THE SOURCE — the
  stripped mini at 0.35 missed a close-up→two-shot cut; every
  detected cut splits the segment into sub-shots with their own
  windows, and a sub-shot that changes person count switches
  treatment (three-shot → close-up uses the CU formula, never
  force strips onto a close-up — it cut the guest's head top
  off). (3) Movement inside a segment (host turns from camera to
  guest over ~10 s): a fixed window cannot center a moving head —
  animate the crop x linearly between the two measured endpoints
  (frame-index expression, scale fixed) or split at a real cut;
  never leave a fixed window over a moving head. (4) Verify every
  (sub-)segment with at least one rendered frame before composing
  pieces; a class sample that passes does not pass the class.
- Frame-exact splicing (2026-10-24 user rule): a splice must not
  duplicate or truncate any frame anywhere, except deletions the
  user already approved (e.g. a removed political block, which is
  already baked into the reference timeline). Method: (1) snap
  every segment/sub-segment boundary to a frame number
  (round(t × fps)); a cut point IS a frame index — the new shot's
  FIRST frame; the previous sub-shot is [F_start, F_cut), the next
  [F_cut, F_end). (2) Build pieces with EXACT frame counts
  (frame-count trims, audio trimmed to the matching sample
  count) — never float-second cuts: float `-t` rounded each v4
  piece up ~2–3 frames and v4 gained 42 frames over v3. (3)
  Splice into the REFERENCE timeline (v3, never a drifted
  intermediate). Acceptance gate: the final file's total video
  frame count MUST equal the reference file's frame count
  exactly. (4) Junction check: for every new cut point, compare
  the two frames straddling the cut against the master at the
  same frame indices — continuous, no duplicate, no skip.
- Scene-detection + frame-count lessons (2026-10-24 Yahoo v5):
  (1) scene-detection values run systematically 1 frame LATE —
  the true cut = detected value − 1, and detection only nominates
  candidates: every cut must be confirmed by eyeballing the
  boundary frames on both sides. (2) A "false detection" verdict
  needs boundary-frame evidence on BOTH sides of the cut — a
  41699 detection once dismissed as false was a real cut (a
  close-up hidden inside a "close-up segment"). (3) Long segments
  (>300 frames) cannot be certified by 2 sample points: run a
  0.15-threshold scene scan over the WHOLE segment plus one
  internal verification frame every ~150–200 frames. (4) Total
  frame counts MUST come from `ffprobe -count_frames` real counts
  — never derive them from seconds × frame rate (a 1619.48 s
  estimate gave 48584 vs the real 48583, a 1-frame error that
  nearly polluted a splice).
- Logo-intersection completeness (2026-10-24 Yahoo lesson): after
  building the reframe graph, PROGRAMMATICALLY list every window —
  CU, MED and strips alike — whose rect intersects a logo/bug rect,
  and patch every one. The first Yahoo cut patched only the strips
  and the top-right bug; 7 CU/MED windows still showed a readable
  logo fragment ("…ance") in the corner.
- Compose-range method (2026-10-24 Yahoo lesson): when composing a
  range that does not start at 0, use TRIM filters on sequentially
  decoded inputs (trim + setpts re-zero, subtitles offset via a
  second setpts) — NEVER input `-ss` seeks into the fragmented
  reframe for a long compose: a ~1300 s seek stalled the filter
  graph ~2 frames in and the video froze solid while the audio ran
  on (the muxer duplicated the last frame to the end). A short seek
  for a single verification frame is fine.
- Piece-compose from a fragmented mini (2026-10-24 Yahoo lesson):
  when a replacement piece is composed from a mini with an input
  `-ss` seek, add `setpts=PTS-STARTPTS` to the mini input BEFORE
  the overlay — input-seek timestamps do not re-zero, and without
  the re-zero the overlay emits black frames until the seek point.
  (The same trap bites sample frames taken from a still-encoding
  mini; wait for the mini to finish or re-zero.)
- Final QC addition: run `freezedetect` (n=0.003, d=3) over the
  finished file — any long freeze is a defect, not a static shot;
  also spot-check frames just after every internal join/seam.
- Panel, exact geometry (all y are ASS bottom-anchored positions;
  user-confirmed by the approved Yahoo samples — landscape uses FIVE
  rows because the panel column is taller): header `本集生词 N 个` 44 px at
  (x=1200, y=100), left-aligned with the row text; progress `i/N`
  44 px gold at (x=1870, y=100), right-aligned. NO divider line is
  drawn in the landscape chain (an earlier draft claimed one — the
  approved frames have none); the header-to-first-row gap does the
  separating: first row EN top ≈154, i.e. 54 px below the header
  bottom, never overlapping. Column gutters: panel text inset 50 px
  from the zone boundary (x=1150 → text x=1200) and 50 px from the
  right frame edge (×N right edge x=1870 → frame 1920).
- Panel rows （横屏）: a 5-row window of distinct words ordered by
  most-recent occurrence; the CURRENT word is the BOTTOM row.
  Landscape selection rule, stated on its own: the current word's
  EN, ZH and ×N all turn gold together, with NO background highlight
  bar — color change only, never a bar. Before the first word is
  spoken, the first window is shown from frame 0 with the first word
  pre-selected gold (§7 panel-timing rule).
  Row pitch 150 px (was 178 — tightened 2026-10-25 so the list
  clears the subtitle zone); within a row (bottom-anchored): EN at
  y_en, ZH gloss + phonetic at y_en+56, dots at y_en+108 — giving
  ~14 px clear gaps between EN/ZH, ZH/dots, and dots/next-row EN,
  so no two rows or row elements ever touch or overlap. Row 1 EN
  y=200, row 5 EN y=800 (ZH 856, dots bottom 908).
  BOUNDARY RULE (user 2026-10-25): the panel BACKGROUND (frost)
  runs to y=1080, but the vocab LIST never enters the subtitle
  zone — the last row's dots bottom (908) must clear the subtitle
  EN top (928) by ≥10 px (here 20 px). Only background sits under
  the subtitles, never list text. Verify by frame check: no row
  element may touch or overlap any subtitle line.
- Each row: EN word (48 px, pale #C7D8C7; current word 57 px gold
  bold; phrases / words over 14 chars render smaller: 38 px,
  current 41 px gold) — ZH gloss + phonetic below it (42 px white;
  current 48 px gold), phonetic in a SINGLE slash pair AFTER the
  gloss — ×N right-aligned at x=1870 (38 px gray; current 44 px
  gold). ×N is a fixed right-aligned column at x=1870.
- Dots row under each gloss (30 px): one dot per occurrence (capped
  at 14, scaled proportionally) — filled gold = already occurred
  (for the current word this includes the ongoing occurrence),
  hollow gray = remaining. The ×N number stays authoritative.
- Subtitles, exact geometry (2026-10-25 user rule, size order
  corrected the same day — see color/size order below): centered
  on the FULL frame (x=960), NO background — the lines float
  transparently over the person area and the vocab-panel
  background. EN 72 px white bold, top at y=928 (bottom ≈1000);
  ZH 60 px gold, top at y=1012 (bottom ≈1072); EN/ZH gap 12 px,
  never touching. One clause per card; EN 1 line + ZH 1 line per
  card, always (see the card rule below — 2-line blocks are
  forbidden: they push the EN line up into the panel dots).
  Vocab words in the subtitle are highlighted yellow-bold;
  wrap-never-truncate: a clause that would wrap is split into
  more cards instead (EN wraps within the frame width, centered
  style — no line may touch the left/right frame edge, verified
  by frame). All Chinese text is Simplified Chinese (the
  reference frame's Traditional glyphs are NOT copied; §14b
  Traditional is TikTok-only).
- Color + size order (user 2026-10-25, per the MJ reference frame
  the user sent — the user confirmed 2026-10-25: follow THAT frame
  for sizes and colors, no further re-derivation; these values are
  FROZEN): four treatments as in the reference — vocab EN GREEN
  (#6EC88C, ASS &H008CC86E — the reference's mint, deepened only
  enough to read as green on our brightened frost, where the
  earlier pale mint #C7D8C7 washed out to white), vocab ZH white,
  subtitle EN white bold, subtitle ZH GOLD (#FFC61A, ASS
  &H001AC6FF — the reference's gold, deepened only enough to read
  as gold on frost, where the earlier pale gold #F5D67B washed out
  to near-white). The current-word highlight uses the same gold.
  Note, as in the reference: vocab ZH and subtitle EN are both
  white by design — told apart by size (42 vs 72) and weight
  (regular vs bold). Size order, largest to smallest: subtitle EN
  72 > subtitle ZH 60 > vocab EN 48 > vocab ZH 42. (The subtitle
  ZH is deliberately LARGER than the vocab EN here — the earlier
  v6 demo had it inverted, 42 vs 56, and the hierarchy read
  backwards against the reference.)
- Subtitle cards, one clause per card (user 2026-10-25, from the
  v6b g73 defect): a landscape subtitle card is ALWAYS EN 1 line
  + ZH 1 line, never more. A 2-line ZH block shifts the whole
  block upward (EN center pulled to y=885) and the EN line then
  collides with the panel's last-row dots (dots bottom 908) — the
  g73 frame showed the EN line and the panel dots touching. So:
  any sentence that would wrap to 2 lines in either language is
  SPLIT by clause boundaries (then phrase/comma boundaries if a
  single clause still overflows) into more cards, EN/ZH paired per
  card, times split by word timestamps — the same clause-split
  method as the vertical safe-zone rule (§9). Multi-line shift
  arithmetic is therefore retired for landscape: no card ever
  needs it, because no card ever has 2 lines. The panel boundary
  (dots 908 vs EN top 928) holds precisely because every card is
  1+1 lines.
  Anchor alignment (2026-10-25 Yahoo v6c lesson): a Chinese cut
  placed by proportional position can misplace a distinctive ASCII
  token (person/brand/number name, upper-case or numeric) into the
  neighbouring card — anchor the Chinese cut to that token
  instead (extend the previous card's last Chinese word past the
  punctuation, or cut the next card's first word forward),
  provided the anchor sits within half a span of the proportional
  target (guards against false matches); Chinese punctuation
  boundaries set by the translator still take priority over
  anchors.
  Chinese split must never break a word (2026-10-25 Yahoo v6c
  lesson): a card split that lands inside a Chinese word (e.g.
  构建|自己, 应该|建立 split across two cards) is a defect even
  when both cards stay within 1+1 lines. Split only at word
  boundaries; if a balanced split would cut a word, move the whole
  word to the next card. QC: re-joining the split cards' Chinese
  must reconstruct the original sentence character-for-character —
  no character lost, duplicated, or stranded. This applies to the
  vertical clause splits (§9) as well as landscape cards.
  Numeric tokens stay whole (2026-10-25 Yahoo v6c lesson): a number
  with its unit or percent sign (e.g. 80%) must never be split
  across cards — if a split would separate the number from "%" or
  put the token itself across the boundary, move the whole token
  to the next card. This extends the ASCII-token anchor rule above
  to numbers and percentages, which the anchor rule alone did not
  catch.
  Rework junction check (2026-10-25 user rule): after any rework
  that touches a contiguous block (re-translation, re-cut,
  re-build), verify BOTH ends of the adjusted block before
  delivery: the subtitle-card timeline must neither overlap nor
  drop/duplicate a card across either junction, frame-check both
  sides of each junction, and confirm audio/video continuity at
  the rebuilt pieces' splice points; report both junctions
  explicitly.
- Outro: `make_outro_landscape()` renders the same 4 s fan-group card
  at 1920x1080 (same texts/brand); append with `concat_mp4s()` exactly
  like vertical (§14a). The 4 s does not count toward the §12 cap.
  Plus the §0 attribution line in small gray text beneath the fixed
  card copy (via the `source_line` parameter):
  `原视频：{频道名}《{原标题}》` — mandatory on every video, the fixed
  card copy itself stays unchanged.

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
- **Mechanical gates do NOT certify translation (2026-10-25 Yahoo
  v6c lesson)**: v6c passed every mechanical gate — exact frame
  count, clean decode, freeze only on the outro card, panel
  boundary, 675 cards all 1+1 lines — and still reached delivery
  with a ~46-segment shifted translation block. Delivery QC must
  therefore include the §5 translation-shift audit (semantic
  EN-ZH correspondence scan + eye-check of block head/middle/
  tail) as a SEPARATE gate; a file that passes only the
  mechanical gates is not cleared for delivery.
- **Post-render political re-scan (2026-10-25 Yahoo v6d method)**:
  after the final render, scan the full burned subtitle text plus
  the vocab-panel text for political keywords and read every hit
  in context; separately verify that every marker phrase of any
  block cut at §6 is ABSENT from the finished video. This is a
  post-render gate, distinct from the pre-compose §6 screening —
  a cut that was decided but not actually removed must be caught
  here, not by the user.

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

### 16. 切片 — 从成片切短视频矩阵（2026-10-27 用户立下，通用）

- 只从已交付的成片母带直切：ffmpeg 按段边界精确截取、重编码，画面、字幕、生词栏原样保留；不重渲染、不改布局、不碰母带与段数据；绝不含片尾卡；绝不起于半句、止于半句。
- 选段标准（按序）：反直觉结论、具体数字或例子、生词密度高、完整问答；跳过自我介绍、寒暄、过渡语。
- 分层：获客层 30–90 秒（一个结论加一个例子）；承接层 1–3 分钟（一个完整问答加生词）；完整版只做合集锚点，不考核播放量。
- 一次性交付审核：同一访谈的全部切片一次交齐给用户审片（附每支的母带时间、标题、描述、标签），不一支一支零散交付。
- 审核门禁：用户审完定夺（可整批通过或单支调整）后才可上传；任何一支用户没点头的不传；发后不删改重传（§9c）。
- 上传节奏：通过后按隔天一支的顺序上传（2026-10-27 用户定，先跑两周看数据再决定是否加密）；窗口沿用 18:20。
- 封面：切片一律使用其完整视频的封面，不再每支单独配封面帧。
- 标题与描述：由助手自行把握，但必须遵守账号文案口径（只写客观事实，不自夸；描述末尾带来源行「原视频：{频道名}《{原标题}》」；标签沿用该访谈的标签组）。
- 合集归属：切片进该访谈的切片合集（每访谈一个）；完整版进全账号共用的「访谈完整版」合集（收全部已发布完整视频）；完整版合集封面不带人名。
- 上传分工：完整版文件大，由用户自己传；切片由助手传。

### 17. 分工 — 助手做 vs 提醒用户做（2026-10-27 用户立下，通用）

助手做的事（不用用户动手）：
- 全流程代跑：三层审查、双平台同源核查、转写、翻译、生词、合成、核实截图、视频封面与合集封面设计。
- 切片：从成片直切、批量交齐审核、标题/描述/标签把握、合集归属。
- 网页端操作：建合集、换合集封面、往合集加视频、隔天一支上传已通过审核的切片（窗口 18:20）。
- 数据复盘：每支发完 72 小时看 2 秒跳出率、完播率、单支涨粉数、合集新增关注并汇报。
- skill 维护与 GitHub 推送（用户给 token 后）。

必须提醒用户做的事（每项都要列入交付清单，不能只在聊天里提一句）：
- 审片定发：成片与切片批量审核，用户说"发"才发；没点头的不传。
- 完整版自己上传（文件大）。
- App 内置顶轮换：置顶位固定 3 个（最新完整版、数据最好切片、机动 1 个）；每出新访谈，提醒用户把置顶换成最新完整版（置顶网页端失败，只能 App 内做）。
- App 内看审核通知：视频被判不适宜公开等情况，以 App 审核通知为准。
- App 内改简介、头像（如需）。
- 选片拍板：三层审查命中、台湾话题例外等，必须用户定夺后才开工。
- 推送时提供 GitHub token（聊天里给，用后撤销）。

## Workflow with the user

- User sends a URL → run stages 1–7 → sample frames for approval →
  full render → user verifies the finished video → publish only on the
  user's explicit go-ahead.
- Orientation: the user says 横屏 or 竖屏 per video (default 竖屏）;
  横屏 uses §9L functions, everything else is identical.
- **Progress estimates are re-based every round (2026-10-25 Yahoo
  v6c lesson)**: never carry an estimate over from a previous
  round — the v6b round's "1–1.5 hours" was quoted for v6c after
  the scope had changed (color deepening + clause re-splitting
  forced a full re-render), and had to be corrected to ~2.5 hours.
  Recompute from the CURRENT round's measured piece speed and
  remaining piece count, and always present the number as an
  estimate, never a commitment.

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

### 9c. 长期规则补遗（2026-10-16/17 用户立下，之前漏记；方向见 Orientation map：标【竖】的仅竖屏，其余共用）

- **核实截图必须带字幕**：发布前的开始/中间/结束 3 张截图必须含字幕区+生词栏完整界面，无字幕用户无法审批布局
- **插图可放生词界面左侧**：独立于裁剪方案的长期要求
- **不压制画质**：成片在 1GB 上限内用原画质直接发布，不为上传压缩（2026-10-17 用户否决压缩提议）
- **发后不删改重传**：标题、描述、封面、标签发布前一次弄对，发出去就别动——同一视频删掉原样重传会被平台去重机制判"重复/搬运"压推荐，已跑起来的版本删掉等于浪费推荐 momentum（2026-10-18 v13 教训）
- **生词栏标题**（"本集生词 N 个"）：与生词列表左对齐并拉开距离，不得重叠
- **面板位置**【竖】：y=180，接近灵动岛但不被覆盖（v13 定版）
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
