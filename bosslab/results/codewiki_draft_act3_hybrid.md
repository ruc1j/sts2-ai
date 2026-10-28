# 追記草稿（docs/CODEWIKI.md へ移す想定）

口調は既存の日付節（`## 2026-10-13: Act 2ボス突破のためのデッキ構築の検証` など）に合わせた。各項目は
「**結論** → 原因 → 効き → 回避策 + 根拠（デコンパイル file:line / commit）」の順。

## 2026-10-28: Act 3 hybrid ラボの忠実性の落とし穴（遺物の入場時効果）

**BossLab は run を組んだあと `RunManager.EnterRoomDebug` でいきなりボス室へ入るので、注入した遺物自身の
入場 hook が走る。** 多くの遺物（Vajra の力、Gorget の Plating 等）は recorded entry も同じ hook で作られた
ので再発火がちょうど再現になる。だが次の 6 系統は recorded deck / HP / ポーション / 手札が既にその変更を
含んでいるため、同じ操作を二重に適用するか、lab 側が復元できない per-run 状態に依存して、忠実性チェックの
不一致に出る。**入場時効果が記録済みの状態と食い違う遺物は、`bosslab/tools/relic_entry_effects.py`
（handling 4 種）と `relic_run_state.json` に台帳として持ち、plan 生成側で処理か除外を決める。**

### STONE_CRACKER（`defer_relics`）

- **結論**: 入室 hook を走らせないよう `defer_relics` を付けて入室後に付与する。ただし defer の副作用で開戦手札の中身が実走とずれるので、判定は deck multiset と中盤以降の状態で行い、開戦手札の構成・枚数の差は無視する。
- 原因: `RELIC.STONE_CRACKER` は `AfterRoomEntered`（StoneCracker.cs:20-28）でアップグレード可能な抽選 2 枚を升目し、その前に StableShuffle を引く。lab が入室 hook で再発火させると、別の 2 枚が上がって抽選順も変わり、開戦手札がずれる。recorded deck は既にアップグレード済み。
- 効き: defer すると `StableShuffle(CombatCardSelection)`（同じ箇所）が入室 hook で開戦手札の RNG stream を消費しなくなり、**deck の総枚数と各札の cost/値は一致するが、引かれる札だけ実走と違う**。
- 回避策: `relic_entry_effects.py` の `defer_relic_addition` で入室後に付与（confirm3_fixed で deck multiset と札の cost/値は一致、T21.3）。この panel で影響は 1 trial（spec 1563989f9e55）。その trial の初手構成差は戦略でなく注入の帰結なので、判定では開戦手札の構成・枚数の差を無視する。

### PHIAL_HOLSTER（ポーション枠の再計算）

- **結論**: 枠を recorded potion list に合わせて広げる。遺物既定の 3 枠で計算し直すと recorded のポーションが落ちる。
- 原因: `RELIC.PHIAL_HOLSTER`（PhialHolster.cs:26-28）は `AfterObtained` で `GainMaxPotionCount`（PotionSlots var 1）を上げるが、silent な遺物追加は `AfterObtained` を走らせない。記録 entry には既に追加枠とその取得時ポーション 2 本が入っている。
- 効き: 3 枠の cap のままだと recorded potion list の超過分が捨てられて入場ポーションが減る。POTION_BELT・ALCHEMICAL_COFFER も同じ型。
- 回避策: `relic_entry_effects.py` の `widen_potion_slots` で recorded potion list に合わせて枠を広げる（再計算しない）。

### PANTOGRAPH / ROYAL_POISON（HP 再適用の位置）

- **結論**: recorded HP の再適用は「入室後」でも「Run 開始前」でもなく、エージェント初手判断の直前に 1 回だけ行う。
- 原因: `RELIC.PANTOGRAPH`（Pantograph.cs:27-32、BeforeCombatStart で CreatureCmd.Heal）など回復系は recorded entry HP が既に回復後。一方 `RELIC.ROYAL_POISON`（RoyalPoison.cs）は最初のプレイヤーターン開始（AfterPlayerTurnStart、TurnNumber≤1）で自分へブロック不能 4 ダメを当てるが、入場観測はその hook 前に取られているので記録 HP に含まれていない。
- 効き: `131a5a0` のように戦闘開始確定後・Run 前に Reapply すると、Reapply（記録 90）→ Run 内 RoyalPoison −4 → **86** となって、記録に本来無い 4 を二重に引く（confirm3_fixed 再走 trial 0004 / 0010 で lab 86 / 元 90）。全レリック走査でターン開始に自分の HP を削るのは RoyalPoison のみ。
- 回避策: commit `927f26f`。CombatBridge に使い切りの `FirstDecisionHook`（開戦手札配了かつ当ターンの AfterPlayerTurnStart 完了後の最初の Play フェーズで 1 度だけ、AutoSlay では常時 null）を足し、BossLab は Run 前に `ReapplyRecordedHp` をそこへ設定（戦闘が判断に到達せず終わる備えに finally で消す）。これで 0007 は 114→90、0004/0010 は RoyalPoison 着地後の 90 を維持、回復なし組も記録値に着地。レリックのホワイトリストは持たない。

