# 配対 trace 差分（base: data/bosslab_act3_dev5_base 対 cand: data/bosslab_act3_dev5_H3a）

引用: 殴り先差分は apply_hybrid_rule の単独攻撃 slot 差分（`type=card` で Attack、target あり）。* は base と cand の殴り先 multiset が別れた turn。HP は各 turn 最初の観測 snapshot。攻撃 intent は次の行動の想定ダメージ（repeats 込み、block 控除前）。playerHP 最低は turn 中の最小。
### 09e1ef74cb7c (base won=False / cand won=False)

- 殴り先が別れた turn: [3, 5, 10]

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | POMMEL_STRIKE→amalgam~12, SQUASH→amalgam~24, HEADBUTT→amalgam~11, STRIKE_IRONCLAD→amalgam~8 | POMMEL_STRIKE→amalgam~12, SQUASH→amalgam~24, HEADBUTT→amalgam~11, STRIKE_IRONCLAD→amalgam~8 | 199/199 | 400/400 | 13/13 | 81/81 |
| 2 | BASH→amalgam~13, STRIKE_IRONCLAD→amalgam~11 | BASH→amalgam~13, STRIKE_IRONCLAD→amalgam~11 | 119/119 | 389/389 | 18/18 | 81/81 |
| 3 * | BYRD_SWOOP→amalgam~15.0, HEADBUTT→amalgam~11.25 | BYRD_SWOOP→queen~15.0, HEADBUTT→queen~11.25 | 84/84 | 389/389 | 36/36 | 77/77 |
| 4 | - | - | 46/84 | 389/363 | 22/22 | 73/73 |
| 5 * | STRIKE_IRONCLAD→amalgam~12.0, STRIKE_IRONCLAD→amalgam~12.0 | STRIKE_IRONCLAD→queen~12.0, STRIKE_IRONCLAD→queen~12.0 | 41/79 | 389/363 | 24/24 | 67/67 |
| 6 | - | - | 5/79 | 389/359 | 48/48 | 52/52 |
| 7 | HEADBUTT→queen~31.5, BASH→queen~15.0 | HEADBUTT→queen~34.5, BASH→queen~16.5 | None/74 | 389/359 | 0/27 | 52/48 |
| 8 | BYRD_SWOOP→queen~20.25, HEADBUTT→queen~16.5 | BYRD_SWOOP→queen~21.75, HEADBUTT→queen~18.0 | None/69 | 343/299 | 0/28 | 36/32 |
| 9 | BASH→queen~16.5, STRIKE_IRONCLAD→queen~15.0 | BASH→queen~18.0, STRIKE_IRONCLAD→queen~16.5 | None/69 | 289/260 | 0/63 | 25/18 |
| 10 * | HEADBUTT→queen~18.0 | - | None/None | 243/None | 0/None | 25/None |

- Amalgam 削った合計(推定): base 199 / cand 130。base が Amalgam を倒した: True（最終HP 0）、cand が倒した: False（最終HP 69）、cand は削ったが倒せなかった: True

### 3bb38a1da0b5 (base won=False / cand won=False)

- 殴り先が別れた turn: [3, 4, 5]

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | PERFECTED_STRIKE→amalgam~None, STRIKE_IRONCLAD→amalgam~12, RAMPAGE→amalgam~12, ANGER→amalgam~11, FIEND_FIRE→amalgam~10 | PERFECTED_STRIKE→amalgam~None, STRIKE_IRONCLAD→amalgam~12, RAMPAGE→amalgam~12, ANGER→amalgam~11, FIEND_FIRE→amalgam~10 | 199/199 | 400/400 | 18/18 | 80/80 |
| 2 | STRIKE_IRONCLAD→amalgam~12, BASH→amalgam~11 | STRIKE_IRONCLAD→amalgam~12, BASH→amalgam~11 | 111/111 | 400/400 | 18/18 | 79/79 |
| 3 * | BYRD_SWOOP→amalgam~12.75, STRIKE_IRONCLAD→amalgam~11.25, STRIKE_IRONCLAD→amalgam~9.0 | BYRD_SWOOP→queen~12.75, STRIKE_IRONCLAD→queen~11.25, STRIKE_IRONCLAD→queen~9.0 | 85/85 | 400/400 | 36/36 | 66/66 |
| 4 * | STRIKE_IRONCLAD→amalgam~9.0, IRON_WAVE→amalgam~6.0 | STRIKE_IRONCLAD→queen~9.0, IRON_WAVE→queen~6.0 | 28/76 | 400/368 | 22/22 | 30/30 |
| 5 * | PERFECTED_STRIKE→amalgam~None, ANGER→queen~8.25, ANGER→queen~6.75 | POMMEL_STRIKE→queen~9.0, ANGER→queen~8.25, STRIKE_IRONCLAD→queen~9.0, ANGER→queen~6.75, STRIKE_IRONCLAD→queen~11.25, STRIKE_IRONCLAD→queen~9.0, STRIKE_IRONCLAD→queen~9.0 | 10/73 | 400/368 | 24/24 | 13/13 |
| 6 | STRIKE_IRONCLAD→queen~11.25, STRIKE_IRONCLAD→queen~9.0 | BYRD_SWOOP→queen~12.75, ANGER→queen~8.25 | None/64 | 400/327 | 0/48 | 13/13 |

