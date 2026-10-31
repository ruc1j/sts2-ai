# 第2段階（A）事前登録: 入場デッキにBlock札を足す対照実験

登録日時: 2026-10-31（開発用を流す前。結果を見る前に固定する）。

## 問い

Queen戦の入場デッキにBlockを持つ札を足すと、Queen削り割合、総火力/ターン、勝ち、生存ターンはどう変わるか。因果の問いに近づけるため、同じ入場状態（spec）のデッキだけを変えて、対応ありで比べる。

## 条件

- エージェント: `official_agent.py`（base、無変更。sha256は下記）。全アームで同じ。
- 入場状態: 新形式（relic_counters記録あり）のv23＋v24のQueen戦spec 59件（`bosslab/specs_act3_queen_v23v24.jsonl`）から、次の条件を満たす18件を使う: 未解決フラグなし、レリックの危険は STONE_CRACKER（入室後に付与で対応済み）と FORGOTTEN_SOUL（敵HPが数ポイントずれる程度で、全アーム共通のため対応ありで打ち消される）だけ。BELLOWS、CROSSBOW、BLESSED_ANTLERなどは除外。
- 書き戻しは全アームで無効（足した札が山札の先頭に置かれ、1ターン目に必ず引かれる副作用を避けるため）。Cの採用結果は、この実験に影響しない。
- アーム: base（足さない）、add2（SHRUG_IT_OFF 1枚＋FLAME_BARRIER 1枚）、add4（SHRUG_IT_OFF 2枚＋FLAME_BARRIER 2枚）。足す札はすべて未強化。選んだ理由は、パネルのデッキ59件中53件と24件が持つ（実際のデッキに近い）Block札で、combat.pyが扱えるため。
- アームの順序: planの規則どおり、specごとにアームの順を回して割り当てる（先に流すアームが固定されないようにするため）。「0枚、2枚、4枚の順に流す」ではなく、この回転にする。
- 開発用/確認用: 18件をハッシュ順（`sha256(spec_id + "|act3-blockadd-v1")`）に並べ、先頭6件を開発用、次の12件を確認用とする（重ならない）。開発用が12件に満たないのは、条件を満たすspecが18件しかないため（確認用12件を優先して確保した。開発用は発火率の測定のためだけに使い、候補の調整は行わないので、6件で足りる）。
  - 開発用6件: `bosslab_act3_blk_dev.speclist`、plan: `bosslab_act3_plan_blk_dev.json`（18 trial）。
  - 確認用12件: `bosslab_act3_blk_conf.speclist`、plan: `bosslab_act3_plan_blk_conf.json`（36 trial）。
- 乱数: 各アーム1 trial（rng_offset 0）。

## 発火の前提（G'）

足した札が実際に使われた組を数える。組ごとに、addアームでSHRUG_IT_OFFとFLAME_BARRIERを使った回数の合計がbaseアームの合計を超えた組を「発火」とする。開発用で発火が4組未満（6組中）のアームは測定の対象から外す（測定不能＝保留）。確認用も同じく4組以上（12組中）を要する。

## 判定規則

前回の事前登録（4693f2e）の規則1〜6を、addアーム（add2、add4）ごとにbaseと比べて適用する。主信号はQueen削り割合の差（Δshave）と総火力/ターンの差（Δfp）。条件は、Δshave>0、Δfp≥0、Δwin≥0、確認用でp≤0.05、開発用と確認用で方向が一致、組が欠けていないこと、発火の前提G'を満たすこと。すべて満たせば採用、一部が満たされなければ保留、Δshave≤0かつ確認用で逆向きなら不採用とする。この判定は `apply_hybrid_rule.judge_candidate` を機械的に1回だけ呼んで出し、結果を見て規則を直さない。

第2段階の判定への読み替え: 採用＝「効く」、不採用＝「効かない」、保留＝「判定できない」。第3段階は、add2かadd4のどちらかが「効く」の場合だけ行う。

## 固定するファイルのハッシュ（sha256）

```
0c1a9bf7ee34878601c45399920632d8970f84e6eccfca0cb3eece11e486f3cf  bosslab/plans/bosslab_ac
f941b3022def71deb422fab312bae4cc987c96e702a165302cce3f383df8e64f  bosslab/plans/bosslab_ac
61e780f81fb8a7168e2a013031b601e5f0c4169bb8b5fce902fd6b70bfeaf65c  official_agent.py
```
