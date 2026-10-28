#!/usr/bin/env python3
"""Mechanically apply the pre-registered Act3 hybrid accept/keep/reject rule.

Encodes bosslab/results/act3_hybrid_decision_rule.md rules 1-6 (and the dev2 candidate-selection rule)
verbatim and applies them to the recorded panels using analyze_bosslab's own metric helpers, so the
numbers match the comparison report exactly. The pure `decide()` carries every branch (accept 1-6,
reject, keep, provisional, and the selection branches including the H1-on-tie preference) so the real
machine result cannot change the logic that is unit-tested before it is seen. Each condition prints the
rule text it checks (quoted) and its result. The confirm (確認用) set is optional: when it is not
supplied the confirm-dependent conditions report "未実行" and the verdict is provisional, which lets the
script be validated on dev2 alone before confirm4 is looked at. Usage:
    python3 bosslab/tools/apply_hybrid_rule.py \
        --dev-base  data/bosslab_act3_dev3_base \
        --dev H1=data/bosslab_act3_dev3_H1 --dev H2=data/bosslab_act3_dev3_H2 \
        [--confirm-base data/bosslab_act3_confirm4_base --confirm H1=data/bosslab_act3_confirm4_H1]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # bosslab/tools: where analyze_bosslab lives
sys.path.insert(1, str(Path(__file__).resolve().parents[2]))  # repo root (unused here, harmless)

import analyze_bosslab as A  # noqa: E402

BASE_LABEL = "base"

# ---------------------------------------------------------------- verbatim rule text (do not edit)
# Excerpted from bosslab/results/act3_hybrid_decision_rule.md (commit 4693f2e). The rule wording is
# fixed; these strings are printed alongside each condition so the reader sees exactly which line was
# applied. They are the authority for the verdict; the code below only reproduces their logic.
SELECTION = "候補 C が「条件充足」であるための条件（すべて）: `Δshave_C > 0` かつ `Δfp_C ≥ 0` かつ `Δwin_C ≥ 0`。"
SELECT_BOTH = ("両候補が条件充足: `Δfp` の大きい方へ進める。差が 0.5 HP/ターン以内なら同帯として `Δshave` の"
               "大きい方、それでも同値なら H1（削り済み優先の従属則で、脅威型の H2 より挙動が限定的）を優先。")
SELECT_ONE = "片方だけ条件充足: その候補を confirm4 へ進める。"
SELECT_NONE = ("どちらも条件充足でない: hybrid を進めない（両候補を落とす）。confirm4 には base に対して dev2 で最も "
               "`Δshave > 0` を満たす候補を 1 つだけ進め、採否規則で 不採用 を確定する（充足候補が無い場合の"
               "記録用。hybrid 機構自体を却下するかは採否規則の「両候補同じ向き」条項で決める）。")
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


def load_relabel(label: str, lab_path: Path) -> tuple[list, list]:
    """Load one arm's trials and rewrite its arm tag to `label` (each run dir writes arm 'base')."""
    usable, dropped = A.load_trials([lab_path / "lab_results.jsonl"])
    for r in usable:
        r["_arm"] = label
    return usable, dropped


def candidate_delta(trials: list, base_label: str, cand_label: str) -> dict:
    """Δshave / Δfp / Δwin / sign-test p for one candidate against base, via analyze_bosslab."""
    pc = A.paired_continuous(trials, base_label, cand_label)
    rows = {row["metric"]: row for row in pc["rows"]}
    shave = rows["queen_shaved"]
    fp = rows["firepower_total"]
    cand_wins = sum(1 for r in trials if r["_arm"] == cand_label and r["result"]["won"])
    base_wins = sum(1 for r in trials if r["_arm"] == base_label and r["result"]["won"])
    fp_delta = None if (fp["other_mean"] != fp["other_mean"]) else fp["other_mean"] - fp["base_mean"]
    return {
        "Δshave": shave["better"] - shave["worse"],
        "better": shave["better"], "worse": shave["worse"], "tie": shave["tie"], "p": shave["p"],
        "Δfp": fp_delta, "fp_base": fp["base_mean"], "fp_cand": fp["other_mean"],
        "Δwin": cand_wins - base_wins, "cand_wins": cand_wins, "base_wins": base_wins,
        "pairs": pc["pairs"], "not_comparable": pc["not_comparable"],
    }


