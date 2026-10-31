#!/usr/bin/env python3
"""Build a BossLab trial plan from the fixed-entry specs (.dsh/boss_specs.jsonl).

The plan is what official_mod/BossLab.cs reads (one trial per game process, indexed by
--bosslab-trial). Each trial is a base spec plus an arm's mutation, so two arms see the same deck,
HP, relics, potions, run seed and walked floors, and only the mutation differs. That is the
same-entry-state comparison docs/EVALUATION.md:35 requires for local causality.

v1 supports only what BossLab.cs can inject: card id + upgrade, relic ids, potion ids, HP, max HP,
and the walked-floor counts. Specs whose entry state carries enchantments, per-copy stored card
values, relic counters, or entry-time player powers are left out unless --allow-unresolved is
given; the count printed here says how many that leaves (see .dsh/bosslab_notes.md).

Arm grammar (repeat --arm):
  name=+CARD.ID            add one copy of the card to the deck
  name=-CARD.ID            remove one copy of the card from the deck (must be present)
  name=+CARD.ID:1          do it with upgrade level 1
  base                     no mutation
Example: --arm base --arm '+shrug=+CARD.SHRUG_IT_OFF' --arm '-shrug=-CARD.SHRUG_IT_OFF'

Usage (from the worktree root):
  python3 .dsh/make_bosslab_plan.py --arm base --arm '+shrug=+CARD.SHRUG_IT_OFF' \
      --max-specs 12 --trials-per-arm 6 --out .dsh/bosslab_plan.json --md .dsh/bosslab_plan.md
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

sys.path.insert(0, str(HERE))
from relic_entry_effects import defer_relics_for, flag_relics_for, relic_counters_are_known  # noqa: E402

DEFAULT_SPECS = HERE / "boss_specs.jsonl"


def parse_arm(text: str) -> tuple[str, list[tuple[str, str, int]]]:
    """`name=+CARD.X,-CARD.Y:1` -> (name, [("+", "CARD.X", 0), ("-", "CARD.Y", 1)])."""
    name, _sep, body = text.partition("=")
    if not body:
        return name, []
    edits = []
    for piece in body.split(","):
        piece = piece.strip()
        if not piece:
            continue
        op = piece[0]
        if op not in "+-":
            raise SystemExit(f"--arm {name}: edit {piece!r} must start with + or -")
        spec = piece[1:]
        card, _sep, upgrade = spec.partition(":")
        if not card.startswith("CARD."):
            raise SystemExit(f"--arm {name}: {card!r} is not a CARD.<ID>")
        edits.append((op, card, int(upgrade or 0)))
    return name, edits


def card_view_for_trial(card: dict) -> dict:
    """Trial-side card entry: id + upgrade, plus the enchantment when the spec carries one.

    `enchantment_amount` comes from the game's own sources (BossLab reads it into
    SerializableCard.Enchantment). Specs whose enchantment amount is unknown carry 0 and the harness
    uses the enchantment's default of 1; the real-machine fidelity check is what confirms it.
    """
    out = {"id": card["id"], "upgrade": card["upgrade"]}
    if card.get("enchantment"):
        out["enchantment"] = card["enchantment"]
        out["enchantment_amount"] = int(card.get("enchantment_amount") or 0)
    return out


PILE_TYPES = (("hand", "hand"), ("draw_pile", "draw"), ("discard_pile", "discard"), ("exhaust_pile", "exhaust"))


def entry_state_for_trial(spec: dict) -> dict:
    """Recorded enemy HP and combat piles for BossLab.RestoreRecordedEntryState (opt-in per plan)."""
    return {
        "restore_entry_state": True,
        "enemies": [{"id": e["id"], "hp": e["hp"], "max_hp": e.get("max_hp") or e["hp"]}
                    for e in spec["enemies"]],
        "piles": [{"pile_type": pile_type,
                   "cards": [card_view_for_trial(card) for card in spec["piles"][key]]}
                  for key, pile_type in PILE_TYPES],
    }


def apply_arm(deck: list[dict], edits: list[tuple[str, str, int]]) -> tuple[list[dict], list[str]]:
    notes = []
    out = list(deck)
    for op, card_id, upgrade in edits:
        if op == "+":
            out.append({"id": card_id, "upgrade": upgrade})
            notes.append(f"added {card_id}{'+' if upgrade else ''}")
            continue
        index = next((i for i, card in enumerate(out)
                      if card["id"] == card_id and card["upgrade"] == upgrade), None)
        if index is None:
            notes.append(f"absent {card_id}{'+' if upgrade else ''}")
            continue
        out.pop(index)
        notes.append(f"removed {card_id}{'+' if upgrade else ''}")
    return out, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--specs", default=str(DEFAULT_SPECS))
    parser.add_argument("--out", default=str(HERE / "bosslab_plan.json"))
    parser.add_argument("--md", default=str(HERE / "bosslab_plan.md"))
    parser.add_argument("--arm", dest="arms", action="append", default=[],
                        help="arm definition, repeatable (default: base only)")
    parser.add_argument("--trials-per-arm", dest="trials_per_arm", type=int, default=6)
    parser.add_argument("--offset-start", dest="offset_start", type=int, default=0,
                        help="first rng_offset; a second, independent remeasurement plan uses a "
                             "different offset range so its effective seeds differ")
    parser.add_argument("--max-specs", dest="max_specs", type=int, default=12)
    parser.add_argument("--band", dest="bands", action="append", default=[],
                        help="entry-HP band filter, e.g. <60, 60-79, >=80 (repeatable)")
    parser.add_argument("--outcome", choices=("any", "win", "loss"), default="any")
    parser.add_argument("--tag-include", dest="tag_include", action="append", default=[],
                        help="only specs with a source tag starting with this prefix (repeatable)")
    parser.add_argument("--require-card", dest="require_card", action="append", default=[],
                        help="only specs whose deck already holds this CARD.ID (id[:upgrade]); makes a "
                             "-CARD arm actually remove something")
    parser.add_argument("--allow-unresolved", dest="allow_unresolved", action="store_true",
                        help="include specs whose state BossLab.cs v1 cannot inject")
    parser.add_argument("--per-band", dest="per_band", type=int, default=0,
                        help="pick this many specs from each HP band (<60, 60-79, >=80) instead of one "
                             "flat --max-specs top-N, so easy/hard entries are balanced across arms")
    parser.add_argument("--exclude-relic", dest="exclude_relic", action="append", default=[],
                        help="drop specs holding this RELIC.ID (repeatable). Limited-use start-of-combat "
                             "relics (e.g. RELIC.EMBER_TEA, RELIC.STONE_CALENDAR) get rebuilt fresh in "
                             "the lab and re-grant their combat-start effect the real run had already "
                             "spent; see .dsh/bosslab_fidelity.md")
    parser.add_argument("--order-seed", dest="order_seed", default="bosslab")
    parser.add_argument("--skip-specs", dest="skip_specs", default="",
                        help="file of spec_ids to drop before selection (one per line); used to keep "
                             "a confirmation panel disjoint from the development panel")
    parser.add_argument("--spec-ids", dest="spec_ids", default="",
                        help="file of spec_ids, one per line; when set, use exactly these specs in "
                             "this order (ignoring band/outcome/require-card/unresolved filters). "
                             "Use for hand-picked diagnostic plans, e.g. the win-state check "
                             "(.dsh/bosslab_plan_wins.speclist).")
    parser.add_argument("--spec-ids-note", dest="spec_ids_note", default="",
                        help="one-line provenance of how the --spec-ids list was chosen; written to "
                             "the md as the selection criterion (EVALUATION.md traceability)")
    parser.add_argument("--character", default=None, help="override the character id (default: from specs)")
    parser.add_argument("--restore-entry-state", dest="restore_entry_state", action="store_true",
                        help="emit the recorded enemy HP and combat piles per trial and switch on the "
                             "boss-entry write-back in BossLab.cs (default off: the plan stays byte-identical)")
    args = parser.parse_args()

    arms = [parse_arm(text) for text in (args.arms or ["base"])]
    all_specs = [json.loads(line) for line in Path(args.specs).read_text(encoding="utf-8").splitlines() if line.strip()]

    def band_of(spec: dict) -> str:
        hp = spec["player"]["hp"]
        return "<60" if hp < 60 else "60-79" if hp < 80 else ">=80"

    def usable(spec: dict) -> bool:
        if not args.allow_unresolved and spec["unresolved"]:
            return False
        if args.exclude_relic and set(args.exclude_relic) & set(spec["player"]["relics"]):
            return False
        # BossLab can only restore a threshold relic's counter when the source trace carried the
        # relic_counters column; a counter-relic spec from an older bridge has an unknown counter, so
        # drop it rather than silently start the fight at zero (bosslab/tools/relic_entry_effects.py).
        if not relic_counters_are_known(spec["player"].get("relics") or (),
                                        spec.get("relic_counters_observed", False)):
            return False
        if args.tag_include and not any(source["tag"].startswith(prefix)
                                        for prefix in args.tag_include
                                        for source in spec["sources"]):
            return False
        if args.require_card:
            held = {(card["id"], card["upgrade"]) for pile in spec["piles"].values() for card in pile}
            for need in args.require_card:
                card_id, _sep, upgrade = need.partition(":")
                if (card_id, int(upgrade or 0)) not in held:
                    return False
        if args.bands and band_of(spec) not in args.bands:
            return False
        won = spec["recorded_outcome"]["won"]
        if args.outcome == "win" and won is not True:
            return False
        if args.outcome == "loss" and won is not False:
            return False
        return True


    specs_by_id = {spec["spec_id"]: spec for spec in all_specs}

    def hkey(spec: dict) -> str:
        return hashlib.sha256(f"{args.order_seed}|{spec['spec_id']}".encode()).hexdigest()
    manual = bool(args.spec_ids)
    if manual:
        # Hand-picked diagnostic panel: exactly the listed specs, in the given order. Filters are
        # intentionally skipped; unresolved drift is reported in the md so the reader can interpret.
        ids = [line.strip() for line in Path(args.spec_ids).read_text(encoding="utf-8").splitlines() if line.strip()]
        missing = [i for i in ids if i not in specs_by_id]
        if missing:
            raise SystemExit(f"--spec-ids: unknown spec_id(s): {', '.join(missing)}")
        selected: list[dict] = [specs_by_id[i] for i in ids]
        eligible = selected
    else:
        skip_ids = set()
        if args.skip_specs:
            skip_ids = {line.strip() for line in Path(args.skip_specs).read_text(encoding="utf-8").splitlines()
                        if line.strip()}
        eligible = [spec for spec in all_specs if usable(spec) and spec["spec_id"] not in skip_ids]
        # Deterministic selection: hash-order so a different --order-seed draws a different panel, and
        # the same seed always reproduces the same trial list. With --per-band, take that many from each
        # HP band so the three arms see a balanced mix of easy and hard entries.
        eligible.sort(key=hkey)
        if args.per_band:
            selected = []
            for label in ("<60", "60-79", ">=80"):
                group = [s for s in eligible if band_of(s) == label][: args.per_band]
                selected.extend(group)
            selected.sort(key=hkey)
        else:
            selected = eligible[: args.max_specs]
    clean = sum(1 for spec in all_specs if not spec["unresolved"])

    trials: list[dict] = []
    for offset in range(args.offset_start, args.offset_start + args.trials_per_arm):
        for spec_index, spec in enumerate(selected):
            # Rotate the arm order per spec so no arm always runs first within a spec group.
            order = [arm for arm in arms[(spec_index + offset) % len(arms):]] + arms[:(spec_index + offset) % len(arms)]
            for name, edits in order:
                deck, notes = apply_arm(
                    [card_view_for_trial(card) for card in
                     sorted((card for pile in spec["piles"].values() for card in pile),
                            key=lambda card: (card["id"], card["upgrade"]))],
                    edits)
                trial = {
                    "trial_index": len(trials),
                    "trial_id": f"{spec['spec_id']}|{name}|{offset}",
                    "arm": name,
                    "mutation_notes": notes,
                    "spec_id": spec["spec_id"],
                    "encounter": spec["encounter_hint"],
                    "character": args.character or spec["character"],
                    "run_seed": spec["run_seed"],
                    "rng_offset": offset,
                    "act_index": spec["act_index"],
                    "act_floor": spec["act_floor"],
                    "ascension": 0,
                    "history_per_act": spec["history_per_act"],
                    "hp": spec["player"]["hp"],
                    "max_hp": spec["player"]["max_hp"],
                    "deck": deck,
                    "relics": list(spec["player"]["relics"]),
                    # Relics whose own room-entry hook already did its work in the recorded run (it
                    # upgraded draw cards, healed, or widened the potion belt) and whose result the
                    # trial's deck / HP / potion list carries. BossLab attaches these after
                    # EnterRoomDebug so the hook cannot fire a second time with the lab's own RNG;
                    # the HP re-assert and the slot widening in BossLab.cs cover the other two
                    # families. The classification is bosslab/tools/relic_entry_effects.py.
                    "defer_relics": defer_relics_for(spec["player"]["relics"]),
                    # Threshold counters BossLab writes back at the first decision, keyed by
                    # relic.Id.ToString() exactly as the bridge emitted them (BossLab.RestoreRelicCounters).
                    "relic_counters": dict(spec["player"].get("relic_counters") or {}),
                    # Relics that add a card to the opening hand on the first turn. The lab cannot
                    # reproduce which card the recorded run's RNG produced, so analyze_bosslab.py
                    # marks these specs with a dagger and reports the same signal without them.
                    "flag_relics": flag_relics_for(spec["player"]["relics"]),
                    "potions": list(spec["potions"]),
                    # Powers the recorded entry shows that the relic list will not produce on its
                    # own. BossLab applies these after room entry (see BossLab.ApplyEntryPowers), so
                    # the relic-granted part must not be repeated here.
                    "powers": list(spec.get("entry_powers_residual") or []),
                    "recorded": {
                        "won": spec["recorded_outcome"]["won"],
                        "traces": [source["trace"] for source in spec["sources"]],
                    },
                }
                if args.restore_entry_state:
                    trial.update(entry_state_for_trial(spec))
                trials.append(trial)

    deferred_relics = sorted({relic for trial in trials for relic in trial["defer_relics"]})
    flagged_relics = sorted({relic for trial in trials for relic in trial["flag_relics"]})
    plan = {
        "mode": "bosslab",
        "offset_start": args.offset_start,
        "encounters": sorted({trial["encounter"] for trial in trials}),
        "character": trials[0]["character"] if trials else None,
        "arms": [name for name, _edits in arms],
        "specs_selected": len(selected),
        "trials_per_arm": args.trials_per_arm,
        # What the entry-state handling in official_mod/BossLab.cs has to do for this plan
        # (bosslab/tools/relic_entry_effects.py is the decompile-grounded classification).
        "relic_entry_effects": {
            "defer_relics": deferred_relics,
            "flag_relics": flagged_relics,
            "trials_with_defer": sum(1 for trial in trials if trial["defer_relics"]),
            "trials_with_flag": sum(1 for trial in trials if trial["flag_relics"]),
        },
        "trials": trials,
    }
    Path(args.out).write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    per_arm = collections.Counter(trial["arm"] for trial in trials)
    lines = ["# BossLab trial plan", ""]
    if manual:
        unres = [s for s in selected if s["unresolved"]]
        lines.append(f"- specs: `--spec-ids` による手動選択 {len(selected)} 件（band/outcome/card 条件は無視、"
                     "列挙順で trial_index 0.. を割り当てる）")
        lines.append(f"- このうち {len(unres)} 件は v1 の注入で扱えない状態を含み、lab の合成状態は実走から"
                     "次の分だけずれる（方向は既知: enchantment・カードの成長値・入場時 power・relic counter が消える）:")
        for s in unres:
            lines.append(f"  - {s['spec_id']}: {', '.join(s['unresolved'])}")
    else:
        lines.append(f"- specs: `{Path(args.specs).name}` 全 {len(all_specs)} 件のうち選択条件を通ったもの {len(eligible)} 件から"
                     f" {len(selected)} 件（order-seed `{args.order_seed}` の hash 順、上位 {args.max_specs} 件）")
        lines.append(f"- v1 の状態注入で扱えない spec（enchantment・カードの vars・relic counter・入場時 power）"
                     f" を除いた残りは全 spec 中 {clean} 件")
    lines += [
        f"- arms: {', '.join(name for name, _ in arms)}"
        + ("（rotation 付きで spec ごとに先頭を変える）" if len(arms) > 1 else "（単一 arm なので rotation なし）"),
    ]
    if not manual:
        lines.append(f"- require-card: {', '.join(args.require_card) if args.require_card else 'なし'}"
                     "（deck にその札を含む spec だけを選ぶ。除去 arm が実際に除去できるようにする）")
    else:
        lines.append("- 選定条件: " + (args.spec_ids_note or "--spec-ids ファイル列挙時点の裁量（生成器は条件適用なし）"))
    lines += [
        f"- trials: {len(trials)}（arm 別 {dict(per_arm)}）、offset {args.offset_start}..{args.offset_start + args.trials_per_arm - 1}で乱数を振る"
        + ("（再測定計画は別の offset 範囲を使い、実効 seed を独立させる）" if args.offset_start else ""),
        f"- 入室 hook の扱い（bosslab/tools/relic_entry_effects.py）: 入室後に付与する deferred が "
        f"{plan['relic_entry_effects']['trials_with_defer']} trial"
        f"（{', '.join(deferred_relics) if deferred_relics else 'なし'}）、開手札がlab で再現できない "
        f"flag が {plan['relic_entry_effects']['trials_with_flag']} trial"
        f"（{', '.join(flagged_relics) if flagged_relics else 'なし'}）。入場 HP とポーション枠は "
        "BossLab.cs 側で記録値に寄せるため trial 単位の指定はない",
        f"- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan {Path(args.out).name}`",
        "",
        "## 選択された base spec",
        "",
        "| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for spec in selected:
        enemies = "/".join(f"{enemy['id'].split('.')[-1]}:{enemy['hp']}" for enemy in spec["enemies"][:3])
        recorded = "勝" if spec["recorded_outcome"]["won"] is True else "負"
        lines.append(
            f"| {spec['spec_id']} | {spec['player']['hp']} | {enemies} | {spec['deck_size']} | {recorded} | "
            f"{', '.join(name for name, _ in arms)} |"
        )
    lines += [
        "",
        "注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数"
        "（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run "
        "と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。",
    ]
    Path(args.md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out}: trials {len(trials)} specs {len(selected)} arms {[name for name, _ in arms]} "
        f"(clean specs available {clean}/{len(all_specs)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
