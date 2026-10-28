# STS2 AI Code Wiki

評価・採否の現行基準は [EVALUATION.md](EVALUATION.md)（2026-10-05改訂）。以下の過去記録にある「3 seed以上で改善」、合計戦闘勝数による採否、限られた探索からの攻略不可能という判断は、現在の採否根拠にしない。測定値と当時の判断は履歴として残す。Round 135のpricebandは新基準では局所改善あり・全体採用は保留となる。

現行コードの入口、データフロー、Bridge契約を短くまとめる。公式ゲーム内部APIの前提はmanifestと同じ `v0.107.1` である。

## Python

### `official_agent.py`

大型デッキ(16枚以上)では強ブロック3枚未満も防御不足と判定する。SKILL_POTIONは全分岐でincomingがHPの半分以上のときだけ使用する。

`choose(observation, enemy_data=None, simulations=0)` がフェーズ別の入口である。

| `phase` | 呼び出し先 |
| --- | --- |
| `shop` | `choose_shop` |
| `map` | `choose_map` |
| `card_reward` | `choose_card_reward` |
| `rest` | `choose_rest` |
| その他 | combat選択 |

combat選択の順序は、Sandpit中の `Frantic Escape`、Crabのfacing変更、potion、条件を満たす `rollout_choice`、lethalなStrike/Bash、Defend、カード優先度、`end_turn` である。rolloutは**手札にモデル済みカードが1枚でもあれば**実行され(`any`)、未知カードはsim内で未プレイ扱いになる——かつては未知カードが1枚あるだけでrollout全体を放棄していた(Dominateが未モデルだったOBSCURA戦でヒューリスティックに落ち、復活するParafrightを倒し続けてボスに0ダメージの悪手連鎖を招いた)。lethal候補は攻撃してくる敵、次に最もHPの低い敵を優先して倒し、カード優先度が同点の攻撃は最もHPの低い敵へ集中攻撃する。Slippery持ちの敵への実効ダメージは1としてlethal判定し、HardToKill(Exoskeletonの1ヒット上限9)持ちの敵には実効ダメージをキャップして判定する。rolloutで `KeyError`、`ValueError`、`NotImplementedError`、`StopIteration` が出た場合は後段のヒューリスティックを使う。

combat traceには判断時点の手札だけでなく、draw/discard/exhaust pile、playerのpower・relic、敵のcombat id・slot・move historyも記録する。これらは`rollout_choice`の入力を再構築するために必要で、J7GW6DFX9VのTHE_INSATIABLE戦では旧traceにpileが無く、Ruptureを見送った探索の代替手評価を再現できなかった。`trace_piles_T3XQ7WM2VP`の1戦実機runで各フィールドの出力を確認済み。

現行基準（`0a1d41f`、固定16seed）は0勝、202戦186勝。K7M2QX9BTRの初回はゲーム本体が終了コード134で落ちたため無効とし、再走の15戦14勝を採用した。

T3XQ7WM2VPではSmall Capsule由来の`JuggernautPower(amount=6)`が13局面に出ていたが、`POWER_NAMES`に無くrolloutから消えていた。ゲーム実装は、所有者が正のブロックを得るたびに生存中の敵1体をランダムに選び、amount分のUnpoweredダメージを与える。共有のブロック獲得処理でこの効果を再現すると旧観測13局面中6局面の選択が変わったが、固定16seedの再測定結果は基準と同じ0勝、202戦186勝だった。T3も新旧とも9戦8勝・Act 2 Floor 6敗北で、勝敗と到達点は変わらない。ほか15seedのtraceは基準とバイト単位で一致した。

Speed Potionは`DexterityPower(5)`と`SpeedPotionPower(5)`を同時に付与し、プレイヤーターン終了時に後者を除去して同量のDexterityを戻す。観測済みの対象4seedで修正を再測定すると、J7/P4はtraceが完全一致、N8は12戦11勝・Act 2敗退から19戦18勝・Act 3ボス敗退へ改善、R9は11戦10勝・Act 2敗退から7戦6勝・Act 1ボス敗退へ劣化した。固定16seed全体では0勝のままだが、202戦186勝から205戦189勝、Act 3到達は1本増える。正しい持続時間の再現であり全体到達度も上がるため採用し、R9の後退は次の改善対象とする。

R9の後退は、捨て札が空のターンにHeadbuttをPerfected Strikeより先に使い、回収対象を作れなかったことが原因だった。rolloutがHeadbuttを選んだ場合に限り、同じターンに使える15ダメージ以上の非Exhaust Attackを先に使う。R9は11戦10勝・Act 2 Floor 8まで回復した。弱いAttackまで対象にする案はN8のQUEEN戦を残HP208から385へ悪化させたため採用しない。固定16seedではR9以外に条件該当がなく、Speed Potion対応込みの成績は0勝、209戦193勝、Act 3到達2本となる。

**`CARD.THE_GAMBIT`は自動プレイ対象から完全除外**: combat.pyのシミュレータは以前から`TheGambitPower`が未知のため本カードをモデル対象から除外していたが(後述)、それは`rollout_choice`(search経由)を素通りするだけで、ヒューリスティック側の「ブロック値最大のカードを選ぶ」防御フォールバックは素通しで本カードを選び続けていた——0コストでブロック50という数値だけ見れば圧倒的最良の防御札に見えるため。デコンパイルで`TheGambitPower.AfterDeath`(実際は`AfterDamageReceived`)を確認したところ、**このpowerが付いている間に無傷でない(Unblocked)被弾を1回でもすると、残りHPに関係なく即死**(`CreatureCmd.Kill`)する仕様で、自動解除トリガーも見当たらない(このターンに限らず、以降のどのターンで被弾しても発動する)。実機run(VANTOM戦)でHP87から一切のダメージログなしに1ターンでHP0になる事例が発生し、原因はturn1に打ったTHE_GAMBITがturn3のDismember(26ダメージ、ブロックしきれず)で即死判定を踏んだことだった。`choose()`の`cards`構築時点で`CARD.THE_GAMBIT`を除外し、ヒューリスティックのどの経路からも二度と選ばれないようにした。

`_axis` はデッキから `strike`（Perfected StrikeまたはHellraiser）、`self_damage`（RuptureまたはTear Asunder）、`vulnerable`（`VULNERABLE_PAYOFF` とBashまたは `VULNERABLE_APPLY`）、`exhaust`（`EXHAUST_ENABLERS` と `EXHAUST_PAYOFF`）の順に判定する。`_core_priority` はaxisごとの未所持coreカードを順位化し、axisがない場合だけ利用可能な Perfected Strike、Inflame、Rupture、Corruption を候補にする(InflameはStrength軸の種)。

`choose_shop` はlegalな `buy_card` にcore順位を適用し、該当購入がなければPerfected Strikeを含むstrike axisのデッキでは `CARD.DEFEND_IRONCLAD`、それ以外では `CARD.STRIKE_IRONCLAD` の削除を探す。最後はlegalな `skip`、他の最初のaction、空なら `{"type": "skip"}` の順で、1回の観測につき1 actionを返す。この関数自体は価格計算や複数actionの実行をしない。

`choose_card_reward` は `CARD_TIERS` の S/A/B/C/D をbase tierとして数値化し、`_core_priority` のaxis対応coreカードをbase tierより先に比較する。デッキが `_block_starved` 判定(ブロックカードが全体の**40%未満**、または**8ブロック以上の強ブロックカードが2枚未満** — Defend/Iron Wave/True Gritの5〜7ブロックは強ブロックと数えない)のときは、防御カード(Shrug It Off、Flame Barrier等)に+2の優先度を付けてAct 2向けの被弾を減らす。sim19は24枚中8枚(ちょうど1/3)で旧判定が発動せず防御不足のままボス戦に突入したため、閾値を1/3→40%に引き上げた。ボス向け火力として、Strikeタグが5枚以上(スターターで既に5枚)かつ**Perfected Strikeが2枚未満**ならPerfected Strike/Ashen Strikeに+2してStrike軸(6+2/Strikeで即約16ダメージ)を種まきし、Strength源(Inflame/Primal Force/Dominate/Cruelty)が1枚でもデッキにあるならSTRENGTH_CARDS全体に+1して軸を育てる。ボス戦シミュレーションの検証ではPS軸が全構成で敗北しStrength軸が最大ダメージ(100 vs PSの55〜67)を出したため、**PSは1〜2枚の種に制限し3枚目は取らず**、未確定軸seedリストは **Inflameを先頭**(INFLAME, PERFECTED_STRIKE, RUPTURE, CORRUPTION)にしてStrength軸を優先する(ショップ購入も同順)。InflameはStrengthが全攻撃をスケールさせるボス火力としてtier C→Bに引き上げられ、単発火力のBLUDGEONより優先される。デッキ中の**コスト3以上のカードが`HIGH_COST_CAP`(2枚)以上**あるときは、たとえ提示カードがどれだけ強くても(core/tier判定より前で)コスト3以上の候補を非優先にする(取れなくなるわけではなく、他に選択肢が無ければ選ばれる)——3エネルギー/ターンの経済では高コスト札を積みすぎると手札で腐るカードが増えるだけなので、実況フィードバックを受けて追加した。`UNPLAYABLE_REWARDS`(現在はRelaxのみ)は3コストのブロックがgreedy rolloutで使いづらいため報酬で絶対に選ばず、提示がRelaxだけならSkipする。未知カードなどcoreにもtierにもないカードは `option_id == "Skip"` のalternativeへ回す。`choose_map` はAct開始時に全マップが開示されるため、通常HPでは現在地(または開始地点)からBossまでの全経路をDFSで列挙し、`(戦闘マス数, -休憩数, エリート数, -宝箱数, 不明数, -ショップ数)` の優先順で最適ルートを選んでその次の1歩を返す。戦闘マス最小化を最優先するのは、1マップで通常戦闘4つ目以降は強い敵プールになる仕様を回避するためである。Bossに到達できる経路がない場合やBossが存在しない場合は従来のroom valueにフォールバックする。HPが最大値の**3/4以下**(旧2/3から引き上げ——`choose_rest`のHEAL判定と揃えた。通常状態のルーティングはルート全体のMonsterマス数だけを見て「これまで何HP残っているか」を一切考慮しないため、2/3のままでは危険な通常戦を連続で素通りしてから発動することがあり、実機run(Act1 floor1〜6)で80→52HPまで削れてもまだ発動域外(閾値53.3)、結局その後さらに2戦重ねて休憩所到達時にHP10まで落ち込んだ)ではRestSiteへの距離・Elite数・安全性を使う。`choose_rest` はボス直前(floor 13以降)なら負傷時に `HEAL` を優先し、HPが最大値の75%以上なら `HATCH`、負傷中なら `HEAL`、それ以外は `SMITH` を探す。

`choose_potion` はincoming damage、HP、敵数、敵HP、手札を使って、致死回避、回復・防御、範囲攻撃、攻撃強化などの候補を固定順序で選ぶ。敵HPが100以上の長丁場(ボス・大型エリート)では **SHACKLING_POTIONを最優先で使用**し、続いて STRENGTH/FLEX/POWER/COLORLESS/ATTACK/SKILL/DUPLICATOR/DISTILLED_CHAOS/EXPLOSIVE_AMPOULE の攻撃系potionで被弾前に戦闘を短縮する。ポーション検証(勝率92〜100%)でSHACKLINGが最大の勝因と判明したため。**SHACKLING_POTIONは`debuffs`集合や`blocking`側の汎用「危険な時」フォールバックには含めない**——以前は`hp<=max_hp//2`かつ多体戦、あるいは`incoming>=hp//2`の汎用危険判定でも候補に入っており、macOS実機検証(sim13)で個体HP17〜21の複数WRIGGLER戦の危険回避に浪費され、その後HP252のCEREMONIAL_BEAST戦で温存できていたはずのSHACKLINGが手元に無くなった。SHACKLINGは`known`集合(未知potion判定除外用)にだけ残し、実使用は「敵HP>=100」の専用分岐のみに限定する。**「Strength -7が全戦闘効く」という前提は誤りだったと判明**(デコンパイルで確認): `ShacklingPotionPower`は`TemporaryStrengthPower`を継承しており、`AfterSideTurnEnd`が「付与対象(敵)自身のターンが終わった時点」で自分自身を除去し、-7 Strengthを打ち消す——つまり**敵の直後の1ターン分しか効かない**。この誤解のせいで、Act1エリートBYGONE_EFFIGY戦(初手がSLEEP_MOVE/WAKE_MOVEで無害)でturn1に即使用し、攻撃が来る前に効果が切れて完全に浪費される実機回帰が発生した。`incoming > 0`(このタイミングで実際に被弾する攻撃が来ている)の時だけ使用するようガードを追加した。**FORTIFIERは現在ブロックの2倍を追加する効果(`Fortifier.cs`)なので、ブロックが0のターンでは温存**し、ブロック>0の時だけ使用候補に含む——sim19実機runでブロック0に無駄打ちした回帰を修正。自動使用potionは手動選択しない。

`MONSTER.PAELS_LEGION`と`MONSTER.BYRDPIP`(それぞれ遺物Pael's Legion / Byrdonis's Eggが召喚するプレイヤー側ペット、HP9999・`NOTHING_MOVE`のみ・HPバー非表示で実質戦闘に関与しない)は`data/enemies_*.json`に一切存在せず、`rollout_choice`の`specs[observed["id"]]`が毎ターン`KeyError`となりその遺物を持つ間の**全ての戦闘**でrolloutが機能しなかった。`rollout_choice`の敵構築ループで両方をスキップして対応する。

`main` は観測JSONを25ms間隔で読む。`terminal` なら終了し、seqが前回と異なるとき `choose` の結果にseqを付け、`atomic_write`（tmp + `os.replace`）でaction JSONを書く。JSON/I/O一時エラーはpollを継続し、その他の例外はerror logへ記録してlegalな `end_turn` があれば書き込む。

### `combat.py`

`Enemy` と `Combat` はfrozen dataclassである。`initial_combat` は敵編成・敵HP・move・初期手札を生成し、`legal_actions` はenergyとtargetに基づくカード action と `End turn` を返す。`step` はカード、敵ターン、山札、power、状態遷移を更新する。`search` は各初手から最大60手のランダムロールアウトを行い、平均評価で並べる。

代表的な近似対応は、Vulnerable、Weak、Frail、Strength、Slippery、HardToKill、Sandpit、Crab背面攻撃、Anger、Shrug It Off、Battle Trance、Slimed、Bully、Dismantle、Iron Waveに加え、Cinder、Ashen Strike、Hemokinesis、Perfected Strike、Inflame、Primal Force、Unrelenting、Giant Rock、Relax、Tremble、Breakthrough、Whirlwind、Bloodletting、FEED、FlutterPower、Dominate、BYRD_SWOOP(0コスト14ダメージ)、PILLAGE(1コスト6ダメージ+非攻撃カードを引くまでドロー)、EQUILIBRIUM(2コスト13ブロック)である。加えてBreak・Taunt・Thunderclap(いずれもVulnerable付与)、HowlFromBeyond・DramaticEntrance(全体攻撃)、Impervious・Lift・UltimateDefend(固定ブロック)、Rampage・Bolas・Fisticuffs・ThrummingHatchet・UltimateStrike(固定ダメージ)を対応させた。カード追加はデコンパイルした`OnPlay`本文から機械抽出したが、`PowerCmd.Apply<X>`の`X`がCanonicalVarsの変数名(ツールチップ表示用)と一致しない実装が複数見つかり(Rupture→実際は`RupturePower`、DemonForm→`DemonFormPower`、Coordinate→`CoordinatePower`、SetupStrike→`SetupStrikePower`など、いずれも未対応のラッパーpower)、「CanonicalVarsに名前があるから安全」という判定は誤りだった。**実際に`PowerCmd.Apply<X>`へ渡されたクラス名で照合**し、未知のpowerを1つでも伴うカードは(TheGambitのブロック50+`TheGambitPower`、PanicButtonのブロック30+`NoBlockPower`のように実は代償を伴う場合があるため)ダメージ/ブロックが実在してもカード全体を追加対象から除外した。Status/Curseの各カードは`CardKeyword.Unplayable`または`HasTurnEndInHandEffect`(手札に残った状態でターン終了時に発動)という別の実行モデルのため対象外。Dominateは1コストSkillで、対象にVulnerable 1を付与した後、付与後のVulnerable量ぶん自分にStrengthを獲得しExhaustする。`TeammatesOf` をターゲットにする効果(例: THE_OBSCURAのSAIL)は `GetCreaturesOnSide` と同じく**自分を含む同sideの全クリーチャー**に適用される——実トレースでOBSCURA自身がStrength 3→6→9と強化されるのを確認済みで、これによりOBSCURA戦の被弾予測が実ゲーム(ターン5で34被弾)と一致する。Iron Waveは5ダメージと5ブロックを同時に与える。FEEDは1コスト10ダメージのExhaust付きRare攻撃で、キル時の最大HP+3はモデル化しない(Combatにmax_hpがないため)。HardToKillはEXOSKELETONが `AfterAddedToRoom` で初期付与される「1ヒットあたり最大9ダメージ」のキャップで、`initial_combat` で付与され `_damage_enemy` でSlipperyの次に適用される。これによりシミュレーションのEXOSKELETON戦の被弾予測が実ゲーム(約29)に一致する。FlutterPowerはTHIEVING_HOPPERの攻撃被弾1回ごとに1消費される「受ける攻撃ダメージを半減」するpowerで、ブロック前に半減し、0ダメージ(完全ブロック)の被弾では消費しない。THIEVING_HOPPERはTHIEVERY→FLUTTER→HAT_TRICK→NAB→ESCAPEの4攻撃後に逃走する。

`_enemy_turn` の `CardPileCmd.*` 効果のうち、枚数が数値でないもの(THE_INSATIABLEのLiquify、SOUL_FYSHのBeckon/Gaze、NOISEBOTのNoiseなど `AddGeneratedCardToCombat` 系)はスキップされる——生成カードはJSONに実体が無く、数値評価が `KeyError: 'null'` でクラッシュし、ボス戦の**ターン1のrolloutを全滅**させていた(実トレースでターン1だけ `sims=null` になる)。THE_INSATIABLEのLiquify(ターン1でSandpit 4付与+Frantic Escape×3)は専用処理でモデル化済みのため、スキップで正しい。`AddToCombatAndPreview` 系(Slimed/Dazed/Wound等)は数値枚数でdiscardに追加される。

THE_INSATIABLEの砂(Sandpit)は毎敵ターンに1減り、1になると即死する。`_step_score` はFrantic Escapeで砂が回復した時、**砂が3以下(切迫時)に限り1回復=15点**をcreditする——砂が豊富な時にまでFrantic Escapeを優先すると火力が浪費されるため。これによりgreedy/searchのpolicyが砂を維持しつつ、安全な時は攻撃にエネルギーを回す。

Toric Toughness(`CARD.TORIC_TOUGHNESS`)は `astra_goal_deck2` で手札に53回来て探索から1度も選ばれず、`heuristic_fallback` で3回しか使われていなかった。`CARD_COST` に無いカードは `legal_actions` から黙って除外されるためで、Flame Barrierと同じ検出のされ方である。コスト2・ブロック5(強化7)のSkillで、`ToricToughnessPower` は **Instanced**——実際に得たブロック量をインスタンスごとに保存し、続く2回のブロッククリアで同量を再付与する。`combat.py` は同名power集約の `player_powers` では表せないため、`Combat.toric_pending` に `(保存ブロック, 残り回数)` の組を持つ。再付与は `ValueProp.Unpowered` なのでDexterity/Frailを再適用しない(初回の付与時点で既にFrailぶん減った実値が保存される)。Barricadeがある間はブロックがクリアされないので発火させない。観測はpowerの `amount` しか公開せず保存ブロック値は出ないため、エージェント側の再構築では未強化の5と仮定する——過小評価は安全側。正確に扱うならCombatBridgeからpowerの `Block` を公開する必要がある。

