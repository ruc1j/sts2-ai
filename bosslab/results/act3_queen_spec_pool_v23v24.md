# Act 3 QUEEN spec プール（v23 + v24 新形式パネル）

抽出: `.dsh/extract_act3_specs.py` を v23/v24 の agent trace（seed 963F7C2E44 を除く、tmp ディレクトリへ symlink）に実行。出力 `bosslab/specs_act3_queen_v23v24.jsonl`。カード種別・Block 持ちは全 trace の hand 観測から導出（不明 id は種別 `?`・Block なし扱い）。

## 件数

- spec 総数: 59（QUEEN 戦 59 本、重複除去で減らず）
- hazard 無し: 36
- hazard が FORGOTTEN_SOUL / BLESSED_ANTLER のみ（無し含む）: 44
- hazard 定義: FORGOTTEN_SOUL, BLESSED_ANTLER, BELLOWS, CROSSBOW, および relic_entry_effects.py の defer/flag 表の relic（RELIC.BIG_HAT, RELIC.BLESSED_ANTLER, RELIC.CROSSBOW, RELIC.FUNERARY_MASK, RELIC.JEWELED_MASK, RELIC.ORANGE_DOUGH, RELIC.POWER_CELL, RELIC.RADIANT_PEARL, RELIC.STONE_CRACKER, RELIC.TOOLBOX）

- hazard 無しの Block カード枚数分布: 3枚: 1, 4枚: 1, 5枚: 2, 6枚: 3, 7枚: 6, 8枚: 4, 9枚: 6, 10枚: 4, 11枚: 7, 12枚: 1, 14枚: 1
- 二重発火 2 種のみ許容の Block カード枚数分布: 3枚: 1, 4枚: 2, 5枚: 2, 6枚: 4, 7枚: 8, 8枚: 6, 9枚: 7, 10枚: 4, 11枚: 8, 12枚: 1, 14枚: 1
- unresolved 無し（usable）: 21

## spec 一覧

