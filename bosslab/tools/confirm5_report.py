#!/usr/bin/env python3
"""Judge each H3a/H3c candidate once against the frozen confirm5 decision (T39).

Separate entry point from apply_hybrid_rule's single-selection H1/H2 flow. It loads the dev5 panel and the
confirm5 panel, computes each candidate's paired Δshave / Δfp / Δwin (analyze_bosslab) and its prerequisite-G
firing (target-choice divergence across all turns) on BOTH panels, then calls apply_hybrid_rule.judge_candidate
to print a 採用 / 保留 / 不採用 verdict per candidate. The rule wording is the frozen 4693f2e text plus the G
clause; this tool only feeds it. Confirm5 candidate dirs that do not exist yet (the run is still in flight)
leave that candidate's confirm-side conditions "未実行" and its verdict provisional. Run it mechanically once
after confirm5 finishes; do not tune the rule from its output.

Usage:
  python3 confirm5_report.py --dev-base DIR --confirm-base DIR \
      --cand LABEL=DEVDIR=CONFIRMDIR [--cand ...] [--out FILE]
A CONFIRMDIR may be a path that does not exist yet; then that candidate's confirm side is "未実行".
"""
import argparse
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS))
import analyze_bosslab as A  # noqa: E402
import apply_hybrid_rule as H  # noqa: E402

BASE = H.BASE_LABEL


def _panel_delta(base_dir: Path, cand_dirs: dict) -> dict:
    """Δ dict per candidate against base, from one run dir's base plus the candidate run dirs."""
    trials = [dict(r, _arm=BASE) for r in A.load_trials([base_dir / "lab_results.jsonl"])[0]]
    for label, d in cand_dirs.items():
        usable, _ = H.load_relabel(label, d)
        trials += usable
    return {label: H.candidate_delta(trials, BASE, label) for label in cand_dirs
            if any(r["_arm"] == label for r in trials)}


def _parse_cand(spec: str):
    """LABEL=DEVDIR=CONFIRMDIR -> (label, dev_dir, confirm_dir)."""
    parts = spec.split("=")
    if len(parts) != 3:
        raise SystemExit(f"--cand は LABEL=DEVDIR=CONFIRMDIR（got {spec!r}）")
    label, dev, conf = parts
    return label, Path(dev), Path(conf)


def main() -> int:
    ap = argparse.ArgumentParser(description="confirm5 per-candidate verdict (frozen rule + G).")
    ap.add_argument("--dev-base", required=True, help="dev5 base run dir")
    ap.add_argument("--confirm-base", required=True, help="confirm5 base run dir")
    ap.add_argument("--cand", action="append", required=True, metavar="LABEL=DEVDIR=CONFIRMDIR",
                    help="candidate dev5 dir and confirm5 dir (confirm5 dir may not exist yet)")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    dev_base, conf_base = Path(args.dev_base), Path(args.confirm_base)
    cands = [_parse_cand(c) for c in args.cand]
    labels = [c[0] for c in cands]
    dev_dirs = {lab: d for lab, d, _c in cands}
    conf_dirs = {lab: c for lab, _d, c in cands if c.is_dir()}

    if not (dev_base / "lab_results.jsonl").is_file():
        raise SystemExit(f"dev5 base に lab_results.jsonl が無い: {dev_base}")
    dev = _panel_delta(dev_base, {lab: d for lab, d in dev_dirs.items() if d.is_dir()})

    conf = _panel_delta(conf_base, conf_dirs) if conf_dirs else {}

    L = ["# confirm5 判定（候補ごと、4693f2e 規則 + 前提 G）", "",
         f"dev5 base: {dev_base}　confirm5 base: {conf_base}（confirm5 の各候補 dir は実行前なら 未実行）", "",
         "引用（規則原文、変更しない）:",
         f"- 条件充足: {H.SELECTION}",
         f"- {H.CONDITIONS[1].strip()}",
         f"- {H.CONDITIONS[5].strip()}",
         f"- {H.CONDITIONS[6].strip()}",
         f"- {H.FIRING}",
         f"- 保留: {H.KEEP}",
         ""]

    for label in labels:
        dev_dir, conf_dir = dev_dirs[label], {lab: d for lab, d in _parse_cand_pairs(cands)}.get(label)
        fire_dev = H.pair_attack_target_turns(dev_base, dev_dir) if dev_dir and dev_dir.is_dir() else None
        fire_conf = (H.pair_attack_target_turns(conf_base, conf_dir)
                     if conf_dir and conf_dir.is_dir() else None)
        res = H.judge_candidate(dev.get(label), conf.get(label), fire_dev, fire_conf)
        if dev.get(label) is None:
            L += [f"### 候補 {label}: dev5 実行データ無し（判定不能）", ""]
            continue
        L += [H.format_candidate_report(label, res), ""]

    # cross-candidate condition 2: do the candidates agree on the dev5 shave direction (robustness).
    signs = {lab: (0 if dev[lab]["Δshave"] == 0 else (1 if dev[lab]["Δshave"] > 0 else -1))
             for lab in labels if lab in dev}
    if len(signs) >= 2:
        agree = len(set(signs.values())) == 1 and all(v == 1 for v in signs.values())
        L += ["## 候補間の削り割合の向き（dev5、条件2）", "",
              "- dev5 の Δshave の向き: " + ", ".join(f"{lab} {'+' if v>0 else '0' if v==0 else '−'}"
                                                     for lab, v in signs.items()),
              f"- 条件2（dev5 で全候補 `Δshave > 0`）: {'充足' if agree else '不充足'}", ""]

    text = "\n".join(L)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def _parse_cand_pairs(cands):
    """(label, dev_dir, confirm_dir) list -> [(label, confirm_dir)] for building the fire-confirm map."""
    return [(lab, conf) for lab, _d, conf in cands]


if __name__ == "__main__":
    raise SystemExit(main())
