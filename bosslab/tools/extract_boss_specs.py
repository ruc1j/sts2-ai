#!/usr/bin/env python3
"""Extract fixed-entry Act 2 boss specs from recorded official-run traces (BossLab input).

Reads only trace + mod log artifacts (gitignored, read-only here) and writes spec JSON next to
this script. The default input directory is the main tree's data/ because the run artifacts are
not tracked in git and a detached worktree does not contain them.

What a spec is
--------------
One entry state of an Act 2 boss fight (THE_INSATIABLE), rebuilt from the fight's first decision
line: deck (with upgrade flags and enchantments, in pile order), current and max HP, energy,
relics with counters, potions in slot order, player powers, and the enemies with their HP, move
and intents. Plus the fields a repeat of that fight needs from the game:

  run_seed            the run's string seed (mod log "Starting run with seed=...")
  act_index           0-based act index of the boss room (Act 2 = 1)
  act_floor           the floor number inside the act (Act 2 boss = 16 in these maps)
  total_floor         MapPointHistory length when the boss room is entered. RunState.TotalFloor is
                      exactly that count (Runs/RunState.cs:158) and the encounter's monster
                      generation RNG is seeded from runSeed + TotalFloor + hash(encounter id)
                      (Models/EncounterModel.cs:266-269), so reproducing this number reproduces
                      the boss composition.
  room_type           the room the fight happened in (Boss), which the agent's potion policy reads
                      (CombatBridge.cs:324-326, official_agent.py:2253,2262)
  recorded outcome    the fight's combat_end line, for calibrating the lab against the real run

Specs are deduplicated by (run seed, act floor, HP, deck multiset, relics, potions, enemy HP).
Every source occurrence is kept in `sources`, so the same entry seen in two panels is one spec.

Usage (from the worktree root or anywhere):
  python3 .dsh/extract_boss_specs.py                      # data/ of the main tree -> .dsh/boss_specs/
  python3 .dsh/extract_boss_specs.py --traces-dir <dir> --out-dir <dir> --limit 50
Writes boss_specs.jsonl (one spec per line), boss_specs.sample.json (the first spec, pretty), and
boss_specs.md (counts by tag, by entry-HP band, and the spec the C# harness should test against).
"""

from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
# The main checkout, which holds the gitignored run artifacts. Override with --traces-dir.
MAIN_TREE = Path(os.environ.get("STS2_MAIN_TREE", "/Users/mao/workspace/sts2-ai"))

ENTER = re.compile(
    r"^\d\d:\d\d:\d\d\.\d+ \[INFO\] \[AutoSlay\] Entering (\w+) room \(Act (\d+), Floor (\d+)\)"
)
SEED_LINE = re.compile(r"\[AutoSlay\] Starting run with seed=([A-Z0-9]+)")
BOSS_SUFFIX = "THE_INSATIABLE"
PILE_KEYS = ("hand", "draw_pile", "discard_pile", "exhaust_pile")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def read_rows(path: Path) -> list[dict]:
    rows = []
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            rows.append(record)
    return rows


def room_entries(modlog: Path) -> list[tuple[str, int, int]]:
    """(room kind, act, floor) for each room entry, consecutive duplicates collapsed.

    The AutoSlay log repeats the current room line on watchdog dumps; collapsing matches
    .dsh/random20_act2boss.py's alignment rule, which is what the trace blocks line up with.
    """
    rooms: list[tuple[str, int, int]] = []
    previous = None
    for line in read_text(modlog).splitlines():
        match = ENTER.match(line)
        if not match:
            continue
        item = (match.group(1), int(match.group(2)), int(match.group(3)))
        if item == previous:
            continue
        previous = item
        rooms.append(item)
    return rooms


COMBAT_KINDS = ("Monster", "Elite", "Boss")


def combat_blocks(rows: list[dict]) -> list[dict]:
    blocks: list[dict] = []
    current = None
    for row in rows:
        if row.get("phase") == "combat":
            if current is None:
                current = {"lines": [row]}
                blocks.append(current)
            else:
                current["lines"].append(row)
        elif row.get("phase") == "combat_end" and current is not None:
            current["end"] = row
            current = None
    return blocks


def card_entry(card: dict | None) -> dict | None:
    if not isinstance(card, dict) or not card.get("id"):
        return None
    return {
        "id": card["id"],
        "upgrade": int(card.get("upgrade") or 0),
        "enchantment": card.get("enchantment"),
        "vars_grown": any(
            (isinstance(var, dict) and var.get("value") is not None and var.get("base_value") is not None
             and var.get("value") != var.get("base_value"))
            for var in (card.get("vars") or ())
        ),
    }