| spec_id | seed | 版 | HP/max | デッキ | Atk | Skill | Pow | 種別不明 | Block持ち | relic数 | relic_counters | hazard | unresolved | 実走勝 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 80c13bd206c8 | 0D459C3862 | v24 | 27/58 | 32 | 11 | 15 | 6 | 0 | 9 | 12 | 無 | - | relic_run_state:RELIC.EMBER_TEA,RELIC.HAPPY_FLOWER | False |
| 4bb6cf77fdd9 | 1AEE656BEB | v24 | 77/81 | 27 | 9 | 15 | 3 | 0 | 10 | 12 | 無 | - | - | False |
| c589d7860c35 | 3169EC2E1C | v23 | 53/94 | 18 | 9 | 5 | 3 | 0 | 5 | 11 | 無 | - | - | False |
| 25a514fcb3bd | 37E263D80E | v24 | 46/90 | 29 | 15 | 10 | 4 | 0 | 11 | 11 | 無 | - | relic_run_state:RELIC.EMBER_TEA | False |
| 32a042506ca3 | 3BDD1BD98D | v24 | 72/85 | 28 | 13 | 13 | 1 | 0 | 9 | 11 | 有 | - | relic_run_state:RELIC.EMBER_TEA | False |
| e75781521da8 | 41ACBF0DEA | v23 | 75/75 | 26 | 16 | 7 | 2 | 0 | 8 | 10 | 無 | - | - | False |
| 8292c6c64002 | 42A34FA0F2 | v23 | 85/111 | 30 | 15 | 12 | 3 | 0 | 8 | 12 | 無 | - | relic_run_state:RELIC.HAPPY_FLOWER,RELIC.VENERABLE_TEA_SET | False |
| dcde3977cd52 | 469AAE3BED | v23 | 87/87 | 24 | 10 | 10 | 3 | 0 | 6 | 12 | 無 | - | card_value_state | False |
| 29834a67b1dd | 46E15BFA6F | v23 | 87/87 | 29 | 15 | 12 | 1 | 0 | 11 | 14 | 無 | - | relic_run_state:RELIC.EMBER_TEA | False |
| a4f376cd945f | 47E1B2B908 | v24 | 87/87 | 29 | 13 | 11 | 4 | 0 | 9 | 14 | 無 | - | - | False |
| d19d73f7f6c4 | 4952AC25C0 | v23 | 85/100 | 28 | 16 | 10 | 1 | 0 | 7 | 11 | 無 | - | entry_mid_turn,relic_overapplies:VIGOR_POWER+8 | False |
| b841fe9f3f2c | 49B8CC820F | v24 | 78/78 | 28 | 13 | 14 | 1 | 0 | 11 | 11 | 無 | - | relic_run_state:RELIC.HAPPY_FLOWER | False |
| 90f3d97472a1 | 4FDF910744 | v24 | 91/91 | 26 | 13 | 10 | 2 | 0 | 8 | 11 | 無 | - | entry_mid_turn | False |
| 4c69c357dcda | 50B404C802 | v23 | 76/80 | 31 | 14 | 14 | 3 | 0 | 10 | 14 | 有 | - | - | False |
| 42dd87a750c8 | 6A023D3C89 | v24 | 106/106 | 30 | 13 | 14 | 3 | 0 | 11 | 12 | 無 | - | card_value_state | False |
| 9b3dcb765729 | 731E2B691C | v24 | 74/74 | 29 | 12 | 14 | 2 | 0 | 12 | 11 | 有 | - | relic_run_state:RELIC.EMBER_TEA,RELIC.VENERABLE_TEA_SET | False |
| 0be389384303 | 76B6C57B33 | v24 | 72/72 | 30 | 12 | 16 | 2 | 0 | 11 | 13 | 無 | - | - | False |
| 859203ff5b28 | 793CDC4E24 | v24 | 68/68 | 19 | 8 | 9 | 2 | 0 | 8 | 14 | 有 | - | card_value_state,relic_run_state:RELIC.FUR_COAT | False |
| 1d1d991ac4d6 | 81E19F92F4 | v23 | 107/109 | 27 | 16 | 10 | 1 | 0 | 7 | 12 | 有 | - | relic_run_state:RELIC.STONE_CALENDAR | False |
| fd39a3b868b5 | 83EF113AF3 | v24 | 69/80 | 22 | 10 | 11 | 1 | 0 | 7 | 10 | 無 | - | - | False |
| 821b5aa92c3f | 85A990F154 | v23 | 69/80 | 32 | 14 | 10 | 4 | 0 | 9 | 13 | 無 | - | relic_run_state:RELIC.HAPPY_FLOWER,RELIC.VENERABLE_TEA_SET | False |
| 29bc53ff6cf2 | 895C061BBB | v24 | 76/85 | 30 | 16 | 11 | 3 | 0 | 11 | 11 | 無 | - | entry_mid_turn | False |
| 5b3328eda1dc | 925AC3E0CC | v24 | 121/121 | 32 | 14 | 16 | 2 | 0 | 11 | 8 | 無 | - | - | False |
| f63bb56cde11 | A34F57C907 | v24 | 63/80 | 23 | 11 | 8 | 3 | 0 | 3 | 11 | 無 | - | relic_run_state:RELIC.EMBER_TEA,RELIC.VENERABLE_TEA_SET | False |
| fb398a1b1816 | A37AF69710 | v23 | 83/87 | 29 | 13 | 13 | 3 | 0 | 7 | 12 | 無 | - | card_value_state | False |
| 20f1190a6585 | B5341AD0C2 | v23 | 70/100 | 31 | 14 | 14 | 3 | 0 | 9 | 9 | 無 | - | relic_run_state:RELIC.FUR_COAT | False |
| 2ef593df593d | BC3F444E7D | v23 | 88/88 | 32 | 10 | 19 | 2 | 0 | 14 | 13 | 有 | - | card_value_state | False |
| fef5e8158e35 | BF5B24014F | v23 | 46/90 | 22 | 11 | 9 | 1 | 0 | 7 | 11 | 無 | - | - | False |
| 614271466f56 | C2111DD7C7 | v24 | 73/84 | 20 | 13 | 6 | 1 | 0 | 4 | 9 | 無 | - | - | False |
| 8e78301e34bf | C232A16A62 | v23 | 90/90 | 23 | 13 | 8 | 1 | 0 | 7 | 12 | 有 | - | card_value_state | False |
| 2acc173f1ae2 | C8E2B78A0E | v23 | 83/83 | 30 | 13 | 14 | 3 | 0 | 10 | 12 | 無 | - | card_value_state,relic_run_state:RELIC.GIRYA | False |
| 259e8012883d | CE0C776D9C | v24 | 121/121 | 23 | 15 | 5 | 2 | 0 | 5 | 12 | 無 | - | card_value_state,relic_run_state:RELIC.HAPPY_FLOWER | False |
| d0bc17ef4ab6 | D71DA535AD | v23 | 41/84 | 26 | 11 | 10 | 4 | 0 | 9 | 13 | 無 | - | card_value_state,relic_run_state:RELIC.HAPPY_FLOWER | False |
| b37c3498e7f8 | EA10792935 | v24 | 70/76 | 24 | 12 | 11 | 1 | 0 | 10 | 13 | 無 | - | - | False |
| 73ed4b8fa3b9 | F287271E7D | v23 | 60/100 | 24 | 12 | 10 | 2 | 0 | 6 | 13 | 無 | - | entry_mid_turn | False |
| 3bb38a1da0b5 | FB52AEBE99 | v23 | 80/80 | 29 | 14 | 9 | 6 | 0 | 6 | 13 | 無 | - | - | False |
| 61bd59ad4d50 | 038CDAC87B | v23 | 80/80 | 27 | 14 | 10 | 3 | 0 | 7 | 16 | 有 | FORGOTTEN_SOUL | card_value_state,relic_run_state:RELIC.VENERABLE_TEA_SET | False |
| eb8756252bb6 | 161F480E76 | v23 | 67/68 | 24 | 12 | 10 | 0 | 0 | 8 | 11 | 有 | STONE_CRACKER | - | False |
| b8ddbf388f0d | 198DFA073E | v24 | 105/105 | 28 | 9 | 16 | 1 | 0 | 9 | 10 | 有 | STONE_CRACKER | relic_run_state:RELIC.EMBER_TEA | False |
| 479936ac3307 | 23A7CEECF7 | v23 | 42/84 | 19 | 9 | 8 | 2 | 0 | 4 | 15 | 有 | STONE_CRACKER | card_value_state,relic_run_state:RELIC.VENERABLE_TEA_SET | False |
| 14f7eb980539 | 2C08EC12EA | v24 | 85/90 | 24 | 12 | 9 | 2 | 0 | 6 | 8 | 無 | BELLOWS | - | False |
| d22ed45bc52f | 465F76FB32 | v23 | 53/73 | 29 | 18 | 9 | 2 | 0 | 7 | 9 | 有 | FORGOTTEN_SOUL | - | False |
| 2893f6bccf3c | 495FF454B7 | v23 | 99/113 | 28 | 12 | 11 | 5 | 0 | 9 | 10 | 無 | STONE_CRACKER | relic_run_state:RELIC.EMBER_TEA | True |
| dd4fd0cb9ce0 | 4B07AC4E2A | v23 | 89/94 | 26 | 12 | 10 | 3 | 0 | 10 | 14 | 無 | STONE_CRACKER | relic_run_state:RELIC.VENERABLE_TEA_SET | False |
| 75495c03f631 | 562858EF63 | v23 | 33/74 | 21 | 12 | 9 | 0 | 0 | 6 | 11 | 無 | FORGOTTEN_SOUL STONE_CRACKER | - | False |
| 15b387a90fc5 | 5B5EA36CCE | v23 | 75/90 | 30 | 12 | 16 | 2 | 0 | 11 | 11 | 有 | FORGOTTEN_SOUL | relic_run_state:RELIC.HAPPY_FLOWER | False |
| 504058dad5ab | 5E58E8A550 | v23 | 68/68 | 29 | 16 | 10 | 2 | 0 | 8 | 14 | 無 | CROSSBOW | card_value_state | False |
| 16d838af30eb | 65A711FB05 | v24 | 76/84 | 22 | 12 | 9 | 1 | 0 | 9 | 9 | 無 | FORGOTTEN_SOUL | - | False |
| 60058beedf0a | 6765D9C84A | v24 | 70/81 | 26 | 13 | 11 | 2 | 0 | 10 | 12 | 無 | FORGOTTEN_SOUL STONE_CRACKER | - | False |
| 30c98f643174 | 67A743CCD8 | v23 | 97/97 | 26 | 13 | 9 | 3 | 0 | 9 | 12 | 無 | STONE_CRACKER | - | False |
| a86bbc9e5a86 | 7042706FD5 | v23 | 80/80 | 23 | 14 | 7 | 2 | 0 | 8 | 14 | 無 | FORGOTTEN_SOUL | relic_run_state:RELIC.EMBER_TEA | False |
| 0256297739fc | 7CA7B893D4 | v23 | 92/100 | 30 | 13 | 14 | 3 | 0 | 10 | 14 | 無 | BELLOWS | - | False |
| 9f1c92a6e409 | 992E1B8DE0 | v23 | 89/89 | 22 | 11 | 10 | 1 | 0 | 6 | 12 | 有 | FORGOTTEN_SOUL | relic_run_state:RELIC.HAPPY_FLOWER,entry_mid_turn | False |
| 0e94ce9d9456 | C394628E60 | v23 | 85/87 | 30 | 14 | 13 | 2 | 0 | 10 | 17 | 有 | STONE_CRACKER | relic_run_state:RELIC.EMBER_TEA,entry_mid_turn | False |
| 3e393663fab0 | C527A4A732 | v24 | 71/71 | 22 | 14 | 7 | 1 | 0 | 4 | 12 | 有 | FORGOTTEN_SOUL | card_value_state | False |
| 8b63743eb0b7 | C5989A3E01 | v24 | 90/94 | 29 | 9 | 15 | 5 | 0 | 13 | 14 | 無 | BELLOWS | card_value_state | False |
| 25e1d94f4337 | E8B0886845 | v24 | 78/78 | 24 | 10 | 11 | 3 | 0 | 9 | 11 | 無 | STONE_CRACKER | entry_mid_turn | False |
| a7137fc0ab43 | F43E1FF27B | v24 | 42/100 | 32 | 18 | 12 | 2 | 0 | 11 | 11 | 有 | CROSSBOW | card_value_state,relic_run_state:RELIC.STONE_CALENDAR | False |
| 3f682f8c583f | F786F0D94E | v23 | 81/81 | 29 | 11 | 12 | 2 | 0 | 8 | 9 | 無 | BLESSED_ANTLER | - | False |

注: relic_counters 列は spec の player.relic_counters が空でないか。全 spec が新形式 trace 由来。各 spec の relics 全文は jsonl の player.relics を参照。
