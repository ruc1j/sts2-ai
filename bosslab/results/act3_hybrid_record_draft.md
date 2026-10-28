# Act3 hybrid 候補：実験記録の草稿（docs/ACT3_BOSSLAB_20261028.md への追記案）

EVALUATION.md の記録書式に沿った草稿。confirm4 の実機結果は leader 側で走行中（base、H1 の順）なので、結果欄は空き、確定値は act3_dev3_compare.md / act3_dev3_base_desc.md / act3_dev3_interpretation.md を参照。

## 記録フォーマット（記入）

```text
仮説・変更の種類・対象場面:
  仮説: Queen を先に殴る（target 変更）と Queen 削りが進み Act3 踏破に効くか。Amalgam は二次ミニオン
    （QUEEN 死亡で道連れに消える）なので、Queen 削りの補助に Amalgam 掃除を足せるかを問う。
  変更の種類: 戦略変更（エージェントの単一ターゲット方針）。正しさの修正（忠実度）とは分離。
  対象場面: Act3 QUEEN + Torch Head Amalgam ボス戦闘（Glory、floor 15）。

旧版／候補版、ゲーム／Mod／userdata／探索条件:
  旧版 base: official_agent.py（queen_minion_direct で Amalgam 優先）。
  候補 queenfirst: 同一 entry で Amalgam への単一アタックを Queen に付け替える写し。
  候補 H1: bosslab/agents/official_agent_H1.py（make_h_candidates.py 生成）。Amalgam 実効 HP(hp+block)
    が 0< <=50 のときだけ Amalgam、それ以外 Queen。定数 QUEENFIRST_H1_AMALGAM_HP=50。
  候補 H2: bosslab/agents/official_agent_H2.py。Amalgam の次手番の自由な一撃が自分を殺しうる時だけ
    Amalgam、それ以外 Queen。
  ゲーム: v0.107.1。キャラクター: Ironclad。難易度: 既定。 userdata: BossLab が記録 entry から再構築。
  Mod: Sts2Ai.dll。dev2/dev3 3-arm は忠実度修正 131a5a0 まで（HP 即時 clamp 927f26f 未反映）で実行。
    confirm4 は 927f26f を含む DLL（本ビルド済み、ゲーム未起動のまま leader が起動）。agent_script の
    sha256 は run_official_bosslab.ps1 が各行に記録。
  探索: rollout 100。乱数: trial は spec_id と offset（plan の rotation）から決まる effective_seed。

開発用 seed／確認用 seed、選定方法、反復数:
  開発用（dev2 系）: plan_dev2 の QUEEN spec 12 件、offset 0..（base/H1/H2/queenfirst を同一 entry で配対）。
    dev2 base・confirm 系で計 26 spec を使用済み（.dsh/bosslab_act3_used.speclist）。
  確認用（confirm4）: act3_boss_specs.jsonl 180 件の QUEEN のうち、unresolved と使用済み 26 件を除き、
    開手札ランダム付与系・RELIC.PAELS_CLAW（Goopy）・RELIC.PENDULUM（カウンタ draw）を除外した eligible
    40 件から、order-seed act3-confirm4 の sha256(seed|spec_id) 順で上位 12 件（offset 2..、used と重複なし）。
    候補の結果を知らずに対象効果・過去勝利を条件に選ばない。選定は dev2 結果の前に確定（コミット 245c38c、
    除外 id 修正と PENDULUM 追加で再生成 0e060c6）。
  反復数: 各 arm 12 trial（1 spec×1 反復/組）。同一 seed の再走は再現性確認で独立 seed 数に数えない。

予定 run 数／時間上限／再実行条件:
  予定: 開発用 dev3 base/H1/H2 各 12（計 36、完了）、確認用 confirm4 base/H1 各 12（計 24、base/H1 走行中）。
  時間上限: trial 毎 TimeoutSeconds 700・IdleTimeoutSeconds 320。
  再実行条件: 外部クラッシュ・中断は未完了として別 tag へ同一 spec/版/条件で再走。結果を見て有利 seed を
    足さない、勝った時点で打ち切らない。

判定に使う指標（標準から変える場合は測定前に理由を記録）:
  標準の Act3 踏破数は lab が直接測れない（lab は 1 戦闘のみ）。よって到達点同値の最終戦の進捗として
  Queen 削り割合（=1−最終 Queen HP/入室時最大 HP、Amalgam は Queen 進捗に合算しない、EVALUATION.md
  召喚物の扱い）を主信号に、総火力/ターン（Queen+Amalgam への総 HP 削除÷プレイヤーターン、300→213 の報告の
  軸）と Queen 火力/ターンを副主信号、Amalgam 撃破・死亡ターン・失った HP を補助に、勝敗は母数 0 の記録。
  指標の事後追加ではなく測定前に固定（コミット 7903ecb で --compare-pair の主信号化、4693f2e で採否規則）。

計画数／完了数／不明数／外部障害／候補由来の障害:
  dev3 base 12/12、H1 12/12、H2 12/12、（既存）queenfirst 12/12 完了。全 trial 全 12 件 outcome_source=
  combat_end_trace（fallback・欠測 0）。confirm4 base/H1 は走行中（leader 側、完了数は後記）。候補由来の
  例外・停止は観測されていない。

局所検証: 発動機会・判断差・結果差（件数と seed 数）:
  H1 の Amalgam 掃除は dev2 で一度も発火しなかった。実走 12 trial で戦闘中の Amalgam 実効 HP の最小が
  111〜199（1 度も 50 以下にならず、act3_dev3_interpretation.md）。queen_minion_h1 は 148 件だが全件 Queen
  を殴った（Amalgam 単独撃破 0/12）。＝「Amalgam を倒せる状況ではそちらを優先する」機構は dev2 では実質
  未試行。H2 も base との判断差は 3 手番分（queenfirst と同挙動に近く、詳細は reproduce_h_targets.py 系）。
  結果差（削り）: dev2 で H1 は 12 組中 9 増 3 減（精密両側 p=0.146）、H2 は 8 増 4 減（p=0.388）。

全体比較: 集合ごとの Act3・2・1 突破数／母数、到達点の改善・悪化・同値:
  lab は Act3 踏破率（突破数/母数）を測れない。win 記録は dev2 の全腕で 0/12（母数 0 の補助）。
  到達点（Queen 削り）改善・悪化・同値: H1 改善9 悪化3 同値0、H2 改善8 悪化4 同値0（base 比、12 組）。
  総火力/ターンは base 37.4 に対し H1 32.9・H2 35.7 と両候補低下（EVALUATION.md の「到達点同値なら削っ
  た割合」以前に、火力の絶対低下が踏破に不利な追加ゲート）。

到達点同値の最終戦: 比較可能／不能な組数、形態・削った割合の差、残 HP の観測時点:
  配対可能 12/不能 0（同一 spec×offset）。Queen 削り差は上記。残 HP/最終 Queen HP は trace の combat_end
  時点（勝 trial は撃破の 1 手前で trace が切れ実質撃破として扱う、EVALUATION.md の残 HP 観測時点の注意）。
  HP 即時 clamp 修正前の dev3 では idx11（ROYAL_POISON）が絶対注意対象（dev3 全腕で同じ制約）。

各 seed の結果、悪化例、証拠ファイル:
  証拠: data/bosslab_act3_dev3_{base,H1,H2}/（trace + lab_results.jsonl）、bosslab/results/act3_dev3_compare.md、
  act3_dev3_base_desc.md、act3_dev3_interpretation.md。削りが悪化した例は H1 の idx 0/6/8（45→38% 等、
  集計 act3_dev3_compare.md）。同一 entry 配対で向きが割れた組を残す。

採用／保留／不採用、その根拠と次に必要な証拠:
  事前登録の採否規則（act3_hybrid_decision_rule.md、コミット 4693f2e）の適用結果: 両候補が火力/ターンで base
  を下回り選定条件を満たさないため hybrid は進めない（規則上この機構は dev2 で次 arm 化しない）。dev2 で
  削り差が最も大きい H1 を 1 本だけ記録用に confirm4 へ進める（採用の約束ではなく、H1 が queenfirst と同挙動
  だった点の確認）。採用の暫定判定は confirm4（確認用集合）の結果で埋める。次に必要な証拠: confirm4 base/H1
  の完了、および「実際に Amalgam を削る」ことを保証する次候補 H3（act3_hybrid_h3_design.md、次 goal 用）。
```

