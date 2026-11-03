#!/usr/bin/env python3
"""PILOT-4: upper-bound levers inside combat.py's model.

Each fight starts from a recorded boss entry state (the same 89 entries as
PILOT-3) and is played to the end with search() every decision.  Arms either
rewrite the entry state (D*) or change how the fight is played (P*).

    python3 bosslab/tools/pilot4_sim.py run --root <checkout> --arm D1 \
        --entries /tmp/pilot3_entries.json --out /tmp/D1.json

Arms:
  main  unmodified
  D1    +1 max energy and +1 energy (every turn, since step() refills to max)
  D2    every card upgraded
  D3    player at full HP
  D4    remove half of the Strikes and Defends from the deck
  D5    add Rupture, Crimson Mantle, Inflame to the draw pile
  D6    D1 + D2
  P2    search with 1000 simulations (restricted entry set)
  P1    turn planning: beam over card sequences, score end-of-turn states
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import multiprocessing as mp
import os
import random
import sys

MAIN = "/Users/mao/workspace/sts2-ai"
ENEMY_FILES = ("enemies_overgrowth.json", "enemies_hive.json", "enemies_glory.json")
DATA = None
ROOT = None
ARM = "main"


def _load_data(root):
    monsters = []
    for name in ENEMY_FILES:
        with open(os.path.join(root, "data", name), encoding="utf-8-sig") as f:
            monsters.extend(json.load(f)["monsters"])
    return {"monsters": monsters}


def _init(root, arm):
    global ROOT, DATA, ARM
    ROOT = root
    ARM = arm
    sys.path.insert(0, root)
    DATA = _load_data(root)


def _modify(state, arm):
    import combat as C
    replace = dataclasses.replace
    if arm in ("D1", "D6"):
        state = replace(state, max_energy=state.max_energy + 1, energy=state.energy + 1)
    if arm in ("D2", "D6"):
        up = lambda card: replace(card, upgraded=True)
        state = replace(state, hand=tuple(up(c) for c in state.hand),
                        draw_pile=tuple(up(c) for c in state.draw_pile),
                        discard_pile=tuple(up(c) for c in state.discard_pile),
                        exhaust_pile=tuple(up(c) for c in state.exhaust_pile))
    if arm == "D3":
        state = replace(state, player_hp=state.player_max_hp)
    if arm == "D4":
        # Keep half of each basic (Strike/Defend) across every pile, drawing the cut evenly.
        basics = {"Strike", "Defend"}
        piles = {"hand": list(state.hand), "draw": list(state.draw_pile),
                 "discard": list(state.discard_pile)}
        totals = {name: sum(1 for pile in piles.values() for c in pile
                            if getattr(c, "name", "") == name) for name in basics}
        keep = {name: totals[name] - totals[name] // 2 for name in basics}
        seen = {name: 0 for name in basics}
        thinned = {}
        for key, pile in piles.items():
            out = []
            for card in pile:
                name = getattr(card, "name", "")
                if name in basics:
                    seen[name] += 1
                    if seen[name] > keep[name]:
                        continue
                out.append(card)
            thinned[key] = tuple(out)
        state = replace(state, hand=thinned["hand"], draw_pile=thinned["draw"],
                        discard_pile=thinned["discard"])
    if arm == "D5":
        extra = (C.Card(C.RUPTURE), C.Card(C.CRIMSON_MANTLE), C.Card(C.INFLAME))
        state = replace(state, draw_pile=tuple(state.draw_pile) + extra)
    return state


def _value(state, data, rounds=8, seed=0):
    """v1-style value of a state: mean over greedy rollouts of the loss-progress score."""
    import combat as C
    scores = []
    for sim in range(rounds):
        rng = random.Random(seed * 1_000_003 + sim)
        s = state
        for _ in range(60):
            if s.terminal or s.player_hp <= 0:
                break
            s = C.step(s, C._greedy_action(s, data), data, rng)
        won = s.player_hp > 0 and not any(e.alive and e.primary for e in s.enemies)
        if won:
            scores.append(1.0 + max(0, s.player_hp) / 100)
            continue
        progress = 0.0
        weight = 0.0
        for enemy in state.enemies:
            values = {}
            for monster in data["monsters"]:
                if monster["id"] == enemy.model:
                    values = monster.get("values") or {}
                    break
            max_hp = values.get("MaxInitialHp") or values.get("MinInitialHp") or 0
            if not max_hp:
                continue
            final = next((e.hp for e in s.enemies if e.model == enemy.model and e.slot == enemy.slot), 0)
            share = 1.0 - max(0, min(final, max_hp)) / max_hp
            factor = 1.0 if enemy.primary else 0.5
            progress += factor * share
            weight += factor
        scores.append(-1 + 0.9 * (progress / weight if weight else 0.0))
    return sum(scores) / len(scores)


def _plan_first(state, data, seed, beam_width=3, depth=3):
    """Beam search over this turn's card order; return the first card of the best line."""
    import combat as C
    beam = [(state, [])]
    for _ in range(depth):
        cands = []
        for st, seq in beam:
            actions = [a for a in C.legal_actions(st) if a != C.END_TURN]
            if not actions:
                cands.append((st, seq))
                continue
            for action in actions:
                try:
                    nxt = C.step(st, action, data, random.Random(seed))
                except Exception:  # noqa: BLE001 - model gaps, skip the branch
                    continue
                cands.append((nxt, seq + [action]))
        if not cands:
            break
        scored = [(_value(st, data, 6, seed), st, seq) for st, seq in cands]
        scored.sort(key=lambda item: -item[0])
        beam = [(st, seq) for _, st, seq in scored[:beam_width]]
    best = max(beam, key=lambda item: _value(item[0], data, 6, seed))
    return best[1][0] if best[1] else C.END_TURN


