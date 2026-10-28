#!/usr/bin/env python3
"""Mechanically apply the pre-registered Act3 hybrid accept/keep/reject rule.

Encodes bosslab/results/act3_hybrid_decision_rule.md rules 1-6 (and the dev2 candidate-selection rule)
verbatim and applies them to the recorded panels using analyze_bosslab's own metric helpers, so the
numbers match the comparison report exactly. Each condition prints the rule text it checks (quoted) and
its result. The confirm (確認用) set is optional: when it is not supplied the confirm-dependent
conditions report "未実行" and the verdict is provisional, which lets the script be validated on dev2
alone before the confirm4 real-machine run is looked at. Usage:
    python3 bosslab/tools/apply_hybrid_rule.py \
        --dev-base  data/bosslab_act3_dev3_base \
        --dev H1=data/bosslab_act3_dev3_H1 --dev H2=data/bosslab_act3_dev3_H2 \
        [--confirm-base data/bosslab_act3_confirm4_base --confirm H1=data/bosslab_act3_confirm4_H1]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import analyze_bosslab as A  # noqa: E402


# ---------------------------------------------------------------- verbatim rule text (do not edit)
# Excerpted from bosslab/results/act3_hybrid_decision_rule.md (commit 4693f2e). The rule wording is
# fixed; these strings are printed alongside each condition so the reader sees exactly which line was
# applied. They are the authority for the verdict; the code below only reproduces their logic.
SELECTION = "候補 C が「条件充足」であるための条件（すべて）: `Δshave_C > 0` かつ `Δfp_C ≥ 0` かつ `Δwin_C ≥ 0`。"
SELECT_BOTH = "両候補が条件充足: `Δfp` の大きい方へ進める。差が 0.5 HP/ターン以内なら同帯として `Δshave` の大きい方、それでも同値なら H1 を優先。"
SELECT_ONE = "片方だけ条件充足: その候補を confirm4 へ進める。"
SELECT_NONE = ("どちらも条件充足でない: hybrid を進めない（両候補を落とす）。confirm4 には base に対して dev2 で最も "
               "`Δshave > 0` を満たす候補を 1 つだけ進め、採否規則で 不採用 を確定する（充足候補が無い場合の記録用。"
               "hybrid 機構自体を却下するかは採否規則の「両候補同じ向き」条項で決める）。")
CONDITIONS = {
    1: "**採用**（すべてを満たす）: 1. C* が confirm4 の主信号 削り割合で `Δshave > 0`（候補優 > base 優）、かつ dev2 でも `Δshave > 0`（両集合で同じ向き＝機構が頑健。EVALUATION.md §採用）。",
    2: "2. 両候補 H1/H2 の **削り割合の向きが dev2 で同じ**（ともに `Δshave > 0`）。H1 が良く H2 が悪い等の割れは機構頑健でなく採用しない。",
    3: "3. confirm4 と dev2 の両方で `Δfp ≥ 0`（総火力/ターンが base を下回らない）。",
    4: "4. confirm4 と dev2 の両方で `Δwin ≥ 0`（勝ちが base を下回らない）。",
    5: "5. confirm4 の削り割合の配対符号検定で精密二側 p ≤ 0.05。",
    6: "6. 未解消の信頼性の悪化が無い（配対不能 entry が無い＝12 組すべて配対、lab 例外や通信障害が無い）。",
}
REJECT = ("**不採用**（いずれか）: C* が削り割合で dev2・confirm4 の両集合で `Δshave ≤ 0`（悪化または同値）；"
          "削りが悪化して、かつ 総火力/ターン も base を下回った；前提・実装の誤りが実測で判明"
          "（HP 修正後も fidelity の一致が取れない、lab 例外、配対不能）。→ base の継続。")
KEEP = ("**保留**: 削り割合は確認用で改善したが火力/wins/両集合の向き/p≤0.05/頑健性のどれかを満たさない；"
        "H1 と H2 の向きが dev2 で割れた；配対不足・欠測・同値で主信号がどちらにも傾かない。")


def load_relabel(label: str, lab_path: Path) -> list[dict]:
    """Load one arm's trials and rewrite its arm tag to `label` (each run dir writes arm 'base')."""
    usable, dropped = A.load_trials([lab_path / "lab_results.jsonl"])
    for r in usable:
        r["_arm"] = label
    return usable, dropped


