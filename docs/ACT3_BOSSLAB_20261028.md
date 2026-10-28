# Act 3 ボス実験記録: 固定入場 QUEEN 戦で測る 殴り先変更（2026-10-28）

実装・解析・plan・パス別の結果は `bosslab` ブランチ（commit `769e025`、worktree `~/.sts2/wt-bosslab`。個別のcommit `ac9f3f0` / `a07d3d6` / `21d2727` / `d32a132` / `747b477` / `43b5a2e` / `2748bc1` / `9fac8ff` / `65afc58`）に置いた。本文の `.dsh/` のパスは同ブランチの `bosslab/tools`・`bosslab/plans`・`bosslab/results`・`bosslab/agents` の同名ファイルに対応する。Mod のコード（`official_mod/BossLab.cs`）を main に入れると対照 run の DLL ハッシュが変わるため main には入れていない。実機 run は leader が単独で回し、dsh 側はゲームを一度も起動していない。

この記録は confirm3（第3の集合、base 12 + 候補 12）の完走後に埋め直した。3 集合 75 trial が揃い、§5-1 の表と §6 の判定が確定版になっている（数値の再計算手順は §附）。

```text
仮説・変更の種類・対象場面:
  仮説: 「QUEEN 戦で Amalgam（Torch Head Amalgam）へ集中している殴りを QUEEN 本人へ振り向け
  ば、実走の敗北 run でも Queen 自身を削れるようになり、最終戦の進捗が改善する」。
  変更の種類: 局部検証（戦闘方針の攻撃対象の選択のみ。報酬選択・デッキ取得への影響は未測定）。
  対象場面: Act 3 ボス QUEEN（+ TORCH_HEAD_AMALGAM）の入場観測。実走 trace から抽出した
  同一入場状態で base / 候補を反復する isolated 比較（1 trial = 1 戦闘）。

旧版／候補版、ゲーム／Mod／userdata／探索条件:
  旧版（base）: official_agent.py（sha256 61e780f81fb8a716…）。
  候補版: bosslab/agents/official_agent_queenfirst.py（sha256 bab9519afd7f96ce…、main は無変更）。
  変更は heuristic 内の 2 か所だけで、どちらも queen_present で守られた条件の中
  （diff -u official_agent.py bosslab/agents/official_agent_queenfirst.py、5 hunk / 変更 59 行）。
  両版とも同一の Mod: BossLab 入り Sts2Ai.dll sha256 9a298350ec1d580a…（ポーション UI 再初期化
  込み、commit 747b477 のビルド）、ゲーム v0.107.1、探索 sim=100、userdata 非汚染（
  UnlockState.all、SetUpNewSingleplayer(shouldSave:false)）。実行条件は各 lab_meta.json に記録。
  idle kill: dev2 と fidelity2 の base は無効（lab_meta の idle 欄 None）、confirm2 base は 0、
  confirm3 base と候補 3 panel は -IdleTimeoutSeconds 320。いずれの dir の stdout log にも stalled
  は 0 件（発火しきい値に届く停止は無かった）。

開発用seed／確認用seed、選定方法、反復数:
  seed は入場状態 spec（spec 1 件 = 実走 1 回の入場状態、run_seed + 踏破済 floor 履歴で再現）。
  開発用 dev2: 12 spec（sha256 8e58c97a143cc2b1…、offsets 0、実効 seed 12）。
  確認用 confirm2: 12 spec（1673df30de074263…、offsets 2、dev2 と spec 重複 0）。
  確認用 confirm3: 12 spec（9b4a0daf26de1c0d…、offsets 2、dev2・confirm2・fidelity2 と重複 0）。
  忠実性確認 fidelity2: 3 spec（6c79192f5b83beb3…、Nimble 復元 1・札素朴 1・power 注入 1）。
  選定方法: usable pool（180 spec 中 80 件）から order-seed 指定の hash 順（結果・band・
  enchantment 有無を選定条件にしない）。run 状態レリック（TEA_OF_DISCOURTESY・VENERABLE_TEA_SET・
  EMBER_TEA・GIRYA など 14 種）を持つ spec、relic counter を持つ spec、preview で説明できない
  カード値を持つ spec、入場観測が戦闘途中の spec は除外。反復: 各 spec 1 実効 seed（1 trial）。

予定run数／時間上限／再実行条件:
  予定: base 39 trial（fidelity2 3 + dev2 12 + confirm2 12 + confirm3 12）、候補 36 trial（dev2 12 +
  confirm2 12 + confirm3 12）。合計 75 trial。時間上限 -TimeoutSeconds 700/ trial。
  再実行条件: 失敗 trial は同じ plan で -From/-To を指定して再走（pass1 では停止 2 本を再走した）。
  plan を差し替えない限り plan_sha256 は lab_meta に記録される。

判定に使う指標（標準から変える場合は測定前に理由を記録）:
  主信号: Queen 自身の 400 HP に対する削り割合（lab の全 trial は 1 戦闘のみなので到達点は
  同値、EVALUATION.md:27 の「到達点同値の最終戦の進捗」に該当。勝ちは 1.0、敵一覧に Queen が
  無い = 死亡）。実走の Act 3 base 勝率は約 7% で床に張り付くため、勝敗を主信号にすると
  0/12 と 1/12 の間の噪声で判定が壊れる。
  補助: Amalgam 撃破可否（召喚物は Queen の進捗に合算しない、EVALUATION.md の扱い）、
  死亡ターン、失った HP、block で吸収した概算。勝敗は補助のまま。
  検定: 同じ spec・offset の配对について同値を除く符号検定（McNemar 精密 p、両側）。
  集合横断のプールは参考値とし、集合ごとの判定に代えない。

計画数／完了数／不明数／外部障害／候補由来の障害:
  計画 75 / 完了 75（base fidelity2 3・dev2 12・confirm2 12・confirm3 12、候補 dev2 12・confirm2 12・
  confirm3 12）/ 実行中 0 / 結果行なし 0。
  外部障害 0（base 39 trial で失敗 0、ポーション例外 0 件、pass1 の 200 秒停止 2 本は修正 DLL で解消。
  confirm3 は base・候補とも 12 本完走、idle kill 0、stdout log の UsePotionAction 例外 0 件）。
  候補由来の障害 0（候補 36 trial で失敗 0、idle kill 0、例外 0）。

局所検証: 発動機会・判断差・結果差（件数と seed数）:
  発動機会: QUEEN + Amalgam の戦闘 36 試行（12 spec x 3 集合、集合間の spec 重複 0）。候補の短絡は
  36 試行すべてで 1 回以上発火（decision_source `queen_direct` の出現行数は dev2 148、confirm2 117、
  confirm3 122。base 側の対応する行は `queen_minion_direct` が dev2 125、confirm2 94、confirm3 100）。
  判断差: 攻撃の向け先が Amalgam から Queen へ移った（Amalgam 撃破が dev2 9/12→0/12、confirm2
  7/12→1/12、confirm3 6/12→2/12）。rollout 判断は rollout_success 196→120（dev2）、181→142
  （confirm2）、141→97（confirm3）へ減り、短絡がそれだけ引き取った。ポーション判断の回数は
  direct_potion 16→19 / 9→7 / 22→21（向先以外の変化ではないが、同一条件での分岐差として記録する）。
  結果差: dev2 12 組で候補優 9 / base 優 3 / 同値 0（Queen 削り平均 0.273 → 0.406、精密 p 0.146）。
  confirm2 12 組で候補優 8 / base 優 3 / 同値 1（0.282 → 0.377、精密 p 0.227）。
  confirm3 12 組で候補優 8 / base 優 3 / 同値 1（0.333 → 0.422、精密 p 0.227）。
  3 集合で向きは同じ（平均 +0.133 / +0.095 / +0.089）。プール（参考値）36 組で候補優 25 / base 優 9 /
  同値 2、精密 p 0.009。集合別にはどれも 5% 水準に届かない。
  勝ちは dev2 0 → 0、confirm2 1 → 1、confirm3 2 → 1（合計 3/36 → 2/36。win 記録のある spec を 4 件
  含む。confirm3 の 624ae0d1306b だけが base の勝ち → 候補の敗北へ移った）。

全体比較: 集合ごとのAct 3・2・1突破数／母数、到達点の改善・悪化・同値:
  未測定。ラボは 1 戦闘だけを測るので Act 3 踏破・Act 2/1 突破は出ない（EVALUATION.md の
  主指標は Act 3 踏破率で、この実験では測れていない）。到達点（その戦闘にたどり着くまでの進行）は
  同じ plan の同じ入場状態なので全 36 組で同値。戦闘そのものの結末は base 勝ち 3/36 → 候補勝ち 2/36
  （両版が勝った組 2、base だけ 1、候補だけ 0）。

到達点同値の最終戦: 比較可能／不能な組数、形態・削った割合の差、残HPの観測時点:
  比較可能 36 組（比較不能 0）。削り割合の差は上の表のとおり（dev2 平均 +0.133、confirm2 平均
  +0.095、confirm3 平均 +0.089、組別では dev2 9/12・confirm2 8/12・confirm3 8/12 が上振れ）。
  QUEEN は単一形態、Amalgam は別記で
  199 HP の secondary（MinionPower、QUEEN 死亡で自動消滅: CombatManager.cs:192、
  Creature.cs:245-268、TorchHeadAmalgam.cs:40-44）。残 HP と敵 HP の観測時点は bridge が書く
  combat_end 直前の最終観測行で、撃破の 1 手は確定しない（lab の lab_results は
  enemy_hp_last_observed を最終観測時点で切る）。

各seedの結果、悪化例、証拠ファイル:
  dev2 12 spec: 候補が削った組 9（実数値の例 8e975fbd 14%→37%、f7fe72c3 3%→42%、
  b91b9246 6%→32%）、悪化 3（0b21d5e5 45%→38%、9c9b1484 43%→39%、b947d020 36%→36% の微減）、
  同値扱い 0。confirm2 12 spec: 候補優 8、悪化 3（94149577 25%→20%、a8f49615 54%→47%、
  a3a10386 23%→22%）、同値 1（54912dc8: 両版とも Queen を殺して勝ち）。confirm3 12 spec: 候補優 8
  （1a05bb73 13%→35%、c77f7c05 2%→33%、83e6a346 1%→32%、e7578152 25%→53%）、悪化 3（624ae0d1
  100%→68% ＝ base の勝ちが候補の敗北へ移った唯一の組、739389f7 59%→30%、703d7333 36%→32%）、
  同値 1（bf5c0080 100%→100% 両版勝ち）。
  候補の死亡内訳: 36 試行中 33 が Amalgam を生かしたまま死んだ（base は 14/36）。死亡ターン中央値は
  dev2 7.5→6.0、confirm2 7.0→6.0、confirm3 7.0→6.0。失 HP の中央値は dev2 78→78、confirm2 78→78、
  confirm3 82→85。敵の telegraph から推定した浴びた合計ダメージ（失 HP + 吸収分）の中央値は dev2
  172→166、confirm2 168→166、confirm3 164→166 で、ターンが短いぶん候補のほうが少ないか同程度。
  火力は trace の HP 減少合計で測り直した（定義は §5-2）。候補の総火力は base より小さい。
  証拠: .dsh/act3_queenfirst_dev2.md、.dsh/act3_queenfirst_confirm2.md、
  .dsh/act3_queenfirst_confirm3.md（leader が実行）、.dsh/act3_queenfirst_sets.md（集合横断）、
  火力と内訳は .dsh/act3_queenfirst_behavior.py と .dsh/act3_queenfirst_confirm3_detail.txt、
  raw は data/bosslab_act3_{dev2,confirm2,confirm3}*_queenfirst/ の lab_results.jsonl と
  trial_*_agent.jsonl、lab_meta.json。
  実走側の台帳と忠実性照合: .dsh/act3_boss_losses.md（§1-§8）、
  .dsh/act3_pass2_fidelity/*.md、.dsh/act3_boss_fights.jsonl。

採用／保留／不採用、その根拠と次に必要な証拠:
  判定: **保留**。主信号（Queen 削り割合）は 3 集合すべてで同じ向きに改善し（dev2 +0.133、
  confirm2 +0.095、confirm3 +0.089）、横断プールの 36 組では候補優 25 / base 優 9 / 同値 2、精密 p
  0.009。ただし集合別の精密 p は 0.146 / 0.227 / 0.227 で、どれも単独では 5% 水準に届かない。
  勝ちは 3/36 → 2/36 に 1 組減り（624ae0d1306b の base の勝ちが候補の敗北へ）、補助指標は Amalgam
  撃破 22/36 → 3/36、死亡ターン中央値 7〜7.9 → 6 に悪化。Act 3 踏破率（EVALUATION.md の主指標）は
  ラボでは測定不能。EVALUATION.md:68 の「到達点同値で削った割合だけ改善」の形では、削りの改善が
  3 独立集合で同じ向きに出たので進捗改善としての根拠は強いが、勝ち込みが減っているため同文法の
  「採用」には進めない。因果と一般化は主張しない。
  次に必要な証拠: (1) フル run パネルでの Act 3 踏破率（ラボでは測れない主指標）。
  (2) 勝ち筋のある spec を増やす（usable 80 件のうち win 記録は 4 件しかなく、36 組でも勝ち転換の
  検出は弱い）。(3) Amalgam の攻撃を止めないまま Queen を削る方針の内訳検証（Amalgam 処置前後の
  挙動を分けた arm、部分的 Amalgam 処理・block 配置の arm）。(4) 忠実性の残る 3 種の修正（§3 参照）。
  (5) Act 3 TEST_SUBJECT 用の lab（旧 trace 限定で deck multiset を作れる trace が増えるまで spec 0 件）。
```

