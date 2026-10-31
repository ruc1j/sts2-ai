# Act 2 ボス戦: Shrug It Off の加点外し（候補）の再測定、事前登録

登録日時: 2026-10-31（開発用を流す前）。

## 問い

報酬選択でShrug It Offへの強ブロック不足・ボス軸の加点を外す変更（4c03ab4、v22の候補。比較v22で保留となり、fa516ccでmainから戻された）は、Act 2ボス（THE_INSATIABLE）戦に効くか。前回の局所検証（`docs/BOSSLAB_20261028.md`、176試行）は、ポーションの効果が抜けた状態の結果だった。ポーションUIの再初期化を直した`bosslab`ブランチで、新しい入場状態から測り直す。

## 候補のラボ上の定義

加点を外すと、Shrug It Offがデッキに入りにくくなる。その効果を、同じ入場状態からデッキの未強化Shrug It Offを1枚外す（アーム `noshrug`）ことで近似する。前回は「1枚足す」で測ったが、候補の向きに合わせて、今回は「1枚外す」とする。base はデッキを記録どおりに使う。エージェントは両アームとも `official_agent.py`（無変更）。外すのは、デッキに未強化Shrugが1枚以上ある入場状態に限る（全アームでデッキの差は、その1枚だけ）。

## 条件

- 入場状態: v23＋v24のパネル（新形式、relic_counters記録あり）のAct 2ボス戦spec 176件（`bosslab/specs_act2_boss_v23v24.jsonl`、すべてTHE_INSATIABLE。91件がv23、85件がv24、seed 963F7C2E44 は除外）から、次の条件を満たす29件を使う: 未解決フラグなし、レリックの危険は STONE_CRACKER と FORGOTTEN_SOUL だけ（またはなし）、未強化Shrugが1枚以上。実走の勝敗は選定条件に使わない。
- 29件を `sha256(spec_id + "|act2-noshrug-v1")` の順に並べ、先頭12件を開発用、次の12件を確認用とする（重ならない。残り5件は使わない）。
- 書き戻しは全アームで無効（前回のAct 2実験と同じ扱い）。ポーションは修正後のDLLで効果が適用される。
- 開発用: `bosslab_act2_plan_ns_dev.json`（12 spec × base/noshrug = 24 trial）。確認用: `bosslab_act2_plan_ns_conf.json`（24 trial）。各アーム1 trial（rng_offset 0）。アームの順序は、planの規則どおりspecごとに回す。

## 発火の前提（G''）

加点外しが戦いの判断を変えたかを、デッキから1枚外したことでShrug It Offの使用回数が変わった組で見る。組ごとに、baseアームのShrug It Off使用回数が、noshrugアームの使用回数を超えた組を「発火」とする。開発用で発火が4組未満（12組中）なら、候補を測定の対象から外す（測定不能＝保留）。確認用も4組以上（12組中）を要する。

## 判定規則

前回の事前登録（4693f2e）の規則1〜6を、noshrugをbaseと比べて適用する。主信号は、ボスを削った割合の差（Δshave、候補優の組数−base優の組数）と総火力/ターンの差（Δfp）。条件は、Δshave>0、Δfp≥0、Δwin≥0、確認用でp≤0.05、開発用と確認用で方向が一致、組が欠けていない（比較不能0、開発用・確認用とも12組）、発火の前提G''。判定は `apply_hybrid_rule.judge_candidate` を機械的に1回だけ呼び、結果を見て規則を直さない。

## 訂正（開発用を1回流して全trialが失敗したあと。結果は1件も出ていない）

抽出ツールが `encounter_hint` に敵id（`MONSTER.THE_INSATIABLE`）を入れていたため、開発用の24 trialがすべて約4秒で `ModelNotFoundException: Model id=ENCOUNTER.` で失敗した（`ENCOUNTER.THE_INSATIABLE_BOSS` が正しい）。spec 176件の `encounter_hint` を直し（抽出ツールの定数も直し）、同じspec選定で2つのplanを作り直した。選定（spec、アーム、規則）は変わらない。変わったのはplanのハッシュだけである。

## 固定するファイルのハッシュ（sha256、訂正後）

```
c0b495bc50baafe627522a0007aecbd41650c8f1fb5cf6501c8d126260dd2441  bosslab/plans/
eb0405ac3068b5d01d1922ea1db13540bfccae7bfd0723632b4c986b720ca001  bosslab/plans/
61e780f81fb8a7168e2a013031b601e5f0c4169bb8b5fce902fd6b70bfeaf65c  official_agent
4701614578b7bb7ae60b4224b466f67e7f3eba5db671c191210df7aee134a33b  combat.py
```
