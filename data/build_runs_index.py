#!/usr/bin/env python3
"""Index every run artifact in data/ into one JSON file.

Read-only with respect to the artifacts: this script only stats files, reads the
small record files (manifest / runmeta / result) and the tail of the runner
stdout logs.  It writes a single output file (data/runs_index.json by default).

Run layout: a run is identified by (panel, seed), encoded in the file name as
``<panel>_<SEED>_<kind>`` where SEED is 10 upper-case alphanumerics.  Panel
names contain underscores, so the panel is whatever precedes the seed token.
"""
import argparse
import json
import os
import re
import sys
import time

SEED_RE = re.compile(r"^(?P<panel>.+)_(?P<seed>[0-9A-Za-z]{10})_(?P<kind>.+)$")
ROOM_RE = re.compile(r"Entering (\w+) room \(Act (\d+), Floor (\d+)\)")
FAIL_RE = re.compile(r"\[ERROR\].*?seed=(\S+?):\s*(.+)")
EID_RE = re.compile(r"\bseed=([0-9A-Za-z]{10})\b")

# kinds that are the run record rather than raw output
RECORD_KINDS = {"manifest.json", "runmeta.json", "result.json"}

# older ad-hoc runs predate the "<panel>_<seed>_" convention and were named
# "<label>_<kind>" without a seed; these suffixes identify the kind so the
# label can still be recovered.
KNOWN_KINDS = (
    "attempt1_stdout.log", "attempt1_mod.log", "attempt1_runmeta.json",
    "observations.jsonl", "visible_trace.jsonl", "trace.jsonl", "agent.jsonl",
    "map_ACT.HIVE.json", "map_ACT.GLORY.json", "map_ACT.UNDERDOCKS.json",
    "map.json", "result.json", "runmeta.json", "manifest.json", "plan.json",
    "log.txt", "stdout.log", "mod.log", "errors.log", "agent.err",
    "runner.log", "game.log",
)


def kind_of(rest, name):
    """Split the post-seed file name into (kind, is_record, is_attempt_variant)."""
    attempt = ""
    m = re.match(r"^(attempt\d+)_(.+)$", rest)
    if m:
        attempt, rest = m.group(1), m.group(2)
    record = name in RECORD_KINDS
    kind = rest
    if attempt:
        kind = f"{attempt}/{rest}"
    return kind, record


def read_json(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def read_tail(path, size=8192):
    try:
        with open(path, "rb") as f:
            try:
                f.seek(-size, os.SEEK_END)
            except OSError:
                f.seek(0)
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def split_name(name):
    """Return (run_key, panel, seed, kind, is_record) or None for non-artifacts.

    Newer runs use ``<panel>_<SEED>_<kind>``; older ad-hoc runs use
    ``<label>_<kind>`` with no seed, and ``<label>_<SEED>_<kind>`` still parses
    through the seed branch.
    """
    m = SEED_RE.match(name)
    if m:
        panel, seed, rest = m.group("panel"), m.group("seed"), m.group("kind")
        kind, record = kind_of(rest, name)
        return f"{panel}/{seed}", panel, seed, kind, record
    for suffix in sorted(KNOWN_KINDS, key=len, reverse=True):
        if not name.endswith("_" + suffix):
            continue
        label = name[: -(len(suffix) + 1)]
        if not label:
            return None
        kind, record = kind_of(suffix, name)
        return f"{label}/-", label, None, kind, record
    return None


def scan(data_dir, extra=None):
    """Index the files on disk plus (optionally) the members of old archives."""
    runs = {}
    unmatched = []
    for name in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, name)
        if not os.path.isfile(path):
            continue
        st = os.stat(path)
        parsed = split_name(name)
        if parsed is None:
            unmatched.append({"name": name, "bytes": st.st_size,
                              "mtime": int(st.st_mtime)})
            continue
        key, panel, seed, kind, record = parsed
        run = runs.setdefault(key, {
            "panel": panel,
            "seed": seed,
            "files": {},
            "bytes": 0,
            "first_mtime": st.st_mtime,
            "last_mtime": st.st_mtime,
        })
        run["files"][kind] = {"bytes": st.st_size, "mtime": int(st.st_mtime),
                              "record": record, "path": name}
        run["bytes"] += st.st_size
        run["first_mtime"] = min(run["first_mtime"], st.st_mtime)
        run["last_mtime"] = max(run["last_mtime"], st.st_mtime)

    for item in extra or ():
        name = os.path.basename(item["rel"])
        parsed = split_name(name)
        if parsed is None:
            unmatched.append({"name": name, "bytes": item["bytes"],
                              "mtime": item["mtime"], "archived_to": item["archive"]})
            continue
        key, panel, seed, kind, record = parsed
        run = runs.setdefault(key, {
            "panel": panel, "seed": seed, "files": {}, "bytes": 0,
            "first_mtime": item["mtime"], "last_mtime": item["mtime"],
        })
        run["files"][kind] = {"bytes": item["bytes"], "mtime": item["mtime"],
                              "record": record, "path": name,
                              "archived_to": item["archive"]}
        run["bytes"] += item["bytes"]
        run["first_mtime"] = min(run["first_mtime"], item["mtime"])
        run["last_mtime"] = max(run["last_mtime"], item["mtime"])
    return runs, unmatched


