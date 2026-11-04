# PILOT-8 報告1: MYTEの被弾、踏破2本の分岐、部品別の集計

読むだけ。C1のコードとゲームには触れていない。

## 1. MYTE戦の「意図19に対し29被弾」は未モデルではない

`astra_clear5_c1_598FC4B069` の seq247→248（Act 1、MYTE×2）。直前の意図は SUCK 4 + BITE 15 = 19。
実際のHP減は 29。

内訳: 19 + **手札に残った TOXIC 2枚 × 5ダメージ = 10**。ターン終了時の状態異常ダメージで、
`combat.py` の `HAND_INJECTED_STATUS` に TOXIC:5 が入っており、モデル済み。同時に発生した
プレイヤーの Strength +5（Rupture）も、この自傷で説明できる。

前回「説明不能」と書いたのは、私の走査が敵のintentだけを合計し、終了時の状態異常ダメージを
足していなかったため。正しさの修正候補にはならない。

## 2. 踏破2本の最初の分岐

| seed | 最初の分岐 | C1 | 対照 |
| --- | --- | --- | --- |
| 895C061BBB | Act 1 のショップ（seq88） | INFLAME を先に購入→DEFEND を削除 | DEFEND を先に削除→POMMEL_STRIKE を購入 |
| 4FDF910744 | Act 2 のショップ（seq100） | RUPTURE を購入 | Skip |

- どちらも**部品2（報酬・ショップのengine優先）**が最初の分岐。C1だけが INFLAME/RUPTURE を買っている。
- **部品3（Demon Form先出し）は両runとも発動0回**（DEMON_FORMを一度も持っていない）。
- **部品1（進捗の評価）は最初の分岐に関与していない**。分岐はショップの購入判断で、戦闘の決定ではない。
  その後の戦闘の打ち方が部品1で変わった可能性は残るが、trace の `decision_source` だけでは分離できない。

その後のQueen戦: 895C061BBB は C1 が9ターンで勝ち、対照は9ターンで敗北（INFLAMEの使用12回 vs 8回）。
4FDF910744 は C1 が12ターンで勝ち、対照は8ターンで敗北（C1はRUPTUREを5回、対照はINFLAMEを6回）。

補足: ショップの決定は trace に `legal_actions` が残らないため、`choose_shop` の完全な再生はできない。
分岐内容そのもの（engine札の購入）は trace に残っており、C1固有の規則はengine優先だけなので、
帰属は trace で足りる。

## 3. clear5_pair.py に部品別の発動数

追加した項目: 報酬でのengine採用（行数）、ショップでのengine購入、`demon_form_early_direct` 発動、
DEMON_FORM使用ターン合計。部品1だけは trace から数えられない旨を明記した。

現在のスナップショット（完了114本、同一seed対照114本）:

| 部品 | C1 | 対照 |
| --- | ---: | ---: |
| 報酬でengine採用 | 153 | 72 |
| ショップでengine購入 | 59 | 31 |
| demon_form_early_direct 発動 | 32 | 0 |
| DEMON_FORM 使用ターン合計 | 57 | 7 |

これらは件数で、勝敗の差ではない（途中経過で判定しない）。
