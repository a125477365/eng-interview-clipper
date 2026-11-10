#!/usr/bin/env python3
"""Server-side YouTube download (runs ON the home server).

Downloads a source video directly on the server with yt-dlp. The server
reaches YouTube directly (OpenClash), so no proxy is needed. Installs yt-dlp
via pip if it is not already present.

Usage (on the server):
  server_download.py <youtube_url> <out_path> [format]
  format: yt-dlp -f value. Default: 137+140-2 (1080p video + English audio,
  the interview default). Use "bestvideo+bestaudio/best" for a generic best.
Verifies the download with ffprobe (duration > 0) and prints the size.
"""
import subprocess, sys, os, shutil

FFPROBE = '/root/ffmpeg-static/ffprobe'

def ensure_ytdlp():
    if shutil.which('yt-dlp'):
        return 'yt-dlp'
    print('yt-dlp not found — installing via pip ...', flush=True)
    r = subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', 'yt-dlp'])
    if r.returncode != 0:
        raise SystemExit('pip install yt-dlp failed')
    user_bin = os.path.expanduser('~/.local/bin/yt-dlp')
    if os.path.exists(user_bin):
        return user_bin
    if shutil.which('yt-dlp'):
        return 'yt-dlp'
    raise SystemExit('yt-dlp still not found after install')

def probe_duration(path):
    r = subprocess.run([FFPROBE, '-v', 'error', '-show_entries',
                        'format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return -1.0

def main():
    url, out = sys.argv[1], sys.argv[2]
    fmt = sys.argv[3] if len(sys.argv) > 3 else '137+140-2'
    ytdlp = ensure_ytdlp()
    if os.path.exists(out):
        d = probe_duration(out)
        if d > 0:
            print(f'SKIP {out} already downloaded (duration {d:.1f}s)')
            return
    cmd = [ytdlp, '--js-runtimes', 'node',
           '--extractor-args', 'youtube:player_client=web_embedded',
           '-f', fmt, '-o', out, url]
    print(' '.join(cmd), flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)
    d = probe_duration(out)
    sz = os.path.getsize(out) if os.path.exists(out) else -1
    print(f'DOWNLOAD OK {out} size={sz} ({sz/1e6:.1f} MB) duration={d:.1f}s', flush=True)
    if d <= 0 or sz <= 0:
        print('DOWNLOAD VERIFY FAILED')
        sys.exit(1)

if __name__ == '__main__':
    main()
