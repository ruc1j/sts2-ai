# STS2 AI

Slay the Spire 2（STS2）の公式ゲームエンジン上で動作する、Ironclad 用の外部 AI エージェント。

Harmony ベースの Mod（C# Bridge）がゲーム内の各フェーズを外部 Python エージェントとファイル経由で接続し、AI が観測・行動を交換しながらランを自動プレイします。マップ経路選定、カード報酬・ショップ・休憩の判断に加え、戦闘はモンテカルロ・ロールアウト（探索）によるシミュレーションで行動を決定します。

## 特徴

- **公式エンジンと連動**: ゲーム DLL を直接操作せず、公式の内部 API に Harmony patch を当てた C# Bridge が観測・行動を仲介
- **フェーズ別ポリシー**: マップ / カード報酬 / ショップ / 休憩 / イベント / 戦闘をそれぞれ専用ロジックで処理
- **シミュレーション駆動の戦闘**: 敵データ（逆コンパイル抽出 + 実トレース検証）を使った近似戦闘シミュレータ上で、各初手から貪欲ロールアウトを回して最善手を選択
- **データ駆動の検証**: 敵・マップ・実戦トレースの保存データでオフライン検証が可能
- **Ironclad に特化**: Strength 軸・Perfected Strike 軸などのデッキ軸を判定し、報酬・ショップ選択に反映

## アーキテクチャ

```text
SlayTheSpire2.exe
  └─ official_mod/Sts2Ai.dll          # Harmony mod（C# Bridge）
       ├─ Entry.cs                    # 初期化・Ironclad固定・seed指定
       ├─ CombatBridge.cs             # 戦闘フェーズの観測・行動交換
       ├─ MapBridge.cs                # マップフェーズ
       ├─ RewardBridge.cs             # カード報酬フェーズ
       ├─ RestBridge.cs               # 休憩フェーズ
       ├─ ShopBridge.cs               # ショップフェーズ
       └─ EventBridge.cs              # イベント（Byrdonis の巣）の固定選択
                ▲
                │ observation.json / action.json / trace.jsonl
                ▼
official_agent.py                     # フェーズ別 Python ポリシー
combat.py                             # 複数敵の近似戦闘シミュレータ + ロールアウト
ironclad.py                           # 独立した単一敵 MCTS モデル
act_map.py                            # マップ検証・経路列挙
extract_effects.py                    # 逆コンパイル C# から敵効果を抽出
data/                                 # 敵・マップ・trace・実行結果
test_*.py                             # unittest
```

C# Bridge はゲームの `sts2.dll`、`0Harmony.dll`、`GodotSharp.dll` を参照する `net9.0` プロジェクトです。対応ゲームバージョンは `v0.107.1` 以降です。

## 必要環境

- Slay the Spire 2（Steam 版）
- .NET SDK 9.0
- Python 3.10+
- PowerShell 7（`pwsh`）

### 対応プラットフォーム

Windows と macOS の両方で全パイプラインが動きます。`pwsh` と `dotnet` はどちらもクロスプラットフォームで、`sts2.dll` は名前に反してマネージド .NET アセンブリなので macOS の `dotnet` からそのまま読めます。逆コンパイル（`decompile_game.ps1` の `ilspycmd`）も macOS で動きます。

違いはパスと隔離の有無です。

| | Windows | macOS |
| --- | --- | --- |
| ゲーム本体 | `<GameDir>\SlayTheSpire2.exe` | `<GameDir>/SlayTheSpire2.app/Contents/MacOS/SlayTheSpire2` |
| ネイティブライブラリ | `<GameDir>` 直下 | `SlayTheSpire2.app/Contents/Resources/data_sts2_macos_arm64/` |
| ユーザーデータ | `%APPDATA%\SlayTheSpire2` | `~/Library/Application Support/SlayTheSpire2` |
| 実行中の隔離 | 一時 APPDATA へコピーして隔離 | **隔離なし。実セーブの `settings.save` を直接書き換える** |

macOS では実行が隔離されないため、計測目的で回すときはユーザーデータを退避・復元するラッパーを噛ませてください。同じ seed でも開始レリックが変わり、前後比較が成立しなくなります。

## セットアップ

### 1. Mod のビルド

```powershell
pwsh -File .\build_official_mod.ps1 -GameDir 'E:\SteamLibrary\steamapps\common\Slay the Spire 2'
```

成功すると `official_mod\bin\Release\net9.0\Sts2Ai.dll` が生成されます。

### 2. 敵データの生成（任意）

逆コンパイルソースから敵の行動効果を抽出し、シミュレータの精度を上げられます。

```powershell
pwsh -File .\export_enemies.ps1 -Act Overgrowth -Output .\data\enemies_overgrowth.json
pwsh -File .\decompile_game.ps1    # ゲーム DLL の逆コンパイルソースを作成
python .\extract_effects.py ...
```

### 3. 実行

```powershell
pwsh -File .\run_official_autoslay.ps1 -Seed FV2EVHXLCW
```