## (a) 忠実度 3 種の修正と再照合

- 修正 1 defer_relics（RELIC.STONE_CRACKER の入室 hook による 2 ランダム札アップグレードの二重発火を防ぐ。
  入室後に付与）: コミット 131a5a0。
- 修正 2 ReensureRecordedPotions（記録 entry のポーション枠を入室後に確保）: コミット 131a5a0。
- 修正 3 HP 即時 clamp（記録 HP を最初の判断直前に 1 度だけ寄せる。コミット 927f26f。build 済み・confirm4
  から DLL に入る）。
- 再照合の一致数（同じ入場状態が実際に同じか、`analyze_bosslab.py` の lab vs spec 比較、証拠
  confirm3_fixed_fidelity.md）: 修正 3 適用前（修正 1・2 適用後の confirm3_fixed 実行）で 12 中 8 件完全一致、
  4 件不一致。内訳:
  - idx 0004（spec 1a05bb73e94b）・idx 0010（spec 59ed603b4b73）: 各 1 項目不一致=入室 HP が RoyalPoison の
    ターン 1 自己ダメージ 4 で記録より 4 下がる。これは修正 3 が対象。修正 3 の DLL での再照合は実機待ち
    （confirm4/fidelity で recovery 見込み）。
  - idx 0002（spec 83e6a3465fde）: 2 項目不一致=開戦手札の枚数（5 vs 6）。原因は RELIC.PENDULUM の未搬入
    カウンタ draw と RELIC.STONE_CRACKER の defer による開戦手札 RNG。札の値・deck multiset は一致。
  - idx 0011: 2 項目不一致=RELIC.CROSSBOW が入室 hook で混ぜるランダム無色札（lab が同じ札を出せない）。
  これら 0002/0011 は HP ではなく入室 hook の RNG/状態の再現不能で、戦略差ではない。confirm4 では同じ系統
  （CROSSBOW 族・PAELS_CLAW・PENDULUM）を除外して panel から除いた（コミット 0e060c6）。修正 3 適用後の完全
  一致数が 9/12 に戻るかは実機の再照合で確定させる（draft 時点では未確認と明示）。

