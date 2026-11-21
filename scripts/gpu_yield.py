#!/usr/bin/env python3
"""Run training jobs on one shared GPU, yielding it to other users.

Rules:
  - at most one job, on one GPU, at a time;
  - a job starts only on a GPU that has had no process of anyone for
    --idle-minutes (checked every --interval seconds);
  - the job never makes all GPUs busy: it starts only if at least one other
    GPU is free too, and it yields as soon as every other GPU is in use;
  - when a process of another user appears on our GPU, the job gets SIGTERM:
    train_tagger.py then saves a checkpoint and exits with code 75, and the
    GPU is free within about a minute;
  - a yielded job is restarted later with --resume, on whatever GPU has been
    idle long enough;
  - jobs run at the lowest CPU and I/O priority;
  - creating the file STOP next to this script's log ends everything cleanly.

Jobs come from a JSON file: [{"name": ..., "args": [...]}, ...], each args a
train_tagger.py command line without --resume. Finished jobs are recorded in
the state file and skipped on restart.

Usage:
    gpu_yield.py --jobs JOBS.json --workdir ~/orca [--idle-minutes 30] [--interval 60]
"""
import argparse
import getpass
import json
import os
import signal
import subprocess
import sys
import time

ME = getpass.getuser()


def log(path, msg):
    line = time.strftime('%Y-%m-%d %H:%M:%S ') + msg
    print(line, flush=True)
    with open(path, 'a') as f:
        f.write(line + '\n')


def gpu_users():
    """{gpu index: set of users with a compute process on it}, for every GPU."""
    q = subprocess.run(['nvidia-smi', '--query-gpu=index,uuid', '--format=csv,noheader'],
                       capture_output=True, text=True, check=True).stdout
    uuid2idx = {}
    for line in q.strip().splitlines():
        i, u = [x.strip() for x in line.split(',')]
        uuid2idx[u] = int(i)
    users = {i: set() for i in uuid2idx.values()}
    q = subprocess.run(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader'],
                       capture_output=True, text=True, check=True).stdout
    for line in q.strip().splitlines():
        if not line.strip():
            continue
        u, pid = [x.strip() for x in line.split(',')]
        try:
            who = subprocess.run(['ps', '-o', 'user=', '-p', pid], capture_output=True, text=True).stdout.strip()
        except Exception:
            who = '?'
        users[uuid2idx.get(u, -1)] = users.get(uuid2idx.get(u, -1), set()) | {who or '?'}
    return users


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', required=True)
    ap.add_argument('--workdir', required=True)
    ap.add_argument('--idle-minutes', type=float, default=30)
    ap.add_argument('--interval', type=int, default=60)
    args = ap.parse_args()
    os.chdir(os.path.expanduser(args.workdir))
    logf, statef, stopf = 'yield.log', 'yield-state.json', 'STOP'
    state = json.load(open(statef)) if os.path.exists(statef) else {'done': [], 'failed': {}}
    jobs = [j for j in json.load(open(args.jobs)) if j['name'] not in state['done']]
    idle_since = {}
    proc, job, gpu = None, None, None
    log(logf, f'watchdog started for {len(jobs)} jobs; user {ME}')
    while True:
        if os.path.exists(stopf):
            if proc and proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
                proc.wait()
            log(logf, 'STOP file found; exiting')
            return
        try:
            users = gpu_users()
        except Exception as e:
            log(logf, f'nvidia-smi failed: {e}')
            time.sleep(args.interval)
            continue
        now = time.time()
        for i, us in users.items():
            if us - {ME} or (us and (proc is None or i != gpu)):
                idle_since.pop(i, None)          # someone (or a stray process of ours) is there
            else:
                idle_since.setdefault(i, now)
        if proc is not None:
            rc = proc.poll()
            if rc is None:
                others = users.get(gpu, set()) - {ME}
                all_busy = all(us for i, us in users.items() if i != gpu)
                if others or all_busy:
                    why = (f'another user ({", ".join(sorted(others))}) is on GPU {gpu}' if others
                           else 'every other GPU is in use')
                    log(logf, f'{job["name"]}: {why}; yielding')
                    proc.send_signal(signal.SIGTERM)
                    try:
                        proc.wait(timeout=600)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    idle_since.pop(gpu, None)
                    proc = None
            else:
                if rc == 0:
                    log(logf, f'{job["name"]}: finished')
                    state['done'].append(job['name'])
                    jobs = [j for j in jobs if j['name'] != job['name']]
                elif rc == 75:
                    log(logf, f'{job["name"]}: stopped with a checkpoint; will resume')
                else:
                    n = state['failed'].get(job['name'], 0) + 1
                    state['failed'][job['name']] = n
                    log(logf, f'{job["name"]}: exit code {rc} (failure {n})')
                    if n >= 3:
                        jobs = [j for j in jobs if j['name'] != job['name']]
                        log(logf, f'{job["name"]}: given up after 3 failures')
                json.dump(state, open(statef, 'w'), indent=1)
                proc = None
        if proc is None:
            if not jobs:
                log(logf, 'all jobs done; exiting')
                return
            ready = [i for i, t in idle_since.items() if now - t >= 60 * args.idle_minutes]
            free = [i for i, us in users.items() if not us]
            if ready and len(free) >= 2:          # leave at least one GPU free for others
                gpu, job = ready[0], jobs[0]
                env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), HF_HUB_OFFLINE='1')
                cmd = ['nice', '-n', '19', 'ionice', '-c', '3', '.venv/bin/python', 'scripts/train_tagger.py'] + job['args'] + ['--resume']
                out = open(f'train-{job["name"]}.log', 'a')
                proc = subprocess.Popen(cmd, env=env, stdout=out, stderr=subprocess.STDOUT)
                log(logf, f'{job["name"]}: started on GPU {gpu} (pid {proc.pid})')
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
