# confirm4 base の残った 3 種類の不一致の原因（T28.1・解析のみ）

act3_confirm4_fidelity.md で完全一致 7/12、ROYAL_POISON HP 2/2 一致、残り 5 件（HP・ポーション起因は 0）の
内訳（カウンタ 3・札 1・敵 HP 1）を、デコンパイル（$TMPDIR/sts2-ai-decompiled、実機未起動）と元 trace から特定した。
結論を先に言えば、3 種とも入場状態の実走再現のずれで、base と候補が同じ 12 spec を流す配対比較では両腕に同じ向きで出るため判定（採否）は動かない（下記②で数字で確認）。絶対忠実性はこれから直せる。

## (a) RELIC.PEN_NIB のカウンター（trial 0002・0006・0010）

確認（PenNib.cs）: PenNib はプレイヤーが攻撃カードを **play** する毎に `AttacksPlayed` を増やし、`SavedProperty` で `AttacksPlayed % 10`（0..9）を持つ。10 枚目の攻撃カードのダメージを 2 倍にする（`ModifyDamageMultiplicative`、10 枚目を `AttackToDouble` に指定）。命中するか/ブロックされたか/ダメージ 0 かは問わず、プレイヤー自身の攻撃カードを play した回数だけを数える（pet/Osty の攻撃は数えない）。relic_entry_effects 系では `relic_run_state.json` の `other_saved_prop_relics` に `entry_behaviour=false` で登録済み＝入室では行動せず、カウンタの復元だけが要る部類。

現状: 今の `CombatBridge.RelicCounters`（CombatBridge.cs:300-301）は `PenNib.AttacksPlayed` を毎 observation の `relic_counters` に出す。したがって**今の DLL 以降の実走で採る spec なら、入室観測に真値が入るので抽出器がそれを spec に写し、BossLab が入場時に SavedProperty を書き戻せば厳密に再現できる**（現状 BossLab は書き戻していない）。ただし confirm4 の spec を作った元 trace（`data/candidate_fysh_N8CQ4ZKP2W_agent.jsonl`、`data/fasten_GY_GYIJSAA6W7_agent.jsonl`）は旧ブリッジで、trace のキーは `seq/phase/…/decision_reason` のみで `relic_counters` も `AttacksPlayed` も一切ない（出現 0 回）。つまり真値は trace に直接記録されていない。

推定法（trace から計算できる）: decision trace の各行は実際に打った `card_id` と `hand` 中の札の `type` を持つ。QUEEN 初手番より前の「プレイヤーの攻撃カード play」回数を数え、10 で割った余り＝入場時 `AttacksPlayed`。実測した値: `N8CQ4ZKP2W`（trial 0002・0006）= 203 play → 余り **3**、`GYIJSAA6W7`（trial 0010）= 204 play → 余り **4**。lab は無処理で 0。PenNib の数え方（play 回数で命中/0ダメ/ブロックを問わない・run 全体で mod 10・pet/Osty を数えない）と trace の攻撃 play 数の定義は一致するので、この推定は原理的に妥当。ただし `AttacksPlayed` が boss 入室直前に 9 から 10 へ跨界だと `AttackToDouble` が保留されうる（3/4 では保留なし）、および trace にカウンタが無いので実走値との直接突合はできない（＝計算は妥当だが厳密一致は未検証）。

除外条件の可否（件数つき）: 判定の配対比較には効かない（下記②）。絶対忠実性を出したいなら、(1) 現行ビルドで再抽出して `relic_counters` を spec に記録＋BossLab が入場時 `AttacksPlayed` を書き戻す、が厳密。それが間に合わない集合では「trace に出ない per-relic カウンタ」条件で除外する（PENDULUM と同筋）。対象 spec 数: RELIC.PEN_NIB = confirm4 3/12、dev2 3/12、dev 2/12、confirm2 2/12、fidelity2 1/12、confirm3 0/12。

## (b) trial 0007 の TAUNT/DEMON_FORM が +1

確認（Whetstone.cs / NewLeaf.cs、BossLab.cs:217-218）: 0007 の入場 deck に RELIC.WHETSTONE（`AfterObtained` で deck の upgradable Attack を `StableShuffle` で 2 枚選んで `CardCmd.Upgrade`、CardsVar(2)）と RELIC.NEW_LEAF（`AfterObtained` で 1 枚 `TransformToRandom`）が入っている。記録 deck では TAUNT+0/DEMON_FORM+0、lab では TAUNT/DEMON_FORM が +1。