def sufficed(d: dict) -> bool:
    return bool(d["Δshave"] > 0 and d["Δfp"] is not None and d["Δfp"] >= 0 and d["Δwin"] >= 0)


def select_candidate(dev: dict, cands_dev: list) -> tuple:
    """Apply the dev2 candidate-selection rule. Returns (chosen or None, branch_text)."""
    passed = {c for c in cands_dev if sufficed(dev[c])}
    if len(cands_dev) >= 2 and passed == set(cands_dev):  # both sufficed
        # larger Δfp; within 0.5 HP/turn -> larger Δshave; still tied -> H1
        ranked = sorted(cands_dev, key=lambda c: (dev[c]["Δfp"], dev[c]["Δshave"], 1 if c == "H1" else 0),
                        reverse=True)
        a, b = ranked[0], ranked[1]
        if abs(dev[a]["Δfp"] - dev[b]["Δfp"]) <= 0.5:
            chosen = sorted(cands_dev, key=lambda c: (dev[c]["Δshave"], 1 if c == "H1" else 0), reverse=True)[0]
            return chosen, SELECT_BOTH
        return a, SELECT_BOTH
    if len(passed) == 1:
        return next(iter(passed)), SELECT_ONE
    if passed:  # some but not all sufficed (and not "both")
        best = sorted(passed, key=lambda c: (dev[c]["Δfp"], dev[c]["Δshave"]), reverse=True)[0]
        return best, SELECT_ONE
    # none sufficed: record-send the most Δshave>0 candidate; verdict via accept rule
    cands = [c for c in cands_dev if dev[c]["Δshave"] > 0]
    if not cands:
        return None, SELECT_NONE
    cands.sort(key=lambda c: (dev[c]["Δshave"], 1 if c == "H1" else 0), reverse=True)
    return cands[0], SELECT_NONE


