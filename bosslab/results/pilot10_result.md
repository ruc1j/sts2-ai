# PILOT-10: 札ごとの配対とC3

ゲームは起動していない。C1の踏破runの決定を消さないことを、変更前にtraceで確認した。

## 1. 札ごとの配対（C1が持ち、対照が持たない組）

取得は報酬・ショップの購入で判定。序盤/以降は最初のINSATIABLE戦（Act 2ボス）より前かで分けた。

| 札 | 時期 | n | 到達 改善/悪化/同値 | Act2突破 | 踏破 |
| --- | --- | ---: | --- | ---: | ---: |
| DEMON_FORM | Act1 | 29 | 10/7/12 | 6 | 1 |
| RUPTURE | Act1 | 43 | 7/16/20 | 4 | 1 |
| INFLAME | Act1 | 12 | 3/3/6 | 2 | 0 |
| CRIMSON_MANTLE | Act1 | 14 | 4/2/8 | 1 | 0 |
| RUPTURE | 以降 | 4 | 3/0/1 | 3 | 0 |

RUPTUREを燃料（RUPTURE以外の自傷札）で分けた:
- 燃料あり n=33: 改善9/悪化11、Act2突破 C1 14 対照 12
- 燃料なし n=14: 改善1/悪化5、Act2突破 C1 2 対照 5

さらに燃料なしを取得経路で分けると:
- 報酬で取った n=10: 改善0/悪化5、Act2突破 C1 2 対照 5（明確に悪い側）
- ショップで買った n=4: 改善1/悪化0（悪くない）

DEMON_FORMのAct 1取得は改善10/悪化7で、害は見えない。INFLAMEは同数。

## 2. 踏破runと削り不足のデッキ比較（拡張）

踏破8本（C1の3本＋既知5本。N8CQ4ZKP2Wの重複は除き、未記録2本は時間切れで未抽出）と、
v23+v24のQueen削り0.3未満44戦の比較。

| 札/レリック | 踏破 8本 | 削り<0.3 44戦 |
| --- | ---: | ---: |
| SQUASH | 3/8 (38%) | 3/44 (7%) |
| FORGOTTEN_RITUAL | 2/8 (25%) | 1/44 (2%) |
| MAD_SCIENCE | 4/8 (50%) | 7/44 (16%) |
| PYRE | 1/8 (13%) | 5/44 (11%) |
| WAR_PAINT（強化レリック） | 0/8 | 11/44 |
| WHETSTONE | 0/8 | 5/44 |

- SQUASHとFORGOTTEN_RITUALは踏破側に多い。どちらも報酬で取れる。
- MAD_SCIENCEは報酬に一度も出ない（272runで0）ので候補にできない。
- 強化系レリックは踏破側にむしろ少ない（WAR_PAINT 0/8 対 11/44）。
- 件数が小さいので差とは呼ばない。

## 3. SMITHの強化先（RestBridge.cs:119）のengine順位

点数は RUPTURE 1200（Act 3のボス近傍でRUPTURE所持時）、強ブロック1000+、PERFECTED_STRIKE/HELLRAISER 700、
RUPTURE系680、CORRUPTION系660、INFLAME/PRIMAL_FORCE/DOMINATE 640。**DEMON_FORMとCRIMSON_MANTLEは
明示がなく既定の300**。

DLLは変えない。理由: (a) DEMON_FORMを持つrunはC1でも少なく、forgeの1枚が勝敗を動かす証拠がない、
(b) 変更はDLL再ビルドと照合を伴い、今回の45分では検証できない、(c) 現状の順位でもINFLAMEは640で
RUPTUREは1200と高く、engine札は既に上位に入っている。

## 4. C3の候補（1つ）

**報酬のRUPTURE優先に燃料条件を戻す（ショップは据え置き）。** 既存のpin
`test_reward_does_not_seed_rupture_without_any_fuel` と同じ規則で、C1の1節の数字（報酬経由の燃料なしは0改善/5悪化）が根拠。

踏破3本のengine採用が消えないことの確認:
- 4FDF910744: ショップseq100でRUPTURE購入（報酬ではない）、seq355の報酬は既にBLOODLETTING所持で燃料あり → 影響なし
- 895C061BBB: INFLAME（対象外）
- 665CF52D37: DEMON_FORM（対象外）

## 5. 実装

- ブランチ `cand/engine-pack3`、worktree `~/.sts2/wt-clear5e`、base C1 `8422e56`、commit `c64851e`。
- `official_agent.py` sha256 先頭 `1f64c0f0fa9fad0c`、`combat.py` `932d286163b6071c`（C1と同じ）、DLL `592dc5411a6efda5`（mainと一致）。
- テスト: 860件中854成功・6失敗。C1の10件から4件（RUPTURE燃料、uncommitted RUPTURE、PS軸、tier札）が戻り、
  残る6件はショップ順3件と防御不足3件（C1のengine優先そのものの帰結）。

## 6. 留保

- 1節は「C1が持っている」こととの相関で、取得の因果ではない。
- 2節の踏破8本は重複を除いた小さな標本。
- 削除系の候補（基本札削除の優先）は、踏破2/3本のショップ決定に触れるため採らなかった。
