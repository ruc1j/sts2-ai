#!/usr/bin/env python3
"""Per-turn base-vs-candidate trace diff for a boss-lab firing analysis.

Given a base run dir and a candidate run dir (the same specs, single "base" arm,
`<spec>|base|<offset>` trial ids), locate the turns where the candidate aimed a
single-target Attack at a different enemy slot than base, and show how the fight
split on those turns: each side's attack choices and target, the Amalgam HP, the
Queen's incoming attack intent, and the player HP trajectory. Also a per-pair
roll-up of how much the candidate dealt to the Amalgam and whether it finished it,
so a shaved-but-not-killed minion (the leftover-damage hypothesis) can be seen.

Analysis only: reads the agent traces and the per-trial result lines; no game,
no build. A missing trial or trace degrades to "no data" rather than raising.

Usage:
  python3 trace_turn_diff.py --base DIR --cand DIR --spec SPEC [--spec SPEC ...]
  python3 trace_turn_diff.py --base DIR --cand DIR --all
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS))
import analyze_bosslab as A  # noqa: E402
import apply_hybrid_rule as H  # noqa: E402

QUEEN = A.QUEEN_ID_SUFFIX  # enemy id suffix for the boss Queen
AMALGAM = A.AMALGAM_ID_SUFFIX  # enemy id suffix for Queen's minion


def combat_rows(path: Path) -> list:
    """Combat-decision trace rows for a trial file, oldest first (non-combat rows dropped)."""
    out = []
    for r in A.trace_rows(path):
        if "turn" in r and r.get("phase") == "combat":
            out.append(r)
    return out


def trial_index_map(lab_path: Path) -> dict:
    """spec_id -> (trial_index, offset), first reliable row per spec wins."""
    import json
    lab_path = Path(lab_path)
    out: dict = {}
    if not lab_path.is_file():
        return out
    for l in lab_path.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("error") or (r.get("result") or {}).get("outcome_source") != A.RELIABLE:
            continue
        spec = r.get("spec_id")
        parts = str(r.get("trial_id", "")).split("|")
        off = int(parts[2]) if len(parts) >= 3 and parts[2].lstrip("-").isdigit() else 0
        if spec not in out:
            out[spec] = (r.get("trial_index"), off)
    return out


def _enemy(row, suffix):
    for e in row.get("enemies") or []:
        if str(e.get("id", "")).endswith(suffix):
            return e
    return None


def _intent_attack_damage(enemy) -> int:
    """Incoming attack damage the enemy intends to deal on its next act (sum over repeats)."""
    if not enemy:
        return 0
    total = 0
    for it in enemy.get("intents") or []:
        if str(it.get("type", "")).lower().startswith("attack"):
            total += int(it.get("damage", 0) or 0) * max(1, int(it.get("repeats", 1) or 1))
    return total


def _target_slot(rows, target_id) -> str:
    for r in rows:
        for e in r.get("enemies") or []:
            if e.get("combat_id") == target_id:
                return str(e.get("slot"))
    return "?"


def attack_choices(rows: list) -> dict:
    """turn -> list of (card_id, slot, damage_value) for single-target Attacks that turn."""
    out: dict = {}
    for r in rows:
        if r.get("type") != "card" or r.get("target_id") is None:
            continue
        hi = r.get("hand_index")
        hand = r.get("hand") or []
        if not (isinstance(hi, int) and 0 <= hi < len(hand)):
            continue
        c = hand[hi]
        if c.get("type") != "Attack":
            continue
        dmg = next((v.get("value") for v in c.get("vars", []) if v.get("id") == "Damage"), None)
        out.setdefault(r["turn"], []).append((c.get("id"), _target_slot(rows, r["target_id"]), dmg))
    return out


def turn_start_states(rows: list) -> dict:
    """turn -> first-row snapshot {amalgam, queen, queen_hp, player_hp, q_int, a_int}."""
    first: dict = {}
    for r in rows:
        t = r["turn"]
        if t in first:
            continue
        am, qu = _enemy(r, AMALGAM), _enemy(r, QUEEN)
        first[t] = {
            "amalgam_hp": am.get("hp") if am else None,
            "queen_hp": qu.get("hp") if qu else None,
            "amalgam_alive": bool(am),
            "player_hp": r.get("player_hp"),
            "q_int": _intent_attack_damage(qu),
            "a_int": _intent_attack_damage(am),
        }
    return first


def player_min_hp(rows: list) -> dict:
    m: dict = {}
    for r in rows:
        t = r["turn"]
        hp = r.get("player_hp")
        if isinstance(hp, int):
            m[t] = min(m.get(t, hp), hp)
    return m


def _slot_counter(rows: list) -> dict:
    """turn -> Counter of slots aimed by that turn's single-target Attacks (apply_hybrid_rule semantics)."""
    out: dict = {}
    for t, lst in attack_choices(rows).items():
        out[t] = Counter(slot for _c, slot, _d in lst)
    return out


