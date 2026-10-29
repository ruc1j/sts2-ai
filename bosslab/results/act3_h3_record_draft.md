# 第8章 草稿: H3 候補（序盤 Queen 集中の手仕舞い）の実験記録（2026-10-29）

`docs/ACT3_BOSSLAB_20261028.md` に続ける章。第1〜6章は dev2 世代（旧 `official_agent_queenfirst`）までの記録で、
本草案は H3a / H3c に替えた後の分を、`docs/EVALUATION.md` の記録書式で書く。結果欄は空。dev5 の実走は
leader が進めており（base 完了、H3a / H3c 走行中）、数値は結果が出てから埋める。実機・ビルドは使っていない。

## 8.1 仮説・変更の種類・対象場面

- 仮説: Act 3 QUEEN 戦で、base エージェント（Amalgam を先に削る集中）より Queen を先に狙う候補規則のほうが、
  主指標の Queen 削り割合を上げる。上げるなら、同じ削り割合で base を上回る arm を確認用へ進める。
- 変更の種類: 二つを分ける。①エージェント全体の強さ（H3a / H3c の戦略候補）。②ゲーム再現の正しさ（PenNib 等の
  入場効果の二重発火を直したこと。下方 8.4）。戦略と忠実性の修正を同じ判定に混ぜない。
- 対象場面: 固定入場の QUEEN 戦（`ENCOUNTER.QUEEN_BOSS`、Act 3、total_floor 48 の boss 戦闘）。ラボは記録した
  入場状態から 1 戦闘だけを再構成する。

## 8.2 旧版／候補版、ゲーム／Mod／userdata／探索条件

- 旧版（base）: `official_agent.py`（main）。PenNib 他 counter 復元を含む Mod を使う。
- 候補版: `bosslab/agents/official_agent_H3a.py`（H3a、序盤 N=2 ターン Queen 集中）、`official_agent_H3c.py`
  （H3c、次に受けるダメージが最大 HP の danger 閾値超で Queen 集中。既定 0.5、追加で 0.3）。両者とも
  `focus_to_amalgam` フラグで分岐し、trace に `decision_source` の `_amalgam` / `_queen` を残す。
- ゲーム: Slay the Spire 2 v0.107.1。Mod: `official_mod/Sts2Ai.dll`（HP 補正 927f26f、counter 復元 d216956）。
- userdata: 固定入場 spec 集合 `.dsh/act3_boss_specs.jsonl`（191 spec。new-format usable 35）。探索条件は
  固定入場 1 戦闘で、分岐の再現性確認のみ。run 全体の経路探索は行わない。
- 反復: 各 arm 1 試行（trials_per_arm 1、offset_start 0）。同じ spec・offset で base と候補を配対する。

## 8.3 開発用 seed／確認用 seed、選定方法、反復数

固定 panel の選定方法（`bosslab/tools/make_bosslab_plan.py`。order は hash 順、band は入場 HP の桶 `<60` /
`60-79` / `>=80`、原因レリックを持つ spec を除外、既に使った 26 spec を除外）。panel は base -arm の単一 arm で、
候補規則は別 run dir に出す。

| panel | order seed | spec 数 | band(<60/60-79/>=80) | 記録済みの勝ち | 状態 |
| --- | --- | --- | --- | --- | --- |
| fid5 | fid5-ctrl | 12 | 忠実性検査用 | — | 完了（下 8.4） |
| dev5_swap | dev5-split | 12 | 4/4/4 | 3 | 開発用。base/H3a/H3c を走行中 |
| confirm5_swap | confirm5-split | 12 | 3/4/5 | 0 | 確認用。未開始 |

- 選定: fid5 は忠実性の照合専用。dev5_swap は候補の開発測定、confirm5_swap は dev5 で選ばれた 1 arm だけを進める
  確認用。開発 panel を何度も見て調整した分は開発用に扱い、確認用は候補の結果を知らずに選んだ。multiple
  comparison（同時に多く比べることで見かけの改善が出る）は dev5 側に閉じ込め、confirm5_swap には dev5 で
  ゲートを通過した arm だけを出す。
- dev5_swap の差し替え（原因レリック除外）: 忠実性で入場効果が二重発火した 2 spec を、原因レリックなしの loss
  へ hash 順で差し替えた（`8aa46daede55`→`3bb38a1da0b5`、`e030d2f11e5f`→`96c9cc444c23`）。理由は下 8.4。
- confirm5_swap の差し替え: CROSSBOW 持ち `bbbfd4fc2927`（入場忠実性で開示 hand がずれる系統）を、
  confirm5-split hash 順の先頭 `d48032980ad0`（原因レリックなし・loss）に差し替えた。fid5・dev5_swap と非重複、
  勝ち 0 を維持。ただし原因レリックなしの loss は残りの pool で band >=80 にしか無く、bbbfd の band(<60) とは
  band が変わる（band 3/4/5 へ移動）。同じ band・同じ outcome の差し替え先が存在しない旨を leader が了承済み。