- Amalgam 削った合計(推定): base 199 / cand 135。base が Amalgam を倒した: True（最終HP 0）、cand が倒した: False（最終HP 64）、cand は削ったが倒せなかった: True

### 4c69c357dcda (base won=True / cand won=True)

- 殴り先が別れた turn: [5, 7, 8, 9, 10, 11, 12]

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BASH→amalgam~8, STRIKE_IRONCLAD→amalgam~6, ANGER→amalgam~6, IRON_WAVE→amalgam~5 | BASH→amalgam~8, STRIKE_IRONCLAD→amalgam~6, ANGER→amalgam~6, IRON_WAVE→amalgam~5 | 199/199 | 400/400 | 13/13 | 76/76 |
| 2 | - | - | 147/147 | 384/384 | 18/18 | 76/76 |
| 3 | - | - | 82/82 | 322/322 | 36/36 | 75/75 |
| 4 | - | - | 68/68 | 318/318 | 22/22 | 74/74 |
| 5 * | ANGER→amalgam~4.5 | ANGER→queen~4.5 | 56/56 | 292/292 | 24/24 | 73/73 |
| 6 | - | - | 46/50 | 283/277 | 48/48 | 66/66 |
| 7 * | IRON_WAVE→amalgam~6.0 | - | 11/15 | 279/273 | 27/27 | 65/65 |
| 8 * | - | IRON_WAVE→queen~6.0 | None/9 | 159/230 | 0/28 | 64/58 |
| 9 * | BASH→queen~8.25, ANGER→queen~6.75, ANGER→queen~6.75 | ANGER→queen~6.75 | None/None | 159/221 | 0/0 | 63/49 |
| 10 * | - | BASH→queen~8.25, ANGER→queen~6.75 | None/None | 61/215 | 0/0 | 46/48 |
| 11 * | - | ANGER→queen~6.75 | None/None | 22/120 | 0/0 | 45/47 |
| 12 * | - | ANGER→queen~6.75 | None/None | None/62 | None/0 | None/46 |

- Amalgam 削った合計(推定): base 199 / cand 199。base が Amalgam を倒した: True（最終HP 0）、cand が倒した: True（最終HP 0）、cand は削ったが倒せなかった: False

### 62f27302ec36 (base won=False / cand won=False)

- 殴り先が別れた turn: []

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BASH→amalgam~11 | BASH→amalgam~11 | 198/198 | 399/399 | 18/18 | 44/44 |
| 2 | FIEND_FIRE→amalgam~9 | FIEND_FIRE→amalgam~9 | 160/160 | 372/372 | 18/18 | 44/44 |
| 3 | - | - | 105/105 | 357/357 | 36/36 | 26/26 |

- Amalgam 削った合計(推定): base 93 / cand 93。base が Amalgam を倒した: False（最終HP 105）、cand が倒した: False（最終HP 105）、cand は削ったが倒せなかった: True

### 74062b5e0d2d (base won=True / cand won=False)