def diff_turns(base_rows: list, cand_rows: list) -> list:
    """Turn numbers where the candidate's aimed-slot multiset differs from base."""
    bs, cs = _slot_counter(base_rows), _slot_counter(cand_rows)
    turns = sorted(set(bs) | set(cs))
    return [t for t in turns if bs.get(t, Counter()) != cs.get(t, Counter())]


def _amalgam_present(row) -> bool:
    return any(str(e.get("id", "")).endswith(AMALGAM) for e in (row.get("enemies") or []))


def _amalgam_final_hp(rows: list):
    """Amalgam HP in the last combat row; 0 if it ever lived but is gone (killed); None if never present."""
    if not rows:
        return None
    ever = any(_amalgam_present(r) for r in rows)
    if not ever:
        return None
    last = rows[-1]
    for e in last.get("enemies") or []:
        if str(e.get("id", "")).endswith(AMALGAM):
            return int(e.get("hp") or 0)
    return 0  # present earlier, gone from the final board -> killed


def pair_amalgam_rollup(base_rows: list, cand_rows: list) -> dict:
    """Total Amalgam HP removed and whether each side finished it (shave-but-not-kill flag)."""
    base_final = _amalgam_final_hp(base_rows)
    cand_final = _amalgam_final_hp(cand_rows)
    return {
        "base_removed": A.hp_removed_from_trace(base_rows, AMALGAM),
        "cand_removed": A.hp_removed_from_trace(cand_rows, AMALGAM),
        "base_final_hp": base_final, "cand_final_hp": cand_final,
        "base_killed": base_final == 0, "cand_killed": cand_final == 0,
        "cand_saw": cand_final is not None,
        # candidate damaged the minion but left it alive (the leftover-damage hypothesis trigger)
        "cand_survived_with_damage": cand_final is not None and cand_final > 0
        and (A.hp_removed_from_trace(cand_rows, AMALGAM) or 0) > 0,
    }


def render_pair(spec: str, base_dir: Path, cand_dir: Path, base_rows: list, cand_rows: list,
                base_won, cand_won) -> list:
    L = [f"### {spec} (base won={bool(base_won)} / cand won={bool(cand_won)})", ""]
    if not base_rows or not cand_rows:
        L.append("- base trace または cand trace が無く比較不能")
        L.append("")
        return L
    bt, ct = attack_choices(base_rows), attack_choices(cand_rows)
    bstart, cstart = turn_start_states(base_rows), turn_start_states(cand_rows)
    bmin, cmin = player_min_hp(base_rows), player_min_hp(cand_rows)
    diverging = diff_turns(base_rows, cand_rows)
    L.append(f"- 殴り先が別れた turn: {diverging}")
    L.append("")
    L.append("| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |")
    L.append("| --- | --- | --- | --- | --- | --- | --- |")
    turns = sorted(set(bstart) | set(cstart))
    for t in turns:
        b = bstart.get(t, {})
        c = cstart.get(t, {})
        batk = ", ".join(f"{cid.replace('CARD.','')}→{sl}~{dv}" for cid, sl, dv in bt.get(t, [])) or "-"
        catk = ", ".join(f"{cid.replace('CARD.','')}→{sl}~{dv}" for cid, sl, dv in ct.get(t, [])) or "-"
        mark = " *" if t in diverging else ""
        L.append(f"| {t}{mark} | {batk} | {catk} | {b.get('amalgam_hp')}/{c.get('amalgam_hp')} | "
                 f"{b.get('queen_hp')}/{c.get('queen_hp')} | {b.get('a_int')}/{c.get('a_int')} | "
                 f"{bmin.get(t)}/{cmin.get(t)} |")
    ru = pair_amalgam_rollup(base_rows, cand_rows)
    L.append("")
    L.append(f"- Amalgam 削った合計(推定): base {ru['base_removed']} / cand {ru['cand_removed']}。"
             f"base が Amalgam を倒した: {ru['base_killed']}（最終HP {ru['base_final_hp']}）、"
             f"cand が倒した: {ru['cand_killed']}（最終HP {ru['cand_final_hp']}）、"
             f"cand は削ったが倒せなかった: {ru['cand_survived_with_damage']}")
    L.append("")
    return L