### PENDULUM（カウンタ）

- **結論**: plan から明示除外する。カウンタが trace に出ない per-relic の run 状態だから。
- 原因: `RELIC.PENDULUM`（Pendulum.cs:75-90）は `[SavedProperty] TurnsSeen` が 3 ターン毎に 0 へ wrap した最初のターン開始で 1 枚引く。実走はボス入室時にカウンタ 2 なので初ターン開始に引いて入室手札 6、lab は新規レリック（TurnsSeen=0）で引かず手札 5。
- 効き: 引く/引かないが初手判断のカード枚数そのものを変える。`scan_relic_run_state.py` は本来 AfterPlayerTurnStart を見ず「初手判断に影響なし」と誤分類し、自動除外されず panel に残った。
- 回避策: 走査に AfterPlayerTurnStart を追加（commit `c6a4ac7`）＋ plan 側で `--exclude-relic RELIC.PENDULUM`。

### PAELS_CLAW / Goopy（プレイ回数）

- **結論**: plan から明示除外する。Goopy の Amount が per-card の run 状態で trace に出ないから。
- 原因: `RELIC.PAELS_CLAW`（PaelsClaw.cs:30-46）が配る `ENCHANTMENT.GOOPY` を浴びた Defend の block は「基礎 + (Amount − 1)」、Amount はその札のプレイ回数で増る（Goopy.cs:28-42、EnchantBlockAdditive = Amount − 1）。trace は Amount を出さず hand の block としてしか見せない。
- 効き: run 中で先にプレイ済みの強化済み Defend は、lab が freshly-enchanted した複製より入場時の block が多い（実測 block 5 vs 7、T21.2）。
- 回避策: spec 抽出の `[SavedProperty]` フィルタは遺物本体でなく札側に状態がある PAELS_CLAW を捕まらないので、`--exclude-relic RELIC.PAELS_CLAW` で plan から落とす。

### CROSSBOW（開戦手札のランダム配布）

- **結論**: plan から除外する（`flag_relics` で印を付け判定から除く）。ゲーム側 RNG が作る札なので lab が同じ札を同じ位置に出せる保証がない。
- 原因: `RELIC.CROSSBOW`（Crossbow.cs:17-36）は `AfterSideTurnStart` で解放済みのランダム Attack 1 枚を手札へ足す。lab の RNG が選ぶ札と挿し位置は実走と限らず、hook 前に取った入場観測にはその札自体が無い。
- 効き: TOOLBOX・BIG_HAT・ORANGE_DOUGH・POWER_CELL・BLESSED_ANTLER・FUNERARY_MASK・JEWELED_MASK・RADIANT_PEARL など `flag_unfixed` 族も同じ性質（入室 hook か初ターンの開始・ドローでゲーム側 RNG が札を生む）。
- 回避策: `relic_entry_effects.py` の `flag_unfixed` として台帳に載せ、plan 生成で `flag_relics` に載せて analyze_bosslab が†で印すか、plan から除外。leader が CROSSBOW を除いた判断を `flag_unfixed` 族すべてへ拡張（この panel の flag_relics は 0 件＝除外済み）。

**総則**: 入場時に自分の HP を直接削る遺物は RoyalPoison のみと確認済みなので、HP 再適用は初手判断直前の 1 回で足りる（ホワイトリスト不要）。開戦手札の RNG・カウンタ・per-card の Amount のように trace に出てない per-run 状態に依存する遺物は、lab では復元不能なので plan 側で除外し、忠実性レポート（`bosslab/tools/confirm_fidelity_report.py`）で残留を確認する。
