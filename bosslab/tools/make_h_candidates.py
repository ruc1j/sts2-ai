#!/usr/bin/env python3
"""Generate bosslab/agents/official_agent_H1.py and _H2.py from official_agent.py.

Both are copies of the base that differ only in the Queen-fight target choice, mirroring how
official_agent_queenfirst.py is a copy with only the target choice changed. The single edited region is
the queen_minion_direct short-circuit plus the focused_minions set that gates a forced Amalgam kill;
everything else (block / potion / end_turn / rollout scoring / hand usage) stays byte-identical to the
base. Each generated copy is written by string replacement so the diff against official_agent.py stays
small and reviewable.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # bosslab/tools/ -> repo root
BASE = REPO / "official_agent.py"
OUT_DIR = REPO / "bosslab" / "agents"

text = BASE.read_text(encoding="utf-8-sig")  # base file has a UTF-8 BOM; strip it for the copies

# ---------------------------------------------------------------- common replacements
OLD_MINION = (
    '    queen_minion_ids = {\n'
    '        enemy["combat_id"]\n'
    '        for enemy in observation.get("enemies", ())\n'
    '        if queen_present and enemy.get("id") == "MONSTER.TORCH_HEAD_AMALGAM"\n'
    '    }\n'
)

ID_SETS = (
    '    amalgam_ids = {\n'
    '        enemy["combat_id"]\n'
    '        for enemy in observation.get("enemies", ())\n'
    '        if enemy.get("id") == "MONSTER.TORCH_HEAD_AMALGAM"\n'
    '    }\n'
    '    queen_ids = {\n'
    '        enemy["combat_id"]\n'
    '        for enemy in observation.get("enemies", ())\n'
    '        if enemy.get("id") == "MONSTER.QUEEN"\n'
    '    }\n'
)

OLD_FOCUSED = '    focused_minions = {"MONSTER.TORCH_HEAD_AMALGAM", "MONSTER.KIN_FOLLOWER"}\n'

TAG_TOKENS = [
    ('"rupture_before_queen_focus"', '"rupture_before_{TAG}"'),
    ('"hellraiser_before_queen_focus"', '"hellraiser_before_{TAG}"'),
    ('"inflame_before_queen_focus"', '"inflame_before_{TAG}"'),
    ('"queen_focus_energy"', '"queen_{TAG}_energy"'),
    ('"queen_minion_direct"', '"queen_minion_{TAG}"'),
]


def build(name: str, tag: str, condition: str, header: str, extra_constant: str | None,
          focus_flag: bool = False) -> str:
    src = text
    count = 0

    def sub(old: str, new: str, expect: int = 1) -> None:
        nonlocal src, count
        n = src.count(old)
        assert n == expect, f"{name}: expected {expect} of {old!r}, found {n}"
        src = src.replace(old, new, expect)
        count += 1

    # module docstring + sys.path insertion (the runner launches by absolute path)
    sub("from __future__ import annotations",
        header + "\nfrom __future__ import annotations\n\nimport sys\nfrom pathlib import Path\n\n"
        "# The runner launches this copy by absolute path, so Python puts bosslab/agents/ on sys.path\n"
        "# rather than the repository root where combat.py and act_map.py live. Add the root explicitly.\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))\n", 1)
    if extra_constant:
        sub("CARD_NAMES = {", extra_constant + "\nCARD_NAMES = {", 1)
    # the focus-target selection: swap Amalgam/Queen by the candidate condition
    new_minion = (
        '    # [' + tag.upper() + ' candidate] Aim at the Amalgam only while its condition below holds;\n'
        '    # otherwise the single-target attacks in this short-circuit go to the Queen. Only the focus\n'
        '    # target set differs from the base; the Rupture/Hellraiser/Inflame/Bloodletting setup, the\n'
        '    # block gate and the ordering against lethal are untouched, so the panel measures target choice\n'
        '    # alone. lethal attacks and the AOE branch above still win first.\n'
        + ID_SETS +
        '    ' + condition + '\n'
        '    queen_minion_ids = (amalgam_ids if focus_to_amalgam else queen_ids) if queen_present else set()\n'
    )
    sub(OLD_MINION, new_minion, 1)
    # tags renamed so the trace is distinguishable from base and queenfirst. For the focus arms
    # (H3a/H3c) the queen_minion short-circuit additionally records WHICH enemy it aimed at, so the
    # special-rule state is explicit in the trace without pairing against base: a decision_source of
    # "queen_minion_<tag>_queen" is a divergence from the amalgam-focused base (mirrors the firing_C
    # target-diff in apply_hybrid_rule and the arming rate in act3_h3_firing_model.md).
    for old, tmpl in TAG_TOKENS:
        if focus_flag and old == '"queen_minion_direct"':
            sub(old, '("queen_minion_' + tag + '_amalgam" if focus_to_amalgam else '
                      '"queen_minion_' + tag + '_queen")', 1)
        else:
            sub(old, tmpl.format(TAG=tag), 1)
    # forced-kill priority follows the same focus decision
    new_focused = (
        '    # [' + tag.upper() + ' candidate] Force a lethal Amalgam kill only when this fight is the one\n'
        '    # the short-circuit above decided to focus the Amalgam; otherwise the Queen outranks finishing\n'
        '    # it, matching the target choice above.\n'
        '    focused_minions = (\n'
        '        {"MONSTER.TORCH_HEAD_AMALGAM", "MONSTER.KIN_FOLLOWER"} if focus_to_amalgam\n'
        '        else {"MONSTER.KIN_FOLLOWER"}\n'
        '    )\n'
    )
    sub(OLD_FOCUSED, new_focused, 1)
    return src


H1_HEADER = (
    '"""BossLab 候補エージェント H1 削り済み優先型（official_agent.py のコピー）。\n'
    '\n'
    'Amalgamの実効残HPが閾値QUEENFIRST_H1_AMALGAM_HP以下のときだけAmalgamを殴り、それ以外はQueenを殴る。\n'
    '変更は殴り先だけ。block・ポーション・end_turn・手札の使い方・rollout得点はmainと同じ。\n'
    '\n'
    '閾値の決め方: 下調べ(bosslab/results/act3_queenfirst_hybrid_scan.md)で、baseのdev2/confirm2/confirm3\n'
    '全runの「初回撃破可能ターン」時点でAmalgam実効残HPは最大50（中央値20）まで削れていた。1ターンで\n'
    'Amalgamを落とせる上限が50なので、50以下なら1手番の集中でAmalgam（=Queen戦で唯一のダメージ源）を\n'
    '恒久的に消せる小さな投資、50超ならQueenとの竞速に負ける5〜6手番の削り込み。よってT=50に固定。\n'
    '\n'
    '差分の確認: diff -u official_agent.py bosslab/agents/official_agent_H1.py\n'
    '"""'
)

