# 仮説検証: Demon Form を序盤に出すエージェント（demonfirst）、事前登録

登録日時: 2026-11-01（実行前）。探索的な仮説検証で、採否の判定ではない。

## 問い

Strength札追加の補足（`docs/ACT3_FULLRUN_PANEL_20261029.md`）で、足したDEMON_FORMが12組中2組でしか使われなかった。DEMON_FORMを序盤に出すよう変えたエージェントなら、同じデッキ（INFLAME 2枚＋DEMON_FORM 1枚を足したQueen入場デッキ）でQueen戦の削りと総火力/ターンが上がるか。

## 条件

- plan: `bosslab/plans/bosslab_act3_plan_df18.json`。str実験の18 spec（開発用6＋確認用12）の str3 アーム（足す札: INFLAME 2枚＋DEMON_FORM 1枚）だけを取り出し、アーム名を base に付け替えたもの（18 trial）。書き戻しは無効、rng_offset 0。
- エージェント: base = `official_agent.py`（無変更）、候補 = `bosslab/agents/official_agent_demonfirst.py`。差分は、ターン1〜2に、ボス級の敵（最大HP150以上）がいて、DEMON_FORMが使え、致死攻撃がなく、被ダメージで死なないときに、DEMON_FORMを最初に出す1規則だけ（`diff`で確認）。
- 同じplanを2つのエージェントで別々のOutDirに流し、`analyze_bosslab.py --compare-pair` で spec・offset ごとに対応づける。
- 読み方: 主信号はQueen削り割合と総火力/ターンの対応あり差。18組・各1乱数の探索的な結果で、採否は決めない。「効く可能性がある（次に事前登録した追試へ進む）」「手がかりなし」のどちらかを記録する。向きが一致しない、またはDEMON_FORMの使用が増えない場合は、手がかりなしとする。

## 固定するファイルのハッシュ

plan のハッシュは実行前にこのファイルへ追記する。

```
eb3c9826871e56c3c106a66b94ce0ed1f1c0b721577d2a75da634128d0246517  bosslab/plans/bosslab_act3_plan_df18.json
```
