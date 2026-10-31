# Block札追加（A）の凍結記録（確認用を流す前）

開発用の18 trial（6 spec × base/add2/add4）は完走した（失敗0）。結果は `act3_blk_dev_report.md`。確認用を見る前に、事前登録（`act3_blk_prereg.md`）の規則に従って、次のとおり凍結する。

## 開発用の結果（調整は行わない）

| アーム | G' 発火（閾値4/6組） | Δshave（候補優/base優/同値） | Δfp | Δwin |
| --- | --- | --- | --- | --- |
| add2 | 3 / 6 組 | -3（1 / 4 / 1、p=0.375） | -8.2（42.4→34.2） | 0 |
| add4 | 4 / 6 組 | -5（0 / 5 / 1、p=0.062） | -12.5（42.4→29.9） | 0 |

- add2は発火が閾値（4組）に届かないため、事前登録の規則に従って測定の対象から外す（測定不能＝保留）。確認用は流さない。
- add4は発火が4/6組で、確認用に進める。
- 開発用では、足したアームはQueen削り割合と総火力/ターンの両方が、baseより低い向きだった（add4は削り優0/base優5）。Block札を足すと、攻撃に回る手札と時間が減る方向と整合するが、これは開発用6組の観察で、因果は主張しない。この向きを見ても、アームの定義（札の種類と枚数）は変更しない（調整は0組合せ）。

## 確認用

- plan: `bosslab_act3_plan_blk_conf_add4.json`（登録済みの確認用plan `bosslab_act3_plan_blk_conf.json` から、base と add4 の trial だけを取り出して、trial_index を振り直したもの。12 spec × 2 アーム＝24 trial）。add2の12 trialを流さないのは、上の除外による。
- エージェント: `official_agent.py`（無変更）。

## 固定するファイルのハッシュ（sha256）

```
f6481b56f73a2ee6a8a7fd9a8f82a70c289ab143e3c2d2782f146abc5c0b5443  bosslab/plans/bosslab_ac
61e780f81fb8a7168e2a013031b601e5f0c4169bb8b5fce902fd6b70bfeaf65c  official_agent.py
```
