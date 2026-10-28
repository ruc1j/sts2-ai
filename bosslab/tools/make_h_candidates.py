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


def build(name: str, tag: str, condition: str, header: str, extra_constant: str | None) -> str:
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
    # tags renamed so the trace is distinguishable from base and queenfirst
    for old, tmpl in TAG_TOKENS:
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

for fname, tag, cond, header, constant in [
    ("official_agent_H1.py", "h1", H1_CONDITION, H1_HEADER, H1_CONSTANT),
    ("official_agent_H2.py", "h2", H2_CONDITION, H2_HEADER, None),
]:
    out = build(fname, tag, cond, header, constant)
    path = OUT_DIR / fname
    path.write_text(out, encoding="utf-8")
    print(f"wrote {path} ({len(out.splitlines())} lines)")