def piles_of(entry: dict) -> dict[str, list[dict]]:
    piles = {}
    for key in PILE_KEYS:
        raw = entry.get(key) or []
        cards = [card for card in (card_entry(item) for item in raw) if card]
        piles[key] = cards
    return piles


def deck_multiset(piles: dict[str, list[dict]]) -> list[str]:
    deck = [f"{card['id']}+{card['upgrade']}+{card['enchantment'] or '-'}"
            for pile in piles.values() for card in pile]
    return sorted(deck)


def spec_id(key: tuple) -> str:
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode("utf-8")).hexdigest()[:12]


POOL_TO_CHARACTER = {
    "CARD_POOL.IRONCLAD_CARD_POOL": "CHARACTER.IRONCLAD",
    "CARD_POOL.DEFECT_CARD_POOL": "CHARACTER.DEFECT",
}


def character_guess(piles: dict[str, list[dict]], entry: dict) -> str:
    """Best guess of the character, from the hand cards' pools (the observation's richest signal)."""
    pools = collections.Counter()
    for key in PILE_KEYS:
        for card in entry.get(key) or ():
            if isinstance(card, dict) and card.get("pool"):
                pools[card["pool"]] += 1
    for pool, _count in pools.most_common():
        if pool in POOL_TO_CHARACTER:
            return POOL_TO_CHARACTER[pool]
    relics = set((entry.get("player") or {}).get("relics") or ())
    if "RELIC.BURNING_BLOOD" in relics:
        return "CHARACTER.IRONCLAD"
    return "CHARACTER.UNKNOWN"


def unresolved_flags(piles: dict[str, list[dict]], player: dict) -> list[str]:
    flags = []
    for key, pile in piles.items():
        if any(card["enchantment"] for card in pile):
            flags.append(f"enchantment_in_{key}")
        if any(card["vars_grown"] for card in pile):
            flags.append(f"grown_vars_in_{key}")
    if player.get("relic_counters"):
        flags.append("relic_counters")
    if (player.get("powers") or []):
        flags.append("player_powers_at_entry")
    return flags


def build_spec(trace: Path, entry: dict, end: dict, rooms_before: list[tuple[str, int, int]],
               room: tuple[str, int, int], run_seed: str | None, log_characters: list[str]) -> dict:
    piles = piles_of(entry)
    player = entry.get("player") or {}
    enemies = []
    for enemy in entry.get("enemies") or ():
        if not isinstance(enemy, dict) or not enemy.get("id"):
            continue
        enemies.append({
            "id": enemy["id"],
            "hp": enemy.get("hp"),
            "max_hp": enemy.get("max_hp"),
            "slot": enemy.get("slot"),
            "move": enemy.get("move"),
            "history": list(enemy.get("history") or ()),
            "intents": list(enemy.get("intents") or ()),
            "powers": list(enemy.get("powers") or ()),
        })
    kind, act, floor = room
    # Walked floors per act, excluding this boss room (the game appends the boss point itself when
    # EnterRoomDebug runs). RunState.TotalFloor is the MapPointHistory count (Runs/RunState.cs:158).
    per_act = collections.Counter()
    for prior_kind, prior_act, prior_floor in rooms_before:
        if (prior_kind, prior_act, prior_floor) == (kind, act, floor):
            continue  # skip this boss entry itself (it is the last element of rooms_before)
        per_act[prior_act - 1] += 1
    max_act = max(per_act, default=act - 1)
    history_per_act = [per_act.get(index, 0) for index in range(0, max_act + 1)]
    key = (run_seed, act, floor, player.get("hp"), player.get("max_hp"),
           tuple(deck_multiset(piles)), tuple(player.get("relics") or ()),
           tuple(sorted((str(k), str(v)) for k, v in (player.get("relic_counters") or {}).items())),
           tuple(entry.get("potions") or ()), tuple((e["id"], e["hp"]) for e in enemies))
    return {
        "spec_id": spec_id(key),
        "encounter_hint": "ENCOUNTER.THE_INSATIABLE_BOSS",
        "run_seed": run_seed,
        "act_index": act - 1,
        "act_floor": floor,
        "total_floor_including_boss": len(rooms_before),
        "room_type": kind,
        "history_per_act": history_per_act,
        "character": character_guess(piles, entry),
        "log_characters": log_characters,
        "unresolved": unresolved_flags(piles, player),
        "player": {
            "hp": player.get("hp"),
            "max_hp": player.get("max_hp"),
            "block": player.get("block"),
            "energy": player.get("energy"),
            "max_energy": player.get("max_energy"),
            "relics": list(player.get("relics") or ()),
            "relic_counters": dict(player.get("relic_counters") or {}),
            "powers": [
                {"id": power.get("id"), "amount": power.get("amount"), "facing": power.get("facing")}
                for power in (player.get("powers") or ()) if isinstance(power, dict)
            ],
        },
        "potions": list(entry.get("potions") or ()),
        "piles": piles,
        "deck_size": sum(len(pile) for pile in piles.values()),
        "enemies": enemies,
        "turn": entry.get("turn"),
        "entry_seq": entry.get("seq"),
        "recorded_outcome": {"won": end.get("won"), "end_hp": end.get("hp")},
        "sources": [{
            "trace": trace.name,
            "tag": trace.name[: -len("_agent.jsonl")].rpartition("_")[0],
            "seed": trace.name[: -len("_agent.jsonl")].rpartition("_")[2],
            "entry_seq": entry.get("seq"),
        }],
    }


