# confirm4 base 忠実性チェック（T25.2、12/12）

lab の戦闘開始観測を plan の entry（spec 抽出）と突き合わせた結果。判定には使わない忠実性の確認のみ。
927f26f 入り DLL での実行。`bosslab_fidelity.py --all` の生ログと集計（`confirm_fidelity_report.py`）。

## 結論

- spec entry と完全一致（lab vs spec 一致）: **7 / 12**。
- ROYAL_POISON を持つ組の HP: **2 組とも lab hp = spec(記録) hp に一致**（修正 927f26f で記録値に着地）。
  - trial 0001 (spec c589d7860c35): lab 53 / 記録 53 / 元trace 53 → 一致
  - trial 0008 (spec 59ed603b4b73): lab 90 / 記録 90 / 元trace 90 → 一致
  - 修正前の confirm2（927f26f 前 DLL）では同種の組が lab 90 / 記録 94 で「HP 未修正」だった（RoyalPoison のターン 1 自己ダメ 4 を二重に引いていた）。927f26f で解消された。
- 5 不一致の内訳（項目）: `relic_counters` 3、`deck.multiset` 1、`enemies.id_hp_maxhp` 1。いずれも「spec vs 元trace: 一致」＝抽出は忠実で、ずれたのは lab 側が入場時に作る状態。**HP・ポーション（927f26f の対象）の不一致は 0 件。**

## 不一致の各原因

- **relic_counters（trial 0002 / 0006 / 0010、3 件）**: 3 件とも `RELIC.PEN_NIB` を持つ。PenNib は 3 打撃毎にカードを配るレリックで、カウンタ（次の配直到達度）は per-run の `[SavedProperty]` で trace に出ない。spec（抽出）は counter 項目を持たず `{}`、lab は新規付与で `{"RELIC.PEN_NIB": 0}` を報告 → key の有無で不一致。 PENDULUM と同じ「trace に出ない per-relic カウンタ」の筋だが、PenNib は confirm4 の除外条件（PENDULUM / PAELS_CLAW / flag_unfixed 族）に入っていない。実走がボス入室時にカウンタ 1 以上の進捗だった可能性を lab は復元できないので、**PenNib 所持 spec も PENDULUM と同様に除外候補**（3 件）。
- **deck.multiset（trial 0007、1 件）**: lab は `CARD.TAUNT` と `CARD.DEMON_FORM` を +1（アップグレード）で、記録（元trace も +0）は未アップグレード。lab 側が入室時に 2 札を上げた。0007 は entry-effects 系レリック（STONE_CRACKER 等）を持たないので、原因は別途特定要（entry upgrade か mid-run upgrade の取り込み）。HP/火力とは別枠の 1 件。
- **enemies.id_hp_maxhp（trial 0011、1 件）: Amalgam 1 点 / Queen 1 点の配分差。** lab は Amalgam 198（1 被弾）・Queen 400（満了）、記録（元trace）は Amalgam 199（満了）・Queen 399（1 被弾）。入場前の 1 ダメージが別の敵に入っている差。敵合計 HP は同じ。0011 も entry-effects 系レリックを持たない。1 点配分のみの差で、判定の削り割合（Queen 主信号）には Queen 残 HP 1 点ぶん効くが、絶対値が元 run 基準で効きは別。原因は別途特定要。

## 総括

HP（ROYAL_POISON/PANTOGRAPH）とポーション枠（PHIAL_HOLSTER）の忠実性は confirm4 base で取れた（完全一致 7 組のうち HP・ポーション起因の不一致は無し、ROYAL_POISON 2 組は一致）。残る 5 不一致は per-relic カウンタ（PenNib 3、trace 出ない）、札の upgrade 配分（1）、敵の 1 点配分（1）で、PenNib は除外条件の見直し候補。base の H1 完了待ちで判定規則はまだ適用していない（apply_hybrid_rule.py は H1 完了後に 1 回だけ走らせる）。
