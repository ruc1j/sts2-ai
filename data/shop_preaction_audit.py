"""Read each shop visit's offers before the chosen action ran.

`ShopBridge.OfferSummary` is evaluated when the decision is traced, which is after the action has been
executed, so an item bought in a record is already gone from that record's offer list.  The gold field is
the same story: it is the gold after the purchase.  Both can be undone, because the chosen offer is still
identifiable (action + id) and its price is in the record's own `offers`, so gold_before = gold + cost.

Usage: python3 data/shop_preaction_audit.py <trace.jsonl> [...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def chosen_cost(record: dict) -> int:
    """Price of the item this record bought, or 0 when nothing was bought."""
    action = record.get('action')
    if action not in ('buy_card', 'buy_relic', 'buy_potion', 'remove'):
        return 0
    wanted = record.get('card_id') or record.get('relic_id') or record.get('potion_id')
    kind = {'buy_card': 'card', 'buy_relic': 'relic', 'buy_potion': 'potion', 'remove': 'removal'}[action]
    for offer in (record.get('offers') or ()):
        if offer.get('kind') != kind:
            continue
        if kind == 'removal' or offer.get('id') == wanted:
            cost = offer.get('cost')
            return cost if isinstance(cost, int) else 0
    return 0


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
                record = json.loads(line) if '"phase":"shop"' in line else None
                if record is None:
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
            entry_gold = (first.get('gold') or 0) + chosen_cost(first)
            offers = first.get('offers') or ()
            affordable = [offer for offer in offers if offer.get('affordable')]
            bought = [(record.get('action'), record.get('relic_id') or record.get('card_id') or record.get('potion_id'))
                      for record in visit if record.get('action') not in (None, 'skip')]
            print(f'  seq {first.get("seq"):4d} 入店 gold {entry_gold:4d} ✓ 入店時 affordable 出品 {len(affordable)} ✓ '
                  f'内 relic {sum(1 for o in affordable if o.get("kind") == "relic")} ✓ 行動 {[a for a, _ in bought]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