H2_HEADER = (
    '"""BossLab 候補エージェント H2 脅威型（official_agent.py のコピー）。\n'
    '\n'
    'Amalgamの次手番の予想被ダメージが、今のHP+ブロックで受けきれないときだけAmalgamを殴り、それ以外\n'
    'はQueenを殴る。変更は殴り先だけ。block・ポーション・end_turn・手札の使い方・rollout得点はmainと同じ。\n'
    '\n'
    '予想被ダメージはobservationのintentからbaseが既に算出しているenemy_incoming[combat_id]を用いる\n'
    '（追加情報不要なのでH2は計算可能）。Amalgamの自由な一撃が竞速で自分を殺しうる状況では、そのターン\n'
    'Amalgamを殺して被ダメを止めるのが防御上の必須、それ以外はQueenを削る。\n'
    '\n'
    '差分の確認: diff -u official_agent.py bosslab/agents/official_agent_H2.py\n'
    '"""'
)

H1_CONDITION = (
    '_amalgam_effhp = sum(\n'
    '        _number(enemy_by_id[cid].get("hp")) + _number(enemy_by_id[cid].get("block"))\n'
    '        for cid in amalgam_ids if cid in enemy_by_id\n'
    '    )\n'
    '    focus_to_amalgam = queen_present and 0 < _amalgam_effhp <= QUEENFIRST_H1_AMALGAM_HP'
)
H1_CONSTANT = (
    'QUEENFIRST_H1_AMALGAM_HP = 50  # one-turn-killable ceiling of the Amalgam, see module docstring'
)