## 1. 前提: 実走 Act 3 の敗因分解（T11 要約）

集計時点（2026-10-28 18:1x、main `data/` の trace 1865 本と mod log を突合。再生成手順は §附）。

- Act 3 ボス室で戦闘した run は 274。内訳 QUEEN_BOSS 263（敗北 245・勝利 18）、TEST_SUBJECT_BOSS 10（敗北 7・勝利 3）、AEONGLASS_BOSS 1（敗北 1）。manifest 側（結果確定 run 617 件のうち Act 3 ボス到達 112 件）でもボス敗北 104・踏破 8。
- 勝利に QUEEN 自身の 400 HP 削りだけが必要で、Torch Head Amalgam（199 HP）は MinionPower の secondary。QUEEN が死ねば自動死亡、QUEEN 生存中のみ存在できる。よって進捗は Queen 400 に対する割合で測り、Amalgam は別記。
- agent 形式 trace の QUEEN 敗北 227 本で、死んだ時点の Queen 残 HP 中央値 **328/400（削り 18%）**。無傷で終えたのが 20 本、300 以上残したのが 130 本。QUEEN へ通した火力の中央値 71、Amalgam に消えた火力の中央値 154。Amalgam を処置できた 139 本のうち、その火力レートで QUEEN を殺し切るまで 5 ターン以上必要なものが 100 本、1-2 ターンで済んだのは 14 本。
- 致死一手は Amalgam 側（BEAM/TACKLE 系）86 本、QUEEN 側 burst（OFF_WITH_YOUR_HEAD 112 + EXECUTION 29）141 本。Amalgam を処置できないまま死んだ 86 本と、処置後に QUEEN を殺しきれない 141 本に二分される。QUEEN は Amalgam 死亡後の自強化（OFF→EXECUTION→ENRAGE で Strength を毎回 +2）と恒久の Vulnerable/Weak/Frail（YOU_ARE_MINE）で、ターンが伸びるほど burst が強くなる。
- 勝った run（agent 形式 QUEEN 勝ち 15 本 = 7 seed、legacy 込みで 21 本 / 9 seed）は、7 seed すべてに engine 札（Rupture / Bloodletting / Hemokinesis / Offering / Inflame / Burn 系）が入り、死亡時 Strength 中央値 29（敗北側 4.5）、QUEEN 火力/ターン 中央値 76（敗北側 19）。Obsidian『sts2-aiの勝利シード記録』に書いた N8CQ4ZKP2W=Rupture+Battle Trance+Bloodletting・Strength 30・31枚、H2LV6ZJ4XW=HP 7/130 まで削られた記録と同型。block 札は seed で 0-5 枚とばらつき、受けずに削り切る勝ち方と受け切る勝ち方が混じる。因果は主張せず、候補の仮説として置いた。

