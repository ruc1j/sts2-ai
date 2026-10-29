# H3a/H3c 確認用の事前登録採否規則（最終案・承認で凍結）

前回の規則（`bosslab/results/act3_hybrid_decision_rule.md`、commit 4693f2e）を引き継ぐ。今回唯一の
学びは「候補が発火しなかった」ことなので、**候補の特別規則が実際に発火していることを測定の前提に格上げする**
条件を 1 条だけ足す。これは案で、先生の承認と leader の確認の後で確定する（このファイル時点では凍結しない）。

## 変更点の要点

confirm4 では H1 の「Amalgam を ≤50 で削る」規則が self-lockout で一度も作動せず、H1 は Queen 既定で動いた。
実走の base は Queen 戦で Amalgam 集中なので H1 は base と殴り先が違ったが、それは H1 の意図した削り規則の
結果ではなく既定の反転で、`Δshave` は規則そのものを測っていない（`act3_confirm4_fidelity_causes.md` /
`act3_hybrid_record_draft.md`）。規則が作動しない候補に `Δshave` で採否を出すと、機構をテストしない比較で
判定する。なので前提 G を置き、候補が base と完全一致して何も変わらない場合は採否を出さず保留にする。

## 前提条件 G（発火率、判定の前に検査する）

- G. `firing_C`: 候補 arm について、同じ spec・offset の base trace と配対し、**全ターンの単独攻撃で
  base と別の敵（slot）を狙った組数**を数える（同じ entry の配対 12 組から）。AoE は特定の殴り先を
  表さないため数えない。実装は `bosslab/tools/apply_hybrid_rule.py` の `pair_attack_target_diff`
  （`bosslab_turn_diff.py` と同じ (spec, offset) 突き合わせ）。第一手だけでなく全ターンで見るのは、
  danger 起点の H3c が turn1 では発火せず中盤で発火しうるため、第一手だけを基準にすると実際に発火しうる
  候補を発火 0 に落とすから（実測は `act3_h3_firing_model.md`）。
- dev2 と確認用の両集合で `firing_C ≥ 4` を満たさない候補は充足候補から外す（規則 1-6 の判定材料にしない）。
  候補が 0 件に近く、G を満たす候補が無い panel は測定不能で保留（不採用ではない）。候補が base と
  完全一致なら、機構の作動・不作動のどちらでも起きうる区別のない比較だから。
- 発火には二つの別概念がある。`firing_C`（base と殴り先が違ったか）は「候補が base と違う挙動か」だけを見る。
  arm の意図した Amalgam 削り規則が実際に作動したかは、trace flag `decision_source =
  queen_minion_<arm>_amalgam`（H3a/H3c に実装済み、`test_official_agent_H3.py`）で区別できる。採否の必須
  条件に flag を入れるかは後述の推奨で示す（panel の base 自体が Amalgam 集中なので、flag 単体では発火の
  意味を読み間違える）。両 arm が G を満たし削りが良ければ、arm 間で規則 2 の向き一致で従属則（H1 優先）
  と同様に選ぶ。

## 従来どおり（4693f2e から変更なし、G を通った候補にのみ適用）

規則 1〜6 をそのまま使う（文面は `apply_hybrid_rule.py` に verbatim で固定済みのものを流用）。

1. C\* が confirm4 の主信号 削り割合で `Δshave > 0`、かつ dev2 でも `Δshave > 0`（両集合で同方向）。
2. H3a・H3c の削り割合の向きが dev2 で同じ（ともに `Δshave > 0`）。割れたら機構頑健でなく不採用寄りの保留。
3. confirm4・dev2 両方で `Δfp ≥ 0`（総火力/ターンが base を下回らない）。
4. confirm4・dev2 両方で `Δwin ≥ 0`（勝ちが base を下回らない）。
5. confirm4 の削り割合の配対符号検定で精密二側 p ≤ 0.05。
6. 信頼性の悪化なし（12 組すべて配対、lab 例外・通信障害なし）。新形式 spec だけで組む前提は
   `act3_newfmt_spec_pool.md` を満たすこと。

判定: G を通って 1〜6 をすべて満たす → **採用**。削りが両集合で `Δshave ≤ 0`、または削り悪化かつ火力も
base 下回る、または実装/前提誤りが実測で判明 → **不採用**。削りは改善したが 1〜6 のどれか未满、
または G 不充足（発火せず測定不能） → **保留**。

## 残る確認点への推奨（先生と leader の承認で凍結。承認までは案）

T34.1 で実装した発火測定 `apply_hybrid_rule.firing` を前提に、残った確認点へ推奨を 1 つずつ書く。

1. 閾値 `firing_C ≥ 4`（配対 12 組中）: 推奨は 4 のまま維持。
   - 候補が base と完全一致（fired 0）だと機構の作動・不作動のどちらでも同じ比較になり、採否を出しても
     意味がない。0 件は不採用でなく保留（測定不能）へ送る。4/12 は 1 組だけの偶発的な行動差を弾く下限として
     妥当。H3a/H3c は turn や threshold で中盤に base と差がつく設計なので、全ターン基準なら 4/12 は余裕を
     もって到達する見込み。第一手だけでも dev2 7/12・confirm4 5/12（実測 `act3_h3_firing_model.md`）。
2. 発火の数え方: 推奨は第一手ではなく全ターンの単独攻撃の殴り先差分。実装済みの `pair_attack_target_diff`
   が AoE を除き、単独攻撃の slot を base と付き合わせて数える。
   - danger 起点の H3c は第一手で発火せず中盤で発火しうるため、第一手基準では発火 0 に化ける。全ターン差分で測る。
   - trace flag を必須条件にしない推奨。panel の base（`official_agent.py` の Queen 戦短絡）自体が Amalgam
     集中なので、候補は arm せず Queen に振れた組で base と差がつく。`firing_C` は arm が作動した数でなく
     base と違った数を見る。confirm4 の H1 は ≤50 削り規則が一度も作動していないのに、Queen 既定で base
     （Amalgam 集中）と 12/12 殴り先が違った（`act3_h3_firing_model.md`）。flag（`decision_source` の
     `_amalgam` 决策数）は、差が規則の作動由来か既定反転由来かを解読する補助に留め、採否の必須条件は
     `firing_C ≥ 4` のみとする。flag 読みは解釈メモとして results に出す。
   - dev2 で G を満たす候補が無い（全候補が base と一致）なら選定前の保留（測定不能）で確定。確認用で選択候補の
     `firing_C` が 4 未満へ落ちた場合も不採用でなく保留（測定不能）。実装は `apply_hybrid_rule` の
     `SELECT_NOFIRE` と G 判定。
3. 0 件の扱い: 推奨は 不採用でなく保留。上記 1 と同じ趣旨で `apply_hybrid_rule` に実装済み。

凍結は、この推奨を先生が承認し leader が確認した時点で行う（承認前のいまは案）。`apply_hybrid_rule` は G を
組み込み済みで、`firing=None`（発火測定を省略）では 4693f2e の 1-6 と同一挙動を保つ。単体テストは
`test_apply_hybrid_rule.py` に発火の配対と G 判定、`test_official_agent_H3.py` に H3a/H3c の flag 挙動を置いた
（suite 953 pass）。
