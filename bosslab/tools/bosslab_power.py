#!/usr/bin/env python3
"""Detection-power estimates for the BossLab arm comparison (EVALUATION.md sizing aid).

Analysis only. Reads BossLab result files (same trust filter as analyze_bosslab.py: rows with
error or outcome_source != combat_end_trace are excluded) and answers two questions the leader
needs to size pass2:

1. SE of the arm difference, measured from the pass so far. With win/loss being a binary
   outcome and per-arm counts small, the raw sample SE degenerates (p̂=0 gives SE=0), so the
   binary SE uses an Agresti-Coull adjusted proportion p̃=(k+2)/(n+4) and the required-sample
   numbers additionally report a prior-free column using the T2-measured population boss win
   rate (0.40) as the assumed base rate.
2. Trials per arm needed to see a ±10pt difference (also ±5pt and ±20pt) at two-sided α=0.05
   with 80% power, under three metrics:
   - binary two-proportion (independent arms): n = (z_a+z_b)^2 (p1q1+p2q2) / Δ^2
   - binary paired (McNemar-style, same spec+offset in both arms): n_pair = (z_a+z_b)^2 f / d^2,
     where d is the net flip rate and f the total flip rate; pass1 only bounds f from above
     until discordant pairs actually appear, so the table shows the f sensitivity.
   - continuous "boss depletion" metric: per trial, killed fraction
     d = 1 if won else 1 - remaining_enemy_hp / initial_enemy_hp (losses), capped [0,1].
     Means compare with far less variance than 0/1 outcomes: n/arm = 2 σ̄² (z_a+z_b)^2 / Δ².
     Caveat: depletion is not win rate; it is a proxy for how close the fight came, validated
     against recorded outcomes in the T2 measurement (bands by depletion track recorded win
     rates 15%/35%/57%). Wins are censored at 1.0.

z values: 1.96 (α=0.05 two-sided) and 0.84 (80% power), so (z_a+z_b)^2 = 7.84.

Wall-clock conversion uses the leader's measured ~120 s per trial including relaunch; override
with --seconds-per-trial.

Usage (from the worktree root):
  python3 .dsh/bosslab_power.py --run data/bosslab_pass1 --out .dsh/bosslab_power.md
"""

from __future__ import annotations

import argparse
import collections
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from analyze_bosslab import RELIABLE, load_trials  # noqa: E402

Z_SUM_SQ = (1.96 + 0.84) ** 2  # 7.84: alpha=0.05 two-sided, 80% power
PRIOR_WIN_RATE = 0.40          # T2 measurement: recorded Act 2 boss win rate, 304/753
DELTAS = (0.05, 0.10, 0.20)


def ac_se(k: int, n: int) -> tuple[float, float]:
    """Agresti-Coull adjusted rate and its SE (works when k=0 or k=n)."""
    if n <= 0:
        return float("nan"), float("nan")
    p = (k + 2.0) / (n + 4.0)
    return p, math.sqrt(p * (1 - p) / (n + 4.0))


def depletion(r: dict) -> float | None:
    res = r["result"]
    enemies = res.get("enemy_hp_last_observed") or []
    total_hp = sum(e.get("hp") or 0 for e in enemies)
    total_max = sum(e.get("max_hp") or 0 for e in enemies)
    if total_max <= 0:
        return None
    if res.get("won"):
        return 1.0
    return max(0.0, min(1.0, 1 - total_hp / total_max))


def required_n_binary(p1: float, delta: float) -> float:
    p2 = min(0.999, max(0.001, p1 + delta))
    return Z_SUM_SQ * (p1 * (1 - p1) + p2 * (1 - p2)) / (delta * delta)


def required_n_paired(flip_total: float, net: float) -> float:
    return Z_SUM_SQ * flip_total / (net * net)


