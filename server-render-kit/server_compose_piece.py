#!/usr/bin/env python3
"""Server-side §9L v6 piece compose (runs ON the home server).

Mirrors ~/workspace/clip2vertical/work/hmtuvNfytjM/compose_piece.py exactly
(same filter_complex, same §9L v6 layout, same skip-if-exact), but uses the
server's static ffmpeg and fonts. Does NOT import clipper from the VM.
Self-contained: only ffmpeg + ffprobe + input files.

Server ffmpeg: /root/ffmpeg-static/ffmpeg (7.0.2-static, libx264 + libass).
Server ffprobe: /root/ffmpeg-static/ffprobe.
Fonts: /root/fonts (ASS filter needs fontsdir=/root/fonts).
Thread cap: 12 (server has 16 threads; leave headroom for Frigate/hermes).

Usage (on the server, in the job work dir):
  server_compose_piece.py <mini> <source> <audio_m4a> <ass> <fs_abs> <fe_abs>
       <ep_start_abs> <out>
  fs_abs/fe_abs: absolute 30 fps frame numbers in the full timeline.
  ep_start_abs: absolute 30 fps frame of the episode start (ASS shift origin).
  Audio is trimmed by absolute seconds; ASS is shifted by episode-local offset.
"""
import subprocess, sys, os

FFMPEG = '/root/ffmpeg-static/ffmpeg'
FFPROBE = '/root/ffmpeg-static/ffprobe'
FONTSDIR = '/root/fonts'
THREADS = '12'

def count_frames(path):
    r = subprocess.run([FFPROBE, '-v', 'error', '-count_frames',
                        '-select_streams', 'v:0', '-show_entries',
                        'stream=nb_read_frames', '-of', 'csv', path],
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith('stream,'):
            try:
                return int(line.split(',')[1])
            except ValueError:
                return -1
    return -1

def main():
    mini, src, audio, ass = sys.argv[1:5]
    fs, fe, ep_start = int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7])
    out = sys.argv[8]
    n = fe - fs
    if os.path.exists(out) and count_frames(out) == n:
        print(f'SKIP {out} n={n} (already exact)')
        return
    off_abs = fs / 30.0
    off_local = (fs - ep_start) / 30.0
    dur = n / 30.0
    # Same §9L v6 filter chain as the local compose_piece.py, plus
    # fontsdir for the ASS filter (server fonts live in /root/fonts).
    fc = (
        f"[0:v]setpts=PTS-STARTPTS[pv];"
        f"[1:v]fps=30,setpts=PTS-STARTPTS,"
        f"scale=36:20:flags=bilinear,scale=1920:1080:flags=bilinear,"
        f"lutrgb=r='val*0.62':g='val*0.62':b='val*0.70'[fr];"
        f"[fr][pv]overlay=0:0[v1];"
        f"[v1]setpts=PTS+{off_local:.3f}/TB[subin];"
        f"[subin]ass='{ass}':fontsdir={FONTSDIR}[vass];"
        f"[vass]setpts=PTS-{off_local:.3f}/TB,setsar=1,format=yuv420p[vout];"
        f"[2:a]atrim={off_abs:.3f}:{(fe / 30.0):.3f},asetpts=PTS-STARTPTS[aout]"
    )
    cmd = [FFMPEG, '-nostdin', '-y',
           '-threads', THREADS,
           '-ss', f'{off_abs:.3f}', '-i', mini,
           '-ss', f'{off_abs:.3f}', '-i', src,
           '-i', audio,
           '-filter_complex', fc,
           '-map', '[vout]', '-map', '[aout]',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
           '-threads', THREADS,
           '-r', '30', '-c:a', 'aac', '-b:a', '160k',
           '-frames:v', str(n), '-t', f'{dur:.3f}', out]
    print(' '.join(cmd), flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)
    m = count_frames(out)
    print(f'PIECE OK {out} frames={m} (expect {n})', flush=True)
    if m != n:
        print('PIECE FRAME COUNT MISMATCH')
        sys.exit(1)

if __name__ == '__main__':
    main()