詳細と生成物: `.dsh/act3_boss_losses.md`（§1 件数・§2 台帳・§3 敗因分解と Amalgam 生死×Queen 削り band クロステーブル・§4 勝ちとの同軸比較・§5 spec 再現性・§6 候補 3 案・§7 ラボ pass1/pass2・§8 候補 agent）。

## 2. ラボの Act 3 拡張と修正

- `ENCOUNTER.QUEEN_BOSS` 対応（act_index 2・15 行 map の floor 15・`history_per_act` で踏破済み floor を埋めて敵構成 RNG を再現）: commit `02f603c`。
- **enchantment 復元**: plan の札に `enchantment` id と amount を載せ、`SerializableCard.Enchantment` 経由で `RunState.LoadCard` → `CardModel.FromSerializable`（EnchantInternal + ModifyCard + FinalizeUpgradeInternal、`CardModel.cs:2216-2240`）で復元。commit `02f603c`。
- **residual power 注入**: 入場観測の player power を「レリックが説明できる分」と「それ以外」に分解し、レリックで自動再現される分は注入せず、残った分だけ `EnterRoomDebug` の後・bridge 起動前に `PowerCmd.Apply<T>` で載せる（`BossLab.ApplyEntryPowers`）。180 spec のうち注入が要るのは 5 件だけで、172 件は deck のレリックが説明対象（注入すると二重になる）。commit `02f603c`。
- **ポーション UI の再初期化**（commit `747b477`）: `AddPotionInternal(silent: true)` は `PotionProcured` を上げないため holder node が作られず、使うと `NPotionContainer.RemoveUsed` の `First(...)` が例外投げて action queue が止まっていた（`Nodes/Potions/NPotionContainer.cs:197-207`、`:352-357`）。agent 使用でも `FairyInABottle` の自動使用でも同じ経路。pass1 では停止 2 本と、完走 10 本でも例外 29 件（例外は効果発動前の `RemoveBeforeUse` なので、ポーションは消えるのに効果が適用されない）。`EnterRoomDebug` 後に `TopBar.PotionContainer.Initialize(runState)` を読む `RefreshPotionUi` を追加して解消（実機で trial 0・11 を再走し例外なしで完走、pass2 の 3 dir でも `UsePotionAction` 例外 0 件）。**この不具合は Act 2 の Shrug 176 試行にも影響していた**（main `docs/BOSSLAB_20261028.md` に訂正が入った）。
- **idle watchdog**（commit `21d2727`）: `run_official_autoslay.ps1` の待ち込みを 1 秒 polling に変え、agent trace・mod log・bridge ファイルの最新更新が `IdleTimeoutSeconds` 秒止まったら kill（既定 0 = 無効、`run_official_bosslab.ps1` 経由で渡り `lab_meta.json` に記録）。1 決定に 40〜221 秒かかる Act 3 では 320 秒以上を推奨。

## 3. 忠実性（何を一致させ、何を割り切ったか）

比較項目は HP/最大/block/energy/max_energy・player.powers(id+amount)・relic id と counter・potions・deck multiset（強化・enchantment id 込み）・pile 別枚数・敵 id/hp/max_hp/初期 move/intents・最初の判断のターン、加えて札の preview 値（cost・Damage・Block）。ツールは `bosslab/tools/bosslab_fidelity.py`（commit `43b5a2e` で Act 3 向けに修正。詳細表は `.dsh/act3_dev_fidelity/report.md` と `.dsh/act3_pass2_fidelity/*.md`）。

**忠実性の判定結果**（lab の最初の観測 vs spec、spec vs 実走 trace）:

