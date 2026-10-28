# dev2 base 観測から H1/H2 の殴り先を手番ごとに再現 (T17 item2 続)

各手番の最初の観測で Amalgam 実効HP / Amalgam の予想被ダメを算出し、その手番の攻撃判断が
Amalgam(A) か Queen(Q) か (それ以外=防御/ターン終了/ポーション/強化=『-』) を各ポリシーで再現。
H1閾値=50、H2=その手番のHP+ブロック、H3a=最初のQUEENFIRST_H3_OPEN_TURNS(2)ターンだけA、
H3b=実効HP<=150でA（閾値上げの診断）、H3c=Amalgam予想被ダメが(HP+blk)の5割以上でA（危険前に削り）。
全ポリシー同じ観測に流し、enemy_data無しの決定的heuristic再現（Queen短絡とfocused_minionsが殴り先を決める）。

## trial 0000  (trial_0000)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 199 | 18 | 88 | A | Q | Q | Q | A | Q | Q |
| 2 | 158 | 18 | 70 | A | Q | Q | Q | A | Q | Q |
| 3 | 149 | 36 | 61 | none | none | none | none | none | none | none |
| 4 | 122 | 22 | 22 | none | none | none | none | none | none | none |
| 5 | 105 | 24 | 22 | A | Q | Q | Q | Q | A | A |
| 6 | 39 | 48 | 8 | A | Q | A | A | Q | A | A |

## trial 0001  (trial_0001)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 196 | 18 | 109 | A | Q | Q | Q | A | Q | Q |
| 2 | 174 | 18 | 91 | A | Q | Q | Q | A | Q | Q |
| 3 | 144 | 36 | 81 | A | Q | Q | Q | Q | A | Q |
| 4 | 96 | 22 | 45 | none | none | none | none | none | none | none |
| 5 | 65 | 24 | 23 | Q | Q | Q | Q | Q | Q | Q |
| 6 | 50 | 48 | 33 | A | A | A | A | A | A | A |
| 7 | 0 | 0 | 33 | Q | Q | Q | Q | Q | Q | Q |
| 8 | 0 | 0 | 5 | Q | Q | Q | Q | Q | Q | Q |

## trial 0002  (trial_0002)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 199 | 13 | 60 | A | Q | Q | Q | A | Q | Q |
| 2 | 164 | 18 | 59 | A | Q | Q | Q | A | A | Q |
| 3 | 132 | 36 | 39 | none | none | none | none | none | none | none |
| 4 | 104 | 22 | 14 | A | Q | Q | A | Q | A | A |

## trial 0003  (trial_0003)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 199 | 18 | 49 | A | Q | Q | Q | A | Q | Q |
| 2 | 127 | 18 | 35 | A | A | A | A | A | A | A |
| 3 | 96 | 27 | 31 | A | Q | Q | Q | Q | A | A |
| 4 | 56 | 16 | 3 | A | Q | A | A | Q | A | A |

## trial 0004  (trial_0004)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 199 | 18 | 68 | A | Q | Q | Q | A | Q | Q |
| 2 | 164 | 13 | 61 | A | Q | Q | Q | A | A | Q |
| 3 | 106 | 36 | 59 | A | Q | Q | Q | Q | A | A |
| 4 | 69 | 22 | 29 | A | Q | Q | Q | Q | A | A |
| 5 | 48 | 24 | 20 | A | A | A | A | A | A | A |
| 6 | 0 | 0 | 20 | Q | none | none | none | none | none | none |
| 7 | 0 | 0 | 20 | none | none | none | none | none | none | none |
| 8 | 0 | 0 | 3 | none | none | none | none | none | none | none |
| 9 | 0 | 0 | 2 | Q | Q | Q | Q | Q | Q | Q |
| 10 | 0 | 0 | 2 | none | Q | Q | Q | Q | Q | Q |

## trial 0005  (trial_0005)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 199 | 13 | 88 | A | Q | Q | Q | A | Q | Q |
| 2 | 127 | 18 | 74 | A | Q | Q | Q | A | A | Q |
| 3 | 92 | 36 | 73 | none | none | none | none | none | none | none |
| 4 | 54 | 22 | 69 | A | A | A | A | A | A | A |
| 5 | 49 | 24 | 66 | A | Q | A | Q | Q | A | Q |
| 6 | 0 | 0 | 63 | Q | Q | Q | Q | Q | Q | Q |
| 7 | 0 | 0 | 63 | Q | Q | Q | Q | Q | Q | Q |
| 8 | 0 | 0 | 47 | Q | Q | Q | Q | Q | Q | Q |
| 9 | 0 | 0 | 47 | Q | Q | Q | Q | Q | Q | Q |
| 10 | 0 | 0 | 12 | Q | Q | Q | Q | Q | Q | Q |
| 11 | 0 | 0 | 5 | none | none | none | none | none | none | none |
| 12 | 0 | 0 | 5 | Q | Q | Q | Q | Q | Q | Q |

## trial 0006  (trial_0006)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 196 | 18 | 79 | A | A | A | A | A | A | A |
| 2 | 169 | 18 | 79 | A | Q | Q | Q | A | Q | Q |
| 3 | 139 | 36 | 64 | A | Q | Q | Q | Q | A | A |
| 4 | 92 | 16 | 43 | A | Q | Q | Q | Q | A | Q |
| 5 | 59 | 24 | 33 | A | Q | A | Q | Q | A | A |
| 6 | 28 | 48 | 15 | A | A | A | A | A | A | A |
| 7 | 0 | 0 | 15 | none | Q | Q | Q | Q | Q | Q |