- 殴り先が別れた turn: [3, 4, 5, 6, 7, 8, 9, 11, 12]

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BASH→amalgam~18, IRON_WAVE→amalgam~7 | BASH→amalgam~18, IRON_WAVE→amalgam~7 | 199/199 | 400/400 | 18/18 | 103/103 |
| 2 | POMMEL_STRIKE→amalgam~10, PERFECTED_STRIKE→amalgam~None, STRIKE_IRONCLAD→amalgam~6 | POMMEL_STRIKE→amalgam~10, PERFECTED_STRIKE→amalgam~None, STRIKE_IRONCLAD→amalgam~6 | 171/171 | 400/400 | 18/18 | 102/102 |
| 3 * | POMMEL_STRIKE→amalgam~9.75, STRIKE_IRONCLAD→amalgam~6.75 | POMMEL_STRIKE→queen~9.75, STRIKE_IRONCLAD→queen~6.75 | 98/98 | 400/400 | 36/36 | 94/94 |
| 4 * | POMMEL_STRIKE→amalgam~9.75, POMMEL_STRIKE→amalgam~9.75, IRON_WAVE→amalgam~6.0 | POMMEL_STRIKE→queen~9.75, POMMEL_STRIKE→queen~9.75, IRON_WAVE→queen~6.0 | 74/98 | 400/376 | 22/22 | 67/67 |
| 5 * | UPPERCUT→amalgam~12.0, STRIKE_IRONCLAD→amalgam~6.75 | UPPERCUT→queen~12.0, STRIKE_IRONCLAD→queen~6.75 | 50/98 | 400/372 | 24/24 | 59/59 |
| 6 * | PERFECTED_STRIKE→amalgam~None, BASH→amalgam~9.75 | BASH→queen~9.75, POMMEL_STRIKE→queen~9.75, ANGER→queen~6.75 | 28/98 | 400/370 | 48/48 | 50/44 |
| 7 * | PERFECTED_STRIKE→queen~None, IRON_WAVE→queen~6.0 | UPPERCUT→queen~12.0 | None/98 | 400/353 | 0/27 | 50/26 |
| 8 * | UPPERCUT→queen~12.0 | IRON_WAVE→queen~6.0, ANGER→queen~6.75 | None/98 | 367/335 | 0/28 | 44/13 |
| 9 * | BASH→queen~9.75 | - | None/74 | 316/295 | 0/63 | 33/2 |
| 10 | - | - | None/None | 219/None | 0/None | 33/None |
| 11 * | IRON_WAVE→queen~7.5, BASH→queen~9.75, IRON_WAVE→queen~6.0 | - | None/None | 182/None | 0/None | 30/None |
| 12 * | UPPERCUT→queen~12.0, ANGER→queen~6.75 | - | None/None | 114/None | 0/None | 25/None |

- Amalgam 削った合計(推定): base 199 / cand 125。base が Amalgam を倒した: True（最終HP 0）、cand が倒した: False（最終HP 74）、cand は削ったが倒せなかった: True

### 96c9cc444c23 (base won=False / cand won=False)

- 殴り先が別れた turn: [3, 4, 5]

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | PERFECTED_STRIKE→amalgam~None | PERFECTED_STRIKE→amalgam~None | 199/199 | 400/400 | 18/18 | 64/64 |
| 2 | POMMEL_STRIKE→amalgam~26, POMMEL_STRIKE→amalgam~13, ANGER→amalgam~9 | POMMEL_STRIKE→amalgam~26, POMMEL_STRIKE→amalgam~13, ANGER→amalgam~9 | 166/166 | 380/380 | 18/18 | 62/62 |
| 3 * | BLUDGEON→amalgam~26.25, POMMEL_STRIKE→amalgam~9.75, BASH→amalgam~9.75, STRIKE_IRONCLAD→amalgam~6.75 | BLUDGEON→queen~26.25, POMMEL_STRIKE→queen~9.75, BASH→queen~9.75, STRIKE_IRONCLAD→queen~6.75 | 96/96 | 380/380 | 36/36 | 44/44 |
| 4 * | UPPERCUT→amalgam~12.0 | UPPERCUT→queen~12.0, BASH→queen~9.75 | 42/96 | 380/326 | 22/22 | 8/8 |
| 5 * | POMMEL_STRIKE→queen~9.75 | - | None/None | 380/None | 0/None | 8/None |

- Amalgam 削った合計(推定): base 199 / cand 103。base が Amalgam を倒した: True（最終HP 0）、cand が倒した: False（最終HP 96）、cand は削ったが倒せなかった: True

### a362ff6f5e4e (base won=False / cand won=False)

