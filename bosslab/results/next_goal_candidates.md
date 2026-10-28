# 次の goal の候補（優先順、1 ページ）

goal 直後の空白なく着手できるよう、軸は「必要な実機時間」「効く見込み（判定を前に進める力）」「忠実性への影響」で
並べた。上ほど ROI が高い（少ない手間で判定・忠実性を前に進める）と判断。依存関係は脚記。

## 順位

| 順 | 候補 | 必要な実機時間 | 効く見込み | 忠実性への影響 | 根拠・前提 |
| --- | --- | --- | --- | --- | --- |
| 1 | PenNib 入場カウンタの反映（MOD 改修＋抽出） | 改修はビルドのみで 0（ゲーム不要）。次項の新 spec 採取時に 0 分追加 | 判定は動かない（配対で両腕共通）が、忠実性の残り 5 件の 3 件（PEN_NIB）を消す | 正面改善。`relic_counters` 列を持つ新 build の観測から採る限りの実装（案は `act3_pennib_entry_plan.md`） | 2 の新確認用 spec を現行 DLL で採る前にこれを入れると、その集合はカウンタ付きで clean。単独では決定を出さないが 2 の入力品質を決める |
| 2 | H3a・H3c の実機比較（新しい確認用集合） | 中（base/H3a/H3c 各 12、最大 36 trial、1 trial 上限 700 秒） | 高。H1/H2 が dev2・confirm4 で一度も発火せず実質 queenfirst だった「Amalgam を倒せる状況で優先」機構を、手番/脅威基準で実際に発火させて測る = goal の未検証の空白を埋める本命 | 中立（配対なので入場状態のずれは両腕相殺）。ただし新 spec は 1 の実装入り DLL で採る | H3a/H3c は実装済・単体テスト 14 pass（commit 2b6ef0f）、dev2 base 上の手番表で H3a A=32 / H3c A=29（`act3_queenfirst_h1h2_dev2.md`）。使用済み spec と重複なしの新 12 件を選ぶ |
| 3 | Act 3 フル run パネル（踏破率の実測） | 大（1 戦闘だけでなく run 全体を完走、多数 seed 必要） | 最高得点だが本命ではない。EVALUATION.md の主指標 Act3 踏破率は lab では測れないので、採用を最終確定するなら必要 | 低（フル run は実走そのもの＝忠実性の話ではない） | lab の削り/火力代理で候補が採否条件を通った後に行う。2 の判定が出てから |
| 4 | Act 2 Shrug の測り直し | 中（base/候補 各 2×10、除外 1 件の差し替え） | 中。別系統の再測定。忠実性棚卸しで除外は RELIC.PENDULUM spec 1 本のみでよく、plan 作り直しは配対が成り立てば不要と確定済み | 改善済（PANTOGRAPH・STONE_CRACKER は BossLab 処理済みで除外不要。`act2_shrug_fidelity_stocktake.md`） | 現在の Act 3 hybrid goal とは独立の別 goal。着手順序は 2/3 の次 |
| 5 | TEST_SUBJECT 用の標本集め | 小〜中（spec 採取の run 本数次第、背景で流せる） | 低（即時の判定は出さず、別 agent 系統の準備） | 中立 | lab 見積は `act3_test_subject_lab_estimate.md` に既にある。標本（新 spec）採取は他候補の実機を待たせる隙間で回す |

## 補足

- 1 と 2 は束ねる：先に PenNib 反映（改修・ビルドのみ、dsh 側で実施可）を入れ、そのビルドで 2 の新確認用 12 spec を採れば、カウンタ起因の忠実性不一致を含まない集合で H3a/H3c を測れる。2 だけの新 spec を旧 build で採ると PEN_NIB 不一致が again 残る。
- 忠実性の残り 5 件のうち Whetstone/NewLeaf（0007 の deck 漂移）と 0011 の敵入室 HP は、配対比較で両腕共通なので判定には効かない（`act3_confirm4_fidelity_causes.md`）。これらを直すすべは goal の判定と直交するので、優先は 1（カウンタ）＞ 適宜（残 2 種は次 build で spec を採り直すときにまとめて直す）。
- 実機 run は leader、dsh 側はゲームを起動しない。判定規則（apply_hybrid_rule.py）は 1 回のみ実行が約束で、2 の H3 用に新しい dev/confirm 集合を積むときは同じ規則（commit 4693f2e）を新しい集合に対して別枠で 1 回使う。
