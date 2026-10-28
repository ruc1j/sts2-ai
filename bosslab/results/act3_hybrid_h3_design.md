# 次 goal 候補 H3 の設計（Amalgam を「実際に削る」を保証する規則 2 案）

dev2 base の観測（手番ごとの Amalgam 実効 HP と、その手番に出せる最大ダメージ・予想被ダメ）から再現した
殴り先の一覧。本 doc は次の goal の候補であり、今の goal（hybrid）の判定には使わない。手番表の生データは
bosslab/results/act3_queenfirst_h1h2_dev2.md（reproduce_h_targets.py、base 観測に各ポリシーを流す）。

## 前提: H1/H2 が試されなかった理由の再現

- dev2 base 観測（base が Amalgam を削った後の盤面）に対する各ポリシーの A/Q 選択（97 手番、集計）:
  - base A=55 Q=24（Amalgam 優先）
  - queenfirst A=16 Q=68（Queen 優先、A は Amalgam が lethal 撃破可能な手番のみ）
  - H1 A=26（vs queenfirst 10 手番差）、H2 A=19（vs queenfirst 3 手番差）
- ここでの H1 の A=26 は、base 盤面がすでに Amalgam を ≤50 まで削っている手番で発火した数。実走の H1 は
  自身は Queen 優先なので Amalgam が 199 付近に留まり ≤50 に届かず 0/12 発火（act3_dev3_interpretation.md）。
  つまり本表は「base が削った盤面を各候補が見たら」の反事実で、live の自己閉鎖とは区別が必要（下記）。

## 設計（規則生成は make_h_candidates.py、エージェントは bosslab/agents/official_agent_H3*.py）

H1 型（Amalgam 実効 HP 基準）は「Amalgam が既に低い」ことを条件に含むため、Queen 優先で走ると条件が永久に
発火しない（鶏と卵）。よって削りを保証する設計は、Amalgam 自身の低さではなく、ターン状態か被ダメ脅威で
発火させる。2 案＋診断 1 案。

- H3a 序盤 Amalgam 削り（`QUEENFIRST_H3_OPEN_TURNS=2`）: 最初の 2 プレイヤーターンだけ Amalgam が生きていれば
  殴り、以降 Queen。Amalgam が死んだ/消えれば実効 HP 0 で Queen へ自己律速。手番基準なので盤面が如何ようと
  1〜2 手番目に必ず発火＝削りを保証。live でも Queen 優先の自己閉鎖にならない。
- H3c 危険前に削り（`QUEENFIRST_H3_DANGER_FRAC=0.5`）: Amalgam の次手番の予想被ダメが (HP+ブロック) の 5 割
  以上で、かつ Amalgam が生きている間だけ殴り、それ以外 Queen。自 HP 基準なので Amalgam 実効 HP に依存せず
  発火する。Amalgam は Queen 戦で唯一の定常ダメージ源なので、大半の手番で発火＝常時削りに近い（base に近い
  挙動）。被ダメが小さい（Amalgam 死亡後・自分が堅い時）だけ Queen に切替。
- H3b 閾値上げ診断（`QUEENFIRST_H3_AMALGAM_HP=150`、H1 と同形）: 実効 HP ≤150 で Amalgam。base 盤面では A=44
  と発火が多い（base が ≤150 まで削っているから）。だが live で Queen 優先から始めると Amalgam は 199 から
  削られず 150 に届かないので発火せず、結局 queenfirst に落ちる見込み。閾値を上げてもトリガーが「Amalgam が
  既に低い」前提を消せないことを示す診断。

## 手番ごとの選択（代表 trial、act3_queenfirst_h1h2_dev2.md より）

| turn | Amalgam実効HP | 予想被ダメ | HP+blk | base | queenfirst | H1 | H2 | H3a | H3b | H3c |
|--:|--:|--:|--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 1 | 199 | 18 | 88 | A | Q | Q | Q | **A** | Q | Q |
| 2 | 158 | 18 | 70 | A | Q | Q | Q | **A** | Q | Q |
| 3 | 149 | 36 | 61 | - | - | - | - | - | - | - |
| 4 | 122 | 22 | 22 | - | - | - | - | - | - | - |
| 5 | 105 | 24 | 22 | A | Q | Q | Q | Q | **A** | **A** |
| 6 | 39 | 48 | 8 | A | Q | **A** | **A** | Q | **A** | **A** |

（trial 0000。bold=Amalgam を選んだ差分手番。HP+blk=その手番の生存値。base が 1〜2 手番で Amalgam を 199→158→149→122→105→39 と削っている。）

読み取り: H3a は 1〜2 手番に base と同じく Amalgam を殴り、3 手番以降 Queen（=序盤だけ削りて Queen 集中）。H3c は Amalgam が自分を殺しうる水準（5〜6 手番、被ダメが生存の 5 割超）で Amalgam を殴り、堅い序盤（1〜2 手番、被ダメ 18 程度）は Queen。H3b は base 盤面では 5 手番（105≤150）から発火するが、live で Queen 優先なら Amalgam が削れず 150 不到達＝発火しない。