- 殴り先が別れた turn: [3, 5, 7, 8, 10, 11]

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | POMMEL_STRIKE→amalgam~12, SQUASH→amalgam~12, HEADBUTT→amalgam~11, STRIKE_IRONCLAD→amalgam~16 | POMMEL_STRIKE→amalgam~12, SQUASH→amalgam~12, HEADBUTT→amalgam~11, STRIKE_IRONCLAD→amalgam~16 | 199/199 | 400/400 | 13/13 | 81/81 |
| 2 | BASH→amalgam~11, STRIKE_IRONCLAD→amalgam~9 | BASH→amalgam~11, STRIKE_IRONCLAD→amalgam~9 | 119/119 | 389/389 | 18/18 | 81/81 |
| 3 * | BYRD_SWOOP→amalgam~13.5, HEADBUTT→amalgam~9.75 | BYRD_SWOOP→queen~13.5, HEADBUTT→queen~9.75 | 90/90 | 389/389 | 36/36 | 77/77 |
| 4 | - | - | 56/90 | 389/367 | 22/22 | 73/73 |
| 5 * | STRIKE_IRONCLAD→amalgam~10.5, STRIKE_IRONCLAD→amalgam~10.5 | STRIKE_IRONCLAD→queen~10.5, STRIKE_IRONCLAD→queen~10.5 | 51/85 | 389/367 | 24/24 | 67/67 |
| 6 | - | - | 21/85 | 389/367 | 48/48 | 52/52 |
| 7 * | HEADBUTT→amalgam~14.25 | HEADBUTT→queen~15.75, BASH→queen~15.0 | 21/80 | 389/367 | 27/27 | 46/49 |
| 8 * | BYRD_SWOOP→queen~18.75, HEADBUTT→queen~30.0 | BYRD_SWOOP→queen~40.5, HEADBUTT→queen~16.5, STRIKE_IRONCLAD→queen~14.25 | None/75 | 389/352 | 0/28 | 46/33 |
| 9 | BASH→queen~15.0, STRIKE_IRONCLAD→queen~13.5 | HEADBUTT→queen~17.25, BASH→queen~16.5 | None/75 | 316/267 | 0/63 | 25/15 |
| 10 * | HEADBUTT→queen~16.5 | - | None/None | 281/None | 0/None | 3/None |
| 11 * | STRIKE_IRONCLAD→queen~15.0 | - | None/None | 257/None | 0/None | 3/None |

- Amalgam 削った合計(推定): base 199 / cand 124。base が Amalgam を倒した: True（最終HP 0）、cand が倒した: False（最終HP 75）、cand は削ったが倒せなかった: True

### d22ed45bc52f (base won=False / cand won=False)

- 殴り先が別れた turn: [3]

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BASH→amalgam~10, STRIKE_IRONCLAD→amalgam~6 | BASH→amalgam~10, STRIKE_IRONCLAD→amalgam~6 | 199/199 | 400/400 | 18/18 | 53/53 |
| 2 | BLUDGEON→amalgam~42, ANGER→amalgam~8, ANGER→amalgam~6 | BLUDGEON→amalgam~42, ANGER→amalgam~8, ANGER→amalgam~6 | 162/162 | 400/400 | 18/18 | 35/35 |
| 3 * | POMMEL_STRIKE→amalgam~15.0, HEADBUTT→amalgam~6.75, STRIKE_IRONCLAD→amalgam~4.5, ANGER→amalgam~4.5 | POMMEL_STRIKE→queen~15.0, HEADBUTT→queen~6.75, STRIKE_IRONCLAD→queen~4.5, ANGER→queen~4.5 | 75/75 | 400/400 | 36/36 | 17/17 |

- Amalgam 削った合計(推定): base 168 / cand 124。base が Amalgam を倒した: False（最終HP 31）、cand が倒した: False（最終HP 75）、cand は削ったが倒せなかった: True

### d416e73f2d0b (base won=False / cand won=False)

- 殴り先が別れた turn: [3, 4, 5]

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | POMMEL_STRIKE→amalgam~13, STRIKE_IRONCLAD→amalgam~10 | POMMEL_STRIKE→amalgam~13, STRIKE_IRONCLAD→amalgam~10 | 198/198 | 399/399 | 18/18 | 78/78 |
| 2 | PERFECTED_STRIKE→amalgam~None, STRIKE_IRONCLAD→amalgam~11 | PERFECTED_STRIKE→amalgam~None, STRIKE_IRONCLAD→amalgam~11 | 162/162 | 397/397 | 18/18 | 59/59 |
| 3 * | POMMEL_STRIKE→amalgam~18.0, TWIN_STRIKE→amalgam~8.25 | POMMEL_STRIKE→queen~18.0, TWIN_STRIKE→queen~8.25 | 93/93 | 380/380 | 36/36 | 41/41 |
| 4 * | HEADBUTT→queen~12.0 | HEADBUTT→amalgam~12.0 | 55/89 | 380/346 | 22/22 | 17/17 |
| 5 * | HEADBUTT→amalgam~12.75 | HEADBUTT→queen~12.75 | 40/62 | 336/307 | 24/24 | 17/17 |
| 6 | - | - | 22/56 | 317/276 | 48/48 | 3/3 |

