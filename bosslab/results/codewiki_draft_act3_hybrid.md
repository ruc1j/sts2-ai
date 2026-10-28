# 追記草稿（docs/CODEWIKI.md へ移す想定）

口調は既存の日付節（`## 2026-10-13: Act 2ボス突破のためのデッキ構築の検証` など）に合わせた。各項目は
「**結論** → 原因 → 効き → 回避策 + 根拠（デコンパイル file:line / commit）」の順。引用した file:line は
デコンパイル済みソース（`MegaCrit.Sts2.Core.Models.Relics/*.cs` と `...Models.Enchantments/Goopy.cs`）で
中身を確認した。忠実性の具体値は `bosslab/results/confirm3_fixed_fidelity.md`（修正前の照合）と
`act3_confirm4_fidelity.md`（927f26f 反映後）に対応を確かめた。

## 2026-10-28: Act 3 hybrid ラボの忠実性の落とし穴（遺物の入場時効果）

**BossLab は run を組んだあと `RunManager.EnterRoomDebug` でいきなりボス室へ入るので、注入した遺物自身の入場
hook が走る。** 多くの遺物（Vajra の力、Gorget の Plating 等）は recorded entry も同じ hook で作られたので再発火
がちょうど再現になる。だが次の 6 系統は recorded deck / HP / ポーション / 手札が既にその変更を含んでいるため、
同じ操作を二重に適用するか、lab 側が復元できない per-run 状態に依存して、忠実性チェックの不一致に出る。
入場時効果が記録済みの状態と食い違う遺物は、`bosslab/tools/relic_entry_effects.py`（handling 4 種）と
`relic_run_state.json` に一覧として登録し、plan 生成側で処理か除外を決める。**

### STONE_CRACKER（`defer_relics`）

- **結論**: 入室 hook を走らせないよう `defer_relics` を付けて入室後に付与する。ただし defer の副作用で開戦手札の
  中身が実走とずれるので、判定は deck multiset と中盤以降の状態で行い、開戦手札の構成・枚数の差は無視する。
- 原因: `RELIC.STONE_CRACKER` は `AfterRoomEntered`（StoneCracker.cs:20-28）でアップグレード可能なカード 2 枚を
  強化し、その前に `StableShuffle(CombatCardSelection)` を引く。lab が入室 hook で再発火させると、別の 2 枚が上がって
  抽選順も変わり、開戦手札がずれる。recorded deck は既に強化済み。
- 効き: defer すると同じ箇所の `StableShuffle(CombatCardSelection)`（StoneCracker.cs:25）が入室 hook で開戦手札の
  RNG stream を消費しなくなり、deck の総枚数と各札の cost/値は一致するが、引かれる札だけ実走と違う。
- 回避策: `relic_entry_effects.py` の `defer_relic_addition` で入室後に付与。confirm3_fixed（`131a5a0` まで）の
  照合では deck 31 枚の multiset と各札の cost/Block・Damage は一致し、引かれる札の実走差のみ（`confirm3_fixed_fidelity.md`
  trial_0002 spec 83e6a3465fde）。その trial の初手構成差は戦略でなく注入の帰結なので、判定では開戦手札の構成・枚数差を
  無視する（同じ entry の base / 候補間配対では両腕に同じ制約）。

### PHIAL_HOLSTER（ポーション枠の再計算）

- **結論**: 枠を recorded potion list に合わせて広げる。遺物既定の 3 枠で計算し直すと recorded のポーションが落ちる。
- 原因: `RELIC.PHIAL_HOLSTER`（PhialHolster.cs:26-28）は `AfterObtained` で `GainMaxPotionCount`（PotionSlots var 1）を
  上げるが、silent な遺物追加は `AfterObtained` を走らせない。記録 entry には既に追加枠とその取得時ポーション 2 本が
  入っている。
- 効き: 3 枠の上限のままだと recorded potion list の超過分が捨てられて入場ポーションが減る。POTION_BELT・
  ALCHEMICAL_COFFER も同じ型。
- 回避策: `relic_entry_effects.py` の `widen_potion_slots` で recorded potion list に合わせて枠を広げる（再計算しない）。

### PANTOGRAPH / ROYAL_POISON（HP 再適用の位置）

- **結論**: recorded HP の再適用は「入室後」でも「run 開始前」でもなく、エージェント初手判断の直前に 1 回だけ行う。
- 原因: `RELIC.PANTOGRAPH`（Pantograph.cs:27-32、`BeforeCombatStart` で `CreatureCmd.Heal`）など回復系は recorded
  entry HP が既に回復後。一方 `RELIC.ROYAL_POISON`（RoyalPoison.cs）は最初のプレイヤーターン開始
  （AfterPlayerTurnStart、TurnNumber≤1）で自分へブロック不能 4 ダメージを与えるが、入場観測はその hook 前に取られて
  いるので記録 HP に含まれていない。
- 効き: `131a5a0` のように戦闘開始確定後・run 前に Reapply すると、Reapply（記録 90）→ run 内 RoyalPoison −4 →
  86 となって、記録に本来無い 4 を二重に引く。confirm3_fixed の照合で trial_0004（spec 1a05bb73e94b）と
  trial_0010（spec 59ed603b4b73）が lab 86 / 記録 90 と一致（`confirm3_fixed_fidelity.md`）。全レリック走査でターン
  開始に自分の HP を削るのは RoyalPoison のみ。
