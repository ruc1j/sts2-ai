# Act 2 noshrug の判定（base / noshrug、G'' + 4693f2e 規則）

dev: data/bosslab_act2_ns_dev　confirm: data/bosslab_act2_ns_conf（未実行）

G'' = baseアームの CARD.SHRUG_IT_OFF 使用回数がnoshrugを超えた組。閾値 4 組（dev 12組中、confirm 12組中）。

- 判定: **保留**（暫定: confirm 未実行）

### 候補 noshrug: 判定 **保留**

- 理由: 確認用（confirm5）の実行待ち。dev5 の結果のみで暫定。

- 発火率(dev5): G''発火 = 6/12 組（閾値 4、skipped 0）
- 発火率(confirm5): 実行データ無し
- 前提 G''（両集合で ≥4）: 未実行

- dev5: Δshave +5（候補優6/base優1/同値5, p=0.125） Δfp +1.5（base 28.2→cand 29.7） Δwin +1（base 6→cand 7） 配対 12・比較不能 0
- confirm5: 未実行（確認用待ち）

- dev5 と confirm5 の削り割合の向きの一致: 未実行
  - 条件1: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件3: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件4: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件5: 未実行（確認用待ち）（原文は上の引用を参照）
  - 条件6: 未実行（確認用待ち）（原文は上の引用を参照）

- dev: 勝ち base 6 / noshrug 7　ボス削り平均 base 81.2% / noshrug 87.0%　生存ターン 9.17→9.08（noshrug優4/base優3/同値5）　G''発火 6/12組（trace欠落 0）
  - 02ce63e28656|0: Shrug使用 base 2 → noshrug 2
  - 1f92269cca69|0: Shrug使用 base 7 → noshrug 3 [発火]
  - 25e4bda4047b|0: Shrug使用 base 0 → noshrug 0
  - 42b0443e2e93|0: Shrug使用 base 0 → noshrug 0
  - 520b6026f1ef|0: Shrug使用 base 5 → noshrug 2 [発火]
  - 6f46d84367c0|0: Shrug使用 base 2 → noshrug 0 [発火]
  - 770594549113|0: Shrug使用 base 5 → noshrug 0 [発火]
  - 7ab8203130bd|0: Shrug使用 base 0 → noshrug 0
  - 99848c8a2a05|0: Shrug使用 base 1 → noshrug 1
  - dbe0014239e9|0: Shrug使用 base 2 → noshrug 0 [発火]
  - dbfcde8ae751|0: Shrug使用 base 5 → noshrug 3 [発火]
  - e794f34a10c7|0: Shrug使用 base 3 → noshrug 4
- confirm: 未実行

