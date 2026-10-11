# 2026-10前半の機構・パネル記録(event効果、shop、power/relic実装、Rampart・Axebot・Decimillipede等)

`docs/CODEWIKI.md`から2026-10-11に移した記録。本文は移す前のまま。

## event の option effect（v0.107.1、ilspycmd で確認、panel の reach 付き）

`choose_event` は `EVENT_OPTION_SCORES` に entry の無い event について `{"type": "event_fallback"}` を返し、`EventBridge.cs`（line 141-152、pin `test_official_agent.py:4869`）はそれを `invalid_event_action` として game の fallback に投げる。panel では 81 decision 中 26件（6 seed）がこれに該当する。実走で測れない理由は、trace の event record に**選ばれた option しか残っていない**こと（observation の `options`/`legal_actions` が残っていない）。

panel で出現した未coverage event の effect（decompile 済み）：

| event | option → effect | panel reach |
| --- | --- | --- |
| `SPIRIT_GRAFTER` | LET_IT_IN = heal 25 + `Metamorphosis` を deck に追加 / REJECTION = 1枚 upgrade + 10 Unblockable damage | 2 |
| `THE_LEGENDS_WERE_TRUE` | NAB_THE_MAP = `SpoilsMap`（curse）追加 / SLOWLY_FIND_AN_EXIT = 8 Unblockable damage | 2 |
| `BRAIN_LEECH` | SHARE_KNOWLEDGE = colorless pool から card 1枚 / RIP = 5 Unblockable damage | 2 |
| `DOLL_ROOM` | RANDOM / TAKE_SOME_TIME = 5 damage / EXAMINE = 15 damage（RANDOM の中身は event state 依存） | 1 |
| `WHISPERING_HOLLOW` | GOLD = 35 gold / HUG = HP loss + Transform | 1 |
| `LOST_WISP` | CLAIM = 60 gold + `Decay`(curse) / SEARCH = `Decay`(curse) のみ → **CLAIM が fact 上 strict に良い** | 1 |
| `FIELD_OF_MAN_SIZED_HOLES` | RESIST = `Normality`(curse) / ENTER_YOUR_HOLE = `PerfectFit` enchantment + gold | 1 |
| `THE_LANTERN_KEY` | RETURN_THE_KEY = 100 gold / KEEP_THE_KEY = fight | 1 |
| `TEA_MASTER` | `BoneTea` / `EmberTea` / `TeaOfDiscourtesy` の relic 選択（observation に relic_id が載らない） | 1 |
| `TINKER_TIME` | card type を選んで効果（12 damage / 8 block / Weak 2 / Vulnerable 2 / Strangle 6 / energy 2 / Strength 2 / Dexterity 2） | 1 |
| `POTION_COURIER` | GRAB_POTIONS = `FoulPotion` / RANSACK | 1 |
| `INFESTED_AUTOMATON` | STUDY / TOUCH_CORE | 1 |
| `DENSE_VEGETATION` | TRUDGE_ON = HP loss / REST → FIGHT | 1 |
| `WELCOME_TO_WONGOS` | BARGAIN_BIN / FEATURED_ITEM / MYSTERY_BOX / LEAVE（purchase） | 1 |
| `TRIAL` | curse（`Regret` / `Shame`）分岐 | 1 |
| `BUGSLAYER` | EXTERMINATION = `Exterminate`（未モデル化） / SQUASH = `Squash`（cost 1、damage 10） | 3 |
| `SAPPHIRE_SEED` | EAT = heal 9 / PLANT = `Sown` enchantment | 2 |
| `COLOSSAL_FLOWER` | gold 35/75/135 で dig、damage 5/6/7 | 1 |

fact 上 strict に優る選択は `LOST_WISP` の CLAIM だけで、reach 1（閾値 3 件/3 seed 未満）。残りは「heal/gold/curse/upgrade の trade-off」で、policy の既存 criterion（block-starved、low HP、relic axis）と同じ方向なので、単独の lever として測る意味が無い。よって event scores は追加分を書かない（reach ≥3 が出るまで書かない）。

## shop の affordability は bridge の filter が source（v0.107.1、code + 全 trace で確認）

`ShopBridge.cs`（line 143-194）は observation の `cards`/`relics`/`potions`/`removal` に `cost` と `affordable` を载せ、`legal_actions` には `IsStocked && EnoughGold` の slot だけを追加する。potion はさらに free slot が無いと列挙されない（line 193）。`choose_shop` は `legal_actions` だけで采点するので、**policy が购买できない item を選ぶことは構造上無い**。pin：`test_shop_never_picks_a_card_that_is_not_in_legal_actions`。

実測で確認（panel 8 seed + astra 107 run の全 `decision_reason`）：`invalid_shop_action` / `invalid_potion_action` / `potion_slots_full` は 0件。curse がいて removal が offer されている shop decision 63件で policy は 63/63 removal を選んだ。`choose_shop` の skip は terminal branch（line 2155）で、removal が affordable で curse が無い case の skip は 0件 → policy は自分の criteria に対して整合的。

gold は shop 間で持ち越されるが、最後の shop 以降の gold は combat に効かない（value 0）。astra 107 run の final gold median 121（59 run が ≥100）で、これは「bar を下回った item ばかりだった」ことを意味するだけで defect は無い（bar が高いかは policy choice の話、path closed）。

## 未モデルだった power / relic / curse を実装（2026-10-04、実走測定前）

「対応表にあっても combat.py が消費しなければ一度も発火しない」という既知の欠落 class を、
trace の観測 id 集計で洗った（player powers 56 id 中 8、relic 40 id 中 29 が未対応だった）。

| 追加 | 機構（decompile 由来） | corpus の観測回数 |
|---|---|---:|
| Wither | Curse、`HasTurnEndInHandEffect` で 3 flat Unpowered。`Unblockable` が無いので block が吸収する（Beckon / Bad Luck と違う）。`CARD_NAMES` 対応 + `HAND_INJECTED_STATUS` | 0（corpus 未観測、decompile からの補完） |
| Fiddle | `ModifyHandDrawLate` +2、`ShouldDraw` が hand draw 以外のドローを拒否 | 242 |
| Blood-Soaked Rose | `ModifyMaxEnergy` +1 を毎ターンの energy reset で加算 | 70 |
| Forgotten Soul | `AfterCardExhausted`：1 Unpowered を**ランダム1体**へ（Charon's Ashes の全体とは違う） | 74 |
| Chains of Binding | `AfterCardDrawn` が自分のドローを Amount 枚まで Bound にする。live の hand は bridge の `bound` で既に正しかったが、rollout 内のドローが対応していなかった | 3849 |
| Duplication / OneTwoPunch | `ModifyCardPlayCount +1`：その play の解決がもう1回走る。Attack は hit が倍、block card は grant が倍。play で消費され、turn end で除去 | 69 / 10 |
| Gigantification | 最初に打った powered Attack の damage を ×3、その command で decrement | 38 |
| Panache | `AfterCardPlayed`：適用した play は数えず（`alreadyApplied`）、以降5枚目の play で Amount（10/14）を全敵へ Unpowered、counter リセット | 20 |

機構としての正しさは test_combat の追加分で固定した。実走 panel を回していないので**勝率への効果は未評価**。

### 残っている未モデル

- **PollinousCore**：counter が戦闘横断の `SavedProperty` で観測に無い。phase が不明なので modelable でない（relic counter は観測不能、という既存の結論どおり）
- **BigMushroom / RoyalPoison / Lantern / BagOfMarbles / Vajra / Gorget / Bronze Scales**：effect が combat 開始時または turn 1 だけ。最初の観測が既に反映しているので rollout に影響しない
- **GamblingChip**：player の選択（何枚捨てるか）が模型外
- **ImprovementPower**：`AfterCombatEnd` で deck を upgrade。戦闘内の decision に無関係
- **StratagemPower**：機構は正しいが 2026-09-12 の実走で QUEEN 残 151→363 へ悪化、不採用
- **Enthralled / Wound / Dazed**：combat effect が無い（Eternal / Unplayable のみ）。Dazed は draw pile の汚れとしてのみモデル

## 固定8 seed panel の A/B 完走（2026-10-03）と −6 の原因

arm = HEAD（未モデル power/relic/curse 実装）、control = `e808bdf`（同一条件で取り直した基準）。
game v0.107.1、固定ユーザーデータ、`simulations=100`、Act 3まで、各 seed 1 run。判定はトレースの `won`。

| seed | control | arm | delta | arm の発火 | decision列 |
|---|---:|---:|---:|---|---|
| 9X9WQB4QIH | 14 | 14 | 0 | DuplicationPower 1回 | 完全一致 |
| NFH3RMVJ6D | 15 | 15 | 0 | なし | 完全一致 |
| EAIF2UUVCK | 14 | 14 | 0 | なし | 完全一致 |
| 73P61QQZNU | 13 | 13 | 0 | なし | 完全一致 |
| AM8C6YXHSG | 17 | 11 | **−6** | なし | seq 244 から分歧 |
| VTW80ZJA2G | 13 | 13 | 0 | なし | 完全一致 |
| GEFYYKH1YK | 7 | 7 | 0 | なし | 完全一致 |
| SWRUL944UU | 6 | 6 | 0 | なし | 完全一致 |
| **合計** | **99** | **93** | **−6** | | |

7 seed は decision列が control と完全一致＝測定不能（発火がないのでarm/controlが同じ選ぶ）。
panel 全体で唯一動いた AM8 の −6 は、**機構の実装ではなく生成プールの副作用**だった。

### seq 243 の切り分け（`data/replay_243.py`）

同一 observation を両commitで replay すると記録値がそのまま再現される（arm 1.9925 / control 1.956875）。
hand・draw pile・enemies・powers・relics は完全一致。差の原因は `STOKE_GENERATION` の中身：

```
arm : (..., 'Offering', 'One-Two Punch', 'Pacts End', 'Panache', 'Peck', ...)
ctrl: (..., 'Offering', 'Pacts End', 'Peck', ...)
```

`STOKE_GENERATION` は `CARD_COST` から導出されるので、PANACHE と ONE_TWO_PUNCH を `CARD_COST`
へ足した時点で生成プールが silently に広がっていた。生成セットを control の形へ戻すと arm が
control の記録値（1.956875）を完全再現する。つまり AM8 の −6 は「正しく機構を教えた」ことによる
変化ではなく、近似プールの要素追加による rollout の分岐。

### 生成プールはキャラクター自身のプールだけ（commit `77120b2`）

`Stoke.cs` / `InfernalBlade.cs`（decompile）は `Owner.Character.CardPool.GetUnlockedCards(...)` から
生成する。Ironclad の pool（`IroncladCardPool.cs`、87枚）に Panache は無い — Panache は
`ColorlessCardPool`。したがって Ironclad run で Stoke が Panache を生成することは無い。
One-Two Punch は Ironclad pool に在るので生成しうる（この方の追加は忠実）。

model は知っている札しか生成できないので、忠実な近似は「model が knows ∧ character pool」の集合。
`CARDS_OUTSIDE_THE_CHARACTER_POOL` として固定し、`STOKE_GENERATION` と `INFERNAL_BLADE_ATTACKS`
から除いた（32名）。回帰テスト `test_generated_cards_come_only_from_the_characters_own_pool`。
実走の照合：panel の Stoke 使用 6件で生成された札はすべて `CARD_POOL.IRONCLAD_CARD_POOL` — 一致。

生成プールの限定の決定レベル到達性（arm 記録の replay）：AM8 **11件 / 1 seed**、9X9・NFH3・EAIF・73P で 0。
1 seed の増減は採用根拠にしない rule のまま、正しさ（デコンパイル）で commit した。勝率への効果は未測定。

### 一致の件数（再走5 seed の内訳）

5 seed は AutoSlay watchdog timeout で終了（exit=1、`result.json` なし）→ 判定はトレースの `won`。
decision列を件数で照合した：

| seed | arm rows | control rows | decision diff | wins arm/control |
|---|---:|---:|---:|---|
| 9X9WQB4QIH | 265 | 265 | 0 | 14 / 14 |
| NFH3RMVJ6D | 275 | 275 | 0 | 15 / 15 |
| EAIF2UUVCK | 276 | 276 | 0 | 14 / 14 |
| 73P61QQZNU | 243 | 243 | 0 | 13 / 13 |
| AM8C6YXHSG | 216 | 351 | **52** | 11 / 17 |
| VTW80ZJA2G | 269 | 269 | 0 | 13 / 13 |
| GEFYYKH1YK | 164 | 164 | 0 | 7 / 7 |
| SWRUL944UU | 120 | 120 | 0 | 6 / 6 |

7 seed は decision列が control と完全一致。同じ決定列なら outcome も同じ（game の RNG は seed 由来）
なので、この7件は watchdog の有無に関係なく「測定不能」が確定。AM8 の分歧は seq 244（SWORD_BOOMERANG）
からで、件数差は arm が早く負けたぶん。

`CardFactory.FilterForCombat` は `CanBeGeneratedInCombat && Rarity != Basic/Ancient/Event` を
通すので、model が Basic（Strike/Defend/Bash）を生成集合から除いているのは忠実。忠実な集合は
「model が knows ∧ character pool ∧ non-Basic」で、commit `77120b2` の形がそれ。
実走の生成 record（hand に現れた札）で Basic が一度も出ていないのも一致。

## 機構単独の到達性（2026-10-03、sample）と mechanism panel

固定8 seed panel は機構がほぼ発火しない（12,841件の内、panel 分の発火は 9X9 の DuplicationPower 1回
だけ）ので、この panel では機構の実走効果を測れない。corpus 512 trace の集計：

- 機構 id を含む combat record（`legal_actions` 付き）：**12,841件 / 139 seed**
- decision_source：rollout_success 8,070 / **heuristic_fallback 2,655** / lethal系 672 / direct_potion 266
- 機構の札そのものを打った record：13件（One-Two Punch 10、Panache 3）

同一 observation を両commitで replay した（`STOKE_GENERATION` を control の形へ固定して生成プールの
副作用を隔離、1-in-12 sample）：**照合620件で分歧116件 / 15 seed**。内訳（多い順）
`N8CQ4ZKP2W` 57、`H2LV6ZJ4XW` 24、`AM8C6YXHSG` 15、`R8V2H6N4ZB` 4、`D1W9Y3B7FC` 3、
`P3V8N5K2RX` 2、`B3N8V5T1WQ` 2、`Q6N3V8K2MT` 2、ほか1件ずつ。→ 閾値（≥3 decisions かつ ≥3 seeds）超。

実走：mechanism panel 8 seed（上の順）で control `e808bdf` → arm HEAD（`77120b2` 以降）の順で
16 run を直列実行。生 data は `data/mechpanel_ctrl_*` と `data/mechpanel_arm_*`（git除外）。

### 訂正：curses は実装済み

「残っている未モデル」に並んでいた DOUBT・REGRET・SHAME は main で実装済み（`test_curses_left_in_hand_hit_the_player_at_turn_end` が pin）。
decompile 上、`Regret.OnTurnEndInHand` は hand size ぶんの **Unblockable** Unpowered damage（`Beckon`/`Bad Luck` と
同じ hook だが block で absorb される側・されない側が違う）、`Doubt` は Weak 1、`Shame` は Frail 1
（`SkipNextDurationTick` で次の tick を飛ばす＝player の次のターンに効く）。
`Debt` は `PlayerCmd.LoseGold(min(10, gold))` だけで戦闘効果が無い → model 外（gold 経済を扱わない）なので実装不要。

sample の分歧116件を機構別に分解（record に複数の機構が同時に在る場合はあるので件数は機構別、合計は116超になりうる）：

| 機構 | flip | seed数 |
|---|---:|---:|
| `RELIC.FIDDLE`（hand draw 以外を拒否＋hand draw +2） | **76** | 4 |
| `POWER.CHAINS_OF_BINDING_POWER`（rollout 内のドローを Bound） | **34** | 5 |
| `RELIC.FORGOTTEN_SOUL`（exhaust 1枚につき random 1体へ1） | 24 | 1 |
| `RELIC.BLOOD_SOAKED_ROSE`（毎ターン energy +1） | 8 | 4 |
| `POWER.DUPLICATION_POWER` / `CARD.ONE_TWO_PUNCH` | 2 / 2 | 2 / 2 |
| `CARD.PANACHE` | 1 | 1 |

Fiddle と Chains が分歧の主成分（rollout 内のドロー挙動を変える機構）。Gigantification は sample に
分歧なし（0件）。到達性の内訳が機構ごとに偏っているので、panel 実走は「機構まとめて1本」ではなく
この内訳が実際に勝敗へ伝わるかを見る測定として扱う。

### Fiddle と Chains の照合（panel 実走中に現物で確認）

- `Fiddle.ShouldDraw`：`fromHandDraw` は許可、owner 以外許可、**owner の side 中は拒否**。`ModifyHandDrawLate` は owner の hand draw +2。model の `if not from_hand_draw and RELIC_FIDDLE in player_relics: return` はこれと一致
- `ChainsOfBindingPower.AfterCardDrawn`：「このターンにこの actor が Bound にした枚数」が Amount 未満のとき Afflict。model は hand 内の bound 枚数で同じ上限を掛けている。Bound 札は play できないのでターン内で hand から消えず、ターン end で flush されて bound が落ちる → ターン単位の count として等価
- `Debt` は gold のみ（戦闘効果なし）

sample の分歧主成分（Fiddle 76・Chains 34）は機構の正しさではなく「rollout が将来引く札をどう数えるか」の差。
実走で測れるのは、その差が胜敗へ伝播する seed があるか。panel の control 腕で `N8CQ4ZKP2W` は 5勝1敗
（Act 1 F14 elite で死亡）＝この seed では機構の有無以前に commit 差が勝敗を決めている例。

### run レベルの A/B は「両腕で同じ機構が出た」ときにのみ機構を測れる

機構の出現は path 依存：Fiddle・Blood-Soaked Rose・Forgotten Soul は relic 報酬（自動取得）で、
どの報酬・休憩・戦闘が来るかは policy の分岐で変わる。だから同一 seed でも arm 側で発火して
control 側で発火しないことがある。その seed は A/B として**attribution 不能**（機構の実装差ではなく
game が違った offer を出した）。同じ observation を両commitで replay した到達性計算だけが
「機構単独の差」を隔離できる（上の sample：620件で116分歧）。

mechanism panel の control 腕（`e808bdf`）でこれまでの発火は 0：`N8CQ4ZKP2W` 5W1L・fired none、
`H2LV6ZJ4XW` 12W0L・fired none。`data/compare_panel.py` は tag/seed を引数で受け取る形にした
（commit `bbf0abd`）。panel の判定は per-seed だけでなく **fired を両腕で確認してから**使う。

参考：同じ seed の古い record では FIDDLE が数千行に出る（N8 の `candidate` run 3,419行、
H2 の `candidate` run で FORGOTTEN_SOUL 3,249行）＝取得している run では恒久的に観測へ出る。
control 腕の run が取得していない＝route/reward が違う。

### Forgotten Soul の実走証拠（decompile だけでなく record で確認）

`data/candidate_headbutt_D6A1F8C3E5_agent.jsonl` の seq 379・380：`CARD.TREMBLE`（damage 0 の
exhaust 札）を打った turn で、confound しうるレリック（Charon's Ashes・Nunchaku・Pendulum）は
未所持、enemy の `hp+block` が **ちょうど1** 減っている。`ForgottenSoul.AfterCardExhausted` の
「exhaust 1枚につき random 1 hittable 体へ 1 unpowered」そのもの。全体へ出す Charon's Ashes とは
違う、という実装の主張が record 側でも立った。

同じ条件の record は corpus でこれ以外の0件（drop 0 の反例も無し）＝サンプルは小さいが、
機構の方向性は正しい。Fiddle・Chains・Duplication・Gigantification・Panache・One-Two Punch は
現物照合（hook 名と条件）で固定済み。

### 固定 panel で「両腕が同じ機構を見た」 pair は2件だけ

panel 8 seed を両腕で洗うと、機構が **両腕の record に出る** seed は：

| seed | 機構 | decision diff |
|---|---|---:|
| `9X9WQB4QIH` | `POWER.DUPLICATION_POWER`（両腕） | 0 |
| `73P61QQZNU` | `CARD.ONE_TWO_PUNCH`（両腕） | 0 |

`AM8C6YXHSG` は control 側だけ FIDDLE・FORGOTTEN_SOUL・CHAINS・OneTwoPunch を持っていて、**arm 側の run は一つも見ていない**（機構を引く/route が違った）。だから AM8 の分歧は機構の実装差ではなく、確認済みの生成プール（`STOKE_GENERATION`）の差だけが効いた。EAIF・NFH3・VTW・GEFYY・SWRUL は両腕で発火ゼロ。

→ 固定 panel で機構単独を測れた pair は 2件、reach 0。機構の実走効果は mechanism panel（control 腕完走後に arm 腕）を待つ。

### 同一 commit・同一 seed の再走は decision列が完全一致（再現性の確認）

mechanism panel の control 腕で `AM8C6YXHSG` を `e808bdf` に再走した。先行した `ctrl20261004_AM8C6YXHSG`
（351件）と比較し、**再走分の決定列（seq・card_id・decision_source）が全件一致**（2026-10-03 09:40 時点で
351/351、再走は走行継続中）。条件は同一：固定ユーザーデータ、`simulations=100`、Act 3まで、単一 game instance。

これで「同じ決定列なら outcome も同じ（game の RNG は seed 由来）」が harness 側でも確認できた。
panel の ±0 が本当に「決定が変わっていない」かどうかの判定は、この再現性の上で使える。
（決定列が一致しない場合の原因は policy 差か path 差かの切り分けが要る、という既存の rule はそのまま。）

`AM8C6YXHSG` の control 再走は **outcome まで一致**した：決定列351件完全一致、勝敗も 17勝1敗で
先行 run（`ctrl20261004_AM8C6YXHSG`）と同値（job `bash-116` の RESULT）。同一 commit・同一 seed・同一
固定ユーザーデータの run は決定列も outcome も再現される。panel の ±0 判定はこの再現性の上で使える。

### Blood-Soaked Rose は model で二重計上していた（commit `a328b5c`）

`BloodSoakedRose.ModifyMaxEnergy` は毎ターの energy reset で +1。bridge の `max_energy` は**観測された
ターンの有効値**なので、relic を持っている run は turn 1 から 4 を報告する（実測：`gdv_9X9WQB4QIH` の
turn 1 record が max_energy 4）。model は turn start で `extra_energy += 1` を足していたので、rollout の
turn 2 が **5** になった（same record で再現：model turn2 energy 5）。二重計上。

実測の分布：relic 所持 record の `max_energy` は 4（767件）と 5（255件）。5 の record は Paels Flesh
（turn 3 以降 +1、永続）との併有で、game は両方の加算を already 反映した値を報告している：
`act3_pop2_head_R8V2H6N4ZB` turn 3 = base3 + Flesh1 + Rose1 = 5。

