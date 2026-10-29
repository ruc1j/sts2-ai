#!/usr/bin/env python3
"""Model how many first decisions an H3a / H3c arming rule would flip, from a recorded base panel.

No game run: reads an existing base BossLab panel (the recorded queenfirst agent's per-trial
observation at the first decision) and asks, for each entry, whether the hypothetical H3 rule's
condition holds there and the base did not already do the same thing. That pair count is the
``firing_C`` the accept-rule prerequisite (act3_h3_decision_rule_proposal.md condition G) measures,
so it is the empirical basis for whether the 4/12 threshold is reasonable.

Model (deliberately simple, per the task):
  * first decision = the first observation line (seq 0) of each trial; it is turn 1.
  * the Amalgam (MONSTER.TORCH_HEAD_AMALGAM) is attackable this turn if any legal card action
    targets it (target_id is a 1-based index into obs.enemies; single-target = that index, an AoE
    card with target_id null is NOT counted as "focused on the Amalgam").
  * H3a (QUEENFIRST_H3_OPEN_TURNS=2): arms to focus the Amalgam during the first 2 turns, so at the
    turn-1 first decision its condition holds whenever the Amalgam is alive and attackable. It flips
    the first decision exactly when base did not already single-target the Amalgam.
  * H3c (QUEENFIRST_H3_DANGER_FRAC=0.5): arms on danger, modelled as expected incoming damage at the
    first decision > 0.5 x player surviving HP (incoming = sum of every enemy Attack intent's
    damage x repeats, ignoring block - the recorded opening hand rarely has block worth netting out,
    and this is a coarse arming-rate estimate, not the exact rule). It flips the first decision when
    that holds, the Amalgam is attackable, and base was not already Amalgam-focused.

Usage:
  python3 bosslab/tools/h3_firstdecision_diff_model.py PANEL_DIR [PANEL_DIR ...]
"""
from __future__ import annotations

import glob
import json
import os
import sys

AMALGAM = "MONSTER.TORCH_HEAD_AMALGAM"


def load_first_obs(path: str) -> dict | None:
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("phase") == "combat":
                return record
    return None


def analyse_trial(path: str) -> dict:
    obs = load_first_obs(path)
    if obs is None:
        return {"error": "no obs"}
    enemies = obs.get("enemies") or []
    amalgam_idx = next((i for i, e in enumerate(enemies)
                        if isinstance(e, dict) and e.get("id") == AMALGAM and (e.get("hp") or 0) > 0),
                       None)
    player_hp = obs.get("player_hp") or 0
    incoming = 0
    for e in enemies:
        if not isinstance(e, dict):
            continue
        for intent in (e.get("intents") or ()):
            if isinstance(intent, dict) and intent.get("type") == "Attack":
                incoming += (intent.get("damage") or intent.get("raw_damage") or 0) * (intent.get("repeats") or 1)

    legal_to_amalgam = amalgam_idx is not None and any(
        a.get("target_id") == amalgam_idx + 1 for a in (obs.get("legal_actions") or ())
        if isinstance(a, dict) and a.get("type") == "card")

    chosen = obs.get("target_id")
    base_targets_amalgam = amalgam_idx is not None and chosen == amalgam_idx + 1

    h3a_flip = bool(legal_to_amalgam and not base_targets_amalgam)
    h3c_flip = bool(legal_to_amalgam and not base_targets_amalgam and player_hp > 0
                    and incoming > 0.5 * player_hp)
    return {
        "amalgam_alive": amalgam_idx is not None,
        "attackable": legal_to_amalgam,
        "base_focuses_amalgam": base_targets_amalgam,
        "incoming": incoming,
        "player_hp": player_hp,
        "h3a_flip": h3a_flip,
        "h3c_flip": h3c_flip,
    }


def main(argv: list[str]) -> int:
    dirs = argv[1:] or ["data/bosslab_act3_dev2", "data/bosslab_act3_confirm4_base"]
    grand_a = grand_c = 0
    for panel in dirs:
        trials = sorted(glob.glob(os.path.join(panel, "trial_*_agent.jsonl")))
        rows = [analyse_trial(t) for t in trials]
        ok = [r for r in rows if "error" not in r]
        n = len(ok)
        alive = sum(1 for r in ok if r["amalgam_alive"])
        base_focus = sum(1 for r in ok if r["base_focuses_amalgam"])
        fa = sum(1 for r in ok if r["h3a_flip"])
        fc = sum(1 for r in ok if r["h3c_flip"])
        grand_a += fa
        grand_c += fc
        print(f"{panel}: trials {len(trials)} (readable {n})  amalgam-alive {alive}  "
              f"base-already-Amalgam-first {base_focus}")
        print(f"    H3a first-decision flips (turn<=2 & attackable & base-not-focused): {fa}/{n}")
        print(f"    H3c first-decision flips (danger incoming>0.5*hp & attackable):    {fc}/{n}")
        for r in ok:
            print(f"      hp={r['player_hp']:>3} incoming={r['incoming']:>3} "
                  f"attackable={str(r['attackable']):5} base-focus={str(r['base_focuses_amalgam']):5} "
                  f"h3a={int(r['h3a_flip'])} h3c={int(r['h3c_flip'])}")
    print(f"TOTAL across {len(dirs)} base sets: H3a flips {grand_a}, H3c flips {grand_c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
