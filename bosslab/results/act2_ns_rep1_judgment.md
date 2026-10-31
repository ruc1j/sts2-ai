# Act 2 noshrug の判定（base / noshrug、G'' + 4693f2e 規則）

dev: data/bosslab_act2_ns_rep1_dev　confirm: data/bosslab_act2_ns_rep1_conf

G'' = baseアームの CARD.SHRUG_IT_OFF 使用回数がnoshrugを超えた組。閾値 4 組（dev 12組中、confirm 12組中）。

- 判定: **不採用**

### 候補 noshrug: 判定 **不採用**

- 理由: 削り割合が dev5・confirm5 の両集合で `Δshave ≤ 0`、または削りが悪化してかつ 総火力/ターン も base を下回った。base 継続。

- 発火率(dev5): G''発火 = 8/12 組（閾値 4、skipped 0）
- 発火率(confirm5): G''発火 = 4/12 組（閾値 4、skipped 0）
- 前提 G''（両集合で ≥4）: 充足

- dev5: Δshave +0（候補優3/base優3/同値6, p=1.000） Δfp +0.5（base 29.3→cand 29.9） Δwin +0（base 7→cand 7） 配対 12・比較不能 0
- confirm5: Δshave -1（候補優4/base優5/同値3, p=1.000） Δfp -1.3（base 30.4→cand 29.2） Δwin +1（base 4→cand 5） 配対 12・比較不能 0

- dev5 と confirm5 の削り割合の向きの一致: 不一致
  - 条件1: 不充足（原文は上の引用を参照）
  - 条件3: 不充足（原文は上の引用を参照）
  - 条件4: 充足（原文は上の引用を参照）
  - 条件5: 不充足（原文は上の引用を参照）
  - 条件6: 充足（原文は上の引用を参照）

- dev: 勝ち base 7 / noshrug 7　ボス削り平均 base 83.3% / noshrug 87.0%　生存ターン 8.92→9.00（noshrug優3/base優4/同値5）　G''発火 8/12組（trace欠落 0）
  - 02ce63e28656|1: Shrug使用 base 1 → noshrug 2
  - 1f92269cca69|1: Shrug使用 base 5 → noshrug 4 [発火]
  - 25e4bda4047b|1: Shrug使用 base 2 → noshrug 0 [発火]
  - 42b0443e2e93|1: Shrug使用 base 1 → noshrug 0 [発火]
  - 520b6026f1ef|1: Shrug使用 base 3 → noshrug 3
  - 6f46d84367c0|1: Shrug使用 base 2 → noshrug 0 [発火]
  - 770594549113|1: Shrug使用 base 6 → noshrug 1 [発火]
  - 7ab8203130bd|1: Shrug使用 base 0 → noshrug 0
  - 99848c8a2a05|1: Shrug使用 base 3 → noshrug 1 [発火]
  - dbe0014239e9|1: Shrug使用 base 0 → noshrug 0
  - dbfcde8ae751|1: Shrug使用 base 4 → noshrug 2 [発火]
  - e794f34a10c7|1: Shrug使用 base 2 → noshrug 0 [発火]
- confirm: 勝ち base 4 / noshrug 5　ボス削り平均 base 74.4% / noshrug 75.3%　生存ターン 8.33→8.33（noshrug優3/base優2/同値7）　G''発火 4/12組（trace欠落 0）
  - 0395112a9828|1: Shrug使用 base 0 → noshrug 0
  - 0bee355cb23b|1: Shrug使用 base 5 → noshrug 2 [発火]
  - 346ec700b880|1: Shrug使用 base 2 → noshrug 2
  - 401c5b9edb0e|1: Shrug使用 base 0 → noshrug 0
  - 412d63e4be9e|1: Shrug使用 base 1 → noshrug 2
  - 486f888293cc|1: Shrug使用 base 2 → noshrug 0 [発火]
  - ae8974f4b753|1: Shrug使用 base 1 → noshrug 2
  - b14a4126ee40|1: Shrug使用 base 0 → noshrug 0
  - b1a85c7a9eee|1: Shrug使用 base 1 → noshrug 1
  - b411c1748867|1: Shrug使用 base 6 → noshrug 2 [発火]
  - cbe3ca1b66d8|1: Shrug使用 base 6 → noshrug 5 [発火]
  - f3374cf1f6a3|1: Shrug使用 base 6 → noshrug 7


## 合算（記述のみ、判定は上の機械判定）

元の測定（offset 0）と追試（offset 1）の4集合を並べる。削りの優劣は「noshrug優 / base優 / 同値」。

| 集合 | noshrug優 / base優 / 同値 | Δfp | 勝ち base→noshrug |
| --- | --- | --- | --- |
| offset 0 開発用 | 6 / 1 / 5 | +1.5 | 6→7 |
| offset 0 確認用 | 3 / 6 / 3 | −0.0 | 3→4 |
| offset 1 開発用 | 3 / 3 / 6 | +0.5 | 7→7 |
| offset 1 確認用 | 4 / 5 / 3 | −1.3 | 4→5 |
| 合計（48組） | 16 / 15 / 17 | 約+0.2（平均） | 20→23 |

削りの優劣は合計で16対15、同値17。差は検出されない。勝ちは48組で20対23だが、削りと総火力/ターンに裏づけがない。追試でも開発用と確認用の向きは一致せず、元の測定の割れはゲーム乱数を含む偶然の範囲と読むのが妥当。
