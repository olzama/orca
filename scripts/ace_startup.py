import sys, time, pickle, subprocess, statistics, os
sys.path.insert(0, 'scripts'); sys.path.insert(0, '.')
import supertag_ace as S
S._init('data/profiles-2025/dev')
items = pickle.load(open('data/bench/dev-debertav3large-tags.pkl', 'rb'))['items']
ids = [i for i in items if items[i].get('top')][:300]
ACE, DAT = S.ACE, S.DAT
def run(cmd, inp):
    t = time.perf_counter(); p = subprocess.run(cmd, input=inp, capture_output=True, text=True); return time.perf_counter() - t, p
base = [ACE, '-g', DAT, '-1', '-T', '--max-chart-megabytes=6000', '--max-unpack-megabytes=7000']
# 1. start + load, no sentence
w0 = [run(base, '')[0] for _ in range(15)]
# 2. one short sentence, no -L
w1 = [run(base, 'The dog barked.\n')[0] for _ in range(15)]
# 3. -L lists from real dev items: sizes and per-call time vs one process with that list
sizes, percall, inproc = [], [], []
for sid in ids[:40]:
    it = items[sid]; allowed, disabled, _ = S.allowed_and_disabled(it, 5, 0.001)
    L = ' '.join(sorted(disabled)); sizes.append((len(disabled), len(L)))
    dt, p = run(base + ['-L', L], it['text'] + '\n'); percall.append(dt)
    # same sentence 5 times in one process: per-sentence parse time inside a resident process
    dt5, p5 = run(base + ['-L', L], (it['text'] + '\n') * 5); inproc.append((dt5 - dt) / 4)
print('start+load, no sentence: median %.1f ms (min %.1f)' % (1000*statistics.median(w0), 1000*min(w0)))
print('one short sentence, no -L: median %.1f ms' % (1000*statistics.median(w1)))
print('-L size: median %d lexemes, %d chars (max %d chars)' % (statistics.median(s[0] for s in sizes), statistics.median(s[1] for s in sizes), max(s[1] for s in sizes)))
print('per-call with -L (40 dev sentences): median %.1f ms, mean %.1f' % (1000*statistics.median(percall), 1000*statistics.mean(percall)))
print('the same sentence repeated in one process: median %.1f ms per extra sentence, mean %.1f' % (1000*statistics.median(inproc), 1000*statistics.mean(inproc)))
