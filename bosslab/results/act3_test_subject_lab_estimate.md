# TEST_SUBJECT の BossLab 可行性見積もり（実装なし、issue #6 用）

Act3 代替ボスの一つ `ENCOUNTER.TEST_SUBJECT_BOSS`（`MONSTER.TEST_SUBJECT`、3 形態 100/200/300、実効合計 600）を
BossLab の固定 entry パネルで扱えるかの見積もり。結論は「実行は可能、ただし忠実な entry spec が無いのが主たる
障壁」。実装はしていない。

## 結論

- シミュレータと enemy データは対応済みで、BossLab の実行経路は TEST_SUBJECT をそのまま走れる。ここは障壁でない。
- 忠実な入室 entry（deck/relic/potion/enchantment/開戦 piles）を持つ TEST_SUBJECT の観測が、新しい agent 形式では
  1 件もない。あるのは古い trace 形式だけで、entry 状態が揃っていない。ここが本丸の障壁。
- 判定用ツールは QUEEN 専用なので、TEST_SUBJECT の 3 形態に合わせて一般化する必要がある。中〜小の作業。
- よって feasible だが無料ではない。次の goal に入れるなら、TEST_SUBJECT へ routing する seed で新形式の走行を
  集めて spec を作り、ツールを一般化する、の順。

## 対応済みで障壁でないもの

- 実行経路: BossLab の run は per-trial の `Trial.Encounter` で敵編成を作る encounter 汎用（QUEEN と Amalgam の
  道連れ死亡も同じ汎用経路）。`ENCOUNTER.TEST_SUBJECT_BOSS` を plan に載せれば drive できる。ゲームは起動しない。
- シミュレータ: `combat.py` は TEST_SUBJECT をモデルしている。`RESPAWN_MOVE` による 2 段階復活（`combat.py:322,495,1146`）、
  死亡処理 `_mark_test_subject_death`（`combat.py:1335`）。AdaptablePower/EnragePower は導出 state machine に出ないため
  入室時に注入する設計（`combat.py:1146-1149` のコメント）。`official_agent.py:308-309` に power 名対応もある。
- enemy データ: `data/enemies_glory.json` に `ENCOUNTER.TEST_SUBJECT_BOSS` と `MONSTER.TEST_SUBJECT`（各形態と
  EnrageAmount2, MultiClawDamage10, Phase3LacerateDamage10, BigPounceDamage45 等の damage 値）がある。

## 障壁と、必要な作業

### 1. 忠実な entry spec が無い（主障壁・中程度）
- 新しい agent 形式（`*_agent.jsonl`、pile 出力あり）の TEST_SUBJECT 入室観測は main ワークスペース全体で 0 件。
  control 蓄積 136 本（T24）でも Act3 ボス到達は 33 件すべて QUEEN、TEST_SUBJECT は 0 件。
- 古い trace 形式（`*_trace.jsonl`）で TEST_SUBJECT に到達した run は存在する（`astra_goal_pacts1` 等 約 10 本、
  seed D6A1F8C3E5 系統）。だが古い trace には `relics` / `deck` / `draw_pile` / `discard_pile` / `exhaust_pile` と
  敵の `max_hp` が入っておらず、`hand` と `potions` と敵の現在 HP/intents のみ。BossLab の QUEEN パネルが要求する
  固定 entry（deck multiset・relic・enchantment・開戦 piles・敵最大 HP）を復元できない。
- 必要作業: TEST_SUBJECT に routing する既知 seed（上記）で、現行 agent 形式の autoslay を走らせて pile/relic/
  enchantment/敵 max_hp 付きの入室観測を採集し、そこから spec を抽出する。seed 収集は routing 確認込みで中程度の労力。
  実行は leader（ゲーム起動）。

### 2. spec 抽出ツールが encounter 固定（小）
- `bosslab/tools/extract_boss_specs.py` は Act2 THE_INSATIABLE 固定（`BOSS_SUFFIX`, `encounter_hint` 固定）。
  Act3 QUEEN 用の抽出（main の `.dsh/extract_act3_specs.py`）も QUEEN 前提。TEST_SUBJECT 用に encounter を
  パラメータ化するか TEST_SUBJECT 変種が必要。小。

### 3. 判定ツールが QUEEN 専用（中〜小）
- `bosslab/tools/analyze_bosslab.py` の `continuous_metrics` は `QUEEN_ID_SUFFIX=".QUEEN"`/`AMALGAM_ID_SUFFIX`/
  `QUEEN_MAX_HP=400` で単一 Queen の削り割合を主信号にする。TEST_SUBJECT は単一 `MONSTER.TEST_SUBJECT` が
  形態交代（RESPAWN）で 100/200/300 を経る敵。
- 必要作業: 主信号の「到達点同値」を 3 形態用に再定義する。選択肢は (a) 削除 HP 合計 / 600（形態を跨いだ累計）、
  (b) 処理した形態数 / 3。副信号の Amalgam 撃破は TEST_SUBJECT には対応物が無いので除く。火力/ターンはそのまま。
  敵 max_hp は新しい export にあるので採集し直した trace では削りの分母が使える（古い trace の max_hp 欠落は解消）。
  id 対応表と形態横断の HP 集計の追加で、改変は小〜中。

### 4. 採否規則/EVALUATION との整合
- 事前登録済みの hybrid 採否規則（コミット 4693f2e）の軸（削り割合・火力/ターン・win）は、ツールを 3 形態に
  一般化すればそのまま移せる。ボス交代（形態 switch）を「到達点」の区切りとして扱う定義を先に固定する必要がある。

## 労力の総括（issue #6 用の一句）

TEST_SUBJECT は BossLab と combat.py で機械的に扱える（encounter 汎用 + 2 段階復活・Adaptable/Enrage を実装済み、
enemies_glory.json に形態と damage 値）。障壁は忠実な entry spec の不在で、新形式の TEST_SUBJECT 入室観測は
0 件（蓄積 136 本でも Act3 ボスは 33/33 QUEEN）、あるのは relic/deck/piles/enchantment/max_hp を欠く古い trace だけ。
次の goal で扱うなら、TEST_SUBJECT に routing する既知 seed で新形式の走行を集め（実行は leader）、そこから spec を
抽出し、QUEEN 専用の判定ツールを 3 形態（累计 600 HP / 形態処理）に一般化する。実装は未着手、この doc が見積もり。