- 回避策: commit `927f26f`。CombatBridge に使い切りの `FirstDecisionHook`（開戦手札が配られ、かつ当ターンの
  AfterPlayerTurnStart が完了した後の最初の Play フェーズで 1 度だけ発火、AutoSlay では常時 null）を足し、BossLab は
  run 前に `ReapplyRecordedHp` をそこへ設定（戦闘が判断に到達せず終わる備えに finally で消す）。これで RoyalPoison の
  ターン 1 自己被ダメージ着地後に記録 HP が維持される。927f26f 反映後の confirm4 base 照合では RoyalPoison を持つ
  spec 2 件（c589d7860c35・59ed603b4b73）で入場 HP が記録に一致（`act3_confirm4_fidelity.md`）。レリックの
  ホワイトリストは持たない。

### PENDULUM（カウンタ）

- **結論**: plan から明示除外する。カウンタが trace に出ない per-relic の run 状態だから。
- 原因: `RELIC.PENDULUM`（Pendulum.cs:75-84、CanonicalVars の Turns=3m は同 file:43）は `[SavedProperty] TurnsSeen` が
  3 ターン周期で 0 に戻る最初のターン開始で 1 枚引く。実走のボス入室ではカウンタが周期の直前値なので初ターン開始に
  引いて入室手札 6 枚、lab は新規レリック（TurnsSeen=0）で引かず 5 枚（`Pendulum.cs:79` の wrap と `:84` の Draw で確認、
  枚数差は confirm3_fixed trial_0002 spec 83e6a3465fde の hand 5/6）。
- 効き: 引く/引かないが初手判断のカード枚数そのものを変える。`scan_relic_run_state.py` は当初 AfterPlayerTurnStart を
  見ず「初手判断に影響なし」と誤分類し、自動除外されず panel に残った。
- 回避策: 走査に AfterPlayerTurnStart を追加（commit `c6a4ac7`）＋ plan 側で `--exclude-relic RELIC.PENDULUM`。

### PAELS_CLAW / Goopy（プレイ回数）

- **結論**: plan から明示除外する。Goopy の Amount が per-card の run 状態で trace に出ないから。
- 原因: `RELIC.PAELS_CLAW`（PaelsClaw.cs:32-43）は `AfterObtained` で deck の enchant 可能な札に
  `ENCHANTMENT.GOOPY` を付与する。Goopy を浴びた Defend の block は「基礎 + (Amount − 1)」で、Amount はその札の
  プレイ回数で増える（`MegaCrit.Sts2.Core.Models.Enchantments/Goopy.cs:30-46`、`AfterCardPlayed` で Amount++、
  `EnchantBlockAdditive` が `Amount - 1` を返す）。trace は Amount を出さず hand の block としてしか見せない。
- 効き: run 中で先にプレイ済みの強化済み Defend は、lab が新規に付与した複製（Amount=1）より入場時の block が多くなる。
  ただし Amount 自体が trace に出ないため、具体的な block 値は lab で再現・照合できない（数値例は出さない）。
- 回避策: spec 抽出の `[SavedProperty]` フィルタは遺物本体でなく札側に状態がある PAELS_CLAW を捕捉できないので、
  `--exclude-relic RELIC.PAELS_CLAW` で plan から落とす。

### CROSSBOW（開戦手札のランダム配布）

- **結論**: plan から除外する（`flag_relics` で†を付けて判定から除く）。ゲーム側 RNG が作る札なので lab が同じ札を
  同じ位置に出せる保証がない。
- 原因: `RELIC.CROSSBOW`（Crossbow.cs:17-36）は `AfterSideTurnStart` で、解放済みのランダム Attack 1 枚を
  `GetDistinctForCombat` で選び手札へ足す。lab の RNG が選ぶ札と挿し位置は実走と一致せず、hook 前に取った入場観測に
  その札自体が無い。
- 効き: TOOLBOX・BIG_HAT・ORANGE_DOUGH・POWER_CELL・BLESSED_ANTLER・FUNERARY_MASK・JEWELED_MASK・RADIANT_PEARL など
  `flag_unfixed` 族も同じ性質（入室 hook か初ターンの開始・ドローでゲーム側 RNG が札を生む）。
- 回避策: `relic_entry_effects.py` の `flag_unfixed` として登録し、plan 生成で `flag_relics` に載せて analyze_bosslab.py
  が†で印すか、plan から除外。confirm3_fixed plan の `flag_relics` は `RELIC.CROSSBOW` 1 件（`bosslab_act3_plan_confirm3_fixed.json`）。
  CROSSBOW を除いた判断を `flag_unfixed` 族すべてへ拡張する。confirm3_fixed trial_0011（spec bbbfd4fc2927）は CROSSBOW と
  PAELS_CLAW・PHIAL_HOLSTER を併せ持ち、照合に deck.multiset の `CARD.STOMP+0+` 追加と draw_pile 差が出た。CROSSBOW は
  hand へ生成札を足すだけで deck multiset を変えないため、この deck 差がどの hook 由来かは特定できていない（複数系統が
  同居する trial。いずれも plan で除外印済み）。

**総則**: 入場時に自分の HP を直接削る遺物は RoyalPoison のみと確認済みなので、HP 再適用は初手判断直前の 1 回で
足りる（ホワイトリスト不要）。開戦手札の RNG・カウンタ・per-card の Amount のように trace に出てない per-run 状態に
依存する遺物は、lab では復元不能なので plan 側で除外し、忠実性レポート（`bosslab/tools/confirm_fidelity_report.py`）で
残留を確認する。
