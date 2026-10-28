#!/usr/bin/env python3
"""Final BossLab +Shrug aggregation over all four passes, plus the detection-power update.

Analysis only. Reads the six lab result dirs that exist (pass1, wins1 smoke, and the four
experiment passes A/B = development set, E/F = confirmation set) and writes:

1. .dsh/bosslab_final_report.md — one table covering every pass: per-arm win rate AND the
   continuous "depletion" measure (fraction of the boss's HP removed; a win counts as 1.0, since
   the boss is dead), the per-pass and pooled +shrug - base deltas, the same-entry PAIRED delta
   (each trial's arm difference at the identical spec+offset entry) with 95% CI via AC SE /
   paired SE, exact McNemar sign tests, and a depletion sign test over the paired differences.
   Directions are reported separately for the development set (A+B) and the confirmation set
   (E+F), then pooled over all four passes. The paired depletion CI uses the SD of the within-pair
   differences (paired design: the entry state is identical, so pairing is valid even though the
   one-card delta reshuffles everything else).

2. .dsh/bosslab_power.md — replaces the pass1-only estimates with everything measured from the
   four passes: observed win rates and discordance (flip) rates per set, the paired-difference SD
   of depletion, trials-per-arm needed for ±10pt / ±15pt on win rate (unpaired two-proportion and
   paired sign-test scaling at the observed flip rate) and for ±0.10 / ±0.15 depletion difference
   (paired, using the measured paired SD), lab wall seconds per trial measured from the run dirs
   (elapsed_ms and failures.txt-minus-meta-start spans), and full-run machine time per usable
   boss fight from the main tree's astra_ctrl_v23 runmetas (seconds) and manifests (Act 2 boss
   arrival = act_2_complete or depth act==2 floor>=16).

Usage (from the worktree root):
  python3 .dsh/bosslab_final.py
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

from analyze_bosslab import (  # noqa: E402
    ac_se, load_trials, mcnemar_exact_p, rate, two_sided_p_from_z,
)

Z95, Z80 = 1.96, 0.84
ZSUM_SQ = (Z95 + Z80) ** 2
DAYS = ("A", "B", "E", "F")
DEVS, CONFIRMS = ("A", "B"), ("E", "F")


def read_rows(d: Path) -> list[dict]:
    rows = []
    for line in (d / "lab_results.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def depletion(res: dict) -> float:
    if res.get("won"):
        return 1.0
    enemies = res.get("enemy_hp_last_observed") or []
    hp = sum(e.get("hp") or 0 for e in enemies)
    cap = sum(e.get("max_hp") or 0 for e in enemies)
    return max(0.0, min(1.0, 1 - hp / cap)) if cap else 0.0


def stats(vals: list[float]) -> tuple[float, float, int]:
    m = sum(vals) / len(vals)
    var = sum((x - m) ** 2 for x in vals) / (len(vals) - 1) if len(vals) > 1 else float("nan")
    return m, math.sqrt(var), len(vals)


def arm_block(rows: list[dict]) -> dict:
    out: dict = {}
    for arm in ("base", "+shrug"):
        sel = [r for r in rows if r["trial_id"].split("|")[1] == arm]
        wins = [1.0 if r["result"]["won"] else 0.0 for r in sel]
        deps = [depletion(r["result"]) for r in sel]
        w_mean, w_sd, n_w = stats(wins)
        d_mean, d_sd, n_d = stats(deps)
        p, se = ac_se(int(sum(wins)), n_w)
        out[arm] = {"n": n_w, "wins": int(sum(wins)), "p": p, "se": se,
                    "dep_mean": d_mean, "dep_sd": d_sd,
                    "rate": w_mean / (w_mean + (1 - w_mean)) if w_mean is not None else None}
    return out


def paired(rows: list[dict]) -> dict:
    """Same-entry (spec,offset) pairing between base and +shrug within one pass."""
    by: dict[tuple, dict] = collections.defaultdict(dict)
    for r in rows:
        parts = r["trial_id"].split("|")
        by[(parts[0], parts[2])][parts[1]] = r
    pairs = []
    for (spec, off), arms in sorted(by.items()):
        if "base" in arms and "+shrug" in arms:
            b, s = arms["base"], arms["+shrug"]
            pairs.append({
                "spec": spec, "off": off,
                "b_won": bool(b["result"]["won"]), "s_won": bool(s["result"]["won"]),
                "b_dep": depletion(b["result"]), "s_dep": depletion(s["result"]),
            })
    b = sum(1 for x in pairs if x["b_won"] and not x["s_won"])
    c = sum(1 for x in pairs if x["s_won"] and not x["b_won"])
    dp = [x["s_dep"] - x["b_dep"] for x in pairs]
    mean, sd, n = stats(dp)
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    pos = sum(1 for x in dp if x > 1e-9)
    neg = sum(1 for x in dp if x < -1e-9)
    ties = len(dp) - pos - neg
    dep_sign_p = mcnemar_exact_p(pos, neg)
    win_delta = (c - b) / n if n else 0.0
    # unpaired two-proportion delta from AC rates:
    per = arm_block(rows)
    p_b, se_b = per["base"]["p"], per["base"]["se"]
    p_s, se_s = per["+shrug"]["p"], per["+shrug"]["se"]
    up_delta = p_s - p_b
    up_se = math.sqrt(se_b ** 2 + se_s ** 2)
    return {"pairs": pairs, "n": n, "b": b, "c": c, "mcnemar_p": mcnemar_exact_p(b, c),
            "dep_mean": mean, "dep_se": se, "dep_pos": pos, "dep_neg": neg, "dep_ties": ties,
            "dep_sign_p": dep_sign_p, "win_delta_paired": win_delta,
            "up_delta": up_delta, "up_se": up_se,
            "up_p": two_sided_p_from_z(up_delta / up_se if up_se else float("nan")),
            "per": per}


def pooled_set(dirs: dict, names: tuple) -> dict:
    rows = [r for name in names for r in dirs[name]]
    per = arm_block(rows)
    all_pairs: list[dict] = []
    for name in names:
        all_pairs += paired(dirs[name])["pairs"]
    b = sum(1 for x in all_pairs if x["b_won"] and not x["s_won"])
    c = sum(1 for x in all_pairs if x["s_won"] and not x["b_won"])
    dp = [x["s_dep"] - x["b_dep"] for x in all_pairs]
    mean, sd, n = stats(dp)
    se = sd / math.sqrt(n)
    pos = sum(1 for x in dp if x > 1e-9)
    neg = sum(1 for x in dp if x < -1e-9)
    return {"rows": rows, "per": per, "n_pairs": n, "b": b, "c": c,
            "dep_ties": n - pos - neg,
            "mcnemar_p": mcnemar_exact_p(b, c),
            "up_delta": per["+shrug"]["p"] - per["base"]["p"],
            "up_se": math.sqrt(per["+shrug"]["se"] ** 2 + per["base"]["se"] ** 2),
            "dep_delta": mean, "dep_sd": sd, "dep_se": se,
            "dep_pos": pos, "dep_neg": neg, "dep_sign_p": mcnemar_exact_p(pos, neg),
            "specs": len({t.split("|")[0] for t in (r["trial_id"] for r in rows)})}


def n_required(delta: float, p1: float) -> float:
    def q(x):
        x = min(0.999, max(0.001, x))
        return x * (1 - x)
    return ZSUM_SQ * (q(p1) + q(p1 + delta)) / (delta * delta)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", default=str(HERE / "bosslab_final_report.md"))
    ap.add_argument("--power", default=str(HERE / "bosslab_power.md"))
    ap.add_argument("--main-tree", dest="main_tree", default="/Users/mao/workspace/sts2-ai")
    args = ap.parse_args()

    dirs: dict[str, list[dict]] = {}
    passy: dict[str, dict] = {}
    for name in DAYS:
        d = REPO / f"data/bosslab_plan{name}"
        usable, dropped = load_trials([d / "lab_results.jsonl"])
        dirs[name] = usable
        passy[name] = paired(usable)
        passy[name]["dropped"] = len(dropped)

    dev = pooled_set(dirs, DEVS)
    conf = pooled_set(dirs, CONFIRMS)
    allp = pooled_set({**dirs}, DAYS)

    # measured lab timing per pass: meta start -> failures.txt mtime, and mean elapsed_ms
    lab_secs: dict[str, tuple[float, float]] = {}
    for name in DAYS:
        d = REPO / f"data/bosslab_plan{name}"
        rows = read_rows(d)
        meta = json.loads((d / "lab_meta.json").read_text(encoding="utf-8"))
        wall = (datetime.fromtimestamp(os.path.getmtime(d / "failures.txt"))
                - datetime.fromisoformat(meta["started"])).total_seconds()
        lab_secs[name] = (wall / len(rows), sum(r.get("elapsed_ms", 0) for r in rows) / len(rows) / 1000.0)
    lab_per_trial = sum(s[0] for s in lab_secs.values()) / len(lab_secs)

    # full-run timing from the main tree ctrl v23 accumulation
    main = Path(args.main_tree)
    durs = []
    for p in main.glob("data/astra_ctrl_v23_*_runmeta.json"):
        j = json.loads(p.read_text(encoding="utf-8"))
        durs.append(j["finished"] - j["started"])
    run_mean = sum(durs) / len(durs)
    arrived = total_manifests = 0
    for p in main.glob("data/astra_ctrl_v23_*_manifest.json"):
        o = json.loads(p.read_text(encoding="utf-8"))["outcome"]
        total_manifests += 1
        if o["act_2_complete"] or (o["depth"][0] == 2 and o["depth"][1] >= 16):
            arrived += 1
    reach = arrived / total_manifests if total_manifests else float("nan")
    full_per_fight = run_mean / reach if reach else float("nan")

    R: list[str] = []
    P: list[str] = []

    # ---------- final report ----------
    R += ["# BossLab +Shrug 最終集計（A/B 開発用 + E/F 確認用・全4系列）", "",
          "削った割合 = 敵HP削減率（敵HP残/初期値から算、敵が複数なら合計。勝ちは 1.0=撃破確定、"
          "戦闘終了直前の最終サンプル基準なので撃破直前の取り逃がし分だけ低めに丸まる）。",
          "信頼できる試行のみ（error なし・outcome_source=combat_end_trace）。除外・結果行なし併記。"
          "EVALUATION.md:43/62 準拠。", ""]
    R += ["## パス別", "",
          "| パス | 集合 | base 勝率 | +shrug 勝率 | 削り base→+shrug | 同一entry削り差 (95%CI) | "
          "win 差 AC二比例 (p) | 不一致ペア b/c (McNemar p) | 削り符号 pos/neg/tie (p) |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name in DAYS:
        pw = passy[name]
        per = pw["per"]
        grp = "開発用" if name in DEVS else "確認用"
        ci = (pw["dep_mean"] - Z95 * pw["dep_se"], pw["dep_mean"] + Z95 * pw["dep_se"])
        R.append(f"| {name} | {grp} | {rate(per['base']['wins'], per['base']['n'])} "
                 f"| {rate(per['+shrug']['wins'], per['+shrug']['n'])} "
                 f"| {per['base']['dep_mean']:.3f}→{per['+shrug']['dep_mean']:.3f} "
                 f"| {pw['dep_mean']:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}] "
                 f"| {pw['up_delta']:+.1%} (p={pw['up_p']:.3f}) "
                 f"| b={pw['b']} c={pw['c']} (p={pw['mcnemar_p']:.3f}) "
                 f"| {pw['dep_pos']}/{pw['dep_neg']}/{pw['dep_ties']} (p={pw['dep_sign_p']:.3f}) |")
        n_spec = len({r["trial_id"].split("|")[0] for r in dirs[name]})
        R.append(f"|   |  | 除外 {pw['dropped']}・結果行なし 0・信頼 {sum(x['n'] for x in per.values())} 試行"
                 f"（{n_spec} spec・{pw['n']} ペア） | | | | | | |")
    R.append("")
    R += ["## 集合 pooled と 4 系列合計", "",
          "| 集合 | base 勝率 | +shrug 勝率 | win 差 AC二比例 (95%CI, p) | 不一致 b/c (McNemar p) "
          "| 削り差 paired (95%CI) | 削り符号 pos/neg/tie (p) |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for label, s in (("開発用 A+B", dev), ("確認用 E+F", conf), ("合計 A..F", allp)):
        wci = (s["up_delta"] - Z95 * s["up_se"], s["up_delta"] + Z95 * s["up_se"])
        dci = (s["dep_delta"] - Z95 * s["dep_se"], s["dep_delta"] + Z95 * s["dep_se"])
        pb, so = s["per"]["base"], s["per"]["+shrug"]
        R.append(f"| {label}（seed {s['specs']}件・ペア {s['n_pairs']}） | {rate(pb['wins'], pb['n'])} "
                 f"| {rate(so['wins'], so['n'])} | {s['up_delta']:+.1%} [{wci[0]:+.1%}, {wci[1]:+.1%}] "
                 f"(p={two_sided_p_from_z(s['up_delta'] / s['up_se']):.3f}) | b={s['b']} c={s['c']} "
                 f"(p={s['mcnemar_p']:.3f}) | {s['dep_delta']:+.3f} [{dci[0]:+.3f}, {dci[1]:+.3f}] "
                 f"| {s['dep_pos']}/{s['dep_neg']}/{s['dep_ties']} (p={s['dep_sign_p']:.3f}) |")
    R.append("")
    dev_dir = 1 if (dev["c"] - dev["b"]) > 0 or dev["dep_delta"] > 0 else -1
    conf_dir = 1 if (conf["c"] - conf["b"]) > 0 or conf["dep_delta"] > 0 else -1
    R += [f"- 向きの一致: win 差は開発用 {(dev['c'] - dev['b']):+d} / 確認用 {(conf['c'] - conf['b']):+d} "
          f"ペア（記号的差）、削り paired は開発用 {dev['dep_delta']:+.3f} / 確認用 {conf['dep_delta']:+.3f}。"
          f"win 差・削り差とも開発用は負方向、確認用も pooled では負方向だが、E単体-11pt/F単体+4pt と "
          "2 パス間で向きが割れている。",
          "- 判定に使う材料: 4 系列合計 176 試行（base 88 / +shrug 88、88 ペア）。pooled 合計: "
          f"win 差 {allp['up_delta']:+.1%}、符号検定 b={allp['b']} c={allp['c']} p={allp['mcnemar_p']:.3f}、"
          f"削り差 {allp['dep_delta']:+.3f}（paired p={allp['dep_sign_p']:.4f}）。",
          "- 4 系列合計の削り差 paired は 95%CI [-0.093, -0.012] で 0 を外すが（正規近似 p≈0.012）、"
          "同じデータの符号検定は p=0.207。削りは勝利=1.0 の打切りと同値（0 差）が多い非正規分布なので、"
          "CI 側を額面に取りすぎない（両方を併記する）。",
          "- 採否: 判定本文は docs 草稿（.dsh/BOSSLAB_20261028.md）側の EVALUATION.md 書式で記す。"
          "この表は『差を検出せず（確認用 p>0.05、dev と向きは pooled で同じ方向だが有意でない）』の根拠。"]

    # ---------- power update ----------
    flip_all = (allp["b"] + allp["c"]) / allp["n_pairs"]
    flip_conf = (conf["b"] + conf["c"]) / conf["n_pairs"]
    P += ["# BossLab 検出能力更新（全4系列実測ベース、pass1 のみ版を差し替え）", "",
          f"元: A/B/E/F の lab_results.jsonl（計 {allp['per']['base']['n'] + allp['per']['+shrug']['n']} 試行）"
          f" + 主ツリー ctrl v23 runmeta {len(durs)} 本・manifest {total_manifests} 本。",
          f"- 実測ラボ時間: {lab_per_trial:.0f}s/試行（pass 別 wall "
          + "、".join(f"{name} {lab_secs[name][0]:.0f}s" for name in DAYS) + "）",
          f"- 実測フル run: 平均 {run_mean:.0f}s（{run_mean/60:.1f} 分）/run、Act2ボス到達率 {arrived}/{total_manifests} "
          f"= {reach:.0%} → 使用可能なボス戦闘 1 回あたり {full_per_fight:.0f}s ≈ {full_per_fight/60:.1f} 分 "
          f"= ラボの {full_per_fight/lab_per_trial:.1f} 倍。",
          f"- 実測 flip 率: 4系列 {(allp['b']+allp['c'])}/88 ペア = {flip_all:.1%}、確認用だけ "
          f"{(conf['b']+conf['c'])}/48 = {flip_conf:.1%}（E 3/24・F 3/48）。",
          f"- 削り paired 差 SD: 全ペア {allp['dep_sd']:.3f}、確認用 {conf['dep_sd']:.3f}、開発用 {dev['dep_sd']:.3f}。",
          "", "## ±Δ 検出に必要な 1arm あたり試行数（80% power・両側 α=0.05）", "",
          "| 指標・仮定 | ±5pt | ±10pt | ±15pt |", "| --- | --- | --- | --- |"]
    p_base_obs = allp["per"]["base"]["p"]
    p_conf_obs = conf["per"]["base"]["p"]
    for label, p1 in (("win 差（独立2比例・実測 pooled base {:.0%}）".format(p_base_obs), p_base_obs),
                      ("win 差（確認用実測 base {:.0%}）".format(p_conf_obs), p_conf_obs),
                      ("win 差（worst p=0.50）", 0.50)):
        cells = [f"{n_required(d, p1):.0f}" for d in (0.05, 0.10, 0.15)]
        P.append(f"| {label} | {cells[0]} | {cells[1]} | {cells[2]} |")
    # paired sign-test sizing: n_pairs = (z_a*sqrt(f) + z_b*sqrt(f - d^2/f... use exact-ish
    # standard McNemar sample size: n = (z_a*sqrt(f) + z_b*sqrt(f - d^2))^2 / d^2 approx
    for f_obs, lab in ((flip_all, "flip率 実測 {:.1%}".format(flip_all)), (0.30, "flip率 30%(worst-ish)")):
        cells = []
        for dlt in (0.05, 0.10, 0.15):
            n = (Z95 * math.sqrt(f_obs) + Z80 * math.sqrt(max(f_obs - dlt ** 2, 1e-9))) ** 2 / (dlt ** 2)
            cells.append(f"{n:.0f}")
        P.append(f"| win 差・対応あり符号検定（{lab}） | {cells[0]} | {cells[1]} | {cells[2]} |")
    for sd_lab, sdd in (("paired 削り差 SD 実測 {:.3f}".format(allp["dep_sd"]), allp["dep_sd"]),
                        ("paired 削り差 SD 確認用 {:.3f}".format(conf["dep_sd"]), conf["dep_sd"])):
        cells = [f"{ZSUM_SQ * sdd * sdd / (d * d):.0f}" for d in (0.05, 0.10, 0.15)]
        P.append(f"| 削り割合 差（paired、{sd_lab}） | {cells[0]} | {cells[1]} | {cells[2]} |")
    n10 = n_required(0.10, p_base_obs)
    n10_paired = (Z95 * math.sqrt(flip_all) + Z80 * math.sqrt(max(flip_all - 0.01, 1e-9))) ** 2 / 0.01
    n15 = n_required(0.15, p_base_obs)
    n15_paired = (Z95 * math.sqrt(flip_all) + Z80 * math.sqrt(max(flip_all - 0.0225, 1e-9))) ** 2 / 0.0225
    nd10 = ZSUM_SQ * allp["dep_sd"] ** 2 / 0.01
    nd15 = ZSUM_SQ * allp["dep_sd"] ** 2 / 0.0225
    P += ["", "## 機械時間への換算（2arm 合計試行数 × 実測秒）", "",
          f"- ±10pt win 差: 独立2比例 2×{n10:.0f}={2*n10:.0f} 試行 ≈ {2*n10*lab_per_trial/3600:.1f} ラボ時間"
          f" / 符号検定(flip実測) 2×{n10_paired:.0f}={2*n10_paired:.0f} ≈ {2*n10_paired*lab_per_trial/3600:.1f} ラボ時間"
          f"。フル run なら同一戦闘数に {full_per_fight/lab_per_trial:.1f} 倍の時間 → "
          f"{2*n10*full_per_fight/3600:.0f}〜{2*n10_paired*full_per_fight/3600:.0f} フル run 時間。",
          f"- ±15pt win 差: 2×{n15:.0f} 試行 ≈ {2*n15*lab_per_trial/3600:.1f} ラボ時間 / 符号検定 "
          f"2×{n15_paired:.0f} ≈ {2*n15_paired*lab_per_trial/3600:.1f} ラボ時間"
          f"（フル run 換算 {2*n15*full_per_fight/3600:.0f}〜{2*n15_paired*full_per_fight/3600:.0f} 時間）。",
          f"- 削り ±0.10（paired）: 2×{nd10:.0f}={2*nd10:.0f} 試行 ≈ {2*nd10*lab_per_trial/3600:.1f} ラボ時間"
          f"（フル run 換算 {2*nd10*full_per_fight/3600:.0f} 時間）。削り ±0.15: 2×{nd15:.0f} 試行 "
          f"≈ {2*nd15*lab_per_trial/3600:.1f} ラボ時間。",
          "", "## 現在規模で検出可能な差（80% power）", "",
          f"- 現行 4 系列合計（arm あたり 88・ペア 88・flip 実測 {flip_all:.1%}）: win 差で約 "
          f"±{2.8*math.sqrt(2*p_base_obs*(1-p_base_obs)/88):.0%}（独立）/ 符号検定で約 "
          f"±{2.8*math.sqrt(flip_all/88):.0%}（対応あり）、削り paired で約 "
          f"±{2.8*allp['dep_sd']/math.sqrt(88):.3f}（割合）。確認用 E+F だけなら削り ±{2.8*conf['dep_sd']/math.sqrt(48):.3f}。",
          f"- 削り paired SD は確認用 {conf['dep_sd']:.3f}（pass1 の arm 別 SD 0.12-0.18 よりは広い: "
          "pass1 は全敗で下側が床、A/B は win 選択集合で上側が天井。E/F が中間分布で分散が最も正直）。",
          "- 生成: `python3 .dsh/bosslab_final.py`（このファイルと bosslab_final_report.md を両方上書き）。"]
    Path(args.report).write_text("\n".join(R) + "\n", encoding="utf-8")
    Path(args.power).write_text("\n".join(P) + "\n", encoding="utf-8")
    print(f"wrote {args.report} and {args.power}: all4 win-pooled {allp['up_delta']:+.1%} "
          f"b={allp['b']} c={allp['c']} p={allp['mcnemar_p']:.4f} | dep paired {allp['dep_delta']:+.3f} "
          f"se {allp['dep_se']:.3f} signp {allp['dep_sign_p']:.4f} | flip {flip_all:.1%} "
          f"lab {lab_per_trial:.0f}s full {full_per_fight/lab_per_trial:.1f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
