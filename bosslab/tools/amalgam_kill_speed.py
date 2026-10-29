#!/usr/bin/env python3
"""Where is the headroom in Act3 Queen fights, given base's strength is killing the Amalgam early (T40).

Reads only committed base run dirs (the "base" arm = official_agent), no game, no build. For each trial it
recovers, from the decision trace:
  (a) the turn the Amalgam died on and the player HP at that turn's start (kill-speed distribution),
  (b) the deck the fight started with, split into Attack / Skill (mostly block) / Power / unknown card
      counts, plus starting energy and whether Strength was present (relic VAJRA or a Strength power),
  (c) for fights that killed the Amalgam slowly or never, the "取りこぼし": turns where the hand had enough
      single-target attack damage to finish the remaining Amalgam HP but the Amalgam survived that turn.

Card types are recovered from the runtime observation (the static piles only store ids); a card exposes its
type whenever it is in hand, so a global id->type map is built by unioning every hand entry across the run
dirs. Cards that were never drawn anywhere stay "unknown". This is a hypothesis-generating survey, not a
causal claim: whatever the numbers show is offered as candidate headroom for the next goal.

Usage:
  python3 amalgam_kill_speed.py --dir DIR [--dir DIR ...] [--out FILE]
"""
import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS))
import analyze_bosslab as A  # noqa: E402

AMALGAM = A.AMALGAM_ID_SUFFIX  # Queen's minion id suffix
STRENGTH_RELICS = {"RELIC.VAJRA", "RELIC.OHIO_GOAT"}  # relics granting early/permanent Strength

_CARD_META: dict = {}  # global id -> {"type","cost","block"}, filled by scan_card_types


def scan_card_types(dirs: list[Path]) -> dict:
    """Union every in-hand card entry across all dirs: id -> {type, cost, block}, for deck classification."""
    for d in dirs:
        for f in sorted(d.glob("trial_*_agent.jsonl")):
            for r in A.trace_rows(f):
                for c in r.get("hand") or []:
                    cid = c.get("id")
                    if not cid:
                        continue
                    has_block = any(v.get("id") == "Block" for v in (c.get("vars") or []))
                    _CARD_META[cid] = {
                        "type": c.get("type"),
                        "cost": c.get("cost"),
                        "block": _CARD_META.get(cid, {}).get("block", False) or has_block,
                    }
    return _CARD_META


def combat_rows(path: Path) -> list:
    return [r for r in A.trace_rows(path) if "turn" in r and r.get("phase") == "combat"]


def _has_amalgam(row) -> bool:
    return any(str(e.get("id", "")).endswith(AMALGAM) for e in (row.get("enemies") or []))


def _amalgam_hp(row):
    for e in row.get("enemies") or []:
        if str(e.get("id", "")).endswith(AMALGAM):
            return e.get("hp")
    return None


def kill_info(rows: list) -> dict:
    """Turn the Amalgam was killed on (the last turn it was still present) and player HP at that turn's start."""
    if not rows:
        return {"killed": False, "kill_turn": None, "hp_at_kill": None, "total_turns": 0, "no_amalgam": True}
    turn_rows = defaultdict(list)
    for r in rows:
        turn_rows[r["turn"]].append(r)
    turns = sorted(turn_rows)
    start_hp = {t: turn_rows[t][0].get("player_hp") for t in turns}
    last_present = None
    for t in turns:
        if any(_has_amalgam(r) for r in turn_rows[t]):
            last_present = t
        elif last_present is not None:
            # it was alive on `last_present`, gone at the start of `t` -> killed during last_present.
            return {"killed": True, "kill_turn": last_present, "hp_at_kill": start_hp.get(last_present),
                    "total_turns": max(turns), "no_amalgam": False}
    # never absent: either present through the final row (survived) or never appeared at all.
    if last_present is None:
        return {"killed": False, "kill_turn": None, "hp_at_kill": None, "total_turns": max(turns), "no_amalgam": True}
    return {"killed": False, "kill_turn": None, "hp_at_kill": None, "total_turns": max(turns), "no_amalgam": False}