→ 機構として model に載せるものがない（observation に既にある）。branch を除去し、
`test_blood_soaked_rose_is_not_double_counted_at_energy_reset`（state の max_energy 4 → turn 2 energy 4）で固定。
Paels Flesh の branch は残る：turn 2 の観測は 3 を報告するので、model が turn 3 へ跨ぐときに +1 するのは正しい。

mechanism panel の sample で Rose に紐づいていた分歧8件は、この除去で消える（機構単独の到達性は
Fiddle 76・Chains 34・Forgotten Soul 24・OneTwoPunch 2・Panache 1 へ）。arm 腕の run はこの commit を
含むので、panel の結果を読むときは Rose 分を机构差として数えない。

修正後の同じ record（`gdv_9X9WQB4QIH` の turn 1、relic 所持、max_energy 4）での END_TURN rollout：
model の turn 2 energy は **4**（修正前は5）。game が報告する有効値と一致する形になった。
実走 panel（control 腕）では `R8V2H6N4ZB` が BLOOD_SOAKED_ROSE を所持して発火しているが、
修正後の model にとってこの relic は decision に効かない（観測に既にある） → R8 で動くのは他の機構だけ。

### 修正後の到達性：panel 8 seed のうち2件は測定不能になる

Rose の二重計上 branch を除いた sample 再計算：分歧 **108件 / 11 seed**（116 → 108）。機構別は
Fiddle 76・Chains 34・Forgotten Soul 24・OneTwoPunch 2・Duplication 2・Panache 1。

seed 別（post-fix）：`N8CQ4ZKP2W` 57、`H2LV6ZJ4XW` 24、`AM8C6YXHSG` 15、`D1W9Y3B7FC` 3、
`P3V8N5K2RX` 2、`Q6N3V8K2MT` 2、ほか5 seed各1。

→ mechanism panel の8 seedのうち **`B3N8V5T1WQ` と `R8V2H6N4ZB` は post-fix で到達性 0**
（あの2 seed の分歧は除去した bug branch 由来）。この2 seed の ±0 は判定へ使えない。
使えるのは N8・H2・AM8・D1・P3・Q6 の6 seed（AM8は生成プールの忠実化と混かる）。
R8 の control run（22勝1敗）はすでに完了済みなので記録として残す。

### 二重計上の点検（panel 実走中に機構別で確認）

Rose だけが二重計上だった。ほかは観測と二重計上にならない構造：

- `Fiddle`：`ShouldDraw` は hand draw（`fromHandDraw=True`）を許可、owner の side 中のそれ以外を拒否。
  model は未来ターンのドローだけを変え、hand の枚数（＝game が既に引いた結果）には触らない
- `ChainsOfBinding`：live hand の bound は bridge が `bound` field で正しく出す。model は rollout 内の
  future draw にのみ Afflict を再現
- `Duplication` / `OneTwoPunch` / `Gigantification` / `Panache`：観測 powers の counter を、 hypothetical
  play（rollout）へ適用する形。decision 時点の effect は観測に既にあるので加算は未来分だけ
- `Forgotten Soul`：exhaust の解決は rollout 内で再現（観測の exhaust pile は過去分）。実走証拠は
  `test_curses_left_in_hand_hit_the_player_at_turn_end` ではなく record 側（TREMBLE play で enemy ちょうど1減）

→ 実走 panel の arm 腕は `a328b5c` 以後の code。arm 腕で Rose 分が効かないのはこのため。

### play-count powers の model は multi-effect 札で部分忠実（記録）

`DuplicationPower` / `OneTwoPunchPower`（OneTwoPunch は `CardType.Attack` 限定）は
`ModifyCardPlayCount +1`、`AfterModifyingCardPlayCount` で decrement、player turn end で remove。
＝その play の**解決全体**がもう1回走る。model は damage と block を2回適用する形で再現しているので、

- 単效果札（Strike・Defend・Shrug 等）：忠実
- 多效果札（Burning Pact の exhaust＋damage、draw を伴う Skill、power 適用）：game は exhaust・draw・
  power 適用まで2回走らせる。model は damage/block 分だけ2回 → **部分忠実**

panel の sample で Duplication の分歧は2件（1-in-12 sample、`POWER.DUPLICATION_POWER` を持つ record 上）。
多效果札で duplication が消費された case を洗ってから、埋める価値があるかを判断する（現時点で reach 2、
noise 未満 → 実走対象にしない）。

件数：play-count power が active で Shrug It Off（block + draw の multi-effect）が選ばれた record は
**4件 / 2 seed**（`N8CQ4ZKP2W` seq 126・135・141、`Z2K7D9F4VX` seq 462）→ 閾値（≥3 decisions かつ
≥3 seeds）未満。機構の形（play 全体をもう1回走らせる）は正しいが、この panel では測れない。
実装を変えない（「multi-effect の第二解決が model に無い」として記録だけ）。

mechanism panel の両腕は bridge（C#）が同一：`git diff --name-only e808bdf..HEAD` に `.cs` は 0件。
panel の差は Python 側（policy/模型）だけなので、run 間の差を「DLL が違う」で説明できない。
control 腕 = `e808bdf` worktree、arm 腕 = HEAD（`77120b2` と `a328b5c` を含む）。

### Fiddle のドロー拒否は実走側でも確認できた（1,436件）

Fiddle を持つ run で、draw 系札（Pommel・Shrug・Evil Eye・Battle Trance・Production・Master of Strategy 等）
を打った decision と**同じ turn の次の decision** を照合：hand が伸びた case は **0件**、伸びない case
**1,436件**。＝ game は owner の effect ドローを拒否している（`ShouldDraw` の `fromHandDraw` 以外の拒否）
ので、model の拒否は推測ではなく実走一致。hand draw（turn start）の +2 も同レリックの
`ModifyHandDrawLate` で、view 側の hand には出ないので rollout 加算として扱うのが正しい。

Fiddle は panel の sample で分歧76件（11 seed 中の最大）＝機構単独で最もreachのある筋。
run レベルで測れるのは両腕が Fiddle を持った seed だけ（control 腕では AM8 が所持）。

### Bound は play を阻止しない（commit `5d8bf18`）

`ChainsOfBindingPower.ShouldPlay`：Bound 札を阻止するのは**そのターンに Bound 札を1枚打った後**だけ
（`BeforeCardPlayed` がフラグを立て、`BeforeSideTurnEnd` でフラグと affliction を両方 clear）。
＝第一 choice のゲート前、game は Bound 札を playable として出す。

実測：corpus で**Bound 札を打った decision 279件**（3 seed）、うち **45ターンで1ターンに2枚以上**
打っている。 blanket「Bound は打てない」は忠実でなかった。

model の形の修正：

- `Card.bound` = affliction マーカー（それ自体は play を阻止しない）
- `Combat.bound_played_this_turn` = ShouldPlay のターン内ゲート
- `Card.unplayable_this_turn` = game の legal_actions がその decision で除外したという判定（first move
  では game の list が権威。Snecko の一時的な高コスト等もここに入る）。これを `bound` と同一字段に
  していたのが、忠実でない方向へねじれていた
- `legal_actions`：`unplayable_this_turn` は常に skip、`bound` はゲートが立ってから skip

テスト `test_chains_of_binding_afflicts_cards_drawn_during_the_rollout` をゲート rule へ更新
（play 前は5枚とも legal、bound を1枚打つと残りの bound 2枚は skip、unbound は playable のまま）。
suite **733件成功**。mechanism panel の arm 腕はこの commit を通るので、Chains の sample 到達性34件は
この rule の下で数え直す（gate 前は playable、gate 後だけ skip）。

###  contaminated: arm 腕の4 run は無効（working tree に未commitの実験コードが入っていた）

mechanism panel の arm 腕で `N8CQ4ZKP2W` 0勝1敗、`H2LV6ZJ4XW` 0勝1敗、`AM8C6YXHSG` 1勝1敗、
`R8V2H6N4ZB` 0勝1敗。原因は機構ではなく**agent の exception**：`rollout_choice` に途中入れた
「game の legal_actions に無い action を skip する」guard を、テストが壊れたので revert した但し
revert 前に start した run がそのコードで走っていた（agent は run の開始時に file を読む）。
error log: `IndexError: list index out of range`（N8 9件、H2 9件、AM8 16件、R8 9件）。
agent が fall out すると game は 2分の wait deadline 後に safe default（多くは skip）を取る＝勝てない。

rule：run が走っている間に policy code を編集してはいけない。`sweep2.sh` が print する commit は
start 時の HEAD で、実際に使われた file 内容ではない。この4 seedは `5d8bf18` の code で再走が必要。
`D1W9Y3B7FC`（clean code で start）は正常に decision を出しており有効（sources: rollout_success ほか）。

汚染の判定は decision_source で立つ：contaminated run（`mechpanel_arm_N8CQ4ZKP2W`）は
`agent_exception_fallback` が9件、clean run（`mechpanel_arm_D1W9Y3B7FC`）は rollout_success 97件・
heuristic_fallback 33件で exception は0。つまり汚染 run では agent が fall out して game 側が default
（skip）を取っている。再走後は `*_agent.err` が空であること＋`agent_exception_fallback` が0件であることを
確認してから結果を使う。

### run safety：もう一つの失敗（同時に run を started した）

再走 script を書いたとき、実行中の sweep があることを確認せずに呼んだ。`run_official_autoslay.ps1` は
「Slay the Spire 2 is already running」で throw するので**測定は行われなかった**（4 seed全部 exit=1、
stdout は exception だけ）。ただし sweep の `trap` がユーザーデータを snapshot へ復元したので、走行中の
run の環境へ割り込んだ。artifact は削除済み。

`/Users/mao/.sts2/scripts/rerun_mechpanel.sh` の guard（両方実失敗から）：

- game process が在る then refuse（同時に run を start しない）
- `official_agent.py` / `combat.py` が HEAD と違则 refuse（汚染）

再走は4 seed：`N8CQ4ZKP2W` `H2LV6ZJ4XW` `AM8C6YXHSG` `R8V2H6N4ZB`（tag `mechpanel_arm_rerun`）。
条件は panel と同一（固定ユーザーデータ、`simulations=100`、Act 3まで、1 run/seed）。

### Chains の到達性は blanket rule 由来。忠実なゲートでは再計算が必要（上限45ターン）

sample の Chains 分歧34件は「Bound 札を打てない」という**忠実でない rule**の下で数えた。
修正後（`5d8bf18`）の忠実な形では、ゲートが効くのは「そのターンに Bound 札を1枚打った後、
まだ Bound 札が hand に残っている」case だけ。実測の上限は：

- Bound 札を打った decision 279件 / 3 seed（`N8CQ4ZKP2W` 182、`H2LV6ZJ4XW` 79、`D6A1F8C3E5` 18）
- そのうち **1ターンに2枚以上 Bound を打った turn = 45ターン**（ゲートが実際に効く位置）

→ 忠実なゲートの到達性は45ターンを上限として replay で数え直す（control にはゲートが無いので、
ゲート単独の差）。Fiddle（76件）は rule が忠実と確認済みなのでそのまま。panel 実走で測れるのは、
両腕が同じ機構を見た seed だけ、という条件もそのまま。

### D1：決定は61件違うが outcome は同じ（14勝1敗）

mechanism panel の `D1W9Y3B7FC`：control 14勝1敗、arm（clean code、例外0件）14勝1敗。
decision列は arm 294件 / control 306件で **61件分歧**（first divergence seq 82）。この seed は
**両腕の run とも機構を見ていない**（control 側 fired none、arm 側も none）ので、分歧は機構の実装差
では説明できない。機構が1つも state に入っていない run で arm/control が違いうる通路は
`STOKE_GENERATION` の形（忠実化で32名を除いた）だけ。

→ decision の分歧は outcome へ伝わらないことがある、の実例。panel の判定は per-seed の増減ではなく
母集団の合計、かつ「両腕で同じ機構を見た」seed だけを使う、という rule がそのまま生きる。
D1 の ±0 は「効果なし」ではなく、機構について言えば**測定不能**（分歧の成因が機構と無関係）。

### P3 の分歧は機構ではなくマーカー漏れだった（commit `f8f3966`）

`P3V8N5K2RX` は control 15勝1敗 / arm 13勝1敗で、両腕の run が `POWER.DUPLICATION_POWER` を見た
最初の pair。だが第一分歧（seq 186）の record を両treeで replay すると、机构は state に出ていない
（powers は DexterityPower だけ、hand に Stoke も無い）。違いは `Card.unplayable_this_turn` が
ターン跨ぎで**消えない**ことだった：decision 時点で game の legal_actions が除外した札（energy 0 で
打てなかった Strike / Pommel Strike）が、rollout の後続ターンでもPlayable扱いされず、
`legal_actions` が arm と control で違った。

修正（`f8f3966`）：hand を flush する場合、`bound`（Chains のゲートはターン終了で clear される）と
`unplayable_this_turn`（game のそのターンの判定）を双方クリア。RetainHandPower で hand に残る copy
も同じ。テスト `test_the_per_turn_unplayable_marker_does_not_leak_into_the_next_turn`。

修正後の同じ record：両treeの search が一致（0.7658 `card:3@0` / 0.4666 `card:2` / 0.1209 End turn）
→ P3 の −2 は機構の差ではなくこの bug の差。

**panel の arm 腕は `5d8bf18` を通った run（D1・P3・B3・Q6）も bug 込み**なので、機構単独の測定には
8 seed 全部を `f8f3966` の code で再走する（tag `mechpanel_arm_clean`）。control 腕（`e808bdf`、機構を
教える前の code）はそのまま基準として使える。

### leak の実測：B3 の第一分歧も机构と無関係（post-fix で両tree一致）

`mechpanel_arm_B3N8V5T1WQ` の第一分歧 seq 136：hand に BASH（energy 1 で game は除外）、powers は
Strength・Crimson Mantle、relics に機構なし。record を両treeで replay（`f8f3966`）すると両treeが
`CARD.DEFEND_IRONCLAD` で一致 → run 側で arm が STRIKE を選んだのは漏れたマーカー（BASH が翌ターンでも
打てない扱い）の効果。D1（seq 82）と P3（seq 186）も同じ形で確認済み。

→ これまでの arm 腕（D1・P3・B3・Q6）の decision 分歧は、機構が state に出た場合を除いて漏れの効果。
机构単独の到達性は Fiddle（76、rule 忠実と実走1,436件で確認）と Chains のゲート（上限45ターン）が本体で、
leak は artifact。panel の arm 腕は `f8f3966` の code で8 seed 再走して、`agent_exception_fallback` 0件と
両腕の発火の揃いを確認してから判定する。

### arm 腕の run ごとの code 状態（どれが使えるか）

| seed | arm run | 使用 code | 扱えるか |
|---|---|---|---|
| `N8CQ4ZKP2W` | 0勝1敗・例外9 | 未commitの guard | 無効 |
| `H2LV6ZJ4XW` | 0勝1敗・例外9 | 未commitの guard | 無効 |
| `AM8C6YXHSG` | 1勝1敗・例外16 | 未commitの guard | 無効 |
| `R8V2H6N4ZB` | 0勝1敗・例外9 | 未commitの guard | 無効 |
| `D1W9Y3B7FC` | 14勝1敗・例外0 | `5d8bf18`（漏れ込み） | 機構測定の根拠にできない |
| `P3V8N5K2RX` | 13勝1敗・例外0 | `5d8bf18`（漏れ込み） | 同上 |
| `B3N8V5T1WQ` | 19勝1敗・例外0 | `5d8bf18`（漏れ込み） | 同上 |
| `Q6N3V8K2MT` | 走行中 | `f8f3966`（clean） | run 自体は使えるが、この seed は control 側で発火0 |

再走は7 seed（`mechpanel_arm_clean`）。Q6 は clean code で start した最初の run。
control 腕（`e808bdf`）の8 seed 結果（合計121勝）はそのまま基準。

### Chains の忠実なゲートは3 seed にmaterialに効く（651 record）

game の legal_actions が Bound 札を除外していた record（＝ゲートが立っていた）：**651件 / 3 seed**
（`N8CQ4ZKP2W` 399、`H2LV6ZJ4XW` 224、`D6A1F8C3E5` 28）。同じ条件で Bound 札が legal_actions に
**入っていた** record は622件（ゲート前、両treeが playable 扱い → 差が出ない）。

sample の Chains 分歧34件は blanket rule（常時 skip）の下で数えたので、忠実なゲート下的の分歧件数は
この651件の上で数え直す。panel の arm 腕 re-run（`f8f3966`）が走っている間は CPU を game に譲る（25 ms
ポーリングのdelay → watchdog risk）ので、replay は sweep 完了後。

### control era の bound-hand decision では469件が heuristic_fallback に落ちている

control（`d429b4d` 以前、bound の概念が無い）で、hand に Bound 札が在る decision 1,273件の内訳：
heuristic_fallback **469**、rollout_success 467、queen_minion_direct 233、ほか。heuristic_fallback に
落ちたのは、model が game の legal_actions に無い札（Bound）を top に並べて mapping が fail したため。
忠実な形（ゲート前は playable、ゲート後は skip）では、この469件で model が game-legal の中から
rank する → 第一手が変わりうる。母数は上の651件（gate-active）の上で replay して数える。

seed 別（heuristic_fallback）：`N8CQ4ZKP2W` 336、`H2LV6ZJ4XW` 117、`D6A1F8C3E5` 16。

### panel の第一読取（arm 腕は再走中）と忠実なゲートの分歧率

panel 8 seed（control `e808bdf` vs arm）：

| seed | control | arm（使用 code） | 扱えるか |
|---|---:|---|---|
| `N8CQ4ZKP2W` | 5 | 0（例外9） | 再走 |
| `H2LV6ZJ4XW` | 20 | 0（例外9） | 再走 |
| `AM8C6YXHSG` | 17 | 1（例外16） | 再走 |
| `R8V2H6N4ZB` | 22 | 0（例外9） | 再走 |
| `D1W9Y3B7FC` | 14 | 14（漏れ込み） | 再走 |
| `P3V8N5K2RX` | 15 | 13（漏れ込み） | 再走 |
| `B3N8V5T1WQ` | 16 | 19（漏れ込み） | 再走 |
| `Q6N3V8K2MT` | 12 | **12（clean code）** | 有効。ただし両腕で発火0 → 機構については測定不能 |

忠実なゲート（Bound playable、第一 play 後 skip）の分歧率を gate-active record の30件/seed sample で測った：
**88件で第一手分歧15件（約17%）、control 側の mapping fail 0件**。651件へ外挿すると約110件の決定分歧、
3 seed に分布 → 閾値（≥3 decisions かつ ≥3 seeds）超。re-run（tag `mechpanel_arm_clean`、job `bash-296`）
が走っている間、gate の分歧件数を full で数える。

### clean re-run の照合方法（N8 で実装）

clean run（`mechpanel_arm_clean_N8CQ4ZKP2W`）は control（`e808bdf`）の同じ seed run と、
seqで揃った record 120件まで決定列が一致。この区間で gate-active record は **0件**（Chains がまだ
active ではない）→ 分歧が出ないのは预期どおり。

照合の手顺（panel の arm 腕全体に使う）：
1. `agent_exception_fallback` が0件であること（汚染の確認）
2. 第一分歧の record で、机构が state に出ているか（powers/relics/hand）を見る
3. 机构が出ていない record で分歧するなら、それは机构の差ではない（漏れや生成集合など別通路）
4. 両腕で同じ机构が揃った seed だけ per-seed 勝数へ使う

### 訂正：N8 の「発火1件」は combat ではなく card_reward の提示だった

`mechpanel_ctrl_N8CQ4ZKP2W` で机构 id が出た1件は seq 84 の **card_reward 行**（offer list に
`CARD.ONE_TWO_PUNCH` が載っていた）で、combat decision の state に机构が出ていた件数は0。
`compare_panel` は発火を combat record の状態出現だけで数えるようにした（commit `9bbd4c5`）。

clean run（`mechpanel_arm_clean_N8CQ4ZKP2W`）は control と決定列 **111/111件一致**、outcome も
5勝1敗で同値。つまり N8 はこの run で机构を見ず、機構については測定不能。N8 の到達性57件は
同じ seed の**別の run**（`candidate` ほか）から来ていた。

→ panel の測定力は path 運で決まる。母数として使えるのは、両腕の run が機構を**combat の state に
出した** seed だけ（現時点で control 側は H2 と AM8 が出した。arm 側が同じものを見るかは run 次第）。

### H2 の clean run は pair にならない（relic を引かなかった）

`mechpanel_arm_clean_H2LV6ZJ4XW`：combat record 179件、relics は Burning Blood・Stone Humidifier で
`RELIC.FORGOTTEN_SOUL` は 0件。control（`e808bdf`）の同じ seed run は67件で所持 → **path が分かれて
机构を引かなかった**。H2 の到達性24件は control 側が机构を持つ run（`candidate` ほか）から来ていた。

決定列は seq で揃った213件の分歧0。機構の実装（exhaust 1枚につき random 1体へ1 unpowered）は
1点 damage で、この path では決定を1つも動かしていない。機構の effect が決定へ伝播する母数として、
Fiddle（76件）と Chains のゲート（651件で17%）は実測済み。control era で bound-hand decision の
469件が heuristic_fallback に落ちていた件（model が game に無い札を top に並べた）は、忠実な形の
arm では game-legal の中から rank する → こちらが機構単独の差として残る。

### sample分歧の seed × 機構 分解と、panel で実際に pair になりうるもの

sample（1-in-12、機構単独）の分歧108件を seed × 機構で割ると：

| seed | 機構 | flip |
|---|---|---:|
| `N8CQ4ZKP2W` | Fiddle 56・Chains 20・Duplication 1 | 77 |
| `H2LV6ZJ4XW` | Forgotten Soul 24・Chains 11 | 35 |
| `AM8C6YXHSG` | Fiddle 15 | 15 |
| `D1W9Y3B7FC` | Fiddle 3 | 3 |
| `Q6N3V8K2MT` | Fiddle 2 | 2 |
| `P3V8N5K2RX` | Chains 1・Duplication 1 | 2 |

panel の実走で pair になる条件是、**両腕の同じ run が同じ機構を combat の state に出す**こと。
control 腕（`e808bdf`）で state に出した seedは H2（Forgotten Soul）、AM8（Four）、R8（Chains+Rose）、
P3（Duplication）で、N8 と D1・Q6・B3 は0（N8 の1件は reward 提示）。
したがって N8 の77件、D1 の3件、Q6 の2件は panel の run では使えない。pair になりうるのは H2・AM8・
R8・P3 の4 seed ＋ arm 側が Fiddle 等を引いた case。

### 訂正：H2 は pair（両腕の run が Forgotten Soul を state に出している）

前ラウンドで「H2 は机构を引かなかった」と書いたが誤り。clean run
（`mechpanel_arm_clean_H2LV6ZJ4XW`）は combat record **123件**で `RELIC.FORGOTTEN_SOUL` を所持、
control（`e808bdf`）は67件。前ラウンドの scan は file 選択を誤って0と出した。

