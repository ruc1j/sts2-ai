#!/usr/bin/env python3
"""Compare one BossLab trial's in-game entry state against its spec and the original run entry.

Analysis only; no game, no repo-policy source edits. For one trial trace
(data/bosslab_*/trial_XXXX_agent.jsonl) it checks whether the first combat observation the game
handed the agent matches (a) the plan entry the trial was built from and (b) the original run's
boss-entry observation the spec was extracted from. Any field that differs is a fidelity risk for
win-rate comparison: it means the same nominal entry state is not actually the same state.

Fields compared: player hp / max hp / block / energy / max_energy / powers (id + amount), relic id
list and counters, potions, the full deck multiset (id + upgrade + enchantment id), per-pile sizes,
enemy id / hp / max_hp / move / intents, and the turn number of the first decision.

Two comparisons are only made against the original run's boss-entry observation (the spec file does
not store them), and they are what settles the Act 3 questions:

  card.cost_or_values - per-card cost and Damage / Block preview values, matched by
      (id, upgrade, enchantment). An enchantment applied with the wrong amount shows up here (cost
      for Swift / TezcatarasEmber, Damage or Block for Nimble / Corrupted / Sharp), as does a card
      value a run changed through invisible relic props.
  first_decision_plays - how many cards the first recorded decision says were already played this
      turn, on both sides. Non-zero on the original side means that entry observation was taken
      mid-combat, and BossLab cannot restore the "played this turn" counters.

Run from the worktree root:
  python3 bosslab/tools/bosslab_fidelity.py --trial-trace data/bosslab_test1/trial_0000_agent.jsonl \
      --plan .dsh/bosslab_plan.json --specs .dsh/boss_specs.jsonl \
      --traces-dir /Users/mao/workspace/sts2-ai/data
  python3 bosslab/tools/bosslab_fidelity.py --all --out-dir data/bosslab_test1 --plan ... --specs ...
  # Act 3: --plan .dsh/bosslab_act3_plan_fidelity.json --specs .dsh/act3_boss_specs.jsonl
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MAIN_TREE = Path("/Users/mao/workspace/sts2-ai")


def rows_of(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


def spec_map(specs_path: Path) -> dict[str, dict]:
    return {json.loads(line)["spec_id"]: json.loads(line)
            for line in specs_path.read_text(encoding="utf-8").splitlines() if line.strip()}


def card_key(card: dict) -> str:
    up = card.get("upgrade") or 0
    ench = card.get("enchantment") or ""
    return f"{card.get('id')}+{up}+{ench}"


def pile_cards(obs: dict, key: str) -> list[str]:
    return [card_key(c) for c in (obs.get(key) or []) if isinstance(c, dict) and c.get("id")]


def deck_multiset(obs: dict) -> collections.Counter:
    c: collections.Counter = collections.Counter()
    for key in ("hand", "draw_pile", "discard_pile", "exhaust_pile"):
        c.update(pile_cards(obs, key))
    return c


def first_combat_obs(trace_rows: list[dict]) -> dict | None:
    for r in trace_rows:
        if r.get("phase") == "combat":
            return r
    return None


def spec_enemy_names(spec: dict) -> set:
    """Monster name suffixes the spec's boss is made of (`{"THE_INSATIABLE"}`, `{"QUEEN", ...}`)."""
    return {str(enemy.get("id") or "").split(".")[-1]
            for enemy in (spec.get("enemies") or ()) if enemy.get("id")}


def obs_enemy_names(obs: dict) -> set:
    return {str(enemy.get("id") or "").split(".")[-1]
            for enemy in (obs.get("enemies") or ()) if enemy.get("id")}


def orig_boss_obs(spec: dict, traces_dir: Path) -> dict | None:
    """The original run's boss-entry observation the spec was extracted from.

    Matched by the recorded `entry_seq` when present, otherwise by the first combat in that trace
    whose enemies include the spec's monster names. Act 2's THE_INSATIABLE and Act 3's QUEEN both
    show up several times per trace, so a hardcoded monster name would silently compare the wrong
    act's boss (which is what the Act 3 trials initially did).
    """
    names = spec_enemy_names(spec)
    for src in spec["sources"]:
        path = traces_dir / src["trace"]
        if not path.is_file():
            continue
        rows = rows_of(path)
        for row in rows:
            if row.get("phase") == "combat" and row.get("seq") == src.get("entry_seq"):
                if not names or names & obs_enemy_names(row):
                    return row
                break
        for row in rows:
            if row.get("phase") == "combat" and names & obs_enemy_names(row):
                return row
    return None