Squash(`CARD.SQUASH`)も同じ検出で見つかった(手札18回、`rollout_success` 0回)。Bashと同型のコスト1・ダメージ10・対象にVulnerable 2、強化で+2/+1のEventカードである。

**満杯時のポーション報酬はブリッジで拾えるようにした(実機検証済み)。** 素の `RewardsScreenHandler` は `!(b.Reward is PotionReward) || hasPotionSlots` でフィルタしており、**belt が満杯だとポーション報酬をボタンごと飛ばして床に置き去りにする**——判断がエージェントへ一切渡らない。`official_mod/PotionRewardBridge.cs` がこのハンドラを差し替え、満杯かつ `CanRemovePotions` のときだけ `phase = "potion_reward"` の観測(手持ちと `PotionReward.Potion` の中身)を出して `discard`/`skip` を待つ。`discard` なら `PotionCmd.Discard` で枠を空けてから元のクリック処理へ進む。それ以外の挙動は素の drain loop をそのまま写している。`choose_potion_reward` は `SHOP_POTION_SCORES` で**提示品が手持ち最弱を厳密に上回るときだけ**入れ替える(同格の交換は報酬を捨てるのと変わらず、格下は見送りより悪い)。

実機確認(`astra_potion1`, seed D6A1F8C3E5): seq198で[Snecko Oil, Explosive Ampoule, Fysh Oil]の満杯、seq200で `potion_reward` が発火しSnecko Oilを捨てる判断、seq203で[**Fysh Oil**, Explosive Ampoule, Fysh Oil]になった。戦闘後の必須経路を差し替えているが15戦を通して例外は無い。

**測定用の環境固定**: `/tmp/sts2_goal_run.py` に `STS2_USERDATA_SNAPSHOT` を足した。ディレクトリを渡すと初回にユーザーデータを写し取り、以降の全runがそこから開始・復元する。**これが無いとseedを固定しても同じrunにならない**——`astra_base_*`(03:00)と`astra_v2_*`(08:35)は同じseedで開始レリックが違い(CHANDELIER+PANTOGRAPH vs MOLTEN_EGG+ORICHALCUM)、前後比較が成立しなかった。原因はrun間でユーザーデータが変わっていたこと。**前後を測るときは必ずスナップショットを固定すること。**

**THE_INSATIABLE戦の勝敗を最もよく分けるのは「開始HP」で、戦闘中の指標ではない(実測)。** 全runの同ボス戦を勝敗で分けると:

| | ターン数 | 開始HP | ブロック/ターン | カード/ターン |
|---|---|---|---|---|
| 勝利12戦 | 8.2 | **81** | 9.5 | 3.9 |
| 敗北8戦 | 8.0 | **71** | 8.1 | 3.5 |

**勝った12戦は全て開始HP 80〜86**。負けた側は43/52/70も混じる。ブロック量とカード枚数の差はわずかで、**戦闘の打ち方より、そこへ何HPで到達したかが効いている**。

あわせて測った内訳: 無駄ブロック(被弾予測を超えた分)は31ターンで83、貫通した被弾は337。**1ターンあたり無駄2.7に対し貫通10.9**なので、「軽いターンに厚く重いターンに薄い」配分ミスはあるものの主因ではない。ブロックの総量そのものが足りていない。

→ **改善の当たり所はボス戦の中ではなく、そこまでのHP経済(休憩所の使い方、経路、道中の被弾)。**

**`aoe_threat_direct` は「攻撃してくる敵の数」で判定する。画面上の敵の数ではない。** この事前分岐は複数の攻撃者からの合計火力をrolloutが過小評価する問題への対策だが、条件が `len(enemy_by_id) > 1` だった。QUEEN戦ではTorch Head Amalgamだけが殴りQUEENは防御・バフに徹するので、全体攻撃に広がりの利点が無いのに発火し、**ブロックを差し置いて全エネルギーを注ぎ込む**。全runで17回発火し、うち**6回(35%)は攻撃者が1体以下**だった。最も明確なのが `astra_routecost2_D6A1F8C3E5` seq425——自HP59・被弾48・攻撃者はAmalgam1体のみで、Whirlwindに4エネルギーを使ったが倒しきれず(53→29)、自HPは17まで落ちて2ターン後に敗北。`enemy_incoming` の正の値を数えるよう変えた。

固定環境4seedでは**勝敗も戦闘数も個別勝ちも変わらない**(51戦47勝のまま)。QUEEN戦の与ダメージが19増え最終HPが8減っただけで差引ゼロ。前提が誤っていた事実は動かないので正しさとして採用する。

**Act 3ボスQUEENは純粋な火力検定である。ただし「現在のデッキでは通らない」という当初の結論は同日中に覆った(2026-09-08)。** 最も深く到達するD6A1F8C3E5が毎回ここで死ぬので機序を洗った。`Queen.cs` を読むと、**Torch Head Amalgam(199 HP)が生きている間、QUEEN(400 HP)は BURN_BRIGHT_FOR_ME を繰り返すだけで攻撃しない**——毎ターンStrengthを積み、ブロックを20得る。Amalgamが死ぬと `AfterDeath` が `HasAmalgamDied` を立て、以後は Enrage → Off With Your Head(3×5) → Execution(15) のループへ移る。

つまりこの戦闘の設計は「殴ってこないボスがひたすら強化される横で、199 HPの手下をどれだけ速く倒せるか」であり、**QUEEN本体へのダメージは20ブロックに吸われて無駄になる**。エージェントの狙いは正しく、攻撃16回のうち13回をAmalgamへ向けている。それでも7ターンかかり、倒した時点で自HPは38、QUEENは367残っていた。

**1手目の `search_value` は −0.80**、つまり開始時点でrolloutの約9割が敗北している。打ち回しの問題ではない。599 HPを削り切る火力が要る戦闘に、毎ターン約28ダメージのデッキで入っている。ここは戦闘中の修正では動かない。

**QUEENは勝てる。Strengthエンジンを積めたデッキなら(2026-09-08)。** 上のQUEEN分析を書いた直後、同じcommit `45aa0e1` の16seedスイープでseed **N8CQ4ZKP2W が19戦19勝でAct 3を踏破**し、そのQUEENを倒した(残HP 13/83、`data/wide_base_N8CQ4ZKP2W_result.json`)。

勝ったデッキ(31枚)は**防御が主、エンジンは各1枚**という構成だった。防御がShrug It Off 4・Colossus 2・Taunt 2・True Grit・Feel No Pain・Crimson Mantle、エンジンがRupture・Bloodletting・Pyre各1枚、ドローがBattle Trance 3・Pommel Strike 2。呪いは0枚で、ショップでStrikeを3回除去して初期札はStrike 2・Defend 3まで減っている。最終戦の終盤で**Strength 30**。負けたD6A1F8C3E5のデッキは27枚中にStrike 6・Defend 3・呪い3を抱え、エンジンが無かった。

**構築の順序が効いている。Act 1では防御しか取っていない**——Shrug It Offを3連続で選び、Colossus/Setup Strike/Second Wind/True Gritを退けた。エンジン1枚目のBloodlettingはAct 1 floor 15、RuptureはAct 2 floor 4でようやく入る。さらにAct 1 floor 17で`Offering`(S段位)を含む提示を丸ごとSkipし、Bloodlettingの2枚目以降(act1f13/act2f6/act2f12)も全て退けてBattle Trance・Taunt・Colossusを取っている。**エンジンは1枚で足り、2枚目からは防御を削るだけだった。**これは同日にS段位逃げ道が16seedで劣化4・改善0となった理由そのものである。

**この一件は「1手目の `search_value` が −0.8〜−0.9 なら詰み」という読み方への反証でもある。**N8CQ4ZKP2Wの最終戦もT1で −0.89 だった。あの値はgreedy rolloutで平均的に打った場合の見積もりであり、**勝ち筋が存在しないことを意味しない**。統計としては強い予測子(値1.0で勝率99%、−1.0で18%)だが、個別の局面を諦める根拠には使えない。

→ **改善の当たり所は、デッキがStrengthエンジンのような勝ち筋を組めるかどうか。**HPも打ち回しも、それが無いデッキを救わない。

**Act 3を踏破した2本は、どちらもRupture + Bloodlettingで最終戦Strength 30超(2026-09-08)。** D6A1F8C3E5(`astra_goal_intangible1`、TEST_SUBJECT、Strength 32、29枚)とN8CQ4ZKP2W(`wide_base_N8CQ4ZKP2W`、QUEEN、Strength 30、31枚)。ボスも防御札の柱も違う(Blood Wall 4枚 対 Shrug It Off 4枚)のに、**エンジンだけが一致している**。100本超のrunで踏破したのはこの2本だけ。

`_core_priority` にはこのエンジンを組ませない片方向の噛み合わせがあった。**Ruptureが無い間 `UNCOMMITTED_SELF_DAMAGE`(Bloodletting/Hemokinesis/Offering/Inferno/Blood Wall/Brand/Breakthrough)は報酬点を2〜3減点されるのに、Ruptureが軸の種になるのは「燃料がすでにデッキにあるとき」だけ**——どちらも先には入れない。`astra_base_H2LV6ZJ4XW` act1 f2の提示は `Rupture / Infernal Blade / Bloodletting`、つまり**エンジンの両方が同じ画面にあったのに、どちらも取らなかった**。同じ画面の燃料も燃料として数えるよう直した。

**ただしこの修正は現在の計器では検証できない。**記録済み1649件の報酬決定のうち変わるのは**3件、いずれも古いrunで、16seed基準値では0件**。Ruptureは16runで5回しか提示されていない(1runあたり0.3回)。段位をC→Aまで上げても変化3件・16seedで0件で同じだった。**機序の正しさとして入れるが、勝率への寄与は測っていない。**

なお `_axis` がPerfected Strikeを先に見るためRuptureを持っていても軸がstrikeになる、という当初の仮説は**外れ**だった。Rupture系を持つ状態での報酬判定208件のうち、軸を奪われていたのは6件(古い2runのみ)で、202件は正しくself_damageになっていた。

ただし**ショップで未所持のRuptureを提示された場面には同じ問題が残っていた**。J7GW6DFX9VではPerfected StrikeとBloodlettingを所持していたためstrike軸が優先され、137Gを持ち77GのRuptureを買わずに退出していた。提示中のRuptureと既存の自傷札を先に組み合わせると購入へ変わり、同seedは8勝から12勝へ伸びた。16seed全体では勝利数は1のまま、総戦闘203→207、個別勝ち188→192。Q2VD9LWC7Fも5勝→8勝に伸びたが、これは同時に含まれる`9e2431d`の影響と分離できない。**勝率向上は未証明だが、J7で狙った判断が発火し、悪化seedが無かったため採用する。**

**満杯のポーション報酬をskipした非terminal画面は、ボタンを再試行対象から外すだけでは閉じない。** T3XQ7WM2VPのCRYSTAL_SPHEREでは、同じFlex Potionを3回問い合わせてAutoSlayが停止した。`NRewardButton.GetReward`と`NRewardsScreen.OnProceedButtonPressed`を照合すると、skip済みボタンの無効化・記録に加え、非terminal画面ではbackendのreward setを必要に応じてskipし、overlay stackから画面を直接外す必要がある。修正後の同seedは当該画面を一度で閉じ、Act 2 Floor 6の通常戦まで進んで8勝1敗で自然終了した。ユーザーデータは固定スナップショットから開始し、run後に差分ゼロへ復元済み。

**16seedスイープは、4seedが出せなかった答えを一度で出した(2026-09-08)。** 基準値(commit `d14d60c`): **1勝/16、総戦闘203、個別勝ち188、Act 3到達3本**(D6A1F8C3E5・L3PN5HBQ8T・N8CQ4ZKP2W)。到達actの分布はact1が2本、act2が11本、act3が3本。1周あたり約1時間かかるが、4seedを4周する時間で判定できない答えを4つ集めるより速い。

同じ16seedでS段位逃げ道を測った結果は**劣化4・改善0・同一12**、総戦闘203→193、Act 3到達3→2。4seedでは「1劣化3同一」でコイン投げと区別がつかなかったものが、**16seedでは一方向にしか動かない**とはっきりした。不採用。

つまり `strong_block_shortage` の厳しさは正しい。**ブロックが足りないデッキにS段位のカードを足しても、薄まるだけでブロック不足は解決しない。**「82runが不足に入り48%しか抜けられない」という観測は事実だが、それは直すべき欠陥ではなく、**そのデッキがもう手遅れであることの症状**だった。相関を因果と読み違えていた。

**4seedの固定環境スイープには、変更の良し悪しを判定するだけの分解能が無い(2026-09-08)。** これは個々の変更より重要な発見なので先に書く。環境を固定しているのでrunは決定的で、発火しない変更は**トレースがバイト単位で一致する**。ところが発火した瞬間、カード1枚の違いが以後の全分岐を変え、戦闘数が3つ動く。11周を通して、実際に発火したseedの結果は**改善3・劣化4・変化なし1**——コイン投げと区別がつかない。

しかも劣化は特定のseedに集中する。**P4WZ8NC5HJは発火した変更のほぼ全てで劣化した**(smallheal, actcost, sblock)。このseedの経路が崖の縁にあるだけで、変更の質とは関係がない。4seedでは、発火する変更はどれも1/4の確率でこのseedを踏み、悪く見える。

→ **「4seedで1つ劣化、3つ同一」を根拠に不採用としてきた判断は、いずれも統計的な裏付けを持たない。**採用した3件(turnlethal, normality, aoe)も同様で、それらは機序の正しさで採ったのであって計測で採ったのではない。計測を先に直すこと。

**強ブロック不足ルールにS段位の逃げ道を作るのは有害だった(2026-09-08、16seedで不採用確定)。** 欠陥自体は実在する——`strong_block_shortage`(16枚以上・強ブロック3枚未満)はコア/防御/必要ドロー以外を段位に関係なく見送るが、**ブロックは提示されないカードでは補えないので、このルールには終わり方が無い**。103runのうち82runが不足状態に入り、抜け出せたのは48%だけ。残りは以後の報酬の62%を見送り、S段位109回・A段位95回を捨てている。

S段位のみ通す(自傷・消耗の未確定ペナルティで減点されたもの、重複、不要なドロー札は除く)修正を入れると、記録済み1210件の報酬決定のうち42件が変わる。実機4seedでは3つ同一、P4WZ8NC5HJのみ劣化(12戦→9戦、Perfected StrikeがUnmovableに置き換わった)。上記のとおりこれは判定になっていないため、**不採用ではなく保留**として残す。

**カード報酬の変更も、実機の前にオフラインA/Bで発火数を確かめること。** `data/astra_*_observations.jsonl` の `phase == "card_reward"` を新旧の `choose_card_reward` に通すだけでよい。なおこの手順を作った初回、パッチ適用スクリプトを `exec_module` しただけで `main()` を呼ばず、**適用されていない同一ファイル同士を比べて「変化0」という嘘の測定値を2回出した**。A/Bの前に、パッチ後のファイルに変更が入っていることをgrepで確認すること。

**経路コストをアクト別の実測平均に差し替えるのは失敗した。平均は裾を消す(2026-09-08、不採用)。** 1093戦の実測では通常戦のHPコストがアクトで大きく違う——Act 1が8.2、Act 2が19.2、Act 3が17.1、エリートは通しで31〜33。一律17/32はAct 1の戦闘を2倍に見積もっており、報酬カードを取れる部屋を過剰に避けているはず、と考えてアクト別の定数に置き換えた。**3seedは決定が1つも変わらず、変わったP4WZ8NC5HJが劣化した**(12戦act2f16→11戦act2f6)。

中身がはっきりしている。新しい経路はAct 1 floor 7のエリートを避けて休憩所へ回り、代わりに通常戦を3つ多く踏んだ。その1つで**71→45と26 HPを失い**、ボスへ68で入って9で出て、Act 2 floor 6で力尽きた。旧経路はエリートで15まで落ちたが休憩を挟んでボスへ80で入っている。

**Act 1通常戦のHPコスト分布(n=465): 平均8.3、中央値7、p75=13、p90=18、最大60、無傷が15%。** 「たいてい安いが、たまに致命的」という形をしており、平均値はその裾をちょうど消してしまう。経路計画で比べているのは期待値ではなく生存であるから、この分布に平均を使ってはいけない。加えて、エリートを避けるとレリックも失うが、コスト式はそれを一切評価していない——**エリートの正味コストは31 HPより安い**。

なお全run3111件の地図観測にオフラインで新旧の `choose_map` をかけると、**決定が変わるのは31件(1%)、すべてAct 1**だった。実機4seedで3つが同一だったのは偶然ではなく、この分岐の希少さによる。**経路変更の効果測定は、実機を回す前にこのオフラインA/Bで発火数を確かめること**(`data/astra_*_observations.jsonl` の `phase == "map"` を両版の `choose_map` に通すだけでよい)。

**runログの「Rewards screen did not appear after combat」は普通の戦死である。計器の故障ではない(2026-09-08)。** 全99runのうち55件がこのメッセージで終わっており、一時は計測基盤の障害を疑った。**55件すべて、traceの最後の戦闘記録が `won: false`**——プレイヤーが死んだので報酬画面が出ない、それだけのこと。残る例外終了(watchdog timeout)のうち39件も同じく敗北で、`won: true` のまま終わった5件だけが本物のハングである(いずれもボス部屋入場直後)。**runの成否をログのエラーメッセージで判定してはいけない。traceの最後の `won` を見ること。**

**`NProceedButton` を押しても報酬画面が閉じないことが稀にある。ゲーム側ハンドラはそこでrun全体を落とす(2026-09-08)。** `astra_smallheal_D6A1F8C3E5` が Act 2 floor 11・HP 80/85 という健全な状態で中断した唯一の例。ログを追うと、カード報酬画面が `NRewardsScreen` を再度開き、未受領の報酬が残ったままproceedを押したため画面が閉じず、10秒でTimeoutExceptionが飛んでいる。このコードは `RewardsScreenHandler` の原文をそのまま引き継いだもので、こちらのバグではない。ただしrunを1本丸ごと失うので、`PotionRewardBridge` 側では例外を握って drain loop へ戻すようにした。本当に詰まっているなら AutoSlayer 自身の30秒watchdogが止めるので、握りつぶしても悪化しない。

**休憩所の回復をHP上限との距離で足切りするのは効果が確認できなかった(2026-09-08、不採用)。** 固定4seedの休憩22回中21回がHEALで、76/80で+4、83/85で+2しか戻らない回が8件あった。欠損HPが上限の15%未満ならSMITHへ回す閾値を入れたところ、K7M2QX9BTRが15戦→13戦と悪化、R9TB3LKD6Mが11戦→12戦と改善、P4WZ8NC5HJは同一、D6A1F8C3E5は上記のブリッジ中断で判定不能。**4seedのうち有効3つで上下に割れたため不採用**。恒久強化の価値がその周回内に現れるとは限らず、一方でHPは即座に効く——という非対称が理由の候補だが、この標本では区別できない。

