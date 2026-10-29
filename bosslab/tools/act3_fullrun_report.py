#!/usr/bin/env python3
"""Act 3 full-run panel report: per-run outcomes + Wilson intervals + deck strata.

Input is one or more run-tags (prefixes of the panel artifact names, e.g.
``astra_ctrl_v23 astra_ctrl_v24``). For every run the tool reads the agent trace
(``<tag>_<seed>_agent.jsonl``) and derives the outcome directly from the trace, so it works before a
manifest exists (``astra_ctrl_v24`` manifests are written only after the panel finishes). A run counts
as *complete* when its ``_runmeta.json`` or ``_manifest.json`` is present; in-flight traces without
either are skipped so a still-growing panel is not half-counted.

Per run it reports: (a) entered Act 3, (b) fought the Queen boss, (c) cleared Act 3 (beat Queen),
(d) the Queen-entry state — HP / max HP / deck composition (attack, skill, power, upgraded, potions),
(e) the Queen shave fraction, (f) whether Amalgam was killed, (g) the turn the run died on.

Aggregate over the completed runs of the given tags: Wilson 95% intervals for the enter / Queen-reached
/ clear / Amalgam-kill rates, medians and quartiles for Queen shave and death turn, and deck strata
split at the median (skill count, upgraded count, entry HP), each shown with its sample size. Group
differences are descriptive only — no significance or causality is claimed. When two tags are given the
tool also prints the same metrics per tag, as a check on whether their distributions look poolable.

The Queen shave and Amalgam-kill numbers reuse ``analyze_bosslab.hp_removed_from_trace``: a monster that
left the board is telescoped up to its maximum HP (no overkill), so the Amalgam counts as killed exactly
when its removed HP reaches its maximum (i.e. it is absent from the last Queen-combat row). Deck card
types come from the cards each run showed in hand (draw-pile cards carry ``type: null``), so a card that
was never drawn that run stays an unknown type.

Run from the repository root, e.g.:
    python3 bosslab/tools/act3_fullrun_report.py \
        --data-dir /Users/mao/workspace/sts2-ai/data \
        --prefix astra_ctrl_v23 --out bosslab/results/act3_fullrun_report_v23.md
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_bosslab as A  # noqa: E402  (hp_removed_from_trace + boss id suffixes)

QUEEN_SUFFIX = A.QUEEN_ID_SUFFIX       # ".QUEEN"
AMALGAM_SUFFIX = A.AMALGAM_ID_SUFFIX   # "TORCH_HEAD_AMALGAM"
ACT3 = 2                               # run.act is 0-based; 2 == Act 3


def read_rows(path: Path) -> list:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def queen_fight(rows: list) -> tuple:
    """(combat rows of the Queen fight, cleared?) from the first Queen row to that fight's combat_end.

    A Queen fight can have non-combat rows interleaved (an event or interaction mid-fight), so we scan
    past them and stop only at the combat_end that closes the fight. Combat rows feed the HP-removed
    telescoping; the combat_end gives whether the player won (cleared Act 3)."""
    start = next((i for i, row in enumerate(rows)
                  if row.get("phase") == "combat"
                  and any(str(e.get("id", "")).endswith(QUEEN_SUFFIX) for e in row.get("enemies") or [])), None)
    if start is None:
        return [], False
    qrows, won = [], False
    for row in rows[start:]:
        phase = row.get("phase")
        if phase == "combat_end":
            won = row.get("won") is True
            break
        if phase == "combat":
            qrows.append(row)
    return qrows, won


def entered_act3(rows: list) -> bool:
    return any((row.get("run") or {}).get("act", -1) >= ACT3 for row in rows)


def build_type_map(trace_paths: list) -> dict:
    """Panel-wide card id -> type, unioned from every card each run showed in hand.

    Draw-pile cards carry ``type: null``, so the type reference is assembled across the whole panel;
    a card that was never in hand in any run of this panel stays an unknown type."""
    type_by_id = {}
    for path in trace_paths:
        for row in read_rows(path):
            for card in row.get("hand") or []:
                cid, ctype = card.get("id"), card.get("type")
                if cid and ctype:
                    type_by_id[cid] = ctype
    return type_by_id


def _deck_from_entry(entry: dict, type_map: dict) -> dict:
    """Queen-entry deck composition, typed with the panel-wide hand-observed type table."""
    counts = Counter({"Attack": 0, "Skill": 0, "Power": 0, "unknown": 0})
    upgraded = 0
    total = 0
    for key in ("hand", "draw_pile", "discard_pile", "exhaust_pile"):
        for card in entry.get(key) or []:
            total += 1
            counts[type_map.get(card.get("id"), "unknown")] += 1
            if (card.get("upgrade") or 0) >= 1:
                upgraded += 1
    counts["deck_total"] = total
    counts["upgraded"] = upgraded
    counts["potions"] = len(entry.get("potions") or [])
    return dict(counts)


def analyze_run(seed: str, agent_path: Path, type_map: dict) -> dict:
    """Derive one run's outcome from its trace (no manifest required)."""
    rows = read_rows(agent_path)
    out = {"seed": seed, "entered": entered_act3(rows)}
    qrows, won = queen_fight(rows)
    out["fought_queen"] = bool(qrows)
    if not qrows:
        out["cleared"] = None
        out["queen_entry"] = None
        out["shave"] = None
        out["amalgam_killed"] = None
        return out
    entry = qrows[0]
    player = entry.get("player") or {}
    enemies = {str(e.get("id")): e for e in entry.get("enemies") or []}
    queen = next((e for i, e in enemies.items() if i.endswith(QUEEN_SUFFIX)), None)
    amalgam = next((e for i, e in enemies.items() if i.endswith(AMALGAM_SUFFIX)), None)
    out["cleared"] = won
    out["queen_entry"] = {
        "hp": player.get("hp"),
        "max_hp": player.get("max_hp"),
        "deck": _deck_from_entry(entry, type_map),
    }
    if queen:
        removed = A.hp_removed_from_trace(qrows, QUEEN_SUFFIX) or 0
        out["shave"] = round(removed / float(queen.get("max_hp") or 1), 4)
    else:
        out["shave"] = None
    if amalgam:
        # Killed == Amalgam is gone from the fight's last combat row (it may have entered already
        # damaged, so removed-HP- reaching-max is not a reliable kill test; presence in the last row is).
        last = qrows[-1].get("enemies") or []
        out["amalgam_killed"] = not any(str(e.get("id", "")).endswith(AMALGAM_SUFFIX) for e in last)
    else:
        out["amalgam_killed"] = None
    out["death_turn"] = None if out["cleared"] else qrows[-1].get("turn")
    return out


