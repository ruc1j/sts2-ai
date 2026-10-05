"""Correlate the deck's damage potential with how deep a run gets.

Reads each trace once, streaming, and keeps only what the measurement needs: the last `deck` list seen
before the first record of the Act 2 / Act 3 boss fight.  The potential is a greedy 3-energy upper bound
over the deck's attacks, so it compares decks to each other rather than predicting a fight.
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, '/Users/mao/workspace/sts2-ai')
sys.path.insert(0, '/Users/mao/workspace/sts2-ai/data')
import combat  # noqa: E402
import official_agent  # noqa: E402

DMG = combat.CARD_DAMAGE
COST = combat.CARD_COST


def potential(deck_ids, energy=3):
    attacks = []
    for cid in deck_ids:
        name = official_agent.CARD_NAMES.get(cid) or cid.replace('CARD.', '')
        if name not in combat.ATTACKS:
            continue
        cost = COST.get(name, 1)
        damage = DMG.get(name, 0)
        if damage:
            attacks.append((damage, cost))
    attacks.sort(reverse=True)
    total = 0
    left = energy
    # A 0-cost attack (Anger, Rage, Brutality, Bloodletting) never spends energy, so the greedy loop needs
    # a play cap as well as the energy test - without it it never terminates.
    for _ in range(12):
        pick = None
        for damage, cost in attacks:
            if cost <= left and (pick is None or damage > pick[0]):
                pick = (damage, cost)
        if not pick:
            break
        damage, cost = pick
        left -= cost
        total += damage
    return total


BOSSES = {'MONSTER.THE_INSATIABLE': 'Act2boss', 'MONSTER.QUEEN': 'Act3boss'}
buckets = collections.defaultdict(list)
traces = sorted(Path('/Users/mao/workspace/sts2-ai/data').glob('*_agent.jsonl'))
count = 0
for trace in traces:
    log = trace.with_name(trace.name.replace('_agent.jsonl', '_mod.log'))
    if not log.exists():
        continue
    marks = re.findall(r"Act (\d), Floor (\d+)", log.read_text(encoding='utf-8-sig', errors='replace'))
    if not marks:
        continue
    depth = int(marks[-1][0])
    last_deck = None
    found = {}
    for line in trace.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        if '"deck"' not in line and '"combat"' not in line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        deck = record.get('deck')
        if deck:
            last_deck = deck
            continue
        if record.get('phase') != 'combat':
            continue
        for enemy in record.get('enemies') or ():
            key = BOSSES.get(enemy.get('id'))
            if key and key not in found and last_deck is not None:
                found[key] = (potential(last_deck), len(last_deck))
        if len(found) == len(BOSSES):
            break
    for key, value in found.items():
        buckets[(depth, key)].append(value)
    count += 1

print('runs read:', count)
for (depth, key), items in sorted(buckets.items()):
    values = sorted(x[0] for x in items)
    decks = sorted(x[1] for x in items)
    n = len(items)
    print(f'final Act {depth} ✓ {key}: {n} runs  potential 中央値 {values[n // 2]:3d}  '
          f'25% {values[n // 4]:3d}  75% {values[3 * n // 4]:3d}  deck 中央値 {decks[n // 2]}')