- Amalgam 削った合計(推定): base 176 / cand 142。base が Amalgam を倒した: False（最終HP 22）、cand が倒した: False（最終HP 56）、cand は削ったが倒せなかった: True

### e8b1b9347232 (base won=False / cand won=False)

- 殴り先が別れた turn: [3, 6, 7]

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BASH→amalgam~10, MAUL→amalgam~6, STRIKE_IRONCLAD→amalgam~6, STRIKE_IRONCLAD→amalgam~6 | BASH→amalgam~10, MAUL→amalgam~6, STRIKE_IRONCLAD→amalgam~6, STRIKE_IRONCLAD→amalgam~6 | 199/199 | 400/400 | 13/13 | 56/56 |
| 2 | UNRELENTING→amalgam~23, HEADBUTT→amalgam~12 | UNRELENTING→amalgam~23, HEADBUTT→amalgam~12 | 153/153 | 400/400 | 18/18 | 56/56 |
| 3 * | BLUDGEON→amalgam~26.25, UNRELENTING→amalgam~17.25, PERFECTED_STRIKE→amalgam~None, MAUL→amalgam~8.25 | BLUDGEON→queen~26.25, UNRELENTING→queen~17.25, PERFECTED_STRIKE→queen~None, MAUL→queen~8.25 | 101/101 | 400/400 | 36/36 | 38/38 |
| 4 | MAUL→queen~9.75, STRIKE_IRONCLAD→queen~6.75 | MAUL→queen~10.5, STRIKE_IRONCLAD→queen~7.5 | None/101 | 400/329 | 0/16 | 38/11 |
| 5 | BLUDGEON→queen~27.0 | BLUDGEON→queen~27.0 | None/101 | 376/322 | 0/18 | 20/2 |
| 6 * | MAUL→queen~12.0, MAUL→queen~13.5 | - | None/None | 349/None | 0/None | 7/None |
| 7 * | BLUDGEON→queen~27.0 | - | None/None | 299/None | 0/None | 7/None |

- Amalgam 削った合計(推定): base 199 / cand 98。base が Amalgam を倒した: True（最終HP 0）、cand が倒した: False（最終HP 101）、cand は削ったが倒せなかった: True

### eb8756252bb6 (base won=False / cand won=False)

- 殴り先が別れた turn: [3, 4, 5, 7, 8, 9]

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | POMMEL_STRIKE→amalgam~13, IRON_WAVE→amalgam~7 | POMMEL_STRIKE→amalgam~13, IRON_WAVE→amalgam~7 | 199/199 | 400/400 | 13/13 | 67/67 |
| 2 | TWIN_STRIKE→amalgam~10, POMMEL_STRIKE→amalgam~15, STRIKE_IRONCLAD→amalgam~14 | TWIN_STRIKE→amalgam~10, POMMEL_STRIKE→amalgam~15, STRIKE_IRONCLAD→amalgam~14 | 179/179 | 400/400 | 18/18 | 67/67 |
| 3 * | PERFECTED_STRIKE→amalgam~None | PERFECTED_STRIKE→queen~None | 130/130 | 400/400 | 36/36 | 49/49 |
| 4 * | STRIKE_IRONCLAD→amalgam~12.75, POMMEL_STRIKE→amalgam~11.25, PERFECTED_STRIKE→amalgam~None, STRIKE_IRONCLAD→amalgam~10.5 | STRIKE_IRONCLAD→queen~12.75, POMMEL_STRIKE→queen~11.25, PERFECTED_STRIKE→queen~None, STRIKE_IRONCLAD→queen~10.5 | 102/130 | 400/372 | 22/22 | 19/19 |
| 5 * | STRIKE_IRONCLAD→amalgam~12.75, STRIKE_IRONCLAD→queen~10.5 | STRIKE_IRONCLAD→queen~12.75, STRIKE_IRONCLAD→queen~10.5 | 10/130 | 400/331 | 24/24 | 4/4 |
| 6 | TWIN_STRIKE→queen~7.5, STRIKE_IRONCLAD→queen~10.5 | TWIN_STRIKE→queen~7.5, STRIKE_IRONCLAD→queen~10.5 | None/130 | 400/329 | 0/48 | 4/34 |
| 7 * | STRIKE_IRONCLAD→queen~12.75, POMMEL_STRIKE→queen~11.25, IRON_WAVE→queen~6.75 | - | None/None | 363/None | 0/None | 6/None |
| 8 * | PERFECTED_STRIKE→queen~None, STRIKE_IRONCLAD→queen~10.5 | - | None/None | 318/None | 0/None | 5/None |
| 9 * | TWIN_STRIKE→queen~7.5, STRIKE_IRONCLAD→queen~10.5 | - | None/None | 261/None | 0/None | 5/None |