H2_CONDITION = (
    '_amalgam_incoming = sum(enemy_incoming.get(cid, 0) for cid in amalgam_ids)\n'
    '    focus_to_amalgam = queen_present and _amalgam_incoming > hp + current_block'
)

# ---------------------------------------------------------------- H3 openers (next-goal design)
# H1/H2 gate on a state the Amalgam only reaches if it is already being chipped, so on a Queen-first
# panel that gate never arms (see act3_dev3_interpretation.md). The H3 designs guarantee chipping the
# Amalgam by arming on turn state or on incoming threat, not on the Amalgam's own low HP.

H3A_CONDITION = (
    '_amalgam_effhp = sum(\n'
    '        _number(enemy_by_id[cid].get("hp")) + _number(enemy_by_id[cid].get("block"))\n'
    '        for cid in amalgam_ids if cid in enemy_by_id\n'
    '    )\n'
    '    _turn = int(_number(observation.get("turn")) or 0)\n'
    '    focus_to_amalgam = queen_present and 0 < _amalgam_effhp and _turn <= QUEENFIRST_H3_OPEN_TURNS'
)

H3A_HEADER = (
    '"""BossLab 候補エージェント H3a 序盤 Amalgam 削り型（official_agent.py のコピー）。\n'
    '\n'
    '最初の QUEENFIRST_H3_OPEN_TURNS プレイヤーターンだけ Amalgam を殴り、以降は Queen を殴る。Amalgam が\n'
    '生きている間は削るので、H1 の ≤50 自己閉鎖（Amalgam を削れる手段が Amalgam を殴ることだけ）を序盤の\n'
    '能動削りで解く。Amalgam が死んだ/消えたターンは実効 HP 0 で Queen へ自己律速で切り替わる。変更殴り先のみ。\n'
    '\n'
    'N の決め方（act3_hybrid_h3_design.md、次 goal 設計で 1 本に固定）: dev2 base 盤面は 1〜2 手番目に Amalgam\n'
    'を殴って 199→158→... と削っている（act3_queenfirst_h1h2_dev2.md の手番表）。1 手番だけでは Amalgam を\n'
    '落とし切らず、2 手番で base と同じ序盤の削り込みを再現しつつ Queen 集中に early に戻る。3 手番超は Queen\n'
    '削りが落ち base へ寄り過ぎる。よって基準 N=2 に固定し、実機では N=1〜4 を sweep して掃き込み域を測る。\n'
    '手番基準なので Queen 優先の自己閉鎖にならない（H1/H3b と違い Amalgam 実効 HP に依存しない）。\n'
    '\n'
    '差分の確認: diff -u official_agent.py bosslab/agents/official_agent_H3a.py\n'
    '"""'
)
H3A_CONSTANT = (
    'QUEENFIRST_H3_OPEN_TURNS = 2  # turns chipping the Amalgam before committing to the Queen; '
    'base per design (act3_hybrid_h3_design.md), sweep 1..4 live'
)

H3C_CONDITION = (
    '_amalgam_incoming = sum(enemy_incoming.get(cid, 0) for cid in amalgam_ids)\n'
    '    _amalgam_effhp = sum(\n'
    '        _number(enemy_by_id[cid].get("hp")) + _number(enemy_by_id[cid].get("block"))\n'
    '        for cid in amalgam_ids if cid in enemy_by_id\n'
    '    )\n'
    '    focus_to_amalgam = queen_present and _amalgam_effhp > 0 and _amalgam_incoming >= QUEENFIRST_H3_DANGER_FRAC * (hp + current_block)'
)