**unsafe拒否ガードの `is_lethal` は1枚しか見ない。ターン全体で倒せるなら止めてはいけない(2026-09-08)。** 瀕死時に「ブロックもリーサルも無い攻撃」をrolloutが選ぶと拒否する安全網があるが、`is_lethal` は単札のリーサルしか判定しない。そのため**複数枚で倒しきれる場面でも、その1枚目が拒否される**。`astra_sims400_R9TB3LKD6M` seq137がそれで、自HP6・3エネルギー・VANTOM残16に対しSetup Strike(7)+Pillage(8)+Strike(6)=21が手札にあったのに、`rollout_rejected_unsafe` でDefendに差し替わり、ボスを**残り1 HP**で生かしたまま敗北した。攻撃者が1体だけなら、その1体を倒すことは被弾を丸ごと消すので、ブロックより強い。`turn_can_clear_threats()` を追加し、攻撃してくる敵が1体かつ今ターンのエネルギーで払える攻撃の合計がそのHPに届くときだけガードを外す。複数体のときは外さない——1体倒しても残りが殴ってくるため。

固定環境4seedで**2つのseedが素通り(ガードが単独攻撃者の局面に当たらなかった)、残る2つはどちらも前進**。P4WZ8NC5HJが9戦act1f6→12戦act1f16、R9TB3LKD6Mはボス残42→9。勝利には届かないが劣化ゼロなので採用する。

**`choose_map` の経路評価は、タイル数の固定順ではなく実測HPコストで比べる(2026-09-08)。** 旧キーは `(unrested_elites, Monster数, -休憩数, エリート数, ...)` で、Monster数がエリート数より先だったため「Monster 4＋エリート1」が「Monster 5＋エリート0」に勝っていた。実測ではAct 2の通常戦が17.0 HP、エリートが32.2 HP、休憩の回復が約26 HPなので、この取引は約15 HPの損。新キーは `Monster*17 + エリート*32 - 休憩*26` を1つのコストにまとめる。

**休憩の価値は「その休憩に到達した時点で実際に欠損しているHP」で足切りする(2026-09-19、commit `ef63c66`)。** heal は bank できない——HP満杯の休憩で26 HPの価値を数えるのは誤り。コストの休憩項を、path上のHP推移(Monster -17 / Elite -32 / 休憩で `min(26, max_hp - hp)` を回復、0でclamp)で得したHPに置き換えた。測定の注意：固定8 seed panelで「flip 53/61・8 seed」と書いた数字は **invalid**。あれは各休憩を decision 時点の欠損HPで評価しており、path上に複数の休憩があると同じ欠損HPを多重計上する。path上でHPを移動させた正実装は flip **4 decisions / 4 seeds**（9X9WQB4QIH (2,4)、EAIF2UUVCK (3,4)、AM8C6YXHSG (0,5)、VTW80ZJA2G (6,7)）で、閾値（decision ≥3 かつ seed ≥3）を越える。pin: `test_map_route_vals_rest_by_hp_missing_when_reached`。

**実走結果（commit `ef63c66` vs 同一 commit の対照 `1d5dd5c`、固定8 seed panel、`-StopAfterAct 3`）：採点 92 → 99（+7）、Act 3踏破 0/8（両臂同じ）。** 公式runで経路が分岐したのは 4 decisions / 3 seeds（9X9WQB4QIH 1件、AM8C6YXHSG 2件、VTW80ZJA2G 1件）で、分岐した seed の採点は +1 / +5 / +1、分岐しなかった5 seed は対照と完全一致。この対応が機序の本体で、HPの価値を足切っても**boss 到達時の HP は4件すべて delta 0**だった（capped 形では `hp_cost = -(boss 時点の HP - decision 時点の HP)` そのもの）。つまりこの変更は HP を貯えるのではなく、同一 HP の経路之間で room 構成（エリート・宝箱・ショップ）を選ぶ方向に動く。AM8C6YXHSG は分岐でエリート `(0,8)` を通し、Act 3 boss QUEEN 戦で Amalgam を 95 → 1 HP まで削った（対照 arm は Act 2 boss で敗退)。機序が正しく、指標は悪化していないので**正しさの改善として採用**したが、Act 3勝率には効かない（1 seed の単発差はノイズ）。

途中の失敗も記録する。**まず「エリートを休憩より優先して避ける」順序入れ替えを試したが機序が発火しなかった**——競合していたのはエリート対休憩ではなくMonster対エリートで、直す場所を間違えていた。**次に戦闘側だけを実測コストにしたら、Act 2のエリートは2→0に減った代わりに休憩が7→5に減り、K7M2QX9BTRはボスに辿り着く前のfloor 13で死んだ**。片側だけ実測値にすると、もう片側が犠牲になる。休憩も同じ尺度に載せて解決した。

固定環境4seedでの比較(いずれも0勝): 合計戦闘50→51、個別の勝ち46→47、Act 2エリート2→1、休憩7→7、Act 2ボス開始HP 82→85と61→62。**差は1〜2でノイズの範囲であり「良くなった」とは言えない**が、設計どおりに機序が動き、どの指標も悪化していない。

`CARD.NORMALITY` は Unplayable の Curse だが、**手札にある間そのターン3枚使うと以降カードを打てなくなる**(`ShouldPlay` が `CardsPlayedThisTurn >= 3` で false)。SlothPowerと同じ形だが発生源が power ではなく**手札のカード**。未対応だと rollout が4枚5枚のターンを計画してしまい、ゲームが拒否する手数ぶんダメージとブロックの見積もりが過大になる。`legal_actions` の先頭で、手札にNormalityがあり `cards_played_this_turn >= 3` なら `END_TURN` だけを返す。山札や捨札にあるだけでは効かない。

**砂creditを「砂とHPのどちらが先に尽きるか」で切り替える案は、実走で悪化したので不採用(2026-09-08)。** 死因の分類器としては正しく働いた(下記)が、`_step_score` の重みに組み込むと逆効果だった。固定環境4seedで現行と比較すると、勝敗・戦闘数は同じで、**唯一効くはずだったInsatiable戦(K7M2QX9BTR)で与ダメージが244→207と37減り、ボス残HPが77→114に悪化**した。HPが先に尽ける局面で砂維持を止めると、後半に緊急の脱出を強いられて手数を失うためと見られる。**分類器として正しいことと、評価関数の重みとして正しいことは別**という例。

**砂の価値は「砂とHPのどちらが先に尽きるか」で決まる(死因の分類としては実測で検証済み)。** 砂余命 = 砂 - 1 ターン、HP余命 = HP ÷ 毎ターン被弾 として、`砂余命 <= HP余命` なら砂が先に尽きる。全runのTHE_INSATIABLE戦18件の最終局面で照合すると、**砂死3件は3件とも「砂が先」、HP死15件は14件が「HPが先」**と正しく分類された(外れた1件はHP32・砂2でHP余命1.4対砂余命1の境界)。砂死3件はいずれもHP33〜35・砂1で、HP余命1.4〜1.7に対し砂余命0だった。

この式なら**閾値を勘で決めなくてよい**。HPが高いほど砂が相対的な脅威になり、HPが尽きかけると自動的に火力とブロックへ資源が回る。「砂4〜5にも半分の重みを付ける」という砂の量だけで切る案は、この検証の前に立てたもので**採用しない**。

**砂の即死はHPを区別しない——モデルも評価も。** `_enemy_turn` は `sandpit == 1` で `player_hp = 0` を返すだけなので、HP30で飲まれてもHP5で飲まれても同じ敗北になり、`search` の値も `-1 + max(0, hp)/100` = -1 で同値。敗北の値としてはそれで正しいが、**意味は違う**——HP30の砂死は「戦えたのに脱出が間に合わなかった」回復可能な負けで、HP5なら次の被弾でどのみち死んでいた。

そして `_step_score` の砂回復creditは **HPを一切見ない一律15点**。これは両方向に外れる: HPが高く砂だけが脅威の局面では安すぎ、HPが尽きかけて脱出しても殴られて死ぬ局面では高すぎる。15という値は同じ関数内で「ブロック1＝1」「ダメージ1＝1」と同尺度なので、**砂1回復＝15ダメージ相当**に固定されている。実際の価値は「その砂が無ければ何ターン後に死ぬか」に依存するので、HPと結び付いているのが自然。**重みを触るなら砂の量だけでなくHPも見ること。**

**砂(Sandpit)死は全28戦中3回で、いずれも「供給が途切れる期間に、砂を最小限で維持していた」形。** 内訳は勝利11・砂死3・HP枯渇14。砂死の3件(`blockfix1`/`cards1`/`tear1`)は**最終HPが33〜35もあり、まだ戦えた**状態で砂が0になっている。

- `blockfix1`: turn2で砂4・エネルギー5・**脱出が手札にあるのに使わず**、turn3も砂3で同じ。砂は4→3→2→1と流れ落ちた。`sandpit_critical`(砂≤2)まで待つ方針のため、撃てる時に撃っていない。
- `cards1`: turn3〜turn7の**5ターン連続で脱出が手札に来ていない**(6枚とも捨札→山札を巡回中)。turn8に来た時には既に砂1。

**供給の途切れを実測した(THE_INSATIABLE戦29件)**: 脱出が手札に無いターンの連続長は1ターンが51回、2ターンが12回、**3ターンが12回**。3ターン以上の途切れが12回起きている以上、**砂2で維持する方針は猶予1ターンしかなく構造的に足りない**。砂は途切れの長さぶんの余裕が要る。

`_step_score` の砂回復creditが砂≤3限定、`sandpit_critical` の直接分岐が砂≤2 という現在の設定は、この途切れ分布を測る前に決められたもの。上げる場合は「砂が豊富な時にFrantic Escapeを優先すると火力が浪費される」という元の懸念があるので、**火力側の損失も同時に測ること**。

**THE_INSATIABLE戦の敗因調査(2026-09-08、環境固定後のArm A)。** 環境を固定したベースライン8seedのうち**4本がAct 2 Floor 16のTHE_INSATIABLEで敗北**した。ボスHP321に対し6〜9ターンで83〜184まで削ったところで力尽きる形で揃っている。**火力が1.5〜2倍足りない**。以下は否定された仮説なので、再提案する前に読むこと。

- **「Normalityが手数を制限している」——この4戦のデッキにNormalityは1枚も無い。** `CARD.NORMALITY`はUnplayableのCurseで、手札にある間そのターン3枚使うと以降打てなくなる(`ShouldPlay`が`CardsPlayedThisTurn >= 3`でfalse)という実在の未対応機構ではあるが、**この敗因とは無関係**。手札に16回出ていたのは別のrunだった。カードを見つけたら、まず**その敗北したデッキに入っていたか**を確かめること。
- **「デッキが大きくて砂(Frantic Escape)が回ってこない」——脱出はほぼ毎ターン手札に来ている。** デッキ22〜25枚で、ボスがturn1に6枚注入するため供給は足りている。
- **「脱出のコスト上昇が火力を食っている」——コストはほぼ1のまま。** 使用ごとに+1されるのは個体単位で、新しい個体が引けている間は上がらない。脱出に使うエネルギーは毎ターン1〜2、他のカードに2〜4。

実際に効いているのは**手数**で、毎ターン3枚前後しか打てていない。エネルギーは余り気味で、カードが足りない。

**Entropic Brewは空きスロットが無い間は使わない。** `EntropicBrew.OnUse` は `while HasOpenPotionSlots` で空き全部を埋めるが、**飲んだ本人のスロットが先に空く**ので、満杯で飲むと「1本を1本に交換」で終わる(実測: `astra_base_K7M2QX9BTR` seq117→118でEntropic BrewがStrength Potionに置き換わっただけ)。空きが1つあれば2本以上になる。戦闘効果は無く `PotionUsage.AnyTime` なので、空くまで持っていても損はしない。`choose_potion` の入口で、全スロットが埋まっているときだけ候補から外す。

**ポーションを抱えて死ぬこと自体は必ずしも誤りではない。** `astra_base_B8KD5NR9GC` はCure All/Power/Strengthの3本を持ったままHP13で敗北し、一見「温存しすぎ」に見えた。だが実際にはHP13・被弾22・敵HP44で、手札の最大火力はCinder+Strikeの24、Evil Eyeで8ブロックしても足りない——**どのポーションを飲んでも助からない局面**だった。「死ぬときは温存を解除する」という変更を試したところ、記録済みの `test_saves_major_potion_after_defensive_potion_in_monster_room` が落ちた。テストの側が正しく、変更は撤回した。**敗北時の所持ポーションを見るときは、飲んでいれば勝てたかを必ず確認すること。**

**「取得方針に攻撃の下限が無い」という仮説は測定で否定された(2026-09-07)。** `astra_goal_cards1` のAct 2ボス到達デッキ(28枚中ブロック10・攻撃約10)を目で見て一般化したものだったが、8seedのベースライン(`data/astra_base_*`)をゲーム自身の `type` で数え直すと**ほぼ全てのデッキでAttackがSkillを上回っていた**(例: B8KD5NR9GC 21枚でAttack11/Skill9、T3XQ7WM2VP 17枚でAttack11/Skill6)。「攻撃札 < ブロック札」が成立するのはカード報酬78件中10件だけで、`strong_defense_bonus` に攻撃優先の譲歩を足しても**78件中0件しか判断が変わらなかった**。変更は撤回した。**この方向を再提案する前に、必ず同じ数え直しをすること。**

ベースラインそのものも記録しておく: base `ae68b6c` の8seedで **1勝7敗**(勝ちはD6A1F8C3E5のみ、残HP22/98)。敗北した7本の敗因は「その戦闘に入る前のHPが足りない」形が多く、デッキ構成そのものではない。

`astra_goal_deck2` と `astra_goal_cards1`(seed D6A1F8C3E5)はどちらもAct 2 Floor 16のTHE_INSATIABLEで敗北した。**未モデル機構による敗北ではない**——砂地の即死は `_enemy_turn` の `SandpitPower == 1` で正しくモデル化されており、`search_value` もターン4以降ずっと−0.85〜−1.05で「負けている」と正しく報告していた。ボスHP321に対し到達点は111と105で、砂時計の下で火力が足りない純粋なレースの負けである。deck2の敗北ターンは手札に脱出も引き札も無く、その時点で詰んでいた(脱出は手札に来た5回とも全て使われている)。両runとも敗北後にAutoSlayのwatchdogが報酬画面を待って30秒でタイムアウトするため、`result.json` は書かれず終了コード1になる——**watchdogのstack traceはクラッシュではなく敗北のサイン**で、ログの `Overlay Stack: NGameOverScreen` で判別する。

cards1のAct 2ボス到達時のデッキは28枚で、ブロック札10枚(Defend 5、Blood Wall 4、Flame Barrier)に対し攻撃札は約10枚だった。`_block_starved` の40%判定はブロック札を足すとデッキも増えるため収束が遅く(1枚足すと左辺+5・右辺+2)、28枚10ブロックでもまだ「防御不足」を返し続ける。取得方針には**防御の下限はあるが攻撃の下限が無い**。ただしこの非対称は逆向きの失敗記録(29枚・強防御2枚のみでの敗北)を受けて作られたものなので、2runだけを根拠に閾値を動かさないこと。

Frail対応漏れとVigorを入れた `astra_goal_frail1`(seed D6A1F8C3E5、base 1b737ee)は**14戦連勝でAct 2ボスを突破し、Act 3 Floor 15のTEST_SUBJECTで敗北**した。それまでの4run(deck2/cards1/tear1/status1)は全てAct 2 Floor 16のTHE_INSATIABLE止まりだったので、Frailの取りこぼしが実際に効いていたことになる。TEST_SUBJECT戦はHP100を18まで削ったあと `AdaptablePower` の復活でHP200の次形態になり、攻撃が10×3→10×4→10×5と増える。ターン7にHP18で50被弾して敗北。ここでも `search_value` はターン3から−1.03〜−1.26で負けを正しく報告していた。**Act 3勝利は未達**。

`POWER_NAMES` に `POWER.FRAIL` はあったが、**ゲームが実際に出すのは `POWER.FRAIL_POWER` だけ**で、この対応表は一度も機能していなかった。未対応idはそのまま素通しされるため、`combat.py` が完全に実装しているFrail(ブロック×3/4)が全rolloutで無効になり、モデルは自分のブロックを3割過大評価していた。Weak/Vulnerable/Strengthは短縮形と`_POWER`形の両方が登録されているのに、Frailだけ短縮形しか無かった。**対応表を足すときは実トレースの観測idと突き合わせること**——`data/astra_goal_*_observations.jsonl` の `player.powers[].id` を集計すれば未対応idが出る。この方法で `POWER.VIGOR_POWER`(Akabeko)、`POWER.RADIANCE_POWER`、`POWER.NO_DRAW_POWER`、`POWER.RETAIN_HAND_POWER`、`POWER.TENDER_POWER`、ポーション系powerも未対応と分かった。

Akabeko由来の `VigorPower` は対応済み——`ModifyDamageAdditive` はStrengthと同じ加算段(倍率より前)で、**1枚の攻撃カードの全ヒットに同じ量が乗り**、その攻撃の後に `AfterAttack` が自分を全消費して消える。`_spend_vigor` を単体攻撃と全体攻撃の両方の加算箇所で呼ぶ。

`NoDrawPower`(Battle Tranceが自分のドロー後に自分へ付与)は `ShouldDraw` が `fromHandDraw` のときだけtrueを返す——**ターン開始時の手札ドローだけ通し、そのターンのそれ以外のドローを全て止める**。`AfterSideTurnEnd` で自分を消す。`_draw_into_combat` に `from_hand_draw` を足し、ターン開始のドローだけTrueで呼ぶ。以前は未実装で、モデルはBattle Trance→Drum of Battleと繋げてドローできると誤認していた。`RadiancePower` は `AfterEnergyReset` で+1エネルギーしてDecrementする。

同じ照合でレリックも対応した。Lost Wisp(Powerカードを使うたび全敵に8のUnpoweredダメージ——`_play_card` の `combo_enemies` 段で処理)、Paper Phrog(powered攻撃のVulnerable倍率を1.5→1.75に。`_vulnerable_damage` でCrueltyと同じ加算段)、Strike Dummy(Strikeタグのpowered攻撃に+3)。Gorget(戦闘開始時Plating 4)とRed Mask(ターン1に全敵へWeak 1)は観測がpowerとして直接出すので実害は無い。Lantern(ターン1に+1エネルギー)も観測のenergyに反映済みで、rolloutは現在ターンから始まるため実害は無い。

`HasTurnEndInHandEffect => true` を持つカードはDLL全体で11枚(Toxic、Burn、Infection、Decay、Beckon、Bad Luck、Wither、Regret、Shame、Doubt、Debt)。**未使用カードを洗う際はこの一覧で照合すること**。うちToxic/Burn/Infection/Decayは `ValueProp.Unpowered | Move` でUnblockableが**付いていない**——ターン終了フックが走る時点でブロックはまだ立っている(クリアは次の自ターン開始時)ので、ブロックが先に吸収する。以前は `_apply_player_damage` へ直接渡していてブロックを無視していた。対してBeckon(6)、Bad Luck(13)、Regretは `ValueProp.Unblockable` を持つので `HAND_END_UNBLOCKABLE` として別に扱う。Regret(ダメージ=手札枚数)、Wither(基本3、外部の`FakeUpgrade`で+3ずつ増える)、Shame/Doubt(ダメージではなくFrail/Weakを自分に付与)、Debt(ゴールドのみ)は未対応。

