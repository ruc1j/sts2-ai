#!/usr/bin/env python3
"""Aggregate BossLab results into the local-verification report EVALUATION.md requires.

Analysis only; no game, no repo-policy source edits. Reads one or more BossLab result files (a QUEEN panel is judged on the
Queen-shave axis as its primary signal with win rate kept auxiliary — see continuous_metrics below)
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
import statistics
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


# Act 3 (QUEEN) では主信号を勝敗にしない。実走の Act 3 base 勝率は約7%で床に張り付くため、
# 候補の差が 0/12 と 1/12 の間に埋もれる。ここでは「Queen 自身の 400 HP を何%削れたか」を主信号に
# し、Amalgam 撃破・死亡ターン・失HP を補助として同じ entry ごとに配对で比較する（EVALUATION.md の
# 局所検証の書式。召喚物である Amalgam は Queen の進捗に混ぜず別記）。
def load_entry_state_relics() -> set:
    """入室時の挙動が自分の [SavedProperty] や室数に依存するレリックの一覧。

    これを持つ spec は lab の新生レリックが実走が使い切った効果をもう一度発火させるので、入場状態が
    実走とズレると分かっている。一覧は scan_relic_run_state.py がデコンパイルから作ったもの
    （bosslab/results/entry_state_relics.json）。無ければ空集合で、† 付きの判定は行わない。
    """
    candidates = [root / sub for root in (HERE, HERE.parent, HERE.parents[1])
                  for sub in (Path("bosslab") / "results" / "entry_state_relics.json",
                              Path("results") / "entry_state_relics.json",
                              Path(".dsh") / "relic_run_state.json")]
    for candidate in candidates:
        if candidate.is_file():
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            return {str(relic) for relic in (payload.get("entry_state_relics") or {})}
    return set()


ENTRY_STATE_RELICS = load_entry_state_relics()


def flag_specs_from_plan(plan_trials: list[dict]) -> dict[str, list[str]]:
    """plan の trial から spec 単位で「lab が実走とズレるとKnownのレリック」を拾う。"""
    flags: dict[str, set] = collections.defaultdict(set)
    for trial in plan_trials or ():
        for relic in trial.get("relics") or ():
            relic_id = str(relic)
            if not relic_id.startswith("RELIC."):
                relic_id = "RELIC." + relic_id
            if relic_id in ENTRY_STATE_RELICS:
                flags[trial.get("spec_id")].add(relic_id)
    return {spec: sorted(names) for spec, names in flags.items() if names}


QUEEN_ID_SUFFIX = ".QUEEN"
AMALGAM_ID_SUFFIX = "TORCH_HEAD_AMALGAM"
QUEEN_MAX_HP = 400


def continuous_metrics(trial: dict) -> dict:
    """1試行分から Queen削り割合と補助指標を取り出す。

    BossLab.cs が書く `enemy_hp_last_observed` は戦闘終了時に盤面へ生きている敵だけなので、行に
    存在しない敵は死亡している。勝ちは Queen が死んだことで確定するため、削り割合は 1.0。
    """
    result = trial["result"]
    enemies = list(result.get("enemy_hp_last_observed") or ())
    queen = next((enemy for enemy in enemies if str(enemy.get("id", "")).endswith(QUEEN_ID_SUFFIX)), None)
    amalgam = next((enemy for enemy in enemies
                    if str(enemy.get("id", "")).endswith(AMALGAM_ID_SUFFIX)), None)
    won = bool(result.get("won"))
    if queen is None or won:
        shaved = 1.0
    else:
        max_hp = float(queen.get("max_hp") or 0) or float(QUEEN_MAX_HP)
        shaved = max(0.0, min(1.0, (max_hp - float(queen.get("hp") or 0)) / max_hp))
    entry_hp = result.get("entry_player_hp")
    final_hp = result.get("final_player_hp")
    return {
        "queen_shaved": shaved,
        "amalgam_killed": amalgam is None or won,
        "turns": result.get("last_observed_turn"),
        "hp_lost": entry_hp - final_hp if entry_hp is not None and final_hp is not None else None,
        "won": won,
    }


def is_queen_panel(trials: list[dict]) -> bool:
    return any(str(trial.get("encounter") or "").endswith("QUEEN_BOSS") for trial in trials)


METRICS = (("queen_shaved", True, "Queen削り割合（主信号）"),
           ("amalgam_killed", True, "Amalgamを倒せたか（補助）"),
           ("turns", True, "死亡ターン（補助・長いほど良い）"),
           ("hp_lost", False, "失ったHP（補助・少ないほど良い）"))


def paired_continuous(trials: list[dict], base: str, other: str,
                      exclude_specs: set | None = None) -> dict:
    """同じ entry（spec と offset）で base と候補の連続指標を比べる。

    主信号の Queen削り割合だけを同値を除く符号検定にかけ（EVALUATION.md の flip 検定と同じ
    McNemar 精密p）、補助指標は向きの件数だけ並べる。同じ entry を複数回試行した場合は arm 内で
    平均してから配对する。
    """
    by_key: dict[tuple, dict[str, list[dict]]] = collections.defaultdict(
        lambda: {base: [], other: []})
    for trial in trials:
        if trial["_arm"] in (base, other):
            by_key[(trial["spec_id"], trial["_offset"])][trial["_arm"]].append(
                continuous_metrics(trial))
    pairs = [(spec, off, arms) for (spec, off), arms in sorted(by_key.items())
             if arms[base] and arms[other]
             and not (exclude_specs and spec in exclude_specs)]
    rows = []
    for metric, higher_better, label in METRICS:
        base_values: list[float] = []
        other_values: list[float] = []
        better = worse = tie = 0
        for _spec, _off, arms in pairs:
            b_group = [m[metric] for m in arms[base] if m[metric] is not None]
            o_group = [m[metric] for m in arms[other] if m[metric] is not None]
            if not b_group or not o_group:
                continue
            b = sum((1 if x else 0) if isinstance(x, bool) else x for x in b_group) / len(b_group)
            o = sum((1 if x else 0) if isinstance(x, bool) else x for x in o_group) / len(o_group)
            base_values.append(b)
            other_values.append(o)
            advantage = (o - b) if higher_better else (b - o)
            if advantage > 1e-9:
                better += 1
            elif advantage < -1e-9:
                worse += 1
            else:
                tie += 1
        rows.append({
            "metric": metric, "label": label, "pairs": len(base_values),
            "base_mean": statistics.mean(base_values) if base_values else float("nan"),
            "other_mean": statistics.mean(other_values) if other_values else float("nan"),
            "better": better, "worse": worse, "tie": tie,
            "p": mcnemar_exact_p(worse, better) if metric == "queen_shaved" else None,
        })
    details = []
    for spec, off, arms in pairs:
        b = [m["queen_shaved"] for m in arms[base]]
        o = [m["queen_shaved"] for m in arms[other]]
        details.append((spec, off, sum(b) / len(b), sum(o) / len(o)))
    return {"rows": rows, "details": details, "pairs": len(pairs),
            "not_comparable": sum(1 for _key, arms in by_key.items()
                                  if not arms[base] or not arms[other])}


def parse_run_labels(entries: list[str]) -> tuple[list[str], list[str]]:
    """Split `--run NAME=DIR` into (dirs, labels).

    A candidate panel run under a different -AgentScript still writes arm "base" into its own result
    file, so a label is what lets it be paired entry by entry against the reference panel. A bare
    directory (no "=" or an existing path) keeps an empty label, and the first unlabeled pass becomes
    the reference.
    """
    dirs, labels = [], []
    for entry in entries:
        label, separator, target = entry.partition("=")
        if separator and not Path(entry).is_dir() and not Path(entry).is_file():
            labels.append(label)
            dirs.append(target)
        else:
            labels.append("")
            dirs.append(entry)
    return dirs, labels


def render_continuous_comparison(comparison: dict, base_name: str, other_name: str,
                                flagged: dict[str, list] | None = None,
                                clean: dict | None = None) -> list[str]:
    """paired_continuous の結果を EVALUATION.md の局所検証表として描く（主信号に精密p）。"""
    lines = [f"同じ entry（spec と offset）で配对できた組: {comparison['pairs']}"
             f"（比較不能 {comparison['not_comparable']}）", "",
             "| 指標 | 比較組 | base 平均 | %s 平均 | 候補が優る | base が優る | 同値 | 精密p (両側) |"
             % other_name,
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in comparison["rows"]:
        p_value = "–" if row["p"] is None else f"{row['p']:.3f}"
        lines.append(f"| {row['label']} | {row['pairs']} | {row['base_mean']:.3f} | "
                     f"{row['other_mean']:.3f} | {row['better']} | {row['worse']} | {row['tie']} | "
                     f"{p_value} |")
    lines += ["", f"| spec | offset | {base_name} 削り | {other_name} 削り | 向き |",
              "| --- | --- | --- | --- | --- |"]
    flagged = flagged or {}
    for spec, off, b_value, o_value in comparison["details"]:
        arrow = "+" if o_value > b_value else "-" if o_value < b_value else "="
        mark = "†" if spec in flagged else ""
        lines.append(f"| {spec}{mark} | {off} | {b_value:.0%} | {o_value:.0%} | {arrow} |")
    lines += ["", "- 判定は Queen削り割合の列で見る。Amalgam は Queen の進捗に合算していない"
              "（EVALUATION.md の召喚物の扱い）。勝敗の表はこの節の上にある補助。"]
    if flagged:
        lines.append(f"- † 付き spec は入室時の挙動が run 側の状態に依存するレリックを持つ "
                     f"{len(flagged)} 件（{', '.join(sorted(flagged)[:6])}）。lab の入場状態が実走と"
                     "ズレると分かっているもので、† を除いた数が下の clean 行。")
    if clean is not None:
        primary = next((row for row in clean["rows"] if row["metric"] == "queen_shaved"), None)
        if primary:
            lines.append(f"- † を除いた主信号の配对 {primary['pairs']} 組: 候補が優る "
                         f"{primary['better']} / base が優る {primary['worse']} / 同値 "
                         f"{primary['tie']}（精密p {primary['p']:.3f}）。"
                         f"† のレリック: {', '.join(sorted({r for names in flagged.values() for r in names})[:6])}")
    return lines


def summarize_continuous(trials: list[dict]) -> dict:
    """1つの arm の連続指標を要約する（母数が小さいので中央値と平均を両方出す）。"""
    metrics = [continuous_metrics(trial) for trial in trials]
    if not metrics:
        return {}

    def column(key):
        return [m[key] for m in metrics if m[key] is not None]

    shaved = column("queen_shaved")
    turns = column("turns")
    lost = column("hp_lost")
    return {
        "n": len(metrics),
        "shaved_mean": statistics.mean(shaved) if shaved else float("nan"),
        "shaved_median": statistics.median(shaved) if shaved else float("nan"),
        "untouched": sum(1 for value in shaved if value <= 0.0),
        "killed": sum(1 for m in metrics if m["amalgam_killed"]),
        "turns_median": statistics.median(turns) if turns else float("nan"),
        "hp_lost_median": statistics.median(lost) if lost else float("nan"),
        "wins": sum(1 for m in metrics if m["won"]),
    }


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

    pass_dirs, pass_labels = parse_run_labels(args.runs or [str(HERE.parent / "data")])
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
        spec_flags = flag_specs_from_plan(planned)
        written = {t["trial_id"] for t in trials}
        written |= {dd["trial_id"] for dd in dropped if dd.get("trial_id")}
        run_infos.append({"dir": p, "planned": planned, "spec_flags": spec_flags,
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
        if is_queen_panel(trials):
            out += ["", f"### パス {pi}: Act 3 連続指標（主信号 = Queen 400HP の削り割合。"
                        "勝敗は補助）", ""]
            for a in arms:
                summary = summarize_continuous([t for t in trials if t["_arm"] == a])
                if not summary:
                    continue
                out.append(
                    f"- arm {a}: 試行 {summary['n']} · Queen削り 中央値 {summary['shaved_median']:.0%} / "
                    f"平均 {summary['shaved_mean']:.0%} · 削れず終了 {summary['untouched']}本 · Amalgam撃破 "
                    f"{rate(summary['killed'], summary['n'])} · 死亡ターン中央値 "
                    f"{summary['turns_median']:.0f} · 失ったHP中央値 {summary['hp_lost_median']:.0f} · "
                    f"勝ち {rate(summary['wins'], summary['n'])}")
            for other in [a for a in arms if a != args.base]:
                comparison = paired_continuous(trials, args.base, other)
                flags = info["spec_flags"]
                clean = (paired_continuous(trials, args.base, other, exclude_specs=set(flags))
                         if flags else None)
                out += ["", f"#### {other} vs {args.base}（同じ entry での配对比較）", ""]
                out += render_continuous_comparison(comparison, args.base, other, flags, clean)
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
        if is_queen_panel(trials):
            out.append("- この panel は QUEEN 戦で、base 側の実走勝率は約7%の床。上の 40% は Act 2 の"
                       "母集団値なので、勝敗の一致・不一致より上の連続指標（Queen削り割合）を主信号に"
                       "読む。")
        if drift_lines:
            out.append("- ずれの内訳:")
            out.extend(drift_lines)

    reference = next((index for index, label in enumerate(pass_labels) if not label), 0)
    for index, label in enumerate(pass_labels):
        if index == reference or not pass_trials[index] or not is_queen_panel(pass_trials[index]):
            continue
        prefix = f"{label}/" if label else ""
        merged = list(pass_trials[reference]) + [
            dict(trial, _arm=f"{prefix}{trial['_arm']}") for trial in pass_trials[index]]
        ref_arms = sorted({trial["_arm"] for trial in pass_trials[reference]})
        cand_arms = sorted({f"{prefix}{trial['_arm']}" for trial in pass_trials[index]})
        for arm in cand_arms:
            original = arm[len(prefix):] if prefix else arm
            if original not in ref_arms:
                continue
            flags = dict(run_infos[reference].get("spec_flags") or {})
            for key, value in (run_infos[index].get("spec_flags") or {}).items():
                flags.setdefault(key, value)
            comparison = paired_continuous(merged, original, arm)
            clean = (paired_continuous(merged, original, arm, exclude_specs=set(flags))
                     if flags else None)
            display = label if (label and original == args.base) else arm
            out += ["", f"## パス {index} 候補 vs パス {reference} base"
                        f"{'（' + label + '）' if label else ''}"
                        "（同じ spec・offset で配对。主信号 = Queen削り割合）", ""]
            out += render_continuous_comparison(comparison, original, display, flags, clean)

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