def candidate_delta(trials: list[dict], base_label: str, cand_label: str) -> dict:
    """Δshave / Δfp / Δwin / confirm4-style sign-test p for one candidate against base, via analyze_bosslab."""
    pc = A.paired_continuous(trials, base_label, cand_label)
    rows = {row["metric"]: row for row in pc["rows"]}
    shave = rows["queen_shaved"]
    fp = rows["firepower_total"]
    cand_wins = sum(1 for r in trials if r["_arm"] == cand_label and r["result"]["won"])
    base_wins = sum(1 for r in trials if r["_arm"] == base_label and r["result"]["won"])
    return {
        "Δshave": shave["better"] - shave["worse"],
        "better": shave["better"], "worse": shave["worse"], "tie": shave["tie"],
        "p": shave["p"],
        "Δfp": (fp["other_mean"] - fp["base_mean"]) if not (fp["other_mean"] != fp["other_mean"]) else None,
        "fp_base": fp["base_mean"], "fp_cand": fp["other_mean"],
        "Δwin": cand_wins - base_wins,
        "cand_wins": cand_wins, "base_wins": base_wins,
        "pairs": pc["pairs"], "not_comparable": pc["not_comparable"],
    }


def sufficed(d: dict) -> bool:
    return d["Δshave"] > 0 and (d["Δfp"] is not None and d["Δfp"] >= 0) and d["Δwin"] >= 0


def select_candidate(dev: dict[str, dict]) -> tuple[str | None, str]:
    """Apply the dev2 candidate-selection rule and return (chosen candidate or None, which branch)."""
    passed = {c: d for c, d in dev.items() if sufficed(d)}
    if len(passed) == len(dev) and len(dev) >= 2:
        # both sufficed: larger Δfp, tie (within 0.5) -> larger Δshave, then H1
        best = sorted(dev.items(), key=lambda kv: (kv[1]["Δfp"], kv[1]["Δshave"],
                                                   0 if kv[0] == "H1" else 1), reverse=True)
        a, b = best[0], best[1]
        if abs(a[1]["Δfp"] - b[1]["Δfp"]) <= 0.5 and (a[1]["Δshave"] != b[1]["Δshave"] or a[0] != "H1"):
            chosen = sorted(dev.items(), key=lambda kv: (kv[1]["Δshave"], 0 if kv[0] == "H1" else 1), reverse=True)
            return chosen[0][0], SELECT_BOTH
        return a[0], SELECT_BOTH
    if len(passed) == 1:
        return next(iter(passed)), SELECT_ONE
    if len(passed) >= 1:  # some sufficed but < all and >1 candidates
        best = sorted(passed.items(), key=lambda kv: (kv[1]["Δfp"], kv[1]["Δshave"]), reverse=True)
        return best[0][0], SELECT_ONE
    # none sufficed: send most Δshave>0 to confirm4 as record only (verdict decided by accept rule)
    cands = [(c, d) for c, d in dev.items() if d["Δshave"] > 0]
    if not cands:
        return None, SELECT_NONE
    cands.sort(key=lambda kv: (kv[1]["Δshave"], 0 if kv[0] == "H1" else 1), reverse=True)
    return cands[0][0], SELECT_NONE