def load_pair(base_dir: Path, cand_dir: Path, spec: str):
    """(base_rows, cand_rows, base_won, cand_won, paired?) for one spec across two run dirs."""
    lab_base, lab_cand = base_dir / "lab_results.jsonl", cand_dir / "lab_results.jsonl"
    bi, ci = trial_index_map(lab_base), trial_index_map(lab_cand)
    if spec not in bi or spec not in ci:
        return None, None, None, None, False
    brows = combat_rows(base_dir / f"trial_{bi[spec][0]:04d}_agent.jsonl")
    crows = combat_rows(cand_dir / f"trial_{ci[spec][0]:04d}_agent.jsonl")
    return brows, crows, result_won(lab_base, spec), result_won(lab_cand, spec), True


def result_won(lab_path: Path, spec: str):
    import json
    for l in lab_path.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("spec_id") == spec:
            return (r.get("result") or {}).get("won")
    return None


def summarize_amalgam(base_dir: Path, cand_dir: Path, specs: list) -> list:
    """Cross-pair tally: how often the candidate actually finished the Amalgam vs left it alive."""
    rows = []
    k = s = n = bkill = bwin = cwin = 0
    for spec in specs:
        br, cr, bw, cw, ok = load_pair(base_dir, cand_dir, spec)
        if not ok:
            continue
        ru = pair_amalgam_rollup(br, cr)
        bwin += bool(bw); cwin += bool(cw); bkill += ru["base_killed"]
        if ru["cand_killed"]:
            k += 1; tag = "倒せた"
        elif ru["cand_survived_with_damage"]:
            s += 1; tag = "削ったが倒せず"
        elif ru["cand_saw"]:
            n += 1; tag = "触れずつまり"
        else:
            tag = "Amalgam 無し"
        rows.append(f"| {spec} | {'勝' if bw else '敗'} | {'勝' if cw else '敗'} | {ru['base_removed']} "
                    f"| {ru['cand_removed']} | {'○' if ru['base_killed'] else '−'} | {ru['cand_final_hp']} | {tag} |")
    pairs = len(rows)
    L = ["", "## Amalgam 撃破の内訳（cand 全体、item2）", "",
         "| spec | base 勝敗 | cand 勝敗 | base が削った Amalgam HP | cand が削った Amalgam HP | base 撃破 | cand の Amalgam 最終 HP | cand 判定 |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |", *rows]
    L += ["", f"- 配対 {pairs} 組: cand が Amalgam を倒せた {k} 組、削ったが倒せなかった {s} 組、"
              f"触れずつまり {n} 組。base の Amalgam 撃破 {bkill} 組、base 勝ち {bwin} 対 cand 勝ち {cwin}。"]
    return L


def main() -> int:
    ap = argparse.ArgumentParser(description="per-turn base-vs-candidate trace diff")
    ap.add_argument("--base", required=True, help="base run dir")
    ap.add_argument("--cand", required=True, help="candidate run dir")
    ap.add_argument("--spec", action="append", default=[], help="spec_id to compare (repeat); or --all")
    ap.add_argument("--all", action="store_true", help="compare every spec paired across both dirs")
    ap.add_argument("--out", default="", help="write markdown here (else stdout)")
    args = ap.parse_args()
    base_dir, cand_dir = Path(args.base), Path(args.cand)
    lab_base, lab_cand = base_dir / "lab_results.jsonl", cand_dir / "lab_results.jsonl"
    if not lab_base.is_file() or not lab_cand.is_file():
        print("base または cand の lab_results.jsonl が無い", file=sys.stderr)
        return 1
    bs, cs = trial_index_map(lab_base), trial_index_map(lab_cand)
    specs = args.spec if args.spec else (sorted(set(bs) & set(cs)) if args.all else [])
    if not specs:
        print("--spec を並べるか --all を付ける", file=sys.stderr)
        return 1
    L = [f"# 配対 trace 差分（base: {base_dir} 対 cand: {cand_dir}）", "",
         "引用: 殴り先差分は apply_hybrid_rule の単独攻撃 slot 差分（`type=card` で Attack、target あり）。"
         "* は base と cand の殴り先 multiset が別れた turn。HP は各 turn 最初の観測 snapshot。"
         "攻撃 intent は次の行動の想定ダメージ（repeats 込み、block 控除前）。playerHP 最低は turn 中の最小。"]
    for spec in specs:
        brows, crows, bw, cw, ok = load_pair(base_dir, cand_dir, spec)
        if not ok:
            L.append(f"### {spec}")
            L.append("- どちらかの dir に reliable な試行が無い（比較不能）")
            L.append("")
            continue
        L += render_pair(spec, base_dir, cand_dir, brows, crows, bw, cw)
    L += summarize_amalgam(base_dir, cand_dir, specs)
    text = "\n".join(L)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
