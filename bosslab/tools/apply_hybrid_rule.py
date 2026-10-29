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
import collections
import json
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
SELECT_NOFIRE = ("前提 G により、dev2 で発火基準（base との全ターンの殴り先差分）を満たす候補が無い: 全候補が base と"
                 "同一動作＝測定不能。採否を出さず保留にする（発火しない候補の Δshave は機構を検定しない）。")
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

# ---------------------------------------------------------------- firing prerequisite (added, T34)
# The confirm4 run showed candidates that never diverged from base on the target choice were judged on
# Δshave even though the mechanism never engaged (act3_h3_firing_model.md). Condition G measures firing
# as the number of paired (spec, offset) entries where the candidate chose a DIFFERENT attack target
# (殴り先) than base across the whole fight - not only the first decision - so a threat-based arm that
# arms mid-fight is counted too. A candidate below the threshold is treated as 測定不能 (保留), never
# 不採用, because comparing a silent candidate to base is not evidence about the mechanism.
G_THRESHOLD = 4
FIRING = ("**前提 G（発火率、判定の前に検査）**: 候補 C について、同じ spec・offset の base trace と突き合わせ、"
          "全ターンのうち base と別の単独攻撃の殴り先（敵 slot）を選んだ組数 `firing_C` を数える。dev2 と確認用の"
          f"両集合で `firing_C ≥ {G_THRESHOLD}` を満たさない候補は充足候補から外す。候補が 0 件しかない、または"
          "G を満たす候補が無い panel は**測定不能 = 保留**（不採用ではない）。候補規則が作動せず base と同一動作で、"
          "主指標の効果を検定できないため。")


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