第一分歧 seq 441：relics・powers（Dexterity・Strength）・hand が両腕で同一。arm が end_turn、
control が UPPERCUT。arm 側には機構の実装（exhaust 1枚につき random 1 hittable 体へ1 unpowered）があり
control には無い → ここは机构単独の差として立つ。分歧は seq 441 から51件（H2 clean run 走行中、
16勝0敗；control は 20勝1敗）。

H2 は panel で最初の実質的な pair。1 seed の増減は採用根拠にしない rule のまま（判定は母集団）。

### H2：最初の実測 pair（+2、Forgotten Soul）

`compare_panel`（発火は combat record の状態出現だけ）で H2 を照合：

- control 20勝1敗 / arm（clean）22勝1敗 → **+2**
- pair：`RELIC.FORGOTTEN_SOUL` が両腕の combat state に出ている（arm 123 record、control 67 record）
- arm 側だけに `POWER.CHAINS_OF_BINDING_POWER`（25 record）が出ている → H2 の分歧は Chains 由来とは
  言えない。机构単独で attribution できるのは Forgotten Soul だけ
- 第一分歧 seq 441（relics・powers・hand が両腕同一）→ 机构の実装差で立つ
- Act 3踏破は両腕なし

1 seed の +2 は採用根拠にしない rule（測定の作法 5）どおり、記録として残す。母集団（panel）の
pair が揃う seed が増えてから判定する。現在 pair：H2 の1件。

### H2 の分歧46件は全部、両腕の state に Forgotten Soul が在る位置

combat decision の分歧46件を、その decision の state（relics・powers・hand）で機構の出現を確認して
割った：**46件すべて両腕に `RELIC.FORGOTTEN_SOUL` が在る**。arm 側にだけ Chains が在る位置での分歧は
**0件** → H2 の path で Chains のゲートは決定を動かしていない。

したがって H2 の +2（control 20勝1敗 → arm 22勝1敗）は Forgotten Soul の実装単独の差として attribution
できる。母集団は1 seedなので採用根拠にはしない（rule 5）が、機構単独の差として立つ第一 pair。

### AM8 の分歧は机构ではない（generation pool の差）

clean AM8 run の第一分歧 seq 248：relics・powers が両腕で完全一致、机构は state に出ていない
（arm 12勝0敗・走行中、FIDDLE は arm 側にのみ出現）。seq 250 で `CARD.STOKE` を打つ位置なので、
分歧の成因は `STOKE_GENERATION` の形（control は忠実でない集合、arm は character pool ∩ known）＝
前もって確認済みの生成プールの差。FIDDLE が両腕に出た位置での分歧は現在0件。

→ AM8 は「机构単独の差」として読めない。panel の母集団で机构単独が読めるのは、両腕の同じ decision の
state に同じ机构が出ている位置だけ（H2 の Forgotten Soul 46件がその形）。

### AM8 の分歧68件を state で割った（Fiddle 19件・机构なし33件）

clean AM8 run（14勝0敗・走行中、control 17勝1敗）：seq で揃えた combat decision 246件の分歧68件。

- **19件**：`RELIC.FIDDLE` が両腕の state に出ている位置 → Fiddle の実装単独の差として attribution できる
- **33件**：両腕の state に机构が何も出ていない位置 → 生成プール（`STOKE_GENERATION` の忠実化）の差
- 残りは机构が片腕だけに出た位置（attribution 不能）

H2 と同じ形で、機構単独の差として残るのは Fiddle 19件。run レベルの outcome（AM8 は機構＋忠実化が
混かる）は Fiddle 単独の成果へは開けない。母集団で机构単独が読める位置は、両腕の同じ decision の
state に同じ机构が出た位置だけ、という rule がまた確認された。

### Fiddle の +2 draw：実走で検証できるのは turn 1 の first decision だけ

clean AM8 run の「combat ごとの最初の decision」7件を見ると、turn 1 の1件（combat 1）は hand **7**
＝ 5 + Fiddle 2 で一致。ほか6件は turn 2・7・8・9・11 の decision（その combat の turn 1 の decision が
トレースに無い）なので +2 を検証できない。**inconclusive**で、+2 の根拠は hook
（`Fiddle.ModifyHandDrawLate` が owner の hand draw に +2）のまま。拒否側（effect draw 不许）は
実走1,436件で hand が伸びないことを確認済み。

→ 実走検証できるのは、观測に現れる量（hand size、energy、powers、relics）と hook の対応が
1対1で決まる case だけ。rollout 内部の加算は record から直接検証できない。

### AM8（17勝0敗・走行中、control 17勝1敗）の分歧138件

両腕の同じ decision の state に同じ机构が出た位置で割ると：

- `RELIC.FIDDLE` 両腕：**89件**
- `RELIC.FORGOTTEN_SOUL` 両腕：30件
- `POWER.CHAINS_OF_BINDING_POWER` 両腕：16件
- 両腕に机构が何も出ていない位置：**49件**（→ 生成プールの忠実化の差。机构の差ではない）

（1 decision に複数の机构が両腕で揃っている場合があるので件数は機構別、合計は138超になりうる）

AM8 は Fiddle が決定を動かす位置が最多の seed。run レベルの outcome（17勝0敗 vs control 17勝1敗）は
机构と忠実化が混かるので、Fiddle 単独の成果へは開けない。開けるのは、同一 observation を両treeで
replay して「機構単独」を隔離した件数（Fiddle 76件、Chains の忠実なゲート651件で17%）だけ。

### clean run の現在の判定（測れる2 seedで +2）

| seed | control | arm（clean、例外0件） | delta | pair（両腕の combat state） |
|---|---:|---:|---:|---|
| `N8CQ4ZKP2W` | 5W1L | 5W1L | 0 | none（決定列111件完全一致） |
| `H2LV6ZJ4XW` | 20W1L | 22W1L | **+2** | Forgotten Soul |
| `AM8C6YXHSG` | 17W1L | 17W1L | 0 | Fiddle・Forgotten Soul・Chains（決定分歧138件でも outcome 同値） |

**MEASURABLE（両腕で同じ機構）= 2 seed：control 37勝 / arm 39勝、+2。**
AM8 は決定を138件動かして勝敗が変わっていない → decision の分歧は outcome へ伝わらないことがある
実例（D1 の61件と同じ形）。rule 5（1 seedの当たりで採用しない）の下では +2 はまだ採用根拠にならない。
残4 seed：R8・D1・P3・B3。

### AM8 seq 248 の分歧は生成集合で再現できる（机构ではない）

AM8 の「両腕の state に机构が出ていない」第一分歧 seq 248 を同一 observation で replay：

- control 形の `STOKE_GENERATION`（忠実でない、112名）→ `CARD.BURNING_PACT` ＝ control の run の選択
- faithful（character pool ∩ known、80名）→ `CARD.SHRUG_IT_OFF` ＝ arm の run の選択

→ この分歧は生成集合の忠実化で立つ。机构の実装では説明できない。AM8 の49件（機構なし位置）は
この形。Fiddle 89件・Forgotten Soul 30件・Chains 16件は両腕の state に同じ機構が出ている位置なので
機構単独の差として残る。

### 訂正：run レベルで机构単独の差として立うるのは第一分歧の位置だけ

AM8 で Fiddle が両腕の state に出ている分歧位置（89件）を1件（seq 328）replay して確認した：
同一 observation（arm 側の record）を両treeに流すと、arm tree は `CARD.HEADBUTT`（run の arm の選択と
一致）、control tree は `CARD.ANGER` を選び、**control の run が実際に選んだ `CARD.INFLAME` とは違う**。
control 側の record は state が違う（seq 248 で pool の差から path が分岐した以降）ので、この89件は
「机构単独の差」ではない。分歧位置の机构 presence は、同じ decision の state が両腕で一致している
case 限りで意味を持つ。

panel で机构単独として立つのは第一分歧の位置だけ：

- `H2` seq 441：relics・powers・hand が両腕同一、`RELIC.FORGOTTEN_SOUL` が両腕の state に在る →
  **Forgotten Soul の実装単独**（+2 の成因）。arm が end_turn、control が Uppercut
- `AM8` seq 248：relics・powers・hand が両腕同一、机构は state に出ていない → **生成プールの忠実化**
  （control 形の集合で control の選択、faithful で arm の選択を再現）

→ AM8 の +0 は「机构の効果が出なかった」ではなく、机构が効く位置が第一分歧より後（state が違う）なので
机构単独の差として開けない。機構単独を隔離できるのは同一 observation を両treeで replay する到達性
計算だけ（Fiddle 76件、Chains の忠実なゲート651件で17%）。

### R8 の arm run は机构を1つも state に出していない → R8 の差は机构単独として読めない

clean R8（13勝0敗・走行中、control 22勝1敗）：combat record に機構が0件。control 側は Chains 17 record・
Rose 154 record。arm 側が机构を seen していないので、分歧は机构の実装差では説明できず、残る通路は
生成プールの忠実化（`STOKE_GENERATION`）だけ。

panel で「第一分歧の位置に机构が両腕の state に出ている」seed は現時点 **H2 だけ**（seq 441、
Forgotten Soul）。AM8 の第一分歧 seq 248、R8 の分歧位置は机构なし → 機構単独の差として開けない。
机构単独の差は同一 observation を両treeで replay する到達性計算でしか隔離できない（Fiddle 76件、
Chains の忠実なゲート651件で17%、Forgotten Soul 24件、OneTwoPunch 2件、Duplication 2件、Panache 1件）。

### R8：arm は机构を引かなかったから、決定列が control と301件一致

`mechpanel_arm_clean_R8V2H6N4ZB`（15勝0敗・走行中）は、seq で揃えた combat decision 301件の分歧が
**0件**。arm 側は机构を state に出していない（control 側は Chains 17・Rose 154 record）が、control の
model（`e808bdf`、机构を実装する前）は那些を無視するので、両腕が「机构を持たない run」として同じ
決定を出す。機構を引かなかった path では机构の効果は出ない — 引くかどうかは reward の path 運。

この seed は机构単独の差を持たない。分歧が出るとすれば arm 側が机构を acquisition した後の位置で、
その場合も第一分歧の位置（state が両腕で一致する位置）だけ attribution に使える。

### R8 で二重計上修正の帰結が実走で出た：Rose を両腕が持っても決定列が完全一致

`mechpanel_arm_clean_R8V2H6N4ZB`（21勝0敗・走行中）は、seq で揃えた combat decision の分歧が
**0件**（412 record、2026-10-03 11:30 時点）。両腕の record に `RELIC.BLOOD_SOAKED_ROSE` が出ている
（control 154・arm 156 record）ので pair だが、修正後（`a328b5c`）model は Rose に何もしない（game が
報告する `max_energy` に既に反映済み）→ 機構単独の差は0。arm が control と同じ決定を出している。

これが「機構として model に載せるものがない（observation に既にある）」の実走形。pair でも effect が
無い case の記録。

### R8 の error log から実 bug を1件修正（commit `HEAD`：SoarPower + hit count 0）

`mechpanel_arm_clean_R8V2H6N4ZB_agent.err`：`ZeroDivisionError` in `damage()` →
`value = (value // hits // 2) * hits` が hits == 0 で割る。hits は `_card_hit_count` で、Whirlwind は
「使った energy」が hit count所以 energy 0 だと 0 になる（`CARD_HIT_COUNTS` に 0 の entry は無いので、
0になりうるのは Whirlwind の path だけ）。`HardToKill` 側は `if caps and hits` で guard 済みで、Soar 側
だけ guard が无かった。

R8 はこの decision（seq 546）で game 側の default を取ったが、決定列は control と **454件分歧0**、
outcome も 22勝1敗で同値 → 実走影響は出なかった。guard を入れてテスト
`test_lethal_with_soar_power_does_not_divide_by_a_zero_hit_count`（suite **735件成功**）で固定。

### P3：pair だが決定列の分歧0（Duplication の effect が出なかった path）

`mechpanel_arm_clean_P3V8N5K2RX`：393 aligned recordsで**全 decision field の分歧0**。両腕の combat
state に `POWER.DUPLICATION_POWER` が出ている（control 16・arm record）ので pair。分歧が0なので
機構単独の差は0。

sweep が print した wins=13 は print 時点で trace が未完だった值で、final の parse は 15勝1敗（control
と同じ）。**判定は final の trace（`phase == 'combat_end'` の `won`）で行う**、sweep の grep 行ではない。

D1 も同じ形：aligned 306件分歧0、14勝1敗で同値（機構を引かなかった path）。
現在 panel で機構単独の差として立っているのは H2（Forgotten Soul、第一分歧 seq 441、+2）だけ。

### panel（clean run）の consolidated 判定

| seed | control | arm（clean） | delta | aligned combat decision | 分歧 | 第一分歧の機構（両腕 state） |
|---|---:|---:|---:|---:|---:|---|
| `N8CQ4ZKP2W` | 5W1L | 5W1L | 0 | 111 | 0 | — |
| `H2LV6ZJ4XW` | 20W1L | **22W1L** | **+2** | 390 | **46** | `RELIC.FORGOTTEN_SOUL`（seq 441） |
| `AM8C6YXHSG` | 17W1L | 17W1L | 0 | 323 | 138 | none（→ 生成プール） |
| `R8V2H6N4ZB` | 22W1L | 22W1L | 0 | 454 | 0 | Rose（effect 0） |
| `D1W9Y3B7FC` | 14W1L | 14W1L | 0 | 306 | 0 | — |
| `P3V8N5K2RX` | 15W1L | 15W1L | 0 | 305 | 0 | Duplication（effect 0） |
| `B3N8V5T1WQ` | 16W1L | 走行中（8勝0敗、分歧0） | — | 171 | 0 | — |
| `Q6N3V8K2MT` | 12W1L | 12W1L（first pass、clean code） | 0 | — | 0 | — |

**機構単独の win-rate 効果は、clean run の母集団で H2 の +2（1 seed、46分歧）だけが立った。**
rule 5（1 seedの当たりで採用しない）と閾値（≥3 decisions かつ ≥3 seeds）の立場では、機構は
**正しさの修正として採用済み**（decompile 根拠＋Fiddle のドロー拒否は実走1,436件、Chains のゲートは
実測279 plays/45 turns、play-count powers は decompile 一致）で、win-rate の効果は母集団が薄いまま。
AM8 の138分歧は生成プールの忠実化（同一 observation で control 形／faithful を切り替えて再現）で、
機構の差ではない。

### MEASURABLE（両腕で同じ機構が combat state に出た seed）は4 seed、+2

`compare_panel`（発火は combat record の状態出現のみ）での最終形（B3 は走行中）：

| seed | control | arm | delta | pair | first divergence |
|---|---:|---:|---:|---|---|
| `N8CQ4ZKP2W` | 5 | 5 | 0 | none | — |
| `H2LV6ZJ4XW` | 20 | **22** | **+2** | Forgotten Soul | seq 441（両腕 state 一致） |
| `AM8C6YXHSG` | 17 | 17 | 0 | Fiddle・FS・Chains | seq 248（機構なし＝生成プール） |
| `R8V2H6N4ZB` | 22 | 22 | 0 | Chains・Rose |分歧0 |
| `D1W9Y3B7FC` | 14 | 14 | 0 | none |分歧0 |
| `P3V8N5K2RX` | 15 | 15 | 0 | Duplication | 分歧0 |
| `B3N8V5T1WQ` | 16 | 12（走行中） | — | arm 側が機構を seen せず | 分歧0 |
| `Q6N3V8K2MT` | 12 | （first pass 12） | 0 | none | 分歧0 |

**MEASURABLE = 4 seed：control 74 / arm 76、+2。** 閾値（≥3 decisions かつ ≥3 seeds）は decisions 側は
超える（H2 の46件）が seeds 側が1 → win-rate の採用根拠にはならない。機構は正しさの修正として採用済み
のまま、成果の母集団は薄い。

### B3 でも Rose の effect 0が実走で出た（404件分歧0）

`mechpanel_arm_clean_B3N8V5T1WQ`（15勝0敗・走行中）：両腕の combat state に `RELIC.BLOOD_SOAKED_ROSE`
が出ている（control 125・arm record）ので B3 は pair になり、aligned combat decision **404件で分歧0**。
二重計上を除去した（`a328b5c`）後の model は Rose に何もしないので、分歧が出ないのは预期どおり。
R8（454件分歧0）と同じ形。

panel の MEASURABLE は H2・AM8・R8・P3（＋B3 の Rose）で、机构単独として決定を動かしたのは H2 の
Forgotten Soul 46件だけ。run レベルで机构単独として立つのは第一分歧の位置（state が両腕で一致）の
限り、という rule が B3 でも確認された。

### H2 の第一分歧は机构単独で立つ（生成プールが決定に関与できない）

seq 441（両腕の state が一致、Forgotten Soul が両腕に出ている）の record を確認：hand は
Uppercut・Iron Wave・Strike・Bloodleting、**draw/discard/exhaust に Stoke も Infernal Blade も無い**。
＝生成集合（`STOKE_GENERATION` の忠実化）はその decision の rollout に関与できない。なので分歧は
`ForgottenSoul.AfterCardExhausted`（exhaust 1枚につき random 1 hittable 体へ1 unpowered）の実装差だけが
成因。arm が end_turn、control が Uppercut を選んだ。

panel（clean run）の完走読取：control 121勝 vs arm 123勝（+2、H2 単独）。分歧を持つ pair は H2 だけで、
R8・B3・P3・N8・D1・Q6 は分歧0、AM8 の第一分歧は生成プール。

## panel（clean run）の完走読取

| seed | control（`e808bdf`） | arm（clean） | delta | aligned | 分歧 | 第一分歧 |
|---|---:|---:|---:|---:|---:|---|
| `N8CQ4ZKP2W` | 5 | 5 | 0 | 111 | 0 | — |
| `H2LV6ZJ4XW` | 20 | **22** | **+2** | 390 | 46 | seq 441（Forgotten Soul、単独で立つ） |
| `AM8C6YXHSG` | 17 | 17 | 0 | 323 | 138 | seq 248（生成プール） |
| `R8V2H6N4ZB` | 22 | 22 | 0 | 454 | 0 | — |
| `D1W9Y3B7FC` | 14 | 14 | 0 | 306 | 0 | — |
| `P3V8N5K2RX` | 15 | 15 | 0 | 305 | 0 | — |
| `B3N8V5T1WQ` | 16 | 16 | 0 | 446 | 0 | — |
| `Q6N3V8K2MT` | 12 | 12 | 0 | — | 0 | — |

**機構単独の win-rate 効果：1 seed（H2）で +2。閾値の seeds 側が未達 → 採用根拠にはならない。**
機構は正しさの修正として採用済みのまま。例外は R8 の1件（SoarPower の ZeroDivision、`2aef215` で修正）
で、その run の分歧0・胜敗同値に影響は出なかった。

### mechanisms-only batch の expected reading

`data/mechonly_agent.py`（arm の code、生成集合は control 形）で4 seed を走らせる（job `bash-424`）。
設計の意図：

- 生成集合の差を消す → path が control と揃う → 分歧は機構の実装差だけ
- したがって第一分歧の record は、機構が**両腕の state に出ている**位置になる（机构を引くまでの区間は
  分歧0预期）。H2 は133件 aligned 分歧0、機構未発火 → 预期どおり
- 机构を引かない seed は分歧0のまま（B3・D1・Q6・N8 は引かなかった）。引く seedは control の run で
  機構を state に出した4 seed（H2・AM8・R8・P3）＋ Fiddle の seed

照合は `data/compare_panel.py`（tag `mechonly` vs `mechpanel_ctrl`）。判定は per-seed 勝数と、第一分歧が
機構の位置であること。閾値は ≥3 decisions かつ ≥3 seeds。

### H2 の harness run：機構が出る位置が予備できる（control は seq 423 で出現）

control H2（`e808bdf`）で `RELIC.FORGOTTEN_SOUL` が初めて出る record は **seq 423**（combat、
`CARD.IMPERVIOUS` を play する decision）。生成集合を control 形へピン留めした harness run は、
機構が state に出るまでの区間が control と一致する预期（現在 aligned 165件分歧0）。
机构が出た後の第一分歧が機構単独の差になる — これが harness の目的。H2 では panel の第一回 runで
分歧46件（第一分歧 seq 441）が出ていて、harness run はその再現になるかを見る。

### H2 の harness run が机构単独の差を再現した（22勝地点、分歧46件、第一分歧 seq 441）

生成集合を control 形へピン留めした `mechonly` run（job `bash-424`）で H2：

- aligned 390件で分歧 **46件**、第一分歧 **seq 441**（arm harness: end_turn / control: Uppercut）
- その位置の state に `RELIC.FORGOTTEN_SOUL` が**両腕**で在る（Stoke も Infernal Blade も piles に無い）
- wins 22・losses 0（走行中）＝ panel の clean arm run（22勝1敗）と同じ地点

生成集合の差を消した下で同じ分歧・同じ outcome が出る → H2 の +2 は機構単独（`ForgottenSoul.AfterCardExhausted`）
で立つ。ただし seeds 側は1件のままなので閾値（≥3 seeds）には未達。harness の残3 seed（AM8・R8・P3）を
待つ。

### H2 harness 完走：panel と同じ outcome を機構単独の条件で再現（22勝1敗）

`mechonly_H2LV6ZJ4XW` 完走：**22勝1敗**（control 20勝1敗、+2）、aligned 390件分歧46件、第一分歧 seq 441、
分歧位置の机构は `RELIC.FORGOTTEN_SOUL` が両腕。生成集合を control 形へピン留めた下で、panel の clean
arm run（22勝1敗・分歧46件）と**同じ outcome・同じ分歧**が出た → H2 の +2 は機構単独で立つ、と
run レベルで確認。

harness の残：AM8（1勝0敗・走行中、分歧0、機構未出現）、R8・P3。AM8 は生成集合の差が消えるので、
機構が両腕の path に出る位置から分歧する预期（panel では第一分歧が生成プールだった）。

### harness の動作確認：H2 では pool の差が一度も効かなかった

`mechonly_H2LV6ZJ4XW` と `mechpanel_arm_clean_H2LV6ZJ4XW`（faithful 集合で走った arm）を照合：
aligned 447件で**分歧0**。H2 は Stoke を打つ位置が無かった（少なくとも分歧に効く位置）ので、pin しても
しなくても同じ決定列になる。＝ H2 の分歧46件は最初から機構単独で立っていた（上の state 確認と一致）。

harness の価値は pool が効く seed 側にある。AM8 は panel で第一分歧が生成プール（seq 248）だったので、
pin した harness run は control と揃った path を歩き、機構が両腕の state に出た位置から分歧する预期。
現在 AM8 harness：5勝0敗、aligned 62件分歧0、機構未出現。

### harness が live run で効いていることの確認

`ps` の command line：`-AgentScript ./data/mechonly_agent.py`（seed AM8C6YXHSG、`-AgentSimulations 100`、
`-StopAfterAct 3`）。harness は repo の code を import して `STOKE_GENERATION`（110名）と
`INFERNAL_BLADE_ATTACKS`（51名）を control 形へ上書きするだけなので、live の決定列が control と
揃うはずで、実際に AM8 は138件分歧0（机构未出現、pool の分歧点 seq 248 未通過）。

