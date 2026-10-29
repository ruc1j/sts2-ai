## 集計

- 比較 trial 数: 12
- spec entry と完全一致(lab vs spec 一致): 10 / 12
- 不一致項目の内訳(項目→該当 trial 数):
  - `enemies.id_hp_maxhp`: 1
  - `deck.multiset`: 1
  - `pile_size.draw_pile`: 1

## RELIC.ROYAL_POISON 所持組の HP 漂移(927f26f の成否)

該当 2 組のうち lab hp が spec(記録) hp に一致: 2 組
- trial 0002 (spec 4c69c357dcda, RELIC.ROYAL_POISON 所持): lab hp=76 / spec(=記録) hp=76 / 元trace hp=76 → HP 一致(修正 927f26f で記録値に着地)
- trial 0004 (spec 62f27302ec36, RELIC.ROYAL_POISON 所持): lab hp=44 / spec(=記録) hp=44 / 元trace hp=44 → HP 一致(修正 927f26f で記録値に着地)
