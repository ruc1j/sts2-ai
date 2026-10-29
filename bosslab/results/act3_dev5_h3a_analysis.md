# dev5 H3a と base の戦闘別 検証（T38・実測後の解析）

`data/bosslab_act3_dev5_base`（base）対 `data/bosslab_act3_dev5_H3a`（H3a、序盤 N=2 ターン Queen 集中）。
実走結果は leader（firing 11/12、Queen 削り 候補優5/base優5/同値2、総火力/ターン 42.6→37.6、勝ち 2→1）。
表は `bosslab/tools/trace_turn_diff.py` の生成、全12組の完全版は `bosslab/results/act3_dev5_h3a_turn_diff.md`。
本 doc は 74062b5e0d2d と、他に H3a が悪化した eb8756252bb6 / e8b1b9347232 / 09e1ef74cb7c を取り上げる。
`*` は base と cand で単独攻撃の殴り先が別れた turn。HP は各 turn 開始時点。攻撃 intent は Amalgam の次に
予定された攻撃ダメージ（repeats 込み、block 控除前）。playerHP 最低は turn 中の最小。実機・ビルド不使用。

## 結論

base が勝てた理由は「Amalgam を殴らなかった」ことではない。逆で、base は Amalgam を殴り切って倒し、
その後に Queen へ切った。base は Amalgam を倒したターン以降 Amalgam の攻撃が 0 になり（表中 a intent 0）、
体力を保って Queen を 400 から削り切った。H3a は序盤2ターン Amalgam を削った直後、Amalgam が 74〜130 HP
で生きているうちに Queen へ切り替えた。残った Amalgam が毎ターン 22〜63 の攻撃を続けたため体力を削られ、
勝てる戦いで敗れた（74062b5e0d2d）。H3a の「序盤2ターンで Queen へ」は、Amalgam を倒し切る前に手を
引くため機能していない。

## 1. 戦闘別のターン照合

### 74062b5e0d2d（base 勝 / H3a 敗）

base は T1-6 で Amalgam を 199 から 0 に削り切り、T7 以降 Amalgam の攻撃が消えて Queen へ集中、Queen を
114 まで削って勝った。H3a は T3 で Queen へ切り替え Amalgam を 74〜98 で放置、T7-9 に Amalgam intent が
27・28・63 へ膨らみ playerHP 最低が 2 まで落ち敗北。

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam 次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BASH→amalgam~18, IRON_WAVE→amalgam~7 | BASH→amalgam~18, IRON_WAVE→amalgam~7 | 199/199 | 400/400 | 18/18 | 103/103 |
| 2 | POMMEL_STRIKE→amalgam~10, PERFECTED_STRIKE→amalgam~None, STRIKE→amalgam~6 | POMMEL_STRIKE→amalgam~10, PERFECTED_STRIKE→amalgam~None, STRIKE→amalgam~6 | 171/171 | 400/400 | 18/18 | 102/102 |
| 3 * | POMMEL_STRIKE→amalgam~9.75, STRIKE→amalgam~6.75 | POMMEL_STRIKE→queen~9.75, STRIKE→queen~6.75 | 98/98 | 400/400 | 36/36 | 94/94 |
| 4 * | POMMEL_STRIKE→amalgam~9.75, POMMEL_STRIKE→amalgam~9.75, IRON_WAVE→amalgam~6.0 | POMMEL_STRIKE→queen~9.75, POMMEL_STRIKE→queen~9.75, IRON_WAVE→queen~6.0 | 74/98 | 400/376 | 22/22 | 67/67 |
| 5 * | UPPERCUT→amalgam~12.0, STRIKE→amalgam~6.75 | UPPERCUT→queen~12.0, STRIKE→queen~6.75 | 50/98 | 400/372 | 24/24 | 59/59 |
| 6 * | PERFECTED_STRIKE→amalgam~None, BASH→amalgam~9.75 | BASH→queen~9.75, POMMEL_STRIKE→queen~9.75, ANGER→queen~6.75 | 28/98 | 400/370 | 48/48 | 50/44 |
| 7 * | PERFECTED_STRIKE→queen~None, IRON_WAVE→queen~6.0 | UPPERCUT→queen~12.0 | None/98 | 400/353 | 0/27 | 50/26 |
| 8 * | UPPERCUT→queen~12.0 | IRON_WAVE→queen~6.0, ANGER→queen~6.75 | None/98 | 367/335 | 0/28 | 44/13 |
| 9 * | BASH→queen~9.75 | − | None/74 | 316/295 | 0/63 | 33/2 |
| 10 | − | − | None/None | 219/None | 0/None | 33/None |
| 11 * | IRON_WAVE→queen~7.5, BASH→queen~9.75, IRON_WAVE→queen~6.0 | − | None/None | 182/None | 0/None | 30/None |
| 12 * | UPPERCUT→queen~12.0, ANGER→queen~6.75 | − | None/None | 114/None | 0/None | 25/None |

### eb8756252bb6（base 敗 / H3a 敗）

