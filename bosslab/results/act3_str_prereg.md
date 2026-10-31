# 案Bの前提: 入場デッキにStrengthを伸ばす札を足す対照実験、事前登録

登録日時: 2026-10-31（開発用を流す前。結果を見る前に固定する）。

## 問い

Queen戦の入場デッキに、勝ったrunに共通して入っていたStrengthを伸ばす札を足すと、Queen削り割合などはどう変わるか。Block札を足した実験A（add4は「効かない」）の対になる実験で、報酬方針で「Strength系を採りやすくする」案B（`docs/ACT3_FULLRUN_PANEL_20261029.md` の必要標本数の見積もり参照）を検討する価値があるかを、ラボで先に見る。

## 条件

Aの事前登録（`act3_blk_prereg.md`）と同じ。違いはアームだけ。

- エージェント: `official_agent.py`（無変更）。入場状態: Aと同じ18 specのうち、開発用6件（`bosslab_act3_blk_dev.speclist`）と確認用12件（`bosslab_act3_blk_conf.speclist`）。書き戻しは全アームで無効。各アーム1 trial（rng_offset 0）。アームの順序はplanの規則どおり。
- アーム: base（足さない）、str3（CARD.INFLAME 2枚＋CARD.DEMON_FORM 1枚、すべて未強化）。選んだ理由は、勝ったrunの共通点がStrengthを伸ばす札で（INFLAMEはその一つ）、combat.pyが扱えるため。3枚はAのadd4（4枚）より1枚少なく、デッキ枠の置き換えは行わない（足すだけ）。
- 発火の前提: 組ごとに、str3アームで追加札（INFLAMEとDEMON_FORM）を使った回数の合計がbaseアームを超えた組を「発火」とする。開発用で発火が4組未満（6組中）、確認用で4組未満（12組中）なら測定対象から外す（保留）。
- 判定規則: Aと同じ（4693f2e の規則1〜6、条件6は完全性による読み）。`apply_hybrid_rule.judge_candidate` を機械的に1回だけ呼ぶ（`str_report.py`）。採用＝「効く」、不採用＝「効かない」、保留＝「判定できない」。

## 解釈の約束

- 「効く」でも、案Bの実施は自動では決まらない。報酬方針で同等のデッキ変化が起きるかは別の問いで、必要標本数（+10ptで約602 run）の問題も残る。
- 「効かない」なら、案Bは、Block系にもStrength系にも手がかりがないことになり、報酬選択の方向では根拠が尽きる。

## 固定するファイルのハッシュ（sha256）

```
a9fa91d1c4f7b321022874b0bb0b9c49f612c54de9531f1e1eb74e2c6e7eda9a  bosslab/plans/bosslab_act3_plan_str_dev.json
f353900db84c1d91dbc971ae8b15ffb4edb7d7ecbd3c5c6c3b2a80a3ed77aca5  bosslab/plans/bosslab_act3_plan_str_conf.json
61e780f81fb8a7168e2a013031b601e5f0c4169bb8b5fce902fd6b70bfeaf65c  official_agent.py
```
