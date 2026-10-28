# 新しい走行から採れる Act 3 QUEEN spec プールと H3 用パネルの可否

T32.1 で PenNib ほかしきい値カウンタを復元可能にしたので、次の確認用/開発用パネルは「新しい走行（現行ビルドが
`relic_counters` 列を出した trace）から採った spec だけ」で組む。main の `data/` の実測に基づく。

## 新しい走行の量

| 項目 | 数 | 測り方 |
| --- | --- | --- |
| Act 3 QUEEN に到達した agent trace | 261 | `data/*_agent.jsonl` に `MONSTER.QUEEN` が在る数 |
| そのうち新形式（`relic_counters` 列あり） | 132 | 入室観測に `relic_counters` キーが存在 |
| 更新後抽出器で再生成した dedup QUEEN spec（新旧混在） | 191 | `.dsh/extract_act3_specs.py` を main `data/` へ実行 |
| うち新形式 spec（`relic_counters_observed`） | 114 | spec フィールド |
| うち unresolved なし（usable） | 43 | 入室 hook 系・card_value_state ほかを除いた残りの除去理由なし |
| usable のうち実際にカウンタ値を持つ（この機能で救済される） | 9 | PenNib/Nunchaku/TuningFork の counter が spec に入っている |
| usable かつ used.speclist(26 件) と非重複で次に使える | 35 | 上から used を引く |

カウンタ不明で newly 除外した旧ブリッジ由来 counter-relic spec は 14 件（`relic_counters_unobserved`）。

## 開発 12 組 + 確認 12 組（24 件）を新形式だけで組めるか

- 使える新形式 usable かつ未使用 spec = **35 件 ≥ 必要 24 件**。dev/confirm の 24 件を重複なく選べて、余裕 11 件。
- HP band 内訳 `>=80: 17 / 60-79: 9 / <60: 9`。band 均衡（各 panel 4/4/4、2 件で 8/8/8）で組んでも
  最小 band（60-79 と <60 が各 9）が 8 を満たすので均衡選別も成立。
- 追加の QUEEN 走行は 1 組の dev12+confirm12 には不要（十分）。

## 注意点（正直に出す）

- 記録勝利が new-format usable 全体で **3 件だけ**。パネル自体は成立するが、win 状態の分厚い確認はしたい場合、
  win 到达 spec が足りない。
- 採り直しで 1 セットではなく 2 セット目（通った腕の独立確認用をもう 12+12）を作るなら、余裕 11 件では 13 件
  足りず、追加の Act 3 ボス到達 run が必要になる。概算は「新形式 QUEEN 到達 trace 132 本 → usable 新形式 43 件
  ≒ 1 本あたり 0.33 usable spec」から 13 ÷ 0.33 ≒ **あと 40 本の QUEEN 到達 run**（推定。dedup 重複で実需は増減する）。
  win 到达は 261 本中 10 本（≒ 4%）と低く、win 重視なら本数はさらに増える。これは抽出器出力からの実測比に基づく
  見積もりのみで、実機で確認していない。