def decide(dev: dict, confirm: dict | None, cands_dev: list) -> dict:
    """Pure branch logic: returns chosen candidate, selection branch, per-condition results and verdict.

    `confirm` may be None (確認用 not yet measured) -> conditions 1/3/4 (the confirm side) and 5/6 report
    None so the verdict is 保留（暫定）. A condition value is True/False when measurable, None when it
    depends on an unmeasured confirm set.
    """
    chosen, branch = select_candidate(dev, cands_dev)
    have_confirm = bool(confirm) and chosen is not None and chosen in confirm
    c = {}

    # 1: Δshave>0 in dev AND confirm
    c1_dev = chosen is not None and dev[chosen]["Δshave"] > 0
    c1_confirm = None if not have_confirm else confirm[chosen]["Δshave"] > 0
    c[1] = None if c1_confirm is None else (c1_dev and c1_confirm)

    # 2: both candidates same shave direction on dev2 (both Δshave>0)
    c[2] = bool(len(cands_dev) >= 2 and all(dev[x]["Δshave"] > 0 for x in cands_dev))

    # 3: Δfp>=0 both sets
    c3_dev = chosen is not None and dev[chosen]["Δfp"] is not None and dev[chosen]["Δfp"] >= 0
    c3_confirm = None if not have_confirm else (confirm[chosen]["Δfp"] is not None and confirm[chosen]["Δfp"] >= 0)
    c[3] = None if c3_confirm is None else (c3_dev and c3_confirm)

    # 4: Δwin>=0 both sets
    c4_dev = chosen is not None and dev[chosen]["Δwin"] >= 0
    c4_confirm = None if not have_confirm else confirm[chosen]["Δwin"] >= 0
    c[4] = None if c4_confirm is None else (c4_dev and c4_confirm)

    # 5: confirm4 shave sign-test p <= 0.05
    c[5] = None if not have_confirm else bool(confirm[chosen]["p"] is not None and confirm[chosen]["p"] <= 0.05)

    # 6: all 12 paired, no incomparable entry (信頼性の悪化なし)
    if have_confirm:
        cd = confirm[chosen]
        c[6] = bool(cd["pairs"] == 12 and cd["not_comparable"] == 0)
    else:
        c[6] = None

    accept = [c[1], c[2], c[3], c[4], c[5], c[6]]

    # verdict
    if any(x is None for x in accept):
        verdict = "保留（暫定）"
    elif all(accept):
        verdict = "採用"
    else:
        reject_all_shave = (chosen is not None and dev[chosen]["Δshave"] <= 0
                            and have_confirm and confirm[chosen]["Δshave"] <= 0)
        reject_both_primary = (chosen is not None and have_confirm
                               and confirm[chosen]["Δshave"] < 0
                               and confirm[chosen]["Δfp"] is not None and confirm[chosen]["Δfp"] < 0)
        reject_impl = (have_confirm and (not c[6] or confirm[chosen]["not_comparable"] > 0))
        if reject_all_shave:
            verdict = "不採用"
            reason = "C* が dev2・confirm4 両集合で Δshave ≤ 0"
        elif reject_both_primary:
            verdict = "不採用"
            reason = "削り悪化かつ総火力/ターン base 下回る（主信号両方劣化）"
        elif reject_impl:
            verdict = "不採用"
            reason = "前提・実装の誤り（配対不能 / lab 例外 / 一致取れず）"
        else:
            verdict = "保留"
            reason = "採用条件のどれかを満たさない中間（火力/wins/両集合の向き/p/頑健性）"
        return {"chosen": chosen, "branch": branch, "cond": c, "dev": dev, "confirm": confirm,
                "verdict": verdict, "reason": reason,
                "c1_dev": c1_dev, "c3_dev": c3_dev, "c4_dev": c4_dev}
    return {"chosen": chosen, "branch": branch, "cond": c, "dev": dev, "confirm": confirm,
            "verdict": verdict, "reason": "採用条件 1〜6 すべて充足",
            "c1_dev": c1_dev, "c3_dev": c3_dev, "c4_dev": c4_dev}


def _fmt_delta(d: dict) -> str:
    fp = "NaN" if d["Δfp"] is None else f"{d['Δfp']:+.3f}"
    p = "NaN" if d["p"] is None else f"{d['p']:.4f}"
    return (f"Δshave={d['Δshave']:+d} (候補優{d['better']}/base優{d['worse']}/同値{d['tie']}, p={p}) "
            f"Δfp={fp} (base {d['fp_base']:.3f}→{d['fp_cand']:.3f}) "
            f"Δwin={d['Δwin']:+d} (base勝{d['base_wins']}→{d['cand_wins']})")


def _status(ok) -> str:
    return "未実行（確認用待ち）" if ok is None else ("充足" if ok else "不充足")