harness の判定条件：`python3 data/compare_panel.py mechonly mechpanel_ctrl . .wt-ctrl-e808bdf <seed>`。
分歧が机构の位置（両腕の state に同じ机构）で出た case だけが机构単独の差。

### harness の live 確認：AM8 は pool の分歧点（seq 248）を分歧0で通過した

panel の faithful 集合で走った arm run は AM8 の seq 248 で control と分歧していた（成因は生成集合、
replay で control 形の集合なら control の選択、faithful なら arm の選択を再現）。pin した harness run は
**seq 248 を分歧0で通過**（10勝0敗、aligned 168件、機構未出現）→ live でも pin が効いており、その分歧が
生成集合の差だったことが run レベルでも確認できた。

Fiddle は control 側で seq 322 の event で獲得。harness run は control と揃った path を歩いているので
同じ点で獲得する预期。獲得後の第一分歧が機構単独の差になる。

### 预測（1 record replay）：Fiddle を引いた直後の decision は分歧しない

control AM8 の Fiddle grant（seq 322）の直後の combat decision seq 325 を、arm code（pin 済み）と
control tree で replay：両方 `CARD.PERFECTED_STRIKE`（control の run の実際の選択と同じ）。
＝機構を引いたことが即ち分歧にはならない。分歧は rollout が机构を理由に別の ranking を出す位置で出る
（sample で Fiddle の分歧76件 / 108件の中身）。live の harness run（現在 seq 318、分歧0）がその位置に
入るかを見る。

### AM8 harness：Fiddle 単独の第一分歧が出た（seq 331、state は両腕で完全一致）

`mechonly_AM8C6YXHSG`（14勝0敗・走行中、例外0件）：aligned 262件で分歧 **21件**、その分歧位置の機構は
すべて `RELIC.FIDDLE` が**両腕の state** に出ている。第一分歧 seq 331：

- state は両腕で完全一致（違うのは choice 字段だけ）
- harness（arm code、生成集合は control 形）→ `CARD.STRIKE_IRONCLAD`、control → `CARD.ANGER`
- Fiddle は seq 322 の event で両腕が同じ点で獲得している

＝生成集合の差を消した条件で、分歧は Fiddle の実装（hand draw +2 と effect draw の拒否）だけで立つ。
H2（Forgotten Soul）に続く2件目の机构単独 pair。outcome はまだ決まっていない（harness 14勝0敗、
control は同じ path から17勝1敗）。

これで panel の机构単独 pair は2 seed（H2・AM8）。閾値（≥3 seeds）には harness の R8・P3（＋Fiddle を
引く seed）を待つ。

### AM8 harness：分歧80件の内訳（pin した下で「機構が両腕の state に出た位置」以外に分歧が無い）

`mechonly_AM8C6YXHSG`（17勝0敗・走行中、例外0件、aligned 330件）：

- `RELIC.FIDDLE` 単独が両腕の state に出ている位置：**73件**
- Fiddle ＋ Chains が両腕に出ている位置：14件（単独へは split できない）
- 両腕の state に機構が何も出ていない位置：**0件**

生成集合を control 形へ pin した下で、分歧は全部機構の位置で出ている。＝ AM8 の panel 第一回 run の
分歧（138件）のうちの49件は生成集合の差だったが、pin した harness run ではその差が消えて、機構の位置
だけの分歧になった。Fiddle の単独 attribution が73件で、H2 の Forgotten Soul 46件に続く2件目。

（14件は Fiddle と Chains の両方がある位置なので、機構単独へは同一 observation の replay でしか割れない。）

### harness readings（AM8 完走）

| seed | control | harness | delta | 分歧（両腕の state） |
|---|---:|---:|---:|---|
| `H2LV6ZJ4XW` | 20W1L | **22W1L** | **+2** | 46件、すべて Forgotten Soul |
| `AM8C6YXHSG` | 17W1L | 17W1L | 0 | 80件（Fiddle 73、Fiddle+Chains 7）、勝敗は変わらない |
| `R8V2H6N4ZB` | 22W1L | 1勝0敗・走行中 | — | control 側は Chains を17 record で所持 |
| `P3V8N5K2RX` | 15W1L | 未走 | — | control 側は Duplication を1 record |

AM8 で Fiddle は73件決定を動かしたが outcome は同じ → decision の分歧が win-rate へ伝わらないcase。
机构単独の win-rate 効果は harness でも H2 の +2（1 seed）のまま。閾値 ≥3 seeds は R8・P3（機構が
両腕の path に出る case）を待つ。

### harness の pin が live で効いている決定的確認（AM8 seq 248）

同一 decision（seq 248）の3条件の選択：

- live harness run（pin した集合）→ `CARD.BURNING_PACT`
- control（`e808bdf`、機構なし）→ `CARD.BURNING_PACT`
- faithful 集合で走った arm run → `CARD.SHRUG_IT_OFF`

live の harness が control と同じ选择を返している＝pin が実走で効いている。したがって harness run の
分歧（AM8 87件、H2 46件）は机构の実装差だけで立つ。R8 ではまだ Stoke を打つ位置に来ていない（checked 0）
ので、R8 の pin 効果は機構出現後に分岐するかどうかで見る。

### Rose の effect 0：harness run でも同じ（R8、arm 130 record・分歧0）

`mechonly_R8V2H6N4ZB`：harness run が Rose を保持する combat record **130件**で、control との決定分歧
**0件**。二重計上を除去した model（`a328b5c`）は Rose に何も処理を持たないので、分歧が出ないのは构造上
当然で、実走3件（panel clean R8 454件、panel clean B3 446件、harness R8 130件）で一致した。

Chains のゲート（忠実な形）は R8 の control run で17 record 効いていた位置があるが、harness run は
まだその点（seq 567）に達していない。ゲート単独の分歧は651件の母数で17%（sample）→ R8 の path で
出るかは達してから見る。

### R8：Chains が両腕の state に出た17件で決定分歧0（post-fix 到達性0の実走形）

`mechonly_R8V2H6N4ZB` 完走：22勝1敗 = control と同値。Chains（忠実なゲート）が両腕の combat state に
17 record 出ていて、決定分歧は0。＝ R8 の path ではゲートが決定を動かさなかった。sample で R8 の分歧が
Rose の bug branch 由来（除去後0）だったことと実走で一致。

harness reading（完走分）：H2 46分歧（Forgotten Soul）で +2、AM8 87分歧（Fiddle 73・Chains 14）で outcome
同値、R8 分歧0・同値。P3 は未走。机构単独の win 効果は1 seed（H2）のまま → 閾値 ≥3 seeds 未達。

### gate の実走検証（record を1件ずつ model へ流して確認）

`candidate_bound_D6A1F8C3E5_agent.jsonl` seq 395（実走で gate が効いていた位置の record）を model に流した：

- play 前：bound 札3枚が hand に在り、`legal_actions` は bound を含む（gate 前＝忠実）
- bound 札を1枚 play した直後：`bound_played_this_turn` が True になり、残る bound 2枚は
  `legal_actions` から消える（play 可能な札は非-bound だけ）

＝ `ChainsOfBindingPower.ShouldPlay` の形（first bound play allowed、以降 gate）と model が一致。
harness batch は完走：P3 15勝1敗 = control（Duplication を両腕の state に出すも分歧0）。機構単独で win
効果が出たのは H2（+2）だけ。

### 第二 batch の seed は「control（`e808bdf`）の run が機構を state に出す」条件で選ぶ

機構を state に出た seed（corpus、commit をまたぐ集計）を**player state 出現**で並べ直した：

| seed | 機構（state 出現 record） |
|---|---|
| `H2LV6ZJ4XW` | FS 4346・Chains 984 |
| `AM8C6YXHSG` | Fiddle 1763・Chains 181・FS 177 |
| `R8V2H6N4ZB` | Rose 677・Chains 112 |
| `P3V8N5K2RX` | Chains 231・Duplication 16 |
| `H4L6P2N8XS` | Rose 119・Chains 17 |
| `M7C4Q9V2RH` | Chains 72・OneTwoPunch 2 |
| `V7D3M9H2XW` | Panache 12 |
| `T3XQ7WM2VP` | Gigantification 6・Duplication 2 |
| `M5W9C3T7LQ` | OneTwoPunch 6 |
| `U2M7K5F9RA` | OneTwoPunch 1・Duplication 1 |
| `C8Q1Z7E3KS` | OneTwoPunch 1 |

Fiddle は corpus で N8 4761・AM8 1763・Q6 136・D1 106 の4 seed にしか出ない。そのうち `e808bdf` の
control run が Fiddle を state に出した seed は AM8 だけ（N8・D1・Q6 のolder run は `e808bdf` より後の
commit で、event の選択が違った）。だから Fiddle の run レベル pair は AM8 が母数。

batch2 の設計：control は `e808bdf`、arm は pin した harness。pin した arm は control の path を機構が
効く位置まで追うので、control の run が機構を state に出せば pair が成立する（機構が効く位置から分歧）。
現在 U2M7K5F9RA の control を走行中。

### batch2 の第一 control run が機構を state に出した（`U2M7K5F9RA`、OneTwoPunchPower）

`mechonly_ctrl_b2_U2M7K5F9RA`：7勝0敗・走行中、例外0件、combat の state に
`POWER.ONE_TWO_PUNCH_POWER` が出ている。control（`e808bdf`）が機構を state に出すなら、pin した arm
run は同じ path を追うので pair が成立する（機構が効く位置から分歧する）。判定は `compare_panel` と
`mechonly_attribution`（tag `mechonly_arm_b2` vs `mechonly_ctrl_b2`）。

### batch2 の attribution は构造上clean（pin した arm は机构以外で分歧できない）

batch2 は control（`e808bdf`、机构未実装）と arm（HEAD＋生成集合 pin）を同じ seed・同じ条件で比べる。
arm 側に机构の実装以外に code の差が無い（生成集合は pin で無効化）ので、決定列が分歧する位置は
機構が arm の state に出ている位置に限られる。control の run が機構を state に出した seed では、path が
分歧するまで両腕が同じものを見る ＝ pair が成立する。

従って batch2 の分歧は、機構の実装差として attribution できる。母数：control が機構を state に出した
seed（現時点 `U2M7K5F9RA`：Duplication＋OneTwoPunch、10勝1敗／`T3XQ7WM2VP`：Duplication、7勝0敗・走行中）。

Duplication の run レベル effect は batch1 の P3 で0（1 record 両腕、分歧0）だった。OneTwoPunch の sample
reach は2件。＝ batch2 で分歧が出るかは薄いが、出れば機構単独の差として立つ。

### batch2 での prediction（sample の分歧が既にある2 seed）

1-in-12 sample（機構単独、生成集合は control 形）で batch2 の seed に分歧が残っている：

- `M5W9C3T7LQ` seq 89：arm `CARD.ONE_TWO_PUNCH` / control `CARD.DEFEND_IRONCLAD`（OneTwoPunch）
- `V7D3M9H2XW` seq 312：arm `CARD.SHRUG_IT_OFF` / control `CARD.STONE_ARMOR`（Panache）

ただし sample は blanket bound rule の下で数えたもの（後の忠実なゲートで数え直し済み、Chains の14件は
Fiddle と重複)。実走の batch2 run が同じ位置で分歧するかを見る。分歧すれば3 seed 目になり、閾値
（≥3 decisions かつ ≥3 seeds）へ接近する。

実走の control 側は現時点で `U2M7K5F9RA`（Duplication＋OneTwoPunch、10勝1敗）と `T3XQ7WM2VP`
（Duplication、9勝0敗・走行中）が機構を state に出している。

### play-count powers の忠実度は限定（block grant と damage hit の2通路だけ）

`play_duplicated` の使用箇所：`_grant_block`（line 1071）と damage path（line 2815）。＝dup された play の
「block grant を2回」「damage hit を2回」は model に入っているが、draw・status 付与・energy・self-damage
・multi-effect card の extra resolution は入っていない。したが batch2 の Duplication/OneTwoPunch の
実走效果は**model が捉えている分だけ**の差で、game の完全な效果は understimate する。

Gigantification（line 2137-2154）は play 中の mark された Attack command の damage を3倍（1回）なので、
play-count とは別の通路。こちらも damage通路限定。

→ batch2 で機構単独の分歧が出た case は「model の実装が効いた位置」であり、忠実度の限界は記録したまま
読む（over-claim しない）。

### batch2 の control run に1件 exception（control 側の Hellraiser recursion）

`mechonly_ctrl_b2_M7C4Q9V2RH_agent.err`：`_autoplay_top_of_draw` → `_step` → `_autoplay_top_of_draw` の
再帰で RecursionError。control（`e808bdf`）には HellraiserPower の auto-play に cap が無い；HEAD には
`hellraiser_autoplays_this_turn >= 9` の safety cap がある（後から入れた修正）。

→ batch2 の arm–control 差は「機構の実装」＋「この cap」の2要素になる。`M7C4Q9V2RH` の control run は
例外1件なので、この seed の第一分歧がその decision 位置にある case は机构単独の差として読めない。
rule 9（再走後は exception 0件を確認）の形で、run ごとに例外数を報告する：

| seed | control run | exceptions |
|---|---|---:|
| `U2M7K5F9RA` | 10勝1敗 | 0 |
| `T3XQ7WM2VP` | 12勝1敗 | 0 |
| `M7C4Q9V2RH` | 6勝0敗・走行中 | **1** |

### consumption の実走検証（同一 turn の連続 decision で確認）

実走 trace の「decision → 同一 turn の次の decision」で、power の消費を確認した：

- `POWER.DUPLICATION_POWER`：present → consumed **61件**（decrement/unchanged 0）＝ play 1回で消費、
  model の形と一致
- `POWER.GIGANTIFICATION_POWER`：consumed 13件、unchanged 7件。unchanged の内訳は played card の type
  が Status 4・Skill 2・Power 1 ＝ **Attack を打った時だけ消費**という model の条件（`card in ATTACKS`）と
  一致
- `POWER.ONE_TWO_PUNCH_POWER`：消費を観測できる transition がこの corpus に0件（母数が薄い）

実走で確認できるのは observable な量（powers・relics・hand）だけ。damage が2回 hit したかは trace に
出ない（`_step_score` の value には出るが、game 側の実際の hit 数ではない）。

### R8 の control run にも exception が1件あった（SoarPower の ZeroDivision、HEAD で修正済みの同じ bug）

`mechpanel_ctrl_R8V2H6N4ZB_agent.err`：`damage()` の SoarPower branch での ZeroDivisionError（`value // hits`
が hits 0）。＝ control 側にも同じ bug があり、その decision で game 側の default を取っている。R8 の
read（control 22勝1敗 / arm 22勝1敗、分歧0）はその1 decision 以外は決定列が一致しているが、rule 9 の
形で言えば R8 の control run は汚染 → clean にしたい場合は `e808bdf` で re-take。

batch2 の control では `M7C4Q9V2RH` に1件（Hellraiser recursion、control 側に cap が無い）が出ている。
exceptions を run ごとに報告するように `mechonly_attribution.py` を更新（commit `82cacce`）：

```
H2LV6ZJ4XW: aligned 390 diffs 46 by-mechanism {RELIC.FORGOTTEN_SOUL: 46} no-mechanism 0 exceptions arm 0 control 0
AM8C6YXHSG: aligned 338 diffs 87 by-mechanism {RELIC.FIDDLE: 87, POWER.CHAINS_OF_BINDING_POWER: 14} no-mechanism 0 exceptions arm 0 control 0
R8V2H6N4ZB: aligned 454 diffs 0 exceptions arm 0 control 1
P3V8N5K2RX: aligned 305 diffs 0 exceptions arm 0 control 0
```

### batch2 の照合 usage（arm は main checkout、control は worktree）

`mechonly_attribution.py` は arm 側を `data/<arm_tag>_<seed>_agent.jsonl`（main checkout）、control 側を
`<ctrl_dir>/data/<ctrl_tag>_<seed>_agent.jsonl`（worktree）で見る。batch2 の正しい usage：

```
python3 data/mechonly_attribution.py --arm-tag mechonly_arm_b2 --ctrl-tag mechonly_ctrl_b2 \
  U2M7K5F9RA T3XQ7WM2VP M7C4Q9V2RH C8Q1Z7E3KS M5W9C3T7LQ V7D3M9H2XW
```

batch2 control 進捗（2026-10-03 13:4x、例外数）：`U2M7K5F9RA` 10勝1敗（0、Dup＋OTP）、
`T3XQ7WM2VP` 12勝1敗（0、Dup＋Gigantification）、`M7C4Q9V2RH` 16勝0敗・走行中（**1**、Hellraiser
recursion、機構未出現）。

### cap の追加は batch の走行中に land した（rule 9 の形での内訳）

commit `f16b256`（`_autoplay_top_of_draw` の再帰 cap）は batch2 の control stage 走行中に committed
した。agent は run の start 時に file を読むので、run ごとに code が違う：

- `C8Q1Z7E3KS`（commit 時点で走行中）＝ pre-cap の code
- `M5W9C3T7LQ`・`V7D3M9H2XW`（commit 後に start）＝ cap 入りの code
- arm stage（commit 後）＝ cap 入り

cap は crash を止めるものなので、cap が実際に発火する位置（draw pile に Havoc が9枚以上並ぶ等）で
ないと決定は変えない。したがって batch の解读は保つが、片腕だけ cap が発火した case は机构単独の差
として読めない。run ごとの例外数と code version を報告する。

### 訂正：札名出現は table knowledge で、机构ではない

sample で OneTwoPunch 2件・Panache 1件と数えた分歧は、実際の record を見たら **powers が空**（札が hand
に在るだけ）だった。＝ arm は card table（cost/damage/type）を知っていて control は知らないという
**table knowledge の差**で、play-count power が active だった差ではない。

`mechonly_attribution.py` は機構を **power/relic の state 出現**だけで数えるようにした（commit
`ba67d63`）。例外は Wither など turn end に hand にあることで発動する status（hand presence が条件）。
batch1 の readings は relic 機構（Fiddle・Forgotten Soul）なので数字は変わらない。

→ 机构単独で立つ母数（power/relic出現）：H2 の Forgotten Soul 46件、AM8 の Fiddle 87件（Chains と14件
重複）、R8・P3 は分歧0。play-count powers（Duplication・OneTwoPunch・Gigantification・Panache）の run
レベルの差は、power が state に出た位置で出た分歧だけを数える。

### batch2 の control reading（power/relic の state 出現だけで判定）

| seed | control | exceptions | power/relic が state に出た | pair candidate |
|---|---:|---:|---|---|
| `U2M7K5F9RA` | 10勝1敗 | 0 | Duplication・OneTwoPunch | Yes |
| `T3XQ7WM2VP` | 12勝1敗 | 0 | Duplication・Gigantification | Yes |
| `M7C4Q9V2RH` | 17勝1敗 | **1** | Chains | Yes（control 汚染） |
| `C8Q1Z7E3KS` | 13勝1敗 | 0 | none | No |
| `M5W9C3T7LQ` | 16勝1敗 | 0 | none | No |
| `V7D3M9H2XW` | 5勝0敗・走行中 | 0 | none | No |

pair candidate は3 seed。pin した arm run は control の path を追うので、機構が state に出た位置から
分歧する预期。母集団の判定は、第一分歧が power/relic の位置であり、かつ両 run 例外0件の case だけ使う。
Act 踏破は control 6 seed 全部未踏破（各 run 1敗）なので、成果の判定は per-seed 勝数と分歧数。

### harness が消すのは生成集合の差だけ（card table の knowledge 差は残る）

`mechonly_agent.py` は `STOKE_GENERATION` と `INFERNAL_BLADE_ATTACKS` を control 形へ上書きするだけ。
arm 側の `CARD_COST`/`CARD_DAMAGE`/`SKILLS`/`POWERS` の entry（Panache・OneTwoPunch・Wither など）は
control に無いので、**table knowledge の差は harness でも残る**。だから attribution は power/relic が
state に出た位置だけで機構の差を数える（`mechonly_attribution.py` の今の形）。

実測でその形が出た例：sample の `M5W9C3T7LQ` seq 89（hand に OneTwoPunch、powers 空）と
`V7D3M9H2XW` seq 312（hand に Panache、powers 空）は、札名 knowledge の差。batch2 の control run は
この seed たちで機構を state に出していない（`M5` 16勝1敗・`V7` 9勝0敗・走行中、power/relic 出現0）ので、
arm run が分歧する位置は knowledge 差の位置になり、机构単独の差ではない。

### batch2 arm 1件目の分歧は knowledge-only（機構が state に出る前）

`mechonly_arm_b2_U2M7K5F9RA`（67 aligned、分歧6件）：その6件は**両腕の state に power/relic が出ていない
位置**＝ table knowledge の差（arm は OneTwoPunch などの card entry を持つ、control は持たない）。
control は `POWER.DUPLICATION_POWER` を seq 189 で得るので、arm がその点に達して同じ位置で見た場合の
分歧だけが機構単独の差として数えられる。`mechonly_attribution.py` の by-mechanism は空、no-mechanism 6件。

→ pin は生成集合の差を消すが、knowledge 差は消さない。機構単独の差は power/relic が両腕の state に
出た位置だけ、という rule がそのまま効いている。

### run レベルの判定基準（batch2 で確定）：第一分歧が機構単独である seed だけ使える

batch2 の arm run（`U2M7K5F9RA`、100 aligned、分歧34件）は機構が state に出る**前**の位置で分歧した
（no-mechanism 34件）。分歧した時点で path が分かれるので、その後の位置は機構単独の差として使えない
（機構の acquisition 位置自体が食い違い始める）。

→ run レベルで機構単独の差として立るのは、**第一分歧が power/relic の位置である case** だけ。
その形で立っているのは H2（seq 441、両腕の state に Forgotten Soul、分歧46件、+2）。
AM8 は第一分歧が生成プール（pin した harness run ではその分歧が消える → 分歧0、机构位置から分歧する
预期だったが、AM8 の harness run は第一分歧が Fiddle 位置＝機構単独で立った。harness の AM8 read：
aligned 338、分歧87、by-mechanism Fiddle 87、no-mechanism 0）
- 注：harness の AM8 は no-mechanism 分歧0 → 第一分歧が機構の位置。だから AM8 は機構単独で立つ
  （Fiddle 87件）、ただし outcome は同値（17勝1敗）。

batch2 の `U2M7K5F9RA` は第一分歧が knowledge-only（34件）→ その seed は機構単独の測定に使えない。
control が機構を state に出した seed のうち、arm 側が第一分歧から機構位置で分歧する case だけが母数。

### `U2M7K5F9RA` の機構 acquisition が腕でずれた（control 189 / arm 195）

