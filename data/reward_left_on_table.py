"""How much deck damage the card-reward policy leaves on the table.

For every card_reward decision, the trace records the three offers and the card taken.  This measures, for
the last decision before each boss fight, the greedy 3-energy damage potential of the deck as taken versus
the same deck with the taken card swapped for the highest-damage offer - the same approximation in both
numbers, so the difference is what the choice cost rather than a fight prediction.
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
BOSSES = {'MONSTER.THE_INSATIABLE': 'Act2boss', 'MONSTER.QUEEN': 'Act3boss'}


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
    # 0-cost attacks (Anger, Rage, Brutality, Bloodletting) never spend energy, so cap the plays.
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


rows = collections.defaultdict(list)
traces = sorted(Path('/Users/mao/workspace/sts2-ai/data').glob('*_agent.jsonl'))
runs = 0
for trace in traces:
    log = trace.with_name(trace.name.replace('_agent.jsonl', '_mod.log'))
    if not log.exists():
        continue
    marks = re.findall(r"Act (\d), Floor (\d+)", log.read_text(encoding='utf-8-sig', errors='replace'))
    if not marks:
        continue
    depth = int(marks[-1][0])
    runs += 1
    last_reward = None
    found = {}
    for line in trace.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        if '"card_reward"' in line:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            deck = record.get('deck')
            offers = record.get('cards') or ()
            taken = record.get('card_id')
            if not deck or not offers or taken is None:
                continue
            def offer_id(card):
                # Pile and offer entries are either {"id": ...} dicts or plain id strings.
                return card.get('id') if isinstance(card, dict) else card

            best = max(offers, key=lambda c: DMG.get(official_agent.CARD_NAMES.get(offer_id(c)) or offer_id(c).replace('CARD.', ''), 0))
            best_id = offer_id(best)
            best_damage = DMG.get(official_agent.CARD_NAMES.get(best_id) or best_id.replace('CARD.', ''), 0)
            taken_damage = DMG.get(official_agent.CARD_NAMES.get(taken) or taken.replace('CARD.', ''), 0)
            swapped = [c for c in deck if c != taken] + ([best_id] if best_damage > taken_damage else [])
            last_reward = (potential(deck), potential(swapped), taken, best_id, taken_damage, best_damage)
            continue
        if '"combat"' not in line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get('phase') != 'combat':
            continue
        for enemy in record.get('enemies') or ():
            key = BOSSES.get(enemy.get('id'))
            if key and key not in found and last_reward is not None:
                found[key] = (depth, last_reward)
    for key, (depth, (actual, swapped, taken, best_id, taken_damage, best_damage)) in found.items():
        rows[(depth, key)].append((swapped - actual, taken, best_id, taken_damage, best_damage))

print('runs read:', runs)
for (depth, key), items in sorted(rows.items()):
    deltas = sorted(x[0] for x in items)
    n = len(items)
    missed = [x for x in items if x[0] > 0]
    print(f'final Act {depth} ✓ {key}: {n} runs  置き換えた場合の増分 中央値 {deltas[n // 2]:3d}  '
          f'75% {deltas[3 * n // 4]:3d}  最大 {deltas[-1]:3d}  高 damage の offer を避けた run {len(missed)}/{n}')
    for delta, taken, best_id, taken_damage, best_damage in sorted(missed, key=lambda t: -t[0])[:5]:
        print(f'   +{delta:3d}: {taken.replace("CARD.",""):22s} dmg {taken_damage:2d}  を {best_id.replace("CARD.",""):22s} dmg {best_damage:2d} の代わりに選んだ')
