#!/usr/bin/env python3
"""One command: the dev5 judgment table for a base run dir plus one candidate run dir per arm.

Takes `--base DIR` (the base panel) and `--cand LABEL=DIR` for each candidate (H3a, H3c, ...), each a
BossLab run dir (`lab_results.jsonl` plus per-trial `trial_NNNN_agent.jsonl` traces beside it), and
prints, per candidate, the four views the T36 request names: (a) the whole-turn firing count and the
turn numbers where a fired pair diverged, (b) the paired Queen-shave difference with its sign tally and
exact McNemar p, (c) total and Queen firepower per turn plus survival turns, base mean against candidate
mean, and (d) the accept-gate reading under the pre-registered rule (conditions 1-6 from commit 4693f2e
plus the firing prerequisite G). It reuses analyze_bosslab's metric helpers and apply_hybrid_rule's
`candidate_delta`, `sufficed`, `decide` and `format_report`, so the gate verdict matches the frozen rule
exactly rather than being re-derived here.

confirm5 is optional here. dev5 is the development panel: the confirm-side conditions (1, 3-6) are not
run yet, so the verdict comes out 保留（暫定）exactly as apply_hybrid_rule reports it, and only the dev
side (condition 2 robustness, the firing G clause, and the selection gate) is measured. Supply
`--confirm-base DIR` and `--confirm LABEL=DIR` to get the final verdict once confirm5 exists.

Partial panels must not crash: a candidate dir with no results, a trace missing for one pair, or a spec
present in one arm only, all downgrade to a counted gap (0 pairs / skipped / "未実行") instead of an
exception. Usage:
    python3 bosslab/tools/dev5_report.py \
        --base      data/bosslab_act3_dev5_swap_base \
        --cand H3a=data/bosslab_act3_dev5_swap_H3a \
        --cand H3c=data/bosslab_act3_dev5_swap_H3c
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # bosslab/tools: where the helpers live

import analyze_bosslab as A  # noqa: E402
import apply_hybrid_rule as H  # noqa: E402

BASE_LABEL = H.BASE_LABEL


def parse_cand(entries: list[str]) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for e in entries:
        label, sep, target = e.partition("=")
        if sep:
            out.append((label, Path(target)))
    return out


def load_panel(base_dir: Path, cands: list[tuple[str, Path]]) -> tuple[list, list[str]]:
    """Load base + candidate trials into one merged list tagged by arm, without ever raising."""
    merged: list = []
    try:
        base_trials, _ = A.load_trials([base_dir / "lab_results.jsonl"])
    except OSError:
        base_trials = []
    for r in base_trials:
        r["_arm"] = BASE_LABEL
    merged += base_trials
    labels: list[str] = []
    for label, target in cands:
        try:
            usable, _ = H.load_relabel(label, target)
        except OSError:
            usable = []
        merged += usable
        labels.append(label)
    return merged, labels


def _fmt_pct(x: float) -> str:
    return f"{x:.0%}" if x == x else "nan"


def firing_section(firing: dict, cands: list[str]) -> list[str]:
    """(a) whole-turn firing count with the diverging turn numbers, per candidate."""
    L = ["", "## (a) 前提 G: 全ターンの殴り先発火（base trace との配対）",
         f"引用: {H.FIRING}",
         f"閾値 firing_C ≥ {H.G_THRESHOLD}（dev のみ。確認用は --confirm-base で追加）"]
    for x in cands:
        d = firing.get(x)
        if not d:
            L.append(f"- {x}: 発火 照合データ無し")
            continue
        L.append(f"- {x}: 発火 {d['fired']}/{d['pairs']} 組"
                 + (f"（trace 欠落で照合できず {d['skipped_missing_trace']} 組）"
                    if d.get("skipped_missing_trace") else ""))
        for spec, off, turns in d["fired_detail"]:
            L.append(f"    - {spec}|{off}: 発火ターン {turns}")
    return L


def paired_section(label: str, cand_trials: list, merged: list) -> list[str]:
    """(b)(c) per-pair Queen shave, and the per-arm means for shave / firepower / survival turns."""
    L = [f"", f"## {label}: 配対指標（base 対 {label}）"]
    if not cand_trials:
        L.append("- 実行データ無し（この run dir に reliable な結果行がありません）")
        return L
    pc = A.paired_continuous(merged, BASE_LABEL, label)
    rows = {row["metric"]: row for row in pc["rows"]}
    if pc["pairs"] == 0:
        L.append("- 配対 0 組（同じ spec・offset の entry が base 側にも candidate 側にも揃って居ない）")
    shave = rows.get("queen_shaved")
    if shave:
        L += ["", "### (b) Queen削り割合の対応あり差",
              f"- 配対 {shave['pairs']} 組: 候補優 {shave['better']} / base優 {shave['worse']} / "
              f"同値 {shave['tie']}、精密二側 p = {shave['p'] if shave['p'] is not None else 'nan'}",
              f"- base 平均削り {_fmt_pct(shave['base_mean'])} / {label} 平均削り {_fmt_pct(shave['other_mean'])}",
              "", "| spec | offset | base 削り | 候補 削り |", "| --- | --- | --- | --- |"]
        for spec, off, b, o in pc["details"]:
            L.append(f"| {spec} | {off} | {_fmt_pct(b)} | {_fmt_pct(o)} |")
    L += ["", "### (c) 総火力/ターン と 生存ターン（arm 平均）"]
    for metric, name in (("firepower_total", "総火力/ターン"),
                         ("firepower_queen", "Queen火力/ターン"),
                         ("turns", "生存ターン（長いほど良い）")):
        r = rows.get(metric)
        if not r:
            continue
        delta = (r["other_mean"] - r["base_mean"]) if r["other_mean"] == r["other_mean"] else float("nan")
        L.append(f"- {name}: base {r['base_mean']:.1f} / 候補 {r['other_mean']:.1f} "
                 f"(Δ {delta:+.1f}、候補優 {r['better']} / base優 {r['worse']} / 同値 {r['tie']})")
    return L


def gate_section(label: str, dev: dict, firing: dict, cand_trials: list) -> list[str]:
    """(d) the per-candidate accept-gate reading (the dev-side booleans the rule keys on)."""
    L = [f"", f"## {label}: (d) ゲート判定（4693f2e の規則、dev 側のみ）"]
    if not cand_trials:
        L.append("- 実行データ無し（この run dir に reliable な結果行がありません）")
        return L
    d = dev.get(label)
    if not d:
        L.append("- 実行データ無し")
        return L
    firing_d = firing.get(label) or {}
    fired = firing_d.get("fired", 0)
    L += [f"- Δshave = {d['Δshave']:+d}（候補優 {d['better']} / base優 {d['worse']} / 同値 {d['tie']}、p = {d['p']}）",
          f"- Δfp = {('%+.1f HP/ターン' % d['Δfp']) if d['Δfp'] is not None else 'nan'}"
          f"（base {d['fp_base']:.1f} → 候補 {d['fp_cand']:.1f}）",
          f"- Δwin = {d['Δwin']:+d}（base_win {d['base_wins']} / 候補_win {d['cand_wins']}）",
          f"- firing_C = {fired}（閾値 {H.G_THRESHOLD} 以上 = 前提G充足）",
          f"- 充足条件 Δshave>0 かつ Δfp≥0 かつ Δwin≥0: **{'充足' if H.sufficed(d) else '不充足'}**",
          f"- 配対 {d['pairs']} 組 / 配対不能 {d['not_comparable']} 組（信頼性: 12 組全配対でなくとも dev 結果は出る）"]
    return L


def build_report(base_dir: Path, cands: list[tuple[str, Path]], *, confirm_base=None,
                 confirm_cands=None, threshold: int = H.G_THRESHOLD) -> str:
    merged, labels = load_panel(base_dir, cands)
    per_cand: dict[str, list] = {label: [r for r in merged if r["_arm"] == label] for label in labels}
    firing = {label: H.pair_attack_target_turns(base_dir, target)
              for label, target in cands if label in labels}
    dev = {label: H.candidate_delta(merged, BASE_LABEL, label) for label in labels}

    confirm = None
    if confirm_base:
        ct, _ = load_panel(Path(confirm_base), parse_cand(confirm_cands or []))
        confirm = {label: H.candidate_delta(ct, BASE_LABEL, label)
                   for label in labels if any(r["_arm"] == label for r in ct)}

    L = [f"# dev5 判定表（base: {base_dir}）",
         f"- 候補: {', '.join(labels) if labels else '指定無し'}",
         f"- base 試行 {sum(1 for r in merged if r['_arm']==BASE_LABEL)} / 候補試行 "
         + ", ".join(f"{x}:{len(per_cand[x])}" for x in labels)]
    for label in labels:
        L += firing_section(firing, [label])
        L += paired_section(label, per_cand[label], merged)
        L += gate_section(label, dev, firing, per_cand[label])
    if confirm is not None:
        fired_conf = {label: H.pair_attack_target_turns(Path(confirm_base), target)
                      for label, target in parse_cand(confirm_cands or []) if label in labels}
        firing_final = {"dev": firing, "confirm": fired_conf}
    else:
        firing_final = {"dev": firing, "confirm": None}
    res = H.decide(dev, confirm, labels, firing=firing_final, threshold=threshold)
    L += ["", H.format_report(res, labels)]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True, help="dev base panel run dir")
    ap.add_argument("--cand", dest="cands", action="append", default=[], metavar="LABEL=DIR",
                    help="candidate run dir, repeat (H3a=... H3c=...)")
    ap.add_argument("--confirm-base", default=None)
    ap.add_argument("--confirm", dest="confirm_cands", action="append", default=[], metavar="LABEL=DIR")
    ap.add_argument("--threshold", type=int, default=H.G_THRESHOLD)
    ap.add_argument("--out", default=None, help="write here as well as stdout")
    args = ap.parse_args()

    text = build_report(Path(args.base), parse_cand(args.cands),
                        confirm_base=args.confirm_base, confirm_cands=args.confirm_cands,
                        threshold=args.threshold)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