arm run は `POWER.DUPLICATION_POWER` を seq 195 で得ている。control は seq 189。差の6 record 分は
knowledge-driven の分歧で path が分かれた後なので、同じ seq の record は別の game state を指す
（＝`present()` が両腕で同じ机构を出す位置 even if counted, it is not the same decision）。

→ `U2M7K5F9RA` は run レベルで機構単独の測定に使えない。母数になるのは第一分歧が机构位置である seed
だけ（H2、AM8 の harness）。

### `T3XQ7WM2VP` は clean pair（両腕が同じ seq 119 で Duplication を得ている）

control と arm（pin harness）の両腕が `POWER.DUPLICATION_POWER` を **seq 119** で得て、それまでの
aligned 76件は分歧0。power は card table の knowledge 差に関係しない（table にあるのは card 名だけ）
ので、119 以降の分歧は機構単独の差として立つ。H2（seq 441）と AM8（harness、seq 331）に続く3件目の
clean pair。

母数：`U2M7K5F9RA` は knowledge 差で先に分歧して acquisition までずれた（189/195）ので除外。
`C8Q1Z7E3KS`・`M5W9C3T7LQ`・`V7D3M9H2XW` は arm が機構を state に出すかどうかで決まる（control 側は
V7 で Panache を11 record 出している）。

### run レベルの判定（第一分歧が機構位置である seed）

`data/mechonly_attribution.py` に first-mech（両腕の state に機構が出た第一位置）と
first-diff-mech（第一分歧の位置の機構）を出すようにした（commit `b922915`）。現在の形：

| seed | aligned | diffs | first-mech | first-diff-mech | exceptions |
|---|---:|---:|---|---|---|
| `H2LV6ZJ4XW` | 390 | **46** | (423, FS) | **FS** | 0/0 |
| `AM8C6YXHSG`（harness） | 338 | **87** | (325, Fiddle) | **Fiddle** | 0/0 |
| `R8V2H6N4ZB`（harness） | 454 | 0 | (396, Rose) | none | arm 0 / control 1 |
| `P3V8N5K2RX`（harness） | 305 | 0 | (166, Duplication) | none | 0/0 |
| `U2M7K5F9RA`（batch2） | 129 | 62 | none（knowledge-only） | none | 0/0 |
| `T3XQ7WM2VP`（batch2） | 157 | 0 | (119, Duplication) | none | 0/0 |

機構単独の差として立っているのは H2（46分歧、**+2**）と AM8（87分歧、**outcome 同値**）の2 seed。
閾値（≥3 decisions かつ ≥3 seeds）の seeds 側は未達 → win-rate の效果は未証明。機構は正しさの修正として
採用済みのまま。

### T3XQ7WM2VP：clean pair だが机构位置で分歧0、outcome 同値（12勝1敗）

両腕が `POWER.DUPLICATION_POWER` を seq 119、`POWER.GIGANTIFICATION_POWER` を seq 207 で同じ位置に見て
いて（aligned 201件、分歧0）、arm 完走 12勝1敗 = control と同値。この path では机构が決定を動かさ
なかった。

run レベルで机构単独の差として分歧を出した seed は H2（Forgotten Soul、46件、+2）と AM8（Fiddle、87件、
outcome 同値）の2件のまま。閾値（≥3 decisions かつ ≥3 seeds）の seeds 側未達。

### `M7C4Q9V2RH` は機構位置（468）より前に control 側が分歧している（exception seq 138）

control M7 の exception は seq 138、機構（`POWER.CHAINS_OF_BINDING_POWER`）の第一位置は seq 468。
exception の decision で game 側の default を取ったので、138 以降 path が分かれる → 機構位置での分歧が
出ても机构単独の差として attribution できない。この seed は run レベルの母数から除外。

run レベルで机构単独として立っている seed：H2（46分歧、+2）と AM8（87分歧、outcome 同値）。
knowledge-only で除外：`U2M7K5F9RA`。分歧0：`T3XQ7WM2VP`・`R8V2H6N4ZB`・`P3V8N5K2RX`。除外（机构位置
より前に path 分歧）：`M7C4Q9V2RH`。

### `M7C4Q9V2RH` の分歧は knowledge-driven（seq 120、機構は state に出ていない）

arm が `CARD.STRIKE_IRONCLAD`、control が `CARD.TREMBLE` を選んだ seq 120 は、両腕の state に power/relic
が出ていない位置（＝card table の classification 差）。しかも control 側に exception（seq 138）が后続に
ある。pin した arm は生成集合で control と同じなので、この分歧は机构の実装差ではない。
→ `M7C4Q9V2RH` は机构単独の測定に使えない（knowledge と exception の二重の confound）。

### run レベルの結論（2026-10-03 15:0x 時点、batch2 の arm stage 走行中）

機構単独の差として run レベルで立っている seed は2件：

- `H2LV6ZJ4XW`：第一分歧 seq 441 が Forgotten Soul（両腕の state）。分歧46件、**control 20勝1敗 → arm 22勝1敗（+2）**
- `AM8C6YXHSG`（pin harness）：第一分歧 seq 331 が Fiddle（両腕）。分歧87件（Fiddle 単独73、Fiddle+Chains 14、no-mechanism 0）で **outcome 同値**（17勝1敗）

除外・分歧0：`U2M7K5F9RA`（第一分歧が knowledge-only、62分歧、outcome 同値）、`M7C4Q9V2RH`（knowledge 39
分歧＋ control exception、機構が arm 側に出ていない）、`T3XQ7WM2VP`（clean pair だが分歧0、同値）、
`R8V2H6N4ZB`（分歧0、control exception 1件）、`P3V8N5K2RX`（clean pair・分歧0、同値）、
`C8Q1Z7E3KS`・`M5W9C3T7LQ`・`V7D3M9H2XW`・`N8`・`D1`・`Q6`・`B3`（arm 側が機構を state に出さない）。

**結論：機構8件は正しさの修正として採用済み。win-rate の效果は、母集団（clean pair で第一分歧が機構
位置の seed）で H2 の +2 だけが立った。閾値（≥3 decisions かつ ≥3 seeds）には未達なので、效果ありと
は言わない。** decision レベルの母数（同一 observation を両treeで replay、生成集合を control 形へ固定）
は Fiddle 76・Chains の忠実なゲート651件で17%・Forgotten Soul 24・play-count powers は knowledge 差と
混かる（札名出現は機構ではない）。

### batch2 の outcome（完了分）

| seed | arm | control | delta | attribution |
|---|---:|---:|---:|---|
| `U2M7K5F9RA` | 10勝1敗 | 10勝1敗 | 0 | knowledge-only（機構は arm 側で195、control 189） |
| `T3XQ7WM2VP` | 12勝1敗 | 12勝1敗 | 0 | clean pair（Duplication 119、Gigantification 207）だが分歧0 |
| `M7C4Q9V2RH` | 13勝1敗 | 17勝1敗 | −4 | 第一分歧が knowledge-driven（116分歧）＋ control exception 1件 → 機構単独ではない |
| `C8Q1Z7E3KS` | 13勝1敗 | 13勝1敗 | 0 | 機構を state に出さない |
| `M5W9C3T7LQ` | 1勝0敗・走行中 | 16勝1敗 | — | — |

机构単独の分歧を出した seed は H2（46分歧、+2）と AM8（87分歧、outcome 同値）の2件のまま。
`M7` の −4 は knowledge 差（card table の classification）で path が分かれた結果で、機構の実装差として
読めない。run レベルの母数では机构単独の win 效果は依然 H2 だけ。

### knowledge-confound の内訳（H2 46分歧のうち39件、AM8 87分歧のうち85件）

`control_card_table()` を control の `CARD_COST` ＋ `CARD_NAMES`（basic/status 名）で built した
（commit `0edccb5`）。その形で分歧位置を分けた：

| seed | 分歧 | power/relic が両腕に在る | knowledge-confounded | clean（機構位置かつ control も知っている札だけ） |
|---|---:|---:|---:|---:|
| `H2LV6ZJ4XW` | 46 | 46 | 39 | **7** |
| `AM8C6YXHSG`（harness） | 87 | 87 | 85 | **2** |
| `U2M7K5F9RA` | 62 | 0 | 61 | 0 |
| `M7C4Q9V2RH` | 116 | 0 | 110 | 0 |

confounded の位置は「arm だけが card table を知っている札」が hand に在る位置なので、分歧が機構から
来たのか knowledge から来たのか観測だけでは割れない。割るには同一 observation で arm（control 形の
table）／control を replay する必要がある（sample の形）。

→ 機構単独の win 效果として run レベルで立っているのは H2 の +2 だが、その46分歧のうち clean は7件。
AM8 の87分歧の clean は2件。母集団は薄いまま、という読みが今の正直な形。

### harness が机构の無い path で control と完全一致（M5）

`mechonly_arm_b2_M5W9C3T7LQ`：303 aligned、分歧0、両 run 例外0件、outcome **16勝1敗 = control と同値**。
机构が state に出ない seed では、pin した arm は control と決定列が完全一致する（生成集合の差を消した
ので、difference が机构以外に無い）。harness の预期どおり。

机构の無い seed（M5・C8・N8・D1・Q6・B3）の分歧0は、機構の実装が無効だからではなく、机构を引かなかった
から測定にならない（path 運）。分歧0の seed は機構の実装が決定を動かさなかった case と区別できない。

### `V7D3M9H2XW` は pair candidate（batch2 の control run は PanachePower を seq 221-224 に出している）

前ラウンドで「V7 は機構を state に出していない」と書いたが、その数字は corpus の**別の run**（11 record）
だった。batch2 の control run（`mechonly_ctrl_b2_V7D3M9H2XW`）は combat record の state に
`POWER.PANACHE_POWER` を **seq 221〜224** に出している。arm は現在62 aligned（分歧0）でそこに達していない。
arm が同じ path を追えば同じ位置で Panache を見る预期 → 達した位置からの分歧が機構単独の差になる。

`mechonly_attribution.py` の `first-mech` が V7 で None を返すのは、arm 側がまだその record に達していない
から（aligned 集合の側でしか見ていない）。

### V7：arm が Panache の位置（seq 221）に達して、その位置の分歧は0（現時点）

`mechonly_arm_b2_V7D3M9H2XW`：aligned 170件、分歧0、両 run 例外0件。arm が `POWER.PANACHE_POWER` を
seq 221 で見た（control も 221）→ clean mechanism position。分歧は出ていない（Panache の
counter 5枚目 play 触发がその path で決定を変えていない）。

note の fold：Rose（`a328b5c`）と生成プール（`77120b2`）の項目は完了として `[x]` にし、残る confound は
card table の knowledge 差として書き直した。

### mech vs knowledge の分割（同一条件 replay、game 不在時に実行）

`data/mech_vs_knowledge.py`（commit `ab9634f`）で、harness run の分歧位置を3条件で replay した：

| seed | 分歧 | mechanism-only（variant2 ≠ variant1） | knowledge-only（variant3 ≠ variant1 かつ variant2 = variant1） |
|---|---:|---:|---:|
| `H2LV6ZJ4XW` | 46 | **13** | 0 |
| `AM8C6YXHSG` | 87 | **22** | 0 |
| `R8V2H6N4ZB` | 0 | 0 | 0 |
| `P3V8N5K2RX` | 0 | 0 | 0 |

・replay は recorded decision を再現しないことがある（measure：control の rollout decisions 280件中260件）。
live process は per-run の module state（`upgraded_cards` の memo、Paels Flesh の once-per-run guard 等）を
持つから。だから分割は**同一条件の replay 同士**の比較で、`control-replay-reproduces-record` として別に
出している（H2 0/46、AM8 3/87）。
・ classification が空いている位置（H2 46-13、AM8 87-22）は、fresh replay 下では arm と control が同じ
选择に落ちる位置＝live の決定は module state か fallback 由来。机构単独の差として clean に言えるのは
mechanism-only  counts（13件、22件）だけ。

→ 機構単独の決定差（同一条件で隔离済み）：Forgotten Soul 13件（H2）、Fiddle 22件（AM8）。run レベルの
win 效果は H2 の +2（1 seed）のまま。

### H2 の mechanism-only 13件は机构が1つだけなので attribution が歧義がない

13位置を1件ずつ確認：両腕の state に出ている機構は `RELIC.FORGOTTEN_SOUL` **だけ**（>1の位置0件）。
例（fresh replay、同一条件）：

- seq 444：control replay `CARD.ANGER` / arm replay end_turn
- seq 445：control `CARD.ANGER` / arm `CARD.STRIKE_IRONCLAD`
- seq 446：control `CARD.ANGER` / arm end_turn

→ H2 の13件は Forgotten Soul 単独の差（`AfterCardExhausted`：exhaust 1枚につき random 1 hittable 体へ
1 unpowered）。AM8 の22件は Fiddle 単独（その位置で Fiddle だけの位置が主体。Fiddle＋Chains の14件は
単独へ割れない）。

**破いた実験（記録として正直に）**：Fiddle の「拒否 part」と「+2 part」を分割する test を走らせたが、
その位置の机构は Fiddle ではなく Forgotten Soul だった上、+2 は `_draw_into_combat` の path に無い
（turn start 側）ので patch が効いていない。数字（28/1）は意味を持たない → 破棄。

### play-count powers：game 実装は play 全体をもう一度解像する（model は damage と block だけ）

cached decompile（`MegaCrit.Sts2.Core.Models.Powers/DuplicationPower.cs`）：

```csharp
public override int ModifyCardPlayCount(CardModel card, Creature? target, int playCount) {
    if (card.Owner.Creature != Owner) return playCount;
    return playCount + 1;
}
public override async Task AfterModifyingCardPlayCount(CardModel card) => await PowerCmd.Decrement(this);
```

＝power は **play count を +1** する（play 全体がもう一度解像される）で、modification の直後decrement、
turn 終わりに remove。model は `play_duplicated` flag で damage hit と block grant を2倍にするだけ
（`combat.py` line 1080 と 2824 の2箇所）なので、draw・status 付与・energy・self-damage・multi-effect card
の extra resolution が抜けている。**忠実度の gap として記録**（実装していない：play 本文が `_step` 内に
インラインで、card effects は data-driven ではないため、loop 化は大きい refactor）。

実走でこの gap が決定に出たcaseは Currently 0（P3 の pair で分歧0、batch2 の Duplication位置で分歧0）。
なので gap は correctness の記録として残し、win-rate の判定には影響しない。

### play count の semantics（`CardPlay.cs` の documentation）

> The total number of times this card is going to be played. Usually 1, but when a card has an effect
> like Replay, it will be higher (Replay 1 will have playCount=2, …). You can compare this with playCount
> to see if you're on the final play of the card.

＝ play count は **card が play される回数**で、`AfterCardPlayed` 等の hook は play ごとに走る。だから
Duplication/OneTwoPunch の extra resolution は card の effect 全体（draw・status 付与・power stack・
per-play trigger）をもう一度走らせる。model は damage hit と block grant だけを2倍にする近似。

Gigantification（`BeforeAttack` で first powered Attack **command** を mark、`ModifyDamageMultiplicative`
は mark された command の damage だけ×3、その command 完了で decrement）＝ model の
`card in ATTACKS and attacks_played_this_turn == 0` と等価（multi-hit card は同一 command 内なので全体×3）。
Panache（`alreadyApplied`：適用 play を数えない、5 play ごとに Amount を全 hittable へ Unpowered、
counter reset、turn end で CardsLeft=5 へ戻す）＝ model と一致。

→ 揃っていないのは play-count powers の「effect 全体の再走」だけ。card effects が `_step` 内 inline
（data-driven でない）なので loop 化は大きい refactor。実走でこの gap が決定に出た case は0件
（P3 の pair・batch2 の Duplication位置で分歧0）→ 记録してそのまま。

### play-count powers の gap が決定に出る母数を数えた（73件 / 15 seed）

実走 corpus で、decision の時点で `DuplicationPower`・`OneTwoPunchPower` が active だった recordは
**73件 / 15 seed**。打った札の内訳：

- block cards **54件**（Defend 25・Shrug It Off 25 ほか）
- attack **9件**
- end_turn / none **10件**

model は block grant を2倍にする（line 1080）ので Defend は正しい。**Shrug It Off（block 5 + draw 1）は
draw が2倍にならない** → gap が決定に出る位置は Shrug の25件（＋status 付与札 Taunt 1件、power 札 Colossus
1件）。`CARD_VULNERABLE_TARGET` の status 付与も2倍にならないことを test で確認（Bash + Duplication →
Vulnerable 2 のまま、commit `57011bc` の読みと一致）。

実装は game 走行中で行わない（rule 9：run が in flight の間に policy code を触らない）。batch3 完走後、
draw（と status 付与・power stack）の extra resolution を `play_duplicated` で gate して、テスト
`test_duplication_re_resolves_status_and_draw_effects` で固定する。

### 「hittable」の忠実度：game は alive ∧ ShouldAllowHitting、model は alive だけ

`Creature.IsHittable`（decompile）＝ `IsDead` で false、`Hook.ShouldAllowHitting` が false なら false。
それを override する power は `IllusionPower`・`ReattachPower`・`DieForYouPower`・`AdaptablePower`・
`MockUnhittablePower`。model の hittable 集合（Forgotten Soul・Panache・LostWisp）は `enemy.alive` だけ。

実走 corpus（12,841件の機構 record のうち enemy powers を見た）でこれらの power は **0件** →
観察された case では model と game が一致する。だから現状は fix 不要（未観測の enemy power を
勝手に model に入れない rule のまま）。入れたくなるのは「hittable に filtered されていないから」だが、
根拠が0件なので記録だけ。

### batch3 進捗

`mechonly_ctrl_b3_D6A1F8C3E5` 完走：**17勝1敗、例外0件、`POWER.CHAINS_OF_BINDING_POWER` を state に出した**
→ batch3 で第一の pair candidate（control clean）。`X3C9N6P4WQ` 5勝0敗・走行中（機構未出現）。

### batch3：corpus の母数 ≠ この run の母数（X3・SOS は機構を state に出さなかった）

`mechonly_ctrl_b3` 完走分（control `e808bdf`、例外0件）：

| seed | control | この run での機構 |
|---|---:|---|
| `D6A1F8C3E5` | 17勝1敗 | **Chains**（母数208 は corpus の別 run。この run は17 record） |
| `X3C9N6P4WQ` | 13勝1敗 | none |
| `SOS6XYXCNO` | 13勝1敗 | none |
| `L3PN5HBQ8T` | 3勝0敗・走行中 | none |

seed 選び（corpus の state 出現）は当たりませんでしたが、pair になるのは「この run が機構を state に出す」
case だけ。今の pair candidate は `D6A1F8C3E5` の1件（control clean）。arm（pin harness）が同じ path を
追えば Chains を同じ位置で見る预期。

### play count の全体再走：gate が足りない site（実装前の checklist）

`play_duplicated` を読んでいるのは今2箇所だけ：`_grant_block`（line 1080）と damage path（line 2824）。
game は play count +1 で**play 本文全体**を再走するので、以下が抜けている：

- draw：line 2321（`SHRUG` の draw 1）と line 2329（`CARD_DRAW`）→ `(count * 2 if play_duplicated else count)`
- status 付与：line 2930 付近（`CARD_VULNERABLE_TARGET`、Uppercute の Weak 等）→ 実測で Vulnerable が2倍
  にならないことを確認済み（Bash + Duplication → 2 のまま）
- power grant：`_after_power_play`（line 553）→ stack が1回分足りない
- self damage：`_apply_player_damage`（line 463）

母数（実走 corpus、play-count power が active だった decision 73件）：block cards 54（そのうち Shrug 25＝
draw gate が必要）、attack 9（正しい）、none 10。status 付与札 chosen は 0（Bash は3件）→ status gate は
corpus で決定的に効く母数が薄い。

実装は batch3 完走後（rule 9：run が in flight の間に policy code を触らない）。テストは
`test_duplication_re_resolves_status_and_draw_effects`（draw gate）と status gate の2本を予定。

### play count の再走：effect ごとに実測した（verified table）

同一条件の test 相当で1 play ずつ確認（DuplicationPower 1、dummy enemy）：

| effect | game（decompile：play count +1 で play 全体が再走） | model の現状 | 判定 |
|---|---|---|---|
| block grant | 2回 | 2倍（line 1080） | **一致**（Defend 5→10、Shrug 8→16） |
| damage hit | 2回 | 2倍（line 2824） | **一致**（Twin Strike 4 hit） |
| draw | 2回 | **1回だけ**（Shrug: hand size 1 のまま） | gap |
| status 付与 | 2回 | **1回だけ**（Bash の Vulnerable 2 のまま） | gap |
| power grant | 2回 | **1回だけ**（Demon Form の stack 2 のまま） | gap |
| self damage | 2回 | 1回だけ（gate 無し） | gap |

`play_duplicated` を読んでいるのは `_grant_block`（1080）と damage（2824）の2箇所だけ。
→ draw・status・power・self damage の site に gate を足す（checklist は上の節）。実装は batch3 完走後。

Fiddle との相互作用は正しい：Shrug の draw は `_draw_into_combat(..., from_hand_draw=False)` を呼ぶので、
Fiddle を持つと game は draw を拒否する（model も拒否）。Shrug の母数25件の中で Fiddle を持つ run は
Q6・D1（control-era）で、Fiddle 所持時に Shrug を打つ位置は拒否側で既に一致している。

### gate 追加の母数（決定に影響しうる record）

play-count power が active だった decision 73件の内訳で、model が既に gate している effect だけを持つ札
（attack 9、Defend 25）は gate 追加で変わらない。**gate が足りない effect を持つ札は 27件**：
Shrug It Off 25（draw）、Taunt 1（status）、Colossus 1（power）。＝ gate 追加が決定を変えうる母数は
27件 / 15 seed の中で最大27件。

control（`e808bdf`）が機構を state に出した seed は、既に走った run では batch1 の4（H2・AM8・R8・P3）＋
batch2 の4（U2・T3・M7・V7）＋ batch3 の D6 の9件で、いずれも測った。新しい母数を增やすには新しい seed
の control run が機構を state に出す必要がある（path 運）。

### state 出現だけでは機構は効かない（D6 の gate は0母数）

`mechonly_ctrl_b3_D6A1F8C3E5`（control、364 combat records、例外0件）：

- `POWER.CHAINS_OF_BINDING_POWER` が state に出た record：**38件**
- そのうちの **bound 札が hand にある record は 0件** → game の gate が立つ位置がこの run に無い
  （`legal_actions` から bound が消える事象が一度も無い）

＝机构的な「state 出現」は trigger 条件を満たさない。Chains の gate は *bound 札が hand に在る* decision
で効く（第一 play 後）。同じ形は play-count powers にもある：power が active でも、その decision で
札を打たなければ（end_turn 10件）消費も额外解像も起きない。

→ run レベルの机构単独の差は「機構が trigger した位置」でしか出ない。batch3 は D6 以外の seed が機構を
state に出しておらず、D6 も trigger 位置が無いので、分歧が出ない見込み（arm stage は control の path を
追うので同じ）。母数增やす の目的は、trigger 位置を持つ seed を find することとして继続します。

