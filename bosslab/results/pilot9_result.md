# PILOT-9: C1の内訳とC2の候補

C1 135本（開発用）と同一seed対照v24。ゲームは起動していない。

## 1. 通過に足りない分の内訳

| 指標 | C1 | 対照 |
| --- | ---: | ---: |
| Act 1突破 | 115/135 | 112/135 |
| Act 2突破 | 38/135 | 38/135 |
| Act 3突破 | 3/135 | 0/135 |
| Queen到達 | 21 | 26 |

- Insatiable（Act 2ボス）入場: C1 82戦 HP平均71.3（中央76）、デッキ22.1枚。対照 85戦 HP平均73.4（中央80）、21.7枚。
  HPが中央で4低く、到達数は3少ない。
- Queen入場: C1 21戦 HP平均76.7、26.5枚。対照 26戦 HP77.2、26.5枚。デッキ枚数は同じ。
- Act 3の敗北は C1 QUEEN 9 + AMALGAM+QUEEN 9 ほか、対照 QUEEN 16 + AMALGAM+QUEEN 10 ほか。構成は近い。
- **engine採用が防御補充を押しのけたrun**: C1 89/135（66%）、対照 53/136（39%）。
  そのうちAct 2突破は C1 26/89（29%）、押しのけの無いrunは 12/46（26%）で、**run単位では悪化していない**。

## 2. Queen削り中央値の低下を計器から疑う

- 分布: C1は二峰。0.0が9本、1.0が3本（踏破）、0.5〜0.8に4本。対照は0.0〜0.2に集中（0.0が5、0.1が7、0.2が7）。
- 両方がQueenに到達した13 seedで配对すると、削り差は平均 +0.197（C1が良い8、対照が良い3）、勝ちは C1 2 対 対照 0。
- つまり「中央値0.175→0.095」は、C1に**早く死ぬrunが増えたこと**と**高い裾（踏破3本）ができたこと**が同時に起きた混合分布の見かけで、同一seedで比べるとC1が上。
  中央値は二峰分布の要約として不適切で、計器の誤りではない。

## 3. 部品1（進捗の評価）はC1の中で効いているか

C1の入場状態（Queen 21、Insatiable 30）で、v1あり/なしをモデル内で比較。

| 戦闘 | 勝ち off→on | 削り off→on | 改善/悪化 |
| --- | --- | --- | --- |
| Queen | 0/21 → 1/21 | 0.201 → 0.246 | 7/3 |
| Insatiable | 12/30 → 14/30 | 0.799 → 0.829 | 11/4 |

C1のデッキでも進捗項はプラス。部品1は残す。

## 4. C2の候補（C1からの変更のみ）

- **候補A（採用して実装）**: ブロック不足のときはengine優先を止め、通常のcore/tier順に戻す。
  発動見込み: engine採用が防御補充を押しのけたrun 89/135（66%）。うち3つのpin
  （`test_strike_deck_with_strength_engine_still_fills_defense_shortage` の3件）が戻る。
  モデル内の確認は**できない**（入場デッキを直に使うシミュレーションなので、報酬側の変更が入場状態に現れない）。
  根拠はpinの復元と、C1で押しのけが起きたrunが66%に達していること。
- **候補B（不採用）**: engine札がそろったデッキで基本札削除を優先する。
  発動見込みはショップのremove機会に依存し、C1の記録では engine札2枚以上かつ remove のあるショップが少数。
  今回の1時間では件数を確定できず、Aに比べて根拠が弱い。

## 5. 実装（候補A）

- ブランチ `cand/engine-pack2`、worktree `~/.sts2/wt-clear5d`、base C1 `8422e56`、commit `c689773`。
- 変更は `official_agent.py` の engine優先ブロック2箇所に `if not _block_starved(deck_list)` を足しただけ。閾値は既存の40%のまま。
- `official_agent.py` sha256 先頭 `3d06083e051a20be`、`combat.py` `932d286163b6071c`（C1と同じ）、DLLはmainからコピーして `592dc5411a6efda5` で一致。
- テスト: 860件中853成功・7失敗。C1の10件から3件（防御不足のpin）が戻った。
  残り: `test_reward_does_not_seed_rupture_without_any_fuel`、`test_uncommitted_rupture_does_not_force_core`、
  `test_shop_strike_axis_does_not_buy_rupture`（過去pinの再発）、
  `test_reward_strike_axis_prefers_second_perfected_strike`、`test_reward_without_strike_axis_keeps_first_tier_card`、
  `test_shop_buys_one_missing_required_card`、`test_shop_prefers_basic_remove_over_ordinary_card_only`（戦略変更の帰結）。

## 6. 留保

- 候補Aの効果はモデルで裏づけられていない（報酬側の変更）。フルrunで測るしかない。
- 削りの分布は21本対26本で、混合の重みが変われば中央値は動く。判定は配对で見るべき。