原因: BossLab は relic を silent add（`AddRelicInternal(..., silent: true)`）で入れるが、これは RelicObtained の**イベント**を抑えるだけで **model フック `AfterObtained` は走る**（BossLab.cs の PHIAL_HOLSTER の記述＝「suppresses only the RelicObtained event, not the model hook」）。なので実走で拾った時に 1 回走って記録 deck に焼き込まれている Whetstone の升级（2 枚）や NewLeaf の変換が、lab 入室で**もう一度走り**、lab 側の RNG で別の 2 枚（TAUNT/DEMON_FORM）を升级して、deck multiset が記録から +1 ずつずれる。実走では別枚が升级済み＝記録に反映済み、という状態を lab が上書きする形。

規模: `AfterObtained` が deck/pile を変える relic（HasUponPickupEffect）を持つ spec: confirm4 で Whetstone 5/12・NewLeaf 1/12（dev2 Whetstone 3、confirm3 Whetstone 3、confirm2 Whetstone 1）。ただし升级対象が記録で既に升级済みなら `Upgrade` は冪等なので無変化。実際に net で deck がずれて観測されたのは confirm4 では trial0007 の 1 件だけ（Whetstone 所持 5 件のうち 1）。StableShuffle が lab で違う RNG 順を消費するため、ずれるかどうかは spec ごとの偶然。

推奨: 「拾った結果が既に記録に焼き込まれている」`AfterObtained`（deck/pile を変える系）は lab で走らせるべきでない。PHIAL_HOLSTER のスロット拡大は記録に焼き込まれていないので走らせる（現状通り）と方針が逆になるから、relic ごとに決める。Whetstone/NewLeaf のような upon-pickup の deck/pile 変換系を、defer_relics と同じ扱いの「upon-pickup deck effect」家族として relic_entry_effects.py に追加して抑制するか、該当 relic を持つ spec を忠実性 stocktake から除外する。判定の配対比較には効かない（下記②）。

## (c) trial 0011 の Amalgam/Queen 1 点配分

確認: spec.enemies は Amalgam 199(max 199)/Queen 399(max 400)、lab の入室観測は Amalgam 198/Queen 400。合計 598 は同一で、1 点が Queen 側から Amalgam 側へ動いている。

機構（確認部分）: BossLab は敵の入室 HP を pin しない。player HP は `trial.Hp` から `SetCurrentHpInternal`（BossLab.cs:525-546）＋ FirstDecisionHook で再適用するが、敵は encounter の formation から生成され HP は `spec.enemies[].hp` から復元されない（`EnemyHpLastObserved` は戦闘終了時の読み取りだけ、BossLab.cs:380）。加えて lab の初手判断観測は意図的に TurnNumber≤1 の `AfterPlayerTurnStart` フック完了後（927f26f の FirstDecisionHook 設計＝RoyalPoison のターン 1 自己ダメを正しく扱うため）に撮る。元 run の boss 入室 snapshot はそのターン 1 フックより前。よってターン 1 開始系で Amalgam に乗る 1 ダメージが lab 観測には出て run 記録には出ていない、という観測タイミング差として説明がつく。

未確定点: 敵へターン 1 開始に 1 点入れる効果を元 trace の Amalgam/Queen states から特定できなかった（`data/enemies_glory.json` にランダム 1 ダメージの token を見つけられず、0011 の relic フック scan でも combat/room 開始に damage を入れる relic は無かった）。なので「敵入室 HP が pin されない」「lab 初手観測がターン 1 フック後」という設計帰結は確認したが、Amalgam に 1 点入れた具体源は未確定（Amalgam/Queen の state を狙って個別にデコンパイルすれば確定できる）。

深刻度と推奨: 1 点で合計同一、配対の両腕で同じ lab 手順 → 判定の採否は動かさない。絶対忠実性では、BossLab が敵の入室 current HP を `spec.enemies[].hp` から pin するか、元 run と同じ「ターン 1 フック前」で入室 snapshot を撮る運用で解消できる（pin する案は RoyalPoison 等のターン 1 効果との相互作用に注意）。

## ② 過去の集合（dev2・confirm2・confirm3）への影響：判定は変わらない

前回判定（queenfirst）は base run と候補 run が同じ 12 spec（同一入場状態）を流す配対比較（`paired_continuous` の配対 key は (spec_id, offset)）。同じ spec＝同じ入場状態（PenNib は両腕で lab 0、Whetstone/NewLeaf の deck drift も同一、0011 系の敵 HP 扱いも同一の lab 手順）を両腕で使うので、これらのずれは両腕に同じ向きで出る＝配対の差（win/削り/ターンの差分）から相殺される。判定規則（4693f2e）が見るのは配対の差なので、結論は変わらない。

件数（各集合で PenNib を持つ spec 数）: dev2 3/12、confirm2 2/12、confirm3 0/12。同じ推定法を当てると、絶対削り/火力 magnitude だけがその spec 分で少しずれるが両腕共通なので差に出ない。数字で確かめた通り、queenfirst の採否結論は不変。
