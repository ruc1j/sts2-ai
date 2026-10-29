# fid5 入場忠実性の不一致 2 件の原因（T35、解析のみ）

fid5（`bosslab/results/act3_fid5_fidelity.md`、run dir `data/bosslab_act3_fid5`）は 12 組中 10 組が完全一致。
不一致は次の 2 trial にまたがる。

| trial | spec | 不一致項目 | 直接の原因レリック |
| --- | --- | --- | --- |
| 0009 | `8aa46daede55` | `enemies.id_hp_maxhp`（Amalgam 198/199・Queen 400 が、記録の Amalgam 199・Queen 399 と 1 点ずつ逆） | `RELIC.FORGOTTEN_SOUL` |
| 0010 | `e030d2f11e5f` | `deck.multiset`（lab だけ `CARD.DAZED` が 3 枚多い）、`pile_size.draw_pile`（lab 27 / spec 24） | `RELIC.BLESSED_ANTLER` |

どちらも レリックの カウンタ（PenNib/Nunchaku/TuningFork の `relic_counters`）由来ではない。fid5 が検証した
カウンタ復元と HP clamp 修正（927f26f）は無傷で、`RELIC.ROYAL_POISON` 所持 2 組は HP 一致（上記レポート）。
不一致は両方「入室時または最初のターンの、レリックの入場効果」が lab で一度多く発火して起きる。

## 根拠（デコンパイルと trace）

原因レリックの挙動は dll のデコンパイルで特定した（`$TMPDIR/sts2-ai-decompiled/…Models.Relics/`）。

- `RELIC.FORGOTTEN_SOUL`（`ForgottenSoul.cs`）: `AfterCardExhausted` で、プレイヤーがカードを 1 枚追放すると
  未強化 1 ダメージを 敵 1 体へ与える。狙う敵は `RunState.Rng.CombatTargets.NextItem(HittableEnemies)` で
  乱数選択。`ForgottenSoul.cs:20-30`。
- `RELIC.BLESSED_ANTLER`（`BlessedAntler.cs:45-55`、`relic_entry_effects.py` の `flag_unfixed`）: 最初のターン
  手札を引くとき `BeforeHandDraw` で `CARD.DAZED` を追加する。追加するカードは必ず Dazed（カード内容の乱数はない）。

fid5 の実データで、原因が「入室時点の発火」であることを確認した。元 run の入場観測（`data/…_agent.jsonl` の
entry_seq）は spec と一致し、lab だけがズレていた。

- trial 0009 (`8aa46daede55`, run_seed FD7A9C8F5F, entry_seq 357): 元 run の入場で Queen 399・Amalgam 199・
  exhaust pile 1 枚。spec も同じ（忠実）。lab の再構成入場では Amalgam 198・Queen 400。元 run では入室前に
  1 枚追放済みのカードが FORGOTTEN_SOUL を 1 回発火させ Queen に 1 点乗っていた。lab は同じ入場状態から
  立ち上げる過程で同じ追放をもう一度 FORGOTTEN_SOUL に処理させ、`Rng.CombatTargets` の乱数が別敵（Amalgam）
  を選んだ。与える合計ダメージ（1 点）は同じで、狙う敵だけが違う。
- trial 0010 (`e030d2f11e5f`, run_seed 2872AB854A, entry_seq 398): 元 run の入場 hand 3 枚（うち Dazed 1）
  draw 24 枚（うち Dazed 2）＝ Dazed 合計 3。spec も同じ。lab は hand 3（Dazed 0）draw 27（Dazed 6）＝ Dazed 6。
  BLESSED_ANTLER の「最初のターンに Dazed を引く」効果は元 run で既に適用済み（3 枚が入場 piles に焼き付き）で、
  lab は同じ入場から立ち上げるとき同じ効果をもう一度発火させ Dazed を 3 枚足した。Dazed はカード内容が固定の
  効果なので、発火を止めれば焼き付きの 3 枚のままになり一致する（下記 修正案）。

同じ系統で不一致にならなかった組が、条件の絞り込み根拠になる。fid5/dev5 にある `RELIC.FORGOTTEN_SOUL` 所持
`d22ed45bc52f`（fid5 trial, exhaust 0）と `75495c03f631`（fid5、exhaust 0）は完全一致。入室前に追放されたカードが
無いので FORGOTTEN_SOUL が入場で発火せず、ズレも起きない。つまり FORGOTTEN_SOUL のズレは「所持」だけでは決まらず、
入室前に既に追放 pile が空でない組で起きる。

## 直せるもの（修正案）

両組のズレは「記録済みの入場状態に既に反映済みの効果を lab が再度発火させる」ことで生じる。既存の BossLab は
入場レリック効果を 3 様式で調整している（`relic_entry_effects.py` の defer / reapply_recorded_hp /
widen_potion_slots、および HP clamp 927f26f）。これと同様に、**入室直後に記録した入場状態（敵 HP・最大 HP と
hand/draw/discard/exhaust の各 pile）を lab 側の観測に書き戻す**のが一括の修正案。入場 hook が発火した
あとの状態を spec の記録値で確定させれば、FORGOTTEN_SOUL の再発火（敵 HP 1 点）も BLESSED_ANTLER の再発火
（Dazed 3 枚）も上書きされて入場忠実性が戻る。既にやっている「プレイヤー HP を記録値に固定」を敵 HP と
pile 内容に広げる形。実装は BossLab（dll 側、leader がビルド）で、fid5 を再照合して 12/12 になるかを見る。

