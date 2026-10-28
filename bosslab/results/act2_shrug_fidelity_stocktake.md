# Act 2 Shrug It Off 再測定のための忠実性棚卸し（T27.3、plan は作り直しの必要なし）

bosslab/plans/bosslab_plan_A.json と _B.json（Act 2 の Shrug 計画、arms `base` / `+shrug`、
trials_per_arm 2、10 spec × 2 腕 = 40 trial、両 plan は同じ 10 spec）。今の DLL（927f26f 入り）で、
入場状態の忠実性に効くレリックを各 trial が持つ entry 状態から直接数えた。判定規則の実行とは別に、
次の goal の準備。

## 結論

- 7 指定レリックのうち、**除外が必須なのは RELIC.PENDULUM を持つ spec 1 本だけ**（`08e473c76604`、両 plan 共通）。
  PENDULUM の TurnsSeen（3 ターン毎 wrap で初ターンに 1 枚引く）は trace に出ない per-relic の run 状態で、
  lab は復元できず実走の入室手札（カウンタ 2 なら 6 枚）と lab（新規 5 枚）がずれる。
- **RELIC.PANTOGRAPH（3 spec）と RELIC.STONE_CRACKER（1 spec）は除外不要**（BossLab が処理済み）。
  - PANTOGRAPH は `reapply_recorded_hp`（927f26f で初手判断直前に記録 HP を 1 回再適用）。confirm4 base で
    回復/ROYAL_POISON 起因の HP 不一致 0 件・一致 7/12 を実測済み（`bosslab/results/act3_confirm4_fidelity.md`）。
  - STONE_CRACKER は `defer_relics`（入室 hook を走らせない）。deck multiset と各札の cost/値は一致し、
    入室 hook の 2 ランダム升级の二重発火は起きない。副作用で StableShuffle が開戦手札の RNG を消費しない
    ので引かれる札だけ実走と違う（中盤以降の状態と deck multiset で判定すれば無害）。
- RELIC.PHIAL_HOLSTER / ROYAL_POISON / CROSSBOW / PAELS_CLAW / POTION_BELT / ALCHEMICAL_COFFER /
  TOOLBOX 等の flag_unfixed 族 / PEN_NIB / 他の回復系（MEAL_TICKET, ETERNAL_FEATHER, PLANISPHERE）は
  どの spec にも 0 件。ポーション枠の再計算（widen）も、ランダム配布（flag_unfixed）も不要。

## 除外条件と panel への影響

- 除外条件: `RELIC.PENDULUM` を持つ spec を plan から落とす（両 plan: spec `08e473c76604`）。
  指定 7 レリックで判定すると `PANTOGRAPH` は BossLab 処理済なので除外しない（外すと回復系を過剰に落とす）。
  実運用の除外は「trace に出ない per-relic カウンタ」条件＝PENDULUM（＋前項の PenNib。今回は 0 件）。
- 影響: PENDULUM spec を 1 本除外すると各腕 2 trial ずつ消え、base / +shrug 配対は 9 spec × 2 腕（18 trial）に
  なる。両腕同じ 9 entry 配対なので base vs +shrug の比較は成立する。+shrug 腕は base deck に
  `CARD.SHRUG_IT_OFF+0` を 1 枚足すだけの差分（他は同一）で、Shrug 単体の効果を測る構図は保たれる。
- **plan を作り直す必要は「配対比較が成り立てば不要」**: 9 spec で比較は有効。元の 10 spec panel 規模
  （前回の Act2 結果と同数）を保ちたいなら、PENDULUM spec を別の Act2 クリーン spec 1 本に差し替えて
  10 spec に戻す。再測定の主眼は前回の欠陥＝ポーション効果が欠けていた点なので、entry 忠実性は上記 1 本
  を除き既に取りうる、という結論。

## 注記（この棚卸しの範囲外）

- 前回 Act2 はポーション効果が欠けた状態での走行。今回の entry 忠実性の棚卸し（レリック起因）は上記で、
  「Shrug の Block とポーション効果が lab/シミュレータで正しく発火するか」は runtime の別問題。結果を
  信用する前に、その効果経路が今の DLL / combat.py で通っているかを leader 側で別途確認するのがよい。
- 10→9 spec（×2 腕=18 trial）は Shrug の効果差を見るには母集団が小さい。同じ entry 配対で base 優/+shrug
  優を数える符号検定にかけられる最小構成として、必要なら spec を増やす（10 に戻すか 12 へ）判断は leader。
