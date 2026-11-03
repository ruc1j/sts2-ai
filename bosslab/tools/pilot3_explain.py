#!/usr/bin/env python3
"""Print the per-action search rankings for a set of recorded observations,
under one checkout, so two candidate versions can be read side by side.

    python3 bosslab/tools/pilot3_explain.py --root <checkout> \
        --tasks /tmp/tasks.json --out /tmp/explain_v1.json
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys

MAIN = "/Users/mao/workspace/sts2-ai"
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
    import official_agent as OA
    import combat as C
    path, index = task
    with open(path, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if i == index:
                row = json.loads(line)
                break
        else:
            return None
    captured = {}

    def fake_search(combat, data, simulations=0, seed=0):
        captured.setdefault("combat", combat)
        return [(C.END_TURN, 0.0)]

    original = OA.search
    OA.search = fake_search
    try:
        OA.rollout_choice(row, row.get("legal_actions") or [], DATA, 100)
    except Exception as exc:  # noqa: BLE001 - report, do not hide
        return {"error": type(exc).__name__, "path": path, "index": index}
    finally:
        OA.search = original
    state = captured.get("combat")
    if state is None:
        return {"error": "no_state", "path": path, "index": index}
    detail = [{"action": action, "value": value}
              for action, value in C.search(state, DATA, 100, row.get("seq") or 0)]
    hand = {(r.get("index")): r.get("id") for r in row.get("hand") or ()}
    return {
        "path": path,
        "index": index,
        "seq": row.get("seq"),
        "turn": row.get("turn"),
        "energy": (row.get("player") or {}).get("energy"),
        "hp": row.get("player_hp"),
        "enemies": [{"id": e.get("id"), "hp": e.get("hp"), "max": e.get("max_hp")}
                    for e in row.get("enemies") or ()],
        "hand": [c.get("id") for c in row.get("hand") or ()],
        "detail": [{"action": d["action"], "value": d["value"],
                    "card": hand.get(int(d["action"].split(":")[1].split("@")[0]))
                    if d["action"].startswith("card:") else None}
                   for d in detail],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args(argv)
    with open(args.tasks, encoding="utf-8") as f:
        tasks = [tuple(t) for t in json.load(f)]
    with mp.Pool(args.workers, initializer=_init, initargs=(args.root,)) as pool:
        results = pool.map(_run, tasks, chunksize=1)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    print(f"{len(results)} decisions -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