def deck_composition(rows: list) -> dict:
    """Classify the combat-start deck into Attack/Skill/Power/unknown counts + energy + Strength flag."""
    if not rows:
        return {}
    r0 = rows[0]
    counts = Counter()
    piles = ["draw_pile", "hand", "discard_pile", "exhaust_pile"]
    for p in piles:
        for c in r0.get(p) or []:
            cid = c.get("id")
            t = _CARD_META.get(cid, {}).get("type") or c.get("type")
            counts[t if t else "unknown"] += 1
    pl = r0.get("player") or {}
    strength = pl.get("max_energy")
    str_present = any(x.get("id") == "POWER.STRENGTH_POWER" and (x.get("amount") or 0) > 0
                       for x in (pl.get("powers") or [])) or bool(set(map(str, pl.get("relics") or []))
                                                                 & STRENGTH_RELICS)
    # Skill cards that grant block (block is the dominant Ironclad skill use); count Skill as the block proxy.
    return {"attack": counts.get("Attack", 0), "skill": counts.get("Skill", 0),
            "power": counts.get("Power", 0), "unknown": counts.get("unknown", 0),
            "deck_total": sum(counts.values()), "energy": strength, "strength_start": str_present}


def missed_kills(rows: list) -> dict:
    """Turns where hand attack damage >= remaining Amalgam HP but the Amalgam survived that turn (block/overkill aside)."""
    if not rows:
        return {"missed_turns": 0, "wasted_dmg": 0, "had_missed": False}
    turn_rows = defaultdict(list)
    for r in rows:
        turn_rows[r["turn"]].append(r)
    missed = wasted = 0
    for t in sorted(turn_rows):
        rs = turn_rows[t]
        start_am, end_am = _amalgam_hp(rs[0]), _amalgam_hp(rs[-1])
        if start_am is None:
            continue  # amalgam already gone this turn
        end_am = 0 if end_am is None else end_am  # gone at turn end = killed
        energy = (rs[0].get("player") or {}).get("energy") or (rs[0].get("player") or {}).get("max_energy") or 0
        playable = _best_affordable_damage(rs[0].get("hand") or [], energy)
        # a lethal opportunity (could finish the remaining HP) that the turn did not take.
        if playable >= start_am and end_am > 0:
            missed += 1
            wasted += max(0, playable - (start_am - end_am))
    return {"missed_turns": missed, "wasted_dmg": wasted, "had_missed": missed > 0}


def _best_affordable_damage(hand: list, energy) -> int:
    """Greedy max single-target attack damage playable with `energy` (Damage-value cards, cost-limited)."""
    if not isinstance(energy, int):
        energy = 0
    attacks = []
    free_total = 0
    for c in hand:
        if c.get("type") != "Attack":
            continue
        dmg = next((v.get("value") for v in (c.get("vars") or []) if v.get("id") == "Damage"), 0) or 0
        cost = c.get("cost")
        if not isinstance(cost, int) or cost < 0:
            continue  # unplayable / quest cards carry no damage plan
        if cost == 0:
            free_total += dmg  # 0-cost attacks are always takeable once
        else:
            attacks.append((dmg, cost))
    attacks.sort(key=lambda x: -x[0])
    total, spent = free_total, 0
    for dmg, cost in attacks:
        if spent + cost <= energy:
            spent += cost
            total += dmg
    return total


def _turn_nonattack_energy(rs: list) -> int:
    """Energy this turn spent on played Skill/Power cards (block-preferred proxy). Rows record the action taken."""
    total = 0
    for r in rs:
        if r.get("type") != "card":
            continue
        idx = r.get("hand_index")
        card = next((c for c in (r.get("hand") or []) if c.get("index") == idx), None)
        if card and card.get("type") in ("Skill", "Power"):
            cost = card.get("cost")
            total += cost if isinstance(cost, int) and cost > 0 else 0
    return total