H3C_HEADER = (
    '"""BossLab 候補エージェント H3c 危険前に削り型（official_agent.py のコピー）。\n'
    '\n'
    'Amalgam の次手番の予想被ダメが HP+ブロックの QUEENFIRST_H3_DANGER_FRAC 割以上で、かつ Amalgam が\n'
    '生きている間だけ Amalgam を殴り、それ以外 Queen を殴る。自 HP 基準なので Amalgam 実効 HP が低くなくても\n'
    '1 手番目から発火し、H1 と違い削ることを保証する。H2（被ダメが HP+blk を超えた時だけ）より発火が早く、\n'
    '常時削りに近い。変更殴り先のみ。\n'
    '\n'
    'frac の決め方（act3_hybrid_h3_design.md、次 goal 設計で 1 本に固定）: Amalgam は Queen 戦で唯一の定常\n'
    'ダメージ源なので、自分を殺しうる水準で削るのは防御上の必須。H2 と同じ「超える」判定(>100%)では遅すぎ、\n'
    'base と H1/H2 の中間を狙うため 5 割(0.5)を基準に固定した。0.5 未満（Amalgam が自分を殺せない手番）は Queen\n'
    'に切り替わり Queen 集中が残る。実機では 0.4〜0.75 を sweep して over-invest（Amalgam 処理に割き過ぎ）と\n'
    'Queen 集中の取り分を測る。被ダメ脅威基準なので Amalgam 実効 HP に依存せず発火＝自己閉鎖しない。\n'
    '\n'
    '差分の確認: diff -u official_agent.py bosslab/agents/official_agent_H3c.py\n'
    '"""'
)
H3C_CONSTANT = (
    'QUEENFIRST_H3_DANGER_FRAC = 0.5  # Amalgam next-hit fraction of (hp+block) that arms the chip; '
    'base per design (act3_hybrid_h3_design.md), sweep 0.4..0.75 live'
)

H3B_CONDITION = (
    '_amalgam_effhp = sum(\n'
    '        _number(enemy_by_id[cid].get("hp")) + _number(enemy_by_id[cid].get("block"))\n'
    '        for cid in amalgam_ids if cid in enemy_by_id\n'
    '    )\n'
    '    focus_to_amalgam = queen_present and 0 < _amalgam_effhp <= QUEENFIRST_H3_AMALGAM_HP'
)
H3B_HEADER = (
    '"""BossLab 候補エージェント H3b 閾値上げ型（official_agent.py のコピー）。H1 と同じ形、閾値のみ変更。\n'
    '\n'
    'Amalgam 実効残 HP が QUEENFIRST_H3_AMALGAM_HP 以下なら Amalgam、それ以外 Queen。H1(=50) を 150 に上げて\n'
    'トリガー発火を検証する診断用。入場 199 から Queen 優先で削らなければ 150 にも届かず発火しない可能性が\n'
    '高い（自己閉鎖の診断）。変更殴り先と閾値のみ。\n'
    '\n'
    '差分の確認: diff -u official_agent.py bosslab/agents/official_agent_H3b.py\n'
    '"""'
)
H3B_CONSTANT = (
    'QUEENFIRST_H3_AMALGAM_HP = 150  # raised Amalgam-effhp ceiling (diagnostic vs H1=50)'
)

for fname, tag, cond, header, constant, focus_flag in [
    ("official_agent_H1.py", "h1", H1_CONDITION, H1_HEADER, H1_CONSTANT, False),
    ("official_agent_H2.py", "h2", H2_CONDITION, H2_HEADER, None, False),
    ("official_agent_H3a.py", "h3a", H3A_CONDITION, H3A_HEADER, H3A_CONSTANT, True),
    ("official_agent_H3b.py", "h3b", H3B_CONDITION, H3B_HEADER, H3B_CONSTANT, False),
    ("official_agent_H3c.py", "h3c", H3C_CONDITION, H3C_HEADER, H3C_CONSTANT, True),
]:
    out = build(fname, tag, cond, header, constant, focus_flag)
    path = OUT_DIR / fname
    path.write_text(out, encoding="utf-8")
    print(f"wrote {path} ({len(out.splitlines())} lines)")