base は T1-5 で Amalgam を 0 にした（T6 以降 intent 0）。H3a は T3 で Queen へ切り替え Amalgam を 130 で
放置（削り 69 のみ）。Amalgam intent が T6 に 48。base は Amalgam を倒したうえで Queen を 261 まで削り、
H3a より遠くまで進んだが両敗。

| turn | base 攻撃先 | cand 攻撃先 | Amalgam HP base/cand | QueenHP base/cand | Amalgam intent(base/cand) | playerHP最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | POMMEL→amalgam, IRON_WAVE→amalgam | 同左 | 199/199 | 400/400 | 13/13 | 67/67 |
| 2 | TWIN_STRIKE→amalgam×3 | 同左 | 179/179 | 400/400 | 18/18 | 67/67 |
| 3 * | PERFECTED_STRIKE→amalgam | PERFECTED_STRIKE→queen | 130/130 | 400/400 | 36/36 | 49/49 |
| 4 * | STRIKE・POMMEL・PERFECTED・STRIKE→amalgam | 同 4 枚を→queen | 102/130 | 400/372 | 22/22 | 19/19 |
| 5 * | STRIKE→amalgam, STRIKE→queen | STRIKE→queen×2 | 10/130 | 400/331 | 24/24 | 4/4 |
| 6 | TWIN_STRIKE→queen, STRIKE→queen | 同左 | None/130 | 400/329 | 0/48 | 4/34 |
| 7 * | STRIKE・POMMEL・IRON_WAVE→queen | 攻撃なし | None/None | 363/None | 0/None | 6/None |
| 8 * | PERFECTED・STRIKE→queen | 攻撃なし | None/None | 318/None | 0/None | 5/None |
| 9 * | TWIN_STRIKE・STRIKE→queen | 攻撃なし | None/None | 261/None | 0/None | 5/None |

### e8b1b9347232（base 敗 / H3a 敗）

base は T1-3 で Amalgam を 0 にした。H3a は T3 で Queen へ切り替え Amalgam を 101 で放置。Amalgam が
生きているぶん H3a は playerHP 最低 2 まで削られ、base（7）より手前で折れた。

| turn | base 攻撃先 | cand 攻撃先 | Amalgam HP base/cand | QueenHP base/cand | Amalgam intent(base/cand) | playerHP最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BASH・MAUL・STRIKE×2→amalgam | 同左 | 199/199 | 400/400 | 13/13 | 56/56 |
| 2 | UNRELENTING→amalgam, HEADBUTT→amalgam | 同左 | 153/153 | 400/400 | 18/18 | 56/56 |
| 3 * | BLUDGEON・UNRELENTING・PERFECTED・MAUL→amalgam | 同 4 枚を→queen | 101/101 | 400/400 | 36/36 | 38/38 |
| 4 | MAUL→queen, STRIKE→queen | 同左 | None/101 | 400/329 | 0/16 | 38/11 |
| 5 | BLUDGEON→queen | 同左 | None/101 | 376/322 | 0/18 | 20/2 |
| 6 * | MAUL→queen×2 | 攻撃なし | None/None | 349/None | 0/None | 7/None |
| 7 * | BLUDGEON→queen | 攻撃なし | None/None | 299/None | 0/None | 7/None |

### 09e1ef74cb7c（base 敗 / H3a 敗）

base は T1-6 で Amalgam を 0 にした。H3a は T3 で Queen へ切り替え Amalgam を 74〜69 で放置（削り 130）。
Amalgam intent が T9 に 63。base・H3a とも最終敗だが、Amalgam を倒した base が Queen を 243 まで削った。

| turn | base 攻撃先 | cand 攻撃先 | Amalgam HP base/cand | QueenHP base/cand | Amalgam intent(base/cand) | playerHP最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | POMMEL・SQUASH・HEADBUTT・STRIKE→amalgam | 同左 | 199/199 | 400/400 | 13/13 | 81/81 |
| 2 | BASH→amalgam, STRIKE→amalgam | 同左 | 119/119 | 389/389 | 18/18 | 81/81 |
| 3 * | BYRD_SWOOP→amalgam, HEADBUTT→amalgam | BYRD_SWOOP→queen, HEADBUTT→queen | 84/84 | 389/389 | 36/36 | 77/77 |
| 4 | 攻撃なし | 攻撃なし | 46/84 | 389/363 | 22/22 | 73/73 |
| 5 * | STRIKE×2→amalgam | STRIKE×2→queen | 41/79 | 389/363 | 24/24 | 67/67 |
| 6 | 攻撃なし | 攻撃なし | 5/79 | 389/359 | 48/48 | 52/52 |
| 7 | HEADBUTT→queen, BASH→queen | 同左(AoE dmg 大) | None/74 | 389/359 | 0/27 | 52/48 |
| 8 | BYRD_SWOOP→queen, HEADBUTT→queen | 同左 | None/69 | 343/299 | 0/28 | 36/32 |
| 9 | BASH→queen, STRIKE→queen | 同左 | None/69 | 289/260 | 0/63 | 25/18 |
| 10 * | HEADBUTT→queen | 攻撃なし | None/None | 243/None | 0/None | 25/None |