Decay(`CARD.DECAY`)はUnplayableのCurseだが `HasTurnEndInHandEffect => true` を持ち、手札に残ったままターン終了すると所有者へ **2の固定Unpoweredダメージ**を与える。Toxic/Burn/Infectionと同型なので `HAND_INJECTED_STATUS` に追加した。前2者と違いDecayは戦闘中に注入されるのではなく最初からデッキにあるが、END_TURN側の処理は手札にあるかどうかだけを見るので同じ経路で正しく動く。**未使用カードを「未モデルの可能性」として洗う際、Unplayableだから問題なしと即断しないこと**——Unplayableでも `HasTurnEndInHandEffect` を持つカードは被弾源になる。

Frantic Escapeは `OnPlay` の最後に `EnergyCost.AddThisCombat(1)` を呼ぶため、**使ったその1枚だけ**が戦闘中ずっと1コスト高くなる(Sandpitを+1する処理とは別)。`Card.extra_cost` で個体ごとに持ち、`_effective_cost` に加算し、使用後は増分を載せた同じ個体をdiscardへ戻す。観測は手札の各コピーの現在コストを出すので、エージェント側は `観測コスト − 1` で復元する(実トレース `astra_goal_neowrank1` seq312で観測コスト[1, 2]→extra_cost[0, 1]を確認)。以前はこの分岐がエネルギーを固定で1しか引いておらず、探索が実際には払えない枚数の脱出を打てると誤認していた。

Tear Asunder(`CARD.TEAR_ASUNDER`)はコスト2のRare攻撃で、ダメージ5を **1 + その戦闘で受けた「ブロックを貫通したダメージ」イベント数** 回ヒットさせる(強化でダメージ+2)。`CombatManager.History` の `DamageReceivedEntry` のうち `UnblockedDamage > 0` の行を数えるので、多段攻撃は貫通したヒットごとに1加算される。`Combat.unblocked_hits` で戦闘を通して数える——自傷ダメージは `DamageReceivedEntry` ではないので `_apply_player_damage` ではなく `_enemy_turn` の `damage_events` 側で数える。観測は手札のTear Asunderに `CalculatedHits` を出すため、エージェント側の再構築はその値−1を使い、正確に復元できる。

Stokeは当初この理由で保留にしていた(全試走で手札27回・`rollout_success` 0回)。後に別seedの検証で最大の死に札になったため実装した——下記参照。

Spoils Map(`CARD.SPOILS_MAP`)はUnplayableのQuestカードで、Act 1のマップのTreasure地点にクエストを付け、そこへ行くと600ゴールド。戦闘での未対応ではないが、`choose_map` はこの地点を優先していない。

Byrdonis Egg(`CARD.BYRDONIS_EGG`)は手札に41回来て1度も使われないが、これは `CardKeyword.Unplayable` のQuestカードなのでモデル化の欠落ではない。休憩所の `HATCH` を選ぶと `Byrdpip` レリックを得てデッキから消える。`choose_rest` はHP75%以上のときだけHATCHを選ぶため、それまでは戦闘中ずっと手札を1枚潰す。

**HATCHは恒久的なStrengthではない**（`HatchPower` は `AfterSideTurnEnd` で decrement する counter stack）し、pet（`Byrdpip`）は `combat.py` にモデルが無い——`search()` は HATCH の価値を一切評価できない。「HATCHが選べるなら常にHATCH」はpopulationのrest record 611件で flip **88 decisions / 20 seeds**（engine cardがoptionに出るcard_rewardと同様に、固定8 seed panelでは測れない）だが、`heal_waste → SMITH` という記録済み criterion の wholesale override で、pin 3件（`test_rest_heals_near_boss`、`test_forges_even_next_to_the_boss`、`test_forges_when_the_heal_would_be_mostly_wasted`）を壊す。壊さないことと正しいことは別なので**閉じた**。

**プレイヤーが選ぶ効果をランダムで実装すると、そのカードは探索から永久に避けられる。** `CardSelectCmd.FromHand` を使う Burning Pact と Brand、および**強化版**True Gritは「手札から1枚選んでExhaust」だが、`combat.py` は3つとも常にランダムに選んでいた。結果Burning Pactは「手札の最良札を焼くかもしれない賭け」に見え、`astra_seed2_K7M2QX9BTR` では手札に**55回**来て `rollout_success` は0回だった。`_choose_exhaust_from_hand` を追加し、`EXHAUST_FODDER`(Wound/Dazed/Slimed/Toxic/Burn/Infection/Decay/Beckon/Bad Luck)とモデル未対応カードを優先して捨てる。**Frantic Escapeは意図的に除外**——Sandpitへの唯一の解答だから。未強化のTrue Gritだけは実際に `Rng.CombatCardSelection` なのでランダムのまま。**`CardSelectCmd` が出てきたら、ランダムで代用していないか確認すること。**

`SlothPower` は `ShouldPlay` が `_cardsPlayedThisTurn < Amount` を返すので、**1ターンに打てる枚数がAmount枚に制限される**。RingingPowerと同じく `legal_actions` の先頭で `END_TURN` だけを返す。

Metamorphosis(`CARD.METAMORPHOSIS`)はコスト2のEvent Skill(Exhaust)で、**ランダムな攻撃カードを3枚(強化5枚)山札へ生成し、その戦闘中ずっと無料**にする(`SetToFreeThisCombat`)。生成先は手札ではなく山札。`INFERNAL_BLADE_ATTACKS` のプールと `Combat.free_cards` にそのまま乗る。

`FreeAttackPower` は所持中、手札とプレイ中の**攻撃カードのコストを0**にし、攻撃を1枚打つごとにDecrementする(`BeforeCardPlayed`)。`astra_base_T3XQ7WM2VP` でStrikeが観測コスト0で出ていた4件の正体。

Vicious(`CARD.VICIOUS`)は対応済み。コスト1のPowerで `ViciousPower`(1、強化2)を付与し、powerは `AfterPowerAmountChanged` で**自分がVulnerableを付与するたびAmount枚ドロー**する。付与元はBash/Squash/Break/Taunt/Tremble/Thunderclap/Molten Fist/Dominate/ポーションと散っており、`_apply_enemy_debuff` はEnemyしか返さないので各所にドローを差し込むと漏れる。そこで `step` を薄いラッパーにし、**行動の前後で敵のVulnerable合計が増えたかを1箇所で見る**形にした(実体は `_step`)。この構造は今後「プレイヤーが何かを付与したら」系のpowerにも使い回せる。

旧記述: **未対応のまま残した: `CARD.VICIOUS` と `ViciousPower`。** カードはコスト1のPowerで `ViciousPower`(1、強化2)を付与し、powerは `AfterPowerAmountChanged` で**自分がVulnerableを付与するたびAmount枚ドロー**する。Vulnerableの付与箇所が `CARD_VULNERABLE_TARGET`/TAUNT/TREMBLE/THUNDERCLAP/MOLTEN_FIST/DOMINATEと散っており、`_apply_enemy_debuff` はEnemyしか返さないのでドローを差し込めない。入れるなら単体攻撃パスの出口でVulnerable増加を検出する形になる。`astra_base_M5PC8TQ3BN` で手札12回・`POWER.VICIOUS_POWER` の観測23回。

Stoke(`CARD.STOKE`)は手札を全てExhaustし、その枚数ぶんカードを生成して手札へ戻すコスト1のRare Skill(強化で生成カードも強化済み)。生成は `AddGeneratedCardsToCombat` 系でJSONに実体が無いため、Infernal Bladeと同じ近似——`STOKE_GENERATION`(モデル済みの非Basic・非Statusカード)から抽選する(`ponytail:` コメントあり)。生成カードは無料ではなく自前のコストを払う。

`TangledPower` は所持中、**攻撃カードのコストを+1**する(全Attackに `Entangled` を付与するが、Afflictionに固有ロジックは無くTangledPower側に全て載っている)。自ターン終了で自身を消すので1ターン限り。

`TenderPower` は `AfterCardPlayed` で筋力と敏捷を1ずつ下げ、`AfterSideTurnEnd` にそのターンの枚数ぶんまとめて戻す。**powerを増減させるのではなく `cards_played_this_turn - 1` を読み取り時に引く**形で実装した——`AfterCardPlayed` は解決後に走るので**いま解決中のカードは満額**であり、この形なら自然にそうなる上、ターン終了の戻し処理も要らない(カウンタがターンで戻るため)。powerを直接下げる実装にすると、打ったカード自身まで弱くなる。

敵の `RegenPower` は自ターン終了に `Amount` だけ回復してDecrementする。このモデルの敵は最大HPを持たないので、exportの `MaxInitialHp` を上限に使う。

Blood Vialはターン1開始時に2回復するが、rolloutは常に現在ターンから始まるためLanternと同じく実害が無い。

Havoc(`CARD.HAVOC`)は `CardPileCmd.AutoPlayFromDrawPile(1, Top, forceExhaust)` で、山札の1枚を無料で解決して**廃棄置き場ではなくExhaustへ送る**コスト1のSkill(強化で0)。`astra_seed_R9TB3LKD6M` では手札に39回来て `rollout_success` は0だった。`_autoplay_top_of_draw` を `_autoplay_drawn_strikes`(Hellraiser)と同じ要領で実装した。**このモデルの山札は順序を持たない袋**で `_draw` はランダムに1枚返すため、「一番上」は近似である(`ponytail:` コメントあり)。使えないStatus/Curseが出た場合も手札から消えてExhaustされる。

**低HP時のマップ経路はUnknownを「確定の戦闘より軽く、安全な部屋より重い」中間として扱う。** `astra_seed_K7M2QX9BTR` はAct 2 Floor 13でHP12/85のとき、選択肢がUnknownとShopの2つだけの場面でUnknownへ進み、そこがOvicopter+Tough Eggの戦闘で敗北した。`rest_path`/`safety_path` の `fights` 判定が `{Monster, Elite, Boss}` だけを見ており、**Unknownは戦闘なし扱いだった**。ただしUnknownをMonsterと同じ重みにすると `test_low_hp_prefers_unknown_when_no_rest_is_reachable` が落ちる——「確定の戦闘より、戦闘かもしれない部屋のほうがまし」という記録済みの判断を壊すからで、これは正しい指摘である。よって3段階にした: 確定戦闘=2、Unknown=1(HPが最大値の1/3以下のときのみ)、それ以外=0。1/3という境界は、3/4の帯全体でUnknownを戦闘扱いにすると今回の失敗が正当化する範囲をはるかに超えて経路が変わるため。

**Act 3クリア達成(2026-09-07、seed D6A1F8C3E5、base `3fd097e`)。** `data/astra_goal_intangible1_result.json` に `"act_3_complete": true`、HP22/98、15戦15勝0敗。ゲームの終了コードは0で、ログに `Finished Boss room`(Act 3 Floor 15)があり `Run failed` は無い。決め手は直前に入れたIntangible/Nemesisのモデル化で、最終戦のボスHPはturn7=299(Intangible)→turn8=291(この間8しか削れない)→**turn9=81**(Intangibleが切れた1ターンで210)→turn10で撃破と推移した。**Intangible中は仕込み、切れたターンに火力を集中する**という方針はハードコードしていない——機構を正しく教えただけで `search` が自力で導いている(第3形態の同一手札で、Intangible中はInflame -0.84 > Defend -0.95 > Strike/Bludgeon -0.99の同点、Intangible切れではBludgeonが -0.68 で首位)。

