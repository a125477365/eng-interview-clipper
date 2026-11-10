#!/usr/bin/env python3
"""Server-side mini build (runs ON the home server).

Port of the local build_mini.py: builds the person-zone mini (1150x1080,
30 fps) from the source, window by window, then concatenates. Same window
types (med / cu / strip2 / strip3, optional feathered patch). Same
intermediate params (libx264 veryfast crf 18 yuv420p 30fps frag).

Differences from the local version:
- Uses the server's static ffmpeg/ffprobe.
- 12-thread cap.
- Total frame count is derived from the windows JSON (last window's fe),
  not hardcoded, so this script works for any video.

Server ffmpeg: /root/ffmpeg-static/ffmpeg (7.0.2-static).
Server ffprobe: /root/ffmpeg-static/ffprobe.

Usage (on the server, in the job work dir):
  server_build_mini.py <source.mp4> <windows.json> <mini.mp4>
  windows.json: [{"key": ..., "type": "med"|"cu"|"strip2"|"strip3",
                  "fs": 0, "fe": 9800, ...}, ...] — contiguous, first fs=0.
  The windows JSON is built on the VM (face_detect / scene analysis) and
  transferred as a small file.
"""
import json, subprocess, sys, os

FFMPEG = '/root/ffmpeg-static/ffmpeg'
FFPROBE = '/root/ffmpeg-static/ffprobe'
THREADS = '12'

MASTER, WIN_JSON, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
wins = json.load(open(WIN_JSON))
WORKDIR = os.path.dirname(os.path.abspath(OUT))
TOTAL = wins[-1]['fe']

def run(cmd, what):
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f'{what}: {"OK" if r.returncode == 0 else "FAIL rc=" + str(r.returncode)}',
          flush=True)
    if r.returncode != 0:
        print(r.stderr[-2000:])
        raise SystemExit(f'{what} failed')

def count_frames(path):
    r = subprocess.run([FFPROBE, '-v', 'error', '-count_frames',
                        '-select_streams', 'v:0',
                        '-show_entries', 'stream=nb_read_frames',
                        '-of', 'csv', path], capture_output=True, text=True)
    try:
        return int(r.stdout.strip().split(',')[-1])
    except Exception:
        return -1

assert wins[0]['fs'] == 0, 'first window must start at frame 0'
for a, b in zip(wins, wins[1:]):
    assert b['fs'] == a['fe'], f"gap/overlap: {a['key']} fe={a['fe']} vs {b['key']} fs={b['fs']}"

def blur_params(pw, ph):
    m = min(pw, ph)
    lr = max(1, min(20, (m - 4) // 2))
    cr = max(1, min(8, (m - 4) // 4))
    return f"lr={lr}:cr={cr}:lp=2:cp=1"

def feather_chain(parts, tag, src, px, py, pw, ph, frame_w=None, frame_h=None):
    ramp = max(4, min(22, min(pw, ph) // 2))
    terms = []
    if not (frame_w and px == 0):
        terms.append("X")
    if not (frame_h and py == 0):
        terms.append("Y")
    if not (frame_w and px + pw >= frame_w):
        terms.append("(W-1-X)")
    if not (frame_h and py + ph >= frame_h):
        terms.append("(H-1-Y)")
    BS = chr(92)
    dist = terms[0]
    for t in terms[1:]:
        dist = f"min({dist}{BS},{t})"
    geq = (f"geq=r='r(X{BS},Y)':g='g(X{BS},Y)':b='b(X{BS},Y)':"
           f"a='255*min(1{BS},{dist}/{ramp})'")
    parts.append(f"[{src}]split[{tag}a][{tag}b]")
    parts.append(f"[{tag}b]crop={pw}:{ph}:{px}:{py},boxblur={blur_params(pw, ph)},format=rgba,{geq}[{tag}bb]")
    parts.append(f"[{tag}a][{tag}bb]overlay={px}:{py}[{tag}out]")

for w in wins:
    fs, fe, n = w['fs'], w['fe'], w['fe'] - w['fs']
    out = os.path.join(WORKDIR, f"mini_{w['key']}.mp4")
    if os.path.exists(out) and count_frames(out) == n:
        print(f"SKIP {out} n={n} (already exact)", flush=True)
        continue
    base = "setpts=PTS-STARTPTS"
    t = w['type']
    if t == 'med':
        x0 = w['x0']
        if 'patch' in w:
            px, py, pw, ph = w['patch']
            parts = [f"[0:v]{base},crop=1150:1080:{x0}:0,setsar=1,format=yuv420p[pre]"]
            feather_chain(parts, 'p', 'pre', px, py, pw, ph, frame_w=1150, frame_h=1080)
            vf = ";".join(parts) + ";[pout]format=yuv420p"
        else:
            vf = f"{base},crop=1150:1080:{x0}:0,setsar=1,format=yuv420p"
    elif t == 'cu':
        x0, y0, cw = w['x0'], w['y0'], w['w']
        ch = round(cw * 1080 / 1150)
        vf = (f"{base},crop={cw}:{ch}:{x0}:{y0},"
              f"scale=1150:1080:flags=lanczos,setsar=1,format=yuv420p")
    elif t in ('strip2', 'strip3'):
        k = 2 if t == 'strip2' else 3
        labels = 'abc'[:k]
        chains = []
        for i, (lbl, s) in enumerate(zip(labels, w['strips'])):
            chains.append(f"[{lbl}]crop={s['w']}:{s['h']}:{s['x0']}:{s['y0']},"
                          f"scale={s['tw']}:1080:flags=lanczos,setsar=1,"
                          f"format=yuv420p[s{i}]")
        ins = "".join(f"[{c}]" for c in labels)
        vf = (f"[0:v]{base},split={k}{ins};" + ";".join(chains) +
              f";[s0][s1]" + ("[s2]" if k == 3 else "") + f"hstack={k},format=yuv420p")
    else:
        raise SystemExit(f"unknown window type {t}")
    ss = fs / 30.0
    run([FFMPEG, '-nostdin', '-y', '-v', 'error', '-threads', THREADS,
         '-ss', f'{ss:.4f}', '-i', MASTER,
         '-vf', vf, '-an', '-c:v', 'libx264', '-preset', 'veryfast',
         '-crf', '18', '-pix_fmt', 'yuv420p', '-r', '30',
         '-threads', THREADS, '-frames:v', str(n),
         '-movflags', 'frag_keyframe+empty_moov', out],
        f"mini {w['key']} [{fs},{fe})")
    assert count_frames(out) == n, f"{out} frame count != {n}"

concat_txt = os.path.join(WORKDIR, 'concat_mini.txt')
with open(concat_txt, 'w') as f:
    for w in wins:
        f.write(f"file '{os.path.abspath(os.path.join(WORKDIR, 'mini_' + w['key'] + '.mp4'))}'\n")
run([FFMPEG, '-nostdin', '-y', '-v', 'error', '-threads', THREADS,
     '-f', 'concat', '-safe', '0', '-i', concat_txt,
     '-c:v', 'copy', '-movflags', 'frag_keyframe+empty_moov', OUT],
    'mini concat')
n = count_frames(OUT)
print(f'mini total frames: {n} GATE {TOTAL}:',
      'PASS' if n == TOTAL else 'FAIL')
assert n == TOTAL
print('MINI DONE', OUT)
