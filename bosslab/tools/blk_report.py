#!/usr/bin/env python3
"""Judge the Block-add plan (base / add2 / add4 inside ONE run dir per panel) once, mechanically.

Entry point for the pre-registration bosslab/results/act3_blk_prereg.md. For add2 and add4 against base it
computes paired deltas (analyze_bosslab via apply_hybrid_rule.candidate_delta) on the dev and confirm
panels, the firing prerequisite G' (a spec "fires" when the add arm played CARD.SHRUG_IT_OFF plus
CARD.FLAME_BARRIER more times in total than the base arm, counted from trial_XXXX_agent.jsonl), and the
verdict from apply_hybrid_rule.judge_candidate with G' fed where firing_C was fed. Mapping:
採用 = 効く, 保留 = 判定できない, 不採用 = 効かない. Pairs missing a usable trial on either arm (stalled,
errored, dropped) are listed as "pairing incomplete" and counted into not_comparable. A confirm dir that does
not exist yet is printed as 未実行 and the verdict is provisional. Do not tune the rule from this output.

Usage: python3 blk_report.py --dev DIR --confirm DIR [--out FILE]
"""
import argparse
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS))
import analyze_bosslab as A  # noqa: E402
import apply_hybrid_rule as H  # noqa: E402

BASE = H.BASE_LABEL
ADD_ARMS = ("add2", "add4")
BLOCK_CARDS = ("CARD.SHRUG_IT_OFF", "CARD.FLAME_BARRIER")
MAPPING = {"採用": "効く", "保留": "判定できない", "不採用": "効かない"}


def _trace_plays(path: Path) -> int | None:
    """Total plays of the added Block cards in one agent trace; None when the trace file is absent."""
    if not path.is_file():
        return None
    return sum(1 for row in A.trace_rows(path)
               if row.get("type") == "card" and row.get("card_id") in BLOCK_CARDS)


def _plan_known(run_dir: Path) -> bool:
    try:
        return bool(A.load_dir_trials(run_dir)[1]["planned"])
    except Exception:
        return False


def _expected_keys(run_dir: Path, usable: list, dropped: list) -> set:
    """(spec, offset) entries that should exist: usable rows, dropped rows, and the plan if lab_meta names one."""
    keys = {(r["spec_id"], r["_offset"]) for r in usable}
    for d in dropped:
        parts = (d.get("trial_id") or "").split("|")
        if len(parts) == 3:
            keys.add((parts[0], parts[2]))
    try:
        _t, info = A.load_dir_trials(run_dir)
        for t in info["planned"]:
            parts = t["trial_id"].split("|")
            keys.add((parts[0], parts[2]))
    except Exception:  # plan is optional context; a broken lab_meta must not hide the results
        pass
    return keys


def panel(run_dir: Path) -> dict:
    """Per-arm deltas, firing and incomplete pairs for one run dir (arms read from each row's trial_id)."""
    usable, dropped = A.load_trials([run_dir / "lab_results.jsonl"])
    expected = _expected_keys(run_dir, usable, dropped)
    by_arm_key = {(r["_arm"], r["spec_id"], r["_offset"]): r for r in usable}
    out = {}
    for arm in ADD_ARMS:
        if not any(r["_arm"] == arm for r in usable):
            out[arm] = None
            continue
        d = H.candidate_delta(usable, BASE, arm)
        incomplete = sorted(k for k in expected
                            if (BASE, *k) not in by_arm_key or (arm, *k) not in by_arm_key)
        d["not_comparable"] = len(incomplete)
        pc = A.paired_continuous(usable, BASE, arm)
        turns = next(r for r in pc["rows"] if r["metric"] == "turns")
        d["turns"] = {k: turns[k] for k in ("base_mean", "other_mean", "better", "worse", "tie")}
        fired, skipped, detail = 0, 0, []
        for key in sorted(k for k in expected if k not in incomplete):
            b = _trace_plays(run_dir / f"trial_{by_arm_key[(BASE, *key)]['trial_index']:04d}_agent.jsonl")
            a = _trace_plays(run_dir / f"trial_{by_arm_key[(arm, *key)]['trial_index']:04d}_agent.jsonl")
            if b is None or a is None:
                skipped += 1
                continue
            detail.append((key[0], key[1], b, a))
            fired += 1 if a > b else 0
        out[arm] = {"delta": d, "incomplete": incomplete,
                    "complete": bool(not incomplete and d["not_comparable"] == 0 and _plan_known(run_dir)),
                    "fire": {"pairs": len(detail), "fired": fired, "skipped_missing_trace": skipped,
                             "detail": detail}}
    return out