def collect(traces_dir: Path, limit: int) -> tuple[list[dict], dict]:
    specs: dict[str, dict] = {}
    stats = collections.Counter()
    for trace in sorted(traces_dir.glob("*_agent.jsonl")):
        modlog = trace.with_name(trace.name[: -len("_agent.jsonl")] + "_mod.log")
        if not modlog.is_file():
            stats["no_modlog"] += 1
            continue
        if trace.name.startswith("boss_specs") or trace.name.endswith("_manifest.json"):
            continue
        log_text = read_text(modlog)
        rooms = room_entries(modlog)
        if not any(kind == "Boss" and act == 2 for kind, act, _floor in rooms):
            stats["no_act2_boss"] += 1
            continue
        rows = read_rows(trace)
        blocks = combat_blocks(rows)
        # Only combat rooms line up with combat blocks; event / shop / rest rooms do not appear in
        # the decision trace as combats. Keep the index into `rooms` so TotalFloor can be derived.
        combat_rooms = [(index, room) for index, room in enumerate(rooms) if room[0] in COMBAT_KINDS]
        if len(combat_rooms) != len(blocks):
            stats["unaligned_runs"] += 1
            continue
        seed_match = SEED_LINE.search(log_text)
        run_seed = seed_match.group(1) if seed_match else None
        log_characters = re.findall(r"Selecting character: ([A-Z_.]+)", log_text)
        for pair_index in range(len(combat_rooms)):
            index, room = combat_rooms[pair_index]
            block = blocks[pair_index]
            kind, act, floor = room
            if kind != "Boss" or act != 2 or block.get("end") is None:
                continue
            entry = block["lines"][0]
            if not any((enemy.get("id") or "").endswith(BOSS_SUFFIX) for enemy in entry.get("enemies") or ()):
                continue
            stats["fights"] += 1
            spec = build_spec(trace, entry, block["end"], rooms[: index + 1], room, run_seed, log_characters)
            existing = specs.get(spec["spec_id"])
            if existing is None:
                specs[spec["spec_id"]] = spec
            else:
                existing["sources"].extend(spec["sources"])
                if existing["recorded_outcome"] != spec["recorded_outcome"]:
                    stats["dedupe_outcome_conflict"] += 1
        if limit and len(specs) >= limit:
            break
    return list(specs.values()), stats


