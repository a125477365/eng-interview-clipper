#!/usr/bin/env python3
"""Server-side full-audio extract (runs ON the home server).

Extracts the full audio track from the source into full_audio.m4a
(AAC 160k, 48kHz stereo), the audio input the render stage needs.

Usage (on the server, in the job work dir):
  server_extract_audio.py <source.mp4> [full_audio.m4a]
  Default output: full_audio.m4a in the same dir as the source.
"""
import subprocess, sys, os

FFMPEG = '/root/ffmpeg-static/ffmpeg'
FFPROBE = '/root/ffmpeg-static/ffprobe'
THREADS = '12'

def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(src)), 'full_audio.m4a')
    if os.path.exists(out):
        r = subprocess.run([FFPROBE, '-v', 'error', '-show_entries',
                            'format=duration', '-of', 'csv=p=0', out],
                           capture_output=True, text=True)
        try:
            d = float(r.stdout.strip())
        except Exception:
            d = -1.0
        if d > 0:
            print(f'SKIP {out} already extracted (duration {d:.1f}s)')
            return
    r = subprocess.run([FFMPEG, '-nostdin', '-y', '-v', 'error',
                        '-threads', THREADS, '-i', src,
                        '-vn', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', out])
    if r.returncode != 0:
        sys.exit(r.returncode)
    print(f'AUDIO OK {out}')

if __name__ == '__main__':
    main()
