# confirm5 忠実性不一致（deck.multiset 強化値）の機構 — Bellows（T44、2026-10-29）

解析のみ。実機・ビルド不使用。DLL をデコンパイルした C# を根拠に、T42 の仮説を実体のある説明に置き換える。
対象 2 組（`act3_confirm5_breakdown.md` §1）: spec 0256297739fc の DEFEND_IRONCLAD・METAMORPHOSIS、spec
c247ea1ceac4 の DEMON_FORM。いずれも記録 +0 → lab +1。

## 結論（T42 仮説の実体）

原因レリックは **RELIC.BELLOWS**（両方 の deck に共通して入っている）。Bellows が入場 1 ターン目に
**引いた手札（opening hand）を丸ごと強化する**ので、BossLab 再走では**シャッフルし直した opening hand** が
元の run と違うカードになる → Bellows が強化するカード集合がずれ、deck.multiset の強化値だけが食い違う。
HP 二重発火ではなく、STONE_CRACKER と同系統の「入場効果を lab で再発火させると別のカードに載る」問題。
Bellows は `bosslab/tools/relic_entry_effects.py` の `ENTRY_EFFECTS` に未登録で、いまは lab で再発火している。

## 機構（デコンパイル根拠）

`MegaCrit.Sts2.Core.Models.Relics/Bellows.cs:15-27`（Rare）:

```csharp
public override Task AfterPlayerTurnStart(PlayerChoiceContext choiceContext, Player player) {
    if (player != Owner) return Task.CompletedTask;
    if (Owner.PlayerCombatState.TurnNumber > 1) return Task.CompletedTask;  // 1 ターン目の開始だけ
    Flash();
    CardCmd.Upgrade(PileType.Hand.GetPile(Owner).Cards, CardPreviewStyle.HorizontalLayout);
    ...
}
```

- 鈎: `AfterPlayerTurnStart`（プレイヤーターン開始時）。`TurnNumber > 1` で return するため **1 戦闘につき 1 ターン目の
  開始の 1 回だけ**発火。戦闘ごとに `PlayerCombatState.TurnNumber` は 1 からなので、lab の単一戦闘で**二度発火はしない**。
- 対象: 鈎が走った瞬間の `Hand` の全カードを `CardCmd.Upgrade`（選定なしで手札ごと強化）。どのカードが強化されるかは
  **その戦闘の opening hand（引く順）で決まる＝乱数**。
- 2 組への対応: 0256297739fc はその run の opening hand に DEFEND_IRONCLAD と METAMORPHOSIS（とも Skill）が
  入っていたのでこの 2 枚が +1、c247ea1ceac4 は DEMON_FORM（Power）が入っていたのでその 1 枚が +1。型の違うカードが
  強化されるのは手札を type 無関係でまとめて強化する挙動と一致（Whetstone は Strike/防御のみ、LetterOpener は
  条件付き Skill なので DEMON_FORM を説明できない → T42 が挙げた候補ではなく Bellows）。
- 記録側の強化前/後の問題ではない: 記録（spec）は元の run が Bellows を発火させた**後**の deck を写しており、
  元の opening hand に入ったカードは +1 で記録されている。lab 側が +1 にした別カード（元の run では draw pile
  にあって +0）が食い違いとして出る。つまり差分は「強化されたカードが違う」ことで、lab 側が BossLab の draw
  再シャッフルで別の opening hand を引いたために起きる（`bosslab_act3_plan_fid6.md` の「同じ seed でも引く順は
  元の run と完全には一致しない」注記と同じ根）。

## 修正案（1 つ、実装しない）— 20892cd の書き戻しに足せるか

Bellows を STONE_CRACKER と同じ `defer_relic_addition` に分類し、room entry 後に attach して鈎を lab で発火
させない（`relic_entry_effects.py` の `"RELIC.BELLOWS": {handling: defer_relic_addition, hook: AfterPlayerTurnStart,
calls: CardCmd.Upgrade, evidence: Bellows.cs:15-27}` を追記。`defer_relics_for` が拾い、`make_bosslab_plan.py` は
既に trial へ `defer_relics` を書いている: 249 行近傍）。

- deck.multiset（位置を捨てる多重集合）で一致を見る限り、強化値は**カード自体に付いた記録値**が plan の `deck`
  （記録 upgrade を運ぶ、221 行近傍）で入場時に再現される。Bellows を defer すれば lab で再強化されないので、
  記録どおりの +1/+0 のままになり、opening hand がどれだけシャッフルされてもカードごとに強化値が付いたまま＝
  multiset は記録と一致する。→ 「deck の強化値を記録値で上書き」は、追加機構なしで、Bellows defer だけで成立。
- 既存書き戻し案（20892cd）への相性: 20892cd は入場の**敵 HP と pile（hand/draw/discard/exhaust のカード並び）**
  を記録値で復元する hook（default off）。Bellows の multiset 一致には上記 defer で足り、20892cd の pile 復元は
  opening hand の**中身まで**完全に再現したいときに同じ記録源を共有する。両者は同じ「入場効果を記録時点で凍結し、
  lab で二重に走らせない」設計に載るので、Bellows defer は 20892cd に素直に足せる（新機構は要らない）。
- 実装上の確認 needed（未実行）: BossLab が plan `deck` の upgrade 値を entry deck にそのまま載せること（載せる
  なら defer だけで multiset 一致）、および 20892cd の hook を on にして pile を復元した場合、Bellows が defer
  されていれば鈎が走らず記録強化が二重適用されないこと。この 2 点は実機 1 走（fid6 系）で確かめる。

## 未確定（実機で確かめる）

- fid6 の旧 trace 12 組 0/12 一致・不一致は `relic_counters` のみ（leader 記録済み）。これは Bellows とは別系統
  （カウンタ書き戻しが旧 trace で入場一致を出せていない話）で、本 doc の deck 強化漂移とは無関係。
- Bellows の「手札ごと強化」がプレビュー経由でプレイヤー選択を伴う運用かどうか（`CardCmd.Upgrade(Hand.Cards, ...)`
  の collection 版）は BossLab 自動戦闘での挙動を実機で確認。multiset 判定には影響しない。
