# PILOT-6: engine-pack の凍結準備

ゲーム起動なし、main は未変更。候補は `cand/engine-pack`（worktree `~/.sts2/wt-clear5c`、base main `43f0e09`）。
部品ごとにcommitを分けた: `7961d0f`（v1 combat）→ `d799a51`（合法手フォールバック）→ `24afdd7`（報酬・ショップ）→ `8422e56`（Demon Form先出し）。

## 1. 部品

- 打ち手: v1 の combat.py 変更（負けロールアウトに `0.9×進捗`）をBOM付きで入れ、`rollout_choice` の合法手フォールバックも入れた。
- 報酬: `choose_card_reward` で `DEMON_FORM` → `RUPTURE` → `CRIMSON_MANTLE` → `INFLAME` の順に、core/tier判定と `_large_deck_addition_allowed`（HIGH_COST_CAPを含む）より先に見る。同じ札がデッキに2枚あれば飛ばす。ショップの `buys` でも同じ順で先に見る。
- 序盤出し: `bosslab/agents/official_agent_demonfirst.py` の `demon_form_early_direct` をそのまま移植（turn<=2、敵の最大HP>=150、DEMON_FORM_POWER未付与、コスト分のエネルギーがあり、非ブロック被弾がHP未満）。

## 2. 発動見込み（v23+v24の272 run、card_rewardの提示）

- 4枚のどれかが提示された run: **196/272（72.1%）**。
- 内訳（提示run数）: RUPTURE 98、INFLAME 97、CRIMSON_MANTLE 64、DEMON_FORM 62。
- 現行の採用は RUPTURE 39、INFLAME 71、CRIMSON_MANTLE 24、DEMON_FORM 1。DEMON_FORMの1/62が今回の主対象。

## 3. テスト（860件中850成功・10失敗。テストは書き換えていない）

| 落ちたテスト | 分類 |
| --- | --- |
| `test_reward_does_not_seed_rupture_without_any_fuel` | 過去のpin（RUPTUREは燃料なしで軸にしない、CODEWIKI:41）の再発 |
| `test_uncommitted_rupture_does_not_force_core` | 同上（RUPTUREをcore扱いしない） |
| `test_strike_deck_with_strength_engine_still_fills_defense_shortage`（INFLAME/RUPTURE/DEMON_FORMの3件） | 過去のpin（ブロック不足の解消を優先）との衝突。engine優先が防御補充を押しのける |
| `test_reward_strike_axis_prefers_second_perfected_strike` | 戦略変更の帰結（PS軸よりengine優先） |
| `test_reward_without_strike_axis_keeps_first_tier_card` | 戦略変更の帰結（tier判定より先にengine） |
| `test_shop_buys_one_missing_required_card` | 戦略変更の帰結（ショップのengine優先） |
| `test_shop_prefers_basic_remove_over_ordinary_card_only` | 戦略変更の帰結（同上） |
| `test_shop_strike_axis_does_not_buy_rupture` | 過去のpin（strike軸ではRUPTUREを買わない）の再発 |

HIGH_COST_CAP と Relax の経緯（CODEWIKI:41）は読んだ。Relaxは `UNPLAYABLE_REWARDS` で今回の4枚とは無関係。HIGH_COST_CAPは「コスト3以上を2枚まで」で、DEMON_FORMは対象外にしたので、この規則そのものは壊していない。PS上限（1〜2枚の種に制限）は、engine優先がその判断より先に出る点で衝突する（上の`second_perfected_strike`）。

## 4. ハッシュと動作条件

- `official_agent.py` sha256 先頭 `1669d394af4351e6`、`combat.py` `932d286163b6071c`。
- DLLはビルドせず main からコピー。`592dc5411a6efda5` で一致。
- worktree の `data/run_usability.py` と `data/enemies_*.json` が読めることを確認。

## 5. 未実施

- モデル確認（D7/D8）は30分の上限に届かず未実行。走らせる前に必要なら追加で回す。
- 反事実の確認はしていないので、この候補の良し悪しはフルrunの開発用68本で決めるしかない。
