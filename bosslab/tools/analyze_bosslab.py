#!/usr/bin/env python3
"""Aggregate BossLab results into the local-verification report EVALUATION.md requires.

Analysis only; no game, no repo-policy source edits. Reads one or more BossLab result files
(data/bosslab_*/lab_results.jsonl, each line one trial written by BossLab.cs) and reports per-arm
win rates, the paired base-vs-+shrug and base-vs--shrug outcome per spec, the decision-opportunity /
decision-change / result-change breakdown from docs/EVALUATION.md:43, and (when two passes are
given) whether the win-rate *direction* reproduced across passes.

Grouping is derived from the result lines themselves:
  arm   from trial_id "<spec>|<arm>|<offset>"  (BossLab.cs writes trial_id verbatim)
  band  from result.entry_player_hp            (<60 / 60-79 / >=80, ACT2_BOSS_PLAN bands)
  spec  from spec_id
so no plan file is needed.

Trust filters (EVALUATION.md:62 — never fold unreliable runs into the totals silently):
  a trial counts only when outcome_source == combat_end_trace and error is absent;
  fallback / errored / missing trials are listed separately, not averaged into win rate.

Usage (from the worktree root):
  python3 .dsh/analyze_bosslab.py --run data/bosslab_test1 [--run data/bosslab_test2] \
      --out .dsh/bosslab_analysis.md
"""

from __future__ import annotations

import argparse
import collections
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

BANDS = ("<60", "60-79", ">=80")
RELIABLE = "combat_end_trace"


def band_of(hp: int) -> str:
    return "<60" if hp < 60 else "60-79" if hp < 80 else ">=80"


def load_trials(paths: list[Path]) -> tuple[list[dict], list[dict]]:
    usable, dropped = [], []
    for path in paths:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                dropped.append({"file": str(path), "why": "unparsable line"})
                continue
            res = r.get("result") or {}
            parts = (r.get("trial_id") or "").split("|")
            arm = parts[1] if len(parts) > 1 else "?"
            offset = parts[2] if len(parts) > 2 else "?"
            r["_arm"] = arm
            r["_offset"] = offset
            if r.get("error") or res.get("outcome_source") != RELIABLE:
                dropped.append({"trial_id": r.get("trial_id"), "arm": arm,
                                "why": ("error" if r.get("error")
                                        else f"outcome_source={res.get('outcome_source') or 'none'}")})
                continue
            usable.append(r)
    return usable, dropped


def arm_stats(trials: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in trials:
        s = out.setdefault(r["_arm"], {"n": 0, "wins": 0, "specs": set(), "by_band": collections.Counter()})
        s["n"] += 1
        res = r["result"]
        s["wins"] += 1 if res["won"] else 0
        s["specs"].add(r["spec_id"])
        s["by_band"][band_of(res["entry_player_hp"])] += 1
    for s in out.values():
        s["win_rate"] = s["wins"] / s["n"] if s["n"] else 0.0
    return out


def paired(trials: list[dict], base: str, other: str) -> dict:
    """Per (spec, offset) compare win rate of `other` vs `base` where both arms ran the same entry."""
    by_key: dict[tuple, dict] = collections.defaultdict(lambda: {base: [], other: []})
    for r in trials:
        if r["_arm"] in (base, other):
            by_key[(r["spec_id"], r["_offset"])][r["_arm"]].append(bool(r["result"]["won"]))
    rows = []
    improve = worsen = neutral = 0
    for (spec, off), d in sorted(by_key.items()):
        if not d[base] or not d[other]:
            continue
        bw = sum(d[base]) / len(d[base])
        ow = sum(d[other]) / len(d[other])
        if ow > bw:
            improve += 1
        elif ow < bw:
            worsen += 1
        else:
            neutral += 1
        rows.append((spec, off, bw, ow))
    return {"rows": rows, "improve": improve, "worsen": worsen, "neutral": neutral,
            "compared": len(rows), "not_comparable": sum(1 for (s, o), d in by_key.items()
                                                        if not d[base] or not d[other])}


def per_spec_wins(trials: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in trials:
        s = out.setdefault(r["spec_id"], {"hp": r["result"]["entry_player_hp"], "arms": collections.Counter(),
                                          "wins": collections.Counter()})
        s["arms"][r["_arm"]] += 1
        s["wins"][r["_arm"]] += 1 if r["result"]["won"] else 0
    return out


def rate(count: int, total: int) -> str:
    return f"{count}/{total}" + (f" ({100 * count / total:.0f}%)" if total else "")


def ac_se(k: int, n: int) -> tuple[float, float]:
    """Agresti-Coull adjusted rate and its SE (finite even when k=0 or k=n)."""
    if n <= 0:
        return float("nan"), float("nan")
    p = (k + 2.0) / (n + 4.0)
    return p, math.sqrt(p * (1 - p) / (n + 4.0))


def two_sided_p_from_z(z: float) -> float:
    return 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))