## 8.4 前提: PenNib 反映と忠実性（fid5）の結果

- PenNib 反映: 入場時のレリック counter（PenNib / Nunchaku の AttacksPlayed、TuningFork の SkillsPlayed）を
  Mod が bridge から受け取り、エージェントの第一判定の直前に書き戻す（d216956、`BossLab.RestoreRelicCounters`）。
  counter が 0 から始まると 10 回目の攻撃倍増等が戦闘中盤でずれるため。
- fid5（忠実性 panel）の結果: 12 中 10 が一致、不一致 2。詳細は `bosslab/results/act3_fid5_mismatch_causes.md`。
  - `8aa46daede55` = `RELIC.FORGOTTEN_SOUL`（`AfterCardExhausted` で exhausted ごとにランダムな敵へ 1 ダメージ、
    ForgottenSoul.cs:20-30）。lab の hook が base と別順で走って敵 HP がずれる。
  - `e030d2f11e5f` = `RELIC.BLESSED_ANTLER`（1 ターン目の手札 draw に Deterministic で Dazed を足す、
    BlessedAntler.cs:45-55）。lab が再度 hook を走らせて Dazed を二重に配る。
  - どちらも counter 由来ではない。原因は「入場効果の二重発火」。fix の方針と、それを解く hook（enemy HP と
    pile の書き戻し）は `bosslab/results/act3_h3_codewiki_draft.md` と `official_mod/BossLab.cs`（default off）。

## 8.5 事前登録規則と G 条（全ターン発火）

判定規則は `bosslab/results/act3_h3_decision_rule_proposal.md` で事前登録し、実装は `bosslab/tools/apply_hybrid_rule.py`。

- 候補 C の条件充足: `Δshave_C > 0` かつ `Δfp_C ≥ 0` かつ `Δwin_C ≥ 0`（4693f2e の規則）。
- 前提 G（判定の前に検査）: 候補 C について、同じ spec・offset の base trace と配対し、全ターンの単独攻撃で
  base と別の殴り先（敵 slot）を選んだ組数 `firing_C` を数える。dev・確認用の両集合で `firing_C ≥ 4` を満たさない
  候補は充足候補から外す。満たす候補が無い panel は測定不能 = 保留（不採用ではない）。
- 実装: `pair_attack_target_diff`（件数）と `pair_attack_target_turns`（発火ターン）。`dev5_report.py` が発火件数と
  発火ターンを 1 コマンドで出す。閾値 4 を維持。danger 起点の H3c は第一手で発火せず中盤で発火うるので、第一手
  だけ基準だと実際に発火しうる候補を発火 0 に落とす。完全一致（fired 0）は機構の作動・不作動のどちらでも同じ
  比較になり、Δshave で採否を出さない。

## 8.6 H1 / H2 が発火しなかった経緯

- 旧 panel（dev2 / confirm4）で H1 の「Amalgam を 50 以下で削り切る」規則は self-lockout で一度も作動しなかった。
  H1 は Queen 既定で動いた。base 自体が Amalgam 集中なので、H1 は arm 規則が作動しなくても base と 12/12 で
  殴り先が違った。`firing_C`（base と殴り先が違ったか）は 12/12 だが、arm の意図した削り規則が作動した数は 0。
- ここから「候補の特別規則が実際に作動していること」を測定の前提に格上げした。`firing_C` は arm の作動そのもの
  ではなく base との差だけを見る指標なので、規則の作動由来か既定反転由来かを解読する補助として trace flag
  `decision_source` の `_amalgam` 决策数を使い、採否の必須条件は `firing_C ≥ 4` のみにした。flag 読みは results の
  解釈メモに留める。H3a / H3c は danger 起点にして、第一手で発火しない H3c の発火 0 化けを避けた。

## 8.7 判定に使う指標（標準から変えた点と測定前の理由）

- 主指標: 到達点同値の最終戦の Queen 削り割合（`削った割合 = 1 - 残 HP 合計 / その形態の開始時最大 HP 合計`、
  `docs/EVALUATION.md` §到達点同値の最終戦の進捗）。lab は Queen 単体戦なので形態移行前の削りで測る。trace の
  敵 HP 減り（telescoped、`analyze_bosslab.hp_removed_from_trace`）で算出し、回復前ダメージや block を削った量は
  累積しない。
- 補助指標: 総火力 / ターン、Queen 火力 / ターン、勝ち（`Δwin`）、生存ターン。EVALUATION の「踏破率向上とは呼ばない」
  範囲で、これらは主指標が同値のときに補助として見る。
- 標準からの変更: lab が 1 戦闘のみの固定入場なので、Act 3 踏破率の代わりに Queen 削り割合を主信号へ差し替えた。
  差し替えは dev5 測定前（`act3_h3_decision_rule_proposal.md`）に固定済み。前提 G を判定前に加えたのも事前登録。
- 配対符号検定: 削り割合の better/worse 件数に McNemar 精密二側 p。確認用で p ≤ 0.05 を採用条件の一つ。