### gap の trigger 母数（`e808bdf` の control run では1件だけ）

control run で play-count power が active だった decision を札の effect 別に分けた：

- `T3XQ7WM2VP`：Duplication ×1 = **block 札**（model は block を2倍にするので正しい）、Gigantification ×1 =
  attack（正しい）→ gap の trigger 母数 **0**
- `U2M7K5F9RA`：OneTwoPunch ×1 = **status 札**（status 付与が2倍にならない → gap）、Duplication ×1 = block
  （正しい）→ gap の trigger 母数 **1**

corpus 側の27件（Shrug 25・Taunt 1・Colossus 1）は arm-era commit の run の数字。`e808bdf` の run では
gap が決定に出る母数は1件（U2）でした。

→ gate 追加は**正しさの修正**としては意味がある（decompile 根拠）が、測った outcome を変える母数は
ほぼ無い。実装は batch3 完走後に site 4箇所＋テスト2本で行う（rule 9）。

### gate の trigger 母数：測った control run では9 seed 全部0

`e808bdf` の control run で、Chains が state に出た record と bound 札が hand にある record：

| seed | Chains present | bound in hand（gate 母数） |
|---|---:|---:|
| `H2LV6ZJ4XW` | 0 | 0 |
| `AM8C6YXHSG` | 18 | 0 |
| `R8V2H6N4ZB` | 17 | 0 |
| `P3V8N5K2RX` | 0 | 0 |
| `U2M7K5F9RA` | 0 | 0 |
| `T3XQ7WM2VP` | 0 | 0 |
| `M7C4Q9V2RH` | 21 | 0 |
| `V7D3M9H2XW` | 0 | 0 |
| `D6A1F8C3E5` | 38 | 0 |

power が state にあることと、札が bound であることは別（Chains は引いた札を afflict する）。だから
651件の gate 母数は**札が bound だった run**（corpus 側）の数字で、この panel/batch の control run では
gate が一度も立っていない。→ Chains の gate は run レベルでは測定不能（offline の17%分歧率は同一
observation の replay での数）。

同じ形の note：play-count powers の gap も、`e808bdf` の run では trigger 1件（U2 の status 札）だけ。
機構単独で分歧を出したのは H2（FS、trigger 位置あり）と AM8（Fiddle、draw の trigger 位置あり）だけ。

### ChainsOfBindingPower の decompile（gate は draw 経由で afflicts）

`ChainsOfBindingPower.cs`（power、Debuff/Counter）：

- `AfterCardDrawn`：owner の player が自分の side で札を引いた時、`Bound` affliction が possible なら、
  **その turn に afflict した count が Amount 未満の場合だけ** afflict する（`CardAfflictedEntry` を数える）
- `BeforeCardPlayed`：bound 札を play した時に `boundCardPlayed = true`
- `ShouldPlay`：bound 札は `boundCardPlayed` が立ってから gate される（最初の1枚は打てる）
- `BeforeSideTurnEnd`：`boundCardPlayed` を reset し、bound affliction を**全部 clear**

model の形（`bound_played_this_turn` ＋ turn end flush ＋ rollout 中の draw で afflicts）はこれと一致。
`fromHandDraw` はこの実装では条件に使われていない（turn start の draw も afflict 対象）。

測った control run（`e808bdf`）で bound 札が hand にある record が 0件（9 seed）＝これらの run では
power が active 中に draw が起きなかった（decision で札を打たない、または draw を伴わない play）。
だから gate は run レベルで trigger していない → 分歧が出ない。651件の母数は draw が起きた run の数字。

B4（batch3）：Chains present 29 record、bound in hand 0、gate active 0。

### verified gap：Chains の per-turn cap は「hand に在る bound 札」で数えている（game は afflicted entries）

game（`ChainsOfBindingPower.AfterCardDrawn`）：その turn に afflict した **entry 数**（`CardAfflictedEntry`、
`HappenedThisTurn`）が Amount 未満のときだけ afflict する。札が hand から消えても entry 数カウントは残る。

model（`combat.py` line 808-816）：`already_bound = hand に在る bound 札` ＋今回 mark する分，で cap を
見る。だから bound 札を play して hand から消すと、同じ turn 内で cap を超えて afflict できる。

同一条件で確認（ChainsOfBindingPower amount 2、draw pile に Strike）：

- Flash of Steel（draw 1）→ bound 1件（entry 1）
- その turn で Offering（draw 3）→ model は **2件 additional** mark（total 3 > cap 2）
  game は cap 2 で止まる（2件目の draw 以降は afflict しない）

→ fix：turn 単位の `chains_afflicted_this_turn` counter を持つ（entry 数で cap を見る）。実装は batch3 完走後
（rule 9：run が in flight の間に policy code を触らない）。テストは
`test_chains_afflicts_stop_at_the_per_turn_cap_after_a_bound_card_leaves_hand` を予定。

実走ではこの gap が決定に出る母数が薄い：測った control run 9 seed で bound 札が hand に在る record は0件
（draw が decision で起きなかった）。Shrug の draw は play-count power の gate と同じ位置（U2 の1件）で、
Chains の cap と絡む位置は corpus 側の651件（draw が起きた run）に属します。

### gate の母数は「同じ path」でないと pair にならない（N8 の case）

bound 札が hand に出た run は corpus で N8 786・H2 431・D6 56 record（`candidate_*` の control-era run）。
しかし batch1 の control run（`e808bdf`）で N8 は機構を state に出さなかった（Chains が無い）ので、その
gate 母数は `e808bdf` の run とは別の path（relic 獲得の有無が違う） belongs。同じ seed でも path が
違えば pair にならない → run レベルでは測定できない。

同じ seed の別の run で機構が揃う caseは、`9X9`（Duplication 両腕）と `73P`（OneTwoPunch 両腕）の2件で、
いずれも reach 0。機構が state に出た control run（`e808bdf`）は測った限り H2・AM8・R8・P3・U2・T3・M7・
V7・D6・B4 の10 seed（B4 は gate 母数0）。機構が decision で trigger した seed は H2（FS）と AM8（Fiddle）
だけ。

→ 母数を增やすには trigger 位置（draw が decision で起きる、または play  Count powers が active の play）
を持つ path が必要。batch3 完走後に、忠実度の fix（Chains cap を entry 基準へ、play-count の gate 4箇所）
を実装して、trigger 位置が生まれた run で分歧が出るかを見る。

### Fiddle の decompile（cached tree で原文再確認）

`MegaCrit.Sts2.Core.Models.Relics/Fiddle.cs`：

- `ModifyHandDrawLate`：owner の hand draw に `Cards`（2）を加える
- `ShouldDraw`：`fromHandDraw` は true、owner 以外 true、owner でも current side が自分の side でない限り
  false（＝player side 中の draw を拒否）。`AfterPreventingDraw` は flash だけ（効果なし）

model は両方一致（`combat.py` line 803 の拒否、turn start の +2）。実走1,436件で hand が一度も growth
しなかったこと（player side 中の draw 0件）も同じ根拠。

→ play-count powers の忠実度 half は確認完了。model を揃える未実装 part は2件：
1. Chains の per-turn cap（hand 基準 → **entry 基準**へ）（commit `74a87c6`）
2. play count の全体再走（draw・status・power・self damage の gate）（commit `ef5d31e`）
どちらも batch3 完走後に実装（rule 9）＋テスト2本。

### 訂正：Chains の cap gap は実走では観察されていない（130件は index を札の identity と思った artifact）

- 実走 record で **bound 札が hand に3枚以上在る record は0件**（amount は全 record で3）＝ game の cap と
  contradictions が観察されていない
- 「1 turns 内で ever-bound が amount を超えた130件」は、hand の `index` が play/draw でずれるので同一札を
  別 identity として数えた artifact。trace に stable な card id が無いのでこの検査は使えない
- 実装差（hand 基準 vs entry 基準）は constructed test で示せた（draw 1 → bound 1、同じ turn で draw 3 →
  model は cap を超えて mark できる）が、実走での発生は0件

→ cap の fix は正しさの修正として価値がある（game の entry 基準に揃う）が、実走の決定を変えた記録はない。
play-count powers の gate 追加と同じ位置づけ：実装差はあるが、実走の母数が薄い（27件中実際に決定に
出たcaseは U2 の1件）。

### batch3 の pair candidate 3件、すべて gate 母数0

| seed | control | Chains records | bound in hand | gate active |
|---|---:|---:|---:|---:|
| `D6A1F8C3E5` | 17勝1敗 | 38 | 0 | 0 |
| `B4J8Q1R6YK` | 17勝1敗 | 29 | 0 | 0 |
| `T5R8K2N9QP` | **21勝1敗**（完走） | 34 | 0 | 0 |
| `X3C9N6P4WQ` | 13勝1敗 | 0 | 0 | 0 |
| `SOS6XYXCNO` | 13勝1敗 | 0 | 0 | 0 |
| `L3PN5HBQ8T` | 13勝1敗 | 0 | 0 | 0 |

Chains が state に出ても、その turn で draw が起きなければ gate は trigger しない（bound 札が hand に
現れない）。だから batch3 は机构単独の分歧を出さない見込み（arm stage は control の path を追う）。
arm stage を開始（job `bash-697`、start commit `c3d9fd2`）。忠実度の fix は arm stage 完走後（rule 9）。

### 母数の二 kinds：observed gate（legal_actions から bound が消える）と model の rollout gate

- **observed gate**：game が decision 時に bound 札を hand に持ち、`legal_actions` から除外していた record。
  corpus で651件 / 3 seed（N8 399・H2 224・D6 28）。batch3 の control run（D6・B4・T5）は observed gate
  **0件**（bound 札が hand に出なかった）
- **rollout gate**：model の rollout が future draw を simulate する位置。Chains が state に在れば model は
  draw した札を bound に mark して rollout 中の play から除く。control tree は gate を持たない（札名を
  知らないだけで、rollout は打てる扱い）→ 分歧しうる。これは機構の実装差で、knowledge 差ではない

D6 は両腕が同じ seq 454 で Chains を得た（clean pair）。分歧が出たら rollout gate 由来。arm run は現在
aligned 62件（分歧0）。

→ 前ラウンドの「batch3 は分歧を出さない見込み」は observed gate 関于；rollout gate は Still分歧を生む
うる。判定は power/relic が両腕の state に出た位置で数える（`mechonly_attribution.py` の今の形）。

### `D6A1F8C3E5`：clean pair だが gate が決定を動かさなかった（364件分歧0、outcome 同値）

arm 完走 17勝1敗 = control と同値。Chains が両腕の state に出た位置（38 record、両腕同じ seq 454 から）で
分歧0。rollout gate（model が simulate する draw で bound mark する位置）でも決定が変わらなかった。

batch3 の今の形：`D6` ±0、`X3` 115件分歧0・走行中、残 `SOS`・`L3`・`B4`・`T5`。
机构単独の win 效果は H2（+2）のまま、AM8（22件 mechanism-only）は outcome 同値。

###  planned fix（apply 前の精确な形）：`_draw_into_combat` の chains block

現状（`combat.py` line 803-818）：

```python
chains = _power(combat.player_powers, "ChainsOfBindingPower")
if chains:
    already_bound = sum(1 for value in combat.hand if isinstance(value, Card) and value.bound)
    for value in drawn:
        if isinstance(value, Card) and already_bound < chains:
            value = replace(value, bound=True); already_bound += 1
```

`already_bound` は **hand に在る bound 札**なので、bound 札を play/exhaust して hand から消ると cap が
回復する。game は `CardAfflictedEntry` の `HappenedThisTurn` 数で cap を見る（entry は札が消えても残る）。

→ 追加する field：`chains_afflicted_this_turn: int = 0`（turn start で reset、`_step` の play で消費され
ない）。block を `chains_afflicted_this_turn < chains` に変更、mark 時に increment。テスト：

```
test_chains_afflicts_stop_at_the_per_turn_cap_after_a_bound_card_leaves_hand
```
（draw 1 → bound 1、同じ turn で bound 札を play、draw 3 → game は cap 3 で止まる：model は entry 基準なら
3枚目以降を mark しない。hand 基準だと mark してしまう）

apply は batch3 の arm stage 完走後（rule 9）。play-count powers の gate 4箇所（draw・status・power・
self damage）も同じ run 完走後。

### Chains の gate：`BeforeCardPlayed` は dupe（extra resolution）を数えない

`ChainsOfBindingPower.BeforeCardPlayed`（decompile）：

```csharp
if (card.IsDupe) return Task.CompletedTask;   // extra resolution は flag を set しない
...
if (!(card.Affliction is Bound)) return Task.CompletedTask;
GetInternalData<Data>().boundCardPlayed = true;
```

`ShouldPlay(card, autoPlayType)` は `!boundCardPlayed` を返す（autoPlayType を check しない）＝ autoplay
でも gate される。

model：`bound_played_this_turn` は1枚目の bound play で set、`play_duplicated` は同一 card の extra
resolution（flag を再 set しない）→ game の `IsDupe` bypass と同じ形。

実走の「45 turns で2枚以上の Bound 札を打った」case は、同一札の duplicate resolution（play count 2）で
説明がつく。distinct card の2枚目は game でも gate される。

テスト `test_chains_of_binding_afflicts_cards_drawn_during_the_rollout` は cap の recovery を test していない
（draw 7枚、amount 3 → 3件 bound。hand 基準でも entry 基準でも同じ結果）→ planned fix のテストは新しい1本
として追加する（既存テストは壊さない）。

### power grant も play ごとに走る（Demon Form の decompile）

`DemonForm.cs`：effect は `OnPlay(cardPlay)` 内（`PowerCmd.Apply<DemonFormPower>`）。game は play count だけ
`OnPlay` を走る（`CardPlay.PlayCount` の documentation どおり）→ play count 2 なら power は2回 apply される。
model は1回だけ（実測：Duplication active で Demon Form を打つと stack 2 のまま、commit `88970dc`）。

忠実度の最終形（decompile 根拠で確定）：

- 一致：block grant、damage hit（gate 済み）
- gap（model が1回だけ）：draw、status 付与、power grant、self damage
- gap（basis が違う）：Chains の per-turn cap（game は entry 基準、model は hand 基準）
- 一致：Gigantification（first powered Attack command ×3、dupe bypass の flag 形）、Panache（alreadyApplied、
  5 play trigger、turn end で CardsLeft reset）、Fiddle（+2 と player side 中の draw 拒否）

実装は game が idle になったときに gate 4箇所＋cap の field を追加し、テスト2本で固定する（rule 9）。

### gate 追加は小さい change でよい（effect site が同一 scope に在る）

`play_duplicated` は `_step` 内で play の解像开始前に set される（line 2142-2161）。effect site は同じ
scope：

- status 付与：line 2930（`CARD_VULNERABLE_TARGET`、Uppercut の Weak）
- draw：line 2321（`SHRUG`）、line 2329（`CARD_DRAW`）
- power grant：line 2365・2383（`card in POWERS`、Demon Form）
- self damage：`_apply_player_damage`（line 463）

＝「play 全体をもう一度 loop する」大きな refactor ではなく、各 effect type で `* (2 if play_duplicated
else 1)` を加える形で game と等価になる（game の play count は play ごとに `OnPlay`/commands を走る。
model が enumerate している effect type を全部 gate すれば、multi-effect card も正しく2回分）。

Chains 側は field 1本（`chains_afflicted_this_turn`）＋ block の cap を entry 基準へ。テスト2本。
apply は batch3 の arm stage 完走後（rule 9）。

### refinement：per-play trigger も play count に応じて走る（gate だけだと足りない category）

game は `CardPlay` を play count 回数実行するので、`AfterCardPlayed` 系の trigger（Panache の
`CardsLeft` counter、Juggernaut の block-on-play、Fiend Fire の count、Hellraiser の autoplay 等）も
resolution ごとに走る。model は `_step` 1回で1回だけ counter を動かす。

だから per-effect gate（damage・block・draw・status・power・self damage）に加えて、**per-play trigger**
の category がある。cost と hand の除去は play 単位で1回（game の `CardCmd.Play` は play 1回で、commands
が playCount 回走る）＝ model は cost を1回落とすので正しい。

→ 完全な忠実度は「play 本文を playCount 回 loop する」形。per-effect gate はその近似で、trigger category
が抜ける。母数（実走）は play-count power が active だった decision **73件**、そのうち effect category が
gate 外なのは 27件（draw/status/power/self damage）。trigger category が決定に出た母数は数えていない
（Panache の trigger 位置は corpus で1件、その1件は knowledge-only 分歧だった）。

apply 時に決める：loop 形（完全）か per-effect gate（近似、trigger は記録したまま）。母数が薄いので
近似で十分という読みも正直に書く。

### play loop の実物（`CardModel.cs`）：effect も `AfterCardPlayed` も playCount 回数走る

```csharp
int playCount = await GeneratePlayCount(combatState, target);
...
for (int i = 0; i < playCount; i++)
{
    CurrentPlayIndex = i;
    ...
    CombatManager.Instance.History.CardPlayFinished(combatState, cardPlay);
    await Hook.AfterCardPlayed(combatState, choiceContext, cardPlay);
}
```

card の result pile への移動と cost（`resources`）は loop の外 ＝ play 単位で1回。model も cost を1回
落とすので正しい。loop 内にあるのは card の effect と `AfterCardPlayed`（＝ per-play trigger）。

→ model が gate しているのは damage と block の2 category だけ。per-play trigger（Panache counter、
Juggernaut、Fiend Fire count、Hellraiser autoplay）と draw・status・power・self damage が抜けている。
完全な忠実度は play 本文を playCount 回 loop する形；per-effect gate は近似。実走の母数27件、決定に
出たcaseは U2 の1件（status）＋ Panache の1件（knowledge-only）。

plan（apply 時に決める）：`_step` の play body を loop 化する（diff が大きい）か、per-effect gate を4
category に広げ、trigger category は limitation として記録したまま置く。どちらでもテストは
「1 play で effect が2回走る」形を書く。

### per-play trigger の母数：実走0件（play-count power と同じ decision で trigger power が active な case が無い）

play-count power（DuplicationPower・OneTwoPunchPower）が active だった decision **73件**（15 seed）と、
per-play trigger power（PanachePower・JuggernautPower・FiendFirePower・HellraiserPower）が同じ decision で
active だった case を cross した：**0件**。

→ trigger category の gap は観察された run で0母数。だから近似（per-effect gate 4 category を追加）で
決定の変化は出ない。play count の effect category（draw・status・power・self damage）の母数27件の中で
決定に出たcaseは U2 の1件（status）だけ。

plan の形は変わらない：per-effect gate 4 category を追加＋Chains cap を entry 基準へ、テスト3本。loop 形
（完全な playCount loop）は、trigger category も含むので、将来 trigger が同じ decision で active になる
run が現れたときに必要。母数0の現状では、loop 形を「正しさの完全形」として記録し、apply は per-effect
gate + cap にする（小さい diff、既存736テストを壊さない）。

### apply 時に書くテスト（预先の形）

```python
def test_play_duplicated_re_resolves_draw_effects(self) -> None:
    # Shrug It Off: block 5 + draw 1. With DuplicationPower the game re-runs the whole play,
    # so both the block grant and the draw happen twice.
    draw = tuple(Card(STRIKE) for _ in range(4))
    combat = Combat(80, (Card(SHRUG),), draw, (), (Enemy("MONSTER.DUMMY", 200, "IDLE_MOVE", ()),),
                    energy=1, player_powers=(("DuplicationPower", 1),))
    after = step(combat, "card:0", DUMMY_DATA, random.Random(0))
    self.assertEqual(after.player_block, 10)     # already gated: passes
    self.assertEqual(len(after.hand), 2)         # fails today (draw runs once); passes after the gate

def test_play_duplicated_re_resolves_status_and_power_effects(self) -> None:
    # Bash applies Vulnerable; Demon Form applies a power stack. The game re-runs OnPlay per play count.
    ...

def test_chains_afflicts_stop_at_the_per_turn_cap_after_a_bound_card_leaves_hand(self) -> None:
    # The game counts CardAfflictedEntry happened this turn, so a bound card leaving hand does not
    # free up the cap. Today the model counts bound cards still in hand.
    ...
```

既存の `test_duplication_power_resolves_the_next_play_twice`（damage）と
`test_duplication_power_doubles_the_next_block_card_grant`（block）は gate 追加後も pass する。
`test_chains_of_binding_afflicts_cards_drawn_during_the_rollout`（draw 7、amount 3）は hand 基準でも
entry 基準で同じ結果なので壊れない。

### knowledge-confound の母数（正しく数え直した：123件、札名は status 札）

前ラウンドの「67/352件」は错的。control の `CARD_COST` は display name（"Defend"）で key しており、trace
の id（`CARD.DEFEND_IRONCLAD`）と直接 compare していた。正しくは `official_agent.CARD_NAMES` で id →
display name へ map してから、control の table に在るかを見る。

その形で batch3 の arm run を数え直した（control が score できない札が hand に在る record）：

| seed | records |札名 |
|---|---:|---|
| `D6A1F8C3E5` | 83 | BYRDONIS_EGG・CLUMSY・THINKING_AHEAD・WOUND |
| `B4J8Q1R6YK` | 17 | BYRDONIS_EGG・PROLONG・WOUND |
| `L3PN5HBQ8T` | 15 | WOUND |
| `X3C9N6P4WQ` | 4 | WOUND |
| `SOS6XYXCNO` | 4 | WOUND |
| 合計 | **123** | status 札だけ |

`e808bdf` の control はこれらの status 札名を持たない（head では `HAND_INJECTED_STATUS` に WITHER 等が
あり、status 札の扱いは後から入れた）。confound の母数は123件だが、batch3 では分歧0 → confound が決定
を変えなかった case。

### 訂正：H2・AM8 の分歧は knowledge-confound ではなかった（前数えは bug）

`mechonly_attribution.py` の confound 数えは、trace の id（`CARD.DEFEND_IRONCLAD`）を control の
display-name table（"Defend"）と直接 compare していた。正しくは control 自身の `CARD_NAMES` で id →
display name へ map してから table を見る（commit `8799324`）。

その形で数え直した：

| seed | 分歧 | by-mechanism | knowledge-confounded |
|---|---:|---|---:|
| `H2LV6ZJ4XW` | 46 | Forgotten Soul 46 | **0** |
| `AM8C6YXHSG`（harness） | 87 | Fiddle 87・Chains 14 | **0** |

→ commit `ebfb9dd` の「H2 の46分歧のうち39件は knowledge-confounded、AM8 の87分歧のうち85件」は誤り。
分歧位置の札は control も table に持っていた。knowledge-confound が実在した母数は batch3 の arm run の
123件（status 札 WOUND・CLUMSY・BYRDONIS_EGG・PROLONG・THINKING_AHEAD）で、そこでは分歧0。

同一条件 replay での分割（`data/mech_vs_knowledge.py`、commit `ab9634f`）の数字は別の根拠なのでそのまま：
H2 mechanism-only 13件、AM8 mechanism-only 22件、knowledge-only 0件。