## 集計（全 12 trial / 97 手番、dev2 base 盤面）

| 方針 | A 手番 | Q 手番 | 攻撃以外 | queenfirst と異なる手番 |
|--:|--:|--:|--:|--:|
| base | 55 | 24 | 18 | (base 基準) |
| queenfirst | 16 | 68 | 13 | 0 |
| H1 | 26 | 58 | 13 | 10 |
| H2 | 19 | 65 | 13 | 3 |
| H3a | 32 | 52 | 13 | 16 |
| H3b | 44 | 40 | 13 | 28 |
| H3c | 29 | 55 | 13 | 13 |

（A/Q は Amalgam を殴った/Queen を殴った手番数。live で Amalgam が消えた後の手番は A/Q に出ない。）

## 総火力/ターン・各軸への影響の予測（live、軸ごとに整理）

注: 総火力/ターンはエネルギーで律速される毎ターンの出力レイトに近いため、target の割き方だけで総火力/ターン は
あまり動かない。動くのは (1) その出力が Queen に行くか Amalgam に行くか、(2) Amalgam 早処理が被ダメと生存ターン
をどう変えるか。以下 live 想定。

- H3a（序盤削り）: Queen 削り ↓（序盤 2 出力を Amalgam に割く）、Amalgam 撃破 ↑ただし N=2 では 199 を削り切れず生存、生存ターン ↑（序盤の Amalgam ダメージと Queen buff を 2 分削る）、win: 序盤の被ダメ削減が致死一手を遅らせる分だけ微増の見込みだが N 依存。N を増やすと Amalgam 撃破と生存は ↑、Queen 削りは ↓（base に寄る）。掃き込み域は N=1..4 程度を live で測る価値。
- H3c（危険前に削り）: Amalgam 撃破 ↑↑（脅威ターンの大部分で削り、殺せる）、生存ターン ↑（唯一の定常ダメージ源を恒久的に消す）、Queen 削りは queenfirst 比 ↓（脅威ターンを Amalgam に割く）だが生存が延びれば総 Queen ダメージは挽回の余地、win: base 系より Amalgam 早殺し・堅い時に Queen 集中で最も有望だが、脅威判定が Queen 集中を遅らせ過ぎて Amalgam 処理に over-invest するリスク（frac を上げる、例 0.6〜0.75）。base と H1/H2 の中間を狙う。
- H3b（閾値上げ診断）: live で Queen 優先スタートだと Amalgam が削れず 150 不到達→発火せず queenfirst に収束（＝H1 と同じ失敗の再現時験）。閾値を実効 HP 起点ではなく「Amalgam を N 分削った／最初の K ターン」等の経過量基準にしない限り、閾値上げだけでは自己閉鎖は解けない。次 goal では「削りの経過量」で切る H3a 系と、「被ダメ脅威」で切る H3c 系の 2 系統で確定させ、純粋な閾値 H1/H3b は落としてよい。

## 次の goal への推奨と issue #6 要約

推奨: 削りを保証する 2 系統を実測する。
1. H3a（序盤 N ターン Amalgam、`QUEENFIRST_H3_OPEN_TURNS`）— 手番基準で必ず発火。N=2 を基準に 1〜4 を sweep。
2. H3c（Amalgam の予想被ダメが生存の割で閾値超の間だけ Amalgam、`QUEENFIRST_H3_DANGER_FRAC`）— 被ダメ脅威基準で必ず発火。frac 0.5 基準に 0.4〜0.75 を sweep。
H3b（閾値 150）は診断で「閾値上げだけでは自己閉鎖が解けない」ことを確認するため 1 セットだけ流す。
測定は confirm4 と同じ新規 panel（開手札ランダム付与系・PAELS_CLAW・PENDULUM 除外済み、コミット 0e060c6）で、base・H1（記録）・H3a・H3c を同一 entry 配対。判定は事前登録規則（コミット 4693f2e）をそのまま使う（主=Queen 削り割合と総火力/ターン、火力/勝利が base 以上、確認用で p<=0.05、両集合同方向）。

issue #6 要約（次の goal 候補）:
- 現状 dev2 で「Amalgam を倒せる状況では優先」は実質未試行（H1/H2 は queenfirst に収束）。Amalgam を実際に
  削る保証設計が空白。
- H3a（序盤 N ターン Amalgam、手番基準で必ず発火）と H3c（Amalgam 予想被ダメが生存の割で閾値超の間 Amalgam、
  脅威基準で必ず発火）の 2 系統が候補。H3b（閾値上げ）は閾値が「Amalgam が既に低い」前提を消せず自己閉鎖を解かない
  ことの診断。
- 実測は confirm4 の新規 panel で base/H1/H3a/H3c を同一 entry 配対、判定は事前登録規則のまま。軸別の予測は上の
  とおり（総火力/ターンはレイト律速で動かず、Queen 削り・Amalgam 撃破・生存ターンが動く）。
- 並行して、target 割き方以前に火力上限（engine 札・Strength 立ち上げ）が Act3 踏破の本丸の可能性を別 track で検証。
  TEST_SUBJECT 見積もりは act3_test_subject_lab_estimate.md（T21.5）。