def spec_as_obs(spec: dict) -> dict:
    """Rebuild a synthetic first-observation from the spec's recorded piles/state."""
    return {
        "player": {
            "hp": spec["player"]["hp"], "max_hp": spec["player"]["max_hp"],
            "block": spec["player"].get("block", 0), "energy": spec["player"].get("energy", 3),
            "max_energy": spec["player"].get("max_energy", 3), "relics": spec["player"]["relics"],
            "relic_counters": spec["player"].get("relic_counters", {}),
            "powers": spec["player"].get("powers", []),
        },
        "potions": spec["potions"],
        "enemies": spec["enemies"],
        "hand": [{"id": c["id"], "upgrade": c["upgrade"], "enchantment": c["enchantment"]}
                 for c in spec["piles"]["hand"]],
        "draw_pile": [{"id": c["id"], "upgrade": c["upgrade"], "enchantment": c["enchantment"]}
                      for c in spec["piles"]["draw_pile"]],
        "discard_pile": [{"id": c["id"], "upgrade": c["upgrade"], "enchantment": c["enchantment"]}
                         for c in spec["piles"]["discard_pile"]],
        "exhaust_pile": [{"id": c["id"], "upgrade": c["upgrade"], "enchantment": c["enchantment"]}
                         for c in spec["piles"]["exhaust_pile"]],
    }


def compare(a: dict, b: dict) -> list[tuple[str, object, object]]:
    """Fields where observation a (lab) differs from b (spec/orig). Returns (field, a, b) rows."""
    rows: list[tuple[str, object, object]] = []

    def p(obs, key):
        return (obs.get("player") or {}).get(key)

    for key, label in (("hp", "player.hp"), ("max_hp", "player.max_hp"), ("block", "player.block"),
                       ("energy", "player.energy"), ("max_energy", "player.max_energy")):
        if p(a, key) != p(b, key):
            rows.append((label, p(a, key), p(b, key)))

    if sorted(p(a, "relics") or []) != sorted(p(b, "relics") or []):
        rows.append(("relics.id_set", sorted(p(a, "relics") or []), sorted(p(b, "relics") or [])))
    if (p(a, "relic_counters") or {}) != (p(b, "relic_counters") or {}):
        rows.append(("relic_counters", p(a, "relic_counters"), p(b, "relic_counters")))

    pa = sorted(((x.get("id"), x.get("amount")) for x in (p(a, "powers") or []) if isinstance(x, dict)))
    pb = sorted(((x.get("id"), x.get("amount")) for x in (p(b, "powers") or []) if isinstance(x, dict)))
    if pa != pb:
        rows.append(("player.powers", pa, pb))

    if sorted(a.get("potions") or []) != sorted(b.get("potions") or []):
        rows.append(("potions", sorted(a.get("potions") or []), sorted(b.get("potions") or [])))

    da, db = deck_multiset(a), deck_multiset(b)
    if da != db:
        only_a = da - db
        only_b = db - da
        rows.append(("deck.multiset", dict(only_a), dict(only_b)))

    for key in ("hand", "draw_pile", "discard_pile", "exhaust_pile"):
        if len(pile_cards(a, key)) != len(pile_cards(b, key)):
            rows.append((f"pile_size.{key}", len(pile_cards(a, key)), len(pile_cards(b, key))))

    ea = [(e.get("id"), e.get("hp"), e.get("max_hp")) for e in (a.get("enemies") or [])]
    eb = [(e.get("id"), e.get("hp"), e.get("max_hp")) for e in (b.get("enemies") or [])]
    if ea != eb:
        rows.append(("enemies.id_hp_maxhp", ea, eb))
    ia = [e.get("move") for e in (a.get("enemies") or [])]
    ib = [e.get("move") for e in (b.get("enemies") or [])]
    if ia != ib:
        rows.append(("enemy.initial_move", ia, ib))

    return rows


