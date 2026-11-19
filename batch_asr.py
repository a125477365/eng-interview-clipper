"""Batch ASR loopback check (EP1 asr_check.py, parameterized, §24b).
Transcribes concatenated paragraph audio with faster-whisper, diffs word
by word against script.jsonl. Reports only; never edits script/audio.
Usage: ~/workspace/.venv-media/bin/python batch_asr.py <ep_dir>
Writes <ep_dir>/asr_check_para.json.
"""
import difflib, glob, json, os, subprocess, sys

# ffmpeg on 2225 lives in the conda base Library\bin, not on PATH for
# the asr env: add it so the 'ffmpeg' calls below resolve (2026-11-19).
for _d in (r'E:\miniconda3\Library\bin',
           os.path.join(os.path.dirname(sys.executable), '..', 'Library', 'bin')):
    if os.path.isdir(_d) and _d not in os.environ.get('PATH', ''):
        os.environ['PATH'] = _d + os.pathsep + os.environ['PATH']

# CUDA DLLs from pip nvidia packages (Windows): ctranslate2 loads
# cublas64_12.dll via PATH, not via add_dll_directory (2026-11-19).
# Prepend the nvidia bin dirs so GPU ASR works when run from 2225.
_site = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages')
for _d in glob.glob(os.path.join(_site, 'nvidia', '*', 'bin')):
    if os.path.isdir(_d) and _d not in os.environ.get('PATH', ''):
        os.environ['PATH'] = _d + os.pathsep + os.environ['PATH']

EP = sys.argv[1]
AUD = os.path.join(EP, 'audio_para')
paras = json.load(open(f'{EP}/paras.json', encoding='utf-8'))['paragraphs']
rows = [json.loads(l) for l in open(f'{EP}/script.jsonl', encoding='utf-8')
        if l.strip()]

def norm(w):
    w = w.strip().lower().replace('\u2019', "'").replace('\u2018', "'")
    return w.strip('.,!?":;()[]{}<>-\u2014\u2013')

def main():
    from faster_whisper import WhisperModel
    snaps = sorted(glob.glob(os.path.expanduser(
        '~/.cache/huggingface/hub/models--Systran--faster-whisper-small'
        '/snapshots/*/')))
    path = snaps[0] if snaps else 'small'
    print(f'whisper model: {path}', flush=True)
    lst = os.path.join(AUD, 'asr_list.txt')
    with open(lst, 'w') as f:
        for k in range(1, len(paras) + 1):
            # ffmpeg concat resolves relative file paths against the list
            # file's directory, not the CWD (2026-11-04 EP3: doubled path
            # failure, same class as batch_assemble.py). Absolute paths,
            # native separators: ffmpeg 4.3.1's concat demuxer on Windows
            # only recognises backslash absolute paths (forward-slash
            # entries get the list dir prepended, 2026-11-19).
            p = os.path.abspath(f'{AUD}/p{k:02d}.wav')
            f.write(f"file '{p}'\n")
    wav = os.path.join(AUD, 'asr_concat.wav')
    subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-f',
                    'concat', '-safe', '0', '-i', lst, '-c', 'copy', wav],
                   check=True)
    # GPU-first (2026-11-19 user order): CUDA on 2225 (asr env, verified
    # 2026-11-19 faster-whisper 1.2.1 + ctranslate2 4.9.0), else CPU int8.
    try:
        r = subprocess.run(['nvidia-smi', '-L'], capture_output=True,
                           text=True, timeout=30)
        has_gpu = r.returncode == 0 and 'GPU' in r.stdout
    except Exception:
        has_gpu = False
    if has_gpu:
        model = WhisperModel(path, device='cuda', compute_type='float16')
        print('ASR device: cuda float16', flush=True)
    else:
        model = WhisperModel(path, device='cpu', compute_type='int8')
        print('ASR device: cpu int8', flush=True)
    import numpy as np
    r = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', wav,
                        '-ar', '16000', '-ac', '1', '-f', 's16le', '-'],
                       capture_output=True, check=True)
    audio = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _ = model.transcribe(audio, language='en', beam_size=5)
    heard = []
    for seg in segments:
        for w in seg.text.split():
            nw = norm(w)
            if nw:
                heard.append(nw)
    expected = []
    for i, r in enumerate(rows, 1):
        for w in r['en'].split():
            nw = norm(w)
            if nw:
                expected.append((i, nw))
    exp_words = [w for _, w in expected]
    sm = difflib.SequenceMatcher(None, exp_words, heard, autojunk=False)
    missing, extra = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ('delete', 'replace'):
            for idx in range(i1, i2):
                missing.append({'sentence': expected[idx][0], 'word': expected[idx][1]})
        if tag in ('insert', 'replace'):
            ctx = exp_words[max(0, i1 - 2):i1]
            extra.append({'heard': heard[j1:j2], 'after': ctx})
    matched = sum(b[2] for b in sm.get_matching_blocks())
    rep = {'expected_words': len(exp_words), 'heard_words': len(heard),
           'matched_words': matched, 'missing': missing, 'extra': extra}
    json.dump(rep, open(f'{EP}/asr_check_para.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"ASR CHECK expected={len(exp_words)} heard={len(heard)} "
          f"matched={matched} missing={len(missing)} extra_chunks={len(extra)}", flush=True)
    for m in missing[:40]:
        print(f"  MISS s{m['sentence']}: {m['word']}", flush=True)
    for e in extra[:20]:
        print(f"  EXTRA {e['heard']} after {e['after']}", flush=True)

if __name__ == '__main__':
    main()