**TEST_SUBJECT(Act 3ボス)の第3形態はIntangibleで、殴っても1しか通らない。** 100/200/**300**HPの3形態で総HP約600。形態変化(`RESPAWN_MOVE`)の間はHP0扱いなので `enemy.alive` が偽になり、攻撃が `legal_actions` から落ちる——ここは元から正しい。問題は第3形態の実際のpowerが `[INTANGIBLE_POWER, NEMESIS_POWER]` なのに、`_enemy_turn` の復活処理が `NemesisPower` しか付けず、しかもそれが**効果のない目印**だったこと。`IntangiblePower.ModifyHpLostAfterOsty` はSlipperyと同じフックで**1以上のHP損失を全て1にする**(Slipperyと違い被弾で消費されない)。`NemesisPower.AfterSideTurnEnd` は自ターン終了ごとに内部boolを反転させ、**Intangibleの付与と解除を交互に**行う——つまり1ターンおきに無敵。実トレース `astra_goal_pacts1` でも第3形態は299→298と1ずつしか減っていない。修正前の探索は第3形態300HPを普通に殴り倒せると信じており、勝てない火力レースに突っ込んでいた。復活時に `IntangiblePower` を付け、`_damage_enemy` で1にクランプし、敵ターン終了で反転させる。**`choose` の致死ゲートでもSlipperyと同じ扱いにする**(ヒット数を返す)——探索モデルだけでは足りない。

第3形態の行動は `PHASE3_LACERATE_MOVE`(10×3) → `BIG_POUNCE`(45) → `BURNING_GROWL_MOVE`(Burn3枚+筋力2) の循環。第2形態の `MULTI_CLAW_MOVE` は自分へ戻り続け、ヒット数が毎ターン増える。

**Pact's Endは条件付きで、条件を外すと完全な空振りになる。** `PactsEnd.OnPlay` は `CanDealDamage`(廃棄置き場が `Cards`=3枚以上)のときだけ攻撃する。`ALL_ENEMY_DAMAGE` に17を無条件で入れていたため、`astra_goal_suicide1` seq483ではAct 3ボス残HP9・廃棄置き場1枚の場面で `lethal_direct` が「確定キル」としてPact's Endを打ち、**0ダメージのまま次の10×6=60被弾で敗北した**。`combat.py` 側の判定に加え、`choose` の致死ゲートの `damage()` でも同じ条件を見る——**探索モデルだけ直しても、pre-rollout の致死判定が別経路で嘘をつく**。0コストなので打つこと自体は無害だが、キル扱いにしてはいけない。

**負け確定の局面で自滅しないこと。** `astra_goal_scarf1` seq463はAct 3ボスTEST_SUBJECTの第1形態をHP0まで削り、復活を待つ自HP2・ブロック0の局面だった。探索は自傷2のBlood Wallを選び、**その場で自分を殺して敗北した**。原因は2つ。(1) 実ゲームのHPは0で止まるが `_apply_player_damage` は負の値まで下げるので、`scored_hp/100` が「ちょうど0で今死ぬ」(-1.02)を「後で大きく被弾して-23で死ぬ」(-1.23)より高く評価していた——`max(0, state.player_hp)` でクランプする。(2) クランプしても即死する手が `immediate` のブロック分だけ得をするので、初手で自HPが0以下になる手には即時ボーナスを与えず、さらに0.01引いて**他のどの敗北よりも厳密に低く**する。rolloutが全て負けを返しても、その場で終わらせる手だけは別扱いにするという意味である。修正後、同じseq463はBlood Wall 2枚を最下位に落としてPrimal Forceを選ぶ。

**`search` の即時ボーナスはEnd turnには与えない。** `step` はEnd turnで敵ターンごと進めるため、`_step_score(before, after)` がEnd turn自身の手柄として**その敵ターンのブロック吸収とキルをcredit**してしまっていた。そのブロックは決定より前から場にあり、End turnが作ったものではない。実測(`astra_goal_thin1` seq94、8シード): End turnの即時+10に対しStrikeは+6で、rolloutの最終HP平均はStrikeのほうが1.5高い(78.20 vs 76.73)のにEnd turnが勝っていた。差は平均+0.026〜+0.071で標準偏差0.004〜0.012、8シードとも同符号——ノイズではない。ブロックが場に立っているターンは常にEnd turnに下駄が履かされる構造だった。修正後、thin1とfrail1で「カードが合法なのにrolloutがEnd turnを選んだ」20局面のうち10局面が実際に手を打つようになった(0コスト14ダメージのByrd Swoopを手札に残してEnd turnしていた `frail1` seq454を含む)。既存の585件は全て成功する。この即時ボーナス自体はDefendがEnd turnに負ける問題への対策として入ったもので(下記)、**カード側のcreditは維持したままEnd turn側だけを0にする**のが正しい形である。

Act 3のFABRICATOR戦は `condition: CanFabricate` が未実装で、`astra_goal_thin1` の敗北した戦闘は34局面中27局面が `rollout_exception_not_implemented` になり、**戦闘まるごとヒューリスティックだけで戦っていた**(トレースの `search_value` が全ターンNone)。`Fabricator.CanFabricate` は `GetTeammatesOf` の生存数が4未満かどうかで、`GetTeammatesOf` は自分を含む同sideの全クリーチャーを指す。実トレースとも一致する(ターン1は自分だけ→召喚付き18ダメージ、ターン2は2体→召喚のみ、ターン3は4体→11ダメージのみ)。加えてFABRICATE_MOVE/FABRICATING_STRIKE_MOVEの `effects` はエクスポータが空のまま出す——召喚が `CreatureCmd.Add` 効果ではなく `SpawnDefensiveBot`/`SpawnAggroBot` というC#ヘルパー経由だからで、`_enemy_turn` に合成の召喚を足した。Fabricateは防御型(Guardbot/Noisebot)と攻撃型(Zapbot/Stabbot)を1体ずつ、Fabricating Strikeは攻撃型のみ、いずれもMinionPower付き。修正後は同じ34局面で未実装例外0・rollout成功20になった。**`effects` が空のMoveStateを見たら、C#側にヘルパー経由の効果が無いか疑うこと。**

FROG_KNIGHTの `HasBeetleCharged || base.Creature.CurrentHp >= base.Creature.MaxHp / 2` も同型。191HPで、**半分(95)を切った最初のターンに一度だけBeetle Charge(35ダメージ)**を撃ち、以降 `HasBeetleCharged` が立つのでTongue Lashへ戻る。このフラグの実行時記録は `enemy.history` にあるので `"BEETLE_CHARGE" in enemy.history` で判定する。もう一方の分岐 `!HasBeetleCharged && hp < MaxHp / 2` はこの条件のちょうど否定なので、`_condition` 末尾の `!` 処理がそのまま正しく効く。**この敵はベースラインでは一度も遭遇しておらず、runが深く進んだ結果として初めて出た**——未実装例外が増えたときは、まず「新しい敵に届いただけ」を疑うこと。

LIVING_SHIELDの `GetAllyCount() > 0` も同じ理由で未実装だった(全runで34局面)。`LivingShield.GetAllyCount` は `c != base.Creature` で**自分を除く**生存数を数える——Fabricatorの生の `GetTeammatesOf` には このフィルタが無いので、2つは意図的に別物である。味方が生きている間はShield Slam、独りになるとSmashへ移り以後Smashを繰り返す。この2つを入れた後、全runの戦闘観測3881局面すべてでrolloutが走り未実装例外は0になった。

Brilliant Scarfは `TryModifyEnergyCostInCombatLate` で、**そのターンにちょうど `Cards-1`(=4)枚プレイ済みのときだけ**手札の全カードのコストを0にする——つまり毎ターン5枚目が無料。モデルは `CARD_COST` からコストを引くので、`astra_goal_endturn1` seq476ではTremble/Giant Rock/Defend/Infernoが観測上すべてコスト0なのに「コスト1・エネルギー0で打てない」と見て、HP121のAct 3ボスを前に無料のGiant Rock(16+筋力11=27)を握ったままEnd turnしていた。`_effective_cost` の最後で0を返すよう実装し、観測には手数カウンタが無いので**「基本コストが正のカードが観測上0で出ている」という指紋**から `cards_played_this_turn` を復元する。復元後、同じseq476はGiant Rockを選ぶ。

DLL全体で `TryModifyEnergyCostInCombat` を実装しているのは、レリックがBrilliant ScarfとSpiked Gauntlets、powerがBorrowedTime/Corruption/Curious/FreeAttack/FreePower/FreeSkill/Tangled/Veilpiercer/VoidFormの計11個(mockを除く)。**コストのズレを見つけたらこの一覧で当たること。** 全runを突き合わせた結果、残る未説明はRupture(旧run 8件)とUnmovable(旧run 2件)だけで、どちらも既存の `Combat.free_cards` 機構が扱う「1枚無料」系の可能性が高い。Strikeがコスト0で出ていた151件はNutritious SoupのTezcataras Ember付与を持つ修正前の旧run(`shop1`/`neowrank1`)のもので、`c6ef39b` で対応済みの既知事象——**新しいバグとして追わないこと。**

**未使用カードを見たら、観測の `cost` とモデルの `CARD_COST` を突き合わせること。** カードのコストを動かす経路は複数ある(Brilliant Scarfの5枚目無料、Nutritious SoupのTezcataras Ember付与でコスト0、Frantic Escapeの使用ごと+1、Stompの攻撃ごと減少、Enlightenmentの1上限)。トレースの手札にある `cost` は常に真の現在コストなので、これと `CARD_COST` がずれているカードは未対応の経路を示している。

**「合法なのに使わなかった」の検出方法**: トレースの `type == "end_turn"` の行で `legal_actions` にまだ `type == "card"` が残っているものを数える。さらに `decision_source == "rollout_success"` に絞ると評価関数の問題、`heuristic_fallback` に絞るとrolloutが落ちている問題を切り分けられる。`decision_reason` が `rollout_exception_not_implemented` なら敵データに未実装のコマンド/条件がある。

`search` の評価は勝利を1、敗北を-1、それ以外を0とし、HP/100と「初手を`_step_score`で採点した値/100」を加算する。**この初手ぶんの`_step_score`加算は、`_greedy_action`が毎ターン使っている評価関数を`search`の初手選定にも通すためのもの**——以前は初手だけ「倒した敵の攻撃ダメージ/100」のみを加算し、Defendでブロックした分を一切creditしていなかった。VANTOM(Slippery持ち)の開幕でこの旧実装を検証したところ、60ターンのgreedyロールアウトが平均するとDefendとEnd turnの差が0.01未満まで潰れ、**End turnがDefendを上回って選ばれる**ことがあった(実戦trace: 何もせず2連続End turnでSlippery込みの被弾を許し、turn2→3で80→61までHPを失った)。`_step_score`をそのまま流用したことで同一局面でDefendが最上位に戻り、実機検証でもVANTOMを残りHP21→43まで追い詰められるようになった(セーブ内Act1ボス撃破・Act2ボス部屋到達を確認)。逃走した敵(hoppers等のESCAPE)は勝利扱いせず、キル報酬も与えない——逃走は敵を倒したのではなく戦闘からの離脱であり、残存敵の殲滅が真の勝利条件である。rolloutはランダムではなく `_greedy_action` を使う。`_greedy_action` は各カードを「倒した敵の攻撃ダメージ(被弾防止) + 与ダメージ - 自己ダメージ + 有効ブロック」で評価し、最善のカードを選ぶ。これによりミニオンを毎ターン確実に倒し、被弾を最小化する。

`PlowPower`(CEREMONIAL_BEAST)は`PowerCmd.Apply`で単に`enemy.powers`へ積まれるだけで、実際の「HPが閾値(`PlowAmount`=150)以下になった直後の一撃でStrengthとPlowPowerを剥がしスタンする」条件は`AfterDamageReceived`という仮想メソッドフックで、抽出JSONの静的effectsリストには一切現れない。デコンパイルで確認の上、`_damage_enemy`に「PlowPowerを持ち、被ダメージ後のHPがPlowPower量以下なら、Strength全消去+PlowPower消費+`move="STUN_MOVE"`」を追加した。未対応のままだと毎ターン+2Strengthで被ダメージが際限なく伸びる「詰みボス」としてシミュレートされ、search値が全アクションで-1前後(常時敗北扱い)になっていた。

**`RingingPower`/`CEREMONIAL_BEAST`の`BEAST_CRY_MOVE`(Act1ボス連敗の直接原因)**: PlowPowerでスタン後の後続パターン(`CRUSH_MOVE`→`BEAST_CRY_MOVE`→`STOMP_MOVE`の周期)で毎回`targets`(プレイヤー)へ`RingingPower(1)`を付与する——これは既存の`PowerCmd.Apply`汎用処理で`player_powers`への格納自体はされていたが、その**実際の効果**が一切モデル化されていなかった。デコンパイルで確認したところ、`RingingPower.AfterApplied`はプレイヤーの**デッキ全カード**に`Ringing`という呪いを刻み、`RingingPower.ShouldPlay`は「そのターン中に既に1枚でもカードをプレイしていたら、Ringingが付いたカードは再生不可」を返す——つまり事実上「そのターンはカードを1枚しかプレイできない」という強烈な行動制限である。この`ShouldPlay`チェックは公式modの`CombatBridge.cs`が使う`CardModel.TryManualPlay`→`CanPlayTargeting`の経路でも`AutoPlayType`の値に関わらず呼ばれるため、手動(エージェント)操作にも適用されることをデコンパイルで確認済み——実ゲーム側の`legal_actions`計算はこの制限を正しく反映するので実プレイでは不正アクションにならないが、**`combat.py`の`search()`ロールアウトはこの制限を一切知らず、実際には出せないはずの複数枚コンボを前提に将来ターンを過大評価していた**。これがCEREMONIAL_BEAST戦での局所的な連敗クラスター(同一セッション内で29戦中17敗、うち5敗がこのボス)の直接原因と特定した。`Combat`に`played_this_turn`フラグを追加し、`legal_actions`は「`RingingPower`を持ち、かつ`played_this_turn`が真」なら`End turn`のみを返すよう分岐、カードプレイ時に`played_this_turn=True`をセットし、`step`のEND_TURN処理冒頭(プレイヤー自身のターン終了時、`RingingPower.AfterSideTurnEnd`のタイミング)で`RingingPower`と`played_this_turn`の両方をリセットする形で対応した。

`KnowledgeDemon`(KNOWLEDGE_DEMON_BOSS)のmove遷移`CurseOfKnowledgeBranch`は`_curseOfKnowledgeCounter < 3`という私有フィールド参照の条件式で、`_condition`が対応パターンを持たず必ず`NotImplementedError`を投げていた——PONDER_MOVEの`next`がこの分岐なので、**戦闘4ターン目以降は毎回rolloutがクラッシュしヒューリスティックへフォールバック**していた。`_enemy_turn`でCURSE_OF_KNOWLEDGE_MOVE実行時に`CurseOfKnowledgeCounter`という合成powerを+1し、`_condition`にこのpowerのしきい値比較を追加して解消した。あわせてPONDER_MOVEの回復量`30 * base.Creature.CombatState.Players.Count`の`Players.Count`(本プロジェクトは常にソロ)を`_amount`で1として解決できるよう対応した。

`MinionPower`(`OwnerIsSecondaryEnemy`)を`AfterAddedToRoom`で無条件付与される敵は、`CombatManager`が生存中の`IsPrimaryEnemy`だけを終了条件に見るため**倒す必要がない**。KIN_FOLLOWER(THE_KIN_BOSS)とTORCH_HEAD_AMALGAM(Act3 QUEEN_BOSS)がこれに該当し、`initial_combat`で`primary=False`を付与する。TOUGH_EGGはOvicopterに戦闘中召喚された時だけMinionPowerが付くため(初期編成メンバーとしては通常のprimary)、対象から除外している。official_agent.pyのヒューリスティックのfocus-fire tie-breakにも`POWER.MINION_POWER`を見て非最優先にする補正を追加した——旧実装はFollower(HP58〜63)をPriest(HP190)より先に削る「弱い方を狙う」順位付けのままだった。

`IsOffBalance`(BOWLBUG_ROCKのPOST_HEADBUTT分岐、`.IsFront`/`.IsAlone`と同型だが`base.Creature.`プレフィックスなしの裸のvalues参照)のような未対応の裸識別子条件は、`values`辞書にそのキーがあれば`bool(values[key])`として汎用解決する(`!`否定は末尾の共通処理が担う)。

`BYGONE_EFFIGY`は`AfterAddedToRoom`で`SlowPower(1)`を自身に付与する(未エクスポート)。これは危険を見逃す方向ではなく**プレイヤー有利**な効果——このEffigyへ被ダメージを与えるたび`ModifyDamageMultiplicative`が「そのターン中に相手へ与えたカード枚数×10%」ぶん被ダメージを増加させ(自ターン開始でリセット)、1ターンに複数カードを叩き込むほど後続カードの実効ダメージが伸びる。未対応だと同ターン内の連続攻撃の実効値を過小評価するだけで、危険を見逃すわけではないため優先度は低い(未対応のまま)。

**`IllusionPower`の付与漏れ(dead code)**: `step`のEND_TURN処理は以前から「IllusionPowerを持つ敵は敵フェイズ終了後に最大HPで復活する」ロジックを持っていたが、PARAFRIGHT・EYE_WITH_TEETHとも`AfterAddedToRoom`で無条件付与される`IllusionPower(1)`(未エクスポート)を**`initial_combat`/`_summon`のどちらも一度も付与していなかった**ため、このロジックはプロジェクト全期間にわたり到達不能だった。両モデルの初期編成付与(`initial_combat`)と戦闘中召喚付与(`_summon`、THE_OBSCURAのILLUSION_MOVEなど)の両方に`IllusionPower`付与を追加して解消した。

**`IllusionPower`復活後、`move`が解決不能な合成stateに固まる**: 上記の復活ロジックはHPだけ最大値に戻し、`move`フィールドには一切触れていなかった。デコンパイルで確認したところ、`IllusionPower.AfterDeath`は実際には死亡した瞬間に`SetMoveImmediate(new MoveState("REVIVE_MOVE", ...))`で**実行時にのみ生成される`"REVIVE_MOVE"`**へ強制遷移させており、このstate idはエクスポートJSONのstate machineに一切存在しない(Parafright/EyeWithTeethとも実際の攻撃stateは1つだけで、それとは別枠)。復活後もこの`move`値がそのまま残るため、同じ`search()`ロールアウト内でこの敵が生き返ったまま次の`_enemy_turn`を迎えると`_state()`が見つからず`StopIteration`で丸ごとクラッシュする。加えて、実機ブリッジ(`CombatBridge.cs`の`move = enemy.Monster?.NextMove.Id`)がこの復活直後の一瞬を観測タイミングで捕まえた場合、`rollout_choice`が`observation["move"]`を無条件に信用して**そのままEnemyへ詰めていた**ため、同じクラッシュが実機run側でも起こり得た——`choose()`の例外フォールバック(`StopIteration`は捕捉対象)によりその1手だけ静かにヒューリスティック行動へ切り替わるため、ログ上は気付きにくい。`step`のEND_TURN復活処理で`move`を`spec["initial_state"]`から`_resolve_move`し直すのに加え、`rollout_choice`側でも`observed["move"]`がそのモンスターの`states`に実在しない場合は同じ方法で解決し直すよう二重に防御した。THE_OBSCURA+PARAFRIGHT戦で「search_valueが強気(+2.24)なのに即死する」という実機での再現パターンの調査中に発見。

**「取ったのに使っていないカード」監査から追加した15枚**（先生の実況フィードバックがきっかけ）: Flame Barrier(2コスト、Block12+`FlameBarrierPower(4)`——被弾するたび攻撃元へ4反射し、敵ターン終了時に消える。プレイヤー側のThornsPowerと考えればよい)、Molten Fist(1コスト10ダメージ+対象の既存Vulnerableを同量追加)、Not Yet(2コスト自己回復10、Exhaust——`Combat`にmax_hp概念が無いため上限なしで加算する安全側の簡略化)、Offering(0コスト自傷6(Unblockable)+エネルギー+2+3ドロー、Exhaust)、Pacts End(0コスト全体17ダメージ)、Pommel Strike(1コスト9ダメージ+1ドロー)、Drum of Battle(1コスト2ドロー)、Master of Strategy(0コスト3ドロー、Exhaust)、Production(0コストエネルギー+2、Exhaust)、Impatience(0コスト、手札に攻撃札が無い時だけ2ドロー)、Mind Blast(1コスト、山札枚数ぶんダメージ)、Body Slam(1コスト、現在Blockぶんダメージ)、Believe in You(0コスト、唯一の味方=自分へエネルギー+2)、Finesse(0コストBlock4+1ドロー)。抽出は`IroncladCardPool`/`ColorlessCardPool`(デコンパイル済み、計151枚)を正とし、Power型カード・ループ/RNGを含むもの・`PowerCmd.Apply<X>`が既知安全リスト(Strength/Vulnerable/Weak/Frail/Thorns/FlameBarrierPower)外のものは機械的に除外して安全側候補のみ実装した。ドロー・ハンドサーチ・ポーション生成・カード自動プレイなど新たな山札操作プリミティブを要するもの(Cascade、Havoc、Alchemize、SecretTechnique/SecretWeapon、Anointed、Scrawl、GangUp、GoldAxe、Rend、TearAsunder、Spite、Volleyなど)は意図的に見送り。CardModel.Titleは実際のローカライズ文字列を持たないため(デコンパイルにローカライズJSONが含まれない)、`combat.py`側の表示名は内部識別子として独自に定めており、実ゲーム画面の表示文言と一致している保証はない——`official_agent.py`の`CARD_NAMES`さえ同じ文字列を指していれば動作上は問題ない。

**ドローカードが手札の最後まで温存されてしまう問題**(先生の実況フィードバック): `_step_score`は「防いだダメージ+与ダメージ-自傷+有効ブロック」のみで、Battle Trance等の純ドロー札はどの項にも寄与せずスコア0になるため、`_greedy_action`は常に他の正スコアの札を先に選び、ドロー札は**エネルギーを使い切った後の最後**に打たれてしまい、引いた分を同ターン中に使う機会を失っていた。`_step_score`に「このステップで実際に引いた枚数×0.3」という小さなボーナスを追加した——実ダメージ/ブロックの得点(通常5点以上)より十分小さく、0点同士の選択肢間のタイブレークとしてのみ働くため、本来優先すべき攻撃/防御を上書きすることはない(`state.turn == combat.turn`でEnd turn自身の即時スコア計算には適用しないようガードしている)。

**先制ミニオン(KIN_FOLLOWER)を優先すべきという実況フィードバックの検証結果**: THE_KIN_BOSSの実編成(KIN_FOLLOWER×2+KIN_PRIEST)で`search()`を直接検証したところ、フォロワー先制とプリースト集中はスコアがほぼ同点(ノイズの範囲内)で、明確な偏りは確認できなかった。既存の`_step_score`の`prevented`項(敵を倒すと将来の被弾を防ぐ)が既にこの価値観をロールアウトを通じて織り込んでいるため、根拠不明のまま調整を入れることは見送った(「新しい発見の扱い」——ノイズを傾向と誤認するリスクを避けるため)。

`ENTOMANCER`のPersonalHivePower/PHEROMONE_SPIT_MOVE**(以前は「既知の未対応、見送り」としていたが、Act2ボス戦の連敗調査中に再検証し対応した): `AfterAddedToRoom`で`PersonalHivePower(1)`を無条件付与し(未エクスポート)、`PersonalHivePower.AfterDamageReceived`は「このEntomancerがpowered attackを受けるたびAmountぶんのDazedカード(Unplayable/Ethereal)を山札のランダム位置へ挿入する」——`_draw`は山札からランダムにpopするため、山札への追加位置は挿入順に関係なく単純追記で等価。`step`の単体対象・全体攻撃どちらのダメージ適用点にも、命中した敵の`PersonalHivePower`合計ぶんDazedを`draw_pile`へ追記する処理を追加した。加えて`PHEROMONE_SPIT_MOVE`(`SpitMove`)の実体は「`PersonalHivePower.Amount < 3`ならPersonalHivePower+1とStrength+1、3以上ならStrength+2のみ」というif/elseだが、静的エクスポータはメソッド本体中の`PowerCmd.Apply`呼び出し3つ(PersonalHivePower+1・Strength+1・Strength+2)を条件を無視してすべて書き出しており、**既存の汎用ハンドラをそのまま通すと毎回Strength+3(上限なし)という実際より速い成長を敵に与えてしまっていた**(危険を実際より高く見積もる方向のバグ)。`_enemy_turn`はこの1手だけ汎用effectsループをスキップし、`PersonalHivePower`の現在値を見て正しい分岐を再現する専用処理に置き換えた。

`BYRDONIS`は`AfterAddedToRoom`で`TerritorialPower(1)`を自身に付与する(未エクスポート)。これは`AfterSideTurnEnd`で**どのmoveを実行したかに関係なく毎ターン無条件で+1 Strength**を付与する常時成長効果で、`_enemy_turn`で`enemy.model=="MONSTER.BYRDONIS"`の場合に常時+1 Strengthを加える形で対応した(特定moveへの紐付けなし)。

`SLUMBERING_BEETLE`は`AfterAddedToRoom`で`PlatingPower(15)`と`SlumberPower(3)`を無条件付与する(未エクスポート)。SlumberPowerはSNORE_NEXT分岐の`HasPower<SlumberPower>()`で既存の`HasPower<>`汎用処理により正しく解決されるため、`initial_combat`でSLUMBERING_BEETLEに`SlumberPower(3)`を付与し、`_enemy_turn`でSNORE_MOVE実行のたび(`next`解決の**前**に)1減らす形で対応した——実際の`SlumberPower.AfterSideTurnEnd`は0到達時に`next`遷移を待たず即座に`WakeUpMove`へ強制するため、減算を`next`解決の後に置くと1ターン余分に眠ったままになる。PlatingPower(毎ターンBlockを再生する効果)は未対応のまま(防御面のみの影響で優先度が低いため)。未対応だと本来3ターン眠っているはずのビートルがrollout内で**1ターン目から**攻撃してくる扱いになり、危険度を過大評価する。

`PHROG_PARASITE`は`AfterAddedToRoom`で自身に`InfestedPower(4)`を無条件付与しており(未エクスポート)、その`AfterDeath`がスロットwriggler1〜4に4体のWrigglerを即座に召喚する「第二フェーズ」構造を持つ。`InfestedPower.ShouldStopCombatFromEnding()`が`true`のため、**Parasiteを倒しただけでは戦闘は終わらない**。`_spawn_wrigglers`で対応し、召喚されるWrigglerは`primary=True`(MinionPowerの雑魚とは逆——こちらは倒す必要がある本体)、初期moveはスタン扱いの`SPAWNED_MOVE`(エクスポート済みJSONに存在)とする。未対応だとrolloutが「Parasiteを倒せば勝ち」と誤認し、直後に湧く4体ぶんの被弾を一切見込まずに攻撃へ全振りする。

Wrigglerの`WRIGGLE_MOVE`は自身へのStrength+2に加え、`CardPileCmd.AddToCombatAndPreview`で`Infection`(捨札へ1枚)を仕込む。`_enemy_turn`の`CardPileCmd.*`汎用ハンドラ自体は既にこの効果を捨札へ積んでいたが、Infectionは`Toxic`/`Burn`と同じ`HasTurnEndInHandEffect`持ちのStatusカード(デコンパイル`Infection.cs`確認: `OnTurnEndInHand`で3点のUnpowered固定ダメージ)であるにも関わらず`HAND_INJECTED_STATUS`に未登録だったため、手札に引き込まれてターンを終えても一切被弾しない扱いだった——WRIGGLER戦が長引くほど溜まるはずの見えないダメージ源が完全に欠落し、`search()`が「ほぼ勝てる」と評価したまま同じ試合が実際には力尽きる、という実機での再現パターン(このバグ発見以前に3例観測)の原因だった。`HAND_INJECTED_STATUS = {Toxic: 5, Burn: 2, Infection: 3}`への追加のみで解消する——Toxic/Burnが手札へ直接注入されるのに対し、Infectionは捨札経由で後のターンに引かれて初めて効く点が異なるだけで、ターン終了時の適用ロジック自体は共通。

`ShrinkPower`(SHRINKER_BEETLEのSHRINKER_MOVEがプレイヤーに付与)は名前に反して**相手の防御力を下げる効果ではなく、付与された側自身の以降のpowered attackダメージを30%減らす永続デバフ**である(`ShrinkPower.ModifyDamageMultiplicative`は`base.Owner == dealer`の時だけ効き、amount<0で`IsInfinite=true`となりターン経過で減衰しない)。ボスでもエリートでもないAct1の通常敵だが、`combat.py`はこれを解釈しない汎用power格納のみで無視しており、実際より30%高いダメージ出力を前提に判断していた。Fuzzy Wurm CrawlerのINHALEも通常戦闘としては例外的な+7 Strength一括付与を持つため、この2体の組み合わせは見た目以上に危険である。

`DECIMILLIPEDE_SEGMENT_FRONT/MIDDLE/BACK`(Act2エリート`DECIMILLIPEDE_ELITE`)は`AfterAddedToRoom`で自身に`ReattachPower(25)`を無条件付与しており(未エクスポート)、**HPが0になっても他のセグメントが1体でも生きていればその場では死なない**。`ReattachPower.AfterDeath`はまず`SetMoveImmediate(DeadState)`でmoveを`DEAD_MOVE`に即座に切り替え(自分のターンを待たない)、次に自分のターンで`DEAD_MOVE`(何もしない)→`REATTACH_MOVE`(`DoReattach`が`base.Amount`=25回復)を経て通常のWRITHE/BULK/CONSTRICTローテーションへ復帰する。`ShouldOwnerDeathTriggerFatal`/`DoReattach`はいずれも死亡・reattach時点で`AreAllOtherSegmentsDead()`をチェックしており、**他の全セグメントが同時に死んでいる場合のみ本当の死亡**として扱われ全滅演出に入る。`REATTACH_MOVE`はJSON上のstateとしては存在するが(`next`遷移は汎用`_resolve_move`で解決できる)、回復自体はカスタムpowerメソッドのため`effects`リストに現れない。`step`のダメージ適用2箇所(単体/全体)でalive→not aliveの遷移を検出し、他セグメントが生存中なら`move="DEAD_MOVE"`をタグ付けし、`_enemy_turn`はこのタグを持つ「HP0の敵」だけ早期returnを素通りさせて状態機械を進め、`REATTACH_MOVE`実行時に+25回復する形で対応した。未対応のままだと**セグメントを1体倒すたびに本当に脅威が1体減ったとシミュレータが誤認**し、2ターン後に25HPで復帰してくる分の被弾を一切見込まずに残り2体へ攻撃を素通りさせる——3体編成のこのエリートを繰り返し倒しきれず足止めされていた実戦loss(Act2 Floor13)の直接原因。

`INFESTED_PRISM`(Act2エリート`INFESTED_PRISMS_ELITE`)は`AfterAddedToRoom`で自身に`VitalSparkPower(VitalSparkAmount=2)`を無条件付与し(未エクスポート)、`PULSATE_MOVE`実行のたびさらに`VitalSparkAmount`ぶん積み増す(実トレースで2→4に倍化を確認)。`VitalSparkPower`自体はダメージを増やさない——`BeforeCombatStart`/`AfterCardEnteredCombat`でプレイヤーの**Skillタイプの全カード**に`Tainted`Affliction(量は常時`VitalSparkPower`の現在値に同期)を付与し、`AfterCardPlayed`でTaintedカードをプレイするたび`TaintedPower`(`ModifyDamageAdditive`で「powered attackで自分が対象の時だけ+`base.Amount`」)をプレイヤー自身に付与、`TaintedPower.AfterSideTurnEnd`が敵ターン終了時に自動で剥がれる。つまり**Shrug It Off等のSkillを連打するほど、その直後の被弾が加算式に伸びる**罠で、実戦loss(Act2 Floor7、Infested Prismsエリート)ではShrug It Offを連続プレイした結果TaintedPowerが4まで積み上がり、JAB_MOVE(15ダメージ)が15+4=19に増幅、8ブロックを引いても11点被弾してHP15→4まで削られ、次ターンに力尽きた。各カードの型はデコンパイルした`OnPlay`コンストラクタ(`base(cost, CardType.X, ...)`)で個別に確認し、Skillは`SKILLS`定数(Defend/Shrug It Off/Battle Trance/Primal Force/Relax/Tremble/Bloodletting/Dominate/Equilibrium/Impervious/Lift/Ultimate Defend/Taunt)とした——InflameはPower型、Frantic Escape/SlimedはStatus型でありSkillではないため対象外(ここを誤ると危険性を過大/過小評価する)。「特定のカード実体だけがTaintedになる」という本来の粒度は、Skillカードのほぼ全量が付与対象になる実態から「VitalSparkPowerが立っていればどのSkillを弾いてもTainted」という近似で置き換えた。`step`でSkillカードプレイ時に生存中の敵の`VitalSparkPower`合計ぶん`TaintedPower`をプレイヤーへ付与し(このガードは`BATTLE_TRANCE`/`SHRUG`等の早期returnより前に置く必要がある——後段の共通ブロックまで届かないカードがあるため)、`_enemy_turn`の`DamageCmd.Attack`計算にStrengthと同様の加算項として追加、`step`のEND_TURN処理の最後で`TaintedPower`を0にリセットする形で対応した。未対応のままだと敵ターンの被弾予測がSkill連打にまったく反応せず、Shrug It Offで固めているつもりが実は被弾を増幅させている状況を見逃す。

`MYTE`(TOXIC_MOVE)と`MECHA_KNIGHT`(FLAMETHROWER_MOVE、Act3)は`CardPileCmd.AddToCombatAndPreview`で`PileType.Hand`を対象に、それぞれToxic 2枚・Burn 4枚を**山札や捨札ではなく手札へ直接**追加する。`_enemy_turn`の`CardPileCmd.*`汎用ハンドラは従来どの`PileType`指定であろうと一律で捨札(discard_pile)へ積んでいたため、この2体だけは実際と異なる場所にカードを送っていた。ToxicとBurnはいずれも`HasTurnEndInHandEffect`(手札に残ったままターンを終えると発動)を持つカードで、Toxicはプレイヤーに5点、Burnは2点の**Unpowered(Strength等で増減しない)固定ダメージ**を与える——実戦loss(Act2 Floor6、MYTE×2)でHP48→46→28→12と急落した一因はこれで、捨札行きの汎用処理では山札に混入するだけで即座の被弾に繋がらず、危険度を大きく過小評価していた。`_enemy_turn`は`effect["arguments"][1] == "PileType.Hand"`の時だけ`discard`ではなく`hand`へ積むよう分岐し、`step`のEND_TURN処理は「自ターン終了時に手札に残っているToxic/Burnの分だけ先に被弾させてから手札を捨札に送り(この時点で手札は空になる)、続く敵ターンでMYTE等が新たなToxic/Burnを手札へ直接注入し、最後にその上へ通常の5枚を追加ドローする」という実際の順序(自ターン終了→捨札→敵ターン中の注入→次の自ターン頭のドロー)を再現する形に組み替えた。`HAND_INJECTED_STATUS = {Toxic: 5, Burn: 2}`で管理し、Toxicは`CARD_COST`に未登録のため(コスト1でプレイ自体は本来可能だが)シミュレータ上はプレイして先に処分する選択肢を持たない——安全側(危険を過大評価する側)の単純化として許容している。

`SPINY_TOAD`(Act2)は`PROTRUDING_SPIKES_MOVE`で自身に`ThornsPower(5)`を付与し(既存の`PowerCmd.Apply`汎用処理でpowerの格納自体は対応済み)、次の`SPIKE_EXPLOSION_MOVE`で23ダメージ攻撃と同時に`ThornsPower(-5)`を剥がす。しかし`ThornsPower.BeforeDamageReceived`の実体——「Thornsを持つ相手がpowered attackを受けるたび、ブロック計算とは無関係にAmountぶんのUnpoweredダメージを攻撃者(プレイヤー)へ即座に反射する」——は、powerの格納だけでは自動的に再現されず、`step`のカードダメージ適用側に対応する処理が無ければプレイヤーへの反射ダメージは一切発生しない。実戦loss(Act2 Floor6)ではThorns展開中の自ターンにStrike/Bash等を連打し、23ダメージの本体攻撃に加えてこの反射ダメージが完全に見えないまま被弾しHP35→17→死亡と急落した。`step`の単体対象ダメージ処理・全体攻撃(WHIRLWIND/THUNDERCLAP等)処理の両方に、命中した敵(全体攻撃なら命中前に生存していた敵全員)の`ThornsPower`合計ぶんをプレイヤーへ即時反射する処理を追加した。反射はブロック前・命中した敵の数だけ(カード単位、複数回攻撃するWHIRLWINDは対象ごとに1回)発生し、`_step_score`の自己ダメージペナルティ(`combat.player_hp - state.player_hp`の差分)には既存の仕組みでそのまま反映されるため、スコアリング側の追加対応は不要だった。

`_greedy_action` の評価には3つの補正がある。(1) primary(ボス)を倒した場合はその残りHPぶんを加算し、復活するミニオンよりボスのトドメを優先する。(2) Slipperyを剥がした分を加算し、Slippery持ちのボス(例: VANTOM)への攻撃を促す。(3) BASH/TREMBLEのようなVulnerable付与カードには、手札の後続アタックの強化分(ダメージの1/2)を加算し、弱体付与を先に打つ。プレイヤーのStrengthは攻撃ダメージに加算され、Ashen Strikeはexhaust山の枚数、Perfected StrikeはStrikeタグ数で増加する。IllusionPowerを持つミニオン(例: Parafright)は敵フェイズ終了時に最大HPで復活し、SAILのような味方バフは自分以外の生存敵に適用される。

`STRIKE_TAGGED`はgameの`CardTag.Strike`と同じ集合で、Pommel StrikeもStrikeタグを持つ(decompile v0.107.1の`CanonicalTags`)。panel実測のPerfected Strike乖離31件中27件がこの欠落の説明だった。policy側の`STRIKE_TAGGED_REWARDS`はreward tier用の別集合でPommelを含まないが、panelのcard_reward 103件でPommel Strikeがoptionとして出たrecordが0件なので、ここを変える意味はmeasureできない(変更しない)。

### `ironclad.py`

公式Bridgeとは独立した単一敵モデルである。`State`、`legal_actions`、`step`、深さ60のMCTS (`search`) を持ち、初期状態はHP80、Strike 5、Defend 4、Bash 1である。`load_enemy` は敵JSONのclass名を正規化して読む。

### `act_map.py` / `extract_effects.py`

`act_map.load_map` はpoint ID重複、存在しない子、隣接しないrowを拒否する。`paths` はAncientからBossまでの全経路、`matching_paths` はroom type列に一致する経路を返す。

`extract_effects.effects` は逆コンパイルC#の指定メソッドから、攻撃、block、heal、summon、escape、kill、HP設定、power、card pileのコマンドを順序付きで抽出する。CLIは敵JSONの状態機械とperformメソッドへ効果を追記する。

## C# Bridge

### 共通

`Entry.Initialize` は `--sts2ai-autoslay` または `--unlock-ironclad-epochs` がある場合だけ起動する。AutoslayではHarmony patchを適用し、`IroncladPatch` が新規ランのcharacterをIronclad、seedをコマンドライン値へ固定する。epoch解除のみの起動ではIronclad Epoch 2～7を取得・公開して終了する。

Bridgeはゲームの標準Handlerをagent modeだけ差し替える。`CombatBridge`、`MapBridge`、`RewardBridge`、`RestBridge`、`ShopBridge`、`EventBridge` がそれぞれのphaseを担当する。

### `combat` (`CombatBridge.cs`)

Combatのplayer turnで、hand、pile、potion、player powers、敵のHP/block/move/history/intent/powerを観測する。カードはhand indexと合法target、potionはslotと合法target、最後に `end_turn` を `legal_actions` として出す。

action受信後、cardはhand indexとcard ID、potionはslot・potion ID・target・queue状態を再検証して公式APIへ渡す。`agent-max-combats` の上限を超えたcombatは元のHandlerを使う。終了時は `combat_end` traceを書く。

### `map` (`MapBridge.cs`)

合法な次地点を公式の `MapTravel.GetTravelablePointsFrom` から作る。最初はStartingMapPoint、最終行はBoss、二体目のBossがあればそのpointを候補にする。map observationにはrun情報、全pointのparents/children、legal map actionを含める。選択は `VoteForMapCoordAction` をenqueueして `RoomEntered` を待つ。最初のsnapshotは `bridge-map` に一度だけ保存する。

### `card_reward` (`RewardBridge.cs`)

カード報酬画面をcaptureし、カードとalternative、playerのHP/max HP/gold/deckを観測する。`card_reward` または `card_reward_alternative` のindexとIDが一致した場合だけUI signalを発火する。`Skip` はlocal reward setをskipして報酬を回収する。

### `rest` (`RestBridge.cs`)

有効なRestSite buttonを観測し、`index` と `option_id` を検証してクリックする。Proceed buttonまたはoverlayの応答を待つ。

### `shop` (`ShopBridge.cs`)

Merchant inventoryから、カード・relic・potion、削除費用、削除可能カード、gold、deckを観測する。legal actionは購入可能な `buy_card`、`buy_relic`、`buy_potion`、削除可能な `remove`、常に存在する `skip` である。

購入は商品IDとslot/index、削除はdeck indexとcard IDを再照合してから実行し、最後にinventoryを閉じてProceedする。agentが2分以内に返答しなければskipする。Bridgeは商品の合法性だけを提供し、axis gatingと購入優先度はPythonの `choose_shop` が決める。

### `event` (`EventBridge.cs`)

agent modeで `BYRDONIS_NEST` のロックされていないTAKE optionがあればクリックする。その後は通常の `EventRoomHandler` に委譲する。汎用イベントのJSON交換はない。

### potion card selection

`PotionChooseCardPatch` はPowerPotion、ColorlessPotion、AttackPotion、SkillPotionのカード選択を固定処理する。PowerPotionは現在energyで払える最初のカード、それ以外は最初のカードを選び、skip可能ならnullを返す。

## ファイルプロトコル

ゲーム側は `--bridge-observation`、`--bridge-action`、任意で `--bridge-trace` と `--bridge-map` を受け取る。`AgentIo.NextSequence()` の最初のseqは0で、phaseをまたいで増加する。C#とPythonは一時ファイルからrenameしてJSONを交換する。

```json
{
  "seq": 12,
  "terminal": false,
  "phase": "combat",
  "legal_actions": []
}
```

Python actionには同じseqを付ける。C#はaction JSONを25msごとに読み、seq不一致・不完全JSONを無視する。待機deadlineは2分である。

| phase | observationの主な項目 | actionの主な項目 |
| --- | --- | --- |
| `map` | `run`、`map`、`legal_actions` | `type=map`、`col`、`row` |
| `combat` | `turn`、`player`、hand/pile、potions、enemies、`legal_actions` | `card` / `potion` / `end_turn`、index/ID/target |
| `card_reward` | `player`、`cards`、`legal_actions` | cardまたはalternativeのindex/ID |
| `rest` | `run`、`player`、`legal_actions` | `type=rest`、`index`、`option_id` |
| `shop` | `gold`、deck、商品列、`remove_cards`、`legal_actions` | `buy_*` / `remove` / `skip` |

`terminal: true` は `stop-after-agent` または `stop-after-reward` で終了するときに書かれる。通常の戦闘終了はtraceの `phase=combat_end` であり、terminal observationとは別である。

## 代表的な確認コマンド

```powershell
python -m unittest discover -p 'test_*.py'
python .\ironclad.py --enemy-hp 40 --enemy-attack 8 --simulations 500 --seed 0
python .\combat.py .\data\enemies_overgrowth.json ENCOUNTER.SLIMES_WEAK --simulations 500 --seed 0
```

公式DLLを更新した場合は、Modのビルド、敵・マップJSONの再生成、Pythonテスト、最小公式run、trace/resultの確認を順に行う。

`run_official_autoslay.ps1`は`-AgentScript`を明示しないと`--sts2ai-agent`フラグ自体が付かず、**ゲーム内蔵のAutoSlay AIがコストを無視するような挙動でプレイする**(Pythonエージェントは一切関与しない)。さらに`-AgentMaxCombats`のデフォルトは1で、指定した戦闘数を超えると`CombatBridge.cs`の`ReachedAgentLimit`が働き**2戦目以降は同じくゲーム内蔵AIへ自動的に切り替わる**(実機検証中、「初戦だけコストが減って次戦から減らない」という報告で発覚)。Act単位でエージェントの実力を検証する時は必ず`-AgentScript official_agent.py -AgentMaxCombats 999`のように明示すること——省略すると一見ランが進んでいるように見えても、Python側の改修が何一つ検証されていない。

**戦闘中に自動発動するレリック効果**は元々`combat.py`に一切モデル化されておらず、`CombatBridge.cs`の観測にも`player.Relics`が含まれていなかった(先生からの質問で発覚)。`PlayerCombatState.MaxEnergy`(レリック補正込み)を`max_energy`として観測に追加したのに続き、`player.Relics`も`relics`として追加し、`Combat`に`player_relics`フィールドを新設した。デコンパイルでIroncladRelicPool+SharedRelicPoolの126種を監査し、戦闘関連フックを持つ68種のうち、`TurnNumber <= 1`一発限定の効果(Anchor・Akabekoなど13種)は**初回observationの時点で既に反映済みのため未対応でよい**と判断(searchはturn1を再シミュレートしない)。残る55種のうち、21種はターン跨ぎのロールアウト予測に直結する頻出パターンとして先行実装し、続く34種(BeatingRemnant・RainbowRing・RedSkull・SelfFormingClayなど)は、29種をロールアウトの状態遷移として追加した。BookOfFiveRings・LavaLamp・LuckyFysh・PetrifiedToad・VenerableTeaSetの5種は、初回observation、報酬、ショップ、次戦闘の状態へゲーム本体が反映するため、重複した戦闘状態を持たせずライブ観測を利用する。EventRelicPool(Pael/Orobas/Tezcatara等のAncientイベント専用レリック、約140種)は別系統として未監査である。DemonTongue/CentennialPuzzleは自傷カード(Hemokinesis等)由来の被弾には反応しない近似(FlameBarrierPowerと同じ簡略化方針)である。

レリックには**counter(発動回数)があるが観測に載らない**(`CombatBridge.cs`はrelic idだけを書く。game側は`ShowCounter`/`DisplayAmount`を持つ)。modelは`attacks_played_combat`を自分で数えるが、decisionごとにstateを再構築するのでcounterは常に0から始まる。`0 % 10 == 0`は「発動済み」と読んでしまい、Pen Nib(10攻撃目に発動しその攻撃を倍)とNunchaku(10攻撃ごとにenergy)が**毎戦闘の1発目から発動扱い**だった。実走traceの敵HP乖離(NFH3RMVJ6DのStrike 3件。gameは10攻撃目に倍、modelは1発目で倍)がこれを指していた。counterがunknownのときは「発動していない」と扱うのが正しいので、`attacks_combat >= 10`の条件を追加した。同じ理由で、per-instanceの保存値(ToricToughnessPowerがcardごとに保存したblock、CrimsonMantlePowerの`SelfDamage`)も観測に現れないため、replay照合では復元不能な値として除外している。



## 記録の索引

2026-10-11に、日付順の調査記録と作業ログを`docs/codewiki/`へ分けた。本文は移す前のまま。方策の数値やしきい値を変える前は、ここだけでなく`docs/codewiki/`も検索すること(`grep -rn <語> docs/CODEWIKI.md docs/codewiki/`)。結論は当時の検証の範囲のもので、後の節で訂正されていることがある。

- [`docs/codewiki/2026-08.md`](codewiki/2026-08.md) (1410行): 2026-08の調査記録(未モデル領域の監査、08-15・08-23セッション)。
  - 節: 既知の未モデル領域(2026-08-15 監査) / 2026-08-15セッションまとめ(このセッション区切りでの終了時点) / 2026-08-23セッション: 修正前ベースライン計測(researcher R5)
- [`docs/codewiki/2026-09.md`](codewiki/2026-09.md) (585行): 2026-09の調査記録(09-12・09-13、判定基準の変更、ボスの構造的な壁)。
  - 節: 2026-09-12セッション: 計測環境の再構築と、後回し評価の実測 / 2026-09-12 判定基準の変更: 勝利seed保護から母集団の総合成績へ / 2026-09-13 Act 3ボス(QUEEN)戦の敗因は打ち回しではない / 2026-09-13 敗因の分布と、2つのボスの構造的な壁
- [`docs/codewiki/2026-10-mechanics.md`](codewiki/2026-10-mechanics.md) (2500行): 2026-10前半の機構・パネル記録(event効果、shop、power/relic実装、Rampart・Axebot・Decimillipede等)。
  - 節: event の option effect（v0.107.1、ilspycmd で確認、panel  / shop の affordability は bridge の filter が source（v0 / 未モデルだった power / relic / curse を実装（2026-10-04、実走測定前 / 固定8 seed panel の A/B 完走（2026-10-03）と −6 の原因 / 機構単独の到達性（2026-10-03、sample）と mechanism panel / panel（clean run）の完走読取 / RampartPower：ブロック再付与が敵側に見えていなかった（2026-10-04、commit / Axebot の StockPower：1戦闘が Axebot 3体である事が model に見えな / ThievingHopper のカード奪取（2026-10-04、commit 119cb28） / Rampart の 2nd panel（新3 seed、data/rampart_ab2.sh） / 敵側 PlatingPower の実装と、その修正が勝敗を下げた実走 A/B（2026-10-04、 / Decimillipede の move 本体（export に effects が無い）と、そこか ほか1節
- [`docs/codewiki/2026-10-rounds.md`](codewiki/2026-10-rounds.md) (4750行): 2026-10のRound 4〜135の作業ログと記録品質の教訓。
  - 節: Round 4〜135のほか 未解決 gap の記録: Attack を玩んだ瞬間 player がちょうど 2 減る group / 未解決 gap の切り分けをやり直した: 551 件の player ダメージ差は 48 件が今の  / 長い間使ってきた数字の訂正 ：Act 2 boss「進入 HP 中央値 17 （36%  が 10  / 記録品質の教訓（round 130-135 の文章について）

## 2026-10-11の比較のまとめ

開始時のmain`767b5e2`から、固定seedの比較v2〜v7を順に回した。各比較の原本は`docs/ACT3_EVAL_V*_20261011.md`。

| 比較 | 変更 | 判定 |
| --- | --- | --- |
| v2 | 復活する取り巻き(IllusionPower)への確定討伐を致死回避時だけに限定 | 保留(確認用で発動機会なし) |
| v3 | 致死被弾時に助からない討伐と、主敵が生きている間の取り巻きだけの討伐を強制しない | 保留(同上) |
| v4 | 強ブロック不足時の報酬見送りを撤廃、余剰ゴールドで点数外レリック購入 | 不採用(両集合で悪化)。報酬の変更は取り消し、ショップは保留 |
| v5 | 探索の共通乱数、最後の主敵へのとどめ判定 | 到達度改善として採用(両集合でAct 2突破が増加) |
| v6 | 上の組合せをまとめたmain対`767b5e2`、未使用10 seed | 改善: Act 3踏破1対0(E8282AC0A7)、到達点 改善4・悪化1・同値5 |
| v7 | v6に正しさの修正2件を加えたmain対`767b5e2`、未使用8 seed | 保留: 確定6 seedでAct 2突破1対0、到達点 改善1・悪化1。候補由来の停止1件(余剰ゴールドのレリック購入がOrreryを買った。`849692b`で取り消し) |
| v8 | 余剰ゴールドのレリック購入を取り消したmain対`767b5e2`、未使用16 seed | 改善(弱い): Act 3踏破0対0、Act 2突破4対3、Act 1突破13対15、到達点 改善4・悪化4。v6〜v8の確定32 seed合算はAct 3 1対0、Act 2 7対5、Act 1 28対29、到達点 改善9・悪化6 |
| v9 | コスト0のRageを防御札の後に回さない(`58758bd`)、v8の16 seed(対照再利用)+新規8 seed | 保留: 判断が分かれたのは24 seed中3 seed。集合Aは到達点 改善1、集合Bは悪化1、突破数はすべて同値 |
| v10 | 今日の変更をすべて含むmain(`78c8e59`)対`767b5e2`、未使用8 seed | 改善(弱い): Act 3踏破1対0(DD1018C7FF、対照はAct 2ボスで敗北)、Act 2突破2対1、到達点 改善2・悪化2。v6・v7・v8・v10の確定40 seed合算はAct 3 2対0、Act 2 9対6、Act 1 34対36、到達点 改善11・悪化8 |
| random20 | `dc18fe4`単独、ランダムseed 20本(比較なし) | Act 3踏破0/20、Act 2突破4/20、Act 1突破20/20。死亡はTHE_INSATIABLE 11(到達15で4勝、勝ちは全て満タン入場、入場60未満0勝6敗)、QUEEN 3。詳細は[RANDOM20_20261012](RANDOM20_20261012.md)、対策案は[ACT2_BOSS_PLAN_20261012](ACT2_BOSS_PLAN_20261012.md) |
| v11 | 案A(Act 2通常戦の残りHP重み0.02)対`dc18fe4`、開発用20 seed | 開発用で悪化: Act 2突破3対4、到達点 改善2・悪化7・同値11。確認用は未実施で案Aは`efa7f63`で取り消し。詳細は[ACT2_EVAL_V11_20261012](ACT2_EVAL_V11_20261012.md) |
| v12 | 直行規則の停止・砂脱出の後回し・イベント点数(`efa7f63`)対`dc18fe4`、開発用20+確認用10 seed | 保留(v13・v14で再現せず、当初は到達度改善として採用): Act 3 0対0、Act 2突破 開発用7対4・確認用2対1、到達点 改善11・悪化6・同値13。詳細は[ACT2_EVAL_V12_20261012](ACT2_EVAL_V12_20261012.md) |
| v13 | 現在のmain(`8af98a6`)対`dc18fe4`、未使用12 seed | この集合では悪化(1 seed分): Act 3 0対0、Act 2 2対2、Act 1 9対10、到達点 改善2・悪化3・同値7。v12確認用と割れたのでv14で追加確認。詳細は[ACT2_EVAL_V13_20261012](ACT2_EVAL_V13_20261012.md) |
| v14 | v13と同じ候補対`dc18fe4`、未使用12 seed | この集合では悪化: Act 3 0対1、Act 2 3対6、Act 1 10対11。v12確認用・v13・v14の34組合算でAct 3 0対1、Act 2 7対9。v12の判定を保留に変更。詳細は[ACT2_EVAL_V14_20261012](ACT2_EVAL_V14_20261012.md) |
| v15 | mainからイベント点数を外した版(`038b2ea`)対main、未使用12 seed | 外すと1 seed分悪化: Act 3 0対0、Act 2 2対2、Act 1 8対9。イベント点数が原因という証拠なし。詳細は[ACT2_EVAL_V15_20261012](ACT2_EVAL_V15_20261012.md) |
| v16 | main(`8af98a6`)対`dc18fe4`、未使用20 seed | この集合では1 seed分悪化(Act 2 6対6、Act 1 17対18)。v12確認用・v13・v14・v16の54組合算でAct 3 0対1、Act 2 13対15、Act 1 45対48、到達点 改善11・悪化15。保留のまま。詳細は[ACT2_EVAL_V16_20261012](ACT2_EVAL_V16_20261012.md) |
| v17 | `dc18fe4`・main(`04791ab`)・却下方針全部入り(`1a8e238`)の3版、新DLL、未使用8 seed | 差を検出できず: Act 3 0/0/0、Act 2 2/2/2、Act 1 7/6/6。詳細は[ACT2_EVAL_V17_20261012](ACT2_EVAL_V17_20261012.md) |
| v18 | main(`2f9e814`、補正2件除去・イベント点数・Foul換金)対`dc18fe4`、同じ新DLL、未使用6 seed | この集合では改善: Act 3 0対0、Act 2 4対0、Act 1 5対5、到達点 改善4・悪化0。6組なので確認を継続。詳細は[ACT2_EVAL_V18_20261012](ACT2_EVAL_V18_20261012.md) |
| v19 | v18と同条件、未使用4 seed | 改善: Act 2 1対0、到達点 改善1・悪化0・同値3。v18＋v19の10組でAct 2突破5対0、改善5・悪化0。到達度改善として採用(踏破率は未確認)。詳細は[ACT2_EVAL_V19_20261012](ACT2_EVAL_V19_20261012.md) |
| v20 | v18・v19と同条件、未使用6 seed | 単独では1 seed分悪化(Act 2 0対1、到達点 改善2・悪化1)。v18〜v20の16組でAct 2突破5対1、改善7・悪化1。採用は維持。詳細は[ACT2_EVAL_V20_20261012](ACT2_EVAL_V20_20261012.md) |
| v21 | 強ブロック不足の見送りにS/A級攻撃札の例外(`777a573`)対main、開発用16(対照はv18〜v20候補runを再利用)+確認用12 seed | 保留(集合間で割れた): 開発用Act 2 4対5、確認用Act 1 12対11。悪化3組はいずれもAct 2でPommel Strikeを余分に取っていた。mainから戻した(`e6d659d`)。詳細は[ACT2_EVAL_V21_20261013](ACT2_EVAL_V21_20261013.md) |
| v22 | 報酬でShrug It Offの強ブロック不足・ボス軸の加点を外す(`4c03ab4`)対main、開発用28(対照は既存runを再利用)+確認用12 seed | 保留(集合間で割れた): 開発用Act 2 6対9、確認用4対2。mainから戻した(`fa516cc`)。詳細は[ACT2_EVAL_V22_20261013](ACT2_EVAL_V22_20261013.md) |

あわせてゲーム再現の正しさの修正2件(Perfected StrikeがUltimate StrikeをStrikeとして数える、強化Ashen Strikeの上乗せ)を入れた。
v2〜v5の監査でモデルとゲームの一致は99.8%、残った不一致はこの2件でほぼ説明できた。

学んだこと:
- 特定の戦闘でしか働かない判断の変更は、6 seedの確認用集合では発動しないことが多い(v2・v3)。全判断に効く変更(v5)は差が出やすい。
- `lethal_direct`の決め打ちは、復活・召喚・致死局面のそれぞれで探索より悪い手を強制していた(OVICOPTER・FOGMOG戦で繰り返し死亡)。
- 報酬見送りの規則は記録どおりの役割を果たしていた。外すと重いパワー(Unmovable、Dark Embrace)を取りすぎて悪化した。


## 2026-10-11午後: THE_INSATIABLE戦と探索回数の検証（閉じた筋）

v2〜v7の117 runの死亡地点はTHE_INSATIABLE(Act 2ボス)が50件で最多。重複除去した60戦闘は勝ち18・負け42。

- 勝ち戦と負け戦の差は火力: 1ターン平均与ダメージの中央値43.6対23.3、突入HP80対67.5、ターン数7対7.5（`~/.sts2/analysis/insatiable_scan.md`）。
- 探索の評価値は突入直後から勝敗を当てている。勝ち戦は1〜2ターン目から正、負け戦はほぼ全ターン−0.6〜−1.0。戦闘中の打ち回しより、突入時のデッキで決まっている。
- 砂(Sandpit)の扱いに無駄は見当たらない。v5〜v8で脱出を打った砂の値は1が32回、2が145回で、3以上は探索が選んだもの。
- 最後のAct 2報酬で`BOSS_CARD_AXES`のINSATIABLE軸から強ブロックを外しても、312判断で変わるのは13件(9 seed)。変わる先は見送りかBattle Trance。レバーとして小さい。
- モデル実験(突入局面に1枚足して貪欲ロールアウト200回): 1枚の追加で勝率はほぼ±5pt以内。エネルギー+1は+30pt前後、全カード強化は+15pt前後、HP満タンは0〜6pt。ただし実際に勝った戦闘でも予測勝率0〜9%の例が多く、貪欲ロールアウトは実際の打ち手より弱い。小さい差を測る道具としては鈍い。古代の民のレリック選択は既に+1エネルギー系を最上位にしている。
- 探索回数: INSATIABLE戦の137判断で、100回探索の選択の損失(2000回探索を基準)は、Successive Halving(同じ100回)でも200回探索でも変わらなかった(差0.0005±0.003)。探索回数を増やす案は効果なし。
- v7対照AA6F8282C0の300秒打ち切りは、ターン12のend_turn後に次の観測が来ないまま起きた。Python側の判断時間は戦闘全体で約39秒。他のボス部屋は最長83秒。traceに時刻が無いため原因は特定できない。
- 決め打ち規則の監査(v5〜v8の規則による判断約1100件を、同じ局面の600回探索で評価): 規則の手と探索の最善手の評価差は平均0.08〜0.15で、探索自身の選択の損失(約0.015)より一桁大きかった。ただし`rage_direct`の大きな差の例(v6候補9629CB6A2E seq349: Rage(0)とVolley(X)のどちらを先に打つか)は、打つ順番が実質同じ手でも、先に打った手の後の貪欲ロールアウトの動きが変わるだけで差が出ていた。セットアップ系の規則(Rage、Frantic Escape、Inflameなど)について、この差は規則の良し悪しの証拠にならない。
- Rageの打ち順(`58758bd`、v9で比較): 実ゲームのRageはv2〜v8で観測した163枚すべてコスト0。`rage_defense_direct`はコスト1を前提に「受けるダメージがRageのブロックを超えるなら防御札を先に打つ」としていたため、Rageが攻撃の後ろに回った。発火した165ターンで、Rageより前に打った攻撃が95回、Rageを打たずに終えたターンが25回。防御優先の分岐をコスト1以上の場合に限った。
- `CARD.OMNISLICE`(無色、コスト0)は`official_agent.CARD_NAMES`にも`combat.py`にも無く、探索から見えない。v2〜v8では2 seed(EB97217329、1941B188DE)で手札に189行出て、33回は主に`rollout_disabled_no_playable_card`の後始末で打たれた。逆コンパイル(`Omnislice.OnPlay`): 対象に8(強化11)の通常攻撃。その最初の結果の`TotalDamage + OverkillDamage`(ブロックされた分も含む)を、対象以外の攻撃可能な敵全員へ`Unpowered`で与える。`ed42a7f`でモデル化した(2 runの監査で比較局面が26件増え、すべて一致)。
- AutoSlayの戦闘部屋の上限は`CombatRoomHandler.Timeout => TimeSpan.FromMinutes(5)`(ショップは120秒、宝箱30秒)。ModはHarmonyを使っているので、getterへのPostfixで延ばせる。ただしv7対照AA6F8282C0の打ち切りが長考なのか停止なのかは未確定で、延ばすとDLLのハッシュと評価条件が変わる。未着手。
- Duplicatorの後のガード(`33512fe`、判断の変更、比較は未実施): Primal Forceの再生でゲームが落ちる対策(`e67dbb1`)が、手札にPrimal Forceが無くてもそのターンの探索をすべて止めていた。v8候補6729739567のVANTOM戦seq117〜118では、Duplicatorの後のPerfected StrikeとStrikeを規則で打った(探索ならStone Armor)。v5〜v8で理由なしの`heuristic_fallback`は10件。手札にPrimal Forceがあるときだけ止める。
- 同じVANTOM戦は探索の評価値が最後まで正(ターン10で+0.62)のまま負けたが、HP減少はPlatingを含めすべて予告どおりで、未モデルの被弾ではない。最後のターンに防御札を1枚も引けなかった。
- Bloodlettingは手札に来た475ターン(v5〜v8、重複除去)のうち42ターンしか打たれていない(`~/.sts2/analysis/bloodletting_scan.md`)。勝ちが見えている道中戦では「HP3とエネルギー2」がモデル上ほぼ釣り合い(評価差0.05〜0.1)、打たない判断自体は誤りではない。一方、取得36回(報酬17、ショップ購入19)はすべてRuptureの無いデッキだった。Rupture+Bloodlettingの筋力エンジンを狙う方針(Act 3踏破2本の形)の結果だが、Ruptureが来ないと枠を使うだけになる。「Ruptureが無いうちはBloodlettingを取らない・買わない」は次の比較候補(未実施)。
- ゲーム再現の修正3件(v8の監査から): (1) `dc9c888` Spiteの「この手番にHPを失った」は`CombatHistoryEntry.HappenedThisTurn`(同じラウンド・同じ陣営)で、敵の手番の被弾は数えず、Crimson Mantle・Infernoのターン開始の自傷は数える。観測に無いのでエージェントがターン内のHP低下とターン開始の自傷を追跡する。combat.pyはターン開始の自傷の後でフラグを消していたのを直し、同じ箇所でターン終了に外したFlame Barrier等が自傷処理の後に戻っていたのも直した。(2) `c55b3b6` Vigorous(Stone of All Timeが付与、量8)は戦闘中の最初の1回だけ攻撃に8を足す。ブリッジは無効化後もエンチャント名を出すので、実際に打った手から使用済みを記録し、ターン1で消す。(3) `b97ddf8` 監査が、とどめの一撃を次の戦闘のターン1の観測と比べていた(combat_idが戦闘ごとに振り直されるため)。v8の監査はSpite 9件・Hemokinesis 7件・境界2件の不一致が消え、6148局面中6147一致。v5〜v7もStrike 3件が消えて5946局面中5945一致。
- `c4d41b4` Body Slamのダメージ(現在のブロック量)に、そのBody Slam自身で発動するRage等のAfterCardPlayedのブロックを含めていた(モデルはそれらをカード本体の解決前に加える)。v8 2A33BA8A51 seq380でゲーム5・モデル8。修正後、監査はv8が6148局面、v5〜v7が5945局面、v2〜v4が5987局面すべて一致。
- エンチャントとカードの伸び(全traceの監査から): `d3c59d9` Sharp(攻撃のたびに+量、Self Help Bookで2、Gnarled Hammerで3。名前しか出ないのでGnarled Hammerの有無で決める)、`2cb0811` Nimble(ブロック+2、53 runに出現。記録済みのプレイのブロックは修正前0/181件、修正後162/181件が一致)とSown(戦闘中の初回だけエネルギー+1、27 run)、`9d5a143` Thrash・Maulの伸びた基礎ダメージを手札の`base_value`から取り込む(v8 88141BFEC3 seq279でゲーム42・モデル18)。監査はHPしか比べないため、Nimbleのブロック差は監査に出ていなかった。エンチャントの一覧は逆コンパイルの`MegaCrit.Sts2.Core.Models.Enchantments/`にある。Souls Power(Exhaustを外す)は`0ab2058`で対応。Perfect Fit(山札の並び)、Goopy・Glam・Cloneは未対応。
- 監査にブロック量の比較を加えた(`7a069e8`、同じ手番の中のカード使用後)。これで見つかった再現誤り: Vambrace(戦闘で最初のカードブロックだけ2倍)の発動済みが観測に無く毎回2倍にしていた、Glam(戦闘中の初回だけ再生+1)、Unmovableの「その手番に打ったブロック札の枚数」も観測に無い、Rageは再生された攻撃でも1回ごとにブロックを得る、そして**防御札の強化量**(`33f2a2e`)。CARD_BLOCKの強化量は一部を除き一律+1だったが、逆コンパイルではIron Wave +2、Equilibrium +3、Impervious +10、Lift +5、Ultimate Defend +4、Flame Barrier +4、Finesse +3。強化した防御札のブロックを探索が過小評価していた。攻撃の強化量は逆コンパイルと一致していた(Uppercut・Peck・Sword Boomerangは回数やデバフの強化で別処理)。修正後の監査(ブロック込み)はv8が6619局面中6618、v2〜v4が6443局面すべて一致。v5〜v7に残るのはD55BC878ED対照のTUNNELER戦で攻撃のたびにブロックが1増える現象(原因未特定)など。
- `c359b78` Daughter of the Wind(攻撃を打つたびにUnpoweredのブロック1)が未対応だった(v5 D55BC878ED対照のTUNNELER戦)。修正後、v5〜v7の監査(ブロック込み)は6378局面中6376一致。
- 一回限りのエンチャント(Vigorous・Sown・Glam)の使用済みは「カードidとエンチャント」単位で記録している。同じエンチャントの同じカードが2枚あると、ゲームは1枚ずつ管理するが観測では区別できず、2枚目も使用済みとして扱う(v5 DCC93C65AA seq363: Glam付きTauntが2枚、2枚目の初回でゲームはブロック10、モデル5)。既知の限界。
- `Pael's Legion`(古代の民PAELの選択肢、v2〜v9の164 run中11 run)はクールダウン0のときカードのブロックを2倍にし、2ターンのクールダウンに入る。未対応だった(v9 6F6F2E036C seq254でゲーム14・モデル7)。クールダウンは観測に無いので、手札の防御札の`Block`表示が素の値(基礎+敏捷、Frailなら×0.75)の1.5倍以上なら発動可能とみなす(Unmovableの2倍も同じ表示に入るので倍率に含める)。
- `Stampede`の自動プレイは、組み直した手札でエネルギー不足のため`unplayable_this_turn`が付いた攻撃も打つ(コスト無し)。印のせいで打てていなかった(v9 364D012944 seq336、Bashが3枚目の攻撃でOrnamental Fanのブロック4も発動)。修正後、v9の監査は6647局面すべて一致。

## 2026-10-12: 探索を通らない直行規則の検証

各規則が実際に発動した局面（`data/astra_*` のtrace）から、次の2つの続きを比べた。どちらも、その後は探索（100回、残りHPの重み0.01）で戦闘を最後まで打つ。各局面2〜3回。

- 規則の手を打つ。
- 探索の最善手を打つ。

検証スクリプトはセッションのscratchpadにあった `rule_vs_search.py` と `focus_rule.py`（リポジトリには入っていない）。

| 規則 | 発動 | 手が違った局面 | 探索−規則 残りHP | 勝率差 | 処置 |
|---|---|---|---|---|---|
| `generic_multi_primary_focus_direct` | 272 | 64/90 | +2.3（SE 0.74、30対15） | +5.7pt | `29ceb7d` で探索が使えるときは使わない |
| `heuristic_fallback / rollout_rejected_unsafe` | 714 | 25/59 | −0.7（SE 0.46） | 0 | 現状維持 |
| `queen_minion_direct` | 355 | 17/20 | −0.7（SE 0.86） | 0 | 現状維持（QUEEN戦は31戦3勝で、両方とも負ける） |
| `rage_direct` | 250 | 43/50 | −2.0（SE 0.61、4対25） | 0 | 現状維持。Rageは探索より規則のほうが良い |
| `rage_defense_direct` | 310 | 19/25 | 0.0（SE 1.15） | +5pt | 現状維持 |
| `two_card_lethal_setup_direct` | 62 | 39/50 | +0.6（SE 0.51） | −2.6pt | 現状維持 |
| `rollout_success / decimillipede_focus`（探索の手の対象を最大HPの節へ付け替える） | 106 | 56/60 | +4.5（SE 1.06、29対9） | +3.6pt | `e99b22a` で外した |
| `rollout_success / obscura_focus`（探索の手の対象をObscura本体へ付け替える） | 51 | 49/50 | +3.6（SE 0.96、24対9） | +2.0pt | `e99b22a` で外した |
| `direct_potion` | 1100 | 12/31（モデル外ポーション29件は比較不能） | −0.2（SE 0.59） | −4.2pt | 現状維持 |
| `sandpit_draw` | 129 | 41/50 | +0.4（SE 0.50） | +3.7pt | 現状維持 |
| `vulnerable_multi_lethal_direct`（dsh実施） | 49 | 50組 | +1.25（SE 0.71） | — | 現状維持（2SE未満） |

- `sandpit_escape` は単発の判定しか見ておらず、複数枚の組み合わせで倒しきれるターンにも脱出を打っていた（5F213792B3 seq314: ボスHP54に対し、Bludgeon＋Anger 2枚で77出せた）。`e657cfb` で、手札とエナジーの最大ダメージ（ナップサック）がボスHPを超えるときは、脱出を後回しにした。全traceの脱出534件のうち、変わる判断はボスHP19〜61の局面だった。
- 点数の無いイベントは、ゲームの `EventRoomHandler` がランダムに選ぶ（v11とrandom20の481イベントのうち114件）。HPを払う分岐がある上位イベントに点数を付けた（`7c5526c`、`5955acf`）。

**同じseedの比較は、ごく小さな変化でも分岐する。** `ed1b3ee` で探索の残りHPの項を `scored_hp / 100` から `scored_hp * hp_weight`（既定0.01）に変えた。数学的には同じだが、浮動小数点では `57*0.01 = 0.5700000000000001`、`57/100 = 0.57` と一致しない。このため、ほぼ同点の手の順位が入れ替わった。DC167E87AE seq225では、局面（手札、デッキ18枚、レリック）がまったく同じなのに、対照はUppercut、v11とv12の候補はDefendを打ち、そこから先の展開が分かれた。`b6c1b07` で元の計算に戻した。v11とv12の候補はこの揺れを含んでいる。seedごとの改善と悪化には、変更の中身と無関係な分岐が混ざっていると考えること。

**AutoSlayは通算49階で打ち切る（実行環境の天井）。** `AutoSlayer.PlayRunAsync` は `while (runState.TotalFloor < 49)` で回る（`AutoSlayConfig.maxFloor = 49` は定数で、ループに埋め込まれている）。`TotalFloor` は `MapPointHistory` の合計。49階に達すると、`Run completed (max floor reached). Abandoning` で放棄する。

- Act 3を踏破した7本は、すべて17+16+15=48階だった。
- Act 2が18階のマップ（`[2, 18]` の到達点が出るseed）では、17+18=35階を使う。Act 3は14階までしか進めず、ボス（15階）に届かない。
- v14対照 8DF8EC394A は、Act 3 F13の戦闘にHP41で勝った直後に打ち切られた。放棄処理でもUIノードが見つからずエラーになり、incompleteになった。全runでこの打ち切りが出たのは、この1本だけ（ほとんどのrunは49階より前に死ぬ）。
- 対策案（未着手）: Harmonyのtranspilerで `PlayRunAsync` のstate machineにある定数49を引き上げる。DLLが変わるので、比較では両版を同じDLLにそろえる必要がある。

**倒れたときに持っていたポーション（2026-10-12）。** 負けた304戦のうち104戦はポーションを持ったまま倒れた。

- 最多はFOUL_POTION（27件）。戦闘中は自分を含む全員に12ダメージを与える。ただしショップ内で使うと、商人に投げて100ゴールドもらえる（`FoulPotion.OnUse` の `MerchantRoom` 分岐）。ShopBridgeにはショップでポーションを使う操作が無かった。`eace30e` で `use_foul_potion` を追加し、`choose_shop` は買い物より先にこれを選ぶようにした。DLLの再ビルドが要る。最初の版は、品物の画面を開いたままにしていたため発動しなかった（`FoulPotion.GetFoulPotionMerchantTarget` は `!inventory.IsOpen` を要求する）。`7177f39` で、投げる前に画面を閉じて後で開き直すようにした。実機確認: smoke2_foul FD7A9C8F5F seq167・168で2本を投げ、ゴールドが144→244→344に増え、その後ポーション・削除・カード2枚を買った。
- 攻撃ポーション（Fire 20、Potion-Shaped Rock 15、Explosive Ampoule 10）で、最後の戦闘の最後のターンに、唯一の主敵（HP＋ブロック）を倒しきれた局面は0件だった。攻撃ポーションを抱えて死ぬことは、取りこぼしの証拠にならない。

**ボス戦の勝敗の内訳（2026-10-12、全trace、seed＋入場HPで重複除去）。**

- VANTOM（Act 1ボス、HP173）: 213戦で183勝30敗（dshの集計 `.dsh/vantom_analysis.md`）。
  - 開始時のSlippery 8は、1ヒット1ダメージで削れる。Slippery中の与ダメージは、勝ちでも負けでも約8で同じだった。
  - 差はSlipperyが消えた後に出る。1ターンの与ダメージは、勝ち25.7、負け18.0。デッキの攻撃札は、勝ち8.8枚、負け7.8枚。
  - 負け戦はスキル札を多く使い（15.7対10.0）、エナジーを余らせて終えたターンも多い。デッキの火力不足で、打ち方の誤りという証拠は無い。
  - 局所検証（2026-10-12夜）: 探索がブロックの札を選び、攻撃も打てた局面を80選んだ（全traceで2640回）。比べられたのは71局面。
    - 実際のブロックの代わりに、最大ダメージの攻撃を打ち、その後は探索で最後まで打った。
    - 残りHPは攻撃のほうが平均2.5少なかった（SE 0.89、攻撃が良い17・ブロックが良い37）。勝率は同じ（80.3%）。
    - 探索は守りすぎていない。VANTOM戦の負けを減らすには、打ち方ではなくデッキの火力（報酬・購入）を見直す必要がある。
- QUEEN（Act 3ボス）: 61戦で3勝。
  - 勝った3戦の入場HPは平均96で、10.7ターン戦った。全戦でTorch Head Amalgamを6.7ターン目に倒している。
  - 負けた58戦の入場HPは平均73で、7.0ターンで倒れた。Amalgamを倒せたのは33戦だけ。
  - Amalgamを倒した時点のQUEENの残りHPは、勝ちでも負けでも約370でほぼ同じ。勝敗を分けたのは、その後の長い戦いを耐えるHPと火力。

## 2026-10-13: Act 2ボス突破のためのデッキ構築の検証

対象はrandom20とv12〜v20の全arm。Act 2ボス（全runでTHE_INSATIABLE）に入った147 run、勝52・負95。集計はdsh（`.dsh/act2_deckbuild.md`、`act2_confound.md`、`rest_audit.md`、`act2_hp_loss.md`、`act2_route.md`、`reward_replay.md`）。

- **入場HPが最大の要因。** 勝率は入場HP60未満で8%（3/39）、60〜79で36%、80以上で55%。
- **入場HP帯をそろえると消える差（原因ではない）。**
  - 店の利用（入店・除去・残りゴールド）と報酬の見送り回数。最初の集計で出ていた差は、勝ったrunがAct 3でした分を数えていたため。
  - 攻撃札の枚数。
  - 休憩所のHEAL/SMITHの回数。`choose_rest`はHPだけで決まる規則なので、HEALが多いのはAct 1で多く削られた結果。
  - 経路の戦闘数。最小経路より平均0.93戦多いが、そのうち0.65は?マスが戦闘になった分。分岐で遠回りした分は約0.28で、低HPモードの遠回りはHPが低い結果でもある。
- **帯をそろえても残る差。** 強化済みの札（80以上の帯で6.5対4.6）と、1ターンの与ダメージ（勝39〜48、負22〜26）。攻撃1回あたりのダメージは勝ち側が大きく（Strike 13.6対10.4）、Inflameを早く多く打っていた（1戦0.48対0.23）。
- **局所検証: 入場局面に札を1枚足して探索で最後まで打つ**（114局面×6回、探索30回、`scratchpad/boss_search_add.py`）。基準の勝率は26.9%。

  | 足した札 | 勝率の差 | SE |
  |---|---|---|
  | Demon Form | +5.6pt | 1.9 |
  | Inflame | +3.9pt | 1.4 |
  | Shrug It Off | −2.0pt | 1.4 |
  | Strike（薄まるだけの対照） | −1.9pt | 1.3 |

  強ブロックを1枚足しても、何もしない札を足したのと同じだけ下がる。筋力源は上がる。2026-10-11の貪欲ロールアウトでは差が見えなかった（`±5pt以内`）。探索で打ち切ると見えた。
- **報酬判断の再生**（記録2962件、変更なしでの一致99.6%。不一致はv17却下版の11件）。
  - `BOSS_CARD_AXES`のINSATIABLE軸にInflame・Demon Formを足しても、変わるのは8件だけ。軸はAct 2の報酬にしか効かない。Demon Formの格付けをC→Sにしても9件。
  - 見送り1004件のうち838件は、`strong_block_shortage`（16枚以上・強ブロック3枚未満）の見送りによるものだった。Act 1でも343件。
  - この見送りの全撤廃は過去2回不採用（2026-09-08 S段位の逃げ道、2026-10-11 比較v4）。v4の悪化は、軸外の重いパワー（Unmovable、Dark Embrace）を取ったことによる。
  - そこで例外に「S/A級の攻撃札」だけを加えた（`777a573`）。変わるのは219件で、すべて見送り→攻撃札（Headbutt 70、Pommel Strike 33、Uppercut 28、Fiend Fire 26、Anger 22など）。パワー札を取る件数は0。
  - これらの札は戦闘で63〜94%打たれている（`.dsh/g_cards_usage.md`）。
  - 比較v21の結果は保留（開発用Act 2 4対5、確認用Act 1 12対11）。mainから戻した。
  - 案Gで新しく取る札を、同じ114局面に1枚足した（探索プレイアウト）。Anger +5.8pt（SE 1.5）、Pommel Strike +3.4pt（1.3）、Uppercut +1.6pt（1.7）、Fiend Fire −0.9pt（1.6）、Headbutt −4.5pt（1.7）。
    - v21の悪化3組は、どれも候補がPommel Strikeを余分に取っていた。だがボス戦ではPommel Strikeはプラスで、その札が弱いことでは説明できない。最初の23局面では−3pt前後に見えたが、114局面でプラスに変わった。途中経過で札の良し悪しを読まないこと。
    - Headbuttは、捨て札から山札の上へ戻す1枚をモデルがランダムに選ぶ（実際はプレイヤーが選ぶ）。そのぶん過小評価される。Strikeとの差（−2.6pt、SE約2.3）は誤差の範囲。
- **局所検証: ボス直前の休憩はHEALかSMITHか**（同じ114局面×6回、探索30回、`scratchpad/boss_rest.py`）。強化先は `RestBridge.SmithCardSelector` の点数で選んだ。基準の勝率は26.9%。

  | 選択 | 勝率の差 | SE |
  |---|---|---|
  | HP+24（上限まで） | +4.2pt | 1.7 |
  | 1枚強化 | +1.5pt | 1.3 |
  | 2枚強化 | +2.5pt | 1.4 |
  | ブロック以外を1枚強化 | +0.9pt | 1.3 |

  入場HP帯別では、60未満でHP+24が+11.7pt（1枚強化は+2.8pt）。80以上ではHEALがほぼ上限で切られ、1枚強化が+4.4pt。これは現在の `choose_rest`（ボス前で負傷していればHEAL、回復の大半が上限で切られるときだけSMITH）と同じ向き。強化先をブロックから攻撃に変える利点も無い。休憩の規則は変えない。
- **比較v22（Shrug It Offの加点外し）も保留。** 開発用Act 2突破6対9、確認用4対2で割れた。
  - v21・v22の2回とも、報酬1回の違いから後の経路が全部変わった。そのため、記録済み判断の数%しか変えない報酬の変更は、28〜40組の比較では良し悪しを判定できない。
  - 局所検証の数字（札1枚で±2〜6pt）は、パネルの1 seed分の揺れより小さい。報酬の調整をパネルで測るなら、seed数を数倍にする必要がある。

## 2026-10-28: Act 2ボスを入場状態固定で測るラボ(BossLab)

実走の比較は1本の分岐が経路全体を変えるため、28〜40組ではカード1枚の良し悪しを判定できなかった(v21、v22)。そこで、Act 2ボス戦(THE_INSATIABLE)だけを、記録済みの入場状態(デッキ・HP・レリック・ポーション・run seed・歩いた階数)から実ゲームで繰り返すラボを作った。詳細は[BOSSLAB_20261028](BOSSLAB_20261028.md)、実装は`bosslab`ブランチ(`762ceb3`)にある。

- 1試行は約1.7分。フルrunでボス戦1回を得る時間(約6分)の約3.6分の1。実走の入場観測と、HP・レリック・ポーション・デッキ・敵の行動列が一致することを確認した。例外はEMBER_TEAの使い切りcounter(ラボだけ+2 Strengthが再発動)で、そのレリックを持つspecは除外した。
- Shrug It Offを1枚足す比較は、開発用(10 spec、A・B)と確認用(12 spec、E・F)の計176試行で、差を検出しなかった(合算で−8.7pt、p=0.18)。計画Aの−33pt(p=0.021)は計画Bで再現せず(+8pt)、同じbaseが55%から30%に動いた。再測定がなければ誤った結論に進むところだった。判定は保留。
- 実走で勝ったspecから選ぶと、baseの勝率が偏って見える(勝者の呪い)。逆に実走で負けたspecだけを選ぶと勝率が床に張り付いて(0/36)差が測れない。選定は結果を条件にしない。
- 実走の入場観測から-22.9ptと見えたShrug It Offの差は、ラボでは再現しなかった。交絡の説明と矛盾しない。ただしv22(報酬の加点外し)の判定は変わらず保留のまま。
- 検出力: 勝率の±10ptには1armあたり194〜355試行が要る。敵を削った割合(連続量)なら±0.10が約29組で足りるので、次はそれを主信号にする。

### 2026-10-28: 対照run蓄積v23(main、`775f366`)

新しいseed 58本を連続で走らせた(`data/run_ctrl_accum.sh`、manifestは`data/astra_ctrl_v23_*_manifest.json`)。完走58、未完了0。Act 1突破46(79%)、Act 2突破20(34.5%、95%区間24〜47%)、Act 3踏破0。敗北地点は、Act 2ボス15、Act 3ボス14、Act 1ボス11、その他18。Act 3ボスまで届いた14本は、いずれも突破できていない。以降の比較の対照に再利用できる(ソースとDLLのハッシュは、v22の対照と一致する)。

走行の落とし穴: ①ゲームを起動するにはSteamが起動している必要がある。②敗北後のゲーム終了コードは1が正常。③`pgrep -f`でゲームを探すと、コマンドラインに同じ文字列を含む別プロセスに誤反応する。④停止したrunを強制終了すると`mods/Sts2Ai`が残る(macOSでは`SlayTheSpire2.app/Contents/MacOS/mods`)。
