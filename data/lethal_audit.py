"""Audit missed lethals in Act 2 boss fights: was a killing move available in the model, and was it played?

For every decision in a THE_INSATIABLE fight we rebuild the model state from the observation, try every
legal action, and ask whether any of them would have killed everything left.  A decision where a kill was
available and the recorded action was not a kill is a missed lethal - either the agent's ranking passed it
up, or the model prices our damage wrong.
"""
import json
import random
import sys
import collections
from pathlib import Path

tree = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 25
sys.path.insert(0, tree)
sys.path.insert(0, f'{tree}/data')

import combat  # noqa: E402
import official_agent  # noqa: E402
from model_match_audit import combat_records, merged_enemy_data, model_state, recorded_action, same_fight  # noqa: E402

TARGET = 'MONSTER.THE_INSATIABLE'
data = merged_enemy_data()
traces = sorted(Path(f'{tree}/data').glob('*_agent.jsonl'))
stats = collections.Counter()
misses = []
fights_audited = 0

for trace in traces:
    if fights_audited >= limit:
        break
    records = combat_records(trace)
    in_fight = False
    official_agent._reset_play_counters()
    previous = None
    for index, record in enumerate(records):
        ids = frozenset(e.get('combat_id') for e in record.get('enemies') or () if e.get('combat_id'))
        hit = any(e.get('id') == TARGET for e in record.get('enemies') or ())
        if not hit:
            if in_fight:
                in_fight = False
            official_agent._PENDING_ACTION = previous
            previous = None
            official_agent._advance_play_counters(record)
            continue
        if not in_fight:
            in_fight = True
            fights_audited += 1
        official_agent._PENDING_ACTION = previous
        previous = None
        if record.get('card_id'):
            previous = {"type": "card", "card_id": record['card_id'], "hand_index": record.get("hand_index", 0)}
        elif record.get('action_type') == 'end_turn':
            previous = {"type": "end_turn"}
        state = model_state(record, data)
        if state is None:
            official_agent._advance_play_counters(record)
            continue
        actions = combat.legal_actions(state)
        lethal_options = []
        for action in actions:
            try:
                after = combat.step(state, action, data, random.Random(record['seq']))
            except Exception:
                continue
            if all(enemy.hp <= 0 for enemy in after.enemies):
                lethal_options.append(action)
        played = recorded_action(record, state, data)
        stats['decisions'] += 1
        if lethal_options:
            stats['lethal available'] += 1
            if played in lethal_options:
                stats['lethal taken'] += 1
            elif played == 'End turn' or played is None:
                stats['lethal missed'] += 1
                misses.append((trace.name[:-len('_agent.jsonl')].rsplit('_', 1)[-1], record['seq'], record.get('turn'),
                               lethal_options[:3], played, [(e.model, e.hp) for e in state.enemies]))
            else:
                stats['lethal available, different play'] += 1
                misses.append((trace.name[:-len('_agent.jsonl')].rsplit('_', 1)[-1], record['seq'], record.get('turn'),
                               lethal_options[:3], played, [(e.model, e.hp) for e in state.enemies]))
        official_agent._advance_play_counters(record)

print(f'{TARGET} fights audited: {fights_audited}')
print(dict(stats))
for seed, seq, turn, lethal, played, enemies in misses[:14]:
    print(f'   seed {seed} seq {seq} turn {turn}: enemies {enemies}  lethal {lethal}  played {played!r}')
