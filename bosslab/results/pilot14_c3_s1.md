# PILOT-14: C3(S1) の実装

ゲーム起動なし。走行中の mods 配置には触れていない。CPUは2コア。

## 1. ブランチとcommit

- `cand/engine-pack5`、worktree `~/.sts2/wt-clear5g`、base は C2 の `c64851e`。`4d505f4`（ショップ強化レリック）は入れていない。
- commit `e68f830`（1 commit）。変更は `official_mod/RestBridge.cs` のみ。

## 2. 変更内容（S1）

`SmithCardSelector.Score` を、強化でダメージが増える攻撃札の順に変えた。

- 攻撃札: `1000 + 強化ダメージ増 × 10 + 基本ダメージ`。増分は `combat.py` の `CARD_UPGRADE_DAMAGE`
  （逆コンパイル由来。Bludgeon/Break +10、Cinder/Ultimate Strike/Unrelenting +6、…31枚）を C# 側の表に写した。
  同点は `CARD_DAMAGE`（40枚）で割る。
- 攻撃札以外: `100 + 旧スコア/10`。**攻撃札が1枚でも強化可能なら、必ずそちらが先**。
  攻撃札が無い（全部強化済み、またはデッキに攻撃が無い）ときは旧スコアの順で選ぶので、forgeを空打ちしない。
- 旧スコアの特別扱い（RUPTURE 1200、ボス近傍の強ブロック 1000+、PS/HELLRAISER 700 など）は
  `LegacyScore` に移し、**攻撃札には適用しない**（アームはダメージ順のみだったため）。
  攻撃札以外の順序はアームと同じく「旧順のまま」。

アームとの差: アームは全カードを (強化ダメージ増, 基本ダメージ) で並べたため、攻撃が無いときは
非攻撃札が元の順で並ぶ。実装は同じ状況で旧スコア順になる。攻撃が無いSMITHは稀なので、モデルは測り直していない。

## 3. DLLと検証

- worktree でビルド: `pwsh -File ./build_official_mod.ps1 -GameDir '<macのSteamパス>'`（成功、警告0・エラー0）。
- 新しい `official_mod/bin/Release/net9.0/Sts2Ai.dll` の sha256:
  `7de9f624f3eb8a5c4f121436857454bd259b77a1f657f2e5e811b6c1d7248980`（266,240バイト）
- main の DLL: `592dc5411a6efda58ef6bb47dd2d22f7429310aae24d6b2ec8667363fd82aede`（264,192バイト）。
  差は RestBridge.cs の変更のみ（worktree の git status は RestBridge.cs だけが変更、他は c64851e と同一）。
- Python は base と同一: `official_agent.py` `1f64c0f0fa9fad0c`、`combat.py` `932d286163b6071c`。
- テスト: 860件中854成功・6失敗。C2（base）と同じ6件で、増えていない
  （ショップ順3件、防御不足3件）。

## 4. SMITHの強化先が変わるrun数（開発用135 seed）

traceのSMITH（`phase=rest, option_id=SMITH`）の直後の戦闘で「新しく強化された札」を観測し、
同じデッキに対して新順序の1位を比べた。

- 対象284回のうち、**256回（90%）で強化先が変わる。run数では119/135**。
- 踏破4本もすべて変わる: 895C061BBB 7回、4FDF910744 2回、665CF52D37 1回、C5989A3E01 2回。
  そのまま報告する（候補を合わせない）。

## 5. 留保

- デッキの `deck` 列は強化状態を持たないため、強化先の同定は戦闘行の `upgrade` フラグの差分で行った。
  同じIDの2枚目を区別できないが、ID単位の比較には足りる。
- 攻撃が無いときの順序だけアームと実装が違う（上記）。モデルは測り直していない。
