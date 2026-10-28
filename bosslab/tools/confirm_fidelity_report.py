#!/usr/bin/env python3
"""Aggregate a BossLab fidelity check into the confirm-report format leader asked for.

Wraps bosslab_fidelity.py's per-trial comparison into: (1) how many trials fully match the spec entry
("lab vs spec: 一致"), (2) a per-field divergence tally across the panel, and (3) a dedicated section
for trials carrying a named relic flag (default RELIC.ROYAL_POISON) showing the player.hp the lab
produced versus the spec and the original run — this is where the HP clamp fix (commit 927f26f) is judged:
if the lab hp now equals the spec/recorded hp, the entry-HP drift is fixed. Run against the confirm4 base
panel once it is 12/12:
    python3 bosslab/tools/confirm_fidelity_report.py \
        --out-dir data/bosslab_act3_confirm4_base \
        --plan .dsh/bosslab_act3_plan_confirm4.json --specs .dsh/act3_boss_specs.jsonl \
        --flag RELIC.ROYAL_POISON --out bosslab/results/act3_confirm4_fidelity.md
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import bosslab_fidelity as F  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate a fidelity run into the confirm-report format.")
    ap.add_argument("--out-dir", dest="out_dir", required=True, help="dir with trial_*_agent.jsonl (the panel run)")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--specs", required=True)
    ap.add_argument("--traces-dir", dest="traces_dir", default=str(F.MAIN_TREE / "data"))
    ap.add_argument("--flag", default="RELIC.ROYAL_POISON", help="relic id whose carrying trials get an HP-drift report")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    specs = F.spec_map(Path(args.specs))
    traces_dir = Path(args.traces_dir)
    trials = {t["trial_index"]: t for t in plan["trials"]}

    full_match = 0
    total = 0
    field_tally: collections.Counter = collections.Counter()
    flag_rows: list[str] = []
    flag_total = 0
    flag_fixed = 0
    lines = ["# BossLab 忠実性集計レポート", "",
             f"入出力 dir: {args.out_dir}  plan: {args.plan}  specs: {args.specs}", "",
             "lab の戦闘開始観測(player hp/敵 hp・max_hp/deck/piles/powers/relics/potions/敵 move)を "
             "spec の entry と突き合わせ、完全一致組数と不一致項目の内訳を出す。flag レリック所持組は "
             "HP 即時 clamp 修正(927f26f)の成否を lab hp / spec hp / 元trace hp で判定する。", ""]

    for trace in sorted(Path(args.out_dir).glob("trial_*_agent.jsonl")):
        idx = int(trace.name.split("_")[1])
        trial = trials.get(idx)
        if not trial:
            continue
        spec = specs.get(trial["spec_id"])
        if not spec:
            continue
        total += 1
        lab = F.first_combat_obs(F.rows_of(trace))
        if lab is None:
            lines.append(f"- trial {idx:04d}: 戦闘観測なし")
            continue
        spec_obs = F.spec_as_obs(spec)
        lab_vs_spec = F.compare(lab, spec_obs)
        if not lab_vs_spec:
            full_match += 1
        for field, _la, _sb in lab_vs_spec:
            field_tally[field] += 1
        lines.append(f"- trial {idx:04d} (spec {spec['spec_id'][:12]}): "
                     + ("一致" if not lab_vs_spec else
                        f"{len(lab_vs_spec)} 項目不一致 " +
                        ", ".join(f"`{f}` lab={F._fmt(la)}/spec={F._fmt(sb)}" for f, la, sb in lab_vs_spec)))
        # flag-relic section (HP drift / 927f26f check)
        spec_relics = [str(r) for r in (spec["player"].get("relics") or [])]
        if args.flag in spec_relics:
            flag_total += 1
            lab_hp = (lab.get("player") or {}).get("hp")
            spec_hp = spec_obs["player"]["hp"]
            orig = F.orig_boss_obs(spec, traces_dir)
            orig_hp = (orig.get("player") or {}).get("hp") if orig else None
            fixed = (lab_hp == spec_hp)
            if fixed:
                flag_fixed += 1
            flag_rows.append(f"- trial {idx:04d} (spec {spec['spec_id'][:12]}, {args.flag} 所持): "
                             f"lab hp={lab_hp} / spec(=記録) hp={spec_hp} / 元trace hp={orig_hp} → "
                             + ("HP 一致(修正 927f26f で記録値に着地)" if fixed else "HP ずれ(未修正)"))

    out = ["## 集計", "",
           f"- 比較 trial 数: {total}",
           f"- spec entry と完全一致(lab vs spec 一致): {full_match} / {total}",
           "- 不一致項目の内訳(項目→該当 trial 数):",
           ] + [f"  - `{field}`: {n}" for field, n in field_tally.most_common()] + [
           "",
           f"## {args.flag} 所持組の HP 漂移(927f26f の成否)", "",
           f"該当 {flag_total} 組のうち lab hp が spec(記録) hp に一致: {flag_fixed} 組"] + (flag_rows or ["- 該当なし"])

    text = "\n".join(out) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
