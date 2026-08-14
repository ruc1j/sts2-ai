#!/usr/bin/env python3
"""Scan tonight's run_multi_* artifacts and render a battle-record dashboard."""
import glob
import html
import json
import os
import re
import sys

CUTOFF = 1786724580  # 2026-08-15 01:23 JST-ish, start of tonight's session
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(DATA_DIR, "dashboard.html")

ROOM_RE = re.compile(r"Entering (\w+) room \(Act (\d+), Floor (\d+)\)")
FAIL_RE = re.compile(r"\[ERROR\] \[AutoSlay\] Run failed with seed=(\S+): (.+)")


def find_tags():
    tags = set()
    for path in glob.glob(os.path.join(DATA_DIR, "run_multi_*_trace.jsonl")):
        if os.path.getmtime(path) >= CUTOFF:
            tag = os.path.basename(path)[len("run_multi_"):-len("_trace.jsonl")]
            tags.add(tag)
    return sorted(tags, key=lambda t: os.path.getmtime(os.path.join(DATA_DIR, f"run_multi_{t}_trace.jsonl")))


def parse_run(tag):
    log_path = os.path.join(DATA_DIR, f"run_multi_{tag}_log.txt")
    trace_path = os.path.join(DATA_DIR, f"run_multi_{tag}_trace.jsonl")
    info = {
        "tag": tag,
        "seed": None,
        "furthest": None,
        "outcome": "in_progress",
        "detail": "",
        "furthest_act": None,
        "furthest_room": None,
        "mtime": os.path.getmtime(trace_path) if os.path.exists(trace_path) else 0,
    }
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        seed_m = re.search(r"seed=(\S+)", text)
        if seed_m:
            info["seed"] = seed_m.group(1)
        rooms = ROOM_RE.findall(text)
        if rooms:
            room, act, floor = rooms[-1]
            info["furthest"] = f"Act{act} F{floor} ({room})"
            info["furthest_act"] = int(act)
            info["furthest_room"] = room
        fail_m = FAIL_RE.search(text)
        if fail_m:
            info["outcome"] = "error"
            info["detail"] = fail_m.group(2)[:160]
    won_line, last_enemy = None, None
    if os.path.exists(trace_path):
        with open(trace_path, encoding="utf-8", errors="replace") as f:
            lines = [line for line in f if line.strip()]
        for line in reversed(lines):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("phase") == "combat" and last_enemy is None and obj.get("enemies"):
                last_enemy = obj["enemies"]
            if obj.get("phase") == "combat_end" and won_line is None:
                won_line = obj
            if won_line is not None and last_enemy is not None:
                break
        if not info["seed"]:
            for line in lines:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("seed"):
                    info["seed"] = obj["seed"]
                    break
        if lines:
            try:
                last = json.loads(lines[-1])
                if last.get("terminal"):
                    info["outcome"] = "cleared"
            except json.JSONDecodeError:
                pass
    # A dead player often trips the GameOverScreen watchdog before the harness notices the
    # loss cleanly - trust the trace's own combat_end record over that log-level noise.
    if won_line is not None and won_line.get("won") is False and won_line.get("hp", 1) <= 0:
        info["outcome"] = "loss"
        boss = ", ".join(f"{e['id'].replace('MONSTER.', '')} (hp={e['hp']})" for e in (last_enemy or []))
        info["detail"] = f"vs {boss}" if boss else info["detail"]
    return info


# Ordered so the chart reads left-to-right as increasing run depth.
MILESTONE_ORDER = [
    "エラー",
    "Act1道中死", "Act1ボスで死", "Act2道中死", "Act2ボスで死", "Act3道中死", "Act3ボスで死",
    "クリア", "進行中",
]


def milestone(r):
    if r["outcome"] == "cleared":
        return "クリア"
    if r["outcome"] == "error":
        return "エラー"
    if r["outcome"] == "loss":
        act = r["furthest_act"] or 1
        at_boss = r["furthest_room"] == "Boss"
        return f"Act{act}{'ボスで死' if at_boss else '道中死'}"
    return "進行中"


def render_chart(runs):
    counts = {label: 0 for label in MILESTONE_ORDER}
    for r in runs:
        counts[milestone(r)] += 1
    peak = max(counts.values(), default=0) or 1
    colors = {
        "エラー": "#ef6c00", "進行中": "#1565c0", "クリア": "#2e7d32",
    }
    bars = []
    for label in MILESTONE_ORDER:
        n = counts[label]
        if n == 0 and label not in ("進行中",):
            continue
        height = round(120 * n / peak) if n else 4
        color = colors.get(label, "#c62828" if "死" in label else "#555")
        bars.append(f"""
        <div class="bar-col">
          <div class="bar-count">{n}</div>
          <div class="bar" style="height:{height}px;background:{color}"></div>
          <div class="bar-label">{html.escape(label)}</div>
        </div>""")
    return f'<div class="chart">{"".join(bars)}</div>'


def render(runs):
    rows = []
    for r in runs:
        badge = {
            "cleared": ("#2e7d32", "CLEARED"),
            "loss": ("#c62828", "LOSS"),
            "error": ("#ef6c00", "ERROR"),
            "in_progress": ("#1565c0", "IN PROGRESS"),
        }[r["outcome"]]
        rows.append(f"""
        <tr>
          <td><code>{html.escape(r['tag'])}</code></td>
          <td><code>{html.escape(r['seed'] or '?')}</code></td>
          <td>{html.escape(r['furthest'] or '-')}</td>
          <td><span class="badge" style="background:{badge[0]}">{badge[1]}</span></td>
          <td class="detail">{html.escape(r['detail'])}</td>
        </tr>""")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="120">
<title>sts2-ai 戦績</title>
<style>
body {{ font-family: -apple-system, sans-serif; background:#111; color:#eee; margin:2rem; }}
h1 {{ font-size:1.4rem; }}
table {{ border-collapse: collapse; width:100%; margin-top:1rem; }}
th, td {{ padding:0.5rem 0.8rem; border-bottom:1px solid #333; text-align:left; font-size:0.9rem; }}
th {{ color:#aaa; font-weight:600; }}
code {{ background:#222; padding:2px 5px; border-radius:3px; }}
.badge {{ color:#fff; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:600; }}
.detail {{ color:#999; font-size:0.8rem; }}
.meta {{ color:#888; font-size:0.85rem; }}
.chart {{ display:flex; align-items:flex-end; gap:1.2rem; height:170px; margin-top:1rem; border-bottom:1px solid #333; padding-bottom:0.5rem; }}
.bar-col {{ display:flex; flex-direction:column; align-items:center; justify-content:flex-end; height:100%; }}
.bar {{ width:34px; border-radius:4px 4px 0 0; }}
.bar-count {{ font-size:0.85rem; color:#ccc; margin-bottom:2px; }}
.bar-label {{ font-size:0.72rem; color:#999; margin-top:6px; writing-mode:horizontal-tb; text-align:center; max-width:60px; }}
</style></head><body>
<h1>Slay the Spire 2 AI - 本日の戦績</h1>
<p class="meta">2分ごとに自動更新されます。件数: {len(runs)}</p>
{render_chart(runs)}
<table>
<tr><th>run</th><th>seed</th><th>到達地点</th><th>結果</th><th>備考</th></tr>
{''.join(rows)}
</table>
</body></html>"""


def main():
    tags = find_tags()
    runs = [parse_run(tag) for tag in tags]
    runs.sort(key=lambda r: r["mtime"])
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(render(runs))
    print(f"wrote {OUT_PATH} ({len(runs)} runs)")


if __name__ == "__main__":
    sys.exit(main())