## 2. Amalgam を倒せたか（12組、cand=H3a）

全ターンの cand 攻撃から Amalgam へ与えた合計と、Amalgam を倒せたか（終盤 board から消えたか）。

| spec | base 勝敗 | cand 勝敗 | base 削a | cand 削a | base 撃破 | cand Amalgam 最終HP |
| --- | --- | --- | --- | --- | --- | --- |
| 09e1ef74cb7c | 敗 | 敗 | 199 | 130 | ○ | 69 |
| 3bb38a1da0b5 | 敗 | 敗 | 199 | 135 | ○ | 64 |
| 4c69c357dcda | 勝 | 勝 | 199 | 199 | ○ | 0 |
| 62f27302ec36 | 敗 | 敗 | 93 | 93 | − | 105 |
| 74062b5e0d2d | 勝 | 敗 | 199 | 125 | ○ | 74 |
| 96c9cc444c23 | 敗 | 敗 | 199 | 103 | ○ | 96 |
| a362ff6f5e4e | 敗 | 敗 | 199 | 124 | ○ | 75 |
| d22ed45bc52f | 敗 | 敗 | 168 | 124 | − | 75 |
| d416e73f2d0b | 敗 | 敗 | 176 | 142 | − | 56 |
| e8b1b9347232 | 敗 | 敗 | 199 | 98 | ○ | 101 |
| eb8756252bb6 | 敗 | 敗 | 199 | 69 | ○ | 130 |
| fef5e8158e35 | 敗 | 敗 | 128 | 85 | − | 114 |

- cand（H3a）が Amalgam を倒せたのは 12 組中 1 組だけ。base は 12 組中 8 組で倒した。
- base の勝ち 2 組（4c69c357dcda と 74062b5e0d2d）は、base が Amalgam を倒してから Queen を削った組。
  うち 74062b5e0d2d で base は勝ち、cand は Amalgam を 74 HP で残して敗けた。cand が勝った唯一の組も
  cand が Amalgam を倒した組（4c69c357dcda、cand 削り 199）だった。
- 削ったのに倒せなかった組で何が起きるか: 残った Amalgam が毎ターン攻撃を続け（cand 側 a intent 16〜63）、
  cand の体力を削った。同じく cand は Queen をゆっくりしか削れていない（74062 で cand の Queen 削りは
  T3-9 合计 105 にとどまり、base は Amalgam を倒した後に 286 削った）。Queen が生きている Amalgam に
  守られている（被ダメージが抑えられる、あるいは Amalgam が Queen を強化している）可能性がある。これは
  候補の仮説で、因果は主張しない（Amalgam 生存と Queen 削りの伸びなさは同じ戦闘で同時に観測されただけ）。

## 3. 追加候補の見直し（dev5_first_extra_candidate.md の更新）

H3a はゲートを通過しない（Δshave = 5/5/2 で `Δshave > 0` を満たさず、firing 11/12 は満たすが、
Δfp −5.0、Δwin −1）。上の方針を踏まえた判断。

- N を小さくする（N=1）は妥当でない。N=1 は「1 ターン目でも Queen へ」切るので、Amalgam をより早く
  放置する。今回の敗因（Amalgam を倒し切る前に手を引く）を強め、総火力/ターンと勝敗はさらに減る方向。
  dev5 の 12 組で cand が Amalgam を倒せたのは N=2 でも 1/12 なので、N=1 にすれば 0 に近づく。
- 妥当なのは Amalgam 撃破の可否で切り替える側（H3c 系）。base が強いのは Amalgam を倒してから Queen に
  移る点。規則も「Amalgam を倒せる見込みがあるか / 残すと同ターン以降の被ダメで死ぬか」で Queen へ切る
  ほうが、実測の勝敗パターンに合う。H3c は現在走行中で、danger（次に受けるダメージ）起点だが、今回の
  データは H3c 系の方向を支持する。
- H3a の形（N 一定）を残すなら、N を上げる（N=3、Amalgam を長く殴る）側のほうが N=1 よりマシ。ただし
  定数ターンではなく撃破可否で切る H3c 系を優先する。
- 次に測る: H3c（閾値 0.5）の実測を待つ（dev5_report.py で (a)〜(d) を出す）。H3c が Amalgam を倒せる
  ターン以降に Queen へ移る挙動で `Δshave > 0` を満たし Δfp/Δwin を落とすなら、その arm を confirm5_swap へ
  進める。閾値 0.3（より素早く Queen へ）は撃破前に手を引く方向なので、H3c 0.5 が Amalgam 撃破前に
  切り替えて失敗した場合に限り、逆に H3c の閾値を上げる（Queen へ切る条件を厳しく＝Amalgam を倒すまで
  待つ）ことを試す。N=1・閾値 0.3 は「Queen へ早く切る」側で、今回の実測と逆方向なので採用候補から落とす。
