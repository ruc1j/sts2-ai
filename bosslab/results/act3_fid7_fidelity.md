# BossLab 忠実性チェック (T4a)

lab の戦闘開始観測を、plan の entry と spec、および元 run の入場観測と比べる。
不一致は「同じ名前の入場状態が実際には同じ状態でない」こと=勝率比較へのリスク。

### trial_0000_agent.jsonl  (spec 09e1ef74cb7c, plan deck 33 cards)

- lab first decision: seq 0 turn 1, hand 7, draw 25, hp 85
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 7 種類のうち 2 種類で不一致（片側だけの preview で比較できない札 1 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る
  - `CARD.HEADBUTT+0+`: lab=[["1", "9", ""]] / orig=[["1", "11", ""]]
  - `CARD.STRIKE_IRONCLAD+0+`: lab=[["1", "6", ""]] / orig=[["1", "8", ""]]

### trial_0001_agent.jsonl  (spec a362ff6f5e4e, plan deck 33 cards)

- lab first decision: seq 0 turn 1, hand 7, draw 25, hp 85
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 7 種類のうち 全部一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0002_agent.jsonl  (spec 4c69c357dcda, plan deck 31 cards)

- lab first decision: seq 0 turn 1, hand 7, draw 24, hp 76
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 6 種類のうち 全部一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0003_agent.jsonl  (spec d22ed45bc52f, plan deck 29 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 24, hp 53
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 5 種類のうち 全部一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0004_agent.jsonl  (spec 62f27302ec36, plan deck 28 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 17, hp 44
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 5 種類のうち 2 種類で不一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る
  - `CARD.ANGER+0+`: lab=[["0", "6", ""]] / orig=[["0", "7", ""]]
  - `CARD.STRIKE_IRONCLAD+0+`: lab=[["1", "6", ""]] / orig=[["1", "7", ""]]

### trial_0005_agent.jsonl  (spec 96c9cc444c23, plan deck 26 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 21, hp 64
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 5 種類のうち 全部一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0006_agent.jsonl  (spec eb8756252bb6, plan deck 24 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 19, hp 67
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 5 種類のうち 1 種類で不一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る
  - `CARD.STRIKE_IRONCLAD+1+ENCHANTMENT.TEZCATARAS_EMBER`: lab=[["0", "9", ""]] / orig=[["0", "15", ""]]

### trial_0007_agent.jsonl  (spec e8b1b9347232, plan deck 23 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 18, hp 56
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 5 種類のうち 全部一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0008_agent.jsonl  (spec 74062b5e0d2d, plan deck 22 cards)

- lab first decision: seq 0 turn 1, hand 3, draw 19, hp 103
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 3 種類のうち 2 種類で不一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る
  - `CARD.POMMEL_STRIKE+1+`: lab=[["1", "10", ""]] / orig=[["1", "18", ""]]
  - `CARD.STRIKE_IRONCLAD+0+`: lab=[["1", "6", ""]] / orig=[["1", "14", ""]]

### trial_0009_agent.jsonl  (spec 8aa46daede55, plan deck 27 cards)

- lab first decision: seq 0 turn 1, hand 3, draw 23, hp 111
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 3 種類のうち 1 種類で不一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る
  - `CARD.STRIKE_IRONCLAD+0+`: lab=[["1", "6", ""]] / orig=[["1", "7", ""]]

### trial_0010_agent.jsonl  (spec e030d2f11e5f, plan deck 27 cards)

- lab first decision: seq 0 turn 1, hand 3, draw 27, hp 77
- lab vs spec: 2 項目で不一致
  - `deck.multiset`: lab={"CARD.DAZED+0+": 3} / spec={}
  - `pile_size.draw_pile`: lab=27 / spec=24
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 2 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 3 種類のうち 全部一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る

### trial_0011_agent.jsonl  (spec 75495c03f631, plan deck 21 cards)

- lab first decision: seq 0 turn 1, hand 5, draw 16, hp 33
- lab vs spec: 一致
- spec vs 元trace: 一致 (抽出の忠実性)
- lab vs 元trace 計: 0 項目
- lab vs 元trace の preview 済みの札の cost / Damage・Block 値: 両側が preview した 5 種類のうち 5 種類で不一致（片側だけの preview で比較できない札 0 種類）。enchantment の amount 違い・relic props 起因の値変更はここで出る
  - `CARD.ANGER+0+`: lab=[["0", "6", ""]] / orig=[["0", "7", ""]]
  - `CARD.BASH+1+`: lab=[["2", "10", ""]] / orig=[["2", "11", ""]]
  - `CARD.EVIL_EYE+0+ENCHANTMENT.NIMBLE`: lab=[["1", "", "8"]] / orig=[["1", "", "10"]]
  - `CARD.POMMEL_STRIKE+1+`: lab=[["1", "10", ""]] / orig=[["1", "11", ""]]
  - `CARD.STRIKE_IRONCLAD+1+`: lab=[["1", "9", ""]] / orig=[["1", "10", ""]]