- lab vs 実走の入場状態が完全一致: pass2 の base panel で **fidelity2 1/3・dev2 5/12・confirm2 8/12**。confirm3 の 12 trial は忠実性照合をまだ走らせていない（同じ plan を base と候補で使う配对比較には影響しないが、絶対値の一致率に confirm3 を含めるなら `bosslab_fidelity.py` を同じ形で実行する必要がある）。spec 抽出は pass1 12/12・pass2 でも各 panel 全 trial で実走と一致（抽出プロセスは正しい）。
- pass1 で出たズレのうち、run 状態レリック由来のもの（`TEA_OF_DISCOURTESY` の `CARD.DAZED` 2 枚追加、`VENERABLE_TEA_SET` の入場 energy 2 不足、Amalgam HP 1 差）は、pass2 の pool から該当 spec を落としたので消えた。`RELIC.PEN_NIB: 0` の表示差は bridge 側の表示の問題として残る（威力に効かない）。`CARD.POMMEL_STRIKE` 1 枚追加は pass1 と同じ spec（b91b9246）が pass2 にも入っており再現したので、決定論的なズレ。
- preview 値: pass1 で比較 22 种类のうち不一致 2、pass2 で dev2 24 种类中 4、confirm2 16 种中 2、fidelity2 3 种中 1（`CARD.MAD_SCIENCE+0+` の lab 未 preview・12/14 差）。TezcatarasEmber 適用済み Strike が一致したので enchantment 復元は cost・Damage とも実走と同値（amount 既定 1 で足りた）。**Nimble はこの panel で両側 preview されず未検証**（deck multiset 上の enchantment id は一致）。
- pass2 で新たに出た注入経路のズレ 3 種（plan 指定値と spec の値は一致しており、lab の読み違いではない）: (1) 札の upgrade が 1 枚ずれる（dev2 trial 0・3、confirm2 trial 6。枚数は同じで実走 `+0` が lab `+1`。該当 trial は Whetstone・Toxic Egg・Pomander・Yummy Cookie 等を持ち、`AddRelicInternal(silent: true)` では `AfterObtained` が飛ばない一方、deck への追加自体に対する hook（Egg 系）や turn 開始時の追加（Crossbow 系）が発火する経路の疑い）。(2) `RELIC.POTION_BELT` を持つ spec で入場観測のポーションが 5 本あるのに lab は 3 本しか乗せない（注入が `slot < player.MaxPotionCount` で打ち切り、Belt のスロット増加が `AfterObtained` 側だから）。(3) 入場 HP が lab だけ 17 大きい（confirm2 trial 7、114/97。hook は未特定）。
- **対応のある比較では打ち消される**（base も候補も同じ plan・同じ DLL・同じ入場状態なので、上のズレは両版に同じ入り方で出る）。ただし絶対値としての忠実性は一致本数が示すより低く、ラボの削り割合を実走の勝率と直接較べる主張には留保が付く。
- 忠実性用に能力別選別した 3 trial（fidelity2）のうち 1 件は「入場観測が戦闘途中」spec を `--allow-unresolved` で意図的に入れてあり、その 7 項目のズレはすべて mid-turn 系（block 22/50、`POWER.VIGOR_POWER 8` が lab に無い=実走は初回攻撃で消費済み、pile 枚数、Amalgam 180/198）。注入した `POWER.NO_DRAW_POWER 1` は両側で一致し、residual 注入は効いている。

## 4. 候補 official_agent_queenfirst の定義

- 置き場所 `bosslab/agents/official_agent_queenfirst.py`（main の `official_agent.py` は無変更。runner が絶対パスで起動するため `sys.path` にリポジトリ直下を足す shim のみ追加）。sha256 bab9519afd7f96ce…。
- 変更 2 か所（`diff -u official_agent.py bosslab/agents/official_agent_queenfirst.py` で 5 hunk / 変更 59 行、生成物を `.dsh/queenfirst_agent.diff` に置いた）。
  1. QUEEN 在戦で TORCH_HEAD_AMALGAM を重点対象にしていた短絡（`queen_minion_ids`・`queen_minion_direct`）の向け先を QUEEN 本人へ。Rupture / Hellraiser / Inflame / Bloodletting の setup、block ゲート、lethal を先に立てる順序はそのまま。タグは `*_queen_direct` 系に改名（trace で base と区別するため）。
  2. `focused_minions` から TORCH_HEAD_AMALGAM を外す（`{"MONSTER.KIN_FOLLOWER"}` のみ）。
- block・ポーション・end_turn・rollout の得点は main と同じ行。`test_official_agent_queenfirst.py` の 7 テストで、QUEEN 戦で attack の target が base は Amalgam・候補は Queen、防御が必要なターンでは両版が同じ防御札、QUEEN が居ない戦闘（Decimillipede・Kin Follower）では base と同一、lethal は同じ、定数表は同一、を固定。base 側の既存 Queen テスト 5 件（`test_official_agent.py`）はそのまま通る。
- rollout（`combat.py` 側の得点）は変えていない。短絡が消えた分の最終判断は rollout か heuristic 末尾が担うが、実測では短絡がむしろ増えた（decision row 集計: `rollout_success` 196→120 / 181→142 / 141→97、`heuristic_fallback` 118→79 / 104→80 / 126→91、`queen_direct` 0→148 / 0→117 / 0→122、base 側の `queen_minion_direct` は 125 / 94 / 100。dev2 / confirm2 / confirm3 の順）。

## 5. 結果

### 5-1 配对比較（同じ spec・offset。主信号 = Queen 削り割合）

| 集合 | base 平均 | 候補平均 | 候補優 | base 優 | 同値 | 精密p（両側） | Amalgam 撃破 base→候補 | 死亡ターン base→候補 | win base→候補 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev2（12 組） | 0.273 | 0.406 | 9 | 3 | 0 | 0.146 | 0.750 → 0.000 | 8.08 → 6.08 | 0 → 0 |
| confirm2（12 組） | 0.282 | 0.377 | 8 | 3 | 1 | 0.227 | 0.583 → 0.083 | 7.92 → 6.67 | 1 → 1 |
| confirm3（12 組） | 0.333 | 0.422 | 8 | 3 | 1 | 0.227 | 0.500 → 0.167 | 7.92 → 6.50 | 2 → 1 |
| プール（参考値・36 組） | 0.296 | 0.402 | 25 | 9 | 2 | 0.009 | 0.611 → 0.083 | 7.97 → 6.42 | 3 → 2 |

集合ごとの判定をプール 1 本に置き換えない（EVALUATION.md: 比較する run 数と反復数は集合単位で揃える）。3 集合とも同じ向きで、プール 36 組の精密 p は 0.009。集合別では p 0.146 / 0.227 / 0.227 と単独では 5% 水準に届かない。表の生成は §附のコマンド 1 本（`.dsh/act3_queenfirst_sets.md`）。

