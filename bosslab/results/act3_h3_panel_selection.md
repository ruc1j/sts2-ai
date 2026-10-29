# Act 3 H3a/H3c 用パネルの選定（fid5 / dev5 / confirm5）

母集団は、更新後抽出器で再生成した `.dsh/act3_boss_specs.jsonl`（191 件）から、`relic_counters_observed` が
真で unresolved が空の新形式 usable spec、かつ `bosslab_act3_used.speclist`（26 件）と非重複の **35 件**。
選択順は `sha256("<order-seed>|<spec_id>")` の hash 順、band は `<60 / 60-79 / >=80` の 3 帯。panel は
いずれも base deck の plan（`--spec-ids` 手動選択、base 1 trial/spec）。H3a/H3c と base の違いは deck ではなく
agent 側の env（`QUEENFIRST_H3_OPEN_TURNS=2` / `QUEENFIRST_H3_DANGER_FRAC=0.5`）で、leader が同じ plan を
3 構成で走らせる。

## 3 パネルの関係

| panel | 件数 | band | 記録win | 重複条件 |
| --- | --- | --- | --- | --- |
| fid5（忠実性再照合） | 12 | 4/4/4 | 3 | 単独。カウンタ値を持つ spec 9（必須）+ 無カウンタ control 3（band 毎 1） |
| dev5（開発用） | 12 | 4/4/4 | 3 | fid5 と重複してよい（fid5 の 10 件を含む）。confirm5 とは非重複 |
| confirm5（確認用） | 12 | 4/4/4 | 0 | fid5 と非重複、dev5 と非重複（=確認用は fid5/dev と完全に別集合） |

`fid5 ∩ confirm5 = ∅`、`dev5 ∩ confirm5 = ∅`、`dev5 ∩ fid5 = 10 件`（leader 許可どおり fid5 は dev の一部）。
3 パネルの延べ distinct は 26 件（35 件中、次に回せる余り 9 件）。

## 勝ち状態の偏りについて（正直な注記）

新形式 usable の 35 件のうち記録勝利は **3 件だけ**で、3 件はすべてカウンタ系レリック（PenNib/Nunchaku）を
持つ spec。カウンタ系 spec は fid5 に必須で入るため、`fid5 ∩ confirm5 = ∅` の制約から **confirm5 は win 0 に
構造的に決まる**（fid5 を除いた集合に win spec が残らない）。dev5 には fid5 重複が許されるので 3 件を入れ、
win 挙動は dev5 と fid5 でのぞく。結果、確認用の Δwin 条件（規則 4）は全 loss の entry で測ることになり、
候補が base の勝ちを下回らないかは確認用では自動で満ち、dev5 側で win 減少の有無を見る。win の厚みを増すには
`act3_newfmt_spec_pool.md` のとおり追加の Act 3 ボス到達 run が必要（win 到达は 261 中 10 ≒ 4%）。

## 選定手順（再現）

1. fid5: 35 件のうちカウンタ値を持つ 9 件を必須で全採用（band 3/3/3）。残り 3 件は band 毎に
   restorable counter を持たない control を `order-seed=fid5-ctrl` の hash 順で 1 件ずつ（fid5 を 4/4/4 に）。
2. confirm5: 35 件から fid5 の 12 件を除いた 23 件を `order-seed=confirm5-split` の hash 順に並べ、band 毎
   最大 4 件ずつ選んで 12 件（4/4/4、この段階で win は 0）。
3. dev5: 35 件から confirm5 の 12 件を除いた 23 件から、まず win 3 件（fid5 所属）を必須で確保し、band 毎
   4 件になるまで `order-seed=dev5-split` の hash 順で補う（4/4/4、win 3）。fid5 と重複してよい。

band 毎 4 件の内訳は、confirm5 候補 23 件が `>=80:13 / 60-79:5 / <60:5`、dev5 候補 23 件も同程度で、どの band
も 4 件を確保できるため 4/4/4 が成立した。used.speclist はこの 3 パネルの実機 run 後に leader が更新する前提で、
dsh 側は 26 件のまま維持した。