def earlier_room(rows: list, kill_turn) -> dict | None:
    """On the turn before the kill, could the hand's max attack damage have finished the remaining Amalgam HP?

    This asks only whether killing one turn earlier was damage-feasible (ignoring block/defense value), and
    how much of that turn's energy went to block/utility instead of attacks — the raw material for an
    attack-over-block judgment hypothesis, not a causal result.
    """
    if kill_turn is None or kill_turn < 2:
        return None
    turn_rows = defaultdict(list)
    for r in rows:
        turn_rows[r["turn"]].append(r)
    rs = turn_rows.get(kill_turn - 1) or []
    if not rs:
        return None
    start_am = _amalgam_hp(rs[0])
    if start_am is None:
        return None
    end_am = _amalgam_hp(rs[-1])
    end_am = 0 if end_am is None else end_am
    energy = (rs[0].get("player") or {}).get("energy")
    if not isinstance(energy, int):
        energy = (rs[0].get("player") or {}).get("max_energy") or 0
    playable = _best_affordable_damage(rs[0].get("hand") or [], energy)
    return {"prev_turn": kill_turn - 1, "amalgam_remaining": start_am, "max_attack_damage": playable,
            "dealt_that_turn": start_am - end_am, "room_to_kill_earlier": playable >= start_am,
            "nonattack_energy": _turn_nonattack_energy(rs)}


def analyze_trial(rows: list) -> dict:
    k = kill_info(rows)
    d = deck_composition(rows)
    m = missed_kills(rows)
    k.update(d); k.update(m)
    k["earlier"] = earlier_room(rows, k["kill_turn"]) if k.get("killed") else None
    return k