def _is_complete(data_dir: Path, prefix: str, seed: str) -> bool:
    stem = data_dir / f"{prefix}_{seed}"
    return (stem.with_name(stem.name + "_runmeta.json")).exists() or (stem.with_name(stem.name + "_manifest.json")).exists()


def collect_runs(data_dir: Path, prefixes: list) -> list:
    """Complete runs for the given tags, one record per (prefix, seed), typed with a panel-wide table."""
    found = []
    for prefix in prefixes:
        for path in sorted(data_dir.glob(f"{prefix}_*_agent.jsonl")):
            seed = path.name[len(prefix) + 1:-len("_agent.jsonl")]
            if not _is_complete(data_dir, prefix, seed):
                continue
            found.append((prefix, seed, path))
    type_map = build_type_map([p for _, _, p in found])
    runs = []
    for prefix, seed, path in found:
        rec = analyze_run(seed, path, type_map)
        rec["tag"] = prefix
        runs.append(rec)
    return runs


# --- statistics ---------------------------------------------------------------
def wilson(k: int, n: int, z: float = 1.96) -> tuple:
    """Wilson 95% score interval for k/n, returned as (low, high) percentages."""
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n
    denom = 1 + z * z / n
    centre = (ph + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return (round(100 * max(0.0, centre - half), 1), round(100 * min(1.0, centre + half), 1))


def _quartiles(values: list) -> tuple:
    """(median, q1, q3) via the inclusive statistics method; empty -> (None,None,None)."""
    if not values:
        return (None, None, None)
    if len(values) == 1:
        return (values[0], values[0], values[0])
    med = statistics.median(values)
    lower = [v for v in values if v < med]
    upper = [v for v in values if v > med]
    q1 = statistics.median(sorted(values)[:len(values) // 2]) if len(values) % 2 else statistics.median(sorted(values)[:len(values) // 2])
    q3 = statistics.median(sorted(values)[-((len(values) + 1) // 2):]) if len(values) % 2 else statistics.median(sorted(values)[len(values) // 2:])
    del lower, upper
    return (med, q1, q3)


def _fmt_pct(x):  # 0.16 -> "16%"
    return "n/a" if x is None else f"{round(100 * x)}%"


def summarize(runs: list) -> dict:
    entered = [r for r in runs if r.get("entered")]
    fought = [r for r in entered if r.get("fought_queen")]
    cleared = [r for r in fought if r.get("cleared")]
    killed = [r for r in fought if r.get("amalgam_killed") is True]
    shaves = [r["shave"] for r in fought if r.get("shave") is not None]
    deaths = [r["death_turn"] for r in fought if r.get("death_turn") is not None]
    return {
        "n_all": len(runs),
        "n_entered": len(entered), "n_fought": len(fought), "n_cleared": len(cleared), "n_killed": len(killed),
        "shave_med": (statistics.median(shaves) if shaves else None),
        "shave_q": _quartiles(shaves),
        "shave_max": max(shaves) if shaves else None,
        "death_med": (statistics.median(deaths) if deaths else None),
        "death_q": _quartiles(deaths),
        "runs": runs, "entered_runs": entered, "fought_runs": fought,
    }


def _strata(fought: list, key_fn, label: str) -> list:
    vals = [(key_fn(r), r) for r in fought if key_fn(r) is not None]
    if not vals:
        return []
    med = statistics.median([v for v, _ in vals])
    groups = []
    for name, pred in (("以上(median↑)", lambda x: x >= med), ("未満(median↓)", lambda x: x < med)):
        sub = [r for _, r in vals if pred(key_fn(r))]
        sh = [r["shave"] for r in sub if r.get("shave") is not None]
        de = [r["death_turn"] for r in sub if r.get("death_turn") is not None]
        groups.append({
            "label": f"{label} {name}", "n": len(sub), "threshold": med,
            "shave_med": (statistics.median(sh) if sh else None),
            "death_med": (statistics.median(de) if de else None),
            "killed": sum(1 for r in sub if r.get("amalgam_killed") is True),
        })
    return groups


def render(s: dict, prefixes: list) -> str:
    fought = s["fought_runs"]
    lines = ["# Act 3 フルrunパネルレポート（act3_fullrun_report.py）", ""]
    lines.append(f"- 対象 tag: {', '.join(prefixes)}  完了run {s['n_all']} 本")
    lines.append("")
    lines.append("## 段階別（Wilson 95%、母集団は標本数）")
    lines.append("")
    lines.append("| 指標 | run数 | 割合 | Wilson 95% |")
    lines.append("| --- | --- | --- | --- |")
    a = s["n_all"]
    e, q, c = s["n_entered"], s["n_fought"], s["n_cleared"]
    lines.append(f"| Act 3 進入（全run） | {e}/{a} | {round(100 * e / a) if a else 0}% | {wilson(e, a)} |")
    lines.append(f"| Queen到達（Act 3進入のうち） | {q}/{e} | {round(100 * q / e) if e else 0}% | {wilson(q, e)} |")
    lines.append(f"| 踏破（Act 3進入のうち） | {c}/{e} | {round(100 * c / e, 1) if e else 0}% | {wilson(c, e)} |")
    lines.append(f"| 踏破（全run） | {c}/{a} | {round(100 * c / a, 1) if a else 0}% | {wilson(c, a)} |")
    lines.append(f"| Amalgam撃破（Queen戦のうち） | {s['n_killed']}/{q} | {round(100 * s['n_killed'] / q) if q else 0}% | {wilson(s['n_killed'], q)} |")
    lines.append("")
    med, q1, q3 = s["shave_q"]
    lines.append("## Queen戦の終局状態（記述のみ）")
    lines.append("")
    lines.append(f"- Queen削り割合: 中央値 {_fmt_pct(med)}（四分位 {_fmt_pct(q1)}〜{_fmt_pct(q3)}、最大 {_fmt_pct(s['shave_max'])}）")
    dm, dq1, dq3 = s["death_q"]
    lines.append(f"- 死亡ターン: 中央値 {dm}（四分位 {dq1}〜{dq3}）")
    lines.append("")
    lines.append("## デッキ層別（中央値で2群、記述のみ・有意性や因果は主張しない）")
    lines.append("")
    lines.append("| 層 | run数 | Queen削り中央値 | Amalgam撃破 | 死亡ターン中央値 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for spec in (
        (lambda r: (r.get("queen_entry") or {}).get("deck", {}).get("Skill"), "Skill枚数"),
        (lambda r: (r.get("queen_entry") or {}).get("deck", {}).get("upgraded"), "強化数"),
        (lambda r: (r.get("queen_entry") or {}).get("hp"), "入場HP"),
    ):
        for g in _strata(fought, *spec):
            lines.append(f"| {g['label']} | {g['n']} | {_fmt_pct(g['shave_med'])} | {g['killed']} | {g['death_med']} |")
    lines.append("")
    lines.append("## 2 tag の分布比較（合算してよいかの確認、記述のみ）")
    lines.append("")
    tags = sorted({r.get("tag") for r in s["runs"]})
    if len(tags) > 1:
        lines.append("| tag | 完了run | Act3進入 | Queen戦 | 踏破 | Amalgam撃破 | 削り中央値 | 死亡中央値 | 入場HP中央 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for t in tags:
            sub = summarize([r for r in s["runs"] if r.get("tag") == t])
            hps = [((r.get("queen_entry") or {}).get("hp")) for r in sub["fought_runs"]]
            lines.append(f"| {t} | {sub['n_all']} | {sub['n_entered']} | {sub['n_fought']} | {sub['n_cleared']} | "
                         f"{sub['n_killed']}/{sub['n_fought']} | {_fmt_pct(sub['shave_med'])} | {sub['death_med']} | "
                         f"{statistics.median([h for h in hps if h is not None]) if any(h is not None for h in hps) else 'n/a'} |")
    else:
        lines.append("（tag が 1 つのため 2 群比較なし）")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Act 3 full-run panel report")
    ap.add_argument("--data-dir", default="data", help="directory holding <tag>_<seed>_agent.jsonl")
    ap.add_argument("--prefix", dest="prefixes", action="append", required=True,
                    help="run tag to include (repeat; e.g. --prefix astra_ctrl_v23)")
    ap.add_argument("--out", default=None, help="markdown output path (default: stdout)")
    args = ap.parse_args(argv)
    data_dir = Path(args.data_dir)
    runs = collect_runs(data_dir, args.prefixes)
    if not runs:
        print(f"no completed runs found for {args.prefixes} under {data_dir}", file=sys.stderr)
        return 1
    s = summarize(runs)
    text = render(s, args.prefixes)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}: {s['n_all']} runs, entered {s['n_entered']}, fought {s['n_fought']}, cleared {s['n_cleared']}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
