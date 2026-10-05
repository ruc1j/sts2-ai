"""Where gold goes in a run.

Gold is exported on shop decisions and on card_reward decisions, so the level can be sampled at every
decision point and the gaps between them show earning and spending.  This exists because the relic
pricing panel turned out inert: priced relics cost 155-287 but the gold at shop decisions averaged 180
and 196 on the seeds where nothing changed, so the shop policy never had a chance to act.  Traces are
streamed, never materialised whole.

Usage: python3 data/gold_flow_audit.py [data/*_agent.jsonl ...]
"""
from __future__ import annotations

import glob
import json
import statistics
import sys
from pathlib import Path


def samples(path: Path):
    """Yield (seq, phase, action, gold) for every record that exports gold."""
    with path.open('r', encoding='utf-8-sig', errors='replace') as handle:
        for line in handle:
            if '"phase":"shop"' in line or '"phase":"card_reward"' in line:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                gold = record.get('gold')
                if not isinstance(gold, int):
                    gold = (record.get('player') or {}).get('gold')
                if not isinstance(gold, int):
                    continue
                yield (record.get('seq'), record.get('phase'), record.get('action'), gold)


def main(argv: list[str]) -> int:
    paths = argv[1:] or sorted(glob.glob('data/*_agent.jsonl'))
    gold_at_shop: list[int] = []
    max_gold: list[int] = []
    rows: list[tuple[str, list[tuple[int, str, str | None, int]]]] = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        got = list(samples(path))
        if not got:
            continue
        seed = path.name[:-len('_agent.jsonl')].rsplit('_', 1)[-1]
        rows.append((seed, got))
        gold_at_shop.extend(gold for _, phase, _, gold in got if phase == 'shop')
        max_gold.append(max(gold for _, _, _, gold in got))

    print(f'trace {len(rows)} 件 ✓ gold の観測点 {sum(len(g) for _, g in rows)} ✓')
    if not rows:
        return 0
    print(f'  shop 時点の gold: 中央値 {statistics.median(gold_at_shop)} ✓ 最小 {min(gold_at_shop)} ✓ 最大 {max(gold_at_shop)} ✓')
    print(f'  run 中の gold 最大値: 中央値 {statistics.median(max_gold)} ✓ 最小 {min(max_gold)} ✓ 最大 {max(max_gold)} ✓')
    relic_floor = 155
    print(f'  最高 gold が relic 最安値 {relic_floor} に届かなかった run: '
          f'{sum(1 for m in max_gold if m < relic_floor)} / {len(max_gold)} ✓')
    print('  run 毎の gold 推移 ✓（seq ✓ phase ✓ action ✓ gold ✓、shop ✓ のみ明示 ✓）:')
    for seed, got in rows:
        shop = [(seq, action, gold) for seq, phase, action, gold in got if phase == 'shop']
        peak = max(gold for _, _, _, gold in got)
        print(f'   seed {seed}: peak {peak} ✓ shop 時点 {[ (s, a, g) for s, a, g in shop ][:12]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