def format_report(res: dict, cands_dev: list) -> str:
    """Human-readable rule-application report from a decide() result."""
    dev, confirm, chosen, c = res["dev"], res["confirm"], res["chosen"], res["cond"]
    L = ["# 候補選定規則（dev2 = 開発用）", f"引用: {SELECTION}"]
    for x in cands_dev:
        L.append(f"- {x}: {_fmt_delta(dev[x])} → 条件充足={'Yes' if sufficed(dev[x]) else 'No'}")
    L.append(f"選定: {res['branch']}")
    L.append(f"→ 進める候補 C* = {chosen}")
    L.append("")
    L.append("# 採否規則（confirm4 = 確認用。dev2 のみ実行時は確認用条件は 未実行）")
    for n in (1, 2, 3, 4, 5, 6):
        detail = ""
        if n in (1, 3, 4) and chosen:
            sub = {1: (res["c1_dev"], dev[chosen]["Δshave"]),
                   3: (res["c3_dev"], dev[chosen]["Δfp"]),
                   4: (res["c4_dev"], dev[chosen]["Δwin"])}[n]
            conf = None if not (confirm and chosen in confirm) else c[n] and True or (c[n] if (confirm and chosen in confirm) else None)
            detail = f"  → dev2 {'充足' if sub[0] else '不充足'}; confirm4 {_status(None if not confirm or chosen not in confirm else confirm_ok(n, confirm, chosen))}; 総合 {_status(c[n])}"
        elif n == 2:
            detail = "  → dev2 両候補 Δshave: " + ", ".join(f"{x}={dev[x]['Δshave']:+d}" for x in cands_dev) + f"; {_status(c[2])}"
        else:
            detail = f"  → confirm4 {_status(c[n])}"
        L.append(f"条件{n}: {CONDITIONS[n]}")
        L.append(detail)
    L.append("")
    if res["verdict"].startswith("保留（暫定"):
        L.append("判定: 保留（暫定）。確認用（confirm4）の条件1・3〜6が未実行のため最終判定は保留。")
        L.append(f"  dev2 側: C*={chosen}; 条件2(頑健性)={_status(c[2])}")
        if chosen and not sufficed(dev[chosen]):
            L.append("  dev2 で C* は火力/wins ゲートを通っていない → 記録用送付。最終は確認用で確定。")
        L.append(f"引用(保留): {KEEP}")
    elif res["verdict"] == "採用":
        L.append("判定: 採用（最終戦の進捗改善として採用、踏破率・到達点の向上は未確認）。")
        L.append(f"引用(採用): {CONDITIONS[1]} ほか 1〜6 すべて充足")
    elif res["verdict"] == "不採用":
        L.append(f"判定: 不採用（{res['reason']}）。")
        L.append(f"引用(不採用): {REJECT}")
    else:
        L.append(f"判定: 保留（{res['reason']}）。")
        L.append(f"引用(保留): {KEEP}")
    return "\n".join(L)


def confirm_ok(n: int, confirm: dict, chosen: str):
    """The confirm-side boolean of a two-set condition, for display."""
    if chosen not in confirm:
        return None
    d = confirm[chosen]
    if n == 1:
        return d["Δshave"] > 0
    if n == 3:
        return d["Δfp"] is not None and d["Δfp"] >= 0
    if n == 4:
        return d["Δwin"] >= 0
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply the pre-registered hybrid accept/keep/reject rule.")
    ap.add_argument("--dev-base", required=True, help="dev (開発用) base panel dir")
    ap.add_argument("--dev", action="append", default=[], metavar="LABEL=DIR")
    ap.add_argument("--confirm-base", default=None)
    ap.add_argument("--confirm", action="append", default=[], metavar="LABEL=DIR")
    args = ap.parse_args()

    def parse_pairs(entries):
        out = []
        for e in entries:
            label, sep, target = e.partition("=")
            if sep:
                out.append((label, Path(target)))
        return out

    dev_trials = list(A.load_trials([Path(args.dev_base) / "lab_results.jsonl"])[0])
    for r in dev_trials:
        r["_arm"] = BASE_LABEL
    cands_dev = []
    for label, target in parse_pairs(args.dev):
        usable, _ = load_relabel(label, target)
        dev_trials += usable
        cands_dev.append(label)
    dev = {x: candidate_delta(dev_trials, BASE_LABEL, x) for x in cands_dev}

    confirm = None
    if args.confirm_base:
        confirm_trials = list(A.load_trials([Path(args.confirm_base) / "lab_results.jsonl"])[0])
        for r in confirm_trials:
            r["_arm"] = BASE_LABEL
        for label, target in parse_pairs(args.confirm):
            usable, _ = load_relabel(label, target)
            confirm_trials += usable
        confirm = {}
        for x in cands_dev:
            if any(r["_arm"] == x for r in confirm_trials):
                confirm[x] = candidate_delta(confirm_trials, BASE_LABEL, x)

    res = decide(dev, confirm, cands_dev)
    print(format_report(res, cands_dev))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
