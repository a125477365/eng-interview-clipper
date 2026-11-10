# Server render kit — interview pipeline (server-first, local fallback)

Two codebases, one rule (2026-11-10 user order):
- **Server code** (this kit): runs ON the home server. Preferred. Use it whenever
  the server is reachable.
- **Local code** (unchanged): `clipper.py`, `run_all.py`, `compose_piece.py`,
  `assemble.py` under `~/workspace/custom-skills/eng_interview_clipper/` and the
  per-video work dirs. Runs on the VM. Used ONLY when there is no server
  available (server unreachable / no server address + credentials for the task).

The dispatcher (`render_dispatch.py`, runs on the VM) implements the priority:
it tests SSH to the server; if reachable it renders on the server, otherwise it
falls back to the local `run_all.py`. Model work (XTTS, whisper ASR, torch)
always stays on the VM — the server has no large models and no AVX2.

## What is in this kit (server-side, self-contained)

| File | Runs where | What it does |
|---|---|---|
| `server_download.py` | server | Download a YouTube source directly on the server (yt-dlp, installs it if missing; default format 137+140-2). Verifies via ffprobe. |
| `server_build_mini.py` | server | Build the person-zone mini (1150x1080, 30fps) from the source, window by window, from a `windows.json` (built on the VM, transferred as a small file). Same window types as the local `build_mini.py`; total frames derived from the windows. |
| `server_extract_audio.py` | server | Extract `full_audio.m4a` (AAC 160k, 48kHz) from the source. |
| `server_compose_piece.py` | server | One §9L v6 piece: mini + frost + ASS + audio slice. Same filter chain as the local `compose_piece.py`; server ffmpeg + `fontsdir=/root/fonts`; 12-thread cap. |
| `server_assemble.py` | server | One episode: outro PNG -> 4 s outro, concat pieces + outro, mux ep audio + 4 s silence. Takes episode config JSON (not hardcoded). |
| `server_run_all.py` | server | Driver: pieces + assemble for all episodes/versions, serially. Config-driven via `job.json`. |
| `render_dispatch.py` | **VM** | Entry point. Server first, local fallback. Syncs kit + small files, runs the server render over SSH, or falls back to local `run_all.py`. |

## Server prerequisites (verified 2026-11-10)

- SSH: `root@104.223.51.196:2222` (via egress proxy; key auth).
- ffmpeg/ffprobe: `/root/ffmpeg-static/ffmpeg` and `/root/ffmpeg-static/ffprobe`
  (7.0.2-static, libx264 + libass + fontconfig).
- Fonts: `/root/fonts/` (NotoSansCJK, DejaVuSans).
- Work dir: `/mnt/data_md0/Public/muse/` (writable, ~843 GB free).
- Thread cap: 12 (16 threads total; leave headroom for Frigate/hermes).
- Python 3.10 on the server.

## How a render runs on the server (preconditions)

The big inputs are produced ON the server — they are NOT transferred over
the slow (~0.7 MB/s) tunnel:
- `source.mp4`: `server_download.py <url> source.mp4` (yt-dlp; server reaches
  YouTube directly via OpenClash; installs yt-dlp if missing).
- `mini.mp4`: `server_build_mini.py source.mp4 windows.json mini.mp4`
  (`windows.json` is built on the VM and transferred as a small file).
- `full_audio.m4a`: `server_extract_audio.py source.mp4`.
- Small files (transferred by the dispatcher, fast): `job.json`,
  `windows.json`, `*.ass` (built on the VM from transcript/translation/
  vocab), `outro_*.png` (built on the VM with the local
  `clipper.make_outro_card_landscape`).

## Usage

1. On the VM, prepare the job in the local work dir as usual (transcribe,
   translate, vocab, ASS, outro PNGs, `job.json` — see `job.json` format in
   `server_run_all.py`).
2. Make sure `source.mp4`, `mini.mp4`, `full_audio.m4a` are in the server work
   dir (downloaded/built on the server).
3. Run the dispatcher from the VM:
   ```
   python3 render_dispatch.py <local_work_dir> <server_work_dir> [ep1|ep2|all]
   ```
   Example:
   ```
   python3 render_dispatch.py ~/workspace/clip2vertical/work/hmtuvNfytjM \
       /mnt/data_md0/Public/muse/hmtuvNfytjM all
   ```
   - Server reachable: renders on the server, finished videos land in the
     server work dir.
   - Server unreachable: falls back to the local `run_all.py` in the local
     work dir.
4. The finished videos stay on the server (upload to Drive from the server,
   or copy back once — a single transfer, not per-piece).

## Test status

- 2026-11-10: server ffmpeg/ffprobe/fonts verified present and working
  (7.0.2-static, libass + libx264). All kit scripts pass syntax check on the
  VM and on the server. A single-piece render test on the server is still
  pending — run it before the first real server render.
