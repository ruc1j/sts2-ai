#!/usr/bin/env python3
"""PILOT-5: counterfactual entry states with HEAL replaced by SMITH.

For each run of astra_ctrl_v23+v24 whose trace has rest decisions, the HEALs
that an arm would replace are converted into upgrades of the deck that entered
the Act 3 boss, and the entry HP is reduced by the healing those rests gave.
The card to upgrade mirrors RestBridge.SmithCardSelector (the agent picks the
card; the game only offers the pile).

    python3 bosslab/tools/pilot5_build_entries.py --out-dir /tmp/p5

Writes one entries file per arm (R50 / R50B / R35 / base) ready for
pilot4_sim.py --arm main.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

MAIN = "/Users/mao/workspace/sts2-ai"

STRONG_BLOCK = {
    "CARD.IMPERVIOUS": 100, "CARD.SHRUG_IT_OFF": 95, "CARD.FLAME_BARRIER": 95,
    "CARD.BLOOD_WALL": 90, "CARD.STONE_ARMOR": 90, "CARD.EQUILIBRIUM": 90,
    "CARD.ULTIMATE_DEFEND": 90, "CARD.TAUNT": 85,
}


def smith_score(card_id, deck_ids, near_boss, queen_boss):
    """Mirror of RestBridge.SmithCardSelector.Score."""
    if queen_boss and "CARD.RUPTURE" in deck_ids and card_id == "CARD.RUPTURE":
        return 1200
    if near_boss and card_id in STRONG_BLOCK:
        return 1000 + STRONG_BLOCK[card_id]
    if "CARD.PERFECTED_STRIKE" in deck_ids and card_id in ("CARD.PERFECTED_STRIKE", "CARD.HELLRAISER"):
        return 700
    if "CARD.RUPTURE" in deck_ids and card_id in (
            "CARD.RUPTURE", "CARD.TEAR_ASUNDER", "CARD.HEMOKINESIS", "CARD.BLOODLETTING"):
        return 680
    if "CARD.CORRUPTION" in deck_ids and card_id in (
            "CARD.CORRUPTION", "CARD.FEEL_NO_PAIN", "CARD.DARK_EMBRACE"):
        return 660
    if card_id in ("CARD.INFLAME", "CARD.PRIMAL_FORCE", "CARD.DOMINATE"):
        return 640
    return {
        "CARD.BATTLE_TRANCE": 600, "CARD.POMMEL_STRIKE": 600, "CARD.BASH": 550,
        "CARD.IRON_WAVE": 520 if near_boss else 500,
        "CARD.SECOND_WIND": 520 if near_boss else 500,
        "CARD.TRUE_GRIT": 520 if near_boss else 500,
        "CARD.STRIKE_IRONCLAD": 100,
    }.get(card_id, 300)


def read_rows(path):
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def rest_events(rows, entry_index):
    """Rest decisions with the HP/max HP in force and a near-boss flag.

    The trace does not record the run floor, so `floor` is approximated by the
    number of combats between the rest and the boss entry: two or fewer counts
    as near boss (the last 2-3 rest sites).
    """
    events = []
    last_max = None
    for i, row in enumerate(rows):
        if row.get("phase") == "combat":
            max_hp = (row.get("player") or {}).get("max_hp")
            if max_hp:
                last_max = max_hp
        if row.get("phase") != "rest":
            continue
        combats_after = sum(1 for r in rows[i:entry_index] if r.get("phase") == "combat")
        events.append({
            "row_index": i,
            "hp": row.get("hp"),
            "max_hp": last_max,
            "option": row.get("option_id"),
            "combats_to_boss": combats_after,
            "near_boss": combats_after <= 2,
        })
    return events


def boss_entry(rows, kind):
    for i, row in enumerate(rows):
        if row.get("phase") != "combat":
            continue
        ids = {str(e.get("id", "")) for e in row.get("enemies") or ()}
        if kind == "QUEEN" and any(x.endswith(".QUEEN") for x in ids):
            return i, row
        if kind == "INSATIABLE" and any("INSATIABLE" in x for x in ids):
            return i, row
    return None, None


def build_entry_obs(entry, upgrades):
    """Upgrade `upgrades` cards in the entry observation (highest Smith score first)."""
    obs = json.loads(json.dumps(entry))
    piles = [obs.get(k) for k in ("draw_pile", "hand", "discard_pile", "exhaust_pile")]
    cards = [c for pile in piles if pile for c in pile]
    deck_ids = {c.get("id") for c in cards}
    near_boss = True   # Act 3 boss entry
    queen_boss = True
    changed = 0
    for _ in range(upgrades):
        candidates = [c for c in cards if not c.get("upgrade")]
        if not candidates:
            break
        best = max(candidates, key=lambda c: smith_score(c.get("id"), deck_ids, near_boss, queen_boss))
        best["upgrade"] = 1
        changed += 1
    return obs, changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=os.path.join(MAIN, "data"))
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--heal-fraction", type=float, default=0.30)
    ap.add_argument("--entries", default="/tmp/pilot3_entries.json",
                    help="restrict to the PILOT-4 entry set (same 89 fights)")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)

    keep = None
    if args.entries and os.path.exists(args.entries):
        with open(args.entries, encoding="utf-8") as f:
            keep = {(e["seed"], e["kind"]) for e in json.load(f)}
    runs = {}
    wanted = keep if keep is not None else None
    for tag in ("astra_ctrl_v23", "astra_ctrl_v24"):
        for path in sorted(glob.glob(os.path.join(args.data_dir, f"{tag}_*_agent.jsonl"))):
            rows = read_rows(path)
            name = os.path.basename(path)
            kinds = [k for k in ("QUEEN", "INSATIABLE")
                     if wanted is None or (name, k) in wanted]
            for kind in kinds:
                index, entry = boss_entry(rows, kind)
                if entry is None:
                    continue
                runs[name + "|" + kind] = {
                "rows": rows, "entry": entry, "entry_index": index,
                "rests": rest_events(rows, index),
            }

    arms = {
        "base": lambda hp_frac, event: False,
        "R50": lambda hp_frac, event: hp_frac >= 0.50,
        "R50B": lambda hp_frac, event: hp_frac >= 0.50 and not event["near_boss"],
        "R35": lambda hp_frac, event: hp_frac >= 0.35,
    }
    summary = {}
    for arm, pred in arms.items():
        entries, rows_out = [], []
        for name, data in runs.items():
            entry = data["entry"]
            replaced = 0
            lost_hp = 0
            min_hp = None
            for event in data["rests"]:
                hp, max_hp = event["hp"], event["max_hp"]
                if not hp or not max_hp:
                    continue
                if str(event["option"]) != "HEAL":
                    continue
                if not pred(hp / max_hp, event):
                    continue
                replaced += 1
                lost_hp += min(int(max_hp * args.heal_fraction), max_hp - hp)
            player = entry.get("player") or {}
            hp = player.get("hp") or 0
            max_hp = player.get("max_hp") or 1
            new_hp = max(int(max_hp * 0.10), hp - lost_hp)
            obs, upgraded = build_entry_obs(entry, replaced)
            obs["player"]["hp"] = new_hp
            kind = "QUEEN" if any(str(e.get("id", "")).endswith(".QUEEN")
                                  for e in entry.get("enemies") or ()) else "INSATIABLE"
            # Walk the rests in order and check the HP the run would have had at the
            # next combat: cumulative healing removed vs the HP the trace recorded.
            lost = 0
            maybe_dead = False
            for event in data["rests"]:
                hp_e, max_e = event["hp"], event["max_hp"]
                if not hp_e or not max_e or str(event["option"]) != "HEAL":
                    continue
                if not pred(hp_e / max_e, event):
                    continue
                lost += min(int(max_e * args.heal_fraction), max_e - hp_e)
                nxt = next((r.get("player_hp") for r in data["rows"][event["row_index"]:]
                            if r.get("phase") == "combat" and r.get("player_hp") is not None),
                           None)
                if nxt is not None and nxt - lost <= 0:
                    maybe_dead = True
            low = None
            entries.append({"kind": kind, "seed": name, "obs": obs})
            rows_out.append({"seed": name, "replaced": replaced, "lost_hp": lost_hp,
                             "hp": hp, "new_hp": new_hp, "upgraded": upgraded,
                             "min_hp_before_entry": low,
                             "maybe_dead": maybe_dead})
        path = os.path.join(args.out_dir, f"{arm}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f)
        summary[arm] = rows_out
        replaced_total = sum(r["replaced"] for r in rows_out)
        runs_with = sum(1 for r in rows_out if r["replaced"])
        maybe_dead = sum(1 for r in rows_out if r["maybe_dead"])
        print(f"{arm}: entries {len(entries)}, replaced HEAL total {replaced_total}, "
              f"runs with replacements {runs_with}, maybe-dead {maybe_dead} -> {path}")
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