def required_n_continuous(sigma: float, delta: float) -> float:
    return 2 * sigma * sigma * Z_SUM_SQ / (delta * delta)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", dest="runs", action="append", required=True,
                    help="BossLab run dir(s) to pool (results rows pooled per arm)")
    ap.add_argument("--out", default=str(HERE / "bosslab_power.md"))
    ap.add_argument("--base", default="base")
    ap.add_argument("--prior-p", dest="prior_p", type=float, default=PRIOR_WIN_RATE)
    ap.add_argument("--seconds-per-trial", dest="secs", type=int, default=120)
    args = ap.parse_args()

    trials: list[dict] = []
    for d in args.runs:
        p = Path(d)
        results = [p / "lab_results.jsonl"] if p.is_dir() else [p]
        results = [r for r in results if r.is_file()]
        usable, dropped = load_trials(results)
        trials += usable
    if not trials:
        raise SystemExit("no usable result rows")

    stats: dict[str, dict] = {}
    for t in trials:
        arm = t["_arm"]
        s = stats.setdefault(arm, {"n": 0, "k": 0, "dep": []})
        s["n"] += 1
        s["k"] += 1 if t["result"]["won"] else 0
        dep = depletion(t)
        if dep is not None:
            s["dep"].append(dep)
    for s in stats.values():
        s["p̃"], s["se"] = ac_se(s["k"], s["n"])
        deps = s["dep"]
        m = sum(deps) / len(deps) if deps else float("nan")
        var = sum((x - m) ** 2 for x in deps) / (len(deps) - 1) if len(deps) > 1 else float("nan")
        s["m̂"], s["σ̂"] = m, math.sqrt(var)

    others = sorted(a for a in stats if a != args.base)
    base = stats.get(args.base, {"n": 0, "k": 0})

    # Paired discordance (same spec_id AND same offset between base and each arm).
    by_pair: dict[tuple, dict[str, bool]] = collections.defaultdict(dict)
    for t in trials:
        by_pair[(t["spec_id"], t["_offset"])][t["_arm"]] = bool(t["result"]["won"])
    pair_lines = []
    for other in others:
        b = c = n_pair = 0
        for _, arms in by_pair.items():
            if args.base in arms and other in arms:
                n_pair += 1
                if arms[args.base] and not arms[other]:
                    b += 1
                elif arms[other] and not arms[args.base]:
                    c += 1
        pair_lines.append((other, n_pair, b, c))

    out = ["# BossLab 検出能力見積 (T5c)", "",
           f"プール対象: {', '.join(args.runs)}  信頼できる試行 {len(trials)} 件"
           f"（error・fallback・結果行なしは除外済み）。",
           f"1試行 ≈ {args.secs} 秒（leader 実測: 起動含む約2分）で wall time に換算。", "",
           "## 観測値", "",
           "| arm | 試行 | 勝利 | p̂ (AC調整) | SE | 削り割合 平均 | SD |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    for arm in [args.base] + others:
        s = stats.get(arm)
        if not s:
            continue
        out.append(f"| {arm} | {s['n']} | {s['k']} | {s['p̃']:.2f} | {s['se']:.3f} | "
                   f"{s['m̂']:.2f} | {s['σ̂']:.2f} |" if s["n"] else f"| {arm} | 0 | - | - | - | - | - |")
    out += ["", "### arm 差の SE（base 比、pass 時点の実測）", ""]
    for other in others:
        so = stats.get(other)
        if not so or not base.get("n"):
            continue
        se = math.sqrt(base["se"] ** 2 + so["se"] ** 2)
        out.append(f"- {other} vs {args.base}: SE(diff) ≈ {se:.3f}"
                   f"（観測 p̃ {base['p̃']:.2f} vs {so['p̃']:.2f}、AC調整ゆえ p̂=0/全勝でも 0 にならない）")
    out += ["", "## 離線対（同じ spec・offset での base vs arm の不一致、McNemar の素材）", ""]
    for other, n_pair, b, c in pair_lines:
        f_obs = (b + c) / n_pair if n_pair else float("nan")
        out.append(f"- {other} vs {args.base}: ペア {n_pair} 組、不一致 {b + c}（{other} 勝ち側 {c} / "
                   f"{args.base} 勝ち側 {b}）、観測 flip rate {f_obs:.2f}")
    out += ["- 不一致が 0 だと「pair 設計で 10pt を検出」の分母が決められない。上の表は感度表で出す。", ""]

    out += ["## ±Δ 検出に必要な 1arm あたり試行数（80% power・両側 α=0.05）", "",
            "binary(独立2比例) は base 勝率 p を仮定、binary(pair) は flip 率 f と正味差 d で決まる"
            "（f 不詳のため感度表）、continuous(削り割合) は pass 実測の SD を使う。", ""]
    sd_obs = next((stats[a]["σ̂"] for a in ([args.base] + others) if stats.get(a, {}).get("σ̂")
                   and not math.isnan(stats[a]["σ̂"])), float("nan"))
    out += ["| Δ | binary@p={:.2f}(prior) | binary@p={:.2f}(pass1) | binary(pair) f=0.10 | f=0.20 | f=0.30 | continuous@SD={} |".format(
        args.prior_p, base.get("p̃", float("nan")), "0.22" if math.isnan(sd_obs) else f"{sd_obs:.2f}"),
        "| --- | --- | --- | --- | --- | --- | --- |"]
    prior = args.prior_p
    for delta in DELTAS:
        row = [f"±{delta:.0%}"]
        n_prior = required_n_binary(prior, delta)
        n_pass = required_n_binary(base.get("p̃", prior), delta)
        row.append(f"{n_prior:.0f} (≈{n_prior * 2 * args.secs / 3600:.1f}h)")
        row.append(f"{n_pass:.0f} (≈{n_pass * 2 * args.secs / 3600:.1f}h)")
        for f in (0.10, 0.20, 0.30):
            n_pr = required_n_paired(f, delta)
            row.append(f"{n_pr:.0f}")
        if not math.isnan(sd_obs):
            n_c = required_n_continuous(sd_obs, delta)
            row.append(f"{n_c:.0f} (≈{n_c * 2 * args.secs / 3600:.1f}h)")
        else:
            row.append("-")
        out.append("| " + " | ".join(row) + " |")
    out += ["", "(h) は arm2つ分（例 base vs +shrug の 2arm）の total wall time。"
                 "3arm 比較なら arm 数をかけてよい。f 列は n_pair/arm。", ""]

    n_now = min((stats[a]["n"] for a in [args.base] + others if stats.get(a, {}).get("n")), default=0)
    if n_now:
        mde_bin = (1.96 + 0.84) * math.sqrt(2 * prior * (1 - prior) / n_now)
        line = (f"- 現在 scale（min arm n={n_now}）で 80% power で検出できる差: "
                f"binary 勝率Rate ±{mde_bin:.0%}（prior p={prior:.2f} 仮定）")
        out.append(line)
        if not math.isnan(sd_obs):
            mde_c = (1.96 + 0.84) * math.sqrt(2 * sd_obs ** 2 / n_now)
            out.append(f"- 削り割合（continuous）なら ±{mde_c:.0%}（SD={sd_obs:.2f} 実測）まで検出可")
    out += ["", "## 読み方", "",
            "- 削り割合は「その敵をどこまで削って死んだか」で、連続量なので binary より少ない試行で済む。"
            "T2 で削り割合の band 別実走勝率は 15%/35%/57% と単調に追従するため、削りの平均差は"
            "勝率変化の先行指標として使える。ただし削り+10pt が必ずしも勝率変化になるとは限らない"
            "(勝利側は 1.0 で打切)。",
            "- pair 設計（同じ entry に 1 枚差す）は元状態が同じだが、札 1 枚で敵行動列と shuffle が"
            "動くため flip は起きる。flip 率 f が観測できて初めて必要サンプル数が決まる。",
            "- 勝率の絶対値は prior 40% と pass1 実測の乖離に幅がある: spec 選択が「実走が負けた "
            "entry 6 件」に偏っている（選択条件に outcome を入れていない偶然）。pass1 完走後の p̃ "
            "で最終的な n を再計算すること。",
            f"- 生成: `python3 .dsh/bosslab_power.py --run <run dir> --out .dsh/bosslab_power.md`"
            "（pass 完走後に再実行すると pass1 の SD・p̃・flip 率で更新される）"]
    Path(args.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: pooled {len(trials)} usable rows, arms {sorted(stats)}, "
          f"paired rows {[(o, npar, b, c) for o, npar, b, c in pair_lines]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
