# dev2 3-arm 結果の解釈（H1 で Amalgam 撃破 9/12→0/12 になった理由）

dev2 3-arm（base/H1/H2、`data/bosslab_act3_dev3_*`）の結果を、事前登録した判断規則（コミット 4693f2e）に当てはめた解釈。規則は動かさない。集計は act3_dev3_compare.md、base 単体記述は act3_dev3_base_desc.md。

## 結論

- 両候補とも主信号「総火力/ターン」が base を下回った（H1 37.4→32.9、H2 37.4→35.7）ので選定条件を満たさず、hybrid は進めない。規則どおり dev2 で Queen 削りの差が最も大きい H1 を 1 本だけ記録用に confirm4 へ進める（採用の約束ではない）。
- H1 の Amalgam 撃破 9/12→0/12 は leader の見立てどおり「H1 は Amalgam 実効残 HP が 50 以下のときだけ殴るが、Queen を先に殴るので Amalgam が 50 まで削れず閾値に一度も届かない」で確定。実測で裏を取った（下記）。
- H1 は実質 queenfirst と同じ動きになった。次の goal 候補に「Amalgam を殴るトリガーを、削れる前に自発的に発火させる設計」を置く。

## 検証: 手番ごとの Amalgam 実効 HP（実走 H1 トレース）

H1 のコードは `bosslab/agents/official_agent_H1.py` の `focus_to_amalgam = queen_present and 0 < _amalgam_effhp <= 50`（実効 HP = hp+block、`QUEENFIRST_H1_AMALGAM_HP=50`）。50 以下でのみ Amalgam、それ以外は Queen を殴る。

### dev3 H1（候補）
| trial | 入場Amalgam実効HP | 戦闘中Amalgam実効HPの最小 | ≤50到達 | Queen最終HP |
| --:|--:|--:|:--:|--:|
|    0 | 199 | 120 | No | 251 |
|    1 | 196 | 111 | No | 252 |
|    2 | 199 | 191 | No | 270 |
|    3 | 199 | 199 | No | 234 |
|    4 | 199 | 156 | No | 257 |
|    5 | 199 | 178 | No | 143 |
|    6 | 196 | 167 | No | 228 |
|    7 | 196 | 159 | No | 293 |
|    8 | 196 | 147 | No | 248 |
|    9 | 199 | 178 | No | 244 |
|   10 | 199 | 163 | No | 204 |
|   11 | 196 | 184 | No | 226 |

12 trial すべて、戦闘中の Amalgam 実効 HP の最小が 111〜199 で 1 度も 50 に届かなかった。＝50 判定が一度も発火せず、H1 は全ターンの攻撃を Queen に入れた（Amalgam 単独撃破 0/12）。

### dev3 base（比較用）
| trial | 入場Amalgam実効HP | 戦闘中Amalgam実効HPの最小 | ≤50到達 | Queen最終HP |
| --:|--:|--:|:--:|--:|
|    0 | 199 | 20 | Yes | 345 |
|    1 | 196 | 5 | Yes | 297 |
|    2 | 199 | 64 | No | 377 |
|    3 | 199 | 26 | Yes | 387 |
|    4 | 199 | 34 | Yes | 264 |
|    5 | 199 | 13 | Yes | 175 |
|    6 | 196 | 12 | Yes | 332 |
|    7 | 196 | 4 | Yes | 369 |
|    8 | 196 | 2 | Yes | 220 |
|    9 | 199 | 8 | Yes | 227 |
|   10 | 199 | 8 | Yes | 237 |
|   11 | 196 | 32 | Yes | 325 |

base は 11/12 で Amalgam 実効 HP が 50 以下（単桁まで削る組が大半）に達し単独撃破 9/12（閾値に届かなかった idx2 のみ未撃破）。base は毎ターン Amalgam を削るので閾値まで落ち、H1 は Queen に割くので落ちない。

## なぜ自己閉鎖になるか

H1 の Amalgam 攻撃条件は「Amalgam が 50 以下」だが、Amalgam を削れる唯一の手段が Amalgam を殴ること。デフォルトが Queen 優先なので Amalgam は入場値 199 付近に留まり、条件は永久に発火しない（鶏と卵）。50 は 1 ターンで倒せる上限だが、199→50 は約 150 削る必要があり、その 150 を入れる先が Amalgam 以外にない。一度 Queen に流れ始めると戻れず、H1 は「低くなったら掃除」ではなく最初から Queen 固定（=queenfirst）として振る舞い、Amalgam は Queen と道連れ死亡するか生き残るかだけで単独撃破 0/12 になった。

この結果は事前登録の規則（火力ゲートで両候補落選）の判定を変えない。H1 が queenfirst と同挙動だった事実は、規則の適用結果（削りゲートは H1 が満たすが火力ゲートで落選）と矛盾しない。

## 次に試す候補（規則は変更せず、次 goal 用の案）

1. 序盤 N ターンは Amalgam を削る設計: 入場で Amalgam は Queen を buff し自身も殴る脅威。最初の 2〜3 手番で Amalgam を削って実効 HP を閾値内へ能動的に下げてから Queen 固定。≤50 自己閉鎖を解く。
2. 閾値を上げる: Amalgam を殴る条件を 50 より上（例 120〜150 以下、または「未処理なら」）にすればトリガーは発火する。発火が早すぎると base（Amalgam 優先）に寄って Queen 削りが落ちる。50 と base の間の掃き込み域を探す。
3. 火力上限そのものの検証: どちらの target 方針も 12 trial で 1 勝なし。Queen 400+Amalgam 199（+Queen buff）に base 火力/t 37.4・生存 8 ターン=総ダメージ約 300 で必要量に大幅不足。target の割き方以前に、勝ちうる火力（engine 札・Strength 立ち上げ）が出ているかを測る方が本丸の可能性が高い（前回 queenfirst で火力/t 300→213 と落ちた報告と同根）。
4. 別ボス（TEST_SUBJECT, 3 形態）の見積もりは act3_test_subject_lab_estimate.md（T21.5、余力）に置く。

注: dev3 base/H1/H2 は HP 即時 clamp 修正 927f26f 導入前の DLL で実行済み。idx11（ROYAL_POISON）は絶対注意対象で dev3 の全腕で同じ制約下。上記 Amalgam 解析は Queen/Amalgam の HP 減少の観測のみで入室 HP のズレの影響は受けない。