## (a-2) confirm4 base 再照合（927f26f 反映後の DLL、2026-10-28 実測）

`bosslab_fidelity.py --all` を confirm4 base（12 trial、927f26f 入り DLL）に実行。完全一致 7/12、
不一致 5 件（証拠 `bosslab/results/act3_confirm4_fidelity.md`、原因詳説
`bosslab/results/act3_confirm4_fidelity_causes.md`）。内訳:
- 修正 3（HP 即時 clamp、927f26f）の検証: ROYAL_POISON を持つ 2 組（c589d7860c35・59ed603b4b73）で lab 入室
  HP が記録 HP に一致（53/53/53・90/90/90）。修正前（confirm2/confirm3_fixed）で lab 90 vs 記録 94 の
  不一致だった RoyalPoison ターン 1 自己ダメの二重差し引きが、実機で解消されたことを確認。
- 残り 5 件の不一致は HP・ポーション枠起因ではなく、3 種の入場状態再現のずれ（全て spec 抽出は元 trace と
  一致＝忠実な抽出、lab 再現側の限界）:
  ① RELIC.PEN_NIB のカウンタ 3 件（0002・0006・0010、`relic_counters`: lab `{PEN_NIB:0}` vs spec `{}`）。
     PenNib は攻撃カード play 毎の `AttacksPlayed % 10`（SavedProperty、10 枚目の攻撃を 2 倍）。元 trace は
     旧ブリッジでカウンタを持たないが、攻撃 play 数から推定可（実測 0002/0006=3、0010=4）。現行 DLL 以降は
     `CombatBridge.RelicCounters` が入場観測に出すので抽出＋書き戻しで厳密化できる。除外条件（trace に出ない
     per-relic カウンタ）に入れても可。
  ② RELIC.WHETSTONE（AfterObtained で deck の Attack 2 枚を升级）と RELIC.NEW_LEAF（1 枚変換）の 0007 の 1 件
     （TAUNT/DEMON_FORM が lab で +1）。BossLab の silent add は `AfterObtained` model フックを抑えないため、
     拾った時に一度走って記録 deck に焼き込んだ効果を入室で再適用してしまう。confirm4 で Whetstone 所持 5 件の
     うち net で deck がずれたのは 1 件（升级が冪等な場合無変化）。upon-pickup の deck/pile 変換系を抑制する
     家族追加で直せる。
  ③ 0011 の Amalgam/Queen の 1 点配分（198/400 vs 記録 199/399、計 598 同一）。BossLab は敵の入室 HP を
     `spec.enemies[].hp` から pin せず formation 生成で、加えて lab の初手観測はターン 1 の AfterPlayerTurnStart
     フック後（927f26f 設計）に撮るため、run 記録（入室 snapshot はターン 1 フック前）と 1 点ずれる。具体源は
     未確定（敵 HP pin で解消見込み）。
