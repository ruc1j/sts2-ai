#!/usr/bin/env python3
"""Run rollout_choice over a fixed list of recorded observations with one
checkout's combat.py / official_agent.py, recording the chosen action.

Used to compare the base policy (main) with the candidate branch on the same
observations: PILOT-2 step 3.

    python3 pilot2_compare.py --root /Users/mao/workspace/sts2-ai \
        --tasks bosslab/results/pilot2_tasks.json --out /tmp/old.json
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time

ENEMY_FILES = ("enemies_overgrowth.json", "enemies_hive.json", "enemies_glory.json")
ROOT = None
DATA = None


def _init(root):
    global ROOT, DATA
    ROOT = root
    sys.path.insert(0, root)
    monsters = []
    for name in ENEMY_FILES:
        with open(os.path.join(root, "data", name), encoding="utf-8-sig") as f:
            monsters.extend(json.load(f)["monsters"])
    DATA = {"monsters": monsters}


def _run(task):
    path, index = task[0], task[1]
    kind = task[2] if len(task) > 2 else "?"
    import official_agent as OA
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i == index:
                    row = json.loads(line)
                    break
            else:
                return {"kind": kind, "skipped": "missing"}
    except (OSError, ValueError):
        return {"kind": kind, "skipped": "unreadable"}
    start = time.time()
    try:
        action = OA.rollout_choice(row, row.get("legal_actions") or [], DATA, 100)
        error = None
    except Exception as exc:  # noqa: BLE001 - compare failures, do not hide them
        action, error = None, type(exc).__name__
    elapsed = time.time() - start
    hand = {c.get("index"): c for c in row.get("hand") or ()}
    card_id = None
    is_power = False
    if action and action.get("type") == "card":
        card = hand.get(action.get("hand_index"))
        if card:
            card_id = card.get("id")
            is_power = card.get("type") == "Power"
    return {
        "kind": kind,
        "seq": row.get("seq"),
        "action": f"{action.get('type')}:{action.get('hand_index')}@{action.get('target_id')}" if action else None,
        "card_id": card_id,
        "power": is_power,
        "error": error,
        "elapsed": elapsed,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    args = ap.parse_args(argv)

    with open(args.tasks, encoding="utf-8") as f:
        tasks = [tuple(item) for item in json.load(f)]
    with mp.Pool(args.workers, initializer=_init, initargs=(args.root,)) as pool:
        results = pool.map(_run, tasks, chunksize=4)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    errors = sum(1 for r in results if r.get("error"))
    total = sum(r.get("elapsed") or 0 for r in results)
    print(f"{len(results)} decisions, {errors} errors, {total/len(results):.2f}s/decision -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
