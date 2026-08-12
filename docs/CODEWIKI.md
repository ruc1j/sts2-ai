# STS2 AI Code Wiki

現行コードの入口、データフロー、Bridge契約を短くまとめる。公式ゲーム内部APIの前提はmanifestと同じ `v0.107.1` である。

## Python

### `official_agent.py`

`choose(observation, enemy_data=None, simulations=0)` がフェーズ別の入口である。

| `phase` | 呼び出し先 |
| --- | --- |
| `shop` | `choose_shop` |
| `map` | `choose_map` |
| `card_reward` | `choose_card_reward` |
| `rest` | `choose_rest` |
| その他 | combat選択 |

combat選択の順序は、Sandpit中の `Frantic Escape`、Crabのfacing変更、potion、条件を満たす `rollout_choice`、lethalなStrike/Bash、Defend、カード優先度、`end_turn` である。lethal候補は攻撃してくる敵、次に最もHPの低い敵を優先して倒し、カード優先度が同点の攻撃は最もHPの低い敵へ集中攻撃する。Slippery持ちの敵への実効ダメージは1としてlethal判定し、HardToKill(Exoskeletonの1ヒット上限9)持ちの敵には実効ダメージをキャップして判定する。rolloutで `KeyError`、`ValueError`、`NotImplementedError`、`StopIteration` が出た場合は後段のヒューリスティックを使う。

`_axis` はデッキから `strike`（Perfected StrikeまたはHellraiser）、`self_damage`（RuptureまたはTear Asunder）、`vulnerable`（`VULNERABLE_PAYOFF` とBashまたは `VULNERABLE_APPLY`）、`exhaust`（`EXHAUST_ENABLERS` と `EXHAUST_PAYOFF`）の順に判定する。`_core_priority` はaxisごとの未所持coreカードを順位化し、axisがない場合だけ利用可能な Perfected Strike、Rupture、Corruption を候補にする。

`choose_shop` はlegalな `buy_card` にcore順位を適用し、該当購入がなければPerfected Strikeを含むstrike axisのデッキでは `CARD.DEFEND_IRONCLAD`、それ以外では `CARD.STRIKE_IRONCLAD` の削除を探す。最後はlegalな `skip`、他の最初のaction、空なら `{"type": "skip"}` の順で、1回の観測につき1 actionを返す。この関数自体は価格計算や複数actionの実行をしない。

`choose_card_reward` は `CARD_TIERS` の S/A/B/C/D をbase tierとして数値化し、`_core_priority` のaxis対応coreカードをbase tierより先に比較する。デッキのブロックカード(`DEFENSE_PRIORITY` とDefend)が全体の1/3未満のときは、防御カード(Shrug It Off、Flame Barrier、Iron Wave等)に+2の優先度を付けてAct 2向けの被弾を減らす。`UNPLAYABLE_REWARDS`(現在はRelaxのみ)は3コストのブロックがgreedy rolloutで使いづらいため報酬で絶対に選ばず、提示がRelaxだけならSkipする。未知カードなどcoreにもtierにもないカードは `option_id == "Skip"` のalternativeへ回す。`choose_map` はAct開始時に全マップが開示されるため、通常HPでは現在地(または開始地点)からBossまでの全経路をDFSで列挙し、`(戦闘マス数, -休憩数, エリート数, -宝箱数, 不明数, -ショップ数)` の優先順で最適ルートを選んでその次の1歩を返す。戦闘マス最小化を最優先するのは、1マップで通常戦闘4つ目以降は強い敵プールになる仕様を回避するためである。Bossに到達できる経路がない場合やBossが存在しない場合は従来のroom valueにフォールバックする。HPが最大値の2/3以下ではRestSiteへの距離・Elite数・安全性を使う。`choose_rest` はボス直前(floor 13以降)なら負傷時に `HEAL` を優先し、HPが最大値の75%以上なら `HATCH`、負傷中なら `HEAL`、それ以外は `SMITH` を探す。

`choose_potion` はincoming damage、HP、敵数、敵HP、手札を使って、致死回避、回復・防御、範囲攻撃、攻撃強化などの候補を固定順序で選ぶ。敵HPが100以上の長丁場(ボス・大型エリート)では STRENGTH/FLEX/POWER/COLORLESS/ATTACK/SKILL/DUPLICATOR/DISTILLED_CHAOS/EXPLOSIVE_AMPOULE の攻撃系potionを先制使用し、被弾前に戦闘を短縮する。自動使用potionは手動選択しない。