def play(obs, rng, arm):
    import official_agent as OA
    import combat as C
    captured = {}

    def fake_search(combat, data, simulations=0, seed=0):
        captured.setdefault("combat", combat)
        return [(C.END_TURN, 0.0)]

    original = OA.search
    OA.search = fake_search
    try:
        OA.rollout_choice(obs, obs.get("legal_actions") or [], DATA, 100)
    finally:
        OA.search = original
    state = captured.get("combat")
    if state is None:
        return None
    state = _modify(state, arm)
    specs = {m["id"]: m for m in DATA["monsters"]}
    entry_hp = {e.model: e.hp for e in state.enemies}
    decisions = 0
    times = []
    import time as _time
    while decisions < 200:
        if state.player_hp <= 0:
            break
        primaries = [e for e in state.enemies if e.primary]
        if primaries and all(not e.alive for e in primaries):
            break
        if state.terminal:
            break
        start = _time.time()
        if arm == "P1":
            action = _plan_first(state, DATA, decisions)
        elif arm == "P2":
            action = C.search(state, DATA, 1000, decisions)[0][0]
        else:
            action = C.search(state, DATA, 100, decisions)[0][0]
        times.append(_time.time() - start)
        state = C.step(state, action, DATA, rng)
        decisions += 1
    final = {e.model: max(0, e.hp) for e in state.enemies}
    won = bool([e for e in state.enemies if e.primary]) and all(
        not e.alive for e in state.enemies if e.primary) and state.player_hp > 0
    result = {"won": won, "turns": state.turn, "decisions": decisions,
              "player_hp": state.player_hp,
              "sec_per_decision": (sum(times) / len(times)) if times else None}
    for model, hp in entry_hp.items():
        if model.endswith(".QUEEN") or "INSATIABLE" in model:
            values = (specs.get(model) or {}).get("values") or {}
            max_hp = values.get("MaxInitialHp") or values.get("MinInitialHp") or hp
            key = "queen_shave" if model.endswith(".QUEEN") else "enemy_shave"
            result[key] = max(0.0, min(1.0, 1.0 - final.get(model, 0) / max_hp))
    return result


def _run(task):
    try:
        return play(task["obs"], random.Random(task["offset"]), task["arm"])
    except Exception as exc:  # noqa: BLE001
        return {"error": type(exc).__name__}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--root", default=MAIN)
    run.add_argument("--arm", required=True)
    run.add_argument("--entries", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--offsets", type=int, default=1)
    run.add_argument("--kinds", default="QUEEN,INSATIABLE")
    run.add_argument("--limit", type=int, default=0)
    run.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)

    with open(args.entries, encoding="utf-8") as f:
        entries = json.load(f)
    kinds = set(args.kinds.split(","))
    entries = [e for e in entries if e["kind"] in kinds]
    if args.limit:
        entries = entries[: args.limit]
    tasks = [{"obs": e["obs"], "offset": off, "arm": args.arm, "kind": e["kind"], "seed": e["seed"]}
             for e in entries for off in range(args.offsets)]
    with mp.Pool(args.workers, initializer=_init, initargs=(args.root, args.arm)) as pool:
        results = pool.map(_run, tasks, chunksize=1)
    for task, result in zip(tasks, results):
        if result:
            result.update(kind=task["kind"], seed=task["seed"], offset=task["offset"])
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    errors = sum(1 for r in results if r and "error" in r)
    print(f"arm {args.arm}: {len(results)} fights, {errors} errors -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