### 5-2 候補の挙動の内訳（なぜ削れて、なぜ勝たないのか）

- **Amalgam を殺さなくなる**: Amalgam 撃破は dev2 9/12→0/12、confirm2 7/12→1/12、confirm3 6/12→2/12（合計 22/36 → 3/36）。死亡時点で Amalgam が生きている試行は base 14/36 → 候補 33/36。死亡ターン中央値は dev2 7.5→6.0、confirm2 7.0→6.0、confirm3 7.0→6.0（配对平均は 7.97 → 6.42）。
- **死因は Amalgam の攻撃**: 候補で Amalgam を生かしたまま死んだ 33 試行は、死んだターンに盤面へ居た attack intent がすべて Amalgam のもの（BEAM_MOVE 21、TACKLE_3_MOVE 7、TACKLE_4_MOVE 5。lab trace の最終観測行の telegraph で、lab には mod log の室情報が無いので 1 手単位の致死一手は特定していない）。base が Amalgam を処置した後に QUEEN の burst で折れた形（Amalgam 処置後の敗北 19 試行）と比べ、**候補は「QUEEN を削る代わりに Amalgam の攻撃で早く死ぬ」形**になっている。
- **削りの改善は火力の「向け直し」であって火力増ではない**: trace の HP 減少合計（撃破で消えた分は残 HP まで加える定義。Queen への与ダメと Amalgam への与ダメを分ける。1 ターンあたりは各版自身の生存ターン `last_observed_turn` で割る）で測ると、Queen への火力/ターンは base 11.9→27.3（dev2）、12.0→21.4（confirm2）、14.0→25.2（confirm3）と上がったが、総火力/ターンは base 37.5→32.9、36.8→31.1、38.7→35.9 と落ちて、総量でも base 300 → 候補 213（36 組平均）へ減った。base の Queen への火力と候補の Amalgam への火力が ±1 以内の組（向先だけを入れ替えた組）は 36 中 0、総火力まで ±1 以内の組も 0。草稿版が書いた「24 中 6」は §3-2 の turn-window 差分ベースの数字で、この定義に組み直した時点で消えた。
- 浴びた合計ダメージ（失 HP + 吸収分の推定。end_turn 観測の telegraph 合計）の中央値は dev2 172→166、confirm2 168→166、confirm3 164→166、失 HP の中央値は 78→78、78→78、82→85。候補は短いターンで同程度のダメージを受け切っている。
- 削りは上がったが勝ちには転じていない: 候補の敗北 34 試行で死亡時点の Queen 残 HP 中央値 258/400（最小 125、最大 358）、base の敗北 33 試行は中央値 332/400。勝ち変化は 3/36 → 2/36 で、base だけが勝った 624ae0d1306b（削り 100%→68%）が候補で敗北へ移った。
- 見立て（根拠の範囲で）: 削り割合の改善は 3 独立集合で同じ向きに出たが、勝ちは増えていない（むしろ 1 組減った）。勝ちに転換するには Amalgam の攻撃を止める/受け切る仕組み（Amalgam を部分的に処理する、block を Amalgam の攻撃ターンに寄せる、Amalgam の攻撃が致死になるときだけ殺す 等）を同じ plan 内の arm として測る必要がある。勝率向上の断定はしない（36 組で win 3→2、Act 3 踏破率は未測定）。

## 6. 判定と次に必要な証拠

- 判定（3 集合 75 trial 完了時点）: **保留**。主信号の Queen 削り割合は dev2 0.273→0.406（候補優 9 / base 優 3、p 0.146）、confirm2 0.282→0.377（8 / 3 / 同値 1、p 0.227）、confirm3 0.333→0.422（8 / 3 / 1、p 0.227）と 3 独立集合すべてで同じ向きに改善し、横断プールの 36 組では候補優 25 / base 優 9 / 同値 2、精密 p 0.009 まで強まった。ただし集合別の p は単独で 5% 水準に届かず、勝ちは 3/36 → 2/36 に 1 組減り（base だけが勝った 624ae0d1306b が候補で敗北）、補助指標は Amalgam 撃破 22/36 → 3/36、死亡ターン中央値 7〜7.9 → 6 へ悪化、候補の総火力は base より小さい（§5-2）。EVALUATION.md:68 の「到達点同値で削った割合だけ改善」の形には該当するが、勝ち込みが減っているため「進捗改善として採用」には進めない。Act 3 踏破率（EVALUATION.md の主指標）はラボで測定不能。因果と一般化は主張しない。
- 次に必要な証拠（順不同）:
  1. **フル run パネル**（同じ方針で Act 3 踏破率が動くか。ラボは 1 戦闘しか測らない）。
  2. **win 記録のある spec を増やす**（usable 80 件のうち win 記録 4 件。勝ち転換の検出母数が小さい）。mid-turn/blocked 系を復元できると pool は 179 件相当まで増える（`.dsh/act3_spec_ladder.json`）。
  3. **Amalgam 処置前後の挙動の内訳**を測る arm（Amalgam を部分的に処理する、Amalgam 攻撃ターンに block を寄せる、Amalgam が致死になるときだけ殺す）。候補1の次の案として plan arm で測る。
  4. **忠実性の残る 3 種の修正**（走査ルールに `AfterObtained` を入れて取得時効果を持つ spec を除外/†表示、BossLab 側のポーションスロット再計算、入場 HP の差の hook 特定）。base/候補の比較は対照的なので、修正後に絶対値を組み直す。
  5. **Act 3 TEST_SUBJECT 用の lab**（現行 spec 0 件。TEST_SUBJECT/AEONGLASS は旧 trace 限定で deck multiset を作れない。新しい agent 形式 trace が溜まるのを待つか、観測側の pile 出力を待つ）。

## 附. 生成・再現手順

