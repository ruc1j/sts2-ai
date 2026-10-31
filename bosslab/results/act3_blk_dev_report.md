# Block札追加の判定（base / add2 / add4、G' + 4693f2e 規則）

dev: data/bosslab_act3_blk_dev　confirm: data/bosslab_act3_blk_conf（未実行）

G' = addアームの CARD.SHRUG_IT_OFF + CARD.FLAME_BARRIER 使用回数がbaseを超えた組。閾値 4 組（dev 6組中、confirm 12組中）。

## add2 vs base

- 第2段階の読み替え: **判定できない**（暫定: confirm 未実行）

### 候補 add2: 判定 **保留**

- 理由: 確認用（confirm5）の実行待ち。dev5 の結果のみで暫定。

- 発火率(dev5): G'発火 = 3/6 組（閾値 4、skipped 0）
- 発火率(confirm5): 実行データ無し
- 前提 G'（両集合で ≥4）: 未実行

- dev5: Δshave -3（候補優1/base優4/同値1, p=0.375） Δfp -8.2（base 42.4→cand 34.2） Δwin +0（base 0→cand 0） 配対 6・比較不能 0
- confirm5: 未実行（確認用待ち）

- dev5 と confirm5 の削り割合の向きの一致: 未実行
  - 条件1: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件3: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件4: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件5: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件6: 未実行（確認用待ち）（原文は上の引用を参照）

- dev: 生存ターン 7.00→7.00（add優4/base優2/同値0）　G'発火 3/6組（trace欠落 0）
  - 0be389384303|0: Block札使用 base 1 → add2 3 [発火]
  - 16d838af30eb|0: Block札使用 base 3 → add2 2
  - 30c98f643174|0: Block札使用 base 3 → add2 5 [発火]
  - 3bb38a1da0b5|0: Block札使用 base 0 → add2 0
  - a4f376cd945f|0: Block札使用 base 6 → add2 2
  - d22ed45bc52f|0: Block札使用 base 0 → add2 1 [発火]
- confirm: 未実行

## add4 vs base

- 第2段階の読み替え: **判定できない**（暫定: confirm 未実行）

### 候補 add4: 判定 **保留**

- 理由: 確認用（confirm5）の実行待ち。dev5 の結果のみで暫定。

- 発火率(dev5): G'発火 = 4/6 組（閾値 4、skipped 0）
- 発火率(confirm5): 実行データ無し
- 前提 G'（両集合で ≥4）: 未実行

- dev5: Δshave -5（候補優0/base優5/同値1, p=0.062） Δfp -12.5（base 42.4→cand 29.9） Δwin +0（base 0→cand 0） 配対 6・比較不能 0
- confirm5: 未実行（確認用待ち）

- dev5 と confirm5 の削り割合の向きの一致: 未実行
  - 条件1: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件3: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件4: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件5: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件6: 未実行（確認用待ち）（原文は上の引用を参照）

- dev: 生存ターン 7.00→6.83（add優2/base優3/同値1）　G'発火 4/6組（trace欠落 0）
  - 0be389384303|0: Block札使用 base 1 → add4 3 [発火]
  - 16d838af30eb|0: Block札使用 base 3 → add4 1
  - 30c98f643174|0: Block札使用 base 3 → add4 6 [発火]
  - 3bb38a1da0b5|0: Block札使用 base 0 → add4 5 [発火]
  - a4f376cd945f|0: Block札使用 base 6 → add4 6
  - d22ed45bc52f|0: Block札使用 base 0 → add4 4 [発火]
- confirm: 未実行

