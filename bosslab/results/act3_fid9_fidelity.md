# BossLab 忠実性チェック (T4a)

lab の戦闘開始観測を、plan の entry と spec、および元 run の入場観測と比べる。
不一致は「同じ名前の入場状態が実際には同じ状態でない」こと=勝率比較へのリスク。

### trial_0000_agent.jsonl  (spec e030d2f11e5f, plan deck 27 cards)

- lab first decision: seq 0 turn 1, hand 3, draw 24, hp 77
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 3 種類のうち 全部一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