def band(hp: int | None) -> str:
    if hp is None:
        return "unknown"
    if hp < 60:
        return "<60"
    if hp < 80:
        return "60-79"
    return ">=80"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--traces-dir", dest="traces_dir", default=str(MAIN_TREE / "data"))
    parser.add_argument("--out-dir", dest="out_dir", default=str(HERE))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    traces = Path(args.traces_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    specs, stats = collect(traces, args.limit)
    specs.sort(key=lambda spec: (-spec["deck_size"], spec["spec_id"]))

    jsonl = out / "boss_specs.jsonl"
    jsonl.write_text("".join(json.dumps(spec, ensure_ascii=False) + "\n" for spec in specs),
                     encoding="utf-8")
    if specs:
        (out / "boss_specs.sample.json").write_text(json.dumps(specs[0], indent=2, ensure_ascii=False) + "\n",
                                                    encoding="utf-8")

    by_band: dict[str, list[dict]] = collections.defaultdict(list)
    by_tag: dict[str, list[dict]] = collections.defaultdict(list)
    for spec in specs:
        by_band[band(spec["player"]["hp"])].append(spec)
        for source in spec["sources"]:
            by_tag[source["tag"]].append(spec)
    won = sum(1 for s in specs if s["recorded_outcome"]["won"] is True)

    lines = [
        "# BossLab 入場spec 抽出結果",
        "",
        f"- 入力: `{traces}` の `*_agent.jsonl`（読み取りのみ。main ツリーの gitignore 済み成果物）",
        f"- 戦闘 {stats['fights']} 本から spec {len(specs)} 件（重複除去: 同一 seed・floor・HP・デッキ・"
        "レリック・ポーション・敵HP を同一とみなして 1 件）。不一致で除けた run: "
        f"{stats['unaligned_runs']}、mod log 無し: {stats['no_modlog']}、Act2ボス無し: {stats['no_act2_boss']}",
        f"- 記録された実走の勝敗: 勝 {won} / 負 {len(specs) - won}。spec 1 件は実走 1 回の結果を持つ。",
        f"- 同じ入場状態（同一 spec）で実走の勝敗が食い違った group: {stats['dedupe_outcome_conflict']} 件。"
        "入場状態を固定しても敵の行動列と引くカードは乱数で変わるため、lab は 1 状態 1 回では測れない"
        "（同じ spec で N 回まわして割合で見る）。",
        "",
        "## 入場HP帯別 spec 数",
        "",
        "| 入場HP | spec | 実走で勝 | 平均デッキ枚数 |",
        "| --- | --- | --- | --- |",
    ]
    for key in ("<60", "60-79", ">=80"):
        group = by_band.get(key) or []
        if not group:
            continue
        deck_average = sum(s["deck_size"] for s in group) / len(group)
        lines.append(
            f"| {key} | {len(group)} | {sum(1 for s in group if s['recorded_outcome']['won'] is True)} "
            f"| {deck_average:.1f} |"
        )
    lines += [
        "",
        "## tag 別（出現回数、spec 数に重複計上）",
        "",
        "| tag | 出現 |",
        "| --- | --- |",
    ]
    for tag, group in sorted(by_tag.items(), key=lambda item: (-len(item[1]), item[0]))[:25]:
        lines.append(f"| {tag} | {len(group)} |")
    lines += [
        "",
        "## C# ハーネスとの契約",
        "",
        "- `run_seed` と `total_floor_including_boss` を `RunState.CreateForNewRun` の seed と"
        "  MapPointHistory の長さとして与えると、encounter の敵構成が元の run と同じ乱数から出る"
        "  （`Runs/RunState.cs:158`、`Models/EncounterModel.cs:266-269`）。入室直後に `enemies` と"
        "  突き合わせて違いが出たら其試行を無効として扱う。",
        "- `player.hp`/`max_hp`・`piles`（hand/draw/discard/exhaust の順と強化・エンチャント込み）・"
        "  `potions`・`relics`/`relic_counters` を `Player` へ流し込む（`CardPile.Clear`+"
        "  `AddInternal`、`Player.AddRelicInternal`、`Player.AddPotionInternal`）。",
        "- `room_type` は `Boss`。`EnterRoomDebug` は model が `EncounterModel` のとき room type を"
        "  encounter 側の値で上書きする（`Runs/RunManager.cs:997-1000`）ので、`fight` コマンドのように"
        "  `RoomType.Monster` で入れると agent のポーション判断が変わる"
        "  （`CombatBridge.cs:324-326`→`official_agent.py:2253,2262`）。",
        "- `act_index`（Act 2 = 1）と `act_floor` も `RunState` 側にセットする。`choose_potion` の"
        "  boss 判定が `{0:17, 1:16, 2:15}` の floor 表を使うため、未設定だと boss 扱いを外す。",
        "- 合成状態（同じ入場状態での card 追加/除去の対照実験）は、`sources` が同じ base spec に対して"
        "  `CARD.SHRUG_IT_OFF` を 1 枚足す／抜く mutation を apply して作る。`draw_pile` 末尾への追加は"
        "  `AddInternal(card)`、除去は `RemoveInternal(card)`。",
        "",
        f"生成: `python3 .dsh/extract_boss_specs.py --traces-dir {traces}`",
        f"成果: `{jsonl.name}`（spec {len(specs)} 件）、`boss_specs.sample.json`（契約のサンプル）、"
        f"`{Path(__file__).name}` からの再生成で追試できる。",
    ]
    (out / "boss_specs.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"wrote {jsonl}: specs {len(specs)} from fights {stats['fights']} "
        f"(wins {won}, 同一spec内で実走結果が食い違った件数 {stats['dedupe_outcome_conflict']}, "
        f"unaligned runs {stats['unaligned_runs']}, no act2 boss runs {stats['no_act2_boss']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