def archived_members(data_dir):
    """Members listed in data/_archive/INDEX.json, as scan() extras."""
    path = os.path.join(data_dir, "_archive", "INDEX.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        index = json.load(f)
    out = []
    for name, record in index.get("archives", {}).items():
        for rel, meta in record.get("members", {}).items():
            out.append({"rel": rel, "bytes": meta.get("bytes", 0),
                        "mtime": meta.get("mtime", 0),
                        "archive": record.get("path", name)})
    return out


def enrich(data_dir, run):
    """Attach the run record (manifest/runmeta/result) and log-derived outcome."""
    files = {k: v for k, v in run["files"].items()
             if os.path.exists(os.path.join(data_dir, v["path"]))}
    manifest = None
    if "manifest.json" in files:
        raw = read_json(os.path.join(data_dir, files["manifest.json"]["path"]))
        if isinstance(raw, dict):
            manifest = {
                "source_commit": raw.get("source_commit"),
                "simulations": raw.get("simulations"),
                "arm": raw.get("arm"),
                "plan_sha256": raw.get("plan_sha256"),
                "runner_sha256": raw.get("runner_sha256"),
                "source_unchanged": raw.get("source_unchanged"),
                "outcome": raw.get("outcome"),
            }
    runmeta = None
    if "runmeta.json" in files:
        raw = read_json(os.path.join(data_dir, files["runmeta.json"]["path"]))
        if isinstance(raw, dict):
            started, finished = raw.get("started"), raw.get("finished")
            runmeta = {
                "exit": raw.get("exit"),
                "started": started,
                "finished": finished,
                "duration_s": (finished - started
                               if isinstance(started, int) and isinstance(finished, int)
                               else None),
            }
    result = None
    if "result.json" in files:
        raw = read_json(os.path.join(data_dir, files["result.json"]["path"]))
        if isinstance(raw, dict):
            result = {
                "game_version": raw.get("game_version"),
                "act_1_complete": raw.get("act_1_complete"),
                "act_2_complete": raw.get("act_2_complete"),
                "act_3_complete": raw.get("act_3_complete"),
                "hp": raw.get("hp"),
                "max_hp": raw.get("max_hp"),
                "gold": raw.get("gold"),
                "deck_size": len(raw.get("deck") or []),
                "relics": len(raw.get("relics") or []),
            }
    # outcome fallback: the tail of the runner stdout carries the furthest room
    # and the fatal error line when no manifest recorded the run.
    log_kind = "stdout.log" if "stdout.log" in files else None
    tail = {}
    if log_kind:
        text = read_tail(os.path.join(data_dir, files[log_kind]["path"]))
        rooms = ROOM_RE.findall(text)
        if rooms:
            room, act, floor = rooms[-1]
            tail["furthest_act"] = int(act)
            tail["furthest_floor"] = int(floor)
            tail["furthest_room"] = room
        fails = FAIL_RE.findall(text)
        if fails:
            tail["error"] = fails[-1][1][:200]
        seeds = EID_RE.findall(text)
        if seeds:
            tail["log_seed"] = seeds[-1]
    run["manifest"] = manifest
    run["runmeta"] = runmeta
    run["result"] = result
    run["derived"] = tail
    run["date"] = time.strftime("%Y-%m-%d", time.localtime(run["last_mtime"]))
    run["arm"] = (manifest or {}).get("arm")
    run["outcome"] = ((manifest or {}).get("outcome") or {}).get("status")
    if run["outcome"] is None and result is not None:
        run["outcome"] = ("result_act3" if result.get("act_3_complete")
                          else "result_act2" if result.get("act_2_complete")
                          else "result_act1" if result.get("act_1_complete")
                          else "result_partial")
    run["first_mtime"] = int(run["first_mtime"])
    run["last_mtime"] = int(run["last_mtime"])
    return run


def summarize(runs, unmatched, data_dir):
    panels = {}
    for run in runs.values():
        p = panels.setdefault(run["panel"], {
            "runs": 0, "seeds": [], "bytes": 0,
            "first": None, "last": None,
            "with_manifest": 0, "with_result": 0, "with_runmeta": 0,
        })
        p["runs"] += 1
        if run["seed"]:
            p["seeds"].append(run["seed"])
        p["bytes"] += run["bytes"]
        d = run["date"]
        p["first"] = d if p["first"] is None else min(p["first"], d)
        p["last"] = d if p["last"] is None else max(p["last"], d)
        p["with_manifest"] += 1 if run["manifest"] else 0
        p["with_result"] += 1 if run["result"] else 0
        p["with_runmeta"] += 1 if run["runmeta"] else 0
    for p in panels.values():
        p["seeds"].sort()
    total_bytes = sum(r["bytes"] for r in runs.values())
    return {
        "generated": int(time.time()),
        "generated_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "data_dir": os.path.abspath(data_dir),
        "totals": {
            "runs": len(runs),
            "panels": len(panels),
            "bytes": total_bytes,
            "unmatched_files": len(unmatched),
            "unmatched_bytes": sum(u["bytes"] for u in unmatched),
        },
        "panels": panels,
    }


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=here, help="artifact directory (default: this one)")
    ap.add_argument("--out", default=os.path.join(here, "runs_index.json"))
    ap.add_argument("--pretty", action="store_true", default=True)
    args = ap.parse_args(argv)

    runs, unmatched = scan(args.dir, archived_members(args.dir))
    for run in runs.values():
        enrich(args.dir, run)
    index = summarize(runs, unmatched, args.dir)
    index["runs"] = [runs[k] for k in sorted(runs)]
    index["unmatched"] = sorted(unmatched, key=lambda u: u["name"])

    tmp = args.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    os.replace(tmp, args.out)

    t = index["totals"]
    print(f"runs={t['runs']} panels={t['panels']} bytes={t['bytes']:,} "
          f"unmatched={t['unmatched_files']} ({t['unmatched_bytes']:,} B)")
    print(f"wrote {args.out} ({os.path.getsize(args.out):,} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