def mcnemar_exact_p(b: int, c: int) -> float:
    """Exact two-sided sign test on discordant pairs (null: equal flip probabilities)."""
    n = b + c
    if n == 0:
        return 1.0
    lo = min(b, c)
    s = sum(math.comb(n, i) for i in range(lo + 1))
    return min(1.0, 2.0 * s / (2 ** n))


def paired_counts(trials: list[dict], base: str, other: str) -> tuple[int, int, int]:
    """(#pairs with both arms, b: base-only wins, c: other-only wins) per (spec, offset)."""
    by_pair: dict[tuple, dict[str, bool]] = collections.defaultdict(dict)
    for t in trials:
        if t["_arm"] in (base, other):
            # one trial per (spec, arm, offset) in BossLab plans; majority vote is defensive
            by_pair[(t["spec_id"], t["_offset"])][t["_arm"]] = bool(t["result"]["won"])
    b = c = n = 0
    for arms in by_pair.values():
        if base in arms and other in arms:
            n += 1
            if arms[base] and not arms[other]:
                b += 1
            elif arms[other] and not arms[base]:
                c += 1
    return n, b, c


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", dest="runs", action="append", default=[],
                    help="a BossLab run dir (lab_results.jsonl inside); repeat, one per pass")
    ap.add_argument("--out", default=str(HERE / "bosslab_analysis.md"))
    ap.add_argument("--base", default="base")
    ap.add_argument("--specs", default=str(HERE / "boss_specs.jsonl"),
                    help="spec jsonl with the recorded real-run outcome per spec")
    args = ap.parse_args()

    orig: dict[str, bool | None] = {}
    specs_path = Path(args.specs)
    if specs_path.is_file():
        for line in specs_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                s = json.loads(line)
                orig[s["spec_id"]] = s["recorded_outcome"]["won"]

    pass_dirs = args.runs or [str(HERE.parent / "data")]
    pass_trials: list[list[dict]] = []
    all_dropped: list[dict] = []
    run_infos: list[dict] = []
    for d in pass_dirs:
        p = Path(d)
        results = [p / "lab_results.jsonl"] if p.is_dir() else [p]
        results = [r for r in results if r.is_file()] or list(p.glob("*/lab_results.jsonl"))
        trials, dropped = load_trials(results)
        for r in trials:
            r["_pass_idx"] = len(pass_trials)
        # Planned trials come from the run's lab_meta.json -> plan file, so trials the runner
        # killed (timeout / no result line) are counted separately from trials it still hasn't
        # started. A run dir whose failures.txt exists has finished.
        planned: list[dict] = []
        meta_path = p / "lab_meta.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            plan_file = meta.get("plan")
            if plan_file and Path(plan_file).is_file():
                planned = json.loads(Path(plan_file).read_text(encoding="utf-8")).get("trials", [])
        written = {t["trial_id"] for t in trials}
        written |= {dd["trial_id"] for dd in dropped if dd.get("trial_id")}
        run_infos.append({"dir": p, "planned": planned,
                          "missing": [t for t in planned if t["trial_id"] not in written],
                          "dropped": dropped, "done": (p / "failures.txt").is_file()})
        pass_trials.append(trials)
        all_dropped.extend(dropped)

    all_trials = [t for group in pass_trials for t in group]
    arms = sorted({t["_arm"] for t in all_trials})
    arms = ([args.base] if args.base in arms else []) + [a for a in arms if a != args.base]

    out = ["# BossLab 集計 (EVALUATION.md 局所検証の書式に準拠)", "",
           "各試行の採算は BossLab.cs が bridge-trace の combat_end から取った勝敗のみ。",
           "fallback・エラーの除外数と、結果行が無い試行（タイムアウト/未起動）を必ず併記し、"
           "母数に混ぜない（EVALUATION.md:62）。", ""]
    for ri, info in enumerate(run_infos):
        reasons = collections.Counter(dd["why"] for dd in info["dropped"])
        status = "完了" if info["done"] else "走行中（途中集計）"
        line = f"- パス {ri} `{info['dir'].name}` [{status}]: "
        if info["planned"]:
            line += (f"計画 {len(info['planned'])} · 結果行 {len(pass_trials[ri]) + len(info['dropped'])}"
                     f"（信頼 {len(pass_trials[ri])} / 除外 {len(info['dropped'])}")
            if reasons:
                line += " " + "、".join(f"{why}×{cnt}" for why, cnt in reasons.most_common())
            line += f" · 結果行なし {len(info['missing'])}"
            line += "）" if info["done"] else "、うち未着手分を含む）"
        else:
            line += (f"lab_meta.json に計画参照がないため結果行のみ: 信頼 {len(pass_trials[ri])}"
                     f" / 除外 {len(info['dropped'])}")
        out.append(line)
        if info["done"] and info["missing"]:
            ids = ", ".join(t["trial_id"] for t in info["missing"][:8])
            out.append(f"  - 結果行なし（runner が kill したタイムアウト/クラッシュ候補）: "
                       f"{len(info['missing'])} 件: {ids}")

    for pi, trials in enumerate(pass_trials):
        info = run_infos[pi]
        stats = arm_stats(trials)
        out += ["", f"## パス {pi}  （信頼 {len(trials)} / 除外 {len(info['dropped'])} / "
                    f"結果行なし {len(info['missing'])}）", "",
                "| arm | 試行 | 勝利 | 勝率 | 別れた spec 数 | band(<60/60-79/>=80) |",
                "| --- | --- | --- | --- | --- | --- |"]
        for a in arms:
            s = stats.get(a)
            if not s:
                continue
            bands = s["by_band"]
            out.append(f"| {a} | {s['n']} | {rate(s['wins'], s['n'])} | {s['win_rate']:.0%} | "
                       f"{len(s['specs'])} | {bands['<60']}/{bands['60-79']}/{bands['>=80']} |")
        for other in [a for a in arms if a != args.base]:
            pr = paired(trials, args.base, other)
            label = f"{other} vs {args.base}"
            out += ["", f"### {label}  （同じ entry での比較）", "",
                    f"- 比較できた entry 組: {pr['compared']}（比較不能 {pr['not_comparable']}）",
                    f"- {other} のほうが勝った entry: {pr['improve']}  /  {args.base} のほうが勝った: "
                    f"{pr['worsen']}  /  同値: {pr['neutral']}",
                    "| spec | offset | base 勝率 | %s 勝率 | 向き |" % other,
                    "| --- | --- | --- | --- | --- |"]
            for spec, off, bw, ow in pr["rows"]:
                arrow = "+" if ow > bw else "-" if ow < bw else "="
                out.append(f"| {spec} | {off} | {bw:.0%} | {ow:.0%} | {arrow} |")
        # spec-by-spec arm breakdown (the seed-level detail EVALUATION.md asks to keep)
        spec_w = per_spec_wins(trials)
        out += ["", f"### パス {pi}: spec 別（各 arm の勝利数/試行数）", "",
                "| spec | 入場HP | " + " | ".join(arms) + " | 実走 |",
                "| --- | --- | " + " | ".join("---" for a in arms) + " | --- |"]
        for spec, s in sorted(spec_w.items(), key=lambda kv: kv[1]["hp"]):
            cells = " | ".join(rate(s["wins"][a], s["arms"][a]) for a in arms)
            o = orig.get(spec)
            out.append(f"| {spec} | {s['hp']} | {cells} | "
                       f"{'勝' if o else '負' if o is False else '?'} |")
        # T5b: same-entry state consistency against the real run that produced the spec. The
        # recorded outcome is a single observation, so a disagreement per se is not a defect;
        # the reportable pattern is systematic drift (lab base winning on specs the real run
        # lost, or a win rate far from the 40% measured across 753 recorded fights).
        agree = drift = unrun = 0
        drift_lines: list[str] = []
        for spec, s in sorted(spec_w.items(), key=lambda kv: kv[1]["hp"]):
            o = orig.get(spec)
            n_base = s["arms"].get(args.base, 0)
            if o is None or n_base == 0:
                unrun += 1
                continue
            won = s["wins"].get(args.base, 0)
            lab_beat = won > 0
            if lab_beat == bool(o):
                agree += 1
            else:
                drift += 1
                drift_lines.append(f"  - {spec}: 実走{'勝' if o else '負'} → lab base {won}/{n_base} 勝"
                                   f"（{'lab が勝った' if lab_beat else 'lab が全敗'}）")
        n_specs_base = sum(1 for s in spec_w.values() if s["arms"].get(args.base))
        total_base = sum(s["arms"].get(args.base, 0) for s in spec_w.values())
        total_base_wins = sum(s["wins"].get(args.base, 0) for s in spec_w.values())
        out += ["", f"### パス {pi}: 実走記録との整合（T5b、base arm vs spec の記録）", "",
                f"- 一致 {agree} / ずれ {drift} / base 未試行 {unrun}（実走は 1 回の観測だけで、"
                f"T2 実測の母集団勝率 40% に対して base {rate(total_base_wins, total_base)}）",
                "- 単発のずれは想定内（40% 勝率で base 2 試行のうち 1 勝は各 spec で約 64% の確率）。"
                "判定したいのは systematic drift: lab base の勝率が 40% から大きく上振れし、"
                "かつ実走敗北の spec で lab が勝つパターンが続く場合、状態忠実性の偏りを疑う。"]
        if drift_lines:
            out.append("- ずれの内訳:")
            out.extend(drift_lines)

    if len(pass_trials) >= 2:
        out += ["", "## 再現性（パス間で勝敗の向きが一致するか）", ""]
        rates0 = arm_stats(pass_trials[0]); rates1 = arm_stats(pass_trials[1])
        common = [a for a in arms if a in rates0 and a in rates1]
        order0 = sorted(common, key=lambda a: -rates0[a]["win_rate"])
        order1 = sorted(common, key=lambda a: -rates1[a]["win_rate"])
        out += ["| arm | パス0 勝率 | パス1 勝率 |", "| --- | --- | --- |"]
        for a in common:
            out.append(f"| {a} | {rates0[a]['win_rate']:.0%} ({rate(rates0[a]['wins'], rates0[a]['n'])}) "
                       f"| {rates1[a]['win_rate']:.0%} ({rate(rates1[a]['wins'], rates1[a]['n'])}) |")
        agree = order0 == order1

        def order_str(rates: dict, order: list[str]) -> str:
            parts: list[str] = []
            for idx, arm_name in enumerate(order):
                if parts and rates[arm_name]["win_rate"] == rates[order[idx - 1]]["win_rate"]:
                    parts.append("≈")
                elif parts:
                    parts.append(">")
                parts.append(arm_name)
            return " ".join(parts)

        out += ["", f"- 勝率順 パス0: {order_str(rates0, order0)}",
                f"- 勝率順 パス1: {order_str(rates1, order1)}",
                f"- 向きの一致: {'一致' if agree else '不一致'}（同値 band が多いと順位は安定しない。≈ は同率）"]
    else:
        out += ["", "## 再現性", "", "- パスが 1 本だけ。EVALUATION.md の再現性確認には同じ計画の 2 回目が必要。"]

    # T7d: per-pass arm-delta with uncertainty, and agreement of the delta's direction across
    # passes. Two passes of the same specs with disjoint offsets are independent measurements:
    # same entry states, fresh RNG seeds per offset.
    if len(pass_trials) >= 2:
        for other in [a for a in arms if a != args.base]:
            head = (f"## 勝率差 {other} − {args.base} と不確かさ（パスごと / 2 パスの向きの一致）", "",
                    "| パス | base 勝率 | " + other + " 勝率 | 差 | SE(AC調整) | z | p(両側) | 不一致ペア b/c | McNemar 検定 p |",
                    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
            rows = []
            directions: list[int] = []
            pooled_k = {"base": [0, 0], other: [0, 0]}
            pooled_bc = [0, 0, 0]
            for pi, trials in enumerate(pass_trials):
                stats = arm_stats(trials)
                if args.base not in stats or other not in stats:
                    rows.append(f"| パス {pi} | — | — | — | — | この arm 比較に必要な trial が無い | | | |")
                    continue
                sb, so = stats[args.base], stats[other]
                pb, seb = ac_se(sb["wins"], sb["n"])
                po, seo = ac_se(so["wins"], so["n"])
                delta = po - pb
                se = math.sqrt(seb ** 2 + seo ** 2)
                z = delta / se if se > 0 else float("nan")
                p = two_sided_p_from_z(z)
                n_pair, b, c = paired_counts(trials, args.base, other)
                pm = mcnemar_exact_p(b, c)
                directions.append(1 if c > b else (-1 if c < b else 0))
                pooled_k[args.base][0] += sb["wins"]; pooled_k[args.base][1] += sb["n"]
                pooled_k[other][0] += so["wins"]; pooled_k[other][1] += so["n"]
                pooled_bc[0] += b; pooled_bc[1] += c; pooled_bc[2] += n_pair
                rows.append(f"| パス {pi} | {rate(sb['wins'], sb['n'])} | {rate(so['wins'], so['n'])} | "
                            f"{delta:+.0%} | {se:.3f} | {z:.1f} | {p:.3f} | b={b} c={c} (n={n_pair}) | {pm:.3f} |")
            pk_b, pn_b = pooled_k[args.base]; pk_o, pn_o = pooled_k[other]
            pbp, seb2 = ac_se(pk_b, pn_b); pop, seo2 = ac_se(pk_o, pn_o)
            pdelta = pop - pbp; pse = math.sqrt(seb2 ** 2 + seo2 ** 2)
            pz = pdelta / pse if pse > 0 else float("nan")
            pp = two_sided_p_from_z(pz)
            ppm = mcnemar_exact_p(pooled_bc[0], pooled_bc[1])
            rows.append(f"| **pooled** | {rate(pk_b, pn_b)} | {rate(pk_o, pn_o)} | {pdelta:+.0%} | {pse:.3f} | "
                        f"{pz:.1f} | {pp:.3f} | b={pooled_bc[0]} c={pooled_bc[1]} (n={pooled_bc[2]}) | {ppm:.3f} |")
            if directions and len(set(d for d in directions if d != 0)) <= 1 and any(directions):
                verdict = "2 パスで向きの一致" + ("（一方または両方が差 0 を含む）" if 0 in directions else "")
            elif directions:
                verdict = "2 パスで向きの不一致（再現できず）"
            else:
                verdict = "判定不能"
            out += ["", *head, *rows, "", f"- 向きの一致: {verdict}",
                    "- 差の SE は AC 調整比率（k+2/n+4）使用。McNemar は同じ entry・offset での不一致ペアのみ"
                    "を使う符号検定（帰無: flip 確率が arm で等しい）。両側 p。",
                    "- 2 パスは同一 spec 群で offset 範囲を排他的にした独立再測定。pooled は trial 独立として"
                    "統合したが、spec 共通ゆきの相関は残り得る（過小評価側に読む）。"]

    # EVALUATION.md:43 opportunity / decision / result framing, counts + seed counts
    n_specs = len({t["spec_id"] for t in pass_trials[0]}) if pass_trials[0] else 0
    out += ["", "## 局所検証の分類 (docs/EVALUATION.md:43)", "",
            "- 状態にカードがある（発動機会）: 選択 spec では base で SHRUG_IT_OFF を1枚以上持つ entry を使い、"
            "+arm で1枚増やし -arm で1枚減らす。発動機会は試行数そのもの（上の arm 別表）。",
            "- 判断が変わるか / 結果が変わるか: 同じ entry での arm 間勝敗差を上側の entry 組表に出した。"
            "札を1枚足しただけで敵行動列と引く順も動くため、entry 組ごとの差は単一の因果ではない。",
            f"- seed(spec) 数: {n_specs}。1 spec あたり arm ごとに offset ぶん繰り返す。",
            "- 採否はここでは断定しない（開発用の実測であり、確認用の独立 seed 集合ではない）。",
            "",
            "生成: `python3 .dsh/analyze_bosslab.py --run <dir> [--run <dir2>] --out .dsh/bosslab_analysis.md`",
            "生データ: 各 run dir の lab_results.jsonl（試行ごと 1 行、BossLab.cs が出す）"]
    Path(args.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: passes {len(pass_trials)} usable trials {[len(t) for t in pass_trials]} "
          f"dropped {len(all_dropped)} missing(no line) {sum(len(i['missing']) for i in run_infos)} arms {arms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