- Amalgam 削った合計(推定): base 199 / cand 69。base が Amalgam を倒した: True（最終HP 0）、cand が倒した: False（最終HP 130）、cand は削ったが倒せなかった: True

### fef5e8158e35 (base won=False / cand won=False)

- 殴り先が別れた turn: [3, 4]

| turn | base 攻撃先(card→slot, dmg) | cand 攻撃先(card→slot, dmg) | Amalgam HP base/cand | QueenHP base/cand | Amalgam の次攻撃 intent(base/cand) | playerHP 最低 base/cand |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BASH→amalgam~10, STRIKE_IRONCLAD→amalgam~8, ANGER→amalgam~8 | BASH→amalgam~10, STRIKE_IRONCLAD→amalgam~8, ANGER→amalgam~8 | 199/199 | 400/400 | 18/18 | 46/46 |
| 2 | POMMEL_STRIKE→amalgam~13, TWIN_STRIKE→amalgam~8 | POMMEL_STRIKE→amalgam~13, TWIN_STRIKE→amalgam~8 | 165/165 | 400/400 | 18/18 | 39/39 |
| 3 * | POMMEL_STRIKE→amalgam~10.5, STRIKE_IRONCLAD→amalgam~9.75 | POMMEL_STRIKE→queen~10.5, STRIKE_IRONCLAD→queen~9.75 | 114/114 | 392/392 | 36/36 | 21/21 |
| 4 * | TWIN_STRIKE→amalgam~7.5, STRIKE_IRONCLAD→amalgam~10.5 | TWIN_STRIKE→queen~7.5, STRIKE_IRONCLAD→queen~10.5 | 95/114 | 392/373 | 22/22 | 8/8 |

- Amalgam 削った合計(推定): base 128 / cand 85。base が Amalgam を倒した: False（最終HP 71）、cand が倒した: False（最終HP 114）、cand は削ったが倒せなかった: True


## Amalgam 撃破の内訳（cand 全体、item2）

| spec | base 勝敗 | cand 勝敗 | base が削った Amalgam HP | cand が削った Amalgam HP | base 撃破 | cand の Amalgam 最終 HP | cand 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 09e1ef74cb7c | 敗 | 敗 | 199 | 130 | ○ | 69 | 削ったが倒せず |
| 3bb38a1da0b5 | 敗 | 敗 | 199 | 135 | ○ | 64 | 削ったが倒せず |
| 4c69c357dcda | 勝 | 勝 | 199 | 199 | ○ | 0 | 倒せた |
| 62f27302ec36 | 敗 | 敗 | 93 | 93 | − | 105 | 削ったが倒せず |
| 74062b5e0d2d | 勝 | 敗 | 199 | 125 | ○ | 74 | 削ったが倒せず |
| 96c9cc444c23 | 敗 | 敗 | 199 | 103 | ○ | 96 | 削ったが倒せず |
| a362ff6f5e4e | 敗 | 敗 | 199 | 124 | ○ | 75 | 削ったが倒せず |
| d22ed45bc52f | 敗 | 敗 | 168 | 124 | − | 75 | 削ったが倒せず |
| d416e73f2d0b | 敗 | 敗 | 176 | 142 | − | 56 | 削ったが倒せず |
| e8b1b9347232 | 敗 | 敗 | 199 | 98 | ○ | 101 | 削ったが倒せず |
| eb8756252bb6 | 敗 | 敗 | 199 | 69 | ○ | 130 | 削ったが倒せず |
| fef5e8158e35 | 敗 | 敗 | 128 | 85 | − | 114 | 削ったが倒せず |

- 配対 12 組: cand が Amalgam を倒せた 1 組、削ったが倒せなかった 11 組、触れずつまり 0 組。base の Amalgam 撃破 8 組、base 勝ち 2 対 cand 勝ち 1。