# ---------------------------------------------------------------- firing (target-choice divergence)
# firing_C = how many paired (spec, offset) entries chose a different single-target attack destination
# than base across the whole fight. Read straight from the recorded per-trial agent traces (each line =
# one observation plus the action the agent took on it); no new game run is needed. Only single-target
# attacks count as an "attack target" (AoE plays have target_id null and hit everyone, so they do not
# express a 殴り先 choice). The compare is against the base trace on the SAME entry (spec + rng offset),
# exactly the pairing analyze_bosslab uses for Δshave.
def _trace_rows(path: Path):
    with open(path, encoding="utf-8-sig", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _attack_slots(trace_path: Path) -> collections.Counter:
    """Multiset of enemy slots this run focused single-target Attacks on, over the whole fight."""
    slots = collections.Counter()
    for obs in _trace_rows(trace_path):
        if obs.get("type") != "card" or obs.get("target_id") is None:
            continue
        hi = obs.get("hand_index")
        hand = obs.get("hand") or ()
        if hi is None or hi >= len(hand) or (hand[hi] or {}).get("type") != "Attack":
            continue
        tid = obs["target_id"]
        slot = None
        for enemy in (obs.get("enemies") or ()):
            if isinstance(enemy, dict) and enemy.get("combat_id") == tid:
                slot = enemy.get("slot")
                break
        if slot is None:  # fall back to a 1-based index into enemies if combat_id did not match
            enemies = obs.get("enemies") or ()
            if isinstance(tid, int) and 1 <= tid <= len(enemies):
                slot = enemies[tid - 1].get("slot")
        if slot is not None:
            slots[slot] += 1
    return slots


def _trial_index_map(lab_path: Path) -> dict:
    """(spec_id, offset) -> trial_index, from a run dir's lab_results.jsonl (BossLab writes trial_id as
    "<spec>|<arm>|<offset>")."""
    lab_path = Path(lab_path)
    if not lab_path.is_file():  # a run dir that never started has no results file
        return {}
    usable, _dropped = A.load_trials([lab_path])
    out = {}
    for r in usable:
        out[(r["spec_id"], r.get("_offset"))] = r.get("trial_index")
    return out


def pair_attack_target_diff(base_dir: Path, cand_dir: Path) -> dict:
    """Compare base and candidate attack targets per paired entry; report the firing count."""
    base_map = _trial_index_map(Path(base_dir) / "lab_results.jsonl")
    cand_map = _trial_index_map(Path(cand_dir) / "lab_results.jsonl")
    shared = sorted(set(base_map) & set(cand_map))
    fired, detail, skipped = 0, [], 0
    for key in shared:
        bt = Path(base_dir) / f"trial_{base_map[key]:04d}_agent.jsonl"
        ct = Path(cand_dir) / f"trial_{cand_map[key]:04d}_agent.jsonl"
        if not (bt.is_file() and ct.is_file()):
            skipped += 1
            continue
        bs, cs = _attack_slots(bt), _attack_slots(ct)
        if bs != cs:
            fired += 1
            detail.append((key[0], key[1], dict(bs), dict(cs)))
    return {"pairs": len(shared), "fired": fired, "skipped_missing_trace": skipped, "fired_detail": detail}


def _attack_slots_by_turn(trace_path: Path) -> dict[int, collections.Counter]:
    """Per-turn multiset of enemy slots this run focused single-target Attacks on.

    Same selection rule as `_attack_slots` (single-target Attack card plays only, AoE has target_id
    null), but kept split by the trace's ``turn`` field so a caller can report WHICH turns diverged,
    not only that the whole fight did. A threat-based arm that arms mid-fight shows up only on its
    later turns, so grouping by turn is how firing is located to specific rounds.
    """
    by_turn: dict[int, collections.Counter] = {}
    for obs in _trace_rows(trace_path):
        if obs.get("type") != "card" or obs.get("target_id") is None:
            continue
        hi = obs.get("hand_index")
        hand = obs.get("hand") or ()
        if hi is None or hi >= len(hand) or (hand[hi] or {}).get("type") != "Attack":
            continue
        tid = obs["target_id"]
        slot = None
        for enemy in (obs.get("enemies") or ()):
            if isinstance(enemy, dict) and enemy.get("combat_id") == tid:
                slot = enemy.get("slot")
                break
        if slot is None:  # fall back to a 1-based index into enemies if combat_id did not match
            enemies = obs.get("enemies") or ()
            if isinstance(tid, int) and 1 <= tid <= len(enemies):
                slot = enemies[tid - 1].get("slot")
        if slot is None:
            continue
        by_turn.setdefault(int(obs.get("turn") or 0), collections.Counter())[slot] += 1
    return by_turn


def pair_attack_target_turns(base_dir: Path, cand_dir: Path) -> dict:
    """Whole-fight firing count plus, for each fired pair, the turn numbers where targets diverged.

    A pair counts as fired if any turn's single-target attack-slot multiset differs from base. The
    returned fired/pairs match `pair_attack_target_diff` exactly (same shared keys, same skip rule), so
    this is the same measure with the diverging rounds located; `fired_detail` carries ``(spec, offset,
    [turns])`` instead of the raw slot counters.
    """
    base_map = _trial_index_map(Path(base_dir) / "lab_results.jsonl")
    cand_map = _trial_index_map(Path(cand_dir) / "lab_results.jsonl")
    shared = sorted(set(base_map) & set(cand_map))
    fired, detail, skipped = 0, [], 0
    for key in shared:
        bt = Path(base_dir) / f"trial_{base_map[key]:04d}_agent.jsonl"
        ct = Path(cand_dir) / f"trial_{cand_map[key]:04d}_agent.jsonl"
        if not (bt.is_file() and ct.is_file()):
            skipped += 1
            continue
        bturn = _attack_slots_by_turn(bt)
        cturn = _attack_slots_by_turn(ct)
        turns = sorted(t for t in set(bturn) | set(cturn) if bturn.get(t) != cturn.get(t))
        if turns:
            fired += 1
            detail.append((key[0], key[1], turns))
    return {"pairs": len(shared), "fired": fired, "skipped_missing_trace": skipped, "fired_detail": detail}


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


def decide(dev: dict, confirm: dict | None, cands_dev: list, *, firing: dict | None = None,
           threshold: int = G_THRESHOLD) -> dict:
    """Pure branch logic: returns chosen candidate, selection branch, per-condition results and verdict.

    `confirm` may be None (確認用 not yet measured) -> conditions 1/3/4 (the confirm side) and 5/6 report
    None so the verdict is 保留（暫定）. A condition value is True/False when measurable, None when it
    depends on an unmeasured confirm set.

    `firing` (optional, added T34) adds prerequisite condition G. It is
    `{"dev": {label: pair_attack_target_diff(...)}, "confirm": {label: ...} | None}`. A candidate only
    competes for selection when its dev-side whole-fight attack-target divergence reaches `threshold`, and
    the verdict additionally requires confirm-side divergence once measured. A candidate below threshold is
    保留 (測定不能), never 不採用 (a silent candidate is not evidence about the mechanism). With `firing=None`
    the rule behaves exactly as the frozen 4693f2e 1-6 version.
    """
    firing_dev = (firing or {}).get("dev") or {}
    firing_confirm = (firing or {}).get("confirm")
    use_g = bool(firing)
    sel_cands = cands_dev
    if use_g:
        sel_cands = [x for x in cands_dev if firing_dev.get(x, {}).get("fired", 0) >= threshold]
    chosen, branch = select_candidate(dev, sel_cands)
    have_confirm = bool(confirm) and chosen is not None and chosen in confirm
    c = {}

    if use_g and not sel_cands:
        # No candidate reached the dev-side firing threshold: every candidate behaved like base, so the
        # mechanism is not exercised at all. This is a definitive 保留 (測定不能), not provisional, and not
        # 不採用 - Δshave against a silent candidate tells us nothing about the rule.
        return {"chosen": None, "branch": SELECT_NOFIRE, "cond": {"G": False, 1: None, 2: None, 3: None,
                        4: None, 5: None, 6: None}, "dev": dev,
                "confirm": confirm, "verdict": "保留",
                "reason": "dev2 で発火基準を満たす候補が無く測定不能（全候補が base と同一動作）",
                "firing": firing, "threshold": threshold,
                "c1_dev": False, "c3_dev": False, "c4_dev": False}

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

    # G (firing prerequisite): dev-side and confirm-side whole-fight attack-target divergence.
    if use_g:
        g_dev = chosen is not None and firing_dev.get(chosen, {}).get("fired", 0) >= threshold
        if firing_confirm is not None:
            g_confirm = chosen is not None and firing_confirm.get(chosen, {}).get("fired", 0) >= threshold
        else:
            g_confirm = None
        c["G"] = None if g_confirm is None else (g_dev and g_confirm)
        accept = [c["G"], c[1], c[2], c[3], c[4], c[5], c[6]]
    else:
        accept = [c[1], c[2], c[3], c[4], c[5], c[6]]

    # verdict
    if any(x is None for x in accept):
        verdict = "保留（暫定）"
    elif all(accept):
        verdict = "採用"
    else:
        if use_g and c.get("G") is False:
            verdict = "保留"
            reason = ("dev2 で発火基準（全ターンの殴り先差分）を満たす候補が無く測定不能"
                      if chosen is None else
                      "選択候補が発火基準（全ターンの殴り先差分）に満たず測定不能（base と同一動作）")
            return {"chosen": chosen, "branch": branch, "cond": c, "dev": dev, "confirm": confirm,
                    "verdict": verdict, "reason": reason, "firing": firing, "threshold": threshold,
                    "c1_dev": c1_dev, "c3_dev": c3_dev, "c4_dev": c4_dev}
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
                "verdict": verdict, "reason": reason, "firing": firing, "threshold": threshold,
                "c1_dev": c1_dev, "c3_dev": c3_dev, "c4_dev": c4_dev}
    return {"chosen": chosen, "branch": branch, "cond": c, "dev": dev, "confirm": confirm,
            "verdict": verdict,
            "reason": "採用条件 1〜6 すべて充足" + ("（前提 G の発火率も両集合で充足）" if use_g else ""),
            "firing": firing, "threshold": threshold,
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
    firing = res.get("firing")
    if firing:
        thr = res.get("threshold", G_THRESHOLD)
        L.append("")
        L.append("# 前提 G（発火率、判定の前に検査。実装: apply_hybrid_rule.firing）")
        L.append(f"引用: {FIRING}")
        L.append("測り方: 同じ spec・offset の base trace との配対で、全ターンの単独攻撃の殴り先（敵 slot）"
                 f"が base と異なる組数。閾値 firing_C ≥ {thr}（dev2・確認用両集合）。")
        for x in cands_dev:
            dv = (firing.get("dev") or {}).get(x)
            cf = firing.get("confirm")
            ds = f"{dv['fired']}/{dv['pairs']}" if dv else "?"
            if cf is None:
                cs = "未実行（確認用待ち）"
            elif x in cf:
                cs = f"{cf[x]['fired']}/{cf[x]['pairs']}"
            else:
                cs = "?"
            extra = ""
            if dv and dv.get("skipped_missing_trace"):
                extra = f"（trace 欠落で照合できず {dv['skipped_missing_trace']} 組）"
            L.append(f"- {x}: dev2 発火 {ds}、確認用 発火 {cs}{extra}")
        L.append(f"前提 G 総合: {_status(c.get('G'))}（選定は dev2 の発火 ≥{thr} の候補のみ対象）")
    L.append("")
    if res["verdict"].startswith("保留（暫定"):
        L.append("判定: 保留（暫定）。確認用（confirm4）の条件1・3〜6が未実行のため最終判定は保留。")
        L.append(f"  dev2 側: C*={chosen}; 条件2(頑健性)={_status(c[2])}")
        if firing:
            L.append(f"  前提 G(発火率): {_status(c.get('G'))}（確認用の発火照合待ち）")
        if chosen and not sufficed(dev[chosen]):
            L.append("  dev2 で C* は火力/wins ゲートを通っていない → 記録用送付。最終は確認用で確定。")
        L.append(f"引用(保留): {KEEP}")
    elif res["verdict"] == "採用":
        gtxt = "（前提 G の発火率も両集合で充足）" if firing else ""
        L.append(f"判定: 採用（最終戦の進捗改善として採用、踏破率・到達点の向上は未確認）。{gtxt}")
        L.append(f"引用(採用): {CONDITIONS[1]} ほか 1〜6 すべて充足" + ("、前提 G" if firing else ""))
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


def firing_from_dirs(args, cands_dev: list, *, have_confirm: bool) -> dict:
    """Build the G-clause firing input from the LABEL=DIR panel dirs on the command line."""
    def pairs(entries):
        out = []
        for e in entries:
            label, sep, target = e.partition("=")
            if sep:
                out.append((label, Path(target)))
        return out

    dev = {}
    for label, d in pairs(args.dev):
        if label in cands_dev:
            dev[label] = pair_attack_target_diff(Path(args.dev_base), d)
    confirm = None
    if have_confirm:
        confirm = {}
        for label, d in pairs(args.confirm):
            if label in cands_dev:
                confirm[label] = pair_attack_target_diff(Path(args.confirm_base), d)
    return {"dev": dev, "confirm": confirm}


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

    res = decide(dev, confirm, cands_dev,
                 firing=firing_from_dirs(args, cands_dev, have_confirm=bool(args.confirm_base)))
    print(format_report(res, cands_dev))
    return 0


# ---------------------------------------------------------------- separate entry: judge one candidate on confirm5 (T39)
# decide() above selects a single candidate from dev then confirms it (the H1/H2 flow). This entry judges
# each H3a/H3c candidate independently against the same frozen 4693f2e conditions 1-6 plus prerequisite G,
# given its dev5 delta, its confirm5 delta (None until the confirm5 run finishes), and the firing inputs for
# both panels. The rule text is unchanged; only the branch order is per-candidate. confirm5 deltas that are
# None make conditions 1/3/4/5/6 report "未実行" and the verdict 保留 (provisional), exactly like decide().

def _fire_pair(fire: dict | None, threshold: int) -> bool | None:
    """Whether prerequisite G is met on one panel; None when that panel has no firing input yet."""
    if not fire or fire.get("pairs", 0) == 0:
        return None
    return bool(fire.get("fired", 0) >= threshold)


def _sign(d: dict | None) -> int:
    if d is None:
        return 0
    return 0 if d["Δshave"] == 0 else (1 if d["Δshave"] > 0 else -1)


def judge_candidate(dev: dict, confirm: dict | None, fire_dev: dict | None,
                    fire_confirm: dict | None, *, threshold: int = G_THRESHOLD) -> dict:
    """Verdict for one candidate (採用/保留/不採用) reproducing 4693f2e conditions 1,3,4,5,6 + prerequisite G."""
    gd = _fire_pair(fire_dev, threshold)
    gc = _fire_pair(fire_confirm, threshold)
    g_pass = (gd is True and gc is True)
    g_status = "未実行" if (gd is None or gc is None) else ("充足" if g_pass else "不充足")

    pending = confirm is None  # 確認用 panel not measured yet
    cond: dict = {"G": (None if g_status == "未実行" else g_pass)}
    if pending:
        for k in (1, 3, 4, 5, 6):
            cond[k] = None
    else:
        cond[1] = bool(dev["Δshave"] > 0 and confirm["Δshave"] > 0)
        cond[3] = bool(dev["Δfp"] is not None and confirm["Δfp"] is not None
                       and dev["Δfp"] >= 0 and confirm["Δfp"] >= 0)
        cond[4] = bool(dev["Δwin"] >= 0 and confirm["Δwin"] >= 0)
        cond[5] = bool(confirm["p"] is not None and confirm["p"] <= 0.05)
        cond[6] = bool(dev["not_comparable"] == 0 and confirm["not_comparable"] == 0
                       and dev["pairs"] > 0 and dev["pairs"] == confirm["pairs"])
        direction_match = (_sign(dev) == _sign(confirm)) and _sign(confirm) != 0

    # verdict precedence: prerequisite G -> 不採用 (REJECT) -> 採用 (conditions 1,3,4,5,6) -> 保留 (KEEP).
    if pending:
        verdict, reason = "保留", "確認用（confirm5）の実行待ち。dev5 の結果のみで暫定。"
    elif g_status == "不充足":
        verdict, reason = "保留", "前提 G（両集合で firing_C ≥ %d）を満たさず測定不能。" % threshold
    else:
        shave_worse_both = (dev["Δshave"] <= 0 and confirm["Δshave"] <= 0)
        shave_and_fp_worse = ((dev["Δshave"] < 0 and dev["Δfp"] is not None and dev["Δfp"] < 0)
                              or (confirm["Δshave"] < 0 and confirm["Δfp"] is not None and confirm["Δfp"] < 0))
        if shave_worse_both or shave_and_fp_worse:
            verdict, reason = "不採用", ("削り割合が dev5・confirm5 の両集合で `Δshave ≤ 0`、または削りが悪化して"
                                         "かつ 総火力/ターン も base を下回った。base 継続。")
        elif all(cond[k] for k in (1, 3, 4, 5, 6)):
            verdict, reason = "採用", "条件1,3,4,5,6 と前提 G を満たす。EVALUATION.md §採用。"
        else:
            unmet = [str(k) for k in (1, 3, 4, 5, 6) if cond[k] is not True]
            verdict, reason = "保留", "条件 " + "・".join(unmet) + " を満たさない（向きの不一致・p>0.05・配対不足等）。"

    return {"verdict": verdict, "reason": reason, "cond": cond, "g_status": g_status,
            "gd": gd, "gc": gc, "direction_match": cond.get(1) if not pending else None,
            "dev": dev, "confirm": confirm, "fire_dev": fire_dev, "fire_confirm": fire_confirm,
            "threshold": threshold}


def format_candidate_report(label: str, res: dict) -> str:
    """Wording for one candidate's verdict: 発火率・削り割合・総火力/ターン・勝ち・配対・各条件・dev5との向きの一致."""
    dev, confirm = res["dev"], res["confirm"]
    thr = res["threshold"]
    L = [f"### 候補 {label}: 判定 **{res['verdict']}**", "", f"- 理由: {res['reason']}"]

    def fire_line(tag, fire):
        if not fire or fire.get("pairs", 0) == 0:
            return f"- 発火率({tag}): 実行データ無し"
        return (f"- 発火率({tag}): firing_C = {fire['fired']}/{fire['pairs']} 組"
                f"（閾値 {thr}、skipped {fire.get('skipped_missing_trace', 0)}）")

    L += ["", fire_line("dev5", res["fire_dev"]), fire_line("confirm5", res["fire_confirm"]),
          f"- 前提 G（両集合で ≥{thr}）: {res['g_status']}", ""]

    def delta_line(tag, d):
        if d is None:
            return f"- {tag}: 未実行（確認用待ち）"
        p = "–" if d["p"] is None else f"{d['p']:.3f}"
        fp = "–" if d["Δfp"] is None else f"{d['Δfp']:+.1f}"
        return (f"- {tag}: Δshave {d['Δshave']:+d}（候補優{d['better']}/base優{d['worse']}/同値{d['tie']}, p={p}） "
                f"Δfp {fp}（base {d['fp_base']:.1f}→cand {d['fp_cand']:.1f}） Δwin {d['Δwin']:+d}"
                f"（base {d['base_wins']}→cand {d['cand_wins']}） 配対 {d['pairs']}・比較不能 {d['not_comparable']}")

    L += [delta_line("dev5", dev), delta_line("confirm5", confirm), ""]
    L.append("- dev5 と confirm5 の削り割合の向きの一致: "
             + ("一致" if res["cond"].get(1) else "未実行" if confirm is None else "不一致"))
    for k in (1, 3, 4, 5, 6):
        status = _status(res["cond"][k])
        L.append(f"  - 条件{k}: {status}（原文は上の引用を参照）")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
