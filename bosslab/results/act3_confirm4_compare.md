# BossLab 集計 (EVALUATION.md 局所検証の書式に準拠)

各試行の採算は BossLab.cs が bridge-trace の combat_end から取った勝敗のみ。
fallback・エラーの除外数と、結果行が無い試行（タイムアウト/未起動）を必ず併記し、母数に混ぜない（EVALUATION.md:62）。


## confirm4_base_H1（base `bosslab_act3_confirm4_base` 12本 vs cand `bosslab_act3_confirm4_H1` 12本。win 記録 1→0）

同じ entry（spec と offset）で配对できた組: 12（比較不能 0）

| 指標 | 比較組 | base 平均 | cand(confirm4_base_H1) 平均 | 候補が優る | base が優る | 同値 | 精密p (両側) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Queen削り割合（主信号） | 12 | 0.403 | 0.385 | 7 | 5 | 0 | 0.774 |
| 総火力/ターン（主信号・Queen+AmalgamへのHP削除÷生存ターン） | 12 | 39.149 | 28.795 | 1 | 11 | 0 | – |
| Queen火力/ターン（主信号・QueenへのHP削除÷生存ターン） | 12 | 15.333 | 23.708 | 9 | 3 | 0 | – |
| Amalgamを倒せたか（補助） | 12 | 0.583 | 0.000 | 0 | 7 | 5 | – |
| 死亡ターン（補助・長いほど良い） | 12 | 8.167 | 6.667 | 1 | 6 | 5 | – |
| 失ったHP（補助・少ないほど良い） | 12 | 83.083 | 83.667 | 0 | 1 | 11 | – |

| spec | offset | base 削り | cand(confirm4_base_H1) 削り | 向き |
| --- | --- | --- | --- | --- |
| 1563989f9e55 | 2 | 0% | 29% | + |
| 2f944dc24562 | 2 | 0% | 13% | + |
| 56accb541102 | 2 | 25% | 36% | + |
| 59ed603b4b73 | 2 | 13% | 22% | + |
| 5f6a1726cfea | 2 | 58% | 38% | - |
| 624ae0d1306b | 2 | 88% | 66% | - |
| 75157844a09c | 2 | 100% | 68% | - |
| 8340d5737b02 | 2 | 18% | 21% | + |
| 8aa46daede55 | 2 | 85% | 70% | - |
| c247ea1ceac4 | 2 | 94% | 46% | - |
| c589d7860c35 | 2 | 0% | 40% | + |
| f737cab6f8b6 | 2 | 4% | 10% | + |

- 判定は Queen削り割合の列で見る。Amalgam は Queen の進捗に合算していない（EVALUATION.md の召喚物の扱い）。勝敗の表はこの節の上にある補助。

## 集合横断のプール符号検定（主信号: Queen削り割合）

- 配对 12 組: 候補が優る 7 / base が優る 5 / 同値 0（精密p 両側 0.774）。上の集合ごとの判定をこれ1本で置き換えない（EVALUATION.md: 比較する run 数と反復数は集合単位で揃える。プールは参考値）。

## 再現性

- 単独 panel の集計はこの実行では指定なし（--compare-pair の配对表のみ）。集合間の spec 重複が 0 なら、集合そのものが独立再測定になっている。

## 局所検証の分類 (docs/EVALUATION.md:43)

- 判断が変わるか / 結果が変わるか: 同じ entry（spec・offset）で base と候補を配对し、主信号は Queen 削り割合。入場状態は plan が同じなので両側で同一。エージェントの分岐が実際に別の target を選んだかは trace の decision_source で確認する。
- 状態にカードがある（発動機会）: 攻撃対象となる QUEEN と Amalgam が入場に居ない panel は 0（配对できた組＝発動機会のある戦闘）。
- seed(spec) 数: 配对 12 組、spec 12 件（集合間は重複除き）。1 spec あたり arm ごとに offset ぶん繰り返す。
- 採否は集合ごとの判定で行う（上の集合別表）。プール符号検定は参考値で、集合ごとの判定に 代えない。

生成: `python3 bosslab/tools/analyze_bosslab.py --compare-pair "LABEL=BASE_DIR:CAND_DIR" [--compare-pair ...] --out <md>`
生データ: 各 run dir の lab_results.jsonl（試行ごと 1 行、BossLab.cs が出す）
