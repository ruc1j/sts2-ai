# Strength札追加の判定（base / str3、G' + 4693f2e 規則）

dev: data/bosslab_act3_str_dev　confirm: data/bosslab_act3_str_conf

G' = addアームの CARD.INFLAME + CARD.DEMON_FORM 使用回数がbaseを超えた組。閾値 4 組（dev 6組中、confirm 12組中）。

## str3 vs base

- 第2段階の読み替え: **効かない**

### 候補 str3: 判定 **不採用**

- 理由: 削り割合が dev5・confirm5 の両集合で `Δshave ≤ 0`、または削りが悪化してかつ 総火力/ターン も base を下回った。base 継続。

- 発火率(dev5): G'発火 = 5/6 組（閾値 4、skipped 0）
- 発火率(confirm5): G'発火 = 12/12 組（閾値 4、skipped 0）
- 前提 G'（両集合で ≥4）: 充足

- dev5: Δshave +0（候補優3/base優3/同値0, p=1.000） Δfp -2.7（base 42.4→cand 39.7） Δwin +0（base 0→cand 0） 配対 12・比較不能 0
- confirm5: Δshave -2（候補優4/base優6/同値2, p=0.754） Δfp -1.6（base 38.8→cand 37.2） Δwin -1（base 1→cand 0） 配対 12・比較不能 0

- dev5 と confirm5 の削り割合の向きの一致: 不一致
  - 条件1: 不充足（原文は上の引用を参照）
  - 条件3: 不充足（原文は上の引用を参照）
  - 条件4: 不充足（原文は上の引用を参照）
  - 条件5: 不充足（原文は上の引用を参照）
  - 条件6: 充足（原文は上の引用を参照）

- dev: 生存ターン 7.00→6.17（add優1/base優4/同値1）　G'発火 5/6組（trace欠落 0）
  - 0be389384303|0: 追加札(Inflame/Demon Form)使用 base 1 → str3 2 [発火]
  - 16d838af30eb|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 2 [発火]
  - 30c98f643174|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 2 [発火]
  - 3bb38a1da0b5|0: 追加札(Inflame/Demon Form)使用 base 1 → str3 3 [発火]
  - a4f376cd945f|0: 追加札(Inflame/Demon Form)使用 base 1 → str3 2 [発火]
  - d22ed45bc52f|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 0
- confirm: 生存ターン 6.58→6.58（add優3/base優4/同値5）　G'発火 12/12組（trace欠落 0）
  - 4bb6cf77fdd9|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 2 [発火]
  - 4c69c357dcda|0: 追加札(Inflame/Demon Form)使用 base 1 → str3 3 [発火]
  - 5b3328eda1dc|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 1 [発火]
  - 60058beedf0a|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 2 [発火]
  - 614271466f56|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 3 [発火]
  - 75495c03f631|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 1 [発火]
  - b37c3498e7f8|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 1 [発火]
  - c589d7860c35|0: 追加札(Inflame/Demon Form)使用 base 1 → str3 2 [発火]
  - e75781521da8|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 3 [発火]
  - eb8756252bb6|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 2 [発火]
  - fd39a3b868b5|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 2 [発火]
  - fef5e8158e35|0: 追加札(Inflame/Demon Form)使用 base 0 → str3 1 [発火]
- 条件6の読み替え（追記）: dev・confirm とも計画した組が全て揃い比較不能0。dev の pairs を confirm に合わせて判定した。

