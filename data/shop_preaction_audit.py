"""Read each shop visit's offers before the chosen action ran.

Use the bridge's gold_before / offers_before snapshot when available. Legacy traces contain only the
post-purchase state. A first removal can be reconstructed from its retained price; a bought item may
already be missing or restocked, so other legacy purchases are reported as unknown rather than free.

Usage: python3 data/shop_preaction_audit.py <trace.jsonl> [...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def chosen_cost(record: dict) -> int | None:
    """Return the recorded purchase price, 0 for no purchase, or None if the price is missing."""
    action = record.get('action')
    if record.get('purchased') is False or action not in ('buy_card', 'buy_relic', 'buy_potion', 'remove'):
        return 0
    wanted = record.get('card_id') or record.get('relic_id') or record.get('potion_id')
    kind = {'buy_card': 'card', 'buy_relic': 'relic', 'buy_potion': 'potion', 'remove': 'removal'}[action]
    for offer in (record.get('offers_before', record.get('offers')) or ()):
        if offer.get('kind') != kind:
            continue
        if kind == 'removal' or offer.get('id') == wanted:
            cost = offer.get('cost')
            return cost if isinstance(cost, int) else None
    return None


def preaction_state(record: dict) -> tuple[int | None, list[dict] | None]:
    """Recover the first decision's state without treating post-purchase flags as entry flags."""
    if isinstance(record.get('gold_before'), int) and isinstance(record.get('offers_before'), list):
        return record['gold_before'], record['offers_before']
    gold = record.get('gold')
    offers = record.get('offers')
    if not isinstance(gold, int) or not isinstance(offers, list):
        return None, None
    cost = chosen_cost(record)
    if record.get('action') == 'skip' or record.get('purchased') is False:
        return gold, offers
    if record.get('action') != 'remove' or cost is None:
        return None, None
    gold += cost
    # Removing a card leaves the shop's other stock and prices intact. The removal slot was
    # stocked before this action even though its post-action affordable flag is false.
    restored = [
        dict(offer, affordable=(offer.get('stocked', True) or offer.get('kind') == 'removal')
             and isinstance(offer.get('cost'), int) and offer['cost'] <= gold)
        for offer in offers
    ]
    return gold, restored


def main(argv: list[str]) -> int:
    for raw in argv[1:]:
        path = Path(raw)
        if not path.exists():
            print(f'{path}: 無し ✗')
            continue
        visits: list[list[dict]] = []
        current: list[dict] | None = None
        with path.open('r', encoding='utf-8-sig', errors='replace') as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except ValueError:
                    record = None
                if not isinstance(record, dict) or record.get('phase') != 'shop':
                    if current:
                        visits.append(current)
                    current = None
                    continue
                if current is None:
                    current = []
                current.append(record)
        if current:
            visits.append(current)
        print(f'{path.name}')
        for visit in visits:
            first = visit[0]
            entry_gold, offers = preaction_state(first)
            bought = [(record.get('action'), record.get('relic_id') or record.get('card_id') or record.get('potion_id'))
                      for record in visit if record.get('action') not in (None, 'skip')
                      and record.get('purchased') is not False]
            if entry_gold is None or offers is None:
                print(f'  seq {first.get("seq"):4d} 入店状態は不明（購入前の記録が不足） 行動 {[a for a, _ in bought]}')
                continue
            affordable = [offer for offer in offers if offer.get('affordable')]
            print(f'  seq {first.get("seq"):4d} 入店 gold {entry_gold:4d} 購入可能な出品 {len(affordable)} '
                  f'うち relic {sum(1 for o in affordable if o.get("kind") == "relic")} 行動 {[a for a, _ in bought]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