- これら 5 件は base と候補が同じ 12 spec（同一入場状態）を流す配対比較では両腕に同じ向きで出るため、
  配対の差（削り/win/ターン）には出ず、判定規則（4693f2e）の採否結論は動かない。絶対削り/火力の magnitude
  だけが該当 spec で僅かにずれる（②③は spec ごとに偶然、①は 3 件）。

## (b) dev2 結果と候補選定規則の適用

dev2 3-arm（base/H1/H2、`data/bosslab_act3_dev3_*`）を事前登録規則（コミット 4693f2e）に当てた集計は
act3_dev3_compare.md、解釈は act3_dev3_interpretation.md。要点: 削り割合は H1 0.261→0.406（9 増 3 減、
p=0.146）、H2 0.261→0.360（8 増 4 減、p=0.388）で改善側。ただし総火力/ターンは base 37.4 に対し H1 32.9・
H2 35.7 に低下、win は 0/12 のまま。選定規則（火力/勝利が base 以上・win 以上が必須ゲート）で両候補が火力
ゲートを通らず落選。hybrid は進めない。dev2 で削り差最大（H1）だけ記録用に confirm4 へ進める。規則は
dev2 結果を見る前に確定済みで、結果を見て動かしていない。

## (c) H1/H2 は「Amalgam 優先」を dev2 で実質試していない

- H1: `0 < Amalgam 実効 HP <= 50` の判定が 12 trial すべてで一度も発火せず（実効 HP 最小 111〜199、
  act3_dev3_interpretation.md）。Amalgam を削る唯一の手段が Amalgam を殴ることで、既定 Queen 優先だと
  Amalgam が入場値 199 付近に留まり条件が永久に発火しない（鶏と卵）。結果 H1 は最初から Queen 固定
  ＝実質 queenfirst と同挙動、Amalgam 単独撃破 0/12。
- H2: Amalgam の次手番の一撃が自分を殺しうる時だけ Amalgam。base との判断差は 3 手番分で、これalso
  queenfirst と大差なく、同じく Amalgam を継続的に削る動作にはなっていない。
- つまり「Amalgam を倒せる状況ではそちらを優先する」という機構そのものが dev2 ではほぼ試行されず、
  試されたのは「常に Queen 優先（=queenfirst）」だった。ここが未検証の空白で、次候補 H3 はこの空白を埋める
  （act3_hybrid_h3_design.md）。

## (d) confirm4 の枠（結果は後で埋める）

確認用集合。新規 12 spec（used と重複なし、CROSSBOW 族・PAELS_CLAW・PENDULUM 除外、defer は RELIC.
STONE_CRACKER 1 件）。同一 entry で base と H1 を配対。H1 は記録用（採用の約束ではない）。判定は act3_
hybrid_decision_rule.md（コミット 4693f2e）の採用条件をそのまま適用: 開発用と確認用の両集合で削り差>0 かつ
同じ向き、火力/ターンと win が base 以上、confirm4 の削り符号検定で両側 p<=0.05、比較不能なし。満たせば
「最終戦の進捗改善として採用、踏破率・到達点の向上は未確認」、満たさなければ保留/不採用を規則どおり記録。
- base 平均（Queen 削り / 総火力/t / Amalgam 撃破 / 生存ターン）: 未記入（実機待ち）
- H1 平均（同上）: 未記入（実機待ち）
- 配対 12/不能 0、符号検定 p、採用/保留/不採用: 未記入（実機待ち）
- 927f26f 反映後の入室 HP 一致（ROYAL_POISON 組）: confirm4 base で 2/2 一致を確認（上記 (a-2)、実測済み）。

## (e) 判定の暫定文

第一案は事前登録規則の適用結果: dev2 で両候補は火力/ターン ゲートを通らず、hybrid は進めない（この target
機構は dev2 では採否保留相当、実質 queenfirst のみ試行）。確認用 confirm4 の結果で「採用/保留/不採用」と
「次に必要な証拠」を確定する。confirm4 でも削りが同方向かつ火力/win ゲートを通れば最終戦進捗改善として採用、
通らなければ保留（H3 へ）、確認用で削りが悪化すれば不採用。いずれも Act3 踏破率向上は lab では未確認のまま
付記する。
