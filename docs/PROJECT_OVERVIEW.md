# STS2 AI プロジェクト概要

## 目的

Slay the Spire 2（STS2）の公式ゲームエンジンを起動し、外部Pythonエージェントとファイル経由で観測・行動を交換して Ironclad のランを操作するプロジェクトである。公式ゲームの完全な再実装ではない。

Python側の `combat.py` は敵データを使う近似戦闘シミュレータであり、公式エンジンの判定そのものではない。保存した敵データ、マップ、trace、Act終了結果を使って、オフライン検証と実行結果の調査を行う。

## 構成

```text
SlayTheSpire2.exe
  └─ official_mod/Sts2Ai.dll
       ├─ Entry.cs          Mod初期化、Ironclad固定、seed、Act終了処理
       ├─ CombatBridge.cs   combat phase の観測・行動交換
       ├─ MapBridge.cs      map phase
       ├─ RewardBridge.cs   card_reward phase
       ├─ RestBridge.cs     rest phase
       ├─ ShopBridge.cs     shop phase
       └─ EventBridge.cs    Byrdonis の卵の固定選択
                ▲
                │ observation.json / action.json / trace.jsonl
                ▼
official_agent.py            フェーズ別Pythonポリシー
combat.py                    複数敵の近似戦闘とロールアウト
ironclad.py                  独立した単一敵MCTSモデル
act_map.py                   マップ検証・経路列挙
extract_effects.py           逆コンパイルC#から敵効果を抽出
data/                        敵・マップ・trace・実行結果
test_*.py                    unittest と成果物検証
```

`official_mod/Sts2Ai.csproj` は `net9.0` を対象に、ゲームの `sts2.dll`、`0Harmony.dll`、`GodotSharp.dll` を参照する。manifestの最小ゲームバージョンは `v0.107.1` である。

## ビルドと実行

ゲーム本体と .NET SDK を用意し、リポジトリルートで実行する。

```powershell
pwsh -File .\build_official_mod.ps1 -GameDir 'E:\SteamLibrary\steamapps\common\Slay the Spire 2'
```

成功時は `official_mod\bin\Release\net9.0\Sts2Ai.dll` が生成される。通常のAutoslayは次のコマンドで起動する。

```powershell
pwsh -File .\run_official_autoslay.ps1 -Seed FV2EVHXLCW
```

`StopAfterAct` の既定値は `1`、`Visible` の既定値は有効、タイムアウトの既定値は300秒である。`-Visible:$false` を指定するとゲームに `--headless` を渡す。

`-AgentScript .\official_agent.py` を指定すると、ゲーム側BridgeとPythonエージェントを別プロセスで接続する。`-AgentMaxCombats` の既定値は1で、上限を超えた戦闘は元のゲームHandlerへ戻る。`-AgentSimulations` はcombatロールアウトの試行数である。`-StopAfterAgent` または `-StopAfterReward` を指定すると、該当条件でterminal observationを書いて終了する。

実行スクリプトはビルド済みModをゲームの `mods\Sts2Ai` に一時配置し、`%TEMP%\sts2-ai-appdata-*` の隔離AppDataを使う。終了時に一時Mod、隔離AppData、子プロセスを削除する。既存のゲームプロセスや同名Modがある場合は上書きせず失敗する。

## Pythonエージェント

`official_agent.choose` は observation の `phase` に応じて `choose_shop`、`choose_map`、`choose_card_reward`、`choose_rest` を呼び分け、それ以外をcombatとして処理する。

- combat: Sandpitの `Frantic Escape`、Crabの向き変更、potion、条件を満たす `combat.search`、即死攻撃、Defend、カード優先度の順。即死攻撃は攻撃してくる敵を優先し、同点の攻撃はHPの低い敵へ集中する。
- `choose_shop`: デッキのaxis（strike、self-damage、vulnerable、exhaust）を判定し、未所持coreカードのlegal購入を優先する。axisがない場合の候補は `CARD.PERFECTED_STRIKE`、`CARD.RUPTURE`、`CARD.CORRUPTION` である。購入できなければ、strike axisでPerfected Strikeを含むデッキはDefendを、それ以外はStrikeをlegal削除し、最後はskipする。
- `choose_card_reward`: `CARD_TIERS` の S/A/B/C/D を基準にしつつ、デッキaxisに対応するcoreカードを優先する。最高値が0なら `Skip` alternativeを返す。
- `choose_map`: 通常HPでは将来経路のroom valueを最大化し、HPが最大値の2/3以下では到達可能なRestSite、経由Elite数、安全性、room valueの順で選ぶ。
- `choose_rest`: HPが最大値の75%以上なら `HATCH`、負傷中なら `HEAL`、それ以外は `SMITH` を優先する。

combatロールアウトは `CARD_NAMES` と `POWER_NAMES` に登録された要素を対象にし、未対応カードやシミュレータ例外時はヒューリスティックへ戻る。`official_agent.py` の `main` は観測ファイルを25ms間隔でpollし、seqが変わったときだけactionを書き込む。通常例外は指定されたerror logへ追記し、legalな `end_turn` があればfallbackに使う。

## データ生成と検証

```powershell
pwsh -File .\export_enemies.ps1 -Act Overgrowth -Output .\data\enemies_overgrowth.json
pwsh -File .\export_map.ps1 -Seed FV2EVHXLCW -Act Overgrowth -Output .\data\map.json
python .\act_map.py .\data\map.json --show-path
```

`export_enemies.ps1` はゲームDLLから敵・遭遇・状態機械を取得する。既定のformationサンプル数は4096であり、有限サンプルである。`decompile_game.ps1` で逆コンパイルソースを作り、`extract_effects.py` で敵performメソッドの効果をJSONへ追加できる。

Pythonテストは標準ライブラリの `unittest` を使う。

```powershell
python -m unittest discover -p 'test_*.py'
```

保存済みの公式成果物は `data/official_act1_result.json`、`data/official_agent_trace.jsonl`、`data/official_act1_map.json` などである。成果物の値は保存時点のゲームバージョン・seedに対する検証入力であり、任意seedの成功やAIの最適性を保証しない。

## 制約

- C# BridgeはゲームDLLの内部APIと `v0.107.1` に依存する。ゲーム更新後はビルド、データ再生成、公式実行を再確認する。
- Bridgeは一時JSONをrenameするpolling方式で、action待ちは最大2分である。agent停止時はタイムアウトまたは安全側のskipになる。
- `ShopBridge` は合法な購入・削除候補を提示し、応答がなければskipする。Pythonの `choose_shop` はaxis gating済みの候補から1 actionを選ぶだけで、価格計算や複数actionの経済最適化は行わない。
- `EventBridge` は汎用イベントエージェントではなく、利用可能なら `BYRDONIS_NEST` のTAKEだけを自動選択する。
- `combat.py` は近似モデルであり、未対応の敵効果・条件・カード・powerでは探索を諦めるか `NotImplementedError` になる。ロールアウトの評価は最適性の証明ではない。
