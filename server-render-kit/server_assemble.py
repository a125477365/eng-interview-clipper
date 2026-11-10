#!/usr/bin/env python3
"""Server-side assemble (runs ON the home server).

Mirrors ~/workspace/clip2vertical/work/hmtuvNfytjM/assemble.py, but:
- Uses the server's static ffmpeg/ffprobe.
- Does NOT import clipper from the VM. The outro card PNG is supplied as an
  input (generated on the VM with the existing local clipper code and
  transferred over — it is a small PNG, fast to copy). The server only
  loops the PNG into the 4 s outro video with ffmpeg, then concats + muxes.
- Episode config comes from a JSON file (not hardcoded), so this script is
  reusable across videos.

Server ffmpeg: /root/ffmpeg-static/ffmpeg (7.0.2-static).
Server ffprobe: /root/ffmpeg-static/ffprobe.
Thread cap: 12.

Usage (on the server, in the job work dir):
  server_assemble.py <ep> <trad:0|1> <pieces_dir> <outro_png> <config.json> <out_final>
  config.json: {"n_vocab": 151, "content_frames": 58830, "t0": 0.0, "t1": 1961.0,
                "full_audio": "/path/to/full_audio.m4a"}
  pieces_dir holds piece_<ep>[_trad]_<i>.mp4 (video+audio per piece).
Steps:
 1. outro PNG -> re-encode video-only to piece params (veryfast crf20
    yuv420p 30fps, exactly 120 frames).
 2. concat demuxer (video copy): pieces + outro -> video_only.
    Gate: frames == content_frames + 120.
 3. mux with episode audio + 4.0 s silence (AAC 48k stereo).
    Gate: size < 1GB, full decode clean.
"""
import os, subprocess, sys, json, re

FFMPEG = '/root/ffmpeg-static/ffmpeg'
FFPROBE = '/root/ffmpeg-static/ffprobe'
THREADS = '12'

def run(cmd, what):
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f'{what}: {"OK" if r.returncode == 0 else "FAIL rc=" + str(r.returncode)}', flush=True)
    if r.returncode != 0:
        print(r.stderr[-2000:])
        raise SystemExit(f'{what} failed')
    return r

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
    EP, TRAD, PIECES_DIR, OUTRO_PNG, CONFIG, OUT_FINAL = (
        sys.argv[1], sys.argv[2] == '1', sys.argv[3], sys.argv[4],
        sys.argv[5], sys.argv[6])
    with open(CONFIG) as f:
        C = json.load(f)
    CONTENT_FRAMES = C["content_frames"]
    TOTAL = C["t1"] - C["t0"] + 4.0
    FULL_AUDIO = C["full_audio"]
    W = os.path.dirname(os.path.abspath(OUT_FINAL))
    OUTRO_DIR = os.path.join(W, f'outro_{EP}_' + ('trad' if TRAD else 'simp'))
    os.makedirs(OUTRO_DIR, exist_ok=True)

    prefix = f'piece_{EP}_trad' if TRAD else f'piece_{EP}'
    _pat = re.compile(r'^' + re.escape(prefix) + r'_\d+\.mp4$')
    pieces = sorted(f for f in os.listdir(PIECES_DIR) if _pat.match(f))
    pieces = [os.path.join(PIECES_DIR, p) for p in pieces]
    assert pieces, f'no pieces in {PIECES_DIR} with prefix {prefix}'
    for p in pieces:
        n = count_frames(p)
        print(f'piece {p} frames={n}')

    # 1. Outro: loop the card PNG into a 4 s silent video, then re-encode
    #    to piece params (veryfast crf20 yuv420p 30fps, exactly 120 frames).
    outro_raw = os.path.join(OUTRO_DIR, 'outro_raw.mp4')
    if not os.path.exists(outro_raw) or count_frames(outro_raw) != 120:
        run([FFMPEG, '-nostdin', '-y', '-v', 'error',
             '-loop', '1', '-framerate', '30', '-i', OUTRO_PNG,
             '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
             '-t', '4.0', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
             '-r', '30', '-c:a', 'aac', '-shortest', outro_raw],
            'outro from card PNG')
    outro_v = os.path.join(OUTRO_DIR, 'outro_ep.mp4')
    run([FFMPEG, '-nostdin', '-y', '-v', 'error', '-threads', THREADS,
         '-i', outro_raw, '-an', '-c:v', 'libx264', '-preset', 'veryfast',
         '-crf', '20', '-pix_fmt', 'yuv420p', '-r', '30',
         '-movflags', 'frag_keyframe+empty_moov', outro_v],
        'outro re-encode')
    assert count_frames(outro_v) == 120, 'outro must be exactly 120 frames'

    # 2. Concat pieces + outro (video copy).
    concat_txt = os.path.join(OUTRO_DIR, 'concat_video.txt')
    with open(concat_txt, 'w') as f:
        for p in pieces:
            f.write(f"file '{p}'\n")
        f.write(f"file '{outro_v}'\n")
    video_only = os.path.join(OUTRO_DIR, 'video_only.mp4')
    run([FFMPEG, '-nostdin', '-y', '-v', 'error', '-threads', THREADS,
         '-f', 'concat', '-safe', '0', '-i', concat_txt,
         '-c:v', 'copy', '-movflags', 'frag_keyframe+empty_moov', video_only],
        'video concat')
    nv = count_frames(video_only)
    print(f'video frames: {nv} GATE {CONTENT_FRAMES + 120}:',
          'PASS' if nv == CONTENT_FRAMES + 120 else 'FAIL')
    assert nv == CONTENT_FRAMES + 120

    # 3. Episode audio + 4.0 s silence (48kHz, sample-exact), then mux.
    ep_audio = os.path.join(OUTRO_DIR, 'ep_audio.m4a')
    if not os.path.exists(ep_audio):
        run([FFMPEG, '-nostdin', '-y', '-v', 'error', '-threads', THREADS,
             '-i', FULL_AUDIO,
             '-af', f'atrim={C["t0"]:.3f}:{C["t1"]:.3f},asetpts=PTS-STARTPTS,'
                    f'apad=whole_dur={TOTAL:.3f},atrim=0:{TOTAL:.3f}',
             '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', ep_audio],
            'ep audio (content + 4s silence)')
    run([FFMPEG, '-nostdin', '-y', '-v', 'error', '-threads', THREADS,
         '-i', video_only, '-i', ep_audio,
         '-map', '0:v', '-map', '1:a',
         '-c:v', 'copy', '-c:a', 'copy',
         '-movflags', 'faststart', OUT_FINAL],
        'mux final')
    sz = os.path.getsize(OUT_FINAL)
    print(f'final: {OUT_FINAL} size={sz} ({sz/1e9:.2f} GB) <1GB:',
          'PASS' if sz < 1e9 else 'FAIL')
    assert sz < 1e9
    run([FFMPEG, '-nostdin', '-y', '-v', 'error', '-threads', THREADS,
         '-i', OUT_FINAL, '-f', 'null', '-'], 'full decode')
    print('ASSEMBLE DONE', OUT_FINAL)

if __name__ == '__main__':
    main()