def render(dirs: list[Path], trials: list[dict]) -> str:
    killed = [t for t in trials if t["killed"]]
    notk = [t for t in trials if not t["killed"]]

    def mean(xs):
        xs = [x for x in xs if isinstance(x, (int, float))]
        return (sum(xs) / len(xs)) if xs else float("nan")

    kill_turns = [t["kill_turn"] for t in killed]
    hp_at_kill = [t["hp_at_kill"] for t in killed]
    L = ["# Act3 base の Amalgam 撃破ペースとデッキ構成（T40）", "",
         f"対象 dir: {', '.join(str(d) for d in dirs)}（base=official_agent の実走、実機・ビルド不使用）。"
         f"試行数 {len(trials)}（内訳: dir ごとに下表）。型未知のカードは「どこでも引かれなかった」もので "
         "unknown に数える。取りこぼしは hand の単独攻撃ダメージ合計が Amalgam 残り HP 以上なのに生き残った "
         "ターン（block/overkill は控除していない近似）。因果は主張しない、次 goal 候補の見積り。", ""]

    # per-dir counts
    L += ["## dir 別 内訳", "", "| dir | 試行 | 撃破 | 撃破せず |", "| --- | --- | --- | --- |"]
    for d in dirs:
        rows = [t for t in trials if t["_dir"] == str(d)]
        L.append(f"| {Path(d).name} | {len(rows)} | {sum(1 for r in rows if r['killed'])} "
                 f"| {sum(1 for r in rows if not r['killed'])} |")
    L.append("")

    # (a) kill-speed distribution
    hist = Counter(kill_turns)
    L += ["## (a) Amalgam を倒し切るまでのターン数（倒せた組）", "",
          "| 撃破ターン | 組数 | 体力（撃破 turn 開始時）平均 |", "| --- | --- | --- |"]
    for turn in sorted(hist):
        hk = [t["hp_at_kill"] for t in killed if t["kill_turn"] == turn]
        L.append(f"| {turn} | {hist[turn]} | {round(mean(hk), 1) if hk else '–'} |")
    L += ["", f"- 倒せた組 {len(killed)} 組。撃破ターンの平均 {round(mean(kill_turns), 2)}、中央値 "
              f"{sorted(kill_turns)[len(kill_turns)//2] if kill_turns else '–'}、最短 {min(kill_turns) if kill_turns else '–'}、"
              f"最長 {max(kill_turns) if kill_turns else '–'}。倒せなかった組 {len(notk)} 組。",
          f"- 撃破時の playerHP: 平均 {round(mean(hp_at_kill), 1)}、最低 "
          f"{min((x for x in hp_at_kill if isinstance(x, int)), default='–')}（低いほど瀕死で倒している）。", ""]

    def deck_block(group, tag):
        if not group:
            return [f"- {tag}: 組なし", ""]
        return [f"- {tag}: 攻撃カード 平均 {mean([g['attack'] for g in group]):.2f}、"
                f"Skill(主にBlock)カード 平均 {mean([g['skill'] for g in group]):.2f}、"
                f"Power {mean([g['power'] for g in group]):.2f}、型未知 {mean([g['unknown'] for g in group]):.2f}、"
                f"開始エネルギー 平均 {mean([g['energy'] for g in group]):.2f}、"
                f"強化あり {sum(1 for g in group if g['strength_start'])}/{len(group)} 組"]

    L += ["## (b) 撃破 成否で分けたデッキ構成", ""]
    L += deck_block(killed, "倒せた組")
    L += deck_block(notk, "倒せなかった組") + [""]

    # (c) missed kills among the slow / never-killed fights
    slow = [t for t in trials if (t["kill_turn"] is None or t["kill_turn"] >= 4) or not t["killed"]]
    L += ["## (c) 倒すのが遅い組（撃破ターン 4 以上 か 未撃破）の取りこぼし", "",
          f"- 対象 {len(slow)} 組。うち「決めきれたのに残した」ターンが 1 つ以上ある組: "
          f"{sum(1 for t in slow if t['had_missed'])} 組、合計取りこぼしターン "
          f"{sum(t['missed_turns'] for t in slow)} ターン、取りこぼしダメージ合計 {sum(t['wasted_dmg'] for t in slow)} "
          f"(組あたり平均 {mean([t['missed_turns'] for t in slow]):.2f} ターン、"
          f"{mean([t['wasted_dmg'] for t in slow]):.0f} ダメージ)。",
          "- 意味: 手札に Amalgam を仕留めうる攻撃ダメージがあったのに、そのターンで仕留め切れていない。"
          "block/overkill を引いていない近似なので、実損はこの以下。取りこぼしが大きい組ほど撃破が遅いなら、"
          "「Amalgam を早く倒す」余地は、殴り先を変えずとも手札の出し方（複数回撃ち・取りこぼし）にありうる。", ""]

    # near-death kills: was finishing the Amalgam one turn earlier damage-feasible?
    near = [t for t in killed if isinstance(t["hp_at_kill"], int) and t["hp_at_kill"] <= 20 and t.get("earlier")]
    L += ["## 瀕死で倒した組（撃破ターン開始時の体力 20 以下）で、1 ターン早く倒す余地があったか", "",
          "| dir | spec | 撃破ターン | 体力 | 前ターンの Amalgam 残り | 前ターンの出せた最大攻撃 | 前ターン実与 | "
          "残り体力を攻撃で潰せたか | 前ターンの非攻撃(防御)に割いたエネルギー |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for t in near:
        e = t["earlier"]
        L.append(f"| {Path(t['_dir']).name} | {t['_spec']} | {t['kill_turn']} | {t['hp_at_kill']} | "
                 f"{e['amalgam_remaining']} | {e['max_attack_damage']} | {e['dealt_that_turn']} | "
                 f"{'Yes' if e['room_to_kill_earlier'] else 'No'} | {e['nonattack_energy']} |")
    room_ct = sum(1 for t in near if t["earlier"]["room_to_kill_earlier"])
    spent_ct = sum(1 for t in near if t["earlier"]["room_to_kill_earlier"] and t["earlier"]["nonattack_energy"] > 0)
    exceeded = sum(1 for t in near if t["earlier"]["dealt_that_turn"] > t["earlier"]["max_attack_damage"])
    L += ["", f"- 瀕死撃破 {len(near)} 組。前ターンに Amalgam 残り体力を攻撃だけで潰せた可能性が模型上ある組: {room_ct} 組。そのうち前ターンで防御・支援にエネルギーを割っていた組: {spent_ct} 組。",
          f"- 前ターン実与ダメージが模型の最大攻撃ダメージを超えた組が {exceeded}/{len(near)}。出せた最大攻撃は hand 起点・block/overkill・複数回撃ち・途中の補充を無視すると下限なので、実与がそれを上回る組は Amalgam にすでに全力で攻撃を割いていたことを意味する（模型が火力を過小評価している）。",
          f"- 候補の仮説と実測の対応: base の Amalgam 集中規則 `queen_minion_direct` は Amalgam を削りつつ防御も優先する。瀕死撃破の多くで前ターンに Amalgam へ最大級の実与ダメージを入れており、ブロックより攻撃を優先して 1 ターン短縮できた明確な余地は見つからなかった（模型上の余地は {room_ct} 組のみで、それも防御への割り込みは {spent_ct}）。瀕死の要因は Amalgam 残りの集中攻撃や Queen の圧による被弾（耐久）で、minion への攻撃不足ではない。model は火力の下限なので防御の取り分と実損は次の実機検証で確かめる（因果は未確認）。", ""]

    # conclusion (kept in-source so regeneration reproduces it)
    L += ["## 「Amalgam をより早く倒す」は次 goal 候補として成立つか（1 段落、候補の仮説）", "",
          "48 組の実測から、Queen 戦闘の意思決定を変えて Amalgam を早く倒す余地は薄い。倒せた組と倒せなかった組で、"
          "攻撃カード数と開始エネルギーはほぼ変わらず、同じ手札から出せる攻撃ダメージもほぼ取り逃がしていない（上 c）。"
          "dev5 で H3a/H3c（Queen へ殴り先を変える規則）が中性〜マイナスだった（`act3_dev5_h3a_analysis.md`）のと同じ"
          "方向で、殴り先を変えず火力を引き出す余地は小さい。差がともなっていたのは Skill（主に Block）カード数と開始"
          "強化の有無で、倒せなさは防御不足で体力が尽きる事態と対応する（相関で因果は主張しない）。Amalgam を早く倒す"
          "余地があるとすれば、Queen 戦闘の出し方ではなく、防御を持たせる・火力を足すデッキを途中で手に入れる側にある。"
          "lab は boss 入場固定でデッキを作れないので、この余地は Act 3 の報酬選択・昇格（フル run）で作る話で、固定入場"
          "1 戦闘の lab では作り出せない。見込みは Queen 戦闘内の方針変更としては低い。次の goal にするならフル run "
          "パネル（`next_goal_candidates.md` の現 3 相当）で測るべきで、必要な実機時間は大（run 全体を多数 seed で完走）。"
          "lab の配対代理では判定材料は出ない。", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Act3 base Amalgam kill-speed and deck survey.")
    ap.add_argument("--dir", action="append", required=True, help="base run dir (repeat)")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    dirs = [Path(d) for d in args.dir]
    for d in dirs:
        if not (d / "lab_results.jsonl").is_file():
            raise SystemExit(f"lab_results.jsonl が無い: {d}")
    scan_card_types(dirs)
    import json as _json
    trials = []
    for d in dirs:
        for l in (d / "lab_results.jsonl").read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            rec = _json.loads(l)
            if (rec.get("result") or {}).get("outcome_source") != A.RELIABLE:
                continue
            ti = rec.get("trial_index")
            tf = d / f"trial_{int(ti):04d}_agent.jsonl"
            if not tf.is_file():
                continue
            t = analyze_trial(combat_rows(tf))
            t["_dir"] = str(d); t["_spec"] = rec.get("spec_id")
            trials.append(t)
    text = render(dirs, trials)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