### knowledge 差の正体：hand だけじゃなく deck/draw pile 経由でも決定を変える

arm と control の card table 差は次の6 entryだけ（`e808bdf` vs HEAD）：

- `CARD_COST`：One-Two Punch、Panache
- `SKILLS`：One-Two Punch、`POWERS`：Panache、`UNTARGETED`：両方
- `HAND_INJECTED_STATUS`：Wither

`mechonly_attribution.py` の confound 数えは hand に在る札だけを見ていた。だから `U2M7K5F9RA` の62分歧
（hand に OneTwoPunch が無い位置）は confound 0 と出たが、rollout が draw pile からその札を引く位置では
control は score できず arm はできる → 同じ knowledge 差で決定が変わる。

→ confound の正しい母数は「hand OR rollout で draw される札」に arm だけの entry が現れる位置。hand だけ
の数えは undercount。正しく分ける方法は `data/mech_vs_knowledge.py`（tables を control 形へ pin した
replay と、arm 形の replay を比べる）で、U2 はその re-run が未実施（game 走行中、CPU rule）。

### attribution の caveat：arm–control 差は「8机构」以外も含む（`e808bdf` 以降の全変更）

`git diff e808bdf..HEAD -- combat.py official_agent.py` = 213 insertions。追加された token を数えたら：

- PANACHE 9、ONE_TWO_PUNCH 6、GIGANTIFICATION 4、FIDDLE 4、WITHER 2 → 8机构の側
- HELLRAISER 2 → HellraiserPower autoplay（`e808bdf` には無い、机构8件とは別）
- それ以外：SoarPower の ZeroDivision guard、Whirlwind の hit count、`bound`/`unplayable_this_turn` の
  分離、autoplay recursion の cap、turn-end curse の pin など

だから pin（生成集合）をしても、arm は control より「8机构＋その他の修正」分だけ違う。分歧位置が机构の
position でない case は「その他の修正」由来であり、机构単独の差として数えられない。

`B4J8Q1R6YK` の第一分歧（seq 430、state は両腕で一致、hand に机构札なし、Chains は 433 から）は
draw pile に `CARD.HELLRAISER` が在る位置 → Hellraiser autoplay の差で説明がつく。機構単独の attribution
には使えない。B4 の by-mechanism 9件は机构 position だが、その前に path が分歧しているので第一分歧の
rule に反する。

→ 判定で使えるのは、第一分歧が机构 position である case だけ。現状 H2（seq 441 が FS、両腕一致）と
AM8（harness、第一分歧が Fiddle 位置）の2件。

### batch3 の outcome（完了分）：全部 control と同値

| seed | arm | control | 分歧 | attribution |
|---|---:|---:|---:|---|
| `D6` | 17勝1敗 | 17勝1敗 | 0 | clean pair（Chains 454）、机构位置で分歧0 |
| `X3` | 13勝1敗 | 13勝1敗 | 0 | 機構を state に出さない |
| `SOS` | 13勝1敗 | 13勝1敗 | 0 | 機構を state に出さない |
| `L3` | 13勝1敗 | 13勝1敗 | 0 | 機構を state に出さない |
| `B4` | 17勝1敗 | 17勝1敗 | 11 | 第一分歧が机构以外（Hellraiser autoplay、seq 430）。机构位置の分歧9件は path 分歧後 |
| `T5` | 走行中（476 aligned、分歧0） | 21勝1敗 | 0 | clean pair（Chains 598）で分歧0 |

batch3 は win レベルで机构単独の差を出さなかった。机构単独で立っているのは H2（+2）と AM8（分歧87、
outcome 同値）の2 seedのまま。

### 実装した（commit `2e195d5`、テスト739件成功）

- draw gate：`SHRUG`（line 2334）と `CARD_DRAW`（line 2338）で play count 分だけ draw 数を挂ける
- status gate：`CARD_VULNERABLE_TARGET`（line 2937）と Uppercut の Weak/Vulnerable（line 2941-2943）で play
  count 分だけ apply する
- self damage gate：line 2375 で play count 分だけ回す
- Chains の cap：`chains_afflicted_this_turn` を追加（field line 307、turn start で reset、draw block で
  entry 数として数える）。hand 基準をやめた

テスト3本（draw・status・cap recovery）。Shrug の block は model の base 8（upgraded 11）なので gate 後は
16。Bash の Vulnerable は table 値2 → gate 後4。

**未 gating（正直に記録）**：power grant の branch（Demon Form・Fasten・Stampede・Aggression…）は多数の
個別 branch で、gate を入れていない。実走の母数1件（Colossus）なので、正しさの完全形（play 本文の loop
化）はまだ残っている。per-play trigger（Panache counter、Juggernaut、Fiend Fire、Hellraiser autoplay）も
同様に未 gating（実走の母数0件）。

忠実度の実装によって、同一条件 replay で「gate が決定を変える位置」の母数は draw 25件（Shrug）＋ status
1件（U2 の Taunt）＝26件。実走 panel の決定列は変更前の code で走っているので、この gate が実走 outcome
を変えた evidence は無い（rule のまま：offline の変化は採用根拠にしない）。

### gate の effect を同一条件で隔离した：73件で決定変化0

同一 record・同一 seed・同一 simulations で、gate 入りの code と gate を外した code（同じ文件の copy で
`(2 if play_duplicated else 1)` を `1` に置換）を比べた：

- records compared: **73**
- gate が choice を変える位置: **0**

＝忠実度の gate は正しさの修正として入れたが、観察された run の決定を変えない（draw/status が ranking
に効く位置がなかった）。前ラウンドの「replay が recorded choice と39件違う」は module state 由来で、gate
由来ではない（同一条件比較で0件）。

→ play-count powers の決定效果は、実走（73件）と同一条件 replay（0件）の両方で0。机构単独で決定を
動かした母数は Fiddle（sample で76件、harness run では分歧87件のうち同一条件で22件）と Forgotten Soul
（108件 sample、harness run 46分歧のうち13件）だけ。

### play count の忠実度：effect category は揃えた（commit `0647658`、テスト740件）

`plays = 2 if play_duplicated else 1` を play path の先で定義し、power grant の22 site を gate した。
これで game の「play 全体を playCount 回解像する」形の effect category（damage・block・draw・status・
power grant・self damage）は model 側も play count 分だけ走る。

- 確認：Demon Form + Duplication → DemonFormPower 4（gate 前2）。テスト
  `test_play_duplicated_re_applies_power_card_effects`
- 同一条件での isolation（73 record、gate 入り vs 外した copy）：**決定変化的0件**（commit `b709c88` の
  draw/status/self damage に加え、power gate も0件）

残る差：**per-play trigger**（`AfterCardPlayed` は play ごとに走る。Panache counter、Juggernaut の
block-on-play、Fiend Fire count、Hellraiser autoplay）。model は play 1回で1回だけ counter を動かす。
実走の母数は play-count power と trigger power が同じ decision で active だった case 0件なので、決定に
効く位置が観察されていない。完全形（play 本文の loop 化）は trigger を含めるために必要だが、母数0の
現状では limitation として記録したままにする。

### per-play trigger：実装した範囲と母数

実装（commit `1dbbd43`、テスト2本、suite **742件成功**）：

- Juggernaut：`AfterBlockGained` なので block を gained した resolution ごとに hit。`_grant_block` で
  `plays` 回 loop（テスト `test_juggernaut_triggers_once_per_play_resolution`）
- Panache：`AfterCardPlayed` は play ごとに走る。counter を `plays` 回 advance し、trigger 後 reset した
  値から次の resolution を数える（テスト `test_panache_counter_advances_once_per_play_resolution`：
  counter 4 の状態で duplicated play → trigger して reset、次の resolution で 1）

実走の母数：play-count power と per-play trigger power が同じ decision で active だった record **0件**
（re-confirm、commit `3661b48` の数字のまま）→ この gate は記録された決定を何も変えない。正しさの修正
として入れた。

まだ loop していない hook：Fiend Fire（OnPlay が hand を exhaust して count 分 damage。第二 resolution は
hand が空なので 0 になる＝単回応用でfaithful である可能性が高いが、card 自身の pile 移動が loop 内か外で
確認していない）、Hellraiser autoplay、Mayhem。これらは play 本文の loop 化をしないと一般に faithful
にならない。母数0なので、loop 化は保留（記録だけ）。

### Fiend Fire は gate 不要（第二 resolution は hand が空）

`FiendFire.OnPlay`（decompile）：hand pile を its 自身で read して `cardCount` を取り、その札を exhaust、
`DamageCmd.Attack(...).WithHitCount(cardCount)`。第二 resolution では hand は空（第一 resolution で全部
exhaust 済み）→ `cardCount = 0` で hit なし。model の単回応用は第一 resolution 相当なので faithful。

残る un-looped hook：Hellraiser autoplay（play ごとに走る）、Mayhem。母数0なので実装しない（記録だけ）。
per-play trigger category の実装範囲：Juggernaut（AfterBlockGained）と Panache（AfterCardPlayed）＝
commit `1dbbd43`、テスト2本、suite 742件成功。

### loop 形の適用範囲（commit `fdfe4f2`、テスト743件）

play 本文を丸ごと loop 化する代わりに、**resolution 単位に直すべき箇所を全部 `plays` で回す**形にした。
覆盖した category：

- effect：damage hit・block grant（relic の doubling は resolution ごと：`per_grant * plays`）・draw・
  status 付与・power grant・self damage
- per-play hook：SKILLS の VitalSpark/Enrage、POWERS の `_after_power_play`（relic）、Panache counter、
  Juggernaut（AfterBlockGained）
- per-play counter：`cards_played_this_turn`・`attacks/skills_played_this_turn`・
  `attacks/skills_played_combat`・`block_cards_this_turn`・`powers_played_this_turn`（テスト
  `test_play_duplicated_advances_the_per_play_counters_twice`）

Fiend Fire は loop 不要（第二 resolution で hand が空 → hit 0、commit `99823df`）。Hellraiser は
AfterCardDrawn なので play count と無関係（draw が重复しない限り triggers しない）。

**效果の測定**：同一条件（同一 record・同一 seed・同一 simulations）で loop 形と `plays = 1` の copy を
比べた → play-count power が active だった decision **73件で決定変化0件**。per-play counter と counting
relic が同じ decision で active だった record は47件あるが、その位置でも決定は変わらなかった。

＝loop 形は model の忠実度を game の形に揃える修正として入れた。実走の決定・outcome は変わらない
（panel の決定列は変更前の code で走った run なので、rule どおり offline の変化は採用根拠にしない）。

## RampartPower：ブロック再付与が敵側に見えていなかった（2026-10-04、commit `5f655ff`）

`data/audit_trace_fidelity.py`（新設）で全 trace 543本・combat record 145,325件を走らせ、
**観測されているのに `POWER_NAMES` に無い power** を数えた。85種類のうち15種類が未登録で、
母数の大きい順に ESCAPE_ARTIST（2,911件/190run）、SWIPE（2,078件/190run）、
TERRITORIAL（2,363件）、RAMPART（560件/73run）。

### 実装差（decompile 根拠）

`RampartPower.AfterSideTurnStart`：

- `side == CombatSide.Player` のときだけ走る
- block を貰うのは **自分ではなく `CombatState.Enemies.Where(c => c.Monster is TurretOperator)`**
- `LivingShield.cs` が自分に Rampart 25 を付与する（state machine の JSON には出てこない）

model は「観測で読めたターの block を、そのターン限り保持する」だけだった。ターの block は自分の
ターン開始に消える（`_enemy_turn` の `block=0`）ので、**第2ターン以降の rollout は block 0 の敵として
火力を計算していた**。replay の第一手だけが正しく、先が全部甘かった。

### 実走 evidence

`POWER.RAMPART_POWER` を持つ record は LivingShield + TurretOperator の対戦だけで560件（73run）。
その中の TurretOperator の block 値：

| 手番 | block 25 の record |
|---|---:|
| 1 | 175 |
| 2 | 163 |
| 3 | 50 |
| 4 | 5 |

LivingShield 本体の block は全 record で 0（自分には配らない）。ゲームの挙動は「毎手番 25 戻る」で、
model の「1回だけ」 Contradiction が record 側に立っていた。

### 実装とテスト

- `combat.py` の player ターン開始 section（`new_turn` を作る所）で、生きている Rampart 合計を
  `MONSTER.TURRET_OPERATOR` の block に足す。複数 LivingShield は足し算（game は copy ごとに走る）
- `official_agent.py` の `POWER_NAMES` に `POWER.RAMPART_POWER` を追加（無いと model が power 自体を見ない）
- テスト2本：`test_rampart_re_grants_turret_block_at_every_player_turn_start`（第2ターンに 25）、
  `test_rampart_stops_granting_block_once_the_shield_is_dead`（盾を倒すと 0）
- 回帰確認：親 commit の worktree で同じテストを走らせ、第2ターンの block が `0`（期待 25）で失敗
- suite **745件成功**

### 決定に出る母数（同一条件 replay）

同一 record・同一 simulations・同一 seed で HEAD（grant あり）と親 commit（grant なし）を比べた。
 trees は差分 commit 1つだけなので、分歧は grant の帰属に閉じる。

- records compared: **560**
- 決定変化: **63**、不変 497、例外 0
- seed 数: **10**（H2LV6ZJ4XW 25、B3N8V5T1WQ 10、R4A8D2K7ME 8、SOS6XYXCNO 6、R8V2H6N4ZB 4、
  D6A1F8C3E5 3、9X9WQB4QIH 3、L3PN5HBQ8T 2、M7C4Q9V2RH 1、B4J8Q1R6YK 1）

play-count powers の gate（73件で0）と違い、**忠実度の修正が決定を動かす位置が実在する**。
分歧の形は「control が block（Shrug It Off / Defend）、arm が attack（Strike / Bash / Anger）」が中心で、
ターの block が毎ターン戻るとなると block で削り合う価値が下ぐ方向。

**limitation**：game は `CombatManager.Instance.PlayersTakingExtraTurn.Count > 0` のとき grant を
飛ばす。model に extra turn は無いのでこの分岐は入れていない（extra turn を model 化するときに併せて必要）。
measure は offline の replay で、run の outcome はまだ見ていない（rule どおり採用根拠にはしない）。

### 同じ監査で残った候補（未実装）

- **ThievingHopper の `SwipePower`**：`ThieveryMove` が Draw+Discard から1枚選んで
  `CardPileCmd.RemoveFromCombat`（優先は Uncommon → Common/Rare/Event）。JSON の effects には
  `PowerCmd.Apply(... "swipe" ...)` だけで、カード除去は C# 側の move 本文。model は除去を見ていない。
  record 側では hand+draw+discard+exhaust の合計が THIEVERY_MOVE 後に1減る変化が **255件**（190run）。
  盗んだカードは hopper を倒すと extra reward で戻る（`SwipePower.BeforeDeath`）、5ターンで Escape すると
  戻らない。Escape 自体は `ESCAPE_MOVE` の `CreatureCmd.Escape` として既に model 化済み。
- **ESCAPE_ARTIST** は decompile 上「visual timer」で効果なし（`AfterSideTurnEnd` で Decrement するだけ）。
  model 化不要。
- **報酬 tier が無い札**：`CARD_NAMES` にある（＝combat で打てる）のに `CARD_TIERS` に無い札が35種類あり、
  実走で Purity 22回・Dramatic Entrance 9回・Production 8回提示されて **1回も取っていない**
  （tier 未登録は `CARD_TIERS.get(card_id, "D")` で最下位になり、deck 15枚以降は Skip 経路に落ちる）。
  Production は 0 energy で +2 energy、Dramatic Entrance は 0 energy で全体11 damage の Innate/Exhaust。
  これは model の忠実度ではなく reward policy の評価表の欠落なので、panel で測る話として保留。

### 報酬 tier が無い札：tier を足しても決定は動かなかった（2026-10-04、`data/reward_tier_probe.py`）

`CARD_NAMES` に在る（=combat.py で打てる）のに `CARD_TIERS` にエントリが無い札が35種類ある。
tier 未登録は `priority.get(card_id, 0)` と `CARD_TIERS.get(card_id, "D")` で最下位になる。
決定 trace の集計では Purity 22回・Dramatic Entrance 9回・Production 8回提示されて **1回も取られていない**。

ただし決定 trace の card_reward record は `cards`（札 id の一覧）しか持たず、policy が見た
`legal_actions` / 札の詳細（cost・type・rarity）を持たない。観測を保存している
`data/*_observations.jsonl`（139 run）と seq で対応付けて replay した：

- paired reward observations: **1649件**
- HEAD の replay が記録された選択を再現: **1622/1649**（98.4%）
- Purity 提示 **9件**（すべて `D6A1F8C3E5` の act1 floor7、deck 20-21枚）
- tier を **B / A / S** に変えても **決定変化 0件**（9件全部 Skip のまま）

理由は tier ではなく既存の Skip 規則だった。deck 20枚は act1 の `_large_deck_addition_allowed` の
limit（20）に達しており、`strong_block_shortage`（16枚以上・強ブロック3枚未満）が立つため、
コア・防御・必要ドロー以外は段位に関係なく Skip になる。`selected_tier` による Skip 規則より先に
効くので、tier を S に上げても届かない。

＝「tier 表の欠落が札を逃している」という仮説は、観測できた9件では **否定された**。
強ブロック不足規則に段位の逃げ道を作る変更は 2026-09-08 に16seedで有害測定済み（上の §124）で、
同じ扉を再度開く理由はこの計測からは出てこない。Dramatic Entrance・Production・Fasten は
observations を保存している run で一度も提示されていない（決定 trace 側には 9・8・1件ある）。

### Rampart の実装を commit 1 つだけ違えた arm/control 実走 A/B（2026-10-04、`data/rampart_ab.sh`）

control は親 commit `d67896f` の worktree（`.wt-ctrl-d67896f`）、arm は main checkout。差分は
`5f655ff` の1コミット（combat.py の grant と `POWER_NAMES` の1行）だけで、生成集合
（`STOKE_GENERATION`・`INFERNAL_BLADE_ATTACKS`）は両ツリー同一。だから生成プールをピン留めした
harness は不要で、`official_agent.py` をそのまま使う panel で分歧は grant の帰属に閉じる。
seed は同一条件 replay で分歧が多かった3件。

| seed | control | arm | delta | aligned | 分歧 | Rampart 位置の分歧 | 第一分歧 seq | 第一分歧で Rampart が両腕の state に在るか |
|---|---|---|---:|---:|---:|---:|---:|---|
| `H2LV6ZJ4XW` | 22勝1敗 | 20勝1敗 | **−2** | 390 | 59 | 6 | 426 | はい（arm BATTLE_TRANCE / control end_turn） |
| `B3N8V5T1WQ` | 16勝1敗 | 17勝1敗 | **+1** | 488 | 87 | 8 | 477 | はい（arm RUPTURE / control end_turn） |
| `D6A1F8C3E5` | 17勝1敗 | 17勝1敗 | **0** | 364 | 2 | 2 | 329 | はい（arm Defend / control Strike） |
| 合計 | 55勝 | 54勝 | **−1** | | | | | 3 seed すべて第一分歧が Rampart 位置 |

**分歧は机构単独で立っている**（3 seed すべて第一分歧の record で `POWER.RAMPART_POWER` が両腕の state に
出ており、その地点より前の決定列は一致）。つまりこれは「path が勝手にズレた」ではなく grant の差。

H2 の −2 の中身：arm は **SLIMED_BERSERKER 戦で6ターン目に HP17 で死亡**（敵残り106HP）。control は
同じ seed で QUEEN まで進み 400HP/20block のところで落ちている。arm の死亡はターのいる戦闘ではなく、
分歧後の path で別戦闘（CUBEX_CONSTRUCT を経由しない進み方）で耐久が足りなくなった形。
＝grant 自体が敵との打ち合いを悪くした証拠ではなく、**勝数への効果は符号が割れて母集団が薄い**
（−2 / +1 / 0）。閾値（≥3 seeds）に対して正の差は出ていない。

なので **Rampart の grant は正しさの修正として入れたまま、win-rate の改善根拠は無し** と記録する。
「忠実度を上げても勝てるとは限らない」の同一形（Wound 対応表・Stratagem と同じ位置）。
次はこの panel のまま他 seed を足して符号を見るか、grant の効果自体（盾を先に倒す価値）が決定に出る
位置を replay で特定する。

### 同じ監査で分かった ThievingHopper のコスト（未実装、母数確定）

`ThieveryMove` が Draw+Discard から1枚を `CardPileCmd.RemoveFromCombat` で戦闘から抜く（優先順
Uncommon → Common/Rare/Event → Basic/Quest → Ancient/Imbued、同一 rarity 内は random）。model は
これを全く見ていない。実走 record での検出：

- 奪取イベント **264件**（190 run、hand+draw+discard+exhaust の合計が1減る位置として検出）
- 奪われた札の内訳（268件）：Inflame 62・Battle Trance 33・Expect a Fight 32・Second Wind 14・
  Stratagem 11・Bludgeon 11 … **Strike は10件だけ**（Basic が第3優先なので最後まで抜かれない）
- うち **戦闘後に deck へ戻らないのは31件だけ**（233件は hopper を倒して extra reward で回収）
  → run あたりの恒久損失は 543 run 中31件 ≈ 0.06枚/run

戦闘中は毎回1枚抜かれるので rollout の「手札が揃う」前提が甘くなるが、恒久効果は小さい。
忠実度として入れるなら raritiy 表が要る（decompile から model 対象131札のうち **129札の rarity が
取得可能**：Uncommon 52・Rare 28・Common 20・Status 9・Event 8・Ancient 5・Curse 5・Basic 1・Token 1）。
Status/Token は `DeckVersion == null` なので候補から除外、Curse は deck 由来だと候補になる
（優先グループのどれにも入らないと full list が fallback）。

## Axebot の StockPower：1戦闘が Axebot 3体である事が model に見えなかった（2026-10-04、commit `03b2055`）

`Rampart` と同じ監査（`data/audit_trace_fidelity.py`）で、観測されるのに `POWER_NAMES` に無い power
として `POWER.STOCK_POWER`（MONSTER.AXEBOT、348 record / 14 run）が出た。decompile：

- `Axebot.AfterAddedToRoom`：`StockAmount > 0` なら自分に `StockPower(StockAmount)` を付与
  （`StockAmount => _stockOverrideAmount ?? 2`、export の values は `StockAmount: 2`）
- `StockPower.AfterDeath`：`Amount > 0` なら `axebot.StockAmount = Amount - 1` で **同じ side / 同じ slot に
  新しい Axebot を追加**し、`ShouldStopCombatFromEnding` で戦闘を終えない
- `GenerateMoveStateMachine`：`_stockOverrideAmount` が入った個体は **BOOT_UP_MOVE から**始まる
  （通常 spawn は HAMMER_UPPERCUT_MOVE から）
- `BOOT_UP_MOVE` の Strength は `BootUpStrGain * (2 - StockAmount)` → **個体ごとに 0 / 3 / 6**

