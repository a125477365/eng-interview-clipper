#!/usr/bin/env python3
"""Render dispatcher (runs on the VM) — server first, local fallback.

This is the single entry point for the interview render stage. It implements
the user's 2026-11-10 rule: prefer the server; only run locally when there
is no server available.

  1. Test whether the home server is reachable via SSH.
  2. If reachable: sync the server kit + the small job files (job.json, ASS,
     outro PNGs) to the server work dir, then run server_run_all.py there
     over SSH. The big inputs (source.mp4, mini.mp4, full_audio.m4a) must
     already be on the server (downloaded / built there — see README; they
     are NOT transferred over the slow tunnel).
  3. If NOT reachable: fall back to the local render (the existing local
     run_all.py in the local work dir, unchanged).

Usage:
  render_dispatch.py <local_work_dir> <server_work_dir> [ep1|ep2|all]
  local_work_dir: VM path, e.g. ~/workspace/clip2vertical/work/hmtuvNfytjM
  server_work_dir: e.g. /mnt/data_md0/Public/muse/hmtuvNfytjM
  ep: which episode to render (default all).

Server kit source (on the VM): the directory containing this file.
Small files synced: job.json, *.ass, outro_*.png (from the local work dir).
"""
import subprocess, sys, os, glob, json

SSH_BASE = [
    'ssh', '-i', '/home/hatch/.ssh/id_ed25519', '-p', '2222',
    '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
    '-o', 'ProxyCommand=nc -X connect -x hatch-egress-proxy:3128 %h %p',
    '-o', 'UserKnownHostsFile=/home/hatch/.ssh/known_hosts',
    'root@104.223.51.196',
]
SCP_BASE = [
    'scp', '-i', '/home/hatch/.ssh/id_ed25519', '-P', '2222',
    '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
    '-o', 'ProxyCommand=nc -X connect -x hatch-egress-proxy:3128 %h %p',
    '-o', 'UserKnownHostsFile=/home/hatch/.ssh/known_hosts',
]
KIT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_KIT_FILES = ['server_compose_piece.py', 'server_assemble.py',
                    'server_run_all.py', 'server_download.py',
                    'server_build_mini.py', 'server_extract_audio.py']

def server_reachable():
    r = subprocess.run(SSH_BASE + ['echo', 'ok'],
                       capture_output=True, text=True, timeout=30)
    return r.returncode == 0 and r.stdout.strip() == 'ok'

def ssh(cmd):
    r = subprocess.run(SSH_BASE + [cmd], capture_output=True, text=True)
    print(r.stdout, end='')
    if r.stderr:
        print(r.stderr, end='', file=sys.stderr)
    return r.returncode

def scp(local_path, remote_path):
    r = subprocess.run(SCP_BASE + [local_path, f'root@104.223.51.196:{remote_path}'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        raise SystemExit(f'scp failed: {local_path} -> {remote_path}')
    print(f'synced {local_path} -> {remote_path}')

def main():
    local_dir = os.path.abspath(sys.argv[1])
    server_dir = sys.argv[2]
    only = sys.argv[3] if len(sys.argv) > 3 else 'all'
    if server_reachable():
        print('server reachable — using SERVER render')
        ssh(f'mkdir -p {server_dir}')
        for f in SERVER_KIT_FILES:
            scp(os.path.join(KIT_DIR, f), os.path.join(server_dir, f))
        # Small job files only: job.json, windows.json, ASS, outro PNGs.
        job_json = os.path.join(local_dir, 'job.json')
        if os.path.exists(job_json):
            scp(job_json, os.path.join(server_dir, 'job.json'))
        else:
            print('WARNING: no job.json in local work dir — server needs one')
        for pat in ('windows.json', '*.ass', 'outro_*.png'):
            for f in sorted(glob.glob(os.path.join(local_dir, pat))):
                scp(f, os.path.join(server_dir, os.path.basename(f)))
        rc = ssh(f'cd {server_dir} && python3 server_run_all.py {only} job.json')
        if rc != 0:
            raise SystemExit(f'server render failed rc={rc}')
        print('SERVER RENDER DONE')
    else:
        print('server NOT reachable — falling back to LOCAL render')
        local_run = os.path.join(local_dir, 'run_all.py')
        if not os.path.exists(local_run):
            raise SystemExit(f'no local run_all.py in {local_dir}')
        r = subprocess.run([sys.executable, local_run, only], cwd=local_dir)
        if r.returncode != 0:
            raise SystemExit(f'local render failed rc={r.returncode}')
        print('LOCAL RENDER DONE (fallback)')

if __name__ == '__main__':
    main()
