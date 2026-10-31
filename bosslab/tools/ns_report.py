#!/usr/bin/env python3
"""Judge the Act 2 'noshrug' plan (base / noshrug inside ONE run dir per panel) once, mechanically.

Entry point for the pre-registration bosslab/results/act2_ns_prereg.md. Paired deltas of noshrug against base
come from apply_hybrid_rule.candidate_delta on the dev and confirm panels (12 pairs each; condition 6 is
applied as-is, no pair-count equalising). Firing prerequisite G'': a pair fires when the BASE arm played
CARD.SHRUG_IT_OFF more times in total than the noshrug arm (agent-trace actions of type 'card'), threshold
apply_hybrid_rule.G_THRESHOLD (4) on each panel. Verdict is judge_candidate's own 採用/保留/不採用.
Pairs missing a usable trial on either arm are listed as "pairing incomplete" and counted into
not_comparable. A confirm dir that does not exist yet prints 未実行 and the verdict is provisional.

Instrument note: analyze_bosslab's "queen" metrics key on the enemy id suffix ".QUEEN" (Act 3). The Act 2 boss
is MONSTER.THE_INSATIABLE, so panel() points that suffix at the Insatiable for the duration of the call
(shave = fraction of its max HP removed, 1.0 on a win; firepower = its HP removed per survival turn, no
Amalgam term). Do not tune the rule from this output.

Usage: python3 ns_report.py --dev DIR --confirm DIR [--out FILE]
"""
import argparse
import contextlib
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS))
import analyze_bosslab as A  # noqa: E402
import apply_hybrid_rule as H  # noqa: E402

BASE = H.BASE_LABEL
CAND = "noshrug"
SHRUG = "CARD.SHRUG_IT_OFF"
BOSS_SUFFIX = ".THE_INSATIABLE"


@contextlib.contextmanager
def _boss_is_insatiable():
    saved = A.QUEEN_ID_SUFFIX
    A.QUEEN_ID_SUFFIX = BOSS_SUFFIX
    try:
        yield
    finally:
        A.QUEEN_ID_SUFFIX = saved


def _trace_plays(path: Path) -> int | None:
    """Total Shrug It Off plays in one agent trace; None when the trace file is absent."""
    if not path.is_file():
        return None
    return sum(1 for row in A.trace_rows(path)
               if row.get("type") == "card" and row.get("card_id") == SHRUG)


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


def panel(run_dir: Path) -> dict | None:
    """Deltas, firing, shave and survival turns for one run dir; None when it holds no noshrug trial."""
    with _boss_is_insatiable():
        usable, dropped = A.load_trials([run_dir / "lab_results.jsonl"])
        if not any(r["_arm"] == CAND for r in usable):
            return None
        for r in usable:  # no Amalgam in Act 2: keep firepower_total defined (= boss damage only)
            r["_amalgam_damage"] = 0
        expected = _expected_keys(run_dir, usable, dropped)
        by_arm_key = {(r["_arm"], r["spec_id"], r["_offset"]): r for r in usable}
        d = H.candidate_delta(usable, BASE, CAND)
        incomplete = sorted(k for k in expected
                            if (BASE, *k) not in by_arm_key or (CAND, *k) not in by_arm_key)
        d["not_comparable"] = len(incomplete)
        rows = {r["metric"]: r for r in A.paired_continuous(usable, BASE, CAND)["rows"]}
    d["shave_base"], d["shave_cand"] = rows["queen_shaved"]["base_mean"], rows["queen_shaved"]["other_mean"]
    d["turns"] = {k: rows["turns"][k] for k in ("base_mean", "other_mean", "better", "worse", "tie")}
    fired, skipped, detail = 0, 0, []
    for key in sorted(k for k in expected if k not in incomplete):
        b = _trace_plays(run_dir / f"trial_{by_arm_key[(BASE, *key)]['trial_index']:04d}_agent.jsonl")
        a = _trace_plays(run_dir / f"trial_{by_arm_key[(CAND, *key)]['trial_index']:04d}_agent.jsonl")
        if b is None or a is None:
            skipped += 1
            continue
        detail.append((key[0], key[1], b, a))
        fired += 1 if b > a else 0  # G'': base plays MORE Shrug than noshrug
    return {"delta": d, "incomplete": incomplete,
            "fire": {"pairs": len(detail), "fired": fired, "skipped_missing_trace": skipped, "detail": detail}}


def _fmt_panel(d: dict) -> str:
    t = d["turns"]
    return (f"勝ち base {d['base_wins']} / noshrug {d['cand_wins']}　"
            f"ボス削り平均 base {d['shave_base']:.1%} / noshrug {d['shave_cand']:.1%}　"
            f"生存ターン {t['base_mean']:.2f}→{t['other_mean']:.2f}"
            f"（noshrug優{t['better']}/base優{t['worse']}/同値{t['tie']}）")


def render(dev_dir: Path, conf_dir: Path, dev: dict | None, conf: dict | None) -> str:
    L = ["# Act 2 noshrug の判定（base / noshrug、G'' + 4693f2e 規則）", "",
         f"dev: {dev_dir}　confirm: {conf_dir}" + ("" if conf is not None else "（未実行）"), "",
         f"G'' = baseアームの {SHRUG} 使用回数がnoshrugを超えた組。閾値 {H.G_THRESHOLD} 組（dev 12組中、confirm 12組中）。", ""]
    if dev is None:
        return "\n".join(L + ["dev に noshrug の実行データ無し（判定不能）", ""])
    res = H.judge_candidate(dev["delta"], conf["delta"] if conf else None,
                            dev["fire"], conf["fire"] if conf else None)
    L += [f"- 判定: **{res['verdict']}**" + ("（暫定: confirm 未実行）" if conf is None else ""), ""]
    L.append(H.format_candidate_report(CAND, res).replace("firing_C", "G''発火").replace("前提 G", "前提 G''"))
    L.append("")
    for tag, p in (("dev", dev), ("confirm", conf)):
        if p is None:
            L.append(f"- {tag}: 未実行")
            continue
        f = p["fire"]
        L.append(f"- {tag}: {_fmt_panel(p['delta'])}　G''発火 {f['fired']}/{f['pairs']}組"
                 f"（trace欠落 {f['skipped_missing_trace']}）")
        if p["incomplete"]:
            L.append(f"  - **pairing incomplete**: {len(p['incomplete'])}組が片アーム欠落"
                     f"（not_comparableに計上）: " + ", ".join(f"{s}|{o}" for s, o in p["incomplete"]))
        for s, o, b, a in f["detail"]:
            L.append(f"  - {s}|{o}: Shrug使用 base {b} → noshrug {a}{' [発火]' if b > a else ''}")
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Act 2 noshrug verdict (prereg act2_ns_prereg.md).")
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