`main` は観測JSONを25ms間隔で読む。`terminal` なら終了し、seqが前回と異なるとき `choose` の結果にseqを付け、`atomic_write`（tmp + `os.replace`）でaction JSONを書く。JSON/I/O一時エラーはpollを継続し、その他の例外はerror logへ記録してlegalな `end_turn` があれば書き込む。

### `combat.py`

`Enemy` と `Combat` はfrozen dataclassである。`initial_combat` は敵編成・敵HP・move・初期手札を生成し、`legal_actions` はenergyとtargetに基づくカード action と `End turn` を返す。`step` はカード、敵ターン、山札、power、状態遷移を更新する。`search` は各初手から最大60手のランダムロールアウトを行い、平均評価で並べる。

代表的な近似対応は、Vulnerable、Weak、Frail、Strength、Slippery、HardToKill、Sandpit、Crab背面攻撃、Anger、Shrug It Off、Battle Trance、Slimed、Bully、Dismantle、Iron Waveに加え、Cinder、Ashen Strike、Hemokinesis、Perfected Strike、Inflame、Primal Force、Unrelenting、Giant Rock、Relax、Tremble、Breakthrough、Whirlwind、Bloodlettingである。Iron Waveは5ダメージと5ブロックを同時に与える。HardToKillはEXOSKELETONが `AfterAddedToRoom` で初期付与される「1ヒットあたり最大9ダメージ」のキャップで、`initial_combat` で付与され `_damage_enemy` でSlipperyの次に適用される。これによりシミュレーションのEXOSKELETON戦の被弾予測が実ゲーム(約29)に一致する。

`search` の評価は勝利を1、敗北を-1、それ以外を0とし、HP/100と「初手で倒した敵が与えるはずだった攻撃ダメージ/100」を加算する。この被弾防止ボーナスにより、攻撃してくるミニオンの討伐がノイズに埋もれず正しく評価される。rolloutはランダムではなく `_greedy_action` を使う。`_greedy_action` は各カードを「倒した敵の攻撃ダメージ(被弾防止) + 与ダメージ - 自己ダメージ + 有効ブロック」で評価し、最善のカードを選ぶ。これによりミニオンを毎ターン確実に倒し、被弾を最小化する。

`_greedy_action` の評価には3つの補正がある。(1) primary(ボス)を倒した場合はその残りHPぶんを加算し、復活するミニオンよりボスのトドメを優先する。(2) Slipperyを剥がした分を加算し、Slippery持ちのボス(例: VANTOM)への攻撃を促す。(3) BASH/TREMBLEのようなVulnerable付与カードには、手札の後続アタックの強化分(ダメージの1/2)を加算し、弱体付与を先に打つ。プレイヤーのStrengthは攻撃ダメージに加算され、Ashen Strikeはexhaust山の枚数、Perfected StrikeはStrikeタグ数で増加する。IllusionPowerを持つミニオン(例: Parafright)は敵フェイズ終了時に最大HPで復活し、SAILのような味方バフは自分以外の生存敵に適用される。

### `ironclad.py`

公式Bridgeとは独立した単一敵モデルである。`State`、`legal_actions`、`step`、深さ60のMCTS (`search`) を持ち、初期状態はHP80、Strike 5、Defend 4、Bash 1である。`load_enemy` は敵JSONのclass名を正規化して読む。

### `act_map.py` / `extract_effects.py`

`act_map.load_map` はpoint ID重複、存在しない子、隣接しないrowを拒否する。`paths` はAncientからBossまでの全経路、`matching_paths` はroom type列に一致する経路を返す。

`extract_effects.effects` は逆コンパイルC#の指定メソッドから、攻撃、block、heal、summon、escape、kill、HP設定、power、card pileのコマンドを順序付きで抽出する。CLIは敵JSONの状態機械とperformメソッドへ効果を追記する。

## C# Bridge

### 共通

`Entry.Initialize` は `--sts2ai-autoslay` または `--unlock-ironclad-epochs` がある場合だけ起動する。AutoslayではHarmony patchを適用し、`IroncladPatch` が新規ランのcharacterをIronclad、seedをコマンドライン値へ固定する。epoch解除のみの起動ではIronclad Epoch 2～7を取得・公開して終了する。

Bridgeはゲームの標準Handlerをagent modeだけ差し替える。`CombatBridge`、`MapBridge`、`RewardBridge`、`RestBridge`、`ShopBridge`、`EventBridge` がそれぞれのphaseを担当する。

