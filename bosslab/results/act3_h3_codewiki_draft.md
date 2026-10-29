# CODEWIKI 追記草稿: レリックの入場効果の二重発火（FORGOTTEN_SOUL、BLESSED_ANTLER）

追記先: `docs/CODEWIKI.md`（日付ログは `docs/codewiki/`）。本草案は BossLab（固定入場ラボ）で、記録した入場
状態を再現するときに入場 hook が二重に走る問題と、その外し方・直し方を書く。戦略判定ではなくゲーム再現の
正しさの話。

## 何が起きるか（原因）

ラボはある run の boss 入場状態を、記録した deck / HP / レリックから 1 戦闘だけ作り直す。入場 hook を持つ
レリックは `RunManager.EnterRoomDebug`（部屋入場）と `Hook.BeforeCombatStart`（戦闘開始）で、lab が入れたレリック
に対して再び走る。するとその hook が起こした変化が、記録済みの入場値に「もう一度」上乗せされる。

- `RELIC.FORGOTTEN_SOUL`: `AfterCardExhausted` で、exhaust 1 回につき `RunState.Rng.CombatTargets.NextItem(HittableEnemies)`
  で選んだランダムな敵へ `CreatureCmd.Damage`（`DamageVar(1, ValueProp.Unpowered)`）を与える（decompile
  `MegaCrit.Sts2.Core.Models.Relics/ForgottenSoul.cs:20-30`）。exhaust 順とランダム選択が base の記録 run と違う
  順で走ると、特定の敵 HP がずれる。lab の Rng シーケンスが記録 run と一致しないことで発火する。
- `RELIC.BLESSED_ANTLER`: `BeforeHandDraw`（1 ターン目の手札 draw 前）に Deterministic で Dazed を手札に足す
  （decompile `MegaCrit.Sts2.Core.Models.Relics/BlessedAntler.cs:45-55`）。lab が戦闘開始 hook を走らせると、
  記録 run で配られた Dazed に加えて lab 側でも配られ、開示 hand が二重になる。
- 同じ構造の入場 hook を持つレリックが他にもある。`RELIC.CROSSBOW` / `TOOLBOX` / `POWER_CELL` / `JEWELED_MASK`
  等は入場時にランダムなカードを手札やドローに足す系統で、ランダム順が一致しないと開示 hand がずれる。

## 見分け方

- lab の忠実性検査 `bosslab/tools/bosslab_fidelity.py` は、同じ spec で base の記録 trace と lab 実行を突き合わせ、
  入場直後の状態（敵 HP、pile、開示 hand、カウンタ）が一致するかを見る。fid5 panel で 12 中 10 一致・不一致 2。
  不一致 spec を `bosslab/tools/relic_entry_effects.py` の `ENTRY_EFFECTS` 表と照合し、その spec が原因レリックを
  所持しているかを見る（下表の handling）。
- counter 由来のずれとの区別: PenNib / Nunchaku / TuningFork の AttacksPlayed / SkillsPlayed は Mod が bridge から
  受けて第一判定直前に書き戻す（d216956、`BossLab.RestoreRelicCounters`）。fid5 の不一致 2 件は counter 由来では
  なく、上の二重発火由来。原因内訳は `bosslab/results/act3_fid5_mismatch_causes.md`。

## 除外条件（いまの fix）

plan 生成側で、入場忠実性が割り切れない spec を panel から落とす（`bosslab/tools/relic_entry_effects.py`）。

- `flag_unfixed`（入場 hook が run 状態に依存し、書き戻しても再現が難しい）: `CROSSBOW` / `TOOLBOX` / `BIG_HAT` /
  `ORANGE_DOUGH` / `POWER_CELL` / `FUNERARY_MASK` / `JEWELED_MASK` / `RADIANT_PEARL` / `BLESSED_ANTLER` 等。
- `RELIC.FORGOTTEN_SOUL`: exhausted pile が空の spec では divergence しない（実測で exhaust 0 の `d22ed45bc52f` 等は
  一致）。exhausted pile にカードが残る spec だけ発火するため、記録の `exhaust_pile` が非空で所持する spec を
  dev/confirm panel から除外した（dev5_swap の `8aa46daede55`、confirm5_swap の `bbbfd4fc2927` ）。