```bash
cd ~/.sts2/wt-bosslab
python3 .dsh/act3_scan.py --jsonl .dsh/act3_fights_census.jsonl   # 件数 census + act3_scan_stats.json
python3 .dsh/act3_boss_detail.py                                   # 戦闘1行=1件の台帳
python3 .dsh/act3_entry_powers.py                                  # 入場 power の由来分解
python3 bosslab/tools/scan_relic_run_state.py                      # 入室時の挙動が run 状態に依存するレリック
python3 .dsh/extract_act3_specs.py                                 # lab 用 spec（この草稿で使った pool）
python3 .dsh/act3_spec_ladder.py                                   # 能力別の usable 数
python3 .dsh/act3_report.py                                        # .dsh/act3_boss_losses.md（§1-§8）
python3 bosslab/tools/bosslab_fidelity.py --all --out-dir data/bosslab_act3_dev2 \
    --plan .dsh/bosslab_act3_plan_dev2.json --specs .dsh/act3_boss_specs.jsonl \
    --out .dsh/act3_pass2_fidelity/bosslab_act3_dev2.md            # 各 panel で同じ形
python3 bosslab/tools/analyze_bosslab.py --run data/bosslab_act3_dev2 \
    --run "queenfirst=data/bosslab_act3_dev2_queenfirst" --out .dsh/act3_queenfirst_dev2.md \
    --specs .dsh/act3_boss_specs.jsonl
python3 bosslab/tools/analyze_bosslab.py --compare-pair "dev2=data/bosslab_act3_dev2:data/bosslab_act3_dev2_queenfirst" \
    --compare-pair "confirm2=data/bosslab_act3_confirm2:data/bosslab_act3_confirm2_queenfirst" \
    --compare-pair "confirm3=data/bosslab_act3_confirm3:data/bosslab_act3_confirm3_queenfirst" \
    --out .dsh/act3_queenfirst_sets.md --specs .dsh/act3_boss_specs.jsonl
python3 .dsh/act3_queenfirst_behavior.py                                 # 火力の内訳と向先変更の検査
python3 -m unittest discover -p 'test_*.py'                        # 893 tests OK（2026-10-28 時点）
```

run の形（実機は leader）: `pwsh -File ./run_official_bosslab.ps1 -GameDir "<game dir>" -Plan .dsh/bosslab_act3_plan_dev2.json -OutDir data/bosslab_act3_dev2_queenfirst -AgentScript bosslab/agents/official_agent_queenfirst.py -AgentSimulations 100 -TimeoutSeconds 700 -IdleTimeoutSeconds 320`

---

## 7. ハイブリッド候補 H1/H2（事前登録採否規則、confirm4 実測で判定 保留）

§1-§6 の queenfirst（常に Queen 優先）とは別の実験で、「Amalgam を倒せる状況では Amalgam を優先」する hybrid 候補 H1/H2 を dev2 で測り、事前登録した採否規則（コミット `4693f2e`、`bosslab/results/act3_hybrid_decision_rule.md`）に当てて機械判定した記録。確認用集合 confirm4 は HP 即時 clamp 修正 927f26f を含む DLL（build 済み・ゲーム未起動のまま leader が起動）で base/H1 を 12/12 完走、判定規則も leader が 1 回実行済みで判定は **保留**（`act3_hybrid_rule_applied.md`、比較 `act3_confirm4_compare.md`）。実機 run は leader が単独で回し、dsh 側はゲームを一度も起動していない。§1-§6 の実験（queenfirst）とは候補 agent と規則が違い、結果を持ち込まない。