なお BLESSED_ANTLER だけを狙って直すなら、`defer_relic_addition` 様式（STONELAB で `AfterRoomEntered` の
deck 変更を遅延させるのと同じ）で BLESSED_ANTLER の `BeforeHandDraw` 注入を起動後に抑えれば、焼き付きの
Dazed 3 枚がそのまま残って一致する。カード内容が固定（必ず Dazed）なので乱数解消は不要。一方 CROSSBOW 等
`flag_unfixed` のうち「ランダムなカードを追加する」レリックは、追加されるカード自体が乱数なので書き戻しで
しか直せない。

## 直せないものへの除外条件（修正案を採らない場合）

BossLab 側を書き戻しで直さず spec 選定で避けるなら、次の条件で除外する（`make_bosslab_plan --exclude-relic`
に渡す一覧）。`RELIC.FORGOTTEN_SOUL` と BLESSED_ANTLER を `relic_entry_effects.py` の表に追加して、選定ツールが
自動で落とせるようにする。

- FORGOTTEN_SOUL 由来の敵 HP 1 点: 除外条件は「`RELIC.FORGOTTEN_SOUL` を所持し、かつ記録入場の
  exhaust pile が空でない組」。所持するだけ（exhaust 0）の `d22ed45bc52f` 等は無害なので残す。乱数選択の
  標的を記録 run と一致させられないため、この条件に当たった組は採否判定に上げず除外する。
- BLESSED_ANTLER 由来の Dazed 追加: 最初のターンに必ず発火し記録入場に焼き付くので、`RELIC.BLESSED_ANTLER`
  を所持する組は入場忠実性パネルから外す。同じく最初のターン固定カード注入の `RELIC.BIG_HAT`
  （Relentless の山札追加）も対象。カード内容がランダム注入の `RELIC.CROSSBOW`（confirm5 の
  `bbbfd4fc2927` が所持）も、開示 hand が一致しないため confirm5 忠実性照合で同じ系統のズレになり得る。

## dev5 / confirm5 への波及（T35.2）

不一致の 2 spec は 24 件のうち dev5 のみに含まれ、confirm5 には入っていない（確認済）。

- dev5: `8aa46daede55`（入場 HP 111、band ≥80 の loss）と `e030d2f11e5f`（HP 77、band 60-79 の loss）を含む。
- confirm5: 2 spec を含まない。ただし `bbbfd4fc2927` が `RELIC.CROSSBOW` を持つ（上記除外条件の候補。confirm5 の
  忠実性照合はまだなので、走るなら同じ入場効果のズレに注意）。

差し替え案は結果（削り・win）を条件にせず、`sha256("dev5-split|<spec_id>")` の hash 順で、同じ band・同じ
outcome（loss）・新形式 usable・used.speclist(26) と confirm5 と非重複・且つ上記の原因レリックを持たない組を選ぶ。
dev5 の band 4/4/4 と win 3 はそのまま保つ。選んだ差し替えは次。生成済み plan: `bosslab/plans/bosslab_act3_plan_dev5_swap.json`。

| 取り除く spec | 差し替える spec（hash 順の先頭） | 入場 HP | band | outcome | 原因レリック |
| --- | --- | --- | --- | --- | --- |
| `8aa46daede55` | `3bb38a1da0b5` | 80 | ≥80 | loss | なし |
| `e030d2f11e5f` | `96c9cc444c23` | 64 | 60-79 | loss | PenNib（カウンタは復元対象で忠実） |

差し替え後 dev5 は band 4/4/4・win 3 を維持（検証済）。band 60-79 の loss で残る候補は `96c9cc444c23` のみ
（PenNib 所持、`relic_counters_observed` 真なので忠実）。残る原因レリックは `d22ed45bc52f` の FORGOTTEN_SOUL
だけだが exhaust 0 なので fid5 で一致済み・ズレない見込み。

生成コマンド（`--spec-ids` は speclist ファイルを指す）:

```bash
python3 bosslab/tools/make_bosslab_plan.py \
  --specs .dsh/act3_boss_specs.jsonl --arm base --trials-per-arm 1 --offset-start 0 \
  --spec-ids bosslab/plans/bosslab_act3_dev5_swap.speclist \
  --out bosslab/plans/bosslab_act3_plan_dev5_swap.json \
  --md bosslab/plans/bosslab_act3_plan_dev5_swap.md
```

## 判断の要約

fid5 の不一致 2 件はどちらも カウンタ由来でなく、レリックの入場時効果（FORGOTTEN_SOUL の乱数標的 1 ダメージ、
BLESSED_ANTLER のターン開始 Dazed 追加）が lab で二度発火して起きた。BossLab が入場直後に記録した敵 HP と
pile を書き戻せば直せる（一括の修正案）。当面 dev5 を走らせるなら、原因レリックを持つ 2 組を clean な別 spec に
差し替えた `bosslab_act3_plan_dev5_swap.json` を使えば同じ band・win 構成で忠実な dev5 が走る。confirm5 は無傷。