CARD_VALUE_IDS = ("Damage", "Block")


def _num(value) -> str:
    """Canonical text for a numeric game value so pairs of cards sort and compare consistently."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, (int, float)):
        return f"{float(value):g}"
    return str(value)


def card_stats(card: dict) -> tuple:
    """A card's observable play values: cost plus the Damage / Block preview values."""
    values = {}
    for var in card.get("vars") or ():
        if isinstance(var, dict) and var.get("id") in CARD_VALUE_IDS:
            values[var["id"]] = var.get("value")
    return (_num(card.get("cost")), _num(values.get("Damage")), _num(values.get("Block")))


def pile_card_map(obs: dict) -> dict:
    """Card kinds to their sorted (cost, Damage, Block) triples across all four piles."""
    grouped = collections.defaultdict(list)
    for key in ("hand", "draw_pile", "discard_pile", "exhaust_pile"):
        for card in obs.get(key) or ():
            if not isinstance(card, dict) or not card.get("id"):
                continue
            grouped[card_key(card)].append(card_stats(card))
    return {name: sorted(stats) for name, stats in grouped.items()}


def populated_card_stats(obs: dict) -> dict:
    """Card kinds to the distinct sets of their computed (cost, Damage, Block) triples.

    The bridge only carries computed values for cards the game is previewing at that moment, so most
    cards in a pile come back with empty cost/vars. Comparing the *distinct populated* triples per
    kind compares previewed values while ignoring which particular copies happened to be in hand
    (the shuffle differs between the lab and the original run by design).
    """
    grouped = collections.defaultdict(set)
    for key in ("hand", "draw_pile", "discard_pile", "exhaust_pile"):
        for card in obs.get(key) or ():
            if not isinstance(card, dict) or not card.get("id"):
                continue
            stats = card_stats(card)
            if any(part != "" for part in stats):
                grouped[card_key(card)].add(stats)
    return {name: sorted(stats) for name, stats in grouped.items()}


def compare_card_values(lab: dict, orig: dict) -> list:
    """Card kinds previewed on both sides whose computed cost or Damage/Block differs.

    An enchantment restored with the wrong amount lands here (its effect is a cost or value change),
    and so does a card value a run changed through relic props the lab cannot see. Kinds that only
    one side previewed cannot be compared, and are reported separately as `skipped`.
    """
    lab_cards, orig_cards = populated_card_stats(lab), populated_card_stats(orig)
    rows = []
    skipped = 0
    for name in sorted(set(lab_cards) | set(orig_cards)):
        in_lab, in_orig = name in lab_cards, name in orig_cards
        if not (in_lab and in_orig):
            skipped += 1
            continue
        if lab_cards[name] != orig_cards[name]:
            rows.append((name, lab_cards[name], orig_cards[name]))
    return rows, len(set(lab_cards) & set(orig_cards)), skipped


def first_decision_plays(obs: dict | None) -> dict:
    plays = (obs or {}).get("plays") or {}
    return {key: value for key, value in plays.items()
            if key in ("cards_this_turn", "attacks_this_turn", "skills_this_turn", "powers_this_turn")}