```text
仮説・変更の種類・対象場面:
  仮説: Queen を先に殴る（target 変更）と Queen 削りが進み Act3 踏破に効くか。Amalgam は二次ミニオン
    （QUEEN 死亡で道連れに消える）なので、Queen 削りの補助に Amalgam 掃除を足せるかを問う。
  変更の種類: 戦略変更（エージェントの単一ターゲット方針）。正しさの修正（忠実度）とは分離。
  対象場面: Act3 QUEEN + Torch Head Amalgam ボス戦闘（Glory、floor 15）。

旧版／候補版、ゲーム／Mod／userdata／探索条件:
  旧版 base: official_agent.py（queen_minion_direct で Amalgam 優先）。
  候補 H1: bosslab/agents/official_agent_H1.py（make_h_candidates.py 生成）。Amalgam 実効 HP(hp+block)
    が 0< <=50 のときだけ Amalgam、それ以外 Queen。定数 QUEENFIRST_H1_AMALGAM_HP=50。
  候補 H2: bosslab/agents/official_agent_H2.py。Amalgam の次手番の自由な一撃が自分を殺しうる時だけ
    Amalgam、それ以外 Queen。変更殴り先のみ。
  ゲーム: v0.107.1。キャラクター: Ironclad。難易度: 既定。 userdata: BossLab が記録 entry から再構築。
  Mod: Sts2Ai.dll。dev2/dev3 3-arm は忠実度修正 131a5a0 まで（HP 即時 clamp 927f26f 未反映）で実行。
    confirm4 は 927f26f を含む DLL。agent_script の sha256 は run_official_bosslab.ps1 が各行に記録。
  探索: rollout 100。乱数: trial は spec_id と offset（plan の rotation）から決まる effective_seed。

開発用 seed／確認用 seed、選定方法、反復数:
  開発用（dev3 系）: plan_dev2 の QUEEN spec 12 件、base/H1/H2 を同一 entry で配対（offset 0..）。
    dev2 base・confirm 系で計 26 spec を使用済み（.dsh/bosslab_act3_used.speclist）。
  確認用（confirm4）: act3_boss_specs.jsonl の QUEEN のうち unresolved と使用済みを除き、開手札ランダム付与系・
    RELIC.PAELS_CLAW（Goopy）・RELIC.PENDULUM（カウンタ draw）を除外した eligible から、order-seed
    act3-confirm4 の sha256(seed|spec_id) 順で上位 12 件（used と重複なし）。候補の結果を知らずに対象効果・
    過去勝利を条件に選ばない。選定は dev2 結果の前に確定（コミット 245c38c、除外 id 修正と PENDULUM 追加で
    再生成 0e060c6）。
  反復数: 各 arm 12 trial（1 spec×1 反復/組）。同一 seed の再走は再現性確認で独立 seed 数に数えない。

予定 run 数／時間上限／再実行条件:
  予定: 開発用 dev3 base/H1/H2 各 12（計 36、完了）、確認用 confirm4 base/H1 各 12（計 24、base/H1 完了）。
  時間上限: trial 毎 TimeoutSeconds 700・IdleTimeoutSeconds 320。
  再実行条件: 外部クラッシュ・中断は未完了として別 tag へ同一 spec/版/条件で再走。結果を見て有利 seed を
    足さない、勝った時点で打ち切らない。

判定に使う指標（標準から変える場合は測定前に理由を記録）:
  標準の Act3 踏破数は lab が直接測れない（lab は 1 戦闘のみ）。よって到達点同値の最終戦の進捗として
  Queen 削り割合（=1−最終 Queen HP/入室時最大 HP、Amalgam は Queen 進捗に合算しない）を主信号に、
  総火力/ターン（Queen+Amalgam への総 HP 削除÷プレイヤーターン、§5-2 の 300→213 の軸）と Queen 火力/ターンを
  副主信号、Amalgam 撃破・死亡ターン・失った HP を補助に、勝敗は母数 0 の記録。採否規則（コミット 4693f2e）は
  削り差>0 かつ火力/ターンと win が base 以上、確認用集合で削り符号検定 p<=0.05、比較不能なし、開発用と確認用が
  同じ向き、をすべて満たすことを採用条件に測定前に固定。

計画数／完了数／不明数／外部障害／候補由来の障害:
  dev3 base 12/12、H1 12/12、H2 12/12 完了。confirm4 base 12/12、H1 12/12 完了（計 24、leader が 927f26f 入り
  DLL で実機実行）。全 trial で outcome_source=combat_end_trace（fallback・欠測 0）、候補由来の例外・停止は観測
  されていない。判定規則（apply_hybrid_rule.py）は leader が 1 回だけ実行し確定済み。

局所検証: 発動機会・判断差・結果差（件数と seed 数）:
  H1 の Amalgam 掃除は dev2 で一度も発火しなかった。実走 12 trial で戦闘中の Amalgam 実効 HP の最小が
  111〜199（1 度も 50 以下にならず、act3_dev3_interpretation.md）。queen_minion_h1 は 148 件だが全件 Queen を
  殴った（Amalgam 単独撃破 0/12）。＝機構は dev2 では実質未試行。H2 も base との判断差は 3 手番分。
  結果差（削り）: dev2 で H1 は 12 組中 9 増 3 減（精密両側 p=0.146）、H2 は 8 増 4 減（p=0.388）。confirm4 で
  H1 は 12 組中 7 増 5 減（p=0.774）で、confirm4 でも Amalgam 実効 HP が 50 以下になる手番が無く Amalgam 単独撃破 0/12。

全体比較: 集合ごとの Act3・2・1 突破数／母数、到達点の改善・悪化・同値:
  lab は Act3 踏破率を測れない。win 記録は dev2 の全腕で 0/12（母数 0 の補助）。到達点（Queen 削り）改善・悪化・
  同値: dev2 で H1 改善9 悪化3 同値0、H2 改善8 悪化4 同値0（base 比、12 組）。総火力/ターンは dev2 で base 37.4 に
  対し H1 32.9・H2 35.7 と低下。confirm4（base 対 H1）: Queen 削り割合 平均 0.403→0.385（候補優 7 / base 優 5 /
  同値 0、精密 p 0.774）、総火力/ターン 39.149→28.795（1 増 11 減）、Queen 火力/ターン 15.333→23.708（9 増 3 減）、
  Amalgam 撃破 7/12→0/12、死亡ターン 8.167→6.667、失った HP 83.083→83.667、win 1→0（base が勝った spec
  75157844a09c が 100%→68% で敗北）。配対 12/不能 0。数値は leader の確認用表 act3_confirm4_compare.md と一致。

到達点同値の最終戦: 比較可能／不能な組数、形態・削った割合の差、残 HP の観測時点:
  配対可能 12/不能 0（同一 spec×offset）。残 HP/最終 Queen HP は trace の combat_end 時点（勝 trial は撃破の
  1 手前で trace が切れ実質撃破として扱う）。HP 即時 clamp 修正前の dev3 では idx11（ROYAL_POISON）が絶対注意対象
  （dev3 全腕で同じ制約）。927f26f 反映後の confirm4 base では入室 HP 一致 2/2。

各 seed の結果、悪化例、証拠ファイル:
  dev2 証拠: data/bosslab_act3_dev3_{base,H1,H2}/（trace + lab_results.jsonl）、act3_dev3_compare.md、
  act3_dev3_base_desc.md、act3_dev3_interpretation.md。confirm4 削りの向き（spec×offset、+ は H1 が上）:
  1563989f9e55 0→29%+、2f944dc24562 0→13%+、56accb541102 25→36%+、59ed603b4b73 13→22%+、5f6a1726cfea 58→38%-、
  624ae0d1306b 88→66%-、75157844a09c 100→68%-、8340d5737b02 18→21%+、8aa46daede55 85→70%-、c247ea1ceac4 94→46%-、
  c589d7860c35 0→40%+、f737cab6f8b6 4→10%+（7 増 5 減）。証拠 data/bosslab_act3_confirm4_{base,H1}/ と
  act3_confirm4_compare.md。

採用／保留／不採用、その根拠と次に必要な証拠:
  事前登録規則（コミット 4693f2e）を apply_hybrid_rule.py で leader が 1 回実行した結果、判定は **保留**
  （act3_hybrid_rule_applied.md）。条件1（両集合で削り Δshave>0: dev2 候補優9>base優3、confirm4 候補優7>base優5）・
  条件2（両候補の向きが dev2 で同じ）は充足。条件3（総火力/t が base 以上: dev2 H1 32.9<37.4、confirm4 H1
  28.8<39.1）・条件4（win が base 以上: confirm4 1→0 で減）・条件5（confirm4 削り符号検定 p≤0.05: p=0.774）・
  条件6（12 組すべて配対）は条件6 のみ充足で 3・4・5 は不充足。よって採否規則上この target 機構（hybrid）は採用しない。
```

### 7-1 忠実性（confirm4 base、927f26f 反映後の DLL、実測済み）

`bosslab_fidelity.py --all` を confirm4 base（12 trial、927f26f 入り DLL）に実行。完全一致 7/12、不一致 5 件
（証拠 `act3_confirm4_fidelity.md`、原因詳説 `act3_confirm4_fidelity_causes.md`）。
- HP 即時 clamp（927f26f）の検証: ROYAL_POISON を持つ 2 組（c589d7860c35・59ed603b4b73）で lab 入室 HP が記録
  HP に一致（53/53/53・90/90/90）。修正前の不一致（RoyalPoison ターン 1 自己ダメの二重差し引き）が実機で解消された。
- 残り 5 件は HP・ポーション枠起因ではなく、3 種の入場状態再現のずれ（spec 抽出は元 trace と一致＝抽出は正しい、
  lab 再現側の限界）: ① RELIC.PEN_NIB のカウンタ 3 件（`relic_counters` lab `{PEN_NIB:0}` vs spec `{}`。PenNib は
  攻撃カード play 毎の `AttacksPlayed % 10` SavedProperty、10 枚目の攻撃を 2 倍。元 trace は旧ブリッジでカウンタ列が
  無く、攻撃 play 数から推定 0002/0006=3・0010=4。§7-6 の案で新 DLL の観測から採る）。② 0007 の TAUNT/DEMON_FORM
  +1（Whetstone の AfterObtained 強化 2 枚と NewLeaf の変換が、silent add でも `AfterObtained` model フックが走る
  ため入室で再適用され deck がずれる。confirm4 で Whetstone 所持 5 件のうち net 変化は 1 件、強化が冪等なら無変化）。
  ③ 0011 の Amalgam/Queen 1 点配分（198/400 vs 記録 199/399、計 598 同一。敵入室 HP を `spec.enemies[].hp` から
  pin せず formation 生成、lab 初手観測はターン 1 の AfterPlayerTurnStart 後に撮る設計帰結。具体源未確定）。
