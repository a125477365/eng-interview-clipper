#!/usr/bin/env python3
"""Server-side run_all driver (runs ON the home server).

Mirrors the local run_all.py: renders all compose pieces + assembles, serially
(one ffmpeg at a time). Order: ep1 simp -> ep1 trad -> ep2 simp -> ep2 trad
(complete films first).

Unlike the local run_all.py (which hardcodes one video's pieces), this driver
is config-driven so it works for any video. The job config JSON describes the
episodes, piece ranges, ASS files, outro PNGs, and finals.

Config JSON format:
{
  "mini": "mini.mp4", "source": "source.mp4", "audio": "full_audio.m4a",
  "pieces_dir": "pieces",
  "episodes": {
    "ep1": {
      "ep_start": 0,
      "pieces": [[0, 9800], [9800, 19600], ...],
      "ass": {"simp": "ass_ep1.ass", "trad": "ass_ep1_trad.ass"},
      "outro_png": {"simp": "outro_ep1_simp.png", "trad": "outro_ep1_trad.png"},
      "final": {"simp": "final_ep1_simp.mp4", "trad": "final_ep1_trad.mp4"},
      "content_frames": 58830, "t0": 0.0, "t1": 1961.0
    },
    "ep2": { ... }
  }
}
All paths in the config are relative to the job work dir (where this script
runs), except "full_audio" which is resolved the same way. The assemble step
gets a per-episode config JSON written to <ep>_<simp|trad>_assemble.json.

Usage (on the server, in the job work dir):
  server_run_all.py [ep1|ep2|all] [config.json]
  Default: all episodes, config.json = job.json in the work dir.
  Logs to run_all.log in the work dir.
Requires mini.mp4 to exist first; aborts otherwise.
"""
import subprocess, sys, os, json

W = os.path.dirname(os.path.abspath(__file__))
FFPROBE = '/root/ffmpeg-static/ffprobe'

def log(msg, logf):
    print(msg, flush=True)
    logf.write(msg + '\n')

def run(cmd, what, logf):
    log(f'RUN {what}: {" ".join(cmd)}', logf)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        log(f'FAIL {what} rc={r.returncode}', logf)
        raise SystemExit(f'{what} failed rc={r.returncode}')
    log(f'OK {what}', logf)

def count_frames(path):
    r = subprocess.run([FFPROBE, '-v', 'error', '-count_frames',
                        '-select_streams', 'v:0', '-show_entries',
                        'stream=nb_read_frames', '-of', 'csv', path],
                       capture_output=True, text=True)
    try:
        return int(r.stdout.strip().split(',')[-1])
    except Exception:
        return -1

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else 'all'
    cfg_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(W, 'job.json')
    with open(cfg_path) as f:
        cfg = json.load(f)
    mini = os.path.join(W, cfg['mini'])
    src = os.path.join(W, cfg['source'])
    audio = os.path.join(W, cfg['audio'])
    pieces_dir = os.path.join(W, cfg.get('pieces_dir', 'pieces'))
    logf = open(os.path.join(W, 'run_all.log'), 'a', buffering=1)
    eps = sorted(cfg['episodes'].keys()) if only == 'all' else [only]
    # Total frames expected in mini (sum of all episode content frames).
    total_frames = sum(e['content_frames'] for e in cfg['episodes'].values())
    n = count_frames(mini)
    log(f'mini frames: {n} (expect {total_frames})', logf)
    assert n == total_frames, 'mini.mp4 not ready — build it first'
    os.makedirs(pieces_dir, exist_ok=True)
    py = sys.executable
    for ep in eps:
        e = cfg['episodes'][ep]
        ep_start = e['ep_start']
        for trad in (0, 1):
            key = 'trad' if trad else 'simp'
            ass = os.path.join(W, e['ass'][key])
            prefix = f'piece_{ep}_trad' if trad else f'piece_{ep}'
            for i, (fs, fe) in enumerate(e['pieces'], 1):
                out = os.path.join(pieces_dir, f'{prefix}_{i}.mp4')
                run([py, os.path.join(W, 'server_compose_piece.py'),
                     mini, src, audio, ass, str(fs), str(fe),
                     str(ep_start), out],
                    f'{ep} {key} piece {i} [{fs},{fe})', logf)
            # Per-episode assemble config.
            acfg = {
                "content_frames": e['content_frames'],
                "t0": e['t0'], "t1": e['t1'],
                "full_audio": audio,
            }
            acfg_path = os.path.join(W, f'{ep}_{key}_assemble.json')
            with open(acfg_path, 'w') as f:
                json.dump(acfg, f)
            run([py, os.path.join(W, 'server_assemble.py'),
                 ep, str(trad), pieces_dir,
                 os.path.join(W, e['outro_png'][key]), acfg_path,
                 os.path.join(W, e['final'][key])],
                f'{ep} {key} assemble', logf)
    log('RUN_ALL DONE', logf)

if __name__ == '__main__':
    main()