### `combat` (`CombatBridge.cs`)

Combatのplayer turnで、hand、pile、potion、player powers、敵のHP/block/move/history/intent/powerを観測する。カードはhand indexと合法target、potionはslotと合法target、最後に `end_turn` を `legal_actions` として出す。

action受信後、cardはhand indexとcard ID、potionはslot・potion ID・target・queue状態を再検証して公式APIへ渡す。`agent-max-combats` の上限を超えたcombatは元のHandlerを使う。終了時は `combat_end` traceを書く。

### `map` (`MapBridge.cs`)

合法な次地点を公式の `MapTravel.GetTravelablePointsFrom` から作る。最初はStartingMapPoint、最終行はBoss、二体目のBossがあればそのpointを候補にする。map observationにはrun情報、全pointのparents/children、legal map actionを含める。選択は `VoteForMapCoordAction` をenqueueして `RoomEntered` を待つ。最初のsnapshotは `bridge-map` に一度だけ保存する。

### `card_reward` (`RewardBridge.cs`)

カード報酬画面をcaptureし、カードとalternative、playerのHP/max HP/gold/deckを観測する。`card_reward` または `card_reward_alternative` のindexとIDが一致した場合だけUI signalを発火する。`Skip` はlocal reward setをskipして報酬を回収する。

### `rest` (`RestBridge.cs`)

有効なRestSite buttonを観測し、`index` と `option_id` を検証してクリックする。Proceed buttonまたはoverlayの応答を待つ。

### `shop` (`ShopBridge.cs`)

Merchant inventoryから、カード・relic・potion、削除費用、削除可能カード、gold、deckを観測する。legal actionは購入可能な `buy_card`、`buy_relic`、`buy_potion`、削除可能な `remove`、常に存在する `skip` である。

購入は商品IDとslot/index、削除はdeck indexとcard IDを再照合してから実行し、最後にinventoryを閉じてProceedする。agentが2分以内に返答しなければskipする。Bridgeは商品の合法性だけを提供し、axis gatingと購入優先度はPythonの `choose_shop` が決める。

### `event` (`EventBridge.cs`)

agent modeで `BYRDONIS_NEST` のロックされていないTAKE optionがあればクリックする。その後は通常の `EventRoomHandler` に委譲する。汎用イベントのJSON交換はない。

### potion card selection

`PotionChooseCardPatch` はPowerPotion、ColorlessPotion、AttackPotion、SkillPotionのカード選択を固定処理する。PowerPotionは現在energyで払える最初のカード、それ以外は最初のカードを選び、skip可能ならnullを返す。

## ファイルプロトコル

ゲーム側は `--bridge-observation`、`--bridge-action`、任意で `--bridge-trace` と `--bridge-map` を受け取る。`AgentIo.NextSequence()` の最初のseqは0で、phaseをまたいで増加する。C#とPythonは一時ファイルからrenameしてJSONを交換する。

```json
{
  "seq": 12,
  "terminal": false,
  "phase": "combat",
  "legal_actions": []
}
```

Python actionには同じseqを付ける。C#はaction JSONを25msごとに読み、seq不一致・不完全JSONを無視する。待機deadlineは2分である。

| phase | observationの主な項目 | actionの主な項目 |
| --- | --- | --- |
| `map` | `run`、`map`、`legal_actions` | `type=map`、`col`、`row` |
| `combat` | `turn`、`player`、hand/pile、potions、enemies、`legal_actions` | `card` / `potion` / `end_turn`、index/ID/target |
| `card_reward` | `player`、`cards`、`legal_actions` | cardまたはalternativeのindex/ID |
| `rest` | `run`、`player`、`legal_actions` | `type=rest`、`index`、`option_id` |
| `shop` | `gold`、deck、商品列、`remove_cards`、`legal_actions` | `buy_*` / `remove` / `skip` |

`terminal: true` は `stop-after-agent` または `stop-after-reward` で終了するときに書かれる。通常の戦闘終了はtraceの `phase=combat_end` であり、terminal observationとは別である。

## 代表的な確認コマンド

```powershell
python -m unittest discover -p 'test_*.py'
python .\ironclad.py --enemy-hp 40 --enemy-attack 8 --simulations 500 --seed 0
python .\combat.py .\data\enemies_overgrowth.json ENCOUNTER.SLIMES_WEAK --simulations 500 --seed 0
```

公式DLLを更新した場合は、Modのビルド、敵・マップJSONの再生成、Pythonテスト、最小公式run、trace/resultの確認を順に行う。