- これら 5 件は base と候補が同じ 12 spec（同一入場状態）を流す配対比較では両腕に同じ向きで出るため、配対の差
  （削り/win/ターン）には出ず、判定規則（4693f2e）の採否結論は動かない（dev2 3/12・confirm2 2/12・confirm3 0/12 で確認）。

### 7-2 dev2 結果と候補選定規則の適用

dev2 3-arm（base/H1/H2）を事前登録規則（コミット 4693f2e）に当てた集計は `act3_dev3_compare.md`、解釈は
`act3_dev3_interpretation.md`。削り割合は H1 0.261→0.406（9 増 3 減、p=0.146）、H2 0.261→0.360（8 増 4 減、
p=0.388）で改善側。ただし総火力/ターンは base 37.4 に対し H1 32.9・H2 35.7 に低下、win は 0/12。選定規則（火力/
勝利が base 以上が必須ゲート）で両候補が火力ゲートを通らず落選、hybrid は進めない。dev2 で削り差最大（H1）だけ
記録用に confirm4 へ進めた。規則は dev2 結果を見る前に確定済み。

### 7-3 H1/H2 は「Amalgam 優先」を 2 集合で実質試していない

- H1: `0 < Amalgam 実効 HP <= 50` が dev2 12 trial でも confirm4 12 trial でも一度も発火せず（実効 HP 最小 111〜199、
  `act3_dev3_interpretation.md`）、Amalgam 単独撃破 0/12。Amalgam を削る唯一の手段が Amalgam を殴ることで、既定
  Queen 優先だと Amalgam が入場値 199 付近に留まり条件が永久に発火しない（鶏と卵）。結果 H1 は Queen 固定＝実質
  queenfirst と同挙動。
- H2: Amalgam の次手番の一撃が自分を殺しうる時だけ Amalgam。base との判断差は 3 手番分で、これも queenfirst と大差ない。
- つまり「Amalgam を倒せる状況ではそちらを優先する」機構そのものが 2 集合でほぼ試行されず、試されたのは「常に
  Queen 優先（=queenfirst）」だった。ここが未検証の空白で、次候補 H3 はこの空白を埋める（`act3_hybrid_h3_design.md`）。

### 7-4 confirm4 配対比較（実測）

| 指標 | 配対 | base 平均 | H1 平均 | H1 優 | base 優 | 同値 | 精密p（両側） |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Queen 削り割合（主信号） | 12 | 0.403 | 0.385 | 7 | 5 | 0 | 0.774 |
| 総火力/ターン | 12 | 39.149 | 28.795 | 1 | 11 | 0 | – |
| Queen 火力/ターン | 12 | 15.333 | 23.708 | 9 | 3 | 0 | – |
| Amalgam 撃破可否（補助） | 12 | 0.583（7/12） | 0.000（0/12） | 0 | 7 | 5 | – |
| 死亡ターン（補助） | 12 | 8.167 | 6.667 | 1 | 6 | 5 | – |
| 失った HP（補助） | 12 | 83.083 | 83.667 | 0 | 1 | 11 | – |
| win | 12 | 1/12 | 0/12 | – | – | – | – |

配対 12/不能 0。規則の機械適用結果（`bosslab/tools/apply_hybrid_rule.py`、leader が 1 回実行、`act3_hybrid_rule_applied.md`）: 判定 **保留**。

### 7-5 判定と次に必要な証拠（確定版）

判定は **保留**。confirm4 でも削り符号（候補優 7>base 優 5）は dev2 と同じ向き（条件1・2 充足）だが、削りの平均
magnitude は 0.403→0.385 に下がり、総火力/ターン 39.1→28.8 と win 1→0 が低下、confirm4 の精密 p は 0.774 で 5% 水準に
届かず（条件3・4・5 不充足）、採否規則上この target 機構（hybrid）は採用しない。留保:
- (a) H1 は dev2 でも confirm4 でも一度も掃除が発火せず実質 queenfirst と同じ動きで、「Amalgam を倒せる状況では
  そちらを優先する」機構は 2 集合で実質未試行。保留は機構が効かない証拠ではなく試されていない状態の記録。
- (b) confirm4 の忠実性は 7/12 で、残りは PEN_NIB のカウンタ（3 件）等の入場状態再現のずれ。配対比較なので両腕に
  同じようにかかり配対の差には出ない（判定に無影響）。
- (c) ラボは Act 3 踏破率を測れない（1 戦闘のみ）。削り割合は到達点同値の最終戦進捗の代理。
- (d) 2 集合とも 12 組で p≤0.05 はこの母数では厳しい基準（dev2 0.146、confirm4 0.774）。
次に必要な証拠: 「実際に Amalgam を削る」ことを保証する次候補 H3a（QUEENFIRST_H3_OPEN_TURNS=2）・H3c
（QUEENFIRST_H3_DANGER_FRAC=0.5、実装済み・単体テスト 14 件 pass・コミット 2b6ef0f）を、使用済み spec と重複の無い
新しい確認用集合に流して測ること（`act3_hybrid_h3_design.md`、dev2 base 手番表 `act3_queenfirst_h1h2_dev2.md`、
H3a A=32 / H3c A=29）。踏破率はフル run パネルで別途測る。

### 7-6 次の goal 準備（実装は未実施）

- H3a（`bosslab/agents/official_agent_H3a.py`、QUEENFIRST_H3_OPEN_TURNS=2）と H3c（QUEENFIRST_H3_DANGER_FRAC=0.5）:
  手番/脅威基準で Amalgam を削るので H1/H3b の「Amalgam が既に低い」前提の自己閉鎖を解く。設計は
  `bosslab/results/act3_hybrid_h3_design.md`、単体テスト `test_bosslab_h3_agents.py`（14 件）、dev2 base 上の手番表は
  `act3_queenfirst_h1h2_dev2.md`（H3a A=32 / H3c A=29）。実機未投入。
- PEN_NIB 入場カウンタ: §7-1① の実装案（新 DLL の観測 `relic_counters` 列から採り、BossLab が入場時 SavedProperty
  を書き戻す。旧ブリッジのtraceから作った confirm4 のような spec では採れない）は `act3_confirm4_fidelity_causes.md`。
- Act 2 Shrug 再測定の忠実性棚卸し: 除外は RELIC.PENDULUM を持つ spec 1 本のみ（PANTOGRAPH×3・STONE_CRACKER×1 は
  BossLab 処理済で除外不要、他レリック 0 件）、plan 作り直しは配対比較が成り立てば不要（`act2_shrug_fidelity_stocktake.md`）。