- panel 選定では原因レリック所持 spec を差し替え先にも選ばない（hash 順・band・outcome 一致・原因レリックなし）。

## 直し方（入場直後に記録値を書き戻す案）

除外せず直すなら、入場 hook が走った「後」、エージェントの第一判定の直前に、記録した敵 HP と combat pile を
上書きする。すでに `BossLab` は同じ位置（`CombatBridge.FirstDecisionHook`）で player HP とレリック counter を
書き戻している（`ReapplyRecordedHp` / `RestoreRelicCounters`）。そこに敵 HP と pile を足す。

- 実装: `official_mod/BossLab.cs` の `RestoreRecordedEntryState`（`RestoreRecordedEnemyHp` と
  `RestoreRecordedPiles`）。敵 HP は `CombatManager.Instance.DebugOnlyGetState().Enemies`（live `Creature`）を id で
  探して `GetCreature(combatId)` 経由で `SetCurrentHpInternal` / `SetMaxHpInternal`。pile は draw/hand/discard/exhaust を
  `PileType.X.GetPile(player)` で空にして、記録順に `AddInternal(card, idx, silent: true)` で並べ戻す。silent は card 自身の
  hook を起こさない（re-entry 二重化や on-draw 再発火を防ぐ）。
- 切替: 既定 OFF。plan の `restore_entry_state` または env `STS2_BOSSLAB_RESTORE_ENTRY_STATE=1` で ON（今回の
  確認用測定は default のまま）。plan に `enemies` と `piles` の記録値が必要です（fid5 の忠実性観測から採れる）。
- 限界: 敵 HP と pile の composition/order は直せるが、入場 hook が run の RNG を消費して後続のランダム選択を
  ずらす効果（CROSSBOW のランダムカード内容そのもの）は、hook を走らせない（除外）か、記録値で上書きする
  しかない。書き戻しは「hook の結果を打ち消す」ので、hook が run RNG を進めた副作用は残る。

## fid5 の 2 件で確かめる手順（実機は leader、ビルド後に実行）

dev5 の結果待ちの間に、この hook が二重発火を直せるかを fid5 の 2 spec で確かめる。

1. Mod をビルド（leader）。`BossLab.RestoreRecordedEntryState` を含む `Sts2Ai.dll` を入れる。
2. plan 生成時に、fid5 の 2 spec の忠実性観測（`bosslab_fidelity.py` が出す入場直後の敵 HP と pile）を
   `enemies` / `piles` フィールドへ書き出す。書き出せない間は default off なので既存挙動のまま。
3. 1 戦闘だけを fid5 の `8aa46daede55`（FORGOTTEN_SOUL）と `e030d2f11e5f`（BLESSED_ANTLER）で、env
   `STS2_BOSSLAB_RESTORE_ENTRY_STATE=1` を立てて再走（実機は leader）。
   ```
   STS2_BOSSLAB_RESTORE_ENTRY_STATE=1 pwsh -File ./run_official_bosslab.ps1 -GameDir "<game dir>" \
     -Plan <fid5 2 spec のみ再構成 plan> -OutDir data/bosslab_fid5_reentry_check \
     -AgentScript official_agent.py -AgentSimulations 100 -TimeoutSeconds 700
   ```
4. `bosslab_fidelity.py --all` で照合。目標は base 記録 trace と入場直後状態が一致し、不一致 2 が 0 になること。
   敵 HP 書き戻しが FORGOTTEN_SOUL の exhaust ダメージのズレを吸収するか、BLESSED_ANTLER の開示 hand の二重化が
   消えるかを、`RestoreRecorded*` の log 行（"re-asserted recorded enemy hp" / "rebuilt combat piles"）で確認する。
5. 一致したら dev5_swap / confirm5_swap の差し替えを hook 書き戻しに戻せるか検討（band 問題も併せて）。一致し
   なければ除外方針（上の除外条件）を維持する。hook を ON にした panel で win / 削り割合が変わらないことも確認
   （忠実性修正が戦略結果を変えていないことの担保）。

## 実装の状態（2026-10-29）

`official_mod/BossLab.cs` に hook と plan フィールドを書いた。ビルド・実機は未実行（このセッションは lab と解析
のみ担当）。Python 側の忠実性観測から `enemies` / `piles` を plan へ書き出す工程は未着手。suite 960 OK。