## 8.8 計画数／完了数／不明数／外部障害／候補由来の障害

| 集合 | 計画(試行) | 完了 | 不明 | 備考 |
| --- | --- | --- | --- | --- |
| fid5 忠実性 | 12 | 12 | 0 | 一致 10 / 不一致 2（原因 8.4）。外部障害なし |
| dev5_swap base | 12 | 12 | 0 | 完了（leader） |
| dev5_swap H3a | 12 | 走行中 | — | 実機で流し中。結果待ち |
| dev5_swap H3c | 12 | 走行中 | — | 実機で流し中。結果待ち |
| confirm5_swap base+選定 arm | 12+12 | 0 | — | dev5 の選定結果待ちで未開始 |

外部障害・候補由来の障害は現状なし。同一 trial の例外・通信停止は結果行の `outcome_source != combat_end_trace` で
droppable とし、配対不能として母数に残す（`analyze_bosslab.load_trials`）。

## 8.9 結果（空欄・dev5 実測待ち）

- dev5_swap base 対 H3a: Δshave = （空）、Δfp = （空）、Δwin = （空）、firing_C = （空）、精密 p = （空）
- dev5_swap base 対 H3c（0.5）: 同上（空）
- dev5_swap base 対 H3c（0.3、追加候補）: 未実施（dev5 で A/B を測ってから決める。`act3_dev5_first_extra_candidate.md`）
- 到達点同値の最終戦（Queen 削り割合）の比較可能／不能な組数: （空）。欠測 trace の組は配対不能として数える。
- 確認用 confirm5_swap の結果: 未開始。

## 8.10 判定と次に必要な証拠

- 判定: 未確定（保留）。dev5_swap の結果が出て、前提 G（`firing_C ≥ 4`）と `Δshave > 0・Δfp ≥ 0・Δwin ≥ 0` を満たす
  arm があるかを見る。
- 次に必要な証拠:
  1. dev5_swap base / H3a / H3c の各 turn 番号つきの全ターン発火件数と、Queen 削り割合の配対差（1 コマンドで
     `python3 bosslab/tools/dev5_report.py --base data/bosslab_act3_dev5_swap_base --cand H3a=..._H3a --cand
     H3c05=..._H3c --out bosslab/results/act3_dev5_tuning_report.md`）。
  2. dev5 でゲートを通過した arm があれば、その 1 arm だけ confirm5_swap へ進めて同じ向きか確認する。通過する
     arm が無ければ hybrid は保留。H3c（0.5）が通った場合のみ、閾値 0.3 の追加候補を感度確認として上げる。
  3. 忠実性 2 件の書き戻し hook は、default off のまま fid5 の 2 spec（8aa46daede55 / e030d2f11e5f）で
     `STS2_BOSSLAB_RESTORE_ENTRY_STATE=1` を立てて再走し、一致するか確かめる（手順は 8.11 と codewiki 草案）。

## 8.11 生成・再現手順（実機は leader）

```bash
# panel 生成（原因レリック除外・hash 順）。.dsh は gitignore、plan 成果物は bosslab/plans に commit 済み。
python3 bosslab/tools/make_bosslab_plan.py --specs .dsh/act3_boss_specs.jsonl --arm base --trials-per-arm 1 \
  --offset-start 0 --spec-ids bosslab/plans/bosslab_act3_dev5_swap.speclist \
  --out bosslab/plans/bosslab_act3_plan_dev5_swap.json --md bosslab/plans/bosslab_act3_plan_dev5_swap.md
python3 bosslab/tools/make_bosslab_plan.py --specs .dsh/act3_boss_specs.jsonl --arm base --trials-per-arm 1 \
  --offset-start 0 --spec-ids bosslab/plans/bosslab_act3_confirm5_swap.speclist \
  --out bosslab/plans/bosslab_act3_plan_confirm5_swap.json --md bosslab/plans/bosslab_act3_plan_confirm5_swap.md

# dev5 評価（run dir が揃った時点で 1 コマンド）
python3 bosslab/tools/dev5_report.py \
  --base data/bosslab_act3_dev5_swap_base \
  --cand H3a=data/bosslab_act3_dev5_swap_H3a \
  --cand H3c05=data/bosslab_act3_dev5_swap_H3c \
  --out bosslab/results/act3_dev5_tuning_report.md

# dev5 の arm 実行（H3c 0.3 を足す場合は同じ plan で env だけ差し替え。実機は leader）
#   pwsh -File ./run_official_bosslab.ps1 -GameDir "<game dir>" \
#     -Plan bosslab/plans/bosslab_act3_plan_dev5_swap.json -OutDir data/bosslab_act3_dev5_swap_H3a \
#     -AgentScript bosslab/agents/official_agent_H3a.py ...
#   H3c 0.3: -AgentScript bosslab/agents/official_agent_H3c.py かつ env QUEENFIRST_H3_DANGER_FRAC=0.3

python3 -m unittest discover -p 'test_*.py'   # 960 tests OK（2026-10-29 時点）
```