model は export の `initial_state` と 1体の HP だけを持っていた。だから **1体を殺した瞬間に
`combat.terminal` になり**、戦闘全体を 76 HP 1体として評価していた。実走（`rampart_ctrl_b1_B3N8V5T1WQ`）
では 74 → 71 → 76 HP の3体が順に出た（combat_id 1 → 2 → 3、3体目だけ STOCK_POWER 無し）で、
その戦闘で 12 ターン使って 26/76 HP 残しで死亡している。

### 実装

- `initial_combat`：AXEBOT に `("StockPower", StockAmount)` を付与（他の「not exported」power と同じ形）
- `_mark_enemy_death`：`StockPower > 0` かつ hp <= 0 のとき BOOT_UP_MOVE で復活、HP は
  MaxInitialHp（game は MinInitialHp..MaxInitialHp から抽選だがこの関数に rng が届かない）、
  powers は空から `StockPower(amount-1)` のみ、`respawns` を1増やす
- `_enemy_turn`：`StockAmount` を **所持している StockPower の量**で上書き。
  1体目=2・2体目=1・3体目は power 無し=0 になるので、export の静的 2 を読むより個体の値になる
- `official_agent.POWER_NAMES` に `POWER.STOCK_POWER` を追加
- テスト2本：`test_axebot_respawns_from_stock_power_until_the_stock_runs_out`、
  `test_axebot_boot_up_strength_grows_with_each_stock_copy`（Strength 0/3/6）
- 回帰確認：親 commit `cd24b1f` の worktree では2本とも失敗（respawn せず、Strength `[0,0,0]`）
- suite **747件成功**

### 決定に出る母数（同一条件 replay、`data/attribution_rampart.py` を power 指定可能にした）

`POWER.STOCK_POWER` が state に出ている record を HEAD と親 commit で replay：

- records compared: **414**
- 決定変化: **135**（不変 279、例外 0）＝ **提示された decision の33%**
- seed 数: **4**（B3N8V5T1WQ 67、D6A1F8C3E5 33、R4A8D2K7ME 26、Q6N3V8K2MT 9）

Rampart（560件で63件）より大きく、分歧の形も「attack を attack で受ける ↔ block や potion に切り替える」
など戦闘全体の組み替え方向。実走 A/B は `data/axebot_ab.sh`（control = `cd24b1f` worktree、
arm = HEAD、seed 3件）。

### Axebot の respawn を commit 1 つだけ違えた arm/control 実走 A/B（2026-10-04、`data/axebot_ab.sh`）

control = 親 commit `cd24b1f` の worktree（`.wt-ctrl-cd24b1f`、Rampart まで入り、Axebot 無し）、
arm = HEAD `03b2055`。seed は replay で分歧が多かった3件。

| seed | control | arm | delta | 第一分歧 seq |
|---|---|---|---|---:|
| `B3N8V5T1WQ` | 17勝1敗 | 17勝1敗 | **0** | 548（arm Crimson Mantle / control Strike） |
| `D6A1F8C3E5` | 17勝1敗 | 17勝1敗 | **0** | 344（arm end_turn / control Shrug It Off） |
| `R4A8D2K7ME` | 21勝1敗 | 21勝1敗 | **0** | 455（arm Maul / control Perfected Strike） |
| 合計 | 55勝 | 55勝 | **0** | |

同一条件 replay で決定を135件動かした机构なのに、3 seed の勝敗は完全に同値。ただし中身は動いている：

- `B3` の死亡戦闘 SOUL_NEXUS（234HP）：control は 13ターンで **26HP 残し**、arm は **13HP 残し**
- `R4` の死亡戦闘 SLIMED_BERSERKER（261HP）：control は 57HP 残し・進入HP 19/72、arm は **5HP 残し**・進入HP 27/72
- 死亡した戦闘の種類は3 seed とも arm/control で同じ

＝respawn を見たことで「あと何ターンで倒せるか」の計算は実走に寄ったが、**胜ち負けの境界は超えない**。
Rampart の A/B（−2/+1/0）と合わせて、この session で入れた2つの忠実度修正は
**正しさの修正として入れたまま、win-rate の改善根拠は無し**。

### 同じ A/B で確認できた壁の実測（6 run の死亡戦闘）

| run | 死亡戦闘 | 進入HP | 与えた合計damage | 残り敵HP |
|---|---|---|---:|---:|
| arm `B3` | SOUL_NEXUS (234HP) | 101/101 | 221（17.0/turn） | 13 |
| ctrl `B3` | SOUL_NEXUS (234HP) | 106/106 | 208（16.0/turn） | 26 |
| arm `D6` | QUEEN+TORCH_HEAD_AMALGAM | 66/77 | 195 | QUEEN 370/400 |
| ctrl `D6` | QUEEN | 85/85 | 287（28.7/turn） | QUEEN 297/400 |
| arm `R4` | SLIMED_BERSERKER (261HP) | 27/72 | 253（42.2/turn） | 5 |
| ctrl `R4` | SLIMED_BERSERKER (261HP) | 19/72 | 201（33.5/turn） | 57 |

`SOUL_NEXUS` は model 側で完全に見えている（block 0・攻撃3種のみに観測一致：SoulBurn 29 /
Maelstrom 6x4=24 / DrainLife 18+Vulnerable+Weak、234HP）。**満タンのHP101で入って13ターン戦って
13HP 残しで死ぬ**形なので、これは model の欠落ではなく deck の火力不足。
全 trace 545 本の死亡戦闘の内訳：THE_INSATIABLE 203、QUEEN(+TORCH_HEAD) 101、VANTOM 53、
EYE_WITH_TEETH+FOGMOG 20、DECIMILLIPEDE 17、OVICOPTER+TOUGH_EGG 16、PARAFRIGHT+THE_OBSCURA 14。

### 同じ監査で「gap ではなかった」事を確認した項目（2026-10-04、再調査の手間を省くための記録）

- `POWER.ESCAPE_ARTIST_POWER`（ThievingHopper、2,911 record）：decompile 上は逃走タイマーの表示だけ
  （`AfterSideTurnEnd` で Decrement）。逃走自体は `ESCAPE_MOVE` の `CreatureCmd.Escape` として
  5ターン目に model 側でも発動する（state machine が THIEVERY→FLUTTER→HAT_TRICK→NAB→ESCAPE 固定）。**モデル化不要。**
- `POWER.REATTACH_POWER`（Decimillipede、1,206 record）：`DoReattach` の `CreatureCmd.Heal(Amount=25)` は
  combat.py の `REATTACH_MOVE` 分岐で既に +25 として入っている。実走の復活 HP も 22-25 で一致。
- `POWER.HATCH_POWER`（ToughEgg、2,422 record）：`AfterSideTurnEnd` で Decrement するだけで、
  HP 変化（HatchlingMinHp..MaxHp）は `Hatch()` 側。combat.py の `HATCH_MOVE` 分岐が既に処理済み。
- `POWER.POSSESS_STRENGTH_POWER` / `POSSESS_SPEED_POWER`（TheLost / TheForgotten）：player への
  -2 debuff と自分の +2 両方が export 済み。未モデル化なのは「 holder が死んだ時に player へ Strength が
  戻る」だけ（player に有利な方向、死亡戦闘の上位14にこの2体は無い）。
- `MONSTER.SOUL_NEXUS`（234HP、今回の A/B で2 run が死亡）：block を持たず攻撃3種のみの観測と一致し、
  漏れ無い（SoulBurn 29 / Maelstrom 6x4 / DrainLife 18 + Vulnerable + Weak）。
- `R4A8D2K7ME` の Act 3 は **分岐の無い廊下**だった（Ancient(0,3)→Monster(1,1)→(2,2)→(3,2)→Unknown(4,2)→
  Monster(5,2)→(6,1)、各行の children が1つ）。act 内の RestSite は (6,5)(8,1)(8,5)(10,4)(11,3)(15,0)(15,3) で、
  廊下の列（col 1-2）には無い。＝「 elite 前に rest を取れていれば残り5HPの死を避けられた」は
  **経路上に rest が無いので実現不能**。rest 経路の重量付け自体は closed lever（§148 §150 §249 §2348）。

## ThievingHopper のカード奪取（2026-10-04、commit `119cb28`）

`ThieveryMove` の本体は export されず、state machine には `"swipe"` の PowerCmd.Apply マーカーと
17ダメージの攻撃だけが出る。C# 本体は攻撃の前に player の **Draw+Discard から1枚を
`CardPileCmd.RemoveFromCombat` で戦闘から抜く**（候補は `DeckVersion != null` の札だけ、優先順
Uncommon → Common/Rare/Event → Basic/Quest → Ancient/Imbued、同一 rarity 内は random、
どのグループにも入らない場合は full list が fallback）。model はこれを全く見ていなかった。

実装：`_enemy_turn` の THIEVERY_MOVE で draw+discard から1枚抜く。抜く順は **Strike/Defend を最後**
にする近似（model には札ごとの rarity が無い）。実走 268件の奪取の内訳が根拠：
Inflame 62・Expect a Fight 33・Battle Trance 33・Second Wind 14・Stratagem 11・Bludgeon 11・
Rupture 10・Stone Armor 10 … **Strike は10件だけ**（Basic は第3優先）、Status/Token 札は1件も無い
→ 定数 `NON_DECK_CARDS`（Slimed・Toxic・Burn・Dazed・Infection・Wither・Decay・Wound・
Frantic Escape・Giant Rock）を候補から除外して一致させる。

回帰：`cd24b1f`（親）では2本とも失敗（抜かれない）。suite **749件成功**。

母数（`data/attribution_rampart.py` に monster id 指定を追加）：`MONSTER.THIEVING_HOPPER` の
record **2964件** replay → **決定変化 189件・34 seed**（AM8C6YXHSG 34、M5PC8TQ3BN 26、
H2LV6ZJ4XW 25、P3V8N5K2RX 13 …）。恒久的なデッキ喪失は 543 run 中31件だけなので、
効果は「その戦闘の rollout が1枚少ない前提で計算される」範囲に留まる。

## Rampart の 2nd panel（新3 seed、`data/rampart_ab2.sh`）

arm = `cd24b1f`（Rampart あり）、control = `d67896f`（親）。`5f655ff` 1コミットだけの差分のまま
新しい seed を足した。

| seed | control | arm | delta | 判定 |
|---|---|---|---:|---|
| `SOS6XYXCNO` | 13勝1敗 | 13勝1敗 | 0 | 2 run とも LivingShield 戦に入らず＝**測定不能** |
| `9X9WQB4QIH` | 17勝1敗 | 17勝1敗 | 0 | Rampart record 6件/6件、**分歧そのものが無し** |
| `R4A8D2K7ME` | 21勝1敗 | 21勝1敗 | 0 | 第一分歧 seq 411（arm Defend / control Maul）、Rampart 位置 |

1st panel と合わせて **6 seed で −2 / +1 / 0 / 0 / 0 / 0（合計 −1）**。replay で63件動く机构だが、
実走では6 seed 中4 seed が无変化、1 seed だけ −2、1 seed だけ +1。
忠実度修正の勝敗効果はこのサイズだと panel で検出できない、が今回の実測の結論。

## 敵側 PlatingPower の実装と、その修正が勝敗を**下げた**実走 A/B（2026-10-04、commit `ca5bd71`）

`FrogKnight.AfterAddedToRoom` / `SlumberingBeetle.AfterAddedToRoom` は `Plating(PlatingAmount=15)` を
自分にかける（export されない）。PlatingPower は

- `BeforeSideTurnStart`：RoundNumber == 1 の間、player サイドのターン開始時に Block = Amount（＝格闘者は
  15 block を持って戦闘を開始する）
- `BeforeSideTurnEndEarly`：自分のターン終了時に Block = Amount を再付与
- `AfterSideTurnStart`：2ラウンド目以降、amount を Decrement.BaseValue（solo では 1）だけ減らす

combat.py は **player 側の PlatingPower しか扱っていなかった**（Iron Unpinion 等の付与）ため、
FrogKnight（191HP、glory）と SlumberingBeetle（86HP、hive）の戦闘で毎ターン 15→14→13…と再生成される
block が rollout から完全に抜けいていた。実走観測は model の想定と一致する：plated Frog Knight の
amount と Block は player turn 1..9 で **15, 15, 14, 13, 12, 11, 10, 9, 8**（各 turn の最大 Block）。
実装後は同一の系列を model も再現する（`test_plated_enemy_re_grants_block_every_turn_and_its_plate_thins`）。
回帰：親 commit `119cb28` の worktree ではこのテストが失敗（`(0,0) != (15,15)`）。suite **751件成功**。

母数：`MONSTER.FROG_KNIGHT` の record **1489件** replay → **決定変化 368件（25%）・8 seed**
（H2LV6ZJ4XW 194、X3C9N6P4WQ 60、R4A8D2K7ME 46、T5R8K2N9QP 20 …）。これまでで最大の母数。

### 実走 A/B（arm = HEAD、control = 親 `119cb28`）

| seed | control | arm | delta | 第一分歧 seq | 分歧地点で Plating が両腕の state に在るか |
|---|---|---|---:|---:|---|
| `H2LV6ZJ4XW` | 22勝1敗 | 20勝1敗 | **−2** | 265 | はい（arm **Defend** / control **Uppercut**） |
| `X3C9N6P4WQ` | 13勝1敗 | 13勝1敗 | 0 | なし（**run が完全に一致**） | 46/46 record |
| `R4A8D2K7ME` | 21勝1敗 | 13勝1敗 | **−8** | 245 | はい（arm **Iron Wave** / control **Uppercut**） |
| 合計 | 56勝 | 46勝 | **−10** | | |

**忠実度修正が勝敗を明確に下げた最初の例。** 死因も変わった：

- arm `H2`：SLIMED_BERSERKER に進入 HP 41/110 で死亡（control は QUEEN まで行って 43/400 残し）
- arm `R4`：OVICOPTER+TOUGH_EGG に **進入 HP 12/72** で死亡（control は SLIMED_BERSERKER で 5HP 差）
- arm `R4` の Plating record は 10件（control 139件）＝ **arm は plating 戦闘を大きく避けています**

原因の形が分歧に直接出ている：第一分歧で arm は攻撃（Uppercut）をやめてブロック札
（Defend / Iron Wave）を打っている。15 block を毎ターン再生成する敵に対してブロックを積むのは
テンポの純損失で、戦闘が伸びるだけ。＝**model が正確になった結果、agent の「長い戦闘で何を打つか」の
選び方が悪いことが見えた**。修正を戻す理由にはならない（model は game と一致すべき）が、
この戦闘種族に対する play の作り直し（plated 敵にはブロックを積まない／Weak・Vulnerable で支える）は
新しい測定対象として残る。routing 側も同じで、elite の HP コスト定数（`Monster*17 + Elite*32`）は
plating の分だけ重いはず、という指摘はこの計測から出る（§148 の closed lever を開け直す根拠になる）。

なお control の H2 22勝は `119cb28`（Rampart+Axebot+Hopper）まで入った値で、`cd24b1f` の 20勝から
**Axebot・Hopper 修正で +2** している。同一 seed の系列として追跡可能。

## Decimillipede の move 本体（export に effects が無い）と、そこから出た次の gap（2026-10-04）

「intents だけあって effects が空の MoveState」を export 全体から数えた：DECIMILLIPEDE_SEGMENT
front/middle/back（各3手）、BYGONE_EFFIGY(2)、KNOWLEDGE_DEMON(1)、ROCKET(1)、SLUMBERING_BEETLE(1)、
LAGAVULIN_MATRIARCH(1) の8体。攻撃力は intent から synthetic DamageCmd で補われているが、
C# 本体にしかない効果は落ちていた。`DecimillipedeSegment`：

- `BulkMove`：攻撃（BulkDamage 6）に加えて自分に `StrengthPower(BulkStrength = 2)`
- `ConstrictMove`：攻撃（ConstrictDamage 8）に加えて player に `WeakPower(1)`
- `WritheMove`：5 x2 攻撃（state 順は WRITHE → CONSTRICT → BULK の循環）

実走では segment の Strength が turn 1 で 0、turn 2 以降で 2、turn 5 以降で 4（player の Weak も
turn 2 から 285 record 出现）→ 効果自体は観測と一致。commit 後 model も同じ系列になる
（`test_decimillipede_bulk_gains_strength_and_constrict_applies_weak`、親 commit `119cb28` では失敗）。
suite **752件成功**。

### 同じ調査で特定した次の gap：player の debuff tick が1手早い／Frail が全く減らない

`step()` の END_TURN 遷移（combat.py 2040-2055 付近）は `_enemy_turn` の**後に**
player の VulnerablePower / WeakPower を `_tick_down_power` している。だから敵のターンで付いた
debuff が同じ遷移内で1減って、player の次のターンに届かない。FrailPower は tick 箇所が**存在しない**
（使用箇所の grep で 2 件だけ：計算と Shame による付与）。実走の Axebot 戦闘（単独・clean）での
player 側 Weak / Frail：

| player turn | Axebot の手 | Weak | Frail | record 数 |
|---:|---|---:|---:|---:|
| 1 | HAMMER_UPPERCUT（まだ手前） | 0 | 0 | 76 |
| 2 | BOOT_UP / ONE_TWO | **2** | **2** | 13 / 68 |
| 3 | HAMMER_UPPERCUT / BOOT_UP | **1** | **1** | 61 / 19 |
| 4 | ONE_TWO | 3・2 | 2 | 20 / 27 |

game は「敵サイドのターン終了時に 1 減る」で、**そのターンに付いた分は減らない**（turn 2 で 2、
turn 3 で 1、2回目の Uppercut で 1+2=3）。model は turn 2 で Weak 1（先に減らす）／Frail は 2 のまま
減らない。実装の形は player 側の Weak/Vulnerable/Frail の tick を敵ターンより前に移し、
enemy 側の Vulnerable/Weak は今の位置（敵ターン後）に置く分岐、になる。
対象は広い（THE_INSATIABLE の player Vulnerable は 6633 record、SOUL_NEXUS の DrainLife が
Vulnerable 2 + Weak 2、Axebot の Uppercut が Weak 2 + Frail 2、Decimillipede、VANTOM、QUEEN …）。
これは次ラウンドの実装候補として一番母数が大きい。

## player debuff の tick が1手早く、Frail が全く減っていなかった（2026-10-04、commit `7ec2a06`）

`WeakPower` / `VulnerablePower` / `FrailPower` の tick は decompile で3つとも同じ形：

```csharp
public override async Task AfterSideTurnEnd(...) { if (side == CombatSide.Enemy) await PowerCmd.TickDownDuration(this); }
```

＝**敵サイドのターン終了時に1減る**（player 所有でも enemy 所有でも）。combat.py は END_TURN 遷移で
`_enemy_turn` の**後に** player の Vulnerable/Weak を減らしていたため、敵のターンで付いた stack が
同じ遷移内で消え、player の次のターンに届かなかった。FrailPower は tick する箇所が**存在しなかった**
（`grep FrailPower combat.py` は使用箇所の2件だけ）。

実走で決まる2つの事実：

1. 敵がそのターンに付した debuff は、そのターンの tick を受けけない（Axebot の Hammer Uppercut
   Weak 2 / Frail 2 → player turn 2 で **2 / 2**、turn 3 で **1 / 1**）
2. player 側に既に乗っていた debuff は、敵の攻撃に効いた後に減る（Waterfall Giant の EXPLODE 22
   ダメージは Vulnerable 1 が生きていてこそ。`test_rollout_preserves_waterfall_steam_damage_from_observed_explode_intent`
   がこの順番を壊す実装で 58 → 65 HP になって失敗した）

実装：END_TURN で**敵フェーズの前に**「すでに走っていた debuff」の集合を記録し（player と各 enemy）、
敵フェーズの後にその集合だけを `_tick_down_power` する（`DEBUFF_POWERS` と `_tick_debuffs`）。
フェーズ中に付いた分は減らないので player の次のターンまで生き、Frail も減り始める。
model の Axebot 系列は turn 2 = 2/2、turn 3 = 1/1、turn 4 = 2/2（1+2 から1減らして2）で実走と一致。
回帰テスト `test_enemy_applied_debuffs_survive_the_turn_that_applied_them`（親 commit では失敗）、
suite **753件成功**。

母数（replay ではなく観測露出で数えた）：combat record 148,905 件のうち **15,343 件**で player が
Weak / Vulnerable / Frail を持っており、**552 run 中 432 run** に現れる。
内訳 FRAIL 8,322・WEAK 4,490・VULNERABLE 2,531。Frail はPreviously 永久に乗る側へ狂っていたので、
この432 run で block の見積もりが系統的に狂っていたことになる。実走 A/B は `data/debuff_ab.sh`
（露出上位3 seed：B3N8V5T1WQ 153、SOS6XYXCNO 129、D6A1F8C3E5 127）。

### debuff tick 修正の実走 A/B（2026-10-04、`data/debuff_ab.sh`）

arm = HEAD `7ec2a06`、control = 親 `0aa9a71`（worktree）。露出上位3 seed。

| seed | control | arm | delta | 死亡戦闘 | arm/control の player debuff record 数 |
|---|---|---|---:|---|---|
| `B3N8V5T1WQ` | 19勝1敗 | **20勝1敗** | **+1** | QUEEN+TORCH_HEAD_AMALGAM（arm 8T/残り QUEEN 393、ctrl 6T/392） | 164 / 160 |
| `SOS6XYXCNO` | 13勝1敗 | 13勝1敗 | 0 | THE_INSATIABLE（arm 残り96HP、ctrl 残り22HP） | 16 / 11 |
| `D6A1F8C3E5` | 17勝1敗 | 17勝1敗 | 0 | arm は QUEEN のみ（TORCH_HEAD を殺しきった）、ctrl は QUEEN+TORCH_HEAD | 145 / 127 |
| 合計 | 49勝 | **50勝** | **+1** | | |

分歧の数は B3 で 537 对齐中 412、D6 で 359 中 103 と大きい。ただし**第一分歧の record には player の
debuff が出ていない**（B3 seq 73、SOS 193、D6 342 で player powers は空）＝この修正の差は観測状態そのもの
ではなく **rollout 内の将来の tick** に現れる。だから「分歧が debuff 付き record に居る数」
（B3 173件、D6 88件、SOS 0件）を以って帰属の根拠にはできない。分歧の帰属をクローズするには
同一 record replay（`data/attribution_rampart.py PLAYER:POWER.WEAK_POWER,...`）を act 別の enemy data
（またはマージした data）で回す必要がある。

同じ seed 系列での忠実度修正の累計は追跡できる：`B3N8V5T1WQ` は
`d67896f` 16勝 → Rampart 17勝 → Axebot・Hopper・Decimillipede 19勝 → debuff tick **20勝**。
まだ Act 3 は踏破していない（QUEEN 400HP が残る）。SOS6XYXCNO の THE_INSATIABLE 戦では arm の方が
**96HP 残し**で負けており（control 22HP 残し）、tick 修正が必ずしも boss 戦を有利にしていない面もある。