def fmt_status(ok) -> str:
    if ok is None:
        return "未実行（確認用待ち）"
    return "充足" if ok else "不充足"


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply the pre-registered hybrid accept/keep/reject rule.")
    ap.add_argument("--dev-base", required=True, help="dev (開発用) base panel dir")
    ap.add_argument("--dev", action="append", default=[], metavar="LABEL=DIR",
                    help="dev candidate panel as LABEL=DIR (repeat for H1 and H2)")
    ap.add_argument("--confirm-base", default=None, help="確認用 base panel dir (optional until confirm4 lands)")
    ap.add_argument("--confirm", action="append", default=[], metavar="LABEL=DIR",
                    help="確認用 candidate panel as LABEL=DIR")
    args = ap.parse_args()

    def parse_pairs(entries):
        out = []
        for e in entries:
            label, sep, target = e.partition("=")
            if sep:
                out.append((label, Path(target)))
        return out

    # dev set
    dev_trials = list(A.load_trials([Path(args.dev_base) / "lab_results.jsonl"])[0])
    for r in dev_trials:
        r["_arm"] = "base"
    dev_labels = ["base"]
    for label, target in parse_pairs(args.dev):
        usable, _ = load_relabel(label, target)
        dev_trials += usable
        dev_labels.append(label)
    cands_dev = [lbl for lbl in dev_labels if lbl != "base"]
    dev = {c: candidate_delta(dev_trials, "base", c) for c in cands_dev}

    confirm = None
    confirm_trials: list[dict] = []
    if args.confirm_base:
        confirm_trials = list(A.load_trials([Path(args.confirm_base) / "lab_results.jsonl"])[0])
        for r in confirm_trials:
            r["_arm"] = "base"
        for label, target in parse_pairs(args.confirm):
            usable, _ = load_relabel(label, target)
            confirm_trials += usable
        confirm = {}
        for c in cands_dev:
            if any(r["_arm"] == c for r in confirm_trials):
                confirm[c] = candidate_delta(confirm_trials, "base", c)

    # ---- print dev2 selection (候補選定規則)
    print("# 候補選定規則（dev2 = 開発用）")
    print(f"引用: {SELECTION}")
    for c in cands_dev:
        d = dev[c]
        print(f"- {c}: Δshave={d['Δshave']:+d} (候補優{d['better']}/base優{d['worse']}/同値{d['tie']}, "
              f"p={d['p']:.4f}) Δfp={d['Δfp'] if d['Δfp'] is not None else float('nan'):+.3f} "
              f"(base {d['fp_base']:.3f}→{d['fp_cand']:.3f}) Δwin={d['Δwin']:+d} "
              f"(base勝{d['base_wins']}→{c}勝{d['cand_wins']}) → 条件充足={'Yes' if sufficed(d) else 'No'}")
    chosen, branch = select_candidate(dev)
    print(f"選定: {branch}")
    print(f"→ 進める候補 C* = {chosen}")
    print()

    # ---- 採否規則 1-6
    print("# 採否規則（confirm4 = 確認用。dev2 のみで実行時は確認用条件は 未実行）")
    cstar = chosen
    accept = []
    # cond 1: Δshave>0 in both dev and confirm
    c1_dev = cstar is not None and dev[cstar]["Δshave"] > 0
    c1_confirm = None if not confirm or cstar not in confirm else confirm[cstar]["Δshave"] > 0
    c1 = None if c1_confirm is None else (c1_dev and c1_confirm)
    accept.append(c1)
    print(f"条件1: {CONDITIONS[1]}")
    print(f"  → dev2 Δshave={'+' if c1_dev else ''}{dev[cstar]['Δshave'] if cstar else 'n/a'} "
          f"{'充足' if c1_dev else '不充足'}; confirm4 {fmt_status(c1_confirm)}; 総合 {fmt_status(c1)}")
    # cond 2: both candidates same shave direction on dev2 (both Δshave>0)
    c2 = all(dev[c]["Δshave"] > 0 for c in cands_dev) and len(cands_dev) >= 2
    accept.append(c2)
    print(f"条件2: {CONDITIONS[2]}")
    print(f"  → dev2 両候補 Δshave: " + ", ".join(f"{c}={dev[c]['Δshave']:+d}" for c in cands_dev)
          + f"; {fmt_status(c2)}")
    # cond 3: Δfp>=0 both sets
    c3_dev = cstar is not None and dev[cstar]["Δfp"] is not None and dev[cstar]["Δfp"] >= 0
    c3_confirm = None if not confirm or cstar not in confirm else (
        confirm[cstar]["Δfp"] is not None and confirm[cstar]["Δfp"] >= 0)
    c3 = None if c3_confirm is None else (c3_dev and c3_confirm)
    accept.append(c3)
    print(f"条件3: {CONDITIONS[3]}")
    print(f"  → dev2 Δfp={dev[cstar]['Δfp'] if cstar and dev[cstar]['Δfp'] is not None else 'n/a'} "
          f"{'充足' if c3_dev else '不充足'}; confirm4 {fmt_status(c3_confirm)}; 総合 {fmt_status(c3)}")
    # cond 4: Δwin>=0 both sets
    c4_dev = cstar is not None and dev[cstar]["Δwin"] >= 0
    c4_confirm = None if not confirm or cstar not in confirm else confirm[cstar]["Δwin"] >= 0
    c4 = None if c4_confirm is None else (c4_dev and c4_confirm)
    accept.append(c4)
    print(f"条件4: {CONDITIONS[4]}")
    print(f"  → dev2 Δwin={dev[cstar]['Δwin'] if cstar else 'n/a'} {'充足' if c4_dev else '不充足'}; "
          f"confirm4 {fmt_status(c4_confirm)}; 総合 {fmt_status(c4)}")
    # cond 5: confirm4 mcnemar p<=0.05
    c5 = None if not confirm or cstar not in confirm else (confirm[cstar]["p"] is not None and confirm[cstar]["p"] <= 0.05)
    accept.append(c5)
    print(f"条件5: {CONDITIONS[5]}")
    print(f"  → confirm4 {fmt_status(c5)}")
    # cond 6: all 12 paired, no incomparable, no exceptions (base & candidate both have 12 usable, 0 not_comparable)
    if cstar and confirm and cstar in confirm:
        cd = confirm[cstar]
        c6 = cd["pairs"] == 12 and cd["not_comparable"] == 0
    else:
        c6 = None
    accept.append(c6)
    print(f"条件6: {CONDITIONS[6]}")
    print(f"  → confirm4 {fmt_status(c6)}")
    print()

    # ---- verdict
    if any(x is None for x in accept):
        # provisional: confirm4 conditions not yet evaluated
        prov_dev = cstar is not None
        print("判定: 保留（暫定）。確認用（confirm4）の条件1・3〜6が未実行のため最終判定は保留。")
        print(f"  dev2 側: C*={cstar}; 条件2(頑健性)={fmt_status(c2)}; hybrid 選定={branch}")
        if cstar and not sufficed(dev[cstar]):
            print("  dev2 で C* は火力/wins ゲートを通っていない → 記録用送付。最終は確認用で確定。")
        print(f"引用(保留): {KEEP}")
        return 0
    if all(accept):
        print("判定: 採用（最終戦の進捗改善として採用、踏破率・到達点の向上は未確認）。")
        print(f"引用(採用): {CONDITIONS[1]} ほか 1〜6 すべて充足")
        return 0
    # reject branches
    if cstar and dev[cstar]["Δshave"] <= 0 and confirm.get(cstar, {}).get("Δshave", 0) <= 0:
        print("判定: 不採用（C* が dev2・confirm4 両集合で Δshave ≤ 0）。")
        print(f"引用(不採用): {REJECT}")
    elif cstar and (confirm[cstar]["Δshave"] < 0) and (confirm[cstar]["Δfp"] is not None and confirm[cstar]["Δfp"] < 0):
        print("判定: 不採用（削り悪化かつ総火力/ターン base 下回る、主信号両方劣化）。")
        print(f"引用(不採用): {REJECT}")
    elif (not c6) or (cstar and confirm[cstar]["not_comparable"] > 0):
        print("判定: 不採用（前提・実装の誤り: 配対不能/一致取れず/lab例外）。")
        print(f"引用(不採用): {REJECT}")
    else:
        print("判定: 保留（採用条件のどれかを満たさない中間。次に必要な証拠を act3_hybrid_decision_rule.md に従い特定）。")
        print(f"引用(保留): {KEEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
