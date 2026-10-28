# BossLab 忠実性チェック (T4a)

lab の戦闘開始観測を、plan の entry と spec、および元 run の入場観測と比べる。
不一致は「同じ名前の入場状態が実際には同じ状態でない」こと=勝率比較へのリスク。

### trial_0000_agent.jsonl  (spec bf5c0080839c, plan deck 21 cards)

- lab first decision: seq 0 turn 1, hand 3, draw 17, hp 97
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 0 種類のうち 全部一致（片側だけの preview で比較できない札 5 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0001_agent.jsonl  (spec 897931d3b0da, plan deck 28 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 23, hp 74
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 2 種類のうち 全部一致（片側だけの preview で比較できない札 6 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0002_agent.jsonl  (spec 83e6a3465fde, plan deck 31 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 26, hp 79
- lab vs spec: 2 項目で不一致
  - `pile_size.hand`: lab=5 / spec=6
  - `pile_size.draw_pile`: lab=26 / spec=25
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 2 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 2 種類のうち 全部一致（片側だけの preview で比較できない札 7 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る
- 最初の判断行のプレイ済み counter: lab={"cards_this_turn": 0, "attacks_this_turn": 0, "skills_this_turn": 0} / orig={}。orig 側が 0 でなければ元trace の入場観測が戦闘途中で、lab はこの counter を復元できない（Perfected Strike 等の初手威力がずれる）
- hand 5 / draw 26（lab）vs 6 / 25（記録=元trace）の原因（T21.3 で確定、注入の帰結で戦略差ではない）: 枚数差は RELIC.PENDULUM が実走の最初のターン開始（カウンタ wrap、Pendulum.cs:75-90）で 1 枚引いた分、lab は per-relic のカウンタ（trace に出ない）を復元できず引かない。中身の差は RELIC.STONE_CRACKER を defer したことで開戦手札を配る CombatCardSelection RNG stream（StoneCracker.cs:20-28）が実走とずれ別の 5 枚が配られる。deck 31 枚 multiset と各札の cost/Block・Damage は一致（上の preview 一致の項目）。判定では STONE_CRACKER / PENDULUM spec の開戦手札の枚数・構成差は無視する（同じ entry の base 候補間配対では両腕に同じ制約）。詳細は bosslab/plans/bosslab_act3_plan_confirm4.md の除外条件に記録。

### trial_0003_agent.jsonl  (spec 703d7333c072, plan deck 30 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 25, hp 77
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 3 種類のうち 全部一致（片側だけの preview で比較できない札 4 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0004_agent.jsonl  (spec 1a05bb73e94b, plan deck 32 cards)

- lab first decision: seq 0 turn 1, hand 3, draw 29, hp 86
- lab vs spec: 1 項目で不一致
  - `player.hp`: lab=86 / spec=90
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 1 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 1 種類のうち 全部一致（片側だけの preview で比較できない札 4 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る
- 最初の判断行のプレイ済み counter: lab={"cards_this_turn": 0, "attacks_this_turn": 0, "skills_this_turn": 0} / orig={}。orig 側が 0 でなければ元trace の入場観測が戦闘途中で、lab はこの counter を復元できない（Perfected Strike 等の初手威力がずれる）

### trial_0005_agent.jsonl  (spec c77f7c059684, plan deck 28 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 23, hp 85
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 0 種類のうち 全部一致（片側だけの preview で比較できない札 9 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る
- 最初の判断行のプレイ済み counter: lab={"cards_this_turn": 0, "attacks_this_turn": 0, "skills_this_turn": 0} / orig={}。orig 側が 0 でなければ元trace の入場観測が戦闘途中で、lab はこの counter を復元できない（Perfected Strike 等の初手威力がずれる）

### trial_0006_agent.jsonl  (spec f737cab6f8b6, plan deck 32 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 27, hp 94
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 2 種類のうち 全部一致（片側だけの preview で比較できない札 6 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0007_agent.jsonl  (spec 624ae0d1306b, plan deck 24 cards)

- lab first decision: seq 0 turn 1, hand 3, draw 20, hp 90
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 1 種類のうち 全部一致（片側だけの preview で比較できない札 4 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0008_agent.jsonl  (spec e75781521da8, plan deck 26 cards)

- lab first decision: seq 0 turn 1, hand 7, draw 19, hp 75
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 2 種類のうち 全部一致（片側だけの preview で比較できない札 9 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0009_agent.jsonl  (spec 739389f7cb7f, plan deck 31 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 26, hp 101
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 4 種類のうち 全部一致（片側だけの preview で比較できない札 2 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る
- 最初の判断行のプレイ済み counter: lab={"cards_this_turn": 0, "attacks_this_turn": 0, "skills_this_turn": 0} / orig={}。orig 側が 0 でなければ元trace の入場観測が戦闘途中で、lab はこの counter を復元できない（Perfected Strike 等の初手威力がずれる）

### trial_0010_agent.jsonl  (spec 59ed603b4b73, plan deck 31 cards)

- lab first decision: seq 0 turn 1, hand 3, draw 28, hp 86
- lab vs spec: 1 項目で不一致
  - `player.hp`: lab=86 / spec=90
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 1 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 0 種類のうち 全部一致（片側だけの preview で比較できない札 6 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る
- 最初の判断行のプレイ済み counter: lab={"cards_this_turn": 0, "attacks_this_turn": 0, "skills_this_turn": 0} / orig={}。orig 側が 0 でなければ元trace の入場観測が戦闘途中で、lab はこの counter を復元できない（Perfected Strike 等の初手威力がずれる）

### trial_0011_agent.jsonl  (spec bbbfd4fc2927, plan deck 28 cards)

- lab first decision: seq 0 turn 1, hand 6, draw 23, hp 59
- lab vs spec: 2 項目で不一致
  - `deck.multiset`: lab={"CARD.STOMP+0+": 1} / spec={}
  - `pile_size.draw_pile`: lab=23 / spec=22
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 2 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 1 種類のうち 全部一致（片側だけの preview で比較できない札 10 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