def describe(trace: Path, plan_trial: dict, spec: dict, orig: dict | None) -> list[str]:
    lab = first_combat_obs(rows_of(trace))
    if lab is None:
        return [f"### {trace.name}\n\nNo combat record in trial trace."]
    spec_obs = spec_as_obs(spec)
    lines = [f"### {trace.name}  (spec {spec['spec_id']}, plan deck {len(plan_trial['deck'])} cards)"]
    lines += [
        "",
        f"- lab first decision: seq {lab.get('seq')} turn {lab.get('turn')}, "
        f"hand {len(pile_cards(lab,'hand'))}, draw {len(pile_cards(lab,'draw_pile'))}, "
        f"hp {(lab.get('player') or {}).get('hp')}",
    ]
    lab_vs_spec = compare(lab, spec_obs)
    lines.append(f"- lab vs spec: {'一致' if not lab_vs_spec else str(len(lab_vs_spec)) + ' 項目で不一致'}")
    for field, la, sb in lab_vs_spec:
        lines.append(f"  - `{field}`: lab={_fmt(la)} / spec={_fmt(sb)}")
    if orig is not None:
        spec_vs_orig = compare(spec_obs, orig)
        lab_vs_orig = compare(lab, orig)
        lines.append(f"- spec vs 元trace: {'一致' if not spec_vs_orig else str(len(spec_vs_orig)) + ' 項目で不一致'} "
                     f"(抽出の忠実性)")
        for field, sa, ob in spec_vs_orig:
            lines.append(f"  - `{field}`: spec={_fmt(sa)} / orig={_fmt(ob)}")
        lines.append(f"- lab vs 元trace 計: {len(lab_vs_orig)} 項目")
        value_diffs, preview_compared, preview_skipped = compare_card_values(lab, orig)
        lines.append(f"- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した "
                     f"{preview_compared} 種類のうち "
                     f"{'全部一致' if not value_diffs else str(len(value_diffs)) + ' 種類で不一致'}"
                     f"（片側だけの preview で比較できない札 {preview_skipped} 種類）。enchantment の "
                     "amount 違い・relic props 起因の値変更はここで出る")
        for name, lab_stats, orig_stats in value_diffs[:12]:
            lines.append(f"  - `{name}`: lab={_fmt(lab_stats)} / orig={_fmt(orig_stats)}")
        lab_plays, orig_plays = first_decision_plays(lab), first_decision_plays(orig)
        if lab_plays != orig_plays:
            lines.append(f"- 最初の判断行のプレイ済み counter: lab={_fmt(lab_plays)} / "
                         f"orig={_fmt(orig_plays)}。orig 側が 0 でなければ元trace の入場観測が戦闘途中"
                         "で、lab はこの counter を復元できない（Perfected Strike 等の初手威力がずれる）")
    else:
        lines.append("- 元trace が見つからない (sources のファイルがディスクに無い)")
    return lines


def _fmt(v) -> str:
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= 120 else s[:117] + "..."


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--trial-trace")
    ap.add_argument("--plan", default=str(HERE / "bosslab_plan.json"))
    ap.add_argument("--specs", default=str(HERE / "boss_specs.jsonl"))
    ap.add_argument("--traces-dir", dest="traces_dir", default=str(MAIN_TREE / "data"))
    ap.add_argument("--all", dest="all", action="store_true", help="every trial_*_agent.jsonl in --out-dir")
    ap.add_argument("--out-dir", dest="out_dir", default="")
    ap.add_argument("--out", default=str(HERE / "bosslab_fidelity.md"))
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    trials = {t["trial_id"]: t for t in plan["trials"]}
    specs = spec_map(Path(args.specs))
    traces_dir = Path(args.traces_dir)

    targets: list[Path] = []
    if args.all:
        targets = sorted(Path(args.out_dir).glob("trial_*_agent.jsonl"))
    elif args.trial_trace:
        targets = [Path(args.trial_trace)]
    else:
        raise SystemExit("give --trial-trace or --all --out-dir")

    out = ["# BossLab 忠実性チェック (T4a)", "",
           "lab の戦闘開始観測を、plan の entry と spec、および元 run の入場観測と比べる。",
           "不一致は「同じ名前の入場状態が実際には同じ状態でない」こと=勝率比較へのリスク。", ""]
    for trace in targets:
        tid = trace.name.replace("trial_", "trial ").replace("_agent.jsonl", "")
        idx = int(trace.name.split("_")[1])
        trial = next((t for t in plan["trials"] if t["trial_index"] == idx), None)
        if trial is None:
            out.append(f"### {trace.name}\n\nplan に trial_index {idx} がない")
            continue
        spec = specs.get(trial["spec_id"])
        if spec is None:
            out.append(f"### {trace.name}\n\nspec {trial['spec_id']} がない")
            continue
        orig = orig_boss_obs(spec, traces_dir)
        out += describe(trace, trial, spec, orig)
        out.append("")
    Path(args.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(targets)} trials compared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
