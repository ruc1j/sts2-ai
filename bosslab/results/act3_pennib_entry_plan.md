# PenNib 入場カウンタの実装案（T29.3、実装は未実施）

結論: 今の DLL は各 observation に `relic_counters`（`CombatBridge.RelicCounters`、CombatBridge.cs:293-310）で
PenNib→`AttacksPlayed` などを入れている。その列を持つ入場観測から spec を採れば、入場時のカウンタを厳密に復元
できる。復元は「戦闘内の閾値・倍率だけを変えるカウンタ」に限り、引かれる札の身分を変えるカウンタ（PENDULUM）には
使えない。旧ブリッジ trace 由来の spec（confirm4 など）は列を持たないので、**今の DLL で採る新しい走行の spec に限る**。

## データ源（確認済）
- `CombatBridge.RelicCounters`（CombatBridge.cs:298-303）が毎 observation の `relic_counters` に出す mapping:
  PenNib→`AttacksPlayed`、Nunchaku→`AttacksPlayed`、TuningFork→`SkillsPlayed`。PenNib の `AttacksPlayed` は
  `SavedProperty`（setter が `value % 10` に正規化、値域 0..9、PenNib.cs）。10 枚目のプレイヤー攻撃カードのダメージを
  2 倍する（`ModifyDamageMultiplicative` と `AttackToDouble`）。
- confirm4 の元 trace（`data/candidate_fysh_N8CQ4ZKP2W_agent.jsonl` 等）は旧ブリッジで、trace のキーは
  `seq/phase/…/decision_reason` のみで `relic_counters` も `AttacksPlayed` も一切無い（出現 0 回）。よってその spec
  では入場カウンタを直接採れない。

## 実装案（3 箇所）
1. 抽出器（`bosslab/tools/extract_bosslab_specs.py` と plan builder）: boss 入室の初回 observation の
   `relic_counters` を spec に取り込む。spec には per-relic counters 用の入れ物 `relic_run_state`（`relic_run_state.json`
   の `other_saved_prop_relics` と対応）が既にあり、いまは空。ここへ PenNib/Nunchaku/TuningFork の観測値（0..9）を
   記録し、plan の各 trial にも載せる。
2. BossLab.cs: 入室 hook 実行と relic の silent add の後、agent の初判断の直前（FirstDecisionHook が記録 HP を
   再適用する箇所、＝ターン 1 の AfterPlayerTurnStart 完了後）に、relic 毎の記録カウンタを書き戻す
   `RestoreRelicCounters(player, trial)` を挟む。PenNib は `BeforeCardPlayed` で `AttacksPlayed` を増やすので、その
   base 値（0..9）をターン 1 の攻撃前に復元すれば、10 枚目の二重化が実走と同じ位置に着く。
3. 書き戻し機構: `AttacksPlayed` の setter は private（`% 10` 正規化）で、`NotifyAttackPlayed` は加算専用。書き戻す
   道が要る。選択肢 (a) リフレクションで `SavedProperty` を名前で set、(b) `AddRelicInternal` に初期カウンタ引数を
   追加、(c) model 側に復元用 public メソッド追加。`relic_run_state.json` の `other_saved_prop_relics`（SavedProperty
   名の一覧）を駆動に、名前で set する汎用復元が保守的（PenNib/Nunchaku/TuningFork ほか同筋を一括で扱う）。

## 設計で決める点
- 同期: 書き戻し対象は `CombatBridge.RelicCounters` の mapping と一致させる（観測に出たカウンタだけが spec に
  記録されるので、出ていない SavedProperty は対象外）。`relic_entry_effects.py` / `relic_run_state.json` に
  「復元可（戦闘内の閾値・倍率だけ変える）」と「復元不可（入室時の draw/shuffle で札の身分を変える）」の区別表を
  新設し、汎用復元は「復元可」だけを走らせる。
- 除外条件との棲み分け: PenNib/Nunchaku/TuningFork は復元で解決するので、今の DLL で採った spec では忠実性除外
  条件から外せる。反して RELIC.PENDULUM（`TurnsSeen` がターン 1 の初ターン draw の札身分を変える）と RELIC.CROSSBOW
  （入室 hook のランダム無色札）はカウンタを書き戻しても lab RNG で札の身分が一致しないので復元不可＝除外維持。
  判別基準＝「そのカウンタが入室時の RNG 消費（draw/shuffle）を伴わず、戦闘内の閾値・倍率だけを変えるか。伴うなら
  復元不可」。
- `AttackToDouble` の保留: PenNib は `AttacksPlayed` が 9→10 に跨界した瞬間だけ当該攻撃を `AttackToDouble` に
  覚えて 2 倍にする。復元する入場値が 0..9 で、boss 入室がちょうど 10 枚目の直後（カウンタ 0 で `AttackToDouble`
  保持）という境界は稀。境界 spec では transient も要復元だが spec が保持しないので、該当 spec を除外するか、次の
  攻撃で正常に解けるため実害なしとして許容するかを設計で決める。
- 回帰テスト: 「今の DLL で採った spec（`relic_counters` あり）→ BossLab 復元 → lab の boss 入室観測に
  `AttacksPlayed` が記録値で出る」を `test_bosslab_*` で回帰化。現行（復元なし＝0）からの差分を assert する。

## 条件（明記）
- この復元が使えるのは、`CombatBridge.RelicCounters` を含む build（今の DLL）で採った入場観測の spec に限る。
  confirm4/confirm2/dev2 のような旧ブリッジ trace 由来の既存 spec は `relic_counters` 列を持たないため、この方式では
  厳密に復元できない。推定（boss 入室前のプレイヤー攻撃 play 数 mod 10、実測 0002/0006=3・0010=4）は取れるが lab
  値との突合はできない。次 goal の新しい確認用集合を今の DLL で採れば、この問題は起きない。