def _fmt_turns(t: dict) -> str:
    return (f"生存ターン {t['base_mean']:.2f}→{t['other_mean']:.2f}"
            f"（add優{t['better']}/base優{t['worse']}/同値{t['tie']}）")


def render(dev_dir: Path, conf_dir: Path, dev: dict, conf: dict | None) -> str:
    L = ["# Block札追加の判定（base / add2 / add4、G' + 4693f2e 規則）", "",
         f"dev: {dev_dir}　confirm: {conf_dir}" + ("" if conf is not None else "（未実行）"), "",
         f"G' = addアームの {' + '.join(BLOCK_CARDS)} 使用回数がbaseを超えた組。閾値 {H.G_THRESHOLD} 組（dev 6組中、confirm 12組中）。", ""]
    for arm in ADD_ARMS:
        dv = dev.get(arm)
        cf = conf.get(arm) if conf is not None else None
        L.append(f"## {arm} vs base")
        if dv is None:
            L += ["", "dev に実行データ無し（判定不能）", ""]
            continue
        dev_delta = dv["delta"]
        note = None
        if cf is not None:
            if dv["complete"] and cf["complete"]:
                dev_delta = dict(dev_delta, pairs=cf["delta"]["pairs"])
                note = "条件6の読み替え（追記）: dev・confirm とも計画した組が全て揃い比較不能0。dev の pairs を confirm に合わせて判定した。"
            else:
                note = "条件6の読み替え（追記）は不適用: 組が欠けている panel があるため、数値をそのまま渡した（条件6は不充足になり得る）。"
        res = H.judge_candidate(dev_delta, cf["delta"] if cf else None,
                                dv["fire"], cf["fire"] if cf else None)
        L += ["", f"- 第2段階の読み替え: **{MAPPING[res['verdict']]}**"
              + ("（暫定: confirm 未実行）" if conf is None or cf is None else ""), ""]
        L.append(H.format_candidate_report(arm, res).replace("firing_C", "G'発火").replace("前提 G", "前提 G'"))
        L.append("")
        for tag, p in (("dev", dv), ("confirm", cf)):
            if p is None:
                L.append(f"- {tag}: 未実行")
                continue
            f = p["fire"]
            L.append(f"- {tag}: {_fmt_turns(p['delta']['turns'])}　G'発火 {f['fired']}/{f['pairs']}組"
                     f"（trace欠落 {f['skipped_missing_trace']}）")
            if p["incomplete"]:
                L.append(f"  - **pairing incomplete**: {len(p['incomplete'])}組が片アーム欠落"
                         f"（not_comparableに計上）: " + ", ".join(f"{s}|{o}" for s, o in p["incomplete"]))
            for s, o, b, a in f["detail"]:
                L.append(f"  - {s}|{o}: Block札使用 base {b} → {arm} {a}{' [発火]' if a > b else ''}")
        if note:
            L.append("- " + note)
        L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Block-add plan verdict (prereg act3_blk_prereg.md).")
    ap.add_argument("--dev", required=True)
    ap.add_argument("--confirm", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    dev_dir, conf_dir = Path(args.dev), Path(args.confirm)
    if not (dev_dir / "lab_results.jsonl").is_file():
        raise SystemExit(f"dev に lab_results.jsonl が無い: {dev_dir}")
    dev = panel(dev_dir)
    conf = panel(conf_dir) if (conf_dir / "lab_results.jsonl").is_file() else None
    text = render(dev_dir, conf_dir, dev, conf)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