## trial 0007  (trial_0007)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 196 | 18 | 75 | A | A | A | A | A | A | A |
| 2 | 175 | 18 | 75 | A | A | A | A | A | A | A |
| 3 | 133 | 36 | 60 | A | Q | Q | Q | Q | A | A |
| 4 | 96 | 16 | 39 | A | Q | Q | Q | Q | A | Q |
| 5 | 66 | 24 | 35 | A | Q | A | Q | Q | A | A |
| 6 | 37 | 48 | 17 | A | A | A | A | A | A | A |
| 7 | 0 | 0 | 17 | Q | Q | Q | Q | Q | Q | Q |

## trial 0008  (trial_0008)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 196 | 18 | 76 | A | A | A | A | A | A | A |
| 2 | 162 | 13 | 70 | A | A | A | A | A | A | A |
| 3 | 101 | 36 | 69 | A | Q | Q | Q | Q | A | A |
| 4 | 61 | 22 | 55 | A | Q | Q | Q | Q | A | Q |
| 5 | 41 | 24 | 49 | A | Q | A | Q | Q | A | Q |
| 6 | 18 | 48 | 33 | A | A | A | A | A | A | A |
| 7 | 0 | 0 | 33 | Q | Q | Q | Q | Q | Q | Q |
| 8 | 0 | 0 | 22 | none | Q | Q | Q | Q | Q | Q |
| 9 | 0 | 0 | 12 | Q | Q | Q | Q | Q | Q | Q |
| 10 | 0 | 0 | 12 | Q | Q | Q | Q | Q | Q | Q |

## trial 0009  (trial_0009)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 199 | 13 | 91 | A | Q | Q | Q | A | Q | Q |
| 2 | 127 | 18 | 77 | A | Q | Q | Q | A | A | Q |
| 3 | 98 | 36 | 76 | A | Q | Q | Q | Q | A | Q |
| 4 | 64 | 22 | 72 | A | A | A | A | A | A | A |
| 5 | 59 | 24 | 69 | A | Q | A | Q | Q | A | Q |
| 6 | 13 | 48 | 53 | none | none | none | none | none | none | none |
| 7 | 8 | 27 | 38 | A | A | A | A | A | A | A |
| 8 | 0 | 0 | 38 | Q | Q | Q | Q | Q | Q | Q |
| 9 | 0 | 0 | 14 | Q | Q | Q | Q | Q | Q | Q |
| 10 | 0 | 0 | 4 | Q | Q | Q | Q | Q | Q | Q |
| 11 | 0 | 0 | 4 | none | Q | Q | Q | Q | Q | Q |

## trial 0010  (trial_0010)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 199 | 13 | 91 | A | Q | Q | Q | A | Q | Q |
| 2 | 127 | 18 | 77 | A | Q | Q | Q | A | A | Q |
| 3 | 98 | 36 | 76 | none | none | none | none | none | none | none |
| 4 | 64 | 22 | 70 | A | A | A | A | A | A | A |
| 5 | 59 | 24 | 67 | A | Q | A | Q | Q | A | Q |
| 6 | 13 | 48 | 49 | none | none | none | none | none | none | none |
| 7 | 8 | 27 | 49 | A | A | A | A | A | A | A |
| 8 | 0 | 0 | 49 | none | Q | Q | Q | Q | Q | Q |
| 9 | 0 | 0 | 24 | none | none | none | none | none | none | none |
| 10 | 0 | 0 | 9 | Q | Q | Q | Q | Q | Q | Q |
| 11 | 0 | 0 | 9 | none | Q | Q | Q | Q | Q | Q |

## trial 0011  (trial_0011)

| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 196 | 18 | 74 | Q | Q | Q | Q | Q | Q | Q |
| 2 | 127 | 18 | 73 | Q | Q | Q | Q | Q | Q | Q |
| 3 | 87 | 27 | 60 | A | Q | A | Q | Q | A | Q |
| 4 | 38 | 22 | 33 | A | Q | A | Q | Q | A | A |
| 5 | 0 | 0 | 23 | Q | Q | Q | Q | Q | Q | Q |
| 6 | 0 | 0 | 23 | Q | Q | Q | Q | Q | Q | Q |
| 7 | 0 | 0 | 2 | Q | Q | Q | Q | Q | Q | Q |

## 集計

- 手番数 97
- Amalgam(A)/Queen(Q) 選択: base A=55 Q=24 攻撃以外=18  queenfirst A=16 Q=68 攻撃以外=13  H1 A=26 Q=58 攻撃以外=13  H2 A=19 Q=65 攻撃以外=13  H3a A=32 Q=52 攻撃以外=13  H3b A=44 Q=40 攻撃以外=13  H3c A=29 Q=55 攻撃以外=13
- queenfirst: base と異なる手番 46  queenfirst と異なる手番 0
- H1: base と異なる手番 36  queenfirst と異なる手番 10
- H2: base と異なる手番 43  queenfirst と異なる手番 3
- H3a: base と異なる手番 30  queenfirst と異なる手番 16
- H3b: base と異なる手番 18  queenfirst と異なる手番 28
- H3c: base と異なる手番 33  queenfirst と異なる手番 13
