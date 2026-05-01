#!/usr/bin/env python3
"""Concurrent load test for embedding service. Run before+after to compare."""
import json
import time
import urllib.request
import concurrent.futures

URL = "http://127.0.0.1:9900/embed"
TEXTS = [f"Test sentence number {i} for measuring concurrent embedding throughput." for i in range(50)]


def hit(text: str) -> float:
    req = urllib.request.Request(
        URL, data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    dur = time.time() - t0
    if "embedding" not in body:
        raise RuntimeError(f"bad response: {body}")
    return dur


def main():
    # Warmup
    hit("warmup")

    n_concurrent = 20
    n_total = 50
    print(f"Hitting {URL} with {n_total} requests at {n_concurrent}-way concurrency")
    t_start = time.time()
    durations = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_concurrent) as ex:
        futures = [ex.submit(hit, TEXTS[i]) for i in range(n_total)]
        for f in concurrent.futures.as_completed(futures):
            durations.append(f.result())
    wall = time.time() - t_start

    durations.sort()
    p50 = durations[len(durations) // 2]
    p95 = durations[int(len(durations) * 0.95)]
    print(f"Wall: {wall:.2f}s  ({n_total/wall:.1f} req/s)")
    print(f"  per-req min:  {durations[0]:.3f}s")
    print(f"  per-req p50:  {p50:.3f}s")
    print(f"  per-req p95:  {p95:.3f}s")
    print(f"  per-req max:  {durations[-1]:.3f}s")
    print(f"  per-req mean: {sum(durations)/len(durations):.3f}s")


if __name__ == "__main__":
    main()