主なオプション:

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `-Seed` | ランで使用するシード | — |
| `-StopAfterAct` | 停止する Act 番号 | `1` |
| `-AgentScript` | 外部 Python エージェント（未指定時はゲーム内 Handler） | — |
| `-AgentSimulations` | 戦闘ロールアウトの試行数 | `1000` |
| `-AgentMaxCombats` | AI が担当する戦闘数の上限 | `1` |
| `-Visible:$false` | ヘッドレス（非表示）で起動 | 表示あり |
| `-TimeoutSeconds` | 実行タイムアウト | `300` |

実行スクリプトはビルド済み Mod をゲームの `mods\Sts2Ai` に一時配置し、Windows では隔離された AppData でゲームを起動します。終了時には一時 Mod・隔離 AppData・子プロセスを自動削除します。手で強制終了すると `mods\Sts2Ai` が残るので、次回起動前に消してください。

`-AgentScript` を渡さないとゲーム内蔵の AutoSlay AI が打ちます。`-AgentMaxCombats` を省くと最初の 1 戦だけが外部エージェント担当になり、以降は内蔵 AI に戻ります。`-StopAfterAct` を省くと Act 1 クリア時点で終了します。**いずれも失敗を報告せず、黙って別のものを走らせます。**

## プロジェクト構成

| ファイル | 役割 |
| --- | --- |
| `official_agent.py` | フェーズ別ポリシーの入口。観測 JSON を 25ms 間隔でポーリングし、行動を書き戻す |
| `combat.py` | 複数敵の近似戦闘シミュレータ。`search` は各初手から貪欲ロールアウトを回して評価する（ランダムプレイアウトではない） |
| `ironclad.py` | 公式 Bridge とは独立した単一敵 MCTS モデル |
| `act_map.py` | マップ JSON の検証と全経路列挙 |
| `extract_effects.py` | 逆コンパイル C# ソースから敵の効果（攻撃・block・summon 等）を抽出 |
| `official_mod/` | C# Bridge ソースとプロジェクト定義 |
| `docs/` | プロジェクト概要・コード Wiki |
| `data/` | 敵・マップ・trace・実行結果の保存データ |

## テスト

```powershell
python -m unittest discover -p 'test_*.py'
```

戦闘シミュレータの単体テストに加え、保存済みの公式成果物（実戦トレース・実行結果）に対する回帰検証も含みます。

## 現状の成果

Act 3（最終 Act）の踏破を確認できたのは、以下の 3 seed です。いずれも公式 `result.json` の `act_3_complete: true` と対応ログが残っています。

| seed | 戦績 | 最終 HP | 決め手 |
| --- | --- | --- | --- |
| `D6A1F8C3E5` | 15戦15勝 | 22/98 | TEST_SUBJECT 第3形態の Intangible（1ターンおきの無敵）をモデル化 |
| `N8CQ4ZKP2W` | 19戦19勝 | 7/81 | Rupture を Bloodletting より先に使い、Vulnerable 込みの複数枚リーサルを認識 |
| `H2LV6ZJ4XW` | 23戦23勝 | 7/130 | 重複購入の抑制と、HP を 1 残す Breakthrough の許可 |

**任意 seed での勝率は低いままです。** 40 seed 規模で回して踏破は上記の 3 本のみで、最頻の敗因は Act 1 ボス VANTOM と Act 2 ボス THE_INSATIABLE です。ここは改善途上であり、README の数字を「このエージェントは強い」と読まないでください。

踏破した 2 本が Rupture + Bloodletting のエンジンを積んでいるのは事実ですが、これは相関であって因果の検証はできていません（Rupture はカード報酬に 1 run あたり 0.3 回しか提示されないため、報酬経由で測る道が塞がっています）。

## 開発の進め方

このリポジトリで方針を変えるときは、**実機 run の前後比較で数字が改善しない限り採用しない**という運用を取っています。詳しい経緯と、測定に否定された仮説の一覧は `docs/CODEWIKI.md` にあります。とくに次の 2 点は繰り返し踏んだ罠です。

- **環境を固定しないと同じ seed でも同じ run にならない。** ユーザーデータのスナップショットと `-AgentSimulations` の値を固定してください。片方でも動くと前後比較は無効です。
- **1 seed の改善を一般化しない。** 変更が発火した seed の結果は、過去 11 周の記録で改善 3・劣化 4・変化なし 1 とコイン投げと区別がつきませんでした。

## 制約・注意事項

- このプロジェクトは公式ゲームの**完全な再実装ではありません**。`combat.py` は近似シミュレータであり、公式エンジンの判定そのものではありません。
- C# Bridge はゲーム内部 API と特定バージョンに依存します。ゲームのアップデート後はビルド・データ再生成・公式実行の再確認が必要です。
- 保存済みの検証データは特定のシード・バージョンに対するものであり、任意シードでの成功や AI の最適性を保証するものではありません。
- 戦闘の評価関数は即時のダメージとブロックを中心に組まれており、見返りが数手先にある札（ドロー・Strength・Power 全般）を過小評価する傾向が残っています。既知の未解決点として `docs/CODEWIKI.md` に実測値とともに記録しています。
- エージェントとゲームの JSON 交換はポーリング方式のため、エージェント停止時は最大 2 分後にタイムアウトまたは安全側のスキップになります。

## ライセンス

本プロジェクトのコードは教育・研究目的で公開されています。Slay the Spire 2 自体の権利は [Mega Crit Games](https://www.megacrit.com/) に帰属します。
