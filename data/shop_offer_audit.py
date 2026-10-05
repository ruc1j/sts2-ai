"""Measure what the shops offered and what we did about it.

Old shop traces record only the chosen action (`buy_card`, `skip`, ...), so a relic that was offered and
declined left no evidence.  ShopBridge now traces `offers` (kind, id, cost, affordable) beside each shop
decision; this tool reads either shape and reports the offer rate, the purchase rate given an offer, and
the gold we held at the decision.  Traces are streamed, never materialised whole.

Usage: python3 data/shop_offer_audit.py [data/*_agent.jsonl ...]
"""
from __future__ import annotations

import collections
import glob
import json
import sys
from pathlib import Path


def iter_records(path: Path):
    with path.open('r', encoding='utf-8-sig', errors='replace') as handle:
        for line in handle:
            if '"phase":"shop"' not in line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def main(argv: list[str]) -> int:
    paths = argv[1:] or sorted(glob.glob('data/*_agent.jsonl'))
    shop_runs = 0
    decisions = collections.Counter()
    offer_shape = collections.Counter()
    relic_offers = collections.Counter()
    relic_costs: list[int] = []
    relic_buys = 0
    gold_at_relic_offer: list[int] = []
    skipped_while_relic_affordable = 0
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        seen_relic_offer = False
        bought_relic = False
        for record in iter_records(path):
            action = record.get('action')
            decisions[action] += 1
            offers = record.get('offers')
            if offers:
                offer_shape['offers ✓ (new traces)'] += 1
                relics = [offer for offer in offers if offer.get('kind') == 'relic']
            else:
                legal = [a for a in (record.get('legal_actions') or ()) if isinstance(a, dict)]
                offer_shape['offers ✗ (old traces)'] += 1
                relics = [{'id': a.get('relic_id'), 'cost': None, 'affordable': True}
                          for a in legal if a.get('type') == 'buy_relic']
            if relics:
                seen_relic_offer = True
                relic_offers['shop record で relic 出品 ✓'] += 1
                for relic in relics:
                    if isinstance(relic.get('cost'), int):
                        relic_costs.append(relic['cost'])
                    if relic.get('affordable'):
                        gold = record.get('gold')
                        if isinstance(gold, int):
                            gold_at_relic_offer.append(gold)
                if action == 'buy_relic':
                    relic_buys += 1
                elif action == 'skip' and any(relic.get('affordable') for relic in relics):
                    skipped_while_relic_affordable += 1
            elif action == 'buy_relic':
                relic_buys += 1
        if seen_relic_offer:
            shop_runs += 1
            if bought_relic:
                decisions['run が relic を買った ✓'] += 1

    total = sum(decisions[action] for action in
                ('buy_card', 'buy_relic', 'buy_potion', 'remove', 'skip'))
    print(f'trace {len(paths)} 件 ✓ shop decision {total} ✓')
    print('  decision 内訳:', dict(decisions.most_common(8)))
    print('  出品情報の形状:', dict(offer_shape))
    print(f'  relic 出品ありの shop decision: {relic_offers["shop record で relic 出品 ✓"]}')
    if relic_costs:
        relic_costs.sort()
        print(f'  relic 価格: 最小 {relic_costs[0]} ✓ 中央値 {relic_costs[len(relic_costs) // 2]} ✓ 最大 {relic_costs[-1]}')
    if gold_at_relic_offer:
        gold_at_relic_offer.sort()
        broke = sum(1 for gold in gold_at_relic_offer if gold < (relic_costs[len(relic_costs) // 2] if relic_costs else 100))
        print(f'  relic 出品時に買えた gold: 中央値 {gold_at_relic_offer[len(gold_at_relic_offer) // 2]} ✓ 割高で買えなかった件数 {broke}')
    print(f'  relic 出品ありで buy_relic: {relic_buys} ✓ / 出品あり decision {relic_offers["shop record で relic 出品 ✓"]}')
    print(f'  relic が買えるのに skip ✓: {skipped_while_relic_affordable}')
    print(f'  relic を1つ以上買った run: {decisions["run が relic を買った ✓"]} ✓ 出品に当たった run {shop_runs}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
