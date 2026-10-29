# dev5 で比べる調整の範囲（上限 3 構成）

dev5（開発用 12 組）で、候補 arm のパラメータを何構成まで比べてよいか決める。H3a は Amalgam を削る
ターン数 `N ∈ {1,2,3}`（`QUEENFIRST_H3_OPEN_TURNS`、既定 2）、H3c は危険閾値 `thr ∈ {0.3,0.5,0.7}`
（`QUEENFIRST_H3_DANGER_FRAC`、既定 0.5）。全組み合わせは 9 だが、dev5 で回す上限を **3 構成**に絞る。

## dev5 で回す 3 構成

| 構成 | arm | パラメータ | dev5 で見るもの |
| --- | --- | --- | --- |
| A | H3a | N=2（設計既定） | 序盤 Amalgam 削りが dev12 で Δshave>0 かつ `firing_C ≥ 4` になるか |
| B | H3c | thr=0.5（設計既定） | 危険時に削る arm が dev12 で同じ条件を満たすか |
| C | H3c | thr=0.3（より素早く作動） | H3c が実際に発火しうる下限方向の感度 |

base（Amalgam 集中）との差分は `apply_hybrid_rule.firing`（全ターンの殴り先差分）で測り、採否は凍結予定の
規則 1-6 で dev5 側のみ先に確認する。dev5 で G（`firing_C ≥ 4`）を通らない arm は、その場で 採否判定に
上げず保留（測定不能）に置く。

## 残りの 6 構成を dev5 で回さない理由

- 調整を増やすほど dev12 に対する過剰適合（multiple comparisons）が進み、dev で選んだ候補を確認用に投げる際の
  選択バイアスが confirm の信頼を落とす（`bosslab/results/act3_newfmt_spec_pool.md`）。
- 上限 3 の意図: 各 arm の設計既定を 1 点ずつ(A・B)見て、片方でも base を上回るかを判定する。加えて H3c だけ
  発火しやすさ方向(0.3)を 1 点(C)。`H3c=0.3` を選んだのは、H3c が turn1 で発火しにくい実測
  （`act3_h3_firing_model.md`: 第一手で 0/12）で、既定 0.5 でも中盤に届かない場合に規則が一度も作動せず
  測定不能に倒れるリスクを、低い閾値で一度だけ潰すため。それでも満たなければ H3c はそのラウンドで保留。
- `H3a N=1/3` と `H3c thr=0.7` は dev5 では回さない。これらは「設計既定の arm が dev で有望だったが境界感度が
  知りたい」ときに、承認済みの次の dev ラウンドで調べる保留枠。先に 9 構成全部を dev で走らせない。

## dev5 → confirm5 への受け渡し（汚染の下限）

dev5 で 3 構成を比べ、規則の dev 側候補選定（両 arm 方向一致、`firing_C ≥ 4`、Δshave>0 など）で 1 つの
arm だけを選び、それを confirm5 の 1 比較に載せる。確認用は候補を増やさず 1 構成のみで測るため、複数の候補
から選び分ける操作は dev 側の 1 段階に限定され、confirm 自体は単一の照合として保たれる（`docs/EVALUATION.md`
の dev/confirm 分離の趣旨）。dev5 の trial 数は 3 構成 × 12 組 + base 12 組 = 48 run、confirm5 は選ばれた
1 arm + base で 24 run。leader の実機負荷も dev 3 構成に抑える。
