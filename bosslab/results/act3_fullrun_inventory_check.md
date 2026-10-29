# Act 3 フルrun 棚卸しの独立再計算と使用済み seed（T45、2026-10-29）

## 一致の可否

**一致。** leader の数値（Act 3 進入 45、Queen 戦った 33、踏破 1）と、私が trace から別組み立てで数えた結果
（45 / 33 / 1）が完全一致。食い違う run は無し。

対象: `data/astra_ctrl_v23_*_manifest.json` 136 本（arm=control、commit 775f366）。leader のスクリプトは使わず、
各 `*_agent.jsonl` trace を戦闘単位で読んで数えた（方法は下の「数え方」）。manifest の `outcome.depth` からも
同じ数を独立に確かめ、両者が一致した。

## 数え方（trace 由来・leader の manifest 集計とは別系統）

trace 各行は观测で、`phase` と `run`（`{act, floor, boss_encounter_id}`、act は 0 から＝2 が Act 3）を持つ。
戦闘は `combat` 行の並びで、`combat_end`（`won`）で閉じる。

- Act 3 進入: `run.act == 2` の記録が 1 つでもある run（＝Act 3 の床に到達）。→ **45**
- Queen と戦った: 戦闘ブロックの敵 id に `MONSTER.QUEEN`（Act 3 boss。子分は `MONSTER.TORCH_HEAD_AMALGAM`）が
  1 回でも現れた run。→ **33**
- 踏破: QUEEN を含んだ戦闘の `combat_end.won` が true（boss を倒した）。→ **1**

同じ集合を manifest 側から独立に数えると、`outcome.depth[0] >= 3`（到達 act が Act 3 以上、depth は 1 から）が
**45**、`act_3_complete` が **1** で、trace 集計と同数。進入 45 の内訳は Act 3 到達後に Queen まで行った 33 と、
Act 3 途中で落ちた 12（例: 03384FE967 は Act 3 2 床の DEVOTED_SCULPTOR 戦で死亡し Queen 未戦）。踏破 1 組は
Queen 戦闘を勝った run の 1 本のみ。

## 使用済み seed の一覧

`data/` の全 manifest と trace、および bosslab plan（`~/.sts2/wt-bosslab/bosslab/plans/*.json`）に出てくる seed を
集めて、1 行 1 seed（10 桁英数字）、重複なしで 1 ファイルにまとめた。

- ファイル: `bosslab/results/act3_fullrun_used_seeds.txt`（**801 seed**）
- 収集元: data 直下の manifest 695 本（`seed` 欄）、trace 2208 本（ファイル名の 10 桁 token と、行内の `seed`/`run_seed` 欄）、
  result json の seed 欄、bosslab plan 21 本の trial `run_seed`。重複除去で 801。
- 形式検証: 全 801 行が 10 桁の英数字（大文字）、重複 0、棚卸しの control seed 136 件すべてを含む。

新規のフルrun を組むときは、この 801 seed に無い seed を選ぶ基準に使える（plan 実行 seed と run seed が同じ
集合から採られるため）。
