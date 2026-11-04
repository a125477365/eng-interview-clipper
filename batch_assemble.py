"""Batch final assembly (EP1 assemble_para.py, parameterized).
Layout per version (NO intro, §24f): seg_p01, xf01_02, ..., seg_pN,
outro(4s). Stream-copy concat. Usage: python3 batch_assemble.py <ep_dir> <nn>
Outputs <ep_dir>/bedtime_epNN_para.mp4 (simplified) and
<ep_dir>/bedtime_epNN_trad_para.mp4 (traditional).
Outro segments are shared batch files (rebuilt 2026-11-03; EP1 outro
segments were deleted in the 2026-11-03 cleanup): batch/outro/outro_simp.mp4
and batch/outro/outro_trad.mp4 (same copy as EP1: 加入粉丝群／下载本期
视频声音内容／完整故事音频／account badge, 4s, silent).
"""
import json, os, subprocess, sys

EP, NN = sys.argv[1], sys.argv[2]
BATCH = '/home/hatch/workspace/new-lines/bedtime/batch-20261110'
n = len(json.load(open(f'{EP}/paras.json', encoding='utf-8'))['paragraphs'])

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print('FAILED:', ' '.join(cmd[:6]), r.stderr[-400:])
        raise SystemExit(1)

def dur(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                        'format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

def concat(entries, out):
    missing = [e for e in entries if not os.path.exists(e)]
    if missing:
        print('MISSING:', missing)
        raise SystemExit(1)
    lst = out + '.concat.txt'
    with open(lst, 'w') as f:
        for e in entries:
            # ffmpeg concat resolves relative file paths against the list
            # file's directory, not the CWD; the list lives inside ep_dir,
            # so CWD-relative entries would double the ep_dir prefix
            # (2026-11-04 EP3: 'ep03/ep03/...' failure). Absolute paths.
            f.write(f"file '{os.path.abspath(e)}'\n")
    run(['ffmpeg', '-nostdin', '-y', '-f', 'concat', '-safe', '0',
         '-i', lst, '-c', 'copy', out])
    print(f'FINAL {out}: {dur(out):.3f}s', flush=True)

def main():
    simp, trad = [], []
    for k in range(1, n + 1):
        simp.append(f'{EP}/segments_para/seg_p{k:02d}.mp4')
        trad.append(f'{EP}/segments_para_trad/seg_p{k:02d}.mp4')
        if k < n:
            xf = f'{EP}/segments_xf/segments_xf{k:02d}_{k + 1:02d}.mp4'
            simp.append(xf)
            trad.append(xf)
    simp.append(f'{BATCH}/outro/outro_simp.mp4')
    trad.append(f'{BATCH}/outro/outro_trad.mp4')
    concat(simp, f'{EP}/bedtime_ep{NN}_para.mp4')
    concat(trad, f'{EP}/bedtime_ep{NN}_trad_para.mp4')

if __name__ == '__main__':
    main()
