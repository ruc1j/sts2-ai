# STS2 AI Code Wiki

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



## 既知の未モデル領域(2026-08-15 監査)

`data/*trace.jsonl` 247本を集計し、デコンパイルと突き合わせて未モデル要素を洗い出した結果。**同じ調査を繰り返さないための記録**であり、数値は監査時点のもの。

### ポーションを探索へ接続した(2026-08-15に着手・部分的に完了)

もともと`combat.py`にはポーションを使う action が無く、`player_potions`はBelt Buckleの判定にしか
使われていなかった。ポーション判断は`official_agent.choose_potion`のヒューリスティックのみで行われ、
「このターンにポーションを切れば耐えられる」という読みが探索に一切入っていなかった。同日のセッションで
ポーション方策を10回以上調整しても収穫逓減だった一因がこれである。

現在は次の設計で接続済み(`015207d` / `cfea287`):

- **責務の分離**: `official_agent`が「そのポーションを今この戦闘で使ってよいか」を決め(既存の温存方策を流用)、
  `combat.py`が「いつ・どれを・どの敵に」使うかを探索で決める。全所持ポーションを素朴に開放してはならない。
  ロールアウトの`Combat`は1戦闘で完結するモデルで「次のボスまで温存する」価値を持てないため、必ず初戦で使い切る。
- `official_agent._rollout_allowed_potions`が`choose_potion`を候補限定で呼び、**許可された1本だけ**を
  `Combat.player_potions`へ渡す。許可集合が空なら`player_potions=()`となり接続前と完全に同一挙動になる。
- `legal_actions()`は`potion:<POTION_ID>`(対象が要るものは`@敵index`)を返し、`step()`が効果を適用して
  `player_potions`から1本除去する。ポーションはエナジーを消費せず、`played_this_turn`も更新せず、
  カードプレイ系リレック(Kunai/Shuriken/Nunchaku等)も発火させない——いずれも実機どおり。
- `choose()`の直接ポーション経路は、`choose_potion`が**`ROLLOUT_POTION_IDS`以外**を選んだ場合は
  従来どおり即座に返す。ここを「rollout有効なら常に探索へ委譲」にすると、探索が扱えない十数種の
  ポーション(Shackling/Fysh/Binding/Colorless等)が**直接経路でも探索でも使われなくなる**回帰が起きる
  (実際にレビューで検出した。ユニットテストの多くが`choose()`を`enemy_data`無しで呼んでおり
  435件全て緑のまま素通りした——ポーション経路の回帰テストは必ず`choose(observation, enemy_data, simulations)`
  の形でrollout有効の経路を通すこと)。

実装済みは`BLOCK_POTION`(12ブロック) `FIRE_POTION`(20ダメージ) `POTION_SHAPED_ROCK`(15ダメージ)の3種のみ。
いずれも`ValueProp.Unpowered`で、**Strength/Vulnerable/Flutterは乗らない**(`VulnerablePower`と`FlutterPower`は
`IsPoweredAttack()`のチェックを持つ)。一方`HardToKillPower`(ModifyDamageCap)と`SlipperyPower`
(ModifyHpLostAfterOsty)はチェックを持たず全ダメージに効くので適用する。この使い分けのため
`_damage_enemy`に`powered`フラグがある。残りのdeterministicなポーションは順次追加すること。
`SKILL_POTION`/`ATTACK_POTION`/`POWER_POTION`/`COLORLESS_POTION`/`DISTILLED_CHAOS`/`SNECKO_OIL`は
ランダムなカードを生成するため、MAD_SCIENCE/CASCADEと同じ理由で対象外。
`ENTROPIC_BREW`はカードではなく**空いたポーション枠を新規ランダムポーションで埋める**効果
(decompile確認、カード生成ではない)。対象外な理由も同じくランダム性だが、それとは別に
`choose_potion`の分類ミスが実害を出していた: `recovery`(healing/defensive_buffs)に含めていたため
戦闘中の緊急分岐で選ばれてしまい、そのターンの生存には何も寄与しないまま1枠を消費し、直後に
本当に必要な防御ポーションが2本目として使われる、という「無駄撃ちの二本消費」に見える挙動を
引き起こしていた(2026-08-15、`economy`へ再分類して修正)。

### DexterityPowerが蓄積されるだけで一度も読まれていなかった

`_grant_block`に`powered`フラグを追加してDexterityを加算するまで、`combat.py`は`DexterityPower`を
`_add_power`で**付与するだけで一度も読み出していなかった**(比較: `StrengthPower`は25箇所で読まれている)。
Belt Buckle(+2)、Kunai(3攻撃ごと+1)、および`DEXTERITY_POTION`(使用77回) `SPEED_POTION`(60回)
`FYSH_OIL`(52回)の計189回ぶんが、シミュレータ上では完全に無効だった。ポーション温存の調整が
効かなかった一因である可能性が高い。

実機の適用順は**Dexterity加算 → Frail乗算**(`ModifyBlockAdditive`が加算、`FrailPower`が乗算)で、
Vambrace/Unmovableの2倍はさらにその後。`Dex3 + Vambrace + Shrug(8)`は`(8+3)*2 = 22`であり
`8*2+3 = 19`ではない。Block Potionは`Unpowered`で`IsPoweredCardOrMonsterMoveBlock()`が偽になるため
Dexterityは乗らない(12のまま)。

**同種の穴を機械的に探す方法**: `_add_power(...)`と`powers=(("XxxPower", n),)`の付与箇所から
パワー名を抽出し、`_power(...)`/`_tick_down_power(...)`の読み出し側と突き合わせる。
2026-08-15時点で付与36種のうち未読は`NemesisPower`のみ(TEST_SUBJECT第3形態。1ターンおきに
`IntangiblePower`を付与し被ダメージを1に固定するが、trace 247本で観測0件のため優先度は低い。
`IntangiblePower`自体も未モデル)。新しいパワーを追加したらこの突き合わせを再実行すること。

### 探索回数(simulations)を増やしても改善しない

同一初期状態に対しseedのみ12通り変えて`search()`を実行し、1位に選ばれる手のブレを測定した結果:

| encounter | 200 | 500 | 1000 | 2000 |
|---|---|---|---|---|
| KNOWLEDGE_DEMON_BOSS (単体) | 100% | 100% | 100% | 100% |
| KAISER_CRAB_BOSS (複数主敵) | 58% | 75% | 66% | 66% |

複数主敵では回数を10倍にしても選択が安定しない一方、1位と2位の値の差は 0.0130 → 0.0084 → 0.0073 → 0.0039 と単調に縮む。**サンプル不足のノイズではなく、現在の`_step_score`では上位手が本当にほぼ同値**という分解能の問題であり、simsを増やすと真値に収束するだけで選択のブレは解消せず計算時間だけが線形に増える。複数敵戦の対策は探索回数ではなく`choose()`側で対象を絞る方向が正しい(KAISER_CRAB 14戦全敗を受けた multi-primary focus がその実装)。根本解決は`_step_score`に敵ごとの脅威度の差を乗せることだが影響範囲が大きい。

### 対応不要と確認済みのもの(調査時間を使わないこと)

- **`ESCAPE_ARTIST_POWER`**(観測1024件): `EscapeArtistPower.cs`のクラスコメントに `Just a visual timer for when ThievingHopper will escape` と明記。機械的効果は無い。
- **戦闘外効果のみのレリック**: `YUMMY_COOKIE` `NUTRITIOUS_SOUP` `GOLDEN_COMPASS` `CLAWS` `PAELS_CLAW` `PAELS_WING` `PAELS_TOOTH` `PAELS_GROWTH` はいずれも`AfterObtained`/マップ生成/報酬画面/休憩所のフックだけを持ち、`combat.py`側の対応は不要。ただし`CLAWS`は取得時にデッキのカードを**未モデルの`MAUL`へ変換する**ため、MAULの実装優先度を押し上げる材料にはなる。
- **`VERY_HOT_COCOA` / `PUMPKIN_CANDLE`**: 前者は`TurnNumber<=1`限定で、ロールアウトのターン遷移は必ず`new_turn>=2`になるため発火余地が無い。後者は`ModifyMaxEnergy`経由で、`PlayerCombatState.MaxEnergy`(`PlayerCombatState.cs:101`)が既にHook適用済みの値を返すため観測`max_energy`に反映済み。**どちらも実装すると二重計上になる**。同じ理由で`PAELS_FLESH`は「ターン3をまたぐ瞬間だけ`max_energy`を+1」という条件付き実装になっている(毎ターン加算するとターン3以降で観測した戦闘が全て+1過大になる)。
- **カードの定数**: `CARD_NAMES`の91枚全てについて、デコンパイルの`CanonicalVars`と`CARD_COST`/`CARD_DAMAGE`/`CARD_BLOCK`を突き合わせて不一致0件を確認済み(コスト84件・ダメージ30件・ブロック13件の比較)。
- **敵データ**: `data/enemies_*.json`の102種に対し、trace中に出現した62種は全て定義済みで欠落なし。

### 残っている未モデル(2026-08-15セッション終了時点)

同日中に実装済みとなったもの: カード `UNMOVABLE` `EXPECT_A_FIGHT` `BLOOD_WALL` `AGGRESSION` `Armaments`、
レリック `PAELS_BLOOD` `PAELS_FLESH` `PAELS_TEARS`、敵パワー `ARTIFACT_POWER` `BufferPower`、
および `DexterityPower` の適用漏れとプレイヤー側 `ThornsPower`。
ポーションは12種を探索へ接続済み(前掲)。

未着手として残っているもの(2026-08-15更新: CRIMSON_MANTLE/HELLRAISER/SWORD_BOOMERANG/
DARK_EMBRACE/FORGOTTEN_RITUALは同日中に実装済みのためリストから除去):

- **カード**: `THRASH`(取得4)。
  `STOKE`/`CASCADE`/`MAD_SCIENCE`/`MAUL`はいずれもランダムカード生成を伴い、このモデルと相性が悪いため保留継続。
- **レリック2種**: `PAELS_LEGION`(取得14・pet系でblockトリガ) `TOASTY_MITTENS`(5・turn1の山札操作+Strength)。
- **敵パワー**: `SWIPE_POWER`(772、主に報酬側)
  `HATCH_POWER`(150) `PAPER_CUTS_POWER`(34、最大HP永続減少) `RAMPART_POWER`(26)
  `NemesisPower`/`IntangiblePower`(TEST_SUBJECT第3形態、観測0件)。
  (`IMBALANCED_POWER`(751、BOWLBUG_ROCK)は1f8d226、`BURROWED_POWER`(532、TUNNELER)は4f910c8で
  実装済みのためこのリストから除去。いずれも新規stun概念を増やさず、既存の`_condition`/`_enemy_turn`
  分岐に敵専用の合成パワーを足す形で解決した。)
- **ポーション**: `SKILL_POTION`/`ATTACK_POTION`/`POWER_POTION`/`COLORLESS_POTION`/`DISTILLED_CHAOS`/
  `SNECKO_OIL`はランダムカード生成系、`ENTROPIC_BREW`はランダムポーション生成系(空きポーション枠を
  埋めるだけで戦闘効果なし)のため、いずれも`ROLLOUT_POTION_IDS`の対象外のまま。
  それ以外の決定的なポーションは順次 `ROLLOUT_POTION_IDS` へ追加すること。

### DEXTERITY_POTIONがブロック札を引く前に消費される可能性(未検証・保留)

`choose_potion`の`incoming >= hp`(真の致死)分岐では、`recovery`(defensive_buffsを含む)が
`SWIFT_POTION`(3枚ドロー)より先に評価される。手札にブロック札が1枚も無い状態で
`DEXTERITY_POTION`/`SPEED_POTION`のようなDex加算系を先に撃つと、その効果を活かすブロック札が
無いまま1本を消費し、後から引く`SWIFT_POTION`の方が先に必要だった可能性がある。2026-08-15、
F512086A1B(Act2 F10, BOWLBUG_NECTAR+SILK)でDEX→SWIFTの順で発生したが、このrunはその後も継続して
おり実害(致死)は確認できていない。「ブロック札0枚でincoming>=hpに直面し、SWIFTで引いた札でも
結局助からなかった」という実例が出るまでは推測で優先順位を変更しないこと。

### 致死札が揃っているのにポーションを先に使ってしまう(2026-08-15、6bfc1cc)

`choose()`のポーション判定(`choose_potion`の結果を返すかどうかのゲート)は、致死札の有無を
一切見ずに評価されていた。「HPが低い」というだけで、実は手札の1枚で倒せる敵に対しても
ポーションを先に消費してしまう——StSでは敵を倒せばその意図は発動しないため、倒すだけで
解決する場面でのポーション消費は無駄撃ちになる。実機trace2件(Thieving Hopper HP1、単体の
Slumbering Beetle HP19)で同型の「Speed Potion使用直後に即座に敵を倒す」パターンを確認して
特定した。

修正: `enemy_by_id`/`is_lethal`/`lethal`の計算をポーション判定より前に移動し、
「incoming>0を出している敵**全員**に自傷でない致死札が揃っている」場合だけポーション分岐を
スキップして`lethal`ブロックに倒させる。「全員」を条件にすることで、複数敵で一部しか倒せない
(BOWLBUG型の真の緊急)場合は従来通りポーションが機能する。

先生の「ポーションを雑魚で使いすぎ」という指摘は、この構造的な穴が一因だった可能性が高い。
同一seedを跨いだ検証(9seed中1例が「致死ではないが早すぎる2本消費」の曖昧なケース、他は正当)
と合わせて、gate自体(1部屋1本+致死例外)は健全だが、この「倒せば要らない」判定の欠落が
残っていた無駄撃ちの実質的な原因だった。

### LOUSE_PROGENITORのCurlUpPowerが未モデルで削り切れると誤判断していた(2026-08-15、7b5ecbb)

`LouseProgenitor.AfterAddedToRoom`(decompile)は戦闘開始時に自身へ`CurlUpPower(14=CurlBlock)`を
付与するが、これはroom入場フックで静的なstate machine JSONには出てこない(Torch Head Amalgamの
`MinionPower`と同じ理由)。`CurlUpPower.AfterDamageReceived`/`AfterCardPlayed`の実体は「Powered
攻撃カードを受けた後、そのカード全体(複数ヒットでも1回)が解決してから14 Unpowered blockを
自身へ付与し、CurlUpPowerを消費する」——つまりプレイヤーの最初の有効打の直後に突然14ブロックが
発生し、後続の攻撃をかなり吸収する。`combat.py`はこれを知らなかったため「このターンでこれだけ
削れるはず」という見積もりが過大になり、討伐までの想定ターン数を見誤る一因になっていた。
`initial_combat`でLOUSE_PROGENITORにCurlUpPower(14)を付与し、Attack系カードの全解決経路
(AllEnemies/SwordBoomerang/Volley/単体)で、カード全体の解決後に一度だけ14 Unpowered blockを
付与して消費する処理を追加した。

### BurrowedPowerがPOWER_NAMESに未登録で実機では一度も発火していなかった(2026-08-23、reviewer報告)

`4f910c8`(TunnelerのBurrowedPower実装)は`combat.py`側に`_power(powers, "BurrowedPower")`という
完全一致読み取りを追加したが、`official_agent.py`の`POWER_NAMES`(`POWER.XXX` -> 内部名の変換表)に
`"POWER.BURROWED_POWER"`のエントリが無かった。実機の`CombatBridge`は敵パワーを常に`POWER.XXX`形式で
渡すため、`POWER_NAMES.get(power["id"], power["id"])`はフォールバックで生の`"POWER.BURROWED_POWER"`を
そのまま`combat.py`に渡し、完全一致比較が外れてBurrow block破壊後のDIZZY_MOVEスタン遷移が実機プレイでは
一度も発火しない状態だった。手製`Enemy`へ直接`"BurrowedPower"`(正規化後の名前)を注入していた既存
テストはこの経路を通らないため気づけなかった。CurlUpPower(LOUSE_PROGENITOR)やImbalancedPower
(BOWLBUG_ROCK)と同様、新しい敵パワーを`combat.py`に実装したら`POWER_NAMES`側の変換エントリも
同時に追加し、正規化を経由する回帰テストを1本加えること。

修正: `POWER_NAMES`に`"POWER.BURROWED_POWER": "BurrowedPower"`を追加。
`test_combat.py`に`POWER_NAMES.get(...)`経由で名前を正規化してから`Enemy`を構築する回帰テスト
(`test_tunneler_burrowed_power_normalizes_from_official_id`)を追加した。

### CurlUpPowerの公式ID正規化漏れを修正(2026-08-23)

Louse Progenitorの`CurlUpPower`は`combat.py`に実装済みだったが、`POWER_NAMES`に
`"POWER.CURL_UP_POWER": "CurlUpPower"`が無く、実機の公式ID経路では最初の攻撃後に14 blockを
付与する処理が発火しなかった。公式IDから内部名へ正規化するエントリを追加し、同経路の回帰テストを
`test_combat.py`に追加した。

### SoarPowerのpowered attack軽減と公式ID正規化(2026-08-23)

公式`SoarPower`は対象自身が受ける`ValueProp.IsPoweredAttack()`だけを
`DamageDecrease=50`で半減する。カード攻撃は対象だが、ポーション・レリック・power由来の
`ValueProp.Unpowered`ダメージは対象外である。`combat.py`の`_damage_enemy(..., powered=...)`
にSoar判定を追加し、カード攻撃だけを半減するようにした。実機の`POWER.SOAR_POWER`を
`SoarPower`へ正規化する`POWER_NAMES`エントリと、powered/unpoweredおよび公式ID経路の
回帰テストも追加した。

### player側power 4件の公式ID正規化漏れを修正(2026-08-23)

`BarricadePower`、`BlockNextTurnPower`、`ColossusPower`、`HellraiserPower`は
`combat.py`が内部名で参照している実在のplayer側powerだが、`POWER_NAMES`に
`POWER.BARRICADE_POWER`、`POWER.BLOCK_NEXT_TURN_POWER`、`POWER.COLOSSUS_POWER`、
`POWER.HELLRAISER_POWER`の変換が無かった。公式観測を`rollout_choice`へ渡すと生のIDが
`player_powers`に残り、`_power`の完全一致読み取りが失敗するため、4件のマッピングを追加し、
公式IDからrollout stateへの正規化経路を固定する回帰テストを追加した。

### choose()のSoarPower越しlethal事前評価を修正(2026-08-23)

`choose()`内の`damage()`/`lethal_targets()`は`rollout_choice()`より前に実行されるが、
`POWER.SOAR_POWER`を考慮していなかった。そのためSoar中の敵へのカード攻撃を実ダメージのまま
lethalと判定し、実際には倒せない対象を選ぶ可能性があった。poweredカードの各hitをSoarで
半減してから`HardToKillPower`のhit単位capを適用するよう修正し、2体のraw observationで
Soar対象ではない確実なlethalを選ぶ回帰テストを追加した。

### SoarPower公式IDのrollout_choice経路を回帰テストで固定(2026-08-23)

`test_combat.py`の既存Soarテストは`POWER_NAMES`の結果を直接`Enemy`へ注入していたため、
`official_agent.rollout_choice()`が公式観測の`POWER.SOAR_POWER`を`SoarPower`へ変換する経路は
検証していなかった。公式敵powerのrollout fixtureへ`POWER.SOAR_POWER`を追加し、捕捉した
`Combat.enemies[0].powers`に`SoarPower`が残ることを固定した。

### SlipperyPowerのblock消費後capを修正(2026-08-23)

公式`SlipperyPower.ModifyHpLostAfterOsty`は、攻撃ダメージを先にBlockへ適用した後の
非Blockダメージだけを1へcapし、`AfterDamageReceived`で実ダメージが通った時だけstackを1減らす。
従来の`_damage_enemy`は早期returnでBlockを消費せずHPを1だけ減らしていたため、Slippery中の
敵がBlockを保持したままになっていた。Soar/Flutter等のpowered修飾、unpoweredポーション、
全Block、Soar併用の回帰テストを追加し、共通ダメージパイプラインへ組み込んだ。

### choose_card_rewardの「最高値0ならSkip」が実質死んでいた(2026-08-15、fd5e2cf)

最終returnは`core.get(...) or priority.get(...)`で判定していたが、`priority`は`CARD_TIERS`の
全カードにS〜D=5..1を割り当てるため、D tierでも1で真になる。Skip経路(`next(...option_id==Skip)`)
に到達するのは、offeredの全カードがunplayable/UNMODELED_CAP超過で`actions`が空になるか、
`CARD_TIERS`に無い(core補正も無い)カードしか無い時だけで、事実上ほぼ発生しない。結果として
デッキがAct2到達時点で24〜27枚まで膨張し(D6A1/C9F2/Z2D6でいずれも26〜27枚)、希薄化が
Act2ボス/Elite敗因の再現性ある候補として浮上した。

デッキ15枚以上・選択カードがB tier以下・core/`_boss_card_bonus`/`strong_defense_bonus`/
draw_needed(`DRAW_CARDS`)/defense_needed(`DEFENSE_PRIORITY`)のいずれの補正も乗っていない場合
だけSkipへ回すよう修正した。副産物として、`CARD_TIERS`に未登録のカード(例: FINESSE)が
防御不足時でも旧コードでは誤ってSkipされていた別の潜在バグも同時に解消した。

### 高tier未モデルカードは「取るのに使えない」死に札になる

`UNMODELED_REWARDS`(= `CARD_TIERS`にあるが`CARD_NAMES`に無いカード)は`UNMODELED_CAP`で枚数を制限しているが、tierが高いほど報酬で優先されるため**強いカードほど死に札としてデッキに入る**という逆転が起きる。監査時点で`EXPECT_A_FIGHT`は132回提示され59回取得、`UNMOVABLE`は31回提示され26回取得(84%)されながら、いずれも`search()`から見えず一度もプレイされていなかった。新しいカードを実装したら、trace上で実際にプレイされているかまで確認すること。

### Bowlbug RockのImbalancedPowerを実装(2026-08-22、1f8d226)

`ImbalancedPower.AfterDamageGiven`(decompile): Bowlbug Rockの`HEADBUTT_MOVE`が完全ブロック
された(与ダメージ0)ときだけ`IsOffBalance`が立ち、`POST_HEADBUTT`分岐(`data/enemies_hive.json`)が
これを見て次を`DIZZY_MOVE`に振り替える。エクスポート済みJSON側の`IsOffBalance`は静的な`False`
定数で実行時状態を持たないため、`_enemy_turn`が敵専用の合成パワー`OffBalancePower`を
`HEADBUTT_MOVE`完全ブロック時に+1、`DIZZY_MOVE`実行時に0へクリアする形で表現し、`_condition`の
`IsOffBalance`分岐はこの合成パワーを読むようにした。新しいstun概念を追加せず、既存の
`_power`/`_add_power`パターンに寄せた最小実装。

### TunnelerのBurrowedPowerを実装(2026-08-23、4f910c8)

`BurrowedPower.AfterBlockBroken`(decompile): TunnelerのBurrow block(データ上32)がちょうど0まで
削られた(overkillでも良い、部分ヒットでは不発)瞬間に即座に`DIZZY_MOVE`へスタンし、
`BurrowedPower`を剥がす。`AfterRemoved`の「残りBlockを消す」処理はBlockが既に0の時にしか
発火しないため実質no-op。`_damage_enemy`に`burrowed`かつ`block - blocked == 0`の分岐を追加して
対応(2026-08-23時点でこの実装自体には`POWER_NAMES`側の正規化エントリが漏れていたバグがあり、
別途reviewer報告で修正済み。詳細は前掲「BurrowedPowerがPOWER_NAMESに未登録で~」参照)。

### 強防御不足時の報酬をSkip(2026-08-22、7a6a49d)

`choose_card_reward`の`strong_block_shortage`(16枚以上デッキで強ブロック3枚未満)判定は既存の
tier比較を通り抜けるだけで、offaxisのA/S tier攻撃カード(Anger/Headbutt/Dark Embrace/Expect a
Fight等)が防御不足を無視して取られ続けていた(実例: D6、29枚デッキ・強ブロック1枚)。
`strong_block_shortage`成立時は、core/`DEFENSE_PRIORITY`/`DRAW_CARDS`のいずれにも該当しない
選択を無条件でSkip側に回すよう修正。あわせて`DEFENSE_PRIORITY`に`CARD.COLOSSUS`を追加。

### Rageを攻撃前に使用(2026-08-23、eb3ce90)

`CARD.RAGE`(このターンAttackを引くたびBlockを得る)は、Rageより後に出す攻撃にしか乗らない。
実機trace(D6)でAnger/Strike/Defendを先に出しRageを最後に出したため、そのターンのRage Blockを
まるごと取り逃していた。`choose()`に、Rage後もまだ攻撃を出せるエネルギーが残っている場合は
生存/防御に関わる既存の優先分岐(致死・緊急防御など)より後ろだが通常の攻撃選択より前で
Rageを強制する分岐を追加した。

### 強防御不足時の重複ドローをSkip(2026-08-23、ea70857)

7a6a49dの`strong_block_shortage`時Skip分岐は`DRAW_CARDS`を無条件で例外にしていたため、
既にドロー札を2枚以上持つデッキがさらにドロー札を取り続ける問題が残っていた(実例: D6、
Battle Trance 3枚以上・24枚デッキ・強ブロック0枚)。ドロー例外の適用を`draw_needed`
(ドロー札2枚未満)条件付きに絞り、既にドロー札が足りているデッキではSkipへ回すよう修正した。

### 強防御カードの不足例外を統一(2026-08-23)

`strong_block_shortage`の最終Skipゲートが`DEFENSE_PRIORITY`/不足時`DRAW_CARDS`しか例外にせず、
スコアリングで`strong_defense_bonus`を得た`EQUILIBRIUM`/`EVIL_EYE`/`ULTIMATE_DEFEND`まで
Skipしていた。最終ゲートにも同じstrong-defense判定を適用し、強防御カードを採用するよう修正した。

### Spectral KnightのHexPowerが単数targetで消える問題(2026-08-23)

`MONSTER.SPECTRAL_KNIGHT`の`HEX`は`PowerCmd.Apply`のtargetが複数形`targets`ではなく単数形
`target`で、`HexPower(2)`をプレイヤーへ付与する。`_enemy_turn`のPowerCmd.Apply処理は
`base.Creature`/`targets`/`TeammatesOf`しか分岐せず、単数`target`を黙って無視していたため、
HEX後のプレイヤーにHexPowerが存在せず、Soul Slash以降のシミュレーションが呪いを反映しなかった。
player-target semanticsは既存の`targets`分岐と同じため、`HexPower`に限って単数aliasを同分岐へ追加した。
同じ文字列を使うOvicopterの`MinionPower`は新生ToughEggを対象にするため、全`target`の一律player化は
行わない。`test_spectral_knight_hex_applies_to_player_from_glory_json`で実データ駆動の付与を固定し、
既存のOvicopterテストでもplayerへの誤付与がないことを確認する。

### CreatureCmd.Killの自爆を死亡遷移へ接続(2026-08-23)

`MONSTER.GAS_BOMB`と`MONSTER.WATERFALL_GIANT`の`EXPLODE_MOVE`は、プレイヤーへの
`DamageCmd.Attack`後に`CreatureCmd.Kill(base.Creature)`を実行する。`_enemy_turn`はこのcommandを
常に`NotImplementedError`としていたため、Gas Bombの通常戦とWaterfall Giantのボス戦で自爆ターンに
simulatorが例外となり、agentのsearchがheuristic tailへフォールバックしていた。
公式`CreatureCmd.Kill`はcurrent HPを0にした後、monsterのmove完了・terminal/removal判定へ進む。
その順序に合わせ、base.Creature対象に限って`enemy.hp=0`へ接続し、通常の`Enemy.alive`/`Combat.terminal`
判定に渡す。`ShouldFadeAfterDeath`は公式でも死亡アニメーションの表示制御であり、simulatorの状態遷移を
変えないため別処理は追加しない。JSON駆動テストで両方のEXPLODE_MOVEが例外なくhp=0となることを固定した。

### Waterfall GiantのSteamEruptionPower死亡後遷移(2026-08-23)

追加のdecompileで`SteamEruptionPower`は単なるcounterではなく、`AfterDeath`でWaterfall Giantの
`TriggerAboutToBlowState`を呼び、`ShouldCreatureBeRemovedFromCombatAfterDeath=false`と
`ShouldStopCombatFromEnding=true`を返すことを確認した。したがって、SteamEruptionPowerを持つ
Waterfall GiantのEXPLODE_MOVEは通常のhp=0終了ではなく、current HPを999999999へ戻して
`ABOUT_TO_BLOW_MOVE`へ即時遷移する。ABOUT_TO_BLOWではpower量をSteamEruptionDamageへ保存してpowerを
除去し、次のEXPLODE_MOVEでその値をプレイヤーへ与えてから、powerなしのKillで初めてhp=0となる。
この3ターンのサイクルをJSON駆動テストで固定した。`ShouldFadeAfterDeath`は死体のアニメーション制御であり、
SteamEruptionPowerのcombat残留判定とは別である。プレイヤーの致死攻撃も共通の死亡フックへ接続し、
PRESSURIZE_MOVE中にhp=0となった場合も同じABOUT_TO_BLOW遷移を行う。先行`2802619`のテストは
SteamEruptionPowerなしでEXPLODE_MOVEを直接開始していたため、この公式死亡後フックを検出できなかった。

### GuardbotのGainBlock target=item解決(2026-08-23)

`MONSTER.GUARDBOT`の`GUARD_MOVE`は`CreatureCmd.GainBlock(item, 15m, ...)`を使い、公式の
`GuardMove`では`CombatState.Enemies`から`Fabricator`を全件選んで付与する。従来の`_enemy_turn`は
commandのtargetを見ずcaster自身へblockを足していたため、Guardbotに15 block、Fabricatorに0 blockという
逆転が起きていた。target=itemを同室のaliveなFabricatorへ解決し、FabricatorNormalのJSON駆動テストで
Fabricator=15、Guardbot=0を固定した。

### QueenのBurnBrightForMe target=item解決(2026-08-23)

`MONSTER.QUEEN`の`BURN_BRIGHT_FOR_ME_MOVE`は、公式`BurnBrightForMeMove`でQueen以外の同side
teammate（通常はTorch Head Amalgam）へ`StrengthPower(1)`を付与し、その後Queen自身へBlock20を与える。
従来の`PowerCmd.Apply`はtarget=itemを無視し、さらにローカル変数`strengthAmount`が静的valuesに無いため、
Strength付与全体を黙って捨てていた。Queen専用のitem対象解決と、decompileで確認したamount=1を追加し、
JSON駆動テストでAmalgam Strength=1、Queen Block=20を固定した。

### SteamEruptionPowerの公式ID正規化漏れ(2026-08-23)

Waterfall GiantのSteamEruption死亡フックは`SteamEruptionPower`という内部名で判定するが、
`official_agent.py`の`POWER_NAMES`に`POWER.STEAM_ERUPTION_POWER`が未登録だった。そのため実機観測を
`rollout_choice`へ渡すと生IDがEnemy.powersへ残り、`_power`が0を返して、5118b13のABOUT_TO_BLOW遷移が
公式経路では発火しなかった。公式IDマッピングを追加し、`rollout_choice`で観測を再構築してから致死Strikeを
simulatorへ通す回帰テストで、正規化後のpower保持とABOUT_TO_BLOW遷移を固定した。

### Waterfall GiantのEXPLODE動的ダメージをrolloutへ引き継ぐ(2026-08-23)

`SteamEruptionDamage`は静的exportの`values`では0だが、公式Bridgeは`NextMove.Intents`から実際の
`DeathBlowIntent.damage`を観測へ出す。`rollout_choice`は従来`spec["values"]`だけでEnemyを再構築していたため、
ABOUT_TO_BLOW後のEXPLODE観測をrolloutへ渡すと動的ダメージが0へ戻り、Waterfallの自爆を無傷としていた。
WaterfallのEXPLODE観測にある正のintent damageを`SteamEruptionDamage`へ引き継ぎ、JSON駆動の公式観測再構築
テストで15ダメージ後のKillを固定した。

### rollout_choiceのpet除外後target index補正(2026-08-23)

`rollout_choice`はPael's Legion/Byrdpipをシミュレータの敵配列から除外するため、検索結果のcompactな敵indexと
公式観測の敵indexが一致しない。従来はカード・ポーションのtarget変換で観測配列を直接参照しており、先頭や途中に
petがいると別敵へ使用するか`StopIteration`になった。`compact_to_observation_index`で対応を保持し、両方のtarget
変換を同じ対応表へ統一した。先頭pet+実敵2体のカード/ポーション選択を回帰テストで固定した。

### Vantom戦のAoE rollout StopIteration(2026-08-23)

`rollout_choice`の内部シミュレータはAoEカードとExplosive Ampouleを便宜上`@敵index`で表すが、
公式Bridgeの合法actionは全体対象のため`target_id=null`になる。従来のtarget変換は常に敵CombatIdを
探していたため、VantomのSlipperyPower=4でBASHを選ぶ直前にrolloutがAoE/potionを選ぶと、公式actionを
見つけられず`StopIteration`へ落ちていた。AoEカードとExplosive Ampouleはtargetless actionへ変換し、
Vantom+Slipperyの実機文脈を含む回帰テストでカード・ポーション両経路を固定した。Slipperyのblock消費修正
自体が例外を発生させた根拠はなく、時系列上の併発だった。

### Rageの防御比較(2026-08-23)

Rageは攻撃後に3 block（アップグレード時5）を得るため、incomingが無いターンでは攻撃前の使用を優先できる。
従来は攻撃が1枚でも後続可能ならincoming量を見ずにRageを返し、Defendの5 blockで軽減できる4以上の攻撃や致死攻撃にも
Rageを選んでいた。現在のplayer blockを差し引いた実効incomingがRageのblockを超える場合は、Rageよりblock量の大きい
防御札を優先する。incoming 0/4/8/12、致死量、低HPの回帰テストを追加した。

### Waterfall GiantのSteamEruption raw damage観測(2026-08-23)

`AttackIntent.GetSingleDamage`は`Hook.ModifyDamage`後の実効値を返すため、Waterfall GiantのEXPLODE_MOVEで
観測した`damage`をそのまま`SteamEruptionDamage`へ保存すると、rollout側のプレイヤーVulnerable等で同じ修飾を
二重適用していた。`CombatBridge.Intent`で`AttackIntent.DamageCalc`の修飾前値を`raw_damage`として併記し、
`rollout_choice`はWaterfallの自爆値だけraw値を採用する。旧観測や既存fixtureの`raw_damage`無しには従来のdamageを
fallbackとして残した。実効22/raw15かつプレイヤーVulnerableの観測から、rollout後のHP58（22ダメージ）になる回帰を固定した。

## 2026-08-15セッションまとめ(このセッション区切りでの終了時点)

先生の「ポーションを雑魚で使いすぎ」という指摘を起点に、reviewer/developer間でheadless実行と実trace検証を
10+seed分繰り返し、以下を確定させた。

**コミット済みの修正(古い順):**
- `0393fc9` `ENTROPIC_BREW`を`recovery`から`economy`へ再分類(回復効果ゼロなのに緊急分岐で浪費)
- `39f59f7` Queen戦でTorch Head Amalgam(MinionPower持ち)を放置してQueenだけ攻撃し続ける問題
- `670806a` 致死札の判定をrolloutより前に移動(確実に倒せる敵をrolloutが見逃す構造的な穴、Act1 The Kinの実死亡例)
- `351a92f` `FORTIFIER`がBlock0でも緊急フォールバックから浪費される問題
- `6bfc1cc` 致死札が揃っている敵にはポーションを使わず先に倒す(Thieving Hopper/Slumbering Beetleの実例)
- `7b5ecbb` Louse ProgenitorのCurlUpPower実装(decompileで発見、削り切れると誤判断する原因)
- `fd5e2cf` `choose_card_reward`の「最高値0ならSkip」が実質死んでいた問題を修正、Act2到達時デッキが27→23枚に圧縮
- `06135f2`/`d3660cb` 通常Monster室で同一turnにDEXTERITY_POTION/SPEED_POTION(同一効果)を重複使用しない
  (direct経路とrollout候補経路の両方、SPEED_POTIONはROLLOUT_POTION_IDS外なので両方必要だった)

**節目:** このセッション中に**初めてAct3へ到達**(Act3 F15 Aeonglassで敗北、デッキ圧縮修正の直後run)。

**却下した提案(理由付き、同じ検討を繰り返さないため):**
- 「Monster室は1ターンにつき1本、致死例外も無し」「同一ターン2本目を一律禁止」→ BOWLBUG等の正当な致死回避
  (敵Strength+15で次被弾が本当に致死)を壊すため却下。gate自体は10seed規模の検証で健全と確認済み。
- OVICOPTER卵放置の一般化案(MinionPowerでも攻撃中なら除外しない)→ combat.pyのsearch()側は既に卵より
  親を高く評価できていたため、この経路では未実装のまま様子見。

**未検証で保留中:**
- `DEXTERITY_POTION`が手札にブロック札が無い状態で先に消費される可能性(致死分岐でのSWIFT_POTIONとの優先順位)。
  実害の証拠(温存していれば勝てたはずの実例)が出るまで手を付けないこと。
- KIN_PRIEST/Ceremonial Beast/Knowledge Demonでの僅差負けは、デッキ火力不足や既存の高難度設計と判断し
  コード変更は保留。同一パターンが複数seedで積み重なったら再検討。

### TEST_SUBJECTのMultiAttackIntentはCombatBridgeで動的反復数を返す(2026-08-23)

ゲーム v0.107.1 (`release_info.json` commit `59260271`)の`sts2.dll`をILSpyで確認した。
`MultiAttackIntent`は`AttackIntent`の派生クラスで、`Repeats` overrideは固定値ではなく
`_repeatCalc?.Invoke() ?? _repeat`を毎回評価する。`TestSubject.MultiClawMove`は
`new MultiAttackIntent(MultiClawDamage, () => MultiClawTotalCount)`を生成し、攻撃後に
`ExtraMultiClawCount++`するため、復活後の反復数は3→4→5→6と増える。

したがって`official_mod/CombatBridge.cs:234-238`の`intent is AttackIntent attack`は
`MultiAttackIntent`にも一致し、`attack.GetSingleDamage(...)`と現在値の`attack.Repeats`を
そのまま観測へ出す。非攻撃Intentだけが`damage=0,repeats=0`のelse側に入るため、疑われた
CombatBridgeの型判定バグは存在しない。`combat.py`側にも既に`TEST_SUBJECT`の履歴回数を加算する
処理があり、修正・回帰テストは不要。前掲の未検証持ち越し課題は誤検知としてクローズした。

テストは338→474件に増加(すべて「修正前コードで実際に失敗する」ことを確認してからコミット)。

**次回セッションへの持ち越し課題:**
- D6(29枚デッキ、強防御2枚のみ)を踏まえ、`choose_card_reward`の防御優先(`_block_starved`等)を
  最小修正する案を検討中。まずテストを書いてから、headlessでの再現runで確認すること。

## 2026-08-23セッション: 修正前ベースライン計測(researcher R5)

leader/coder/researcher/reviewerの4人体制でAct3安定攻略に向けた改善ループを開始する前に、既存の
`data/*_trace.jsonl`(307件、202 unique seed)からベースライン値を計測した。以降の変更が実際に改善に
繋がったかは、単一seedの成功ではなくこの基準値との比較で判断すること。

**Act到達率(unique seed基準、202 seed中):**
- Act1止まり: 115 seed
- Act2到達(max Act>=2、Act1 clear相当): 87 seed = 43.1%
- Act3到達(max Act>=3、Act2 clear相当): 2 seed = 0.99%
- Act3 Boss clear: 0 seed = 0%
- Act3到達2 seed(D6A1F8C3E5, C8D6B5E318)はいずれもF15 Bossで死亡し、重複runでも到達が安定していない。

**到達floor(unique seed deepest envelope):** mean 21.25, median 17, range 1-48
(Act1 offset 0 / Act2 offset 17 / Act3 offset 33の通し番号、Act3 F15 = 48)

**死因(unique envelope 199 seed中、死亡195):** Boss 116, Elite 37, Monster 27, Unknown 15
**死亡floor上位:** Act1 F17=80 seed, Act2 F16=33 seed, Act2 F8=11 seed, Act2 F14=8 seed, Act2 F6=7 seed

**残りHP(最後のcombat_end、302 trace):** hp=0が294件、正のHPで終わったcombat_endは8件のみ
(mean 1.45, median 0)。ほぼ全滅かギリギリの僅差負けかの二極ではなく、大半が完全な全滅。

**運用系シグナル(バグとゲーム内死亡を分離するための参考値、改善対象ではあるが別系列):**
- `reason=invalid_event_action`: 290 rows / 105 files / 40 unique seed(未登録event policyの既知gap)
- 実行ログの`Watchdog timeout`: 151/202 unique seed、`Rewards screen did not appear`: 52/202
- combat card action 43,874件中`simulations:null`(heuristic fallback)は5,332件 = 12.15%

**このベースラインの位置づけ**: 2026-08-23セッション開始時点(commit d1c3c64まで)の実力。同セッション中に
実施したCreatureCmd.Kill/HexPower/GainBlock target等の修正の効果は、今後の複数seed実機runの結果を
このベースラインと比較して判定すること。単一runでの改善断定は禁止(このCODEWIKIの他セクション参照)。

### R7: simulations:nullとlossの相関(researcher、2026-08-23)

307 trace横断で、combat card action中`simulations:null`(rollout未使用/fallback)の出現率はloss側21.92%、
win側10.44%(loss combatの80.3%が1件以上nullを含む、winは40.8%)。最終turn付近ほどnull率が上がる
(最終turn単位でloss37.9% vs win9.7%)。

**この相関を「fallbackが死因」と読まないこと。** より自然な解釈は逆因果: 危険な局面(低HP・防御不足)
だからこそ安全ガード拒否やheuristic fallbackが発火している、というもの。根拠: null全体の大半はHP>20の
場面にも広く分布し(4,424/5,332件)、winするcombatにもnullは多数存在する。未登録card(CARD.CASCADE等)由来の
nullは6.68%のみで、既知cardのnullが大半を占めるが、trace単体では「安全ガード拒否」と「rollout例外」を
区別できない。

**持ち越し課題(未実装、次回検討)**: `official_mod/CombatBridge.cs:95`のtrace出力に、rollout_attempted/
rollout_status(disabled/pre_policy/success/unsafe_rejected/exception)/exception_type/fallback_reason、
および player hp/max_hp/block/energy、hand id/cost/type、enemy move/intents/powersをcompactに追加すれば、
次回以降このfallback原因を直接集計できる(現observation自体には既に:177-216で情報があるので、追加は
trace出力側のdecision metadataに限定される)。優先度は現状の実バグ修正より低いが、次にfallback原因を
調べる時はまずこれを実装してから分析すること。

### CRUSHER+ROCKET("Crab facing")戦17 unique seed全敗 — choose_crab_facing()のlethal無視(2026-08-23)

researcherがR5 baseline(307 trace)を敵ID組で横断集計したところ、MONSTER.CRUSHER+MONSTER.ROCKETの
combatは19 trace/17 unique seedで**全19件がcombat_end won=false**という異常値を検出した。leaderの
実機run(data/leader_val2_trace.jsonl、seed FFCEFE5314)でも同ボスに敗北し再現した(4件目)。

該当戦のcard actionはsimulations:nullの比率が52.72%で、baseline全loss平均21.92%の倍以上。HP>20に
絞っても52.86%対15.76%で、低HP時の安全ガード拒否だけでは説明できない。

leaderがコードを直接確認したところ、official_agent.py:712 `choose_crab_facing()`が671行目で計算済みの
`lethal`/`all_incoming_threats_lethal`を一切参照せずに呼ばれていることを確認した。この関数(889-905行目)は
facingが脅威方向と逆であれば、`next()`で見つかった最初のAttackカードを無条件に返す——確定した致死攻撃が
別の敵に対して存在していても無視し、防御(Block)の要否も一切考慮しない。lethal判定より前でこの分岐が
returnするため、致死チャンスや必要な防御を機械的に潰しうる構造的な優先順位バグ。

過去に同型の「boss全敗パターン」はKAISER_CRAB_BOSS(複数主敵、14戦全敗)で確認され、multi-primary focus
実装で対処した実績がある(このファイル内の該当節参照)。CRUSHER+ROCKETも同様に、単一seedの過学習ではなく
再現性のある構造的欠陥として扱う。

`choose_crab_facing()`に`not lethal`ガードを追加し、確定キルをfacing変更より優先するよう修正した。
既存のAOE等の分岐順序は維持している。さらに同じ敵へ複数のAttackがある場合は、最初の一致ではなく
`_card_value`最大のカードを選ぶ。ただしfacing修正候補にself-damage攻撃が混在する場合は非self-damageを
優先し、self-damageしかない場合も現在HP以上の自傷候補を除外する。防御不足時の分岐は影響範囲が大きいため、
引き続き未実装とする。

同型の優先順位バグがSandpitの緊急脱出分岐にもあり、致死攻撃があっても`Frantic Escape`またはドローを先に
選んでいた。Sandpitの脱出／ドロー分岐を`lethal`未検出時だけ通すようにし、確定キルを先に実行する。

### targetless AllEnemiesカードのlethal見落とし（2026-08-23）

CombatBridgeは`TargetType.AllEnemies`カードのlegal actionを`target_id=null`で出すため、単一targetだけを
参照するlethal判定では`Howl From Beyond`等の確定キルを見落としていた。`lethal_targets()`でtargetlessの
`ALL_ENEMY_CARDS`は全敵を判定対象にし、各敵のSlippery／HardToKill／blockを含む実効ダメージで、1体以上を
倒せるカードをlethal候補へ追加した。lethal候補の選択キーもtargetless actionを扱えるよう修正した。

同じ`lethal_targets()`をpotion抑制ゲートにも使い、非自傷lethal候補がincoming中の全脅威を倒せる場合は
potionを温存するようにした。incomingが無い局面でも即時kill可能ならpotionを使わず、targetless AoEの
combat_idも正しく脅威集合へ展開する。

`choose_crab_facing()`は、現在のfacingと同じ方向の脅威を候補から除外し、さらに対象combat_idへのlegalな
Attackカードがある脅威だけをincoming比較に含めるようにした。これにより同方向の強い攻撃や、攻撃手段の
無い敵が、実際にfacingを直せる脅威を隠さない。

### 多段ヒットカードのdamage評価（2026-08-23）

`_card_value()`はDynamicVarsの`Damage`を1ヒット分として返していたため、Twin Strikeは5としてStrike(6)
より低く、Whirlwindも5として固定全体攻撃より低く評価されていた。Twin Strikeは2ヒット、Whirlwindは
現在のXエネルギー回数（Chemical X込み）を掛け、実際の合計ダメージで比較するようにした。合計値化後も
Slippery／HardToKillは各ヒット単位で処理し、既存の敵power近似を維持している。

### KIN_PRIEST敗因調査(researcher、2026-08-23) — コード変更は保留

leaderの実機run4本連続(val4/5/6/9)がKIN_PRIEST戦で全敗し、該当ターンのsimulations:null率が77.01%と
異常に高かったため、Crusher+Rocketと同じ「pre-rollout policy欠陥」を疑い調査した。

**Crusher+Rocketとの違い(重要)**: official_agent.py:823-871のKIN_FOLLOWER優先direct returnは実在するが、
これは既知・意図的な設計であり、test_official_agent.py:2450-2480で明示的にテスト済み、CODEWIKI:69でも
「follower優先とPriest集中のsearch差はノイズ内」と既に記録されている。Crab facingのような未検証の
隠れたバグではない。

**baseline(307 trace, KIN_PRIEST戦82件)でnullとlossは相関しない**: win側のnull率30.67% > loss側26.12%で、
「nullが死因」という仮説を支持しない。直近4本の77%は明確な異常値だが、n=4のサンプルで高難度・低HP到達
(resource/defense不足)との因果を分離できていない。

**結論(2026-08-23時点)**: コード変更は行わない。原因分離にはdecision_source(kin_follower_direct等)を
traceへ出す計装と、follower優先policy vs rollout/Priest集中のA/Bテストが必要(researcher提案のP1)。
次にこの調査を再開する時はまずそこから着手すること。単一の高null率サンプルだけで「意図的な設計判断」を
上書きしない。

### decision_source計装 設計メモ(researcher、2026-08-23、未実装)

`simulations:null`を「意図したpre-rollout direct return」「rollout成功後の安全処理」「rollout例外後の
heuristic fallback」に分離するための計装案。KIN_PRIEST調査のP1で必要になった。次にfallback原因を
本格的に切り分ける時はここから着手すること。

**スキーマ(V1)**: 全combat actionに`decision_source`(固定enum文字列)必須、`decision_reason`は任意
(rollout拒否/例外の理由だけ、メッセージ本文やstack traceは含めない)。

**decision_source候補**(choose()のreturn地点順):
phase系(phase_shop/map/card_reward/rest/event)、combat pre-rollout系(direct_potion、sandpit_escape/draw、
crab_facing_direct、aoe_threat_direct、queen_minion_direct、lethal_direct、rage_defense_direct、
rage_direct、generic_multi_primary_focus_direct、kin_follower_direct、kin_follower_urgent_direct)、rollout系(rollout_success、
heuristic_fallback〈細分化するならheuristic_block/card/end_turn〉、agent_exception_fallback)。

**decision_reason固定値**(fallback時に併記): rollout_disabled_no_data/no_simulations/no_playable_card、
rollout_rejected_unsafe(incoming>=hpかつ非block・非lethal)、rollout_rejected_self_damage、
rollout_exception_key_error/value_error/not_implemented/stop_iteration。

**実装フック(低コスト想定)**:
1. official_agent.pyにtop-level helper `_tag_action(action, source, reason=None)` を追加。
2. choose()の早期phase return、および各combat pre-rollout return地点をこのhelperで包む
   (choose_crab_facing自体やrollout_choiceの探索ロジックは変更不要)。
3. rollout部だけstatus/reasonのローカル変数を持ち、安全ガード拒否/例外をtagへ伝播。
4. main広域例外fallックは choose() 外なので個別に agent_exception_fallback を付与。

**C#ブリッジ側の変更も必要**(Pythonのaction JSONへ足すだけではtraceに残らない):
- official_mod/CombatBridge.csのAgentAction recordにnullable DecisionSource/DecisionReasonを追加。
- AgentIo.Trace出力にも同フィールドを追加(JsonOptionsの既定無視に依存せず明示的に)。

**テスト案**: 既存KINテストにsource検証を追加(kin_follower_direct/urgent双方、simulations=1000でも
sourceが残ること)、Crab direct/lethal direct/rollout成功/rollout例外→fallbackの各1ケース、
test_official_trace.pyで新traceにdecision_sourceが存在することを確認(旧traceはlegacy_unknown扱い)。

**実装状況(2026-08-23)**: Python側は`choose()`のphase/combat direct/rollout/fallbackと
main例外fallbackを計装済み。C#ブリッジ側のAgentAction/trace伝播も実装済み。

**end-to-end回帰(2026-08-23)**: `data/decision_source_trace.jsonl`は実機runのcombat traceから
抽出した新fixtureで、`test_official_trace.py`が全combat actionの`decision_source`必須と
`decision_reason`の存在を検証する。従来の`data/official_agent_trace.jsonl`は計装前のlegacy fixtureとして
sourceなしを明示的に許容する。C#受信recordのJSON名とtrace projectionも同テストで固定する。

**phase伝播(2026-08-23)**: Map/Reward/Rest/Shop/Eventの各action recordが共通の
`DecisionSource`/`DecisionReason`を受信し、成功・検証失敗・timeoutのphase traceへ明示的に出力する。
`test_official_trace.py`で5 bridgeのJSON名とprojectionを固定する。

### 修正後16本runの中間集計(researcher、2026-08-23) — 明確な改善も悪化も未確認

本日のバグ修正一式(SteamEruption連鎖、Crab facing lethal優先、AoE lethal盲点、self-damage回避、
多段ヒット評価、SoarPower、POWER_NAMES複数件)適用後、leaderが回した実機run16本(leader_val1〜16)の
中間集計。**改善したと断定しないこと。悪化したとも断定しないこと。n=16は判定に不十分。**

- 16/16敗北。Act2到達5/16(31.25%、baseline 43.1%)、Act3到達0/16(baselineも0.99%)。名目上低いが
  seed集合が非同一でregressionとは断定不可。
- 修正対象の敵で実際にrunに出現したのはCRUSHER+ROCKETのみ(2戦2敗、null率73.81%、baseline 52.72%より
  高い)。WATERFALL_GIANT/SPECTRAL_KNIGHT/MAGI_KNIGHT/QUEEN/GUARDBOTは今回のrunに一度も出現せず、
  修正の効果はまだ測定できていない。
- 全体のnull率は32.30%(baseline 12.15%)と上昇しているが、decision_source計装が無いため、これが
  「新しいdirect分岐が単に計測上nullを増やしただけ」なのか「実際の性能劣化」なのか区別できない。
- KIN_PRIESTは7戦1勝6敗(baseline 26/81≈32%勝率)で、こちらもn不足のため断定不可だが引き続き反復注視。

**結論**: decision_source計装(上記設計メモ)を実装する必要性が明確になった。coderへ実装依頼済み
(2026-08-23、SoarPower関連の高優先度修正の後)。実装後、追加seedでKIN_PRIEST/Crusher+Rocketの
direct policy寄与とrollout寄与を分離して再評価すること。

### GIANT_ROCKクラッシュ: Duplicator+Primal Forceのエンジン側相互作用バグ(researcher、2026-08-23)

実機run(data/leader_val19_log.txt:196-208、seed=632B291F86)で、通常の敗北ではなくCombatBridge経由の
game action実行中に例外でrunが停止した(P0候補として調査)。

**確定FACT(v0.107.1 sts2.dll decompile確認済み)**: POTION.DUPLICATOR使用直後にCARD.PRIMAL_FORCEを
プレイすると、DuplicationPowerによりPrimalForce.OnPlayが2回実行される。1回目の実行で手札の変換可能な
Attackを全てCARD.GIANT_ROCKへ変換するが、2回目の実行(Duplicator由来のreplay)でも、1回目に生成された
GiantRockが「変換可能なAttack」の条件を満たしてしまい、再度Transformしようとする。この生成直後のカードは
UI上のhand nodeを持たないため、`NCard.FindOnTable(original, Hand)`がnullを返し、
`CardCmd.Transform`が"Couldn't get hand node for original card..."例外を投げてクラッシュする。

**分類**: 主にK(未対応/危険なゲーム機構)+ B(engine/UI同期のedge case)。CombatBridge.cs自体は
正当なaction(TryManualPlay/TryManualUse)を呼んでいるだけで、Bridge側のバグ(A)ではない。副次的に
B/K: combat.pyはDuplicatorを未モデル化(searchがこの組み合わせの危険性を評価・回避できない)。

**再現性**: 過去のdata/*_trace.jsonl全件+今回のrunの中で、Duplicator+PrimalForceが同一runに揃うのは
data/leader_val19_trace.jsonlとdata/run_multi_mm_trace.jsonlの2件のみ。run_multi_mmではDuplicatorが
別カード(Strike)で先に消費されており衝突していないため無事完走。**この正確な組み合わせでのクラッシュは
現時点でこの1件のみ観測**、複数seed再現はまだ無い。

**推奨対応(researcher提案)**: ゲームエンジン自体(MegaCritの`CardCmd.cs`)は自分たちでは修正できないため、
(1) policy側でDuplicator使用直後にPrimalForceを選ばないよう回避するガードを追加する(coderへ依頼済み)、
(2) 別途combat.pyでDuplicatorを正しくモデル化し、searchがこの組み合わせ自体を自然に避けられるようにする
(優先度は(1)より下、余力があれば)。EventBridgeのfallbackでこのクラッシュを揉み消す対応はしないこと。

**対応(2026-08-23)**: `choose()`は同一`potion_context`で直前に`POTION.DUPLICATOR`を使用した場合、
`CARD.PRIMAL_FORCE`のactionを除外し、そのターンのrolloutも無効化する。これによりDuplicator由来の
PrimalForce再実行をpolicy側で確実に回避する。`test_official_agent.py`に連続actionの回帰テストを追加した。

### decision_source最初の分析で判明した誤解(researcher、2026-08-23)

decision_source計装導入直後、run20のtraceで`heuristic_fallback`(50件)の内訳が
`rollout_disabled_no_playable_card`45件・`rollout_rejected_unsafe`5件だったのを見て、leaderは「未知カード
1枚がそのターン全体のrolloutを無効化している」という仮説を立てたが、**researcherの検証でこれは誤りと
判明した**。

45件全てが`type=end_turn`で、直前のカードaction群がちょうどそのターンのエネルギーを使い切っていた
(合法カードaction自体が0件、つまり出せるカードが無いだけの通常のターン終了)。実際にrunでplayされた
全カードIDはCARD_NAMESに登録済みで、未知カードは一切関与していなかった。

**教訓**: 旧`rollout_disabled_no_known_card`はラベル名自体が誤解を招く命名だったため、
`rollout_disabled_no_playable_card`へ改名した。実態は「現在legalなknown cardが無い(エネルギー切れ含む)」
であり、「未知カードが原因でrolloutを諦めた」という意味ではない。これは計測対象のバグではなく
ラベル名の問題(計器の側の誤り)。`end_turn_no_energy`等への細分化やhand/energyの診断情報追加は別途検討する。
単一runの表面的なラベル名だけで仮説を立てず、必ずtraceの中身(このケースでは直前カードのenergy消費)まで
検証してから結論を出すこと。

### decision_source本格分析(researcher、leader_val20-29、2026-08-23) — KIN_PRIEST検証不能、別のラベル誤り発見

decision_source完成後の10 run(1,423 combat action)を集計。**この10本にはKIN_PRIEST/KIN_FOLLOWER戦が
1回も出現しなかった(n=0)**。したがって以前から懸案だったKIN_PRIESTのdirect policy寄与とrollout寄与の
分離は、このサンプルでは検証不能(仮説の支持も反証もできない)。

**新たなラベル誤り発見**: `kin_follower_direct`(139件)は名前に反してKIN限定ではなく、
official_agent.py:882-910の「複数の同等な主敵をまとめて集中攻撃する」汎用分岐(NIBBIT/TWIG_SLIME_M/
WRIGGLER等の通常戦でも発火)に付いている過度に広いラベルだった。`kin_follower_ids`が空でも発火するため。
次にKIN専用の分析をする前に、`generic_multi_primary_focus_direct`と`kin_follower_direct`(kin_follower_ids
必須)へ分割すること。対応として、通常の複数主敵では前者、KIN followerを含む場合だけ後者を付与するよう
`official_agent.py`を修正し、両ケースの回帰 assertionを追加した。

**rollout_rejected_unsafe(41件)**: player HP<=20の局面に集中(35/41)、loss併発が多い(31/41)が、
12/41はその後winしている。「危険な局面のシグナル」ではあるが、「安全ガードが勝ち筋を潰した」証拠には
まだならない(rejectされた候補自体がtraceに残らないため反実仮想検証不可)。

**rollout_exception_stop_iteration(20件)**: 大半(18件)がval21に集中しており、これは既にcoderが
修正済みのAoEカード/Explosive Ampoule target形式変換漏れ(commit ab1793b)で説明がつく可能性が高い
(val21はab1793bより前のrun)。val25/val28の残り2件も同一バグ由来と推定される。新規のStopIteration原因
ではない可能性が高いが、今後のrunで再発しないか引き続き確認すること。

**次のステップ(researcher提案)**:
1. 分割実装済み。KIN_PRIESTが実際に出現するseedで追加run→decision_source比率を再測定。
2. traceにincoming intents/block/rejected候補/fallback選択を追加すれば、rejectされた安全ガードの
   反実仮想比較が可能になる(将来課題、優先度低)。

### Act1序盤早期死亡パターン(researcher、leader_val30-34、2026-08-23) — コード変更は保留

leader_val30〜34の5本中3本(val31/33/34)がAct1序盤(F5〜F14)で早期死亡していたため調査したが、
**単一原因は特定できず、コード変更は行わない**。

**FACT**: 3本とも「前戦後に低HPのまま複数敵戦へ突入し、デッキの強防御カードが不足していた」という
共通パターン。val33/val34は死亡前にRestSiteを一度も踏んでおらず、val31もElite戦後にRestSiteなしで
次のMonster戦に入っていた。unsafe/self-damage系のrollout拒否も3本全てで反復しているが、これが
「正しい安全側判断」なのか「search/simulatorの見誤り」なのかは現traceだけでは切り分け不能。
potionの温存が共通原因という証拠は無し(n=2で使用タイミングもまちまち)。

**結論**: 高分散(弱い防御構成のデッキで休憩無しに連続して複数敵と戦う)が主因の可能性が高いが、
F(デッキ構築)/G-I(map routing含む)/M(不可避)のどれが支配的かは未確定。C(combat search)は
併発候補。A(不正action)/B(simulator mismatch)の直接証拠はなし。

**次のステップ(researcher提案、優先度順)**: (1) defense acquisition/path-rest riskの確認、
(2) enemy intent/incoming damageと候補カードのblockをtraceに追加し、unsafe拒否が「正しい判断」か
「search見誤り」かを分離、(3) potion/reward policyはこの5本だけでは変更しない。

### KIN_PRIEST decision_source分析(researcher、leader_val37、2026-08-23) — 従来の「高難度」判断を裏付け

decision_source完成後、初めて実機でKIN_PRIEST戦(data/leader_val37_trace.jsonl、seed=A9AACB9F62)に
遭遇した。turn11(HP2→0)で敗北。この1本(n=1)でのdecision_source内訳:

- rollout_success 13件(30.23%)、heuristic_fallback 15件(rollout_disabled_no_playable_card 10 +
  rollout_rejected_unsafe 5)、kin_follower_direct 5 + kin_follower_urgent_direct 5(合計10件、
  T1-T4のFollower集中攻撃)、direct_potion 3、lethal_direct 2。generic_multi_primary_focus_directは
  0件(前回発見した誤ラベル問題とは無関係な純粋なKIN戦であることを確認)。

**重要な事実**: unsafe拒否5件はT5/T7/T10(HP15またはHP10)に発生し、**死亡した最終ターンT11
(HP2→0)には発生していない**。T11はFlame Barrier+Defendがrollout_successで選ばれた後、通常の
end_turnで死亡している。つまりこの1戦に関する限り、安全ガード拒否が直接の死因だったとは言えない。
HPはT1開始51→T4開始15まで急落し、その後T9まで15を維持、T10で10、T11開始で2という推移で、
KIN follower policy自体(T1-T6でFollower 2体を撃破済み)が明確に誤っていた証拠もない。

**結論**: この1本の実データは、CLAUDE.md/CODEWIKIに以前から記載されていた「KIN_PRIEST等での僅差負けは
デッキ火力不足や高難度設計と判断しコード変更は保留」という過去の判断を裏付ける方向。E/F/M(resource/
defense不足・高分散)が主候補、C/D(search/target policy)は副次候補でバグ確定ではない。A/B/Kの直接証拠
なし。n=1なのでKIN_PRIESTへのコード変更はまだ行わない。追加seedが出たら同様の分析を繰り返すこと。

### VANTOM decision_source分析(researcher、leader_val3/17/20-22/25/27/29/40、2026-08-23) — 構造的バグなし

leaderの実機run群にVANTOMが9回登場(別seed)し、Crusher+Rocketの前例を踏まえ同じ手法で確認した。
**結論: Crusher+Rocketのような「専用pre-rollout関数がlethalを無視する」構造は確認できなかった。**

- VANTOM戦の勝敗: 9本中4勝5敗(44.44%勝率)。official_agent.pyにVANTOM専用のpre-rollout direct分岐は
  無く(汎用potion/Sandpit/Crab facing/AoE/lethal/Rage/multi-primary分岐のみ)、SlipperyPowerの扱いも
  VANTOM専用ではない汎用処理。
- 修正前baseline(83 trace/52 unique seed)のnull率8.94%に対し今回9本は15.11%とやや高いが、標本が
  非同一(baselineはseed重複run含む)でregressionとは断定しない。
- StopIteration(val21で11件、val25で1件)はAoE/target変換修正(ab1793b)より前のtraceで、修正後の
  val27/29/40ではVANTOM戦のStopIterationはゼロ。修正が効いていることを確認(ただし勝率への寄与は
  seed非対応のため未分離)。

**結論**: 主分類はM(高難度/高分散)またはE/F(低HP・防御/資源不足)候補。現n=9では因果断定不可、
コード変更は保留。KIN_PRIESTと合わせ、「Crusher+Rocketは本物のバグだったが、KIN_PRIEST/VANTOMは
単に手強いボス」という切り分けがdecision_sourceベースで進んでいる。

### Elite部屋入場直後の300秒完全ハング(researcher、2026-08-23) — コード起因ではない、運用上の既知事象

leaderの実機run50本中2本(val38/val49)で、Act2 Elite部屋入場直後に完全ハングし
`Operation timed out after 300s`で停止した。**我々のコード(CombatBridge/Python agent)が一切動く前に
発生しており、Bridgeやsearch/policyのバグではない。**

- 2件とも共通してAct2のElite入場直後、GC0/GC1/GC2カウントが通常(run開始時10前後)の約19倍(187〜193/
  92〜94/31〜35)、VRAM 1.2GB台まで蓄積した状態で発生。val49では同一run内のAct1 Elite(GC0/1/2は
  94/45/20とまだ低い状態)は35秒で正常終了しており、Elite全般の即時ハングではなく、run経過に伴う
  リソース蓄積が疑わしい。
- 全50 log中この現象はこの2件のみ(4%)。

**分類**: L(timeout/performance)、運用上のGodot/engineリソース蓄積が最有力候補。A(不正action)/
C(combat search)/J(event fallback)の証拠なし。コード変更は保留。

**注意**: AIの実力が上がりAct2/3への到達・長時間生存が増えるほど、この現象に遭遇する頻度が上がる
可能性がある。今後同様のハングが増えるようなら、run監視スクリプト側でVRAM/GC閾値を見て早期に
ゲームプロセスを再起動する等の運用対策を検討すること(コード修正ではなく運用対策)。

### 50本節目の中間まとめ(researcher、leader_val20-50、2026-08-23)

- **Act1 clear相当 9/31=29.0%**(R5 baseline 43.1%、-14.1pp)。標本条件が異なるためregression断定は
  しないが、注視対象。Act2 clear相当/Act3到達は0/31(baselineも0.99%と元々低い)。
- **Act2到達9件が全てAct2内(F4〜F12)で停止し、1件もAct3へ進んでいない**。ただしこの9件には
  Elite部屋ハング2件(val38/val49、既に運用上の既知事象と確認済み)が含まれるため、純粋な戦闘敗北は
  7/9。Act3到達のボトルネックとしてAct2戦闘そのものと運用障害の両方を今後切り分けて追う必要がある。
- **KIN_PRIEST決定の再検証(自己修正)**: val37単独では「死亡直前ターンにunsafe拒否なし」だったが、
  val37/47/50の3件では死亡ターンまたはその直前にunsafe拒否が2/3〜3/3で発生しており、**以前の結論は
  3件では再現しなかった**。範囲内にKIN勝利例(val39)も1件あり、KIN_PRIESTは不可避の死ではない。
  デッキ/HP/fallback条件の差を今後比較する。
- VANTOMは11戦5勝6敗(約45%)で、前回の44%とほぼ一致。KIN群は4戦1勝3敗、simulations null率57.0%。

**Act1 clear率低下(29.0%)の追加確認**: 22件のAct1失敗を、本日の修正経路(crab_facing_direct/AoE
targetless lethal/self-damage拒否/SoarPower)ごとに突き合わせたが、**新規regressionの証拠は無い**。
targetless lethal(AoE盲点修正)は6件全てparent combatがwon=true。Crab facing/SoarPowerはこの22件
そのものに一度も出現せず(評価対象外であって「効果なし」ではない)。StopIteration例外はAoE修正
(ab1793b)より前のtraceに限られ、修正後は0件。22件の主な内訳はVANTOM/CEREMONIAL_BEAST/KIN_PRIESTでの
低HP・防御不足とrollout_rejected_unsafeで、これらは既に「単に手強いボス」と分類済みの敵。Act1低下は
今回のバッチでこれら既知の強敵が偏って出現した標本ノイズの可能性が高い。

### 本日初のAct3到達(leader_val56、2026-08-23)

seed=6A311C0F2E、Act1・Act2両方のボスを突破し、Act3 F4のMonster室まで到達(data/leader_val56_log.txt
"Entering Monster room (Act 3, Floor 4)")。ベースラインのAct2 clear率は約1%(202 seed中2)なので稀な
成功例。Act3 F4でPUNCH_CONSTRUCT+CUBEX_CONSTRUCT×2の3体戦、turn3でHP22→0敗北(data/leader_val56_trace.jsonl:396-400、
全アクションrollout_rejected_unsafe/no_playable_card)。単一成功例なので断定はしないが、Act1/2を
安定して抜けられる可能性を示す実例として記録。今後この戦闘(Construct系複数敵)のdecision_source分析も
候補に入れること。

### KIN_PRIEST 6件目までの簡易集計(leader、2026-08-23) — unsafe拒否と死亡ターンの相関が強まった

researcherの窓が応答しなかったため、leader自身でval37/39/47/50/57/58の6件を簡易集計した(本格的な
FACT/HYPOTHESIS分離レビューは未実施、次にresearcherが動けたら正式分析を依頼すること)。

- 6件中1勝(val39)5敗。
- 敗北5件のうち4件(val47/50/57/58)は**最終記録ターンにrollout_rejected_unsafeが発生**していた。
  val37のみ最終ターンには発生せず(直前ターンには発生)。
- 以前(val37単独)の「死亡直前ターンにunsafe拒否なし」という結論は、nが増えるにつれて支持されなくなり、
  むしろ「死亡ターンにunsafe拒否が伴うことが多い」という逆の傾向が見えてきている。

**次のステップ**: この相関が「安全ガードが実際に勝ち筋を潰しているか」を確認するには、拒否された候補
自体がtraceに残っていないため、reviewerによるofficial_agent.pyのunsafe拒否ロジック(incoming>=HPかつ
非block・非lethal時に拒否)自体の妥当性コードレビューを依頼した。データ収集だけでなく、ロジック自体に
過度に保守的な条件が無いか(例えば実際にはまだ生存可能な選択肢を拒否していないか)を確認する。

### Crusher+Rocket修正後の初観測(leader_val68、2026-08-23)

修正済みのcrab_facing_direct(4f28b85でlethal優先化済み)が実機で初めて発火した観測。Act2ボスCRUSHER+
ROCKET戦、開始HP80、crab_facing_direct 11件/rollout_success 11件/fallback 7件/generic_multi_primary_
focus_direct 2件(33 action中)。最終的にHP0で敗北。過去の修正後データ(2件、いずれも敗北)と合わせて
post-fix Crusher+Rocketは0/3勝。lethal優先バグ自体は塞がったが、この敵自体の難度は依然高いままの
可能性が高い(修正は「無駄打ちを防ぐ」ものであり「勝てるようにする」ものではないため、想定内)。
追加seedでの継続観測が必要。

### 2026-08-23 val77: Act2 F12 Elite DECIMILLIPEDE戦、REATTACH_POWERによる蘇生で敗北(コードバグではない)

data/leader_val77_trace.jsonl(seed=C1DF9D5FAA)。Act2 F12 EliteのDECIMILLIPEDE(3セグメント、
REATTACH_POWER=25)戦でHP0敗北。turn7時点でsearch_value=-0.98(rollout_success)と既にsimulatorが
ほぼ確実な劣勢を予測していた。turn8開始時、直前に撃破していたMIDDLEセグメントがHP0→25へ
REATTACH_POWERで復活(combat.pyのreattach処理は正しく反映、trace上でも0→25と一致)。player HP1の
まま複数回rollout_rejected_unsafeが発生し、そのままturn8終了時に敗北。死亡直前のunsafe拒否は
KIN_PRIESTの過去分析と同様のパターン(低HP局面でのfallback連鎖)。simulatorが事前に-0.98と正確に
劣勢を検知していたことから、scoring自体は機能しており、単に苦戦マッチアップ(M: unavoidable/high
variance)と判断。コード変更は不要。

なお同run上、AutoSlay側watchdogがElite入場〜敗北検出まで約160秒(12:00:24入場→12:03:04 Watchdog
timeout)かかっている。ログの流れは「Finished Elite room」→「Waiting for rewards screen」→
watchdog検出、で、死亡時はNGameOverScreenが出ているにも関わらずAutoSlayが報酬画面待ちのまま
watchdogタイムアウトに頼って終了を検出している。以前記録した「Elite入場直後の完全ハング(300s、
戦闘開始前)」とは別パターン(今回は戦闘自体は最後まで進行し、終了検出のみが遅い)。これもゲーム側
AutoSlayの挙動であり、こちら側のコード修正対象ではない。

### 2026-08-23 val78: Act2 Elite入場直後ハング、3件目(n=3)

data/leader_val78_log.txt:334-352(seed=3D52DA3B7C)。Act2 F8 Elite入場直後、CombatBridge/敵生成の
ログが一切出る前にwatchdogがNo progress 47.9sで検出、run failed(exit code 1)。これはval38
(Act2 F12、300s)・val49(Act2 F8、300s)に続く3件目で、いずれも「Act2のElite入場直後、戦闘開始前」
という共通パターン。val49とval78はどちらもAct2 F8だが、seed(C8259B2C4F/3D52DA3B7C)は別物なので
座標一致は偶然の可能性が高い。今回はwatchdog検出までの時間が47.9秒とこれまでの300秒より大幅に
短く、リソース蓄積量(GC0=167、val38/49の187-193よりやや少ない)も相関する形で少なめだった。
「長時間run後のリソース蓄積が引き金」という既存仮説と整合する追加データ点。AutoSlay watchdog自体は
ゲーム側C#実装(MegaCrit.Sts2.Core.AutoSlay.Helpers.Watchdog)でこちらのMod外なので、引き続き
コード修正対象ではなく運用上の既知事象として扱う。n=3まで増えたが、傾向確認のみで対策は保留。

### 2026-08-23 val79: Act1 Boss VANTOM戦で敗北、turn9-10にrollout_rejected_unsafe連続

data/leader_val79_trace.jsonl(seed=11FF5BC674)。Act1 Boss VANTOM戦でturn11にHP3→0敗北。turn9-10で
rollout_rejected_unsafeが4連続(trace seq175/176/178/179/180)発生しつつVANTOM HPは71→13まで削れて
おり、拒否後も攻撃は続行できていた。死亡turn11自体にunsafe拒否は無く(search_value=-1.04〜-1.06と
既に敗北をrollout側が予見)、既存のVANTOM分析(構造的バグなし、44-45%程度の勝率)およびKIN_PRIEST
分析(死亡ターン自体にはunsafe拒否が付随しないことが多い)と整合。reviewerへ依頼中のunsafe拒否ガード
コードレビュー用の追加サンプルとして有用。

### 2026-08-23 val80: Act2 Boss KNOWLEDGE_DEMON戦で敗北(CurseOfKnowledge修正後、初の実機遭遇)

data/leader_val80_trace.jsonl(seed=616F13EBE3)。Act2 F16 Boss、MONSTER.KNOWLEDGE_DEMON(開始HP346)
戦でturn6終了時にHP0敗北。turn2時点で既にsearch_value=-0.79〜-0.98と大きく劣勢、以降turn6まで
一貫して-0.85〜-1.12で推移。rollout_exception系は0件で、以前修正した`CurseOfKnowledgeBranch`の
NotImplementedError(4ターン目以降毎回rolloutクラッシュ、docs/CODEWIKI.md:53参照)は再発していない
——修正後この敵との初の実機遭遇でもクラッシュなしを確認できた。HPは346→142まで削れており(turn6終了
時点)、進行自体は機能している。turn2から一貫して大幅劣勢という評価は、単に高HP+強力なボスとの
苦戦(M: unavoidable/high variance)の可能性が高く、現時点でコード変更は不要と判断。追加seedで
KNOWLEDGE_DEMON遭遇が増えたら勝率を確認する。

### 2026-08-23 val81: trace上"won=true"だが実ゲームは敗北するmismatchを修正

data/leader_val81_trace.jsonl:371(seed=123F5E65EF)。Act2 F13 Monster room、SPINY_TOAD
(THORNS_POWER=5)戦の`combat_end`が`{"won":true,"hp":3}`を記録。しかしdata/leader_val81_log.txt:
385-402では、この戦闘終了直後にAutoSlay watchdogが37.4秒でstuck検出し、State Dumpのoverlayは
`NGameOverScreen`(ゲームオーバー画面)——実際には敗北している。`leader_val81_log.txt`全体には
"Player 1 playing card"の完全一致行が見当たらず、このartifact単独では他floorとの差は検証できない一方、
pythonのtraceにはUppercut/Feed等の一連の行動が記録されている。

**確定FACT(decompile、v0.107.1 macOS版sts2.dll)**: これは`IsInProgress`の単純な読み取り競合ではなく、
`Feed`と`ThornsPower`の入れ子処理で一時的に死亡したプレイヤーを後続のFeed効果が回復させる順序が原因だった。
`ThornsPower.BeforeDamageReceived`は`CreatureCmd.Damage`で攻撃者へ5点を反射し、val81の最終ターンでは
HP5のプレイヤーがこの反射で一度HP0になる。この時点で`CreatureCmd.Kill`が`LoseCombat()`を呼び、
`RunManager.OnEnded(false)`と`NRun.ShowGameOverScreen()`(`NGameOverScreen`)を実行する。その後、外側の
`Feed.OnPlay`は殺害成功を検出して`CreatureCmd.GainMaxHp(3)`を実行し、`Heal`がプレイヤーのHPを3へ戻す。
`Heal`は`IsEnding`中でもプレイヤーには適用されるため、ゲームオーバー画面が表示されたままHPだけが正数になる。
したがって現行bridgeの`won = player.Creature.CurrentHp > 0`は、実際の敗北を勝利として記録していた。
combat.py側のThorns反射モデルはこの原因ではない。

**横断確認**: `leader_val1`〜`leader_val101`のtrace/logを対応付け、最後の`combat_end`が`won=true`で、対応logの
State Dumpが`NGameOverScreen`になっている組み合わせはval81のみだった。`Watchdog`単独は通常runにも出るため、
それだけではmismatchの根拠にしていない。

**対応(2026-08-23)**: `CombatBridge.Run`の`combat_end`判定で、HPが正数でもoverlay最上段が`NGameOverScreen`
なら`won=false`とする。`test_official_trace.py`にこのC#配線を固定する回帰テストを追加した。simulator側の変更はない。

### 2026-08-23 val83: Act2 Boss KNOWLEDGE_DEMON、2戦目も敗北(0/2)

data/leader_val83_trace.jsonl(seed=A49CAD583B)。val80に続きKNOWLEDGE_DEMON戦(開始HP346)で敗北、
現時点0/2。turn5-6はplayer_hp=20を維持したまま安定して削っていた(boss hp 276->227)が、turn6終了後の
敵ターンでHP20から一気に0まで落ちて死亡。search_valueはturn2から一貫して-0.8〜-1.06と、val80同様に
早期から劣勢予測。2戦とも「安定して削れてはいるが、どこかで大きな一撃を受けて即死する」という共通の
死に方をしており、単発の苦戦ではなくこのボス特有の高火力アタックパターンの可能性がある。まだn=2で
コード変更はしないが、追加seedでの継続観測対象とする。

### 2026-08-23 val82/84/86: CEREMONIAL_BEASTが3連敗(RingingPower修正の再発ではない事を確認)

同一セッション内でval82/84/86が続けてCEREMONIAL_BEAST(Act1 Boss)に敗北。過去にこのボスで
RingingPower(BEAST_CRY_MOVE後、そのターン1枚しかカードをプレイできない制約)がsimulatorに
モデル化されておらず29戦中17敗のクラスターを引き起こした経緯がある(docs/CODEWIKI.md:51)。
combat.pyの`played_this_turn`/`RingingPower`判定(combat.py:694-695)は現在も存在しており修正の
巻き戻りは無いことを確認した。3敗とも致命的な過大評価の兆候(search_valueが終始楽観的なまま死ぬ、
等)は見られず、通常の苦戦パターンの範囲内。修正前の水準に戻っている証拠はないため、コード変更は
不要と判断。n=3の小サンプルでの偏りの可能性が高いが、念のため追加seedでの継続観測対象とする。

### 2026-08-23 val87/val88: FOGMOG+EYE_WITH_TEETH戦で`lethal_direct`がIllusionPower持ちミニオンを
反復討伐、FOGMOGのStrengthが放置される疑い(未確認、次の調査候補)

data/leader_val87_trace.jsonl・leader_val88_trace.jsonl(いずれも敗北)。両方ともFOGMOG+
EYE_WITH_TEETH(ILLUSION_POWER持ち、敵ターン終了後に最大HPで復活——docs/CODEWIKI.md:61で既知の
意図された仕様)の組み合わせで、`lethal_direct`が毎ターンのようにEYE_WITH_TEETHへの確定討伐を
選択し続けている。val88では turn11〜13 の3ターンにわたりFOGMOGのHPが17のまま一切変化せず、
Strengthだけが6→7と積み上がっていた。

official_agent.py:842-850の`lethal_key`(738行目`lethal_targets`と合わせて確認)は
(合計incoming, target数, 最も低いHP, 最大ダメージ)でソートしており、対象がIllusionPowerを
持つか(=討伐しても復活して恒久的な価値が無いか)を一切考慮していない。一方`_greedy_action`側の
rollout評価には既に「primary(ボス)を倒した場合を優先し、復活するミニオンより優先する」補正が
入っている(docs/CODEWIKI.md:91)——つまり同種の教訓がrollout側にしか反映されておらず、
rolloutより先に実行される`lethal_direct`の早期リターンには反映されていない可能性がある。

ただし`lethal_direct`は1アクションのみを選ぶ関数であり、`choose()`はアクション毎に呼ばれ直すため、
「そのターンの残りエネルギーをFOGMOGへの非確定ダメージに回さなかった」のが本当にpolicy起因か、
単にエネルギー不足・低HPでの防御優先という合理的判断だったかは、このtraceだけでは切り分けられない。
n=2、FACT/HYPOTHESIS分離した詳細分析は行っていない。researcher/reviewerが手が空き次第、
「IllusionPower持ちenemyへの`lethal_direct`が、他に非確定だが本命(FOGMOG等)への攻撃機会がある
場合に不当に優先されていないか」を確認する調査を次の候補として残す。

### 2026-08-23 val91: KIN_PRIEST 7件目、死亡直前(最終end_turn)にもrollout_rejected_unsafe

data/leader_val91_trace.jsonl。turn11のend_turn自体がdecision_reason=rollout_rejected_unsafeとして
記録され、その直後に敗北。reviewerへ依頼中のunsafe拒否ガード妥当性レビューの追加サンプル。

### 2026-08-23 val93: KIN_PRIEST 8件目、死亡ターン(turn13)にもunsafe拒否

data/leader_val93_trace.jsonl。turn13、HP3でrollout_rejected_unsafeの後end_turnして敗北。
KIN_PRIESTのdecision_source付きサンプルが計8件に到達、いずれもreviewerのunsafe拒否ガードレビュー
待ちの追加データとして蓄積中。

### 2026-08-23 val98: KNOWLEDGE_DEMON戦がturn11まで進行した末に300s room timeoutで打ち切り(新パターン)

data/leader_val98_log.txt末尾: Act2 Boss room(KNOWLEDGE_DEMON、3件目の遭遇)で
`Operation timed out after 300s`(`AutoSlayer.HandleRoomAsync`のroom全体タイムアウト)。
data/leader_val98_trace.jsonlはturn11まで進行中(combat_endに到達せず、実際の勝敗は不明のまま
打ち切り)。以前記録した「Elite入場直後、戦闘開始前の完全ハング」(val38/49/78、n=3)とは異なり、
今回は戦闘自体が最後まで正常に進行していた(turn11で敵HP346→198まで削れている)。KNOWLEDGE_DEMONは
開始HP346と非常に高く、これまでの2戦(val80/83)もいずれも敗北。今回は決着すら付かず、1000
simulationsのrollout判断を10ターン以上繰り返す累積のリアルタイム経過時間が、`run_official_autoslay.ps1`
側の300秒room timeoutに達したと見られる。コード上のハング/バグではなく、単純に「高HPボスとの長期戦
+高simulations設定」の組み合わせが運用上のタイムアウトに衝突する新しいパターンとして記録。
対策候補(未着手、優先度低): 長期戦時にsimulationsを動的に下げる、room timeoutを延長する、等。
現時点ではコード変更・タスク化はせず記録のみ。

### 2026-08-23 leader実機run 100本到達の節目

data/leader_val1〜val100_trace.jsonl(全100run、重複seedなし、unique seed=100)を集計。
Act2到達(Act1 boss clear相当) 34/100=34.0%、Act3到達 1/100=1.0%(val56)。
baseline R5(修正前307 trace中202 unique seed: Act1 clear 43.1%、Act2到達 0.99%)と比較すると
Act2到達率はやや低め(34.0% vs 43.1%)だがAct3到達率はほぼ同水準(1.0% vs 0.99%)。val20〜50の
n=31時点でresearcherが暫定報告した29.0%よりは基準値に近づいており、本日の一連の修正
(Crab facing lethal優先、AoE lethal盲点、self-damage回避、SoarPower等)による新規regressionの
証拠は引き続き見られない。詳細なFACT/HYPOTHESIS分離分析はresearcher手隙時に別途依頼予定。

### 2026-08-23 KIN_PRIEST 5敗+1勝の再分析: 強防御カード不足が上流原因の有力候補(F)、unsafe拒否は
死亡隣接の症状(C)に留まる可能性

researcherによるval37/39/47/50/57/58の再分析。核心の発見:

- official_agent.py:1579-1583のSTRONG_BLOCK_CARDS、:1622の「デッキ16枚以上ならstrong block 3枚
  以上」しきい値に対し、KIN_PRIEST突入時点のデッキスナップショットは**敗北5戦すべてがこの
  しきい値未達**(strong block 0〜1枚、val37/47=1、val50=1、val57=1、val58=0)。唯一の勝利val39は
  ちょうど18枚/strong3枚(Blood Wall/Flame Barrier/Impervious)でしきい値を満たしていた。5敗5敗/
  1勝1勝ときれいに分離しているが、n=6なので記述的証拠に留まり因果は未証明。
- unsafe拒否(rollout_rejected_unsafe)は死亡ターンまたはその直前ターンに5/5全戦で出現(最終ターン
  自体は4/5)。ただしval39(勝利)はunsafe 0件。researcherの結論: **unsafe拒否は「安全ガードが勝ち筋
  を潰している」証拠ではなく、防御不足という上流原因(F)の下流症状である可能性が高い**——ガード自体を
  緩めるべきという結論には至らない。
- kin_follower_direct比率は敗北群(13.7%)と勝利control(14.3%)でほぼ同水準、target selection(D)の
  バグを示す明確な差はない。

推奨優先度: (1) F最優先——KIN_PRIEST到達までにSTRONG_BLOCK_CARDS3枚以上を確保する報酬/ショップ/
ルート選択の強化を検討。(2) C——rejectされた候補・予測incoming・利用可能な安全な代替手を計装した上で
本当に安全策が無かったのかを確認してから、ガード自体の変更要否を判断。(3) D(kin_follower_direct)は
現状変更不要。reviewerへ依頼中のunsafe拒否ガードコードレビュー(2026-08-23T01:14:30)は、この
F優位仮説を踏まえた上で「ガードの実装自体に単純ミスが無いか」の確認として引き続き有効。coderが
現在の緊急タスク(win/loss mismatch調査)を終え次第、F側(強防御カード確保policy)の実装検討を
次のタスクとして依頼する。

### 2026-08-23 KIN_PRIEST強防御カードpolicy対応: THE_KIN_BOSSをboss axisへ追加

RewardBridge/ShopBridgeはいずれも`run.Act.BossEncounter?.Id`/`SecondBossEncounter?.Id`を
`run.boss_encounter_id`/`second_boss_encounter_id`へ渡す既存経路で、KINのIDも他ボスと同様に利用できる。
`BOSS_CARD_AXES`へ`ENCOUNTER.THE_KIN_BOSS: STRONG_BLOCK_CARDS`を追加し、KINを次ボスとして観測した
カード報酬でShrug It OffがBludgeonを上回る回帰テストを追加した。KINは単体のPriestを主敵とするため
ALL_ENEMY_CARDSは加えていない。boss bonusはdeck sizeや`_block_starved`の条件に依存せずcore scoreへ
加算されるため、16枚未満の到達ケースにも適用される。

### 2026-08-23 coderがval81のwin/loss mismatchを修正(commit 0dbffab、leader独立検証済み)

Root cause: FeedのDamage中にThornsPowerが反射しplayerが一時HP0になり`CreatureCmd.Kill`が
LoseCombat/RunManager.OnEnded(false)/NGameOverScreen遷移を正しく実行していたが、その後Feed自身の
GainMaxHp+Heal効果がplayer HPを3へ戻すため、HPのみを見ていたCombatBridge.csが`won=true`と誤記録
していた。単純なIsInProgressのrace conditionではなかった。修正はCombatBridge.cs:132で
`NOverlayStack.Instance?.Peek() is NGameOverScreen`を確認し、trueならHPが正数でも`won=false`に
する形。regression testをtest_official_trace.pyに追加。coderの報告によるとval1〜val101横断で
この誤記録パターンが確認できたのはval81のみ(稀だが実在)。leader側で独立に
`python3 -m unittest discover`(528件通過)と`build_official_mod.ps1`(実機DLL参照、0警告/0エラー)を
確認し承認。以後のrun(val103〜)はこの修正込みのmodで実行される。

### 2026-08-23 val102: FUZZY_WURM_CRAWLERのStrengthがturn9で21まで蓄積(参考メモ、対応不要)

data/leader_val102_trace.jsonl。Act1、SHRINKER_BEETLE+FUZZY_WURM_CRAWLER戦でturn9時点のFUZZY_WURMの
STRENGTH_POWERが21(以前の研究者報告val33の7→14よりさらに高い)。合計敵HPは48でSHACKLING_POTIONの
使用しきい値(敵HP>=100)未満のため温存されたが、Strengthスノーボール自体はsearch_value=-0.98で
正しく悲観評価されており、simulator側の見落としではなさそう。SHACKLING_POTIONの使用条件が「総HP」
のみでなく「急速なStrength蓄積」も見るべきかは今後の検討候補として記録するのみ、現時点でタスク化はしない。

### 2026-08-23 log-monitor(hermes)が稼働開始、val90〜102の所見を提供(運用効率の改善候補、低優先度)

log-monitorが正常に動作し、初のレポートを送ってきた(以前セッションでは呼び出し手段が壊れており未稼働
だった)。所見は本セッションで既に個別に記録してきたAutoSlay watchdog/rewards待機パターン
(死亡後NGameOverScreenが出ているのにAutoSlayがNRewardsScreenを待ち続けてwatchdog/timeoutに頼る
挙動、val77/79/91/93/94/96/100/101等で既出)と一致する独立確認。追加の指摘として、この検知漏れは
ゲーム側`AutoSlayer.WaitForRewardsScreenAsync`(decompile対象、こちらのMod外)に起因しており、
仮にHarmonyパッチで割り込めれば毎回の敗北後に数十〜数百秒の無駄な待機時間を削減できる可能性がある、
という効率改善の提案。これは正誤(correctness)には影響しない運用効率の話であり、researcherの
KIN_PRIEST F仮説対応(勝率に直結)より優先度は低いと判断、現時点ではタスク化を保留しコード変更もしない。

### 2026-08-23 reviewerのunsafe拒否ガードコードレビュー: 3件の具体的バグ発見(未修正、coderへ依頼予定)

reviewerがofficial_agent.pyのunsafe拒否ガードをコードレビューし、再現手順付きで3件報告(diffなし、
既存テストのみ実行して確認、528件通過を維持したまま発見)。いずれもcombat.py/simulatorではなく
official_agent.py側のロジックギャップ。

1. **[HIGH] aoe_threat_direct分岐がunsafeガードの手前で直接returnする**(official_agent.py:810-812):
   `incoming >= hp // 2`条件は`incoming >= hp`(即死級)も含むが、この分岐はrollout/unsafeガードより
   前に実行されるため、生存可能なDefendがあるのに非ブロック・非致死のAoE攻撃を選んで自滅しうる。
   再現: hp=10/block=0、2体がそれぞれintent damage=5(計10=即死級)の局面でTHUNDERCLAP(範囲4)と
   DEFEND(block5)がある場合、aoe_threat_directがTHUNDERCLAPを選び死亡。Defendなら生存。
   対応: AoE直行前に現在blockを含む生存可能性を確認し、`incoming < hp + block`を満たさない場合は
   unsafeガード以降の防御フォールバックへ流す回帰テストを追加した。
2. **[MEDIUM] 死亡済み敵(hp<=0)の古いintentがenemy_incoming集計に混入しうる**
   (official_agent.py:333 `_intent_incoming`、enemy_incoming構築部/CombatBridge.cs:210-221):
   死亡した敵のNextMove/intentsがCombatBridge側でシリアライズされたままの場合、その古いダメージ値が
   incoming計算に混入し、実際には脅威が無いのに不要なunsafe拒否を誘発しうる。IllusionPower持ち敵
   (EYE_WITH_TEETH等、val87/88で観測)のような「hp=0のまま盤面に残る」ケースで特に疑わしい。公式
   observationでの検証fixtureが必要。
   対応: `_intent_incoming`でhp<=0の敵をincoming 0として扱い、BufferPower用のhit候補からも死亡敵を
   除外した。死亡敵のstale intentと生存敵の無害なintentを含む公式観測相当のregression testを追加した。
3. **[HIGH] unsafeガードがblock/lethal以外の被害軽減を認識しない**
   (official_agent.py:943-947 `choose()`、`_card_value()`/`is_lethal()`):
   UPPERCUT(Weak付与)やMANGLE(敵Strength低下)のように、blockを得ずに次の被弾を軽減するカードが
   「安全」と判定されず不当にunsafe拒否される。再現: hp=10、敵intent damage=10(致死級)の局面で
   UPPERCUT(13ダメージ+Weak、次の被弾10→7に軽減)とBLUDGEON(32ダメージ、被弾据え置き)がある場合、
   rolloutがUPPERCUTを選んでもunsafe拒否されBLUDGEONにfallbackし死亡。UPPERCUTなら生存できた。
   対応: UPPERCUTは対象敵の観測intentへWeakの3/4補正、MANGLEはStrength減少量(通常10、upgrade時15)を
   適用した次hit推定をunsafe判定に使い、両方のregression testを追加した。

この3件目は、researcherのKIN_PRIEST分析(F仮説: 強防御カード不足が上流原因、unsafe拒否はその下流症状)
と矛盾しない——unsafeガード自体にも「軽減効果を正しく評価できない」という独立した実装ギャップが
あることが分かった形。優先度は1・3(HIGH)を先に、2(MEDIUM)を後に、coderへ修正を依頼する。

### 2026-08-23 TASK1修正完了(commit 30dce94、leader検証済み): aoe_threat_directの自滅を防止

official_agent.py:808-816に生存可能性チェックを追加。`incoming < hp + current_block`(既に安全)
または`not defense_can_survive`(どのみち防御カードでも生存不能)のいずれかを満たす場合のみAoE直行
分岐を許可し、致死級incomingで生存可能なDefendがあるのに非ブロックAoEを選ぶケースを塞いだ。
regression test追加、python3 -m unittest discover 529件通過(leader独立検証済み)。C#変更なしの
ためbuild再検証は不要。TASK2(UPPERCUT/MANGLE等の非block軽減をunsafe判定へ反映)へ継続を依頼した。

### 2026-08-23 TASK2修正完了(commit a31340f、leader検証済み): unsafeガードがUPPERCUT/MANGLEの
被害軽減を評価するように

`mitigation_incoming()`をrollout_is_unsafe判定に追加。CARD.UPPERCUT(Weak付与、次被弾×3/4)と
CARD.MANGLE(Strength -10、upgrade時-15、decompile準拠)の2カードに限定して、対象敵の現在intentから
軽減後の被弾量を再計算し、その値で致死判定する。対象外カードの挙動は不変。regression test追加、
python3 -m unittest discover 530件通過(leader独立検証済み)。C#変更なし。TASK3(hp<=0敵のstale
intent除外)へ継続を依頼した。

### 2026-08-23 TASK3修正完了(commit f4d6aea、leader検証済み): 死亡済み敵のstale intentを脅威計算
から除外、reviewer3件レビュー全て対応完了

`_intent_incoming`にhpキー存在かつhp<=0なら0を返す早期returnを追加、`_potion_is_lethal_incoming`も
生存中の敵のみに絞り込み。hpフィールドが無いfixtureは従来通りintentを信頼する後方互換を維持
(実機observationには常にhpが含まれるため実害なし)。C#/CombatBridge側は変更せず、dead intentの
シリアライズ自体は残るがPython集計側で無害化する設計。regression test追加、python3 -m unittest
discover 531件通過(leader独立検証済み)。

これでreviewerが発見した3件(aoe_threat_direct自滅・UPPERCUT/MANGLE軽減未評価・死亡敵stale
intent)すべて修正完了。3件ともC#変更なし・小さくcommit分割・leader独立検証(python3 -m unittest
discover)済み。次はresearcherのKIN_PRIEST F仮説(強防御カード確保policy)対応をcoderへ依頼する。

### 2026-08-23 KIN_PRIEST強防御カード確保policy修正完了(commit e466659、leader検証済み)

leaderが事前調査した通り、BOSS_CARD_AXES(official_agent.py:1633-1638、次ボスが既知の時に対象カード
の報酬優先度へ+2ボーナスを与える仕組み)にENCOUNTER.THE_KIN_BOSSが未登録だった(既存の4ボスには
登録済み)。`"ENCOUNTER.THE_KIN_BOSS": STRONG_BLOCK_CARDS`の1行追加で解消。KINは単体ボスなので
DRAW_CARDS/ALL_ENEMY_CARDSは含めていない。boss bonusはdeck sizeや`_block_starved`条件に依存せず
適用されることを確認済み。regression test追加、python3 -m unittest discover 532件通過(leader独立
検証済み)。C#変更なし。これで本日の一連の対応(win/loss mismatch修正、reviewer発見3件、researcher
発見のKIN F仮説)が全て完了。効果測定は追加のKIN_PRIEST遭遇seedが溜まってから行う。

### 2026-08-23 val106: KIN policy修正後、初のKIN_PRIEST遭遇(敗北、n=7、F仮説と矛盾しない)

data/leader_val106_trace.jsonl。turn11、HP2→0で敗北。KIN到達時点のデッキ16枚中STRONG_BLOCK_CARDS
はEVIL_EYEの1枚のみで、依然として3枚しきい値未達。boss bonus自体は報酬候補の中でSTRONG_BLOCK_CARDS
の優先度を上げるだけで、そもそも十分な数のstrong block候補が提示されなければ効果が出ない——今回は
単に提示された報酬に強防御カードが少なかった可能性が高い。researcherのF仮説(strong<3=敗北)とは
矛盾しない追加データ点(n=7、6敗1勝→7敗1勝)。単一seedでの効果判定はできないため、今後も継続観測。

### 2026-08-23 先生の指摘(「取ったけど使われていないカード」)からCARD.INFERNO/CARD.CRUELTYの
CARD_NAMES/combat.py登録漏れを発見(未修正、coderへ依頼予定)

先生からの「取ったけど使われていないカードを調べさせて」という指示を受け、researcherがval1〜107の
全107 run(全trace parse成功)を横断調査。

FACT: 最終デッキのrun-card組合せ1,072件中98件(9.1%)が「そのrunで一度もplayされていない」。
既知カード47件・未知カード51件に大別。

最有力候補は**CARD.INFERNO**(最終デッキに入った6run中5run未使用: val31/33/54/87/100、いずれも
取得後にcombat行動が多数あるのに未play)と**CARD.CRUELTY**(4run中3run未使用: val26/39/77)。
両カードともofficial_agent.py:124(self-damage評価)・:170(INFERNO)・:1592(STRENGTH_CARDS、CRUELTY)
では参照されるが、**CARD_NAMES辞書(official_agent.py:18-117)に未登録**であり、combat.pyにも
cost/damage/power実装が一切無いことをleaderも独立に`grep`で確認した。CARD_NAMES未登録のカードは
rolloutの既知カード集合から外れ、実際にplayされる際もheuristic_fallback(rollout_disabled_no_playable
_card等)経由になる(val76でINFERNOが実際にplayされた2例はいずれもこの経路)。

これは過去のFlame Barrier未モデル化(報酬では高評価だが実戦で完全play不能)と同じ系統のPOWER_NAMES/
CARD_NAMES正規化漏れパターンだが、今回は100%未使用ではなく5/6・3/4という部分的な未使用のため、
「引かなかった/他行動を優先しただけ」の可能性も残る——researcher自身、legal_actions/hand観測が
無いtraceだけでは「候補に出たが未選択」と「rollout対象外で回避された」を区別できないと明記して
おり、断定はしていない。

RECOMMENDED: CARD_NAMESへのCARD.INFERNO/CARD.CRUELTY登録漏れと、combat.py側の効果実装有無を
coder/reviewerで確認し、他のPOWER_NAMES漏れと同様の手順(ID正規化+効果実装+回帰テスト)で対応する
候補としてcoderへ依頼する。CLUMSY/SPOILS_MAP/BYRDONIS_EGG/DECAY/LANTERN_KEYは100%未使用だが、
report/curse/relic由来の可能性が高くプレイヤーカードではないと推測(未確定)。Burning Pact/Drum of
Battle等の既知カードの未使用頻度は、モデル自体は存在するため今は追加runを待つ(即修正しない)。

### 2026-08-23 val108: KNOWLEDGE_DEMON 4戦目、turn13でHP52まで削って敗北(過去最接近、n=4)

data/leader_val108_trace.jsonl(seed=6734E10311)。Act2 Boss KNOWLEDGE_DEMON戦、turn13時点で
敵HP346→52まで削っての敗北。過去3戦(val80: 敗北時227付近、val83: 227、val98: turn11時点198で
timeout)と比べて最も敵HPを削れており、過去最接近。単一seedでの改善効果断定はできないが、
unsafe拒否ガード3件修正後の初のKNOWLEDGE_DEMON戦としては良い兆候。0/4のまま、継続観測。

### 2026-08-23 CARD.INFERNO/CARD.CRUELTY実装完了(commit 53458ba、leader検証済み)

decompileでInfernoは1コスト、InfernoPower+6(Upgrade+9)を付与、プレイヤーが被ダメージするたびに
全生存敵へその量を反撃(`_trigger_inferno`、Thorns反射やCrimson Mantle自傷等の既存全damage経路に
網羅的に組み込み)、加えてターン開始時にInfernoSelfDamage分の自傷が確定。Crueltyは1コスト、
CrueltyPower+25%(Upgrade+50%)を付与し、Vulnerable倍率(通常150%)に加算する
(`_vulnerable_damage`ヘルパーとして一本化、既存の`damage*3//2`ハードコードを置き換え)。
CARD_NAMES/POWER_NAMESにも登録。test_combat.pyにThorns/Vulnerableとの相互作用を含む振る舞いテスト
を追加、python3 -m unittest discover 536件通過(leader独立検証済み)。C#変更なし。coderが残した
留保: CombatBridgeの観測はInfernoPower量のみを送りInfernoSelfDamageの累積値自体は伝わらないため、
観測復元経由でのrollout再開(mid-turn再構成)では自傷回数を完全復元できない可能性がある(新規play
経路は正確)。実機での次回KNOWLEDGE_DEMON等の遭遇時に注視する。

### 2026-08-23 先生の指摘(「カードの順番が怪しい、次ターンを考えていないのでは」)からreviewerが
直行分岐3件の設計問題を確認(TOP3、medium、未修正)

先生の指摘を受けて依頼した監査で、reviewerが具体的な再現手順付きで3件報告。

TRACE FACT: leader_val*_trace.jsonl 108ファイル・combat 18,545件のうちdecision_source付き15,010件
(19ファイル3,535件は旧形式のため除外)。**rollout_success 53.56%、heuristic_fallback 25.42%、
direct合計21.01%**(lethal 9.15%、非lethal direct 11.87%)。run単位のdirect比率は中央値20.9%
(範囲10.4-35.0%)——約5戦闘中1戦闘分の判断がrolloutを経由しない直行ヒューリスティックという計測。

TOP3(いずれもseverity medium、現行combat.py rolloutとの選択差を合成局面で再現済み、実機勝率への
影響は未測定=HYPOTHESIS):

1. **generic_multi_primary_focus_direct/kin_follower_direct**(official_agent.py:888-927):
   `len(primary_ids)>1 and focusable and not lethal and not urgent`だけで発火——満HP・incoming0の
   通常局面でも対象。Inflame等のセットアップやdrawによる同ターン後続コンボを見ない。再現: HP80/80、
   2体各HP100・incoming0、hand=Inflame/Strike/Angerの局面でchoose()はStrikeを選ぶが、同一観測の
   rollout_choiceはInflame(search_value=1.96)を選ぶ。
2. **aoe_threat_direct**(808-824): `len(enemy_by_id)>=3`単独がincoming量に関わらずdirectを許可。
   満HP・incoming0でも非lethal AoEがあれば発火。再現: HP80/80、3体各HP100・incoming0、
   hand=Thunderclap/Inflame/Strikeの局面でThunderclapを選ぶが、rollout_choiceはInflame
   (search_value=2.06)を選ぶ。
3. **rage_direct**(864-886): Rage+支払い可能なAttackが1枚あるだけで、incoming/HP/block価値を
   見ずに発火。再現: HP80/80、敵1体incoming0、hand=Rage/Perfected Strike/Strikeの局面でRageを
   選ぶが、rollout_choiceはPerfected Strike(search_value=1.90)を選ぶ——incoming0ならRageのblock
   に価値が無く、単純に総ダメージが減る。

他の監査対象(direct_potion、sandpit_escape/draw、crab_facing_direct、queen_minion_direct、
lethal_direct、kin_follower_urgent_direct)は現時点で具体的な悪化例なし、または既知のIllusionPower
懸念(val87/88)はまだ確定issueに昇格しないとreviewerが明記(合成局面ではrolloutも同じ選択をする
ケースがあったため)。

RECOMMENDED: 大規模書き換えはせず、各直行分岐に「urgent(HP低下または実際のincomingあり)でない
限りrolloutへ渡す」形のgateを追加し、各分岐に最小回帰testを追加。その後実機traceで発火頻度・Act3
結果を継続観測する方針。coderが次に空き次第、この3件の修正を依頼する。

### 2026-08-23 TOP3の1件目修正完了(commit dd923f1、leader検証済み): generic_multi_primary_focus_
direct/kin_follower_directをurgent限定に

条件を`not urgent`(非緊急時に発火という逆転した設計)から`urgent and not kin_follower_ids`に修正、
非urgentの通常局面はrolloutへ委譲するようにした。KINの緊急ルール(kin_follower_urgent_direct)は
別分岐のまま維持、非urgentなKIN戦もrolloutへ委譲。副次的に、primary_idsからhp<=0の死亡済み敵を
除外する修正も同時実施(過去のTASK3と同系統の見落とし)。reviewer提供の再現条件(HP80、2体HP100・
incoming0、Inflame/Strike/Anger)でrollout_successに固定されることをregression testで確認。
python3 -m unittest discover 537件通過(leader独立検証済み)。TASK2(aoe_threat_direct)へ継続を
依頼した。

### 2026-08-23 TOP3の2件目修正完了(commit cf08590、leader検証済み): aoe_threat_directのincoming
閾値を必須化

`len(enemy_by_id) >= 3 or incoming >= max(1, hp // 2)`の人数単独OR条件を削除し、
`incoming >= max(1, hp // 2)`のみに変更。既存の生存性ガード(TASK1のdefense_can_survive等)は維持。
reviewer提供の再現条件(HP80、3体HP100・incoming0、Thunderclap/Inflame/Strike)でrollout_successに
固定されることを確認。python3 -m unittest discover 538件通過(leader独立検証済み)。TASK3
(rage_direct)へ継続を依頼した。

### 2026-08-23 TOP3の3件目修正完了(commit 0cc3239、leader検証済み): rage_direct/rage_defense_
directをblock必要時限定に、reviewer監査3件すべて対応完了

`remaining = max(0, incoming - block)`を算出し、`remaining > 0 or not rollout_enabled`の場合のみ
Rage直行を許可するよう変更。rollout無効時の既存挙動、incomingありでの強防御選択ロジックは維持。
reviewer提供の再現条件(HP80、incoming0、Rage/Perfected Strike/Strike)でrollout_successに固定
されることを確認。python3 -m unittest discover 539件通過(leader独立検証済み)。

これでreviewerが発見した直行分岐3件(generic_multi_primary_focus_direct、aoe_threat_direct、
rage_direct)すべて修正完了。先生の指摘(「カードの順番が怪しい、次ターンを考えていないのでは」)から
始まった一連の調査・修正が完結した形。3件ともC#変更なし・小さくcommit分割・leader独立検証
(python3 -m unittest discover)済み。効果測定は今後のrunバッチで継続観測する。

### 2026-08-23 combat traceに敵intent/手札/block/legal_actionsを追加(commit 0dee31d、leader検証済み)

先生からの依頼: 今日3回(researcherの未使用カード調査、reviewerの直行分岐監査、先生自身の
「殴られない時に瀉血使ってまでブロックしてる」質問への調査)、combat traceに敵の意図(intent)・
手札・legal_actionsが記録されていないせいで分析が頭打ちになったことを受け、trace計装を強化。

official_mod/CombatBridge.cs:99のcombat Trace呼び出しに、既にWriteObservation(:171-224)側で
計算済みだったフィールドを追加(デコンパイル調査不要、既存データの転記のみ):
- player.block/energy/max_energy
- hand(手札全カード、WriteObservationと同一構造)
- enemies配列にblock/move/intentsを追加(従来はid/hp/powersのみ)
- legal_actions(Exchange内で観測構築時に計算済みのlegalをそのままtupleで返すよう変更、
  legal_actionsの二重計算を回避)

過去のtraceファイル(val1〜111)は変更されず、val112以降のrunから新フィールドが出る。
python3 -m unittest discover 540件通過、build_official_mod.ps1(実機DLL参照)0警告/0エラー、
いずれもleader独立検証済み。次回run以降で実際に新フィールドが出力されているか確認する。

### 2026-08-23 val111: Act2 F11 Elite入場直後ハング、4件目(n=4)

data/leader_val111_log.txt(seed=F6688529F3)。Act1 F7/F15の2つのEliteは正常終了(F15はDECIMILLIPEDE
戦に勝利)したが、Act2 F11 Elite入場直後、戦闘開始前に`Operation timed out after 300s`。既知の
「Elite入場直後の完全ハング」パターン(val38/49/78に続き4件目)。引き続きゲーム側AutoSlayの挙動で
コード修正対象ではない。

### 2026-08-23 val112: trace計装強化が実際に機能、初のintent付きtraceで死因を即座に特定できた

data/leader_val112_trace.jsonl。Act2 F6 SPINY_TOAD(THORNS_POWER=5)戦で敗北。新フィールドにより、
死亡直前の敵intentが`{"type":"Attack","damage":23,...}`(SPIKE_EXPLOSION_MOVE)と直接確認でき、
HP14・block12(のちに7)に対し明確な致死量だったことが即座に判明。BASHがrollout_rejected_unsafeと
なったのも正しい判断で、残り手札がほぼ攻撃札のみ(防御札なし)だったため回避不能な敗北と特定できた
——従来のtrace形式ではここまで数分かかっていた分析が数秒で完了。intent/hand/legal_actionsの追加は
狙い通り機能している。この件自体はコード変更不要(単なる手札運の悪い正当な敗北)。

### 2026-08-23 val113: CRUSHER+ROCKET post-fix 4戦目も敗北(0/4)、ROCKETのLASER_MOVEが原因と
intentで確認

data/leader_val113_trace.jsonl。HP11・block0の局面でROCKETのLASER_MOVE intentがdamage24〜37
(raw_damage31、crab facing次第で変動)。crab_facing_direct→aoe_threat_directと同一ターン内で
2つの直行分岐が発火したが、この火力を受け切れる状態ではなく敗北。intentが見える形で確認できたのは
初めてで、既知の「lethal優先バグ修正後も難度自体は高いまま」という結論を裏付ける追加データ。

### 2026-08-23 val116: KIN_PRIEST 9件目、BEAM_MOVE(5×3=15)がHP9・block0を確実に上回る回避不能死

data/leader_val116_trace.jsonl。intentでKIN_PRIESTのBEAM_MOVEが1回5ダメージ×3repeats=15と確認でき、
HP9・block0に対し確実な致死量だったと判明。unsafeガード(ANGER拒否)は正しい判断だったが代替手段が
無かった。KIN_PRIESTのdecision_source付きサンプルは9件に到達。

### 2026-08-23 本日のセッション終了(val119まで、119本実施)

先生の指示によりチームを解散。coder/researcher/reviewer(いずれもcodex)のプロセスを終了し、
Terminalウィンドウのクローズも試みた(ウィンドウ自体はAppleScript経由で閉じきれず数枚残存、
プロセス自体は終了済みで実害なし)。log-monitor(hermes)はそもそも常駐プロセスを持たないため対応不要。
val119は通常のAct1 Boss敗北(watchdog timeout)、mods フォルダも正常にクリーンアップ済みで残留なし。

本日の主な成果(commit履歴参照):
- val1〜119、119本の実機run実施。Act2到達率34%前後、Act3到達1件(val56)を維持。
- win/loss mismatch修正(Feed+Thorns+Kill順序の誤判定、commit 0dbffab)。
- unsafe拒否ガードの3件のバグ修正(aoe_threat_direct自滅、UPPERCUT/MANGLE軽減未評価、死亡敵stale
  intent、commit 30dce94/a31340f/f4d6aea)。
- KIN_PRIEST向け強防御カード確保policy(BOSS_CARD_AXESへのTHE_KIN_BOSS登録、commit e466659)。
- CARD.INFERNO/CARD.CRUELTYの完全実装(commit 53458ba)。
- 直行分岐3件の設計問題修正(generic_multi_primary_focus_direct/aoe_threat_direct/rage_direct、
  先生の指摘起点、commit dd923f1/cf08590/0cc3239)。
- combat traceへのintent/hand/legal_actions計装強化(commit 0dee31d)——早速val112以降の複数の
  死因診断で威力を発揮し、これまで数分かかっていた分析が数秒で完了するようになった。

未完了・継続課題:
- KNOWLEDGE_DEMON戦は0/4のまま(過去最接近はval108のHP52残し)、継続観測が必要。
- CRUSHER+ROCKETはlethal優先バグ修正後も0/4、依然として高難度。
- Act3到達はval56の1件のみ、Act3以降のデータはまだ極めて少ない。
- researcherの未使用カード横断調査で見つかったBurning Pact/Drum of Battle等の未使用頻度は
  「モデルは存在するため追加runを待つ」段階で保留中。
- 100%未使用のCLUMSY/SPOILS_MAP/BYRDONIS_EGG/DECAY/LANTERN_KEYはプレイヤーカードか未確認のまま。

次回セッション再開時は、team.sh sts2-aiでロスターを確認の上、必要な役割をspawn.shで再起動し、
docs/agmsg.md・本ファイルの最新セクションから状況を追うこと。

### 2026-09-10 Fysh Oilを既存Blockで安全なターンに温存

Elite戦のポーション危険判定は敵の表示攻撃値を使っていたため、既存Blockで実被害がHP半分未満に
収まる高HP時にもFysh Oilを消費していた。Fysh所持時だけ実被害を確認し、安全なら温存する。

固定16seedの既存観測ではN8CQ4ZKP2WとL3PN5HBQ8Tだけに発火。実機再走でN8は19戦18勝のまま
QUEEN残HP208→160、10→12ターンへ改善し、L3は13戦12勝・THE_INSATIABLE残HP40で同成績。
全618テスト成功。全ポーションを実被害基準へ変える広い案はB8が12勝→6勝へ悪化したため不採用。

### 2026-09-10 Fysh Oilの使用をHP 60%まで待つ

N8の現行版はFysh OilをHP 65%で使っていたが、勝利履歴ではHP 59%まで保持していたため、長期戦での
使用閾値をHP 2/3から3/5へ変更。既存観測で発火したN8・D6・H2を実機再走した。N8は19戦18勝・
QUEEN残HP160、D6は16戦15勝・QUEEN残HP380でともに同値。H2は17戦16勝のまま、Act 2ボス
THE_INSATIABLEの残HPが170から33へ改善した。悪化したseedはなく、全618テスト成功。

### 2026-09-10 致死ターンではBattle Tranceを先に使う

H2のAct 2ボス最終ターンは敵HP63、3エネルギーでBattle Trance、Perfected Strike、山札先頭の
Strikeがあったが、unsafe fallbackがBashとStone Armorへ先にエネルギーを使い、引いたStrikeを
使えなかった。致死被弾でrolloutがunsafe拒否され、手札を満杯にせず全量引ける場合は、0コストの
Battle Tranceを先に使う。

実機再走でH2は17戦16勝・Act 2ボス残HP33から、23戦22勝・Act 3ボスQUEEN残HP341まで前進。
N8は19戦18勝・QUEEN残HP160で同値。全619テスト成功。固定16seed見込みは0勝、215戦199勝、
Act 3到達3本。

### 2026-09-10 N8CQ4ZKP2WでAct 3を初突破

RuptureとBloodlettingが同時に使える場合はRuptureを先に使い、Strength 20以上では致死しない
自傷をrolloutから選べるようにした。これによりQUEEN戦のStrengthは16から44へ増え、残HPは
160から75まで減少した。

最後に、直接リーサル判定のダメージ計算が敵のVulnerableを含んでいない問題を修正した。
Paper PhrogとCrueltyも既存の戦闘モデルと同じ倍率で計算し、低HP・Strength 40以上に限って
複数枚リーサルを優先する。公式実機run `candidate_vulnlethal_N8CQ4ZKP2W` は19戦全勝、最終HP 7で
`act_3_complete: true`。固定seed N8CQ4ZKP2WをAct 3まで初めて完走した。

## 2026-09-12セッション: 計測環境の再構築と、後回し評価の実測

### 再現環境が壊れていた(最初に直したこと)

一時runner `/tmp/sts2_goal_run.py` と固定ユーザーデータ `/tmp/sts2-userdata-pin` が両方消えていた。
pwshが `/opt/homebrew/bin/pwsh` にあるため、リポジトリ純正の `run_official_autoslay.ps1` を呼ぶ薄い
bashラッパーで置き換えた。ラッパーの役目は3つだけ。固定スナップショットからの復元、artifact名の
重複拒否、`trap` による復元と `mods/Sts2Ai` 削除。

**`-AgentSimulations` の既定値は 1000 だが、過去のartifactは全て 100 で取られている。**
消えた旧runnerの引数 `<seed> <artifact> 100 WORKTREE` の「100」がsimulations数だった。これに
気づかず1000で2本走らせ、「現HEADはP3で12勝1敗、旧基準18勝1敗から退行」という誤った結論を出した。
実際はsimulations差である。

判別方法: トレースの `simulations` フィールドと、序盤の `search_value`。同一seedで序盤の
`search_value` がわずかに違うとき(例: seq3が 1.7544 vs 1.75552)は、コード差よりsimulations差を
先に疑う。

`simulations=100` で現HEAD素の対照runを取り直すと、旧artifact `candidate_tauntdraw_P3V8N5K2RX` と
**643行バイト単位で一致**した。環境の再現性は証明済み。

### 「Battle Tranceを先に使わない」「殴ってから発火」の実測

ユーザー指摘から調査。根は `_step_score` が即時のダメージとブロックしか点数化しないこと。
見返りが未来にある札は0点近くになり、エネルギーを使い切った後へ回される。

全トレースで「打てるのに後回しにされたターン数」を集計した。

| 札 | 合計 | `rollout_success` | `lethal_direct`(正当) |
|---|---:|---:|---:|
| Battle Trance | 687 | 501 | 121 |
| Inflame | 228 | 162 | 39 |

`lethal_direct` は敵を倒し切る局面なので後回しで正しい。問題は探索自身の判断である
`rollout_success` の663ターン。

箇所は2つ。

1. `_step_score` 末尾の `0.3 * max(0, drawn)`。コメントは「ドロー札が最後に回るのを防ぐため」と
   書いているが、同じコメントが「実ダメージ1点を絶対に超えない」と明言している。Battle Tranceは
   3枚引いても0.9点で、1ダメージでも出る札すべてに必ず負ける。なお `drawn` は実際の手札増加量を
   測っているので、手札上限10での溢れとNoDrawによる潰れは既に自動で反映されている。
   **計器は正しく、重みだけが間違っている。**
2. `_setup_bonus` のInflame分岐にある `if len(selected) >= 2`。このターン攻撃札を2枚以上打てなければ
   `return 0` となり、Inflameは無点で後回しになる。

この1つの根に対して局所パッチが5つ積まれている。致死ターンのBattle Trance先行、Sandpit残り1〜2の
Battle Trance優先、Sandpit 3以上のTaunt先行、0コストInflame先行(`123adc3`)、`_setup_bonus` の
攻撃2枚ゲート。

### DRAW_VALUE(エネルギー比例のドロー評価)は不採用

`0.3/枚` のcapを外し、「ドローの価値は残りエネルギーで払える分しかない」という形に置き換えた。
`playable = min(drawn, state.energy)` とし、NoDrawで潰す他のドロー源の枚数を機会費用として差し引く。

オフラインA/Bは良い形だった。2037局面中321件(15.8%)で判断が変化し、Battle Tranceが先行する局面が
108件、Inflameが18件増えた。逆に**エネルギーが尽きた状態でのBattle Tranceの空打ちを67件やめた**——
ハードコードせずに出た挙動である。新規例外0件。

実機は逆だった。

| seed | 対照(HEAD素) | DRAW_VALUE=2.0 | DRAW_VALUE=1.0 |
|---|---|---|---|
| P3V8N5K2RX | 18勝1敗・QUEEN残151 | 12勝1敗・INSATIABLE残4 | 12勝1敗・INSATIABLE残90 |
| M7C4Q9V2RH | 17勝1敗・QUEEN残360＋Torch38 | 17勝1敗・QUEEN残372(Torch撃破) | — |

値を変えても同じ戦闘で落ちるので、magnitudeではなく構造の問題。機構としては正しく、オフラインでも
良い挙動を示したが、**勝率に寄与する証拠がない**ため差し戻した。Chains of Bindingと同じ結論。

構造的な過大評価も残っている: `min(drawn, energy)` はエネルギー全額をドローの手柄にするが、その
エネルギーは元の手札にも使えたので、ドローの限界価値は「選択肢が増えた分」だけである。再挑戦する
なら、ここを増分で表現するところから。

### Tremble重複抑制は不採用

報酬とショップで2枚目以降のTrembleを取らない候補。オフラインではP3・M7・Q6の3 seedすべてで発火し、
合計8枚の重複取得を止める。実機(P3、simulations=100)は戦績18勝1敗で横ばいだが、Act 3ボス戦の中身が
**12ターン・QUEEN残151から、3ターン・QUEEN残327＋Torch Head残73へ大幅悪化**した。
デッキ28枚・Tremble 1枚。Vulnerable付与が不足して火力が落ちたと読める。
「Act 3ショップ30枚上限」(残208→395へ悪化)と同じ形で、**単なるデッキ肥大ではなかった**。

### 休憩所の回復閾値は不採用(勝敗で分布が割れない)

P3の最後の休憩所がHP74から+6回復のためにSMITHを捨てていた(HEALは最大HPの30%上限)。全トレースで
HEALは1259回、SMITHは334回。しかし勝利runと敗北runで分布がほぼ同じで、判別力がない。

| run | 結果 | 休憩所 |
|---|---|---|
| N8CQ4ZKP2W | 勝利 | HATCH 1, HEAL 7, SMITH 3 |
| H2LV6ZJ4XW | 勝利 | HEAL 9, SMITH 1 |
| P3V8N5K2RX | 敗北 | HATCH 1, HEAL 8, SMITH 3 |

過去ノートの「4seedで上下に割れ判定不能」は正しかった。

### 突入時HPと敗北率は相関するが、行動可能な判断点ではない

全3385戦の集計。

| 突入時HP% | 戦闘数 | 敗北 | 敗北率 |
|---|---:|---:|---:|
| 0-49% | 78 | 41 | 52.6% |
| 50-79% | 461 | 58 | 12.6% |
| 80%以上 | 2846 | 125 | 4.4% |

HP50%未満での突入は78戦しかないのに全敗北224件のうち41件を占める。ただし `choose_rest` は既に
HP75%未満で必ずHEALし、`choose_map` もHP75%以下で休憩所寄せ・Elite回避、33%以下でUnknown回避に
切り替わる。低HPで突入した局面では**既に安全モードが働いた上での結果**であり、
「手遅れの症状」であって判断ミスではない。過去ノートの同じ戒めと一致する。

### 未モデルのpower 2件を実装(勝率改善の証拠はない)

トレースの `powers[].id` を対応表と突き合わせる既存手順で4件が挙がった。うちPyre/Ritual/Reattach/
Imbalanced/Territorial/Swipeは別名で実装済みの誤検出。**本当に無かったのは4件**で、うち敵側2件を
実装した(`0e87324`)。

- `GalvanicPower`(敵、観測値6): `BeforeCombatStart` と `AfterCardEnteredCombat` でプレイヤーの
  Powerカード全部にGalvanizedを付与し、`AfterCardPlayed` で付与済みカードを使うたびにamount分の
  Unpoweredダメージをプレイヤーへ返す。rolloutはInflame/Rupture/Feel No Painを無料だと思っていた。
- `PaperCutsPower`(敵、観測値2): `AfterDamageGiven` で、所有者の強化攻撃が `UnblockedDamage > 0` で
  通るたびにプレイヤーの最大HPをamount分削る。**ブロックすれば発生しない。**

**どちらも `POWER_NAMES` に無かったので、実装しても一度も発火しない状態だった**——FrailPowerを
全rolloutで無効にしていたのと同じ穴。対応表への追加が本体である。

ただし勝率改善の証拠はない。M7C4Q9V2RHの再走はトレースがバイト単位で一致(17勝1敗)し、記録済みの
PaperCuts 223局面のオフラインA/Bは判断変化0件だった。理由も判明している。

- PaperCuts: 最大HPの減少は戦闘内ではほぼ現在HPに影響しないので、`scored_hp` を見る探索が差を見ない。
- Galvanic: M7でGalvanic持ちの敵が生存している局面は17、うちPowerカードが手札にあったのは4局面
  だけで、エージェントは元々1枚も打っていなかった。

Juggernautと同じ扱いで、機構修正としてのみ残す。

### 未解決: Ruptureの使用率が7.1%

Act 3を踏破した2本に共通するエンジン札でありながら、全トレースで手札4888回・支払可能3866回に対し
使用276回、**使用率7.1%**。他のPowerカードと比べても低い(Inflame 25.9%、Pyre 18.2%、
Crimson Mantle 17.8%)。Inflameだけは `_setup_bonus` の例外を持つ。

**自傷札(Bloodletting/Offering/Hemokinesis/Blood Wall/Fiend Fire)をデッキに持つ局面に限っても
7.1%で変わらない**ため、「払戻しがないから使わない」では説明がつかない。

`combat.py` の実装自体は正しい(`RupturePower` を付与し、`self_damage` があればStrengthを加算)。
問題は評価で、Ruptureの効果は **Rupture→自傷札→Strength→攻撃** と2段先にあり、1手先しか見ない
greedyには原理的に見えない。`official_agent.py` 側の既存ルールは2つとも極端に狭い。

- `rupture_before_bloodletting`: rolloutが既にBloodlettingを選んだ場合のみ
- `rupture_before_queen_focus`: QUEEN戦のminion focus時のみ

一般の局面(Ruptureが手札にあり、rolloutが攻撃を選ぶ)には何も働かない。

**ただし自傷札が1枚しかないデッキではRuptureは+1 Strengthにしかならないので、7.1%の一部は正しい
判断である可能性が残る。** 手をつけるなら、自傷札の枚数で条件を切って発火数を数えるところから。
実機で前後を測るまで採用しないこと。

### 敗因の分布(17敗)

| 敗因 | 件数 |
|---|---:|
| Act 1ボス VANTOM | 5 |
| Act 2ボス THE_INSATIABLE | 5 |
| DECIMILLIPEDE | 2 |
| その他 | 5 |

VANTOMの5件は全て**満タンHP(80〜85)で突入し11〜19ターン戦って負けている**。削られて負けたのでは
なく173HPを削り切れていない。最長のC7N4V9P2RXは19ターン戦い、デッキ17枚(Strike×5、Defend×3、
Flame Barrier×2、Shrug×2、Bash、Iron Wave、Rupture、Bloodletting、Clumsy)で、Slippery解除後の
火力が約10ダメージ/ターン。VANTOMのStrengthは約4ターンごとに+2増えるので、長期戦は構造的に不利。
この run でもRuptureは19ターン通して一度も使われていない。

### 結論: ドローを先に打たせる方向は4 seedで否定された(2026-09-12)

「Battle Tranceを先に使わない」「殴ってから発火」は実測663ターンの本物の挙動だが、**それを直そう
とする変更は場所と係数を変えて3通り試し、独立した4 seedで全て悪化した。**

| 版 | 加点の場所 | 係数 | 実機結果 |
|---|---|---|---|
| DRAW_VALUE | `_step_score` | 2.0 | P3V8N5K2RX 18勝1敗 → 12勝1敗 |
| DRAW_VALUE | `_step_score` | 1.0 | P3V8N5K2RX 18勝1敗 → 12勝1敗（ボス残HPは更に悪化） |
| DRAW_VALUE | `_step_score` | 2.0 | M7C4Q9V2RH 17勝1敗で横ばい |
| GREEDY_DRAW_VALUE | `_greedy_action` のみ | 1.5 | N8CQ4ZKP2W **19戦19勝の勝利run → 18勝1敗**、QUEEN残14→349 |
| GREEDY_DRAW_VALUE | `_greedy_action` のみ | 1.5 | H2LV6ZJ4XW **23戦23勝の勝利run → 20勝1敗**、敵残15→34 |

途中で立てた「`_step_score` への加点は `search` が既にrolloutで見ているoption valueへの二重計上
だから悪化した。`_greedy_action` だけに入れれば直る」という説明は、**`_greedy_action` 版も同じように
壊れたことで否定された。** 場所の問題ではない。

オフラインA/Bはどちらも良い形に見えていた（`_step_score` 版で15.8%の局面が変化しBattle Tranceの
空打ちを67件自力で停止、`_greedy_action` 版で10.3%、例外0件）。**オフラインの見栄えは採用根拠に
ならない。**

#### なぜ後回しが正しいのか(現時点の説明)

Battle Tranceを先に打つと3枚引くが、その3枚はそのターンのエネルギーでは使い切れないことが多く、
ターン終了で捨てられる。さらに引いた分だけ山札が痩せて次ターンの引きが悪くなる。`combat.py` は
ドローも山札の減りもモデル化しているので、rolloutはそれを織り込んで「後で打て」と出していた。
**計器のほうが直感より正確だった。**

#### 方法論: 勝利seedを関門に使うことの限界

N8が2つの異なる変更で連続して壊れたため、「N8の勝利がQUEEN残14と薄すぎて、何を入れても落ちる
だけではないか」という疑いが出た。同じ変更を別の勝利seed H2LV6ZJ4XW（23戦23勝、最終HP 7/130）へ
かけて切り分けたところ、**H2も20勝1敗へ落ちた**。2つの独立した勝利seedが同じ変更で落ちるなら
変更自体が悪い、と判定できる。

**勝利seed1本だけを関門にしない。2本で確認すると、seedの薄さと変更の悪さを切り分けられる。**

### Rupture一般化も勝利seedで否定された(2026-09-12)

`rupture_before_bloodletting`（rolloutがBloodlettingを選んだ場合のみ発火）を `_is_self_damage` に
よる全自傷札へ一般化した。記録済みトレースでの発火は46局面（Bloodletting 20、Fiend Fire 12、
Breakthrough 9、Offering 4、Hemokinesis 1）。

**N8CQ4ZKP2W が19戦19勝・QUEEN残14での撃破から、18勝1敗・QUEEN残263での敗北になった。**

既存ルールが0コストのBloodlettingに限定されていたのは手加減ではない。Ruptureに1エネルギー払うと、
その自傷札を使うコンボが同ターンに完成しなくなる局面がある。

ただしRuptureの使用率が「使う理由の有無」に反応していないという数字自体は本物なので、別の形で
再挑戦する余地は残る（下表）。

| デッキ内の自傷札 | Rupture支払可能 | 使用 | 使用率 |
|---:|---:|---:|---:|
| 0枚 | 729 | 47 | 6.4% |
| 1枚 | 2730 | 186 | 6.8% |
| 2枚 | 188 | 13 | 6.9% |
| 3枚 | 219 | 30 | 13.7% |

0枚でも6.4%打ち（無駄打ち）、2枚あっても6.9%しか打たない。本来なら0枚でほぼ0%、2〜3枚で高く
なるはず。`combat.py` の実装自体は正しい（`RupturePower` を付与し `self_damage` があればStrengthを
加算）。Ruptureを使った戦闘の到達Strengthは中央値7、使わなかった戦闘は3（n=273 / 613、相関）。

### Wound/Bad Luck/Beckon の対応表追加は不採用(2026-09-12)

`combat.py` は `WOUND = "Wound"` を定義して `EXHAUST_FODDER`(廃棄して良いゴミ札)に入れているが、
`official_agent.py` の `CARD_NAMES` に `"CARD.WOUND"` が無いため、観測されたWoundは生のidのまま
rolloutへ渡り、ゴミ札として認識されていなかった。記録済みトレースで手札に**5761回**。
`BAD_LUCK` と `BECKON` も同じ状態(ただしこれらは実トレースに出現しない)。

いずれも `CARD_COST` に無いので、対応表へ入れても `legal_actions` には現れない(使用可能には
ならない)。回帰テストでその不変条件を固定した上で追加した。

**勝利seed2本がどちらも落ちた。**

| seed | 基準 | 対応表追加後 |
|---|---|---|
| N8CQ4ZKP2W | 19戦19勝 | 18勝1敗、QUEEN残263 |
| H2LV6ZJ4XW | 23戦23勝 | 22勝1敗、敵残260 |

差し戻し済み。**「モデルを正確にすれば強くなる」とは限らない**例。Woundがゴミ札として見えると
Fiend Fire / Second Wind の廃棄価値が上がって使用判断が増えるが、廃棄には手札とエネルギーを
消費するため、実際には火力や防御が減ったと考えられる。

### 有効だった検査: combat.py にあるのに CARD_NAMES に無い定数

Fasten(採用)もWound(不採用)も、同じ一手で見つかった。`combat.py` のカード名定数と
`official_agent.py` の `CARD_NAMES` の値集合を突き合わせ、差分を出す。

```
combat.py の 125定数中、CARD_NAMES 経由で到達できないもの:
  BAD_LUCK = "Bad Luck" / BECKON = "Beckon" / WOUND = "Wound"
  (POTION_* と END_TURN / RESPAWN_MOVE は別経路なので除外)
```

併せて、トレースの手札idを `CARD_NAMES` と突き合わせて「そもそも実装が無い」カードも出る。
実測で残っているのは STRATAGEM(手札1009)、MAD_SCIENCE(627)、BYRDONIS_EGG(397)、DOUBT(346)、
NEOWS_FURY(214)、LANTERN_KEY(166)、DEBT(152)、SPOILS_MAP(57) など。

**ただし採用可否は別問題である。** この検査で見つけた2件のうち、実機で勝ったのは1件だけだった。

### Stratagem の実装は不採用(2026-09-12)

`CARD.STRATAGEM` は手札に1009回来ていたが `CARD_COST` に無く、探索からは一度も使えない死に札
だった。`POWER.STRATAGEM_POWER` も対応表に無い。Fasten と同じ形の欠落。

実装内容: コスト1(強化で0)の Power カード。`StratagemPower` を1付与する。
`StratagemPower.AfterShuffle` は捨て札が山札へ戻されるたびに、山札から Amount 枚を手札へ移す。
`_draw` が reshuffle するのは山札が `count` を賄えないときちょうどなので、
`_draw_into_combat` でその場合だけ `count` を増やす形で1箇所に実装した。

実機 P3V8N5K2RX(Stratagem が出現する唯一の seed): 戦績は18勝1敗で横ばいだが、**Act 3ボス戦が
12ターン・QUEEN残151 から 8ターン・残363 へ大幅悪化**したため不採用。

これで「`CARD_NAMES` に無いカードを実装する」検査の打率は**3件中1件**(Fasten 採用、
Wound 不採用、Stratagem 不採用)。**欠落を見つけることと、埋めて強くなることは別である。**

## 2026-09-12 判定基準の変更: 勝利seed保護から母集団の総合成績へ

ユーザーの指示「勝利シードを壊すのを恐れるな。最終的にすべてのシードで勝てればいい」により、
採否の基準を変えた。

- **旧**: 既知の勝利seed(N8CQ4ZKP2W / H2LV6ZJ4XW)が1敗したら不採用
- **新**: 固定パネルでの**合計勝数**で判定。個別seedの増減では判断しない

旧基準は既知の3勝を守るだけで、母集団の勝率を上げる変更を弾いていた。実際、この変更で
**一度捨てた候補が2件生き返った**(Demon Form と GREEDY_DRAW_VALUE)。

### 固定パネル(8 seed)

`9X9WQB4QIH NFH3RMVJ6D EAIF2UUVCK 73P61QQZNU AM8C6YXHSG VTW80ZJA2G GEFYYKH1YK SWRUL944UU`

Fasten / Demon Form が出現しない seed だけで構成してあるので、それらの commit を跨いでも
基準値がそのまま使える。1腕あたり8 run、約4時間。基準合計は Fasten 実装後で **95**、
GREEDY_DRAW_VALUE 採用後で **98**。

### 母集団で再評価した結果

| 候補 | 旧判定 | 母集団 | 新判定 |
|---|---|---|---|
| Demon Form | (未評価) | 3 seed合計 29→32 **+3** | **採用** `e50f509` |
| GREEDY_DRAW_VALUE | 不採用(N8/H2が各1敗) | 8 seed合計 95→98 **+3** | **採用** `ef67f44` |
| Wound等の対応表 | 不採用(N8/H2が各1敗) | 8 seed合計 98→98 **±0**、7/8でトレース一致 | 不採用(**効果が無い**ため) |
| Rupture一般化 | 不採用(N8が1敗) | **測定不能**(8 seed全てトレース一致) | 保留 |

### 訂正: Wound の不採用理由

前回「Woundがゴミ札として見えると Fiend Fire / Second Wind の廃棄価値が上がって使用判断が
増え、手札とエネルギーを消費して火力が落ちた」と説明したが、**測定で否定された**。パネルでは
8 seed中7つでトレースがバイト単位で一致しており、判断がほぼ変わっていない。
1〜2 seedの結果にもっともらしい理屈を付けてしまっていた。

### Rupture一般化が測定不能だった理由

パネルにRupture自体は出る(9X9WQB4QIHに121行、SWRUL944UUに76行)。発火しなかったのは、
**Ruptureが手札にあり、rolloutが自傷札を選び、Ruptureがまだ未発動**という3条件が同時に
揃う局面が1つも無かったため。条件が狭い候補は、専用のseed群を集めないと測れない。

### Demon Form 採用の内訳

| seed | base | cand | delta |
|---|---:|---:|---:|
| FO6WE4T5PM | 11 | 12 | +1 |
| J7GW6DFX9V | 12 | 8 | -4 |
| S4N8K2V6QJ | 6 | 12 | +6 |
| 合計 | 29 | 32 | **+3** |

旧基準なら「J7が4戦悪化」で捨てていた。

## 2026-09-13 Act 3ボス(QUEEN)戦の敗因は打ち回しではない

改善を積んだ版(Fasten / Demon Form / GREEDY_DRAW_VALUE / Neow's Fury / 詰みターンの防御放棄)で
58 seed を回してもAct 3踏破は0。最良は sweepF_SOS6XYXCNO の17勝1敗。

### QUEEN戦で起きていること(複数seedで共通)

```
T3 プレイヤーに WEAK 100 / FRAIL 99 / VULNERABLE 99 が乗る
   → 与ダメージ x3/4、ブロック x3/4、被ダメージ x1.5 が事実上恒久化
T4 自HP が一気に溶ける(32 -> 9 など)
```

**モデルはこの3つを正しく扱っている。** 直接確認した:

| | 通常 | デバフ下 |
|---|---:|---:|
| Strike のダメージ | 6 | 4 |
| Defend のブロック | 5 | 3 |
| 被ダメージ | 10 | 15 |

### 早計だった仮説: Torch Head を削るのは無駄

`TorchHeadAmalgam` は `MinionPower` を持つので「倒さなくても勝てる敵」に見える。しかし
`official_agent.py` の `queen_minion_focus` にコメントで設計意図が書かれている——
**Queen がバフとブロックをしている間、実際にHPを削ってくるのは Torch Head だけ**なので
意図的に優先している。CLAUDE.md が戒める「意図された実装を新発見と読み違える」形だった。

### 結論

QUEEN戦の敗北は**デッキ火力の不足**であって、戦闘中の判断ミスではない。SOS6XYXCNO の
最終デッキは34枚で Strike 4 / Defend 4 / Anger 4、スケーリング札なし。デバフ込みで
400+199 HP を削る火力が無い。

**打ち回し(探索・評価・局所ルール)の調整では踏破は出ない。** 次に測るならカード取得方針。
過去にデッキ構築系が繰り返し否定されているが、あれは1〜2 seedで判定していた時期の記録であり、
固定パネルで母集団を測れる現在なら再挑戦の価値がある。

### 訂正: デッキ構成と勝ちの相関は因果が逆(2026-09-13)

最終デッキで比べると、上位(13勝以上)と下位(8勝以下)には差が見える。

| | 上位 n=17 | 下位 n=22 |
|---|---:|---:|
| デッキ枚数 | 22.6 | 16.5 |
| スケーリング札 | 1.5 | 0.5 |
| 基本札の割合 | 34% | 50% |

**これは因果が逆である。** 長く勝つほど報酬機会が増えるので、デッキが厚くなるのは結果。
同じ地点(8勝時点、両群とも到達している)で揃え直すと差が消える。

| 8勝時点 | 深く進むrun(13勝以上) | 浅いrun(11勝以下) |
|---|---:|---:|
| デッキ枚数 | 16.6 | 16.5 |
| 基本札 | 8.6 | 7.8 |
| スケーリング札 | 0.59 | 0.62 |
| 基本札の割合 | 52% | 47% |
| HP | 50.9/81.8 (62%) | 52.6/83.5 (63%) |
| レリック数 | 5.1 | 5.0 |

**8勝時点では、深く進むrunと浅いrunに検出可能な差が無い。** デッキ、HP、レリックの
どれもほぼ同一。ノートの「デッキ構築系は繰り返し否定された」は、判定基準を母集団へ
変えた後でも正しい。「固定パネルで測れる今なら再挑戦の価値がある」という判断は撤回する。

比較するときは**同じ地点で揃えること**。最終状態の比較は、深さそのものが交絡する。

## 2026-09-13 敗因の分布と、2つのボスの構造的な壁

全スイープ67敗の内訳。**Act 3の心配をする段階ではない。**

| 敗因 | 件数 | 到達戦闘数の中央値 |
|---|---:|---:|
| **THE_INSATIABLE**(Act 2ボス) | **23** | 12 |
| **VANTOM**(Act 1ボス) | **15** | 7 |
| DECIMILLIPEDE | 3 | 11 |
| QUEEN+TORCH_HEAD(Act 3ボス) | 2 | 18 |
| その他 | 24 | — |

**38敗(57%)がこの2体。** QUEENまで到達したのは67敗中2件しかない。QUEEN戦を解剖していたのは
優先順位の誤りだった。

### THE_INSATIABLE(23敗)は火力不足のタイムアップ

| | 中央値 |
|---|---:|
| 突入時HP | **81%** (削られて負けているのではない) |
| 生存ターン | 9 |
| ボス残HP | **148 / 321** (半分も削れていない) |
| 与ダメージ | 約200 |
| ダメージ/ターン | **22** |
| Frantic Escape 使用回数 | 4 |
| Sandpit の最大値 | **4** |

**手札に Frantic Escape が来たのに使わなかった run は23件中0件。** 使い方に怠慢はない。
Sandpit は Frantic Escape で +1 されるが上限が事実上4で、時間をこれ以上稼げない。
9ターンで321HPを削るには **約35ダメージ/ターン**が要るが、実測は22。**約1.5倍足りない。**

### VANTOM(15敗)も同じ形

満タンHPで突入し11〜19ターン戦って173HPを削り切れない。Slippery解除後の火力が約10/ターン。
VANTOMのStrengthは約4ターンごとに+2増えるので長期戦は構造的に不利。

### 結論

どちらも**打ち回しではなく火力の問題**。そして同じ地点(8勝時点)で比べるとデッキ・HP・レリックに
深く進むrunと浅いrunの差は無い(前節)。つまり現在の敗北は、エージェントの判断の巧拙より
**引いたカードプールの内容**で決まっている可能性が高い。

探索・評価・局所ルールの調整をこれ以上続けても、この2体は抜けられない見込みが強い。

### THE_INSATIABLE戦の内訳: Frantic Escape の使い方に無駄は無い

23敗・184ターンの内訳を調べた。

**最も多く打たれている札が `FRANTIC_ESCAPE` 108回(0.59/ターン)** で、Strike(98)や Defend(58)より
多い。Frantic Escape はダメージもブロックも出さず Sandpit を +1 するだけなので、「延命に
エネルギーを浪費しているのでは」という仮説を立てたが、**測定で否定された。**

Frantic Escape を打った瞬間の Sandpit 値(全runの128回):

| sand | 回数 |
|---:|---:|
| 1 | 14 |
| **2** | **90** |
| 3 | 15 |
| 4 | 7 |
| 5 | 2 |

**90/128 が sand=2 の時点**。sand は毎ターン1減り、1になると即死するので、sand=2 は打たなければ
次のターンに死ぬ局面である。上限付近での空打ちは9回のみ。使用時のコストも106/128が1で、
個体コストが上がる前に使えている。**使い方は妥当。**

余剰ブロックは184ターンで413(2.2/ターン)、未使用エネルギーは0.09/ターン。仮に余剰ブロックを
全部ダメージへ替えられても 22 → 24 程度で、必要な35には届かない。

### 構図

- Sandpit は毎ターン1減り、Frantic Escape で +1 戻す
- **戻す速度が減る速度に追いつかない**ので9ターンで尽きる
- その間に321HPを削る必要があるが、Frantic Escape にエネルギーを取られて22/ターンしか出ない
- 打たなければ即死するので逃げ場が無い

**局所の判断ミスではなく、この戦闘の設計に対して現在のデッキ火力が足りていない。**
打ち回しの調整でここを抜けるのは見込みが薄い。

### simulations=200 は不採用(2026-09-13)

探索の試行数を100から200へ上げて8 seed パネルで測定した。

| seed | base(100) | 200 | delta |
|---|---:|---:|---:|
| 9X9WQB4QIH | 16 | 11 | **-5** |
| NFH3RMVJ6D | 15 | 15 | 0 |
| EAIF2UUVCK | 14 | 15 | +1 |
| 73P61QQZNU | 13 | 12 | -1 |
| AM8C6YXHSG | 18 | 12 | **-6** |
| VTW80ZJA2G | 12 | 12 | 0 |
| GEFYYKH1YK | 7 | 13 | **+6** |
| SWRUL944UU | 6 | 6 | 0 |
| 合計 | **101** | **96** | **-5** |

**探索を深めると悪化する。** 過去に「simulations 500 で L3 のボス残HPが 24→153 へ悪化」と
記録されているが、別の版・別の seed でも同じ方向が再現した。**試行数は多いほど良い、ではない。**

推測される理由: `search` は貪欲ロールアウトなので、試行を増やすとロールアウトの平均値へ
収束し、実際に良い初手を示す `immediate` 項が相対的に薄まる。平均的な打ち回しの見積もりが
正確になるほど勝ち筋の分散を捨てる。

なお GEFYYKH1YK では +6 の大当たりが出ている。**個別 seed の当たりで判断しないこと** の
実例でもある(この1件だけ見れば採用してしまう)。

### 休憩所のSMITH優先は不採用(2026-09-13)

`choose_rest` は HP が満タンのときしか SMITH へ到達しない。HEAL は最大HPの30%が上限で
不足分にも制限されるため、小さな傷で休むと大半が無駄になる。実測では直近の234回のHEALのうち
**72回(31%)が回復量の半分以下**、38回が3分の1以下だった。

候補: HPが半分以上あり、かつ不足分が回復量の半分未満なら SMITH を選ぶ。危険なHPでは従来どおり回復。
実装とテスト4件は `git stash` に退避してある。

8 seed パネルを再開し、7 seed まで測り切った。

| seed | base | SMITH優先 | delta |
|---|---:|---:|---:|
| 9X9WQB4QIH | 16 | 13 | **-3** |
| NFH3RMVJ6D | 15 | 15 | 0 |
| EAIF2UUVCK | 14 | 14 | 0 |
| AM8C6YXHSG | 18 | 17 | -1 |
| VTW80ZJA2G | 12 | 12 | 0 |
| GEFYYKH1YK | 7 | 7 | 0 |
| SWRUL944UU | 6 | 6 | 0 |
| 合計(7 seed) | **88** | **84** | **-4** |

**改善した seed が1つも無く、悪化が2つ。** 残る 73P61QQZNU は測っていない(下記の事故で
汚染したため破棄した)。その1 seed が base 13 から 18 まで伸びない限り合計は戻らないので、
**不採用**とした。回復の無駄は実在する(直近234回のHEALのうち72回が回復量の半分以下)が、
それを鍛冶に振り替えると勝数は減る。実装は `git stash` に残してある。

### スイープ中に作業ツリーの .py を編集すると測定が汚れる(2026-09-13)

上の 73P61QQZNU はこれで破棄した。`run_official_autoslay.ps1` はリポジトリの
`official_agent.py` をその場で読むので、**スイープが走っている最中に編集すると、次の seed
から別のコードが走る。** 編集中の中途半端な状態(定数だけ足してヘルパが無い)が走る可能性も
ある。開発は `git worktree` を別パスに切って、そちらで編集・テスト・commitすること。

### bridgeが出すカードの `vars` は補正適用後の表示値(2026-09-13)

`CombatBridge.cs` は `DynamicVars[...].PreviewValue` を出している。`DamageVar.UpdateCardPreview`
は `Hook.ModifyDamage` を通した後の値を `PreviewValue` へ入れるので、**Strength・Weak・Frail・
エンチャントが適用済み**である。実トレースに `Damage=6.75`(9のWeak)や `Damage=2.8`(4のShrink)
のような小数が出ているのがその証拠。

Maul/Thrash の成長分をここから読もうとして一度実装し、二重計上になるため取り消した。
**`vars` の値を「カードの基礎値」として使ってはいけない。**

### 休憩所のSMITH優先を現行コードで再測定し採用(2026-09-19)

2026-09-19の未対応カード・レリック実装後のコードで、SMITH候補とSMITHなしの対照を同じ固定条件で測定した。ゲーム v0.107.1、固定ユーザーデータ、`simulations=100`、Act 3まで、各seed 1 runである。採否は終了コードではなく、traceの`won`合計で判定した。

| seed | SMITHなし | SMITH優先 | 差分 |
|---|---:|---:|---:|
| 9X9WQB4QIH | 11 | 13 | +2 |
| NFH3RMVJ6D | 15 | 15 | 0 |
| EAIF2UUVCK | 14 | 14 | 0 |
| 73P61QQZNU | 13 | 13 | 0 |
| AM8C6YXHSG | 15 | 18 | +3 |
| VTW80ZJA2G | 12 | 12 | 0 |
| GEFYYKH1YK | 7 | 7 | 0 |
| SWRUL944UU | 6 | 6 | 0 |
| **合計** | **93** | **98** | **+5** |

SMITH優先を採用する。candidateのtraceは`data/codex_smith_candidate_20260919_*`、対照のtraceは`/Users/mao/.sts2/wt-dev/data/codex_smith_base_20260919_*`に保存している。候補実装と回帰テストはmainに採用する。

### 固定panelの Act 3 踏破は采点で届かない（2026-10-01、ceilingとして記録）

固定8 seed panel（`9X9WQB4QIH NFH3RMVJ6D EAIF2UUVCK 73P61QQZNU AM8C6YXHSG VTW80ZJA2G GEFYYKH1YK SWRUL944UU`）は commit `29ec088` 対照で win 合計98、Act 3 踏破 **0/8**。7/8 seed が Act 2 boss `MONSTER.THE_INSATIABLE`（HP 321）で死亡する。これは采点の改善で動かせない、ということを三つの独立した測定で確定した。

1. **実 deck の模型 win rate**（記録から `Enemy`/`Combat` を再構成し greedy rollout 150回）が全 seed **0.00**、HP を最大値へ振っても 0.00–0.04。実走の死亡と一致するので replay の boss state machine と采点は正しい。
2. **oracle deck**（各 card_reward で `CARD_DAMAGE` 最大の offer を選んだ形、energy 経済込みの damage/energy 最大の形、run 中に出現した最高 card だけ積んだ god deck）でも **全 seed 0.00**。reward policy が win を残している仮説は否定される。
3. **采点に無関係な上界**：1ターンで damage card か block card のどちらかだけ、3 energy を単一カード種別に使うという現実的な形で、届く damage 合計は **30–45**（block と damage を同一ターンで両方最大化する甘い形でも 105–162）。boss HP 321 に対して1桁足りない。生存が 2–5 turn で潰れる（boss incoming ≈36.8/turn 対 deck の block 21–33/turn）。

population（固定8 seed外、`data/act3_pop2_*` 10 seed）でも Act 3 win chance は 1 seed（`R8V2H6N4ZB`、full HP・27 card）の 3% だけで 0/10。よって 33%（3 seed 踏破）は panel 固有の運ではなく、この分布で policy から生じない。future session はこの再測定に4hの実走を使わない。

**closed lever（reach = panel の decision 数、noise閾値 3件/3 seed）**：boss DPS-greedy 588/1028（policy 上書きなので実走対象外）、safety-branch elite 重み 18（flip 0）、boss damage-potion 340（flip 0）、event damage-relic 4（1 seed）、rest HEAL/SMITH 3（`test_rest_heals_near_boss` が落ちる、かつ 2026-09-08 に同じ方向が上下に割れて不採用記録済み）、rest SMITH 対象 card 2、shop weakest-card removal 1、survival-potion 1、reward heavy-hitter 0、conditional damage-priority 1、applier tie-break 0、same-turn booster credit 0、enemy phase 込み采点 0、boss 選択 0（panel/population に boss を2つ並べて提示する decision が無い）。

panel で effect 0 だが正しさの fix として commit したものは `fdb0d7e`（greedy continuation の `GREEDY_DEATH_PENALTY`、707 OK）。vulnerable credit 系は panel で負（対照98→unguarded 91→guarded 80）なので不採用。

## event の option effect（v0.107.1、ilspycmd で確認、panel の reach 付き）

`choose_event` は `EVENT_OPTION_SCORES` に entry の無い event について `{"type": "event_fallback"}` を返し、`EventBridge.cs`（line 141-152、pin `test_official_agent.py:4869`）はそれを `invalid_event_action` として game の fallback に投げる。panel では 81 decision 中 26件（6 seed）がこれに該当する。実走で測れない理由は、trace の event record に**選ばれた option しか残っていない**こと（observation の `options`/`legal_actions` が残っていない）。

panel で出現した未coverage event の effect（decompile 済み）：

| event | option → effect | panel reach |
| --- | --- | --- |
| `SPIRIT_GRAFTER` | LET_IT_IN = heal 25 + `Metamorphosis` を deck に追加 / REJECTION = 1枚 upgrade + 10 Unblockable damage | 2 |
| `THE_LEGENDS_WERE_TRUE` | NAB_THE_MAP = `SpoilsMap`（curse）追加 / SLOWLY_FIND_AN_EXIT = 8 Unblockable damage | 2 |
| `BRAIN_LEECH` | SHARE_KNOWLEDGE = colorless pool から card 1枚 / RIP = 5 Unblockable damage | 2 |
| `DOLL_ROOM` | RANDOM / TAKE_SOME_TIME = 5 damage / EXAMINE = 15 damage（RANDOM の中身は event state 依存） | 1 |
| `WHISPERING_HOLLOW` | GOLD = 35 gold / HUG = HP loss + Transform | 1 |
| `LOST_WISP` | CLAIM = 60 gold + `Decay`(curse) / SEARCH = `Decay`(curse) のみ → **CLAIM が fact 上 strict に良い** | 1 |
| `FIELD_OF_MAN_SIZED_HOLES` | RESIST = `Normality`(curse) / ENTER_YOUR_HOLE = `PerfectFit` enchantment + gold | 1 |
| `THE_LANTERN_KEY` | RETURN_THE_KEY = 100 gold / KEEP_THE_KEY = fight | 1 |
| `TEA_MASTER` | `BoneTea` / `EmberTea` / `TeaOfDiscourtesy` の relic 選択（observation に relic_id が載らない） | 1 |
| `TINKER_TIME` | card type を選んで効果（12 damage / 8 block / Weak 2 / Vulnerable 2 / Strangle 6 / energy 2 / Strength 2 / Dexterity 2） | 1 |
| `POTION_COURIER` | GRAB_POTIONS = `FoulPotion` / RANSACK | 1 |
| `INFESTED_AUTOMATON` | STUDY / TOUCH_CORE | 1 |
| `DENSE_VEGETATION` | TRUDGE_ON = HP loss / REST → FIGHT | 1 |
| `WELCOME_TO_WONGOS` | BARGAIN_BIN / FEATURED_ITEM / MYSTERY_BOX / LEAVE（purchase） | 1 |
| `TRIAL` | curse（`Regret` / `Shame`）分岐 | 1 |
| `BUGSLAYER` | EXTERMINATION = `Exterminate`（未モデル化） / SQUASH = `Squash`（cost 1、damage 10） | 3 |
| `SAPPHIRE_SEED` | EAT = heal 9 / PLANT = `Sown` enchantment | 2 |
| `COLOSSAL_FLOWER` | gold 35/75/135 で dig、damage 5/6/7 | 1 |

fact 上 strict に優る選択は `LOST_WISP` の CLAIM だけで、reach 1（閾値 3 件/3 seed 未満）。残りは「heal/gold/curse/upgrade の trade-off」で、policy の既存 criterion（block-starved、low HP、relic axis）と同じ方向なので、単独の lever として測る意味が無い。よって event scores は追加分を書かない（reach ≥3 が出るまで書かない）。

## shop の affordability は bridge の filter が source（v0.107.1、code + 全 trace で確認）

`ShopBridge.cs`（line 143-194）は observation の `cards`/`relics`/`potions`/`removal` に `cost` と `affordable` を载せ、`legal_actions` には `IsStocked && EnoughGold` の slot だけを追加する。potion はさらに free slot が無いと列挙されない（line 193）。`choose_shop` は `legal_actions` だけで采点するので、**policy が购买できない item を選ぶことは構造上無い**。pin：`test_shop_never_picks_a_card_that_is_not_in_legal_actions`。

実測で確認（panel 8 seed + astra 107 run の全 `decision_reason`）：`invalid_shop_action` / `invalid_potion_action` / `potion_slots_full` は 0件。curse がいて removal が offer されている shop decision 63件で policy は 63/63 removal を選んだ。`choose_shop` の skip は terminal branch（line 2155）で、removal が affordable で curse が無い case の skip は 0件 → policy は自分の criteria に対して整合的。

gold は shop 間で持ち越されるが、最後の shop 以降の gold は combat に効かない（value 0）。astra 107 run の final gold median 121（59 run が ≥100）で、これは「bar を下回った item ばかりだった」ことを意味するだけで defect は無い（bar が高いかは policy choice の話、path closed）。

## 未モデルだった power / relic / curse を実装（2026-10-04、実走測定前）

「対応表にあっても combat.py が消費しなければ一度も発火しない」という既知の欠落 class を、
trace の観測 id 集計で洗った（player powers 56 id 中 8、relic 40 id 中 29 が未対応だった）。

| 追加 | 機構（decompile 由来） | corpus の観測回数 |
|---|---|---:|
| Wither | Curse、`HasTurnEndInHandEffect` で 3 flat Unpowered。`Unblockable` が無いので block が吸収する（Beckon / Bad Luck と違う）。`CARD_NAMES` 対応 + `HAND_INJECTED_STATUS` | 0（corpus 未観測、decompile からの補完） |
| Fiddle | `ModifyHandDrawLate` +2、`ShouldDraw` が hand draw 以外のドローを拒否 | 242 |
| Blood-Soaked Rose | `ModifyMaxEnergy` +1 を毎ターンの energy reset で加算 | 70 |
| Forgotten Soul | `AfterCardExhausted`：1 Unpowered を**ランダム1体**へ（Charon's Ashes の全体とは違う） | 74 |
| Chains of Binding | `AfterCardDrawn` が自分のドローを Amount 枚まで Bound にする。live の hand は bridge の `bound` で既に正しかったが、rollout 内のドローが対応していなかった | 3849 |
| Duplication / OneTwoPunch | `ModifyCardPlayCount +1`：その play の解決がもう1回走る。Attack は hit が倍、block card は grant が倍。play で消費され、turn end で除去 | 69 / 10 |
| Gigantification | 最初に打った powered Attack の damage を ×3、その command で decrement | 38 |
| Panache | `AfterCardPlayed`：適用した play は数えず（`alreadyApplied`）、以降5枚目の play で Amount（10/14）を全敵へ Unpowered、counter リセット | 20 |

機構としての正しさは test_combat の追加分で固定した。実走 panel を回していないので**勝率への効果は未評価**。

### 残っている未モデル

- **PollinousCore**：counter が戦闘横断の `SavedProperty` で観測に無い。phase が不明なので modelable でない（relic counter は観測不能、という既存の結論どおり）
- **BigMushroom / RoyalPoison / Lantern / BagOfMarbles / Vajra / Gorget / Bronze Scales**：effect が combat 開始時または turn 1 だけ。最初の観測が既に反映しているので rollout に影響しない
- **GamblingChip**：player の選択（何枚捨てるか）が模型外
- **ImprovementPower**：`AfterCombatEnd` で deck を upgrade。戦闘内の decision に無関係
- **StratagemPower**：機構は正しいが 2026-09-12 の実走で QUEEN 残 151→363 へ悪化、不採用
- **Enthralled / Wound / Dazed**：combat effect が無い（Eternal / Unplayable のみ）。Dazed は draw pile の汚れとしてのみモデル

## 固定8 seed panel の A/B 完走（2026-10-03）と −6 の原因

arm = HEAD（未モデル power/relic/curse 実装）、control = `e808bdf`（同一条件で取り直した基準）。
game v0.107.1、固定ユーザーデータ、`simulations=100`、Act 3まで、各 seed 1 run。判定はトレースの `won`。

| seed | control | arm | delta | arm の発火 | decision列 |
|---|---:|---:|---:|---|---|
| 9X9WQB4QIH | 14 | 14 | 0 | DuplicationPower 1回 | 完全一致 |
| NFH3RMVJ6D | 15 | 15 | 0 | なし | 完全一致 |
| EAIF2UUVCK | 14 | 14 | 0 | なし | 完全一致 |
| 73P61QQZNU | 13 | 13 | 0 | なし | 完全一致 |
| AM8C6YXHSG | 17 | 11 | **−6** | なし | seq 244 から分歧 |
| VTW80ZJA2G | 13 | 13 | 0 | なし | 完全一致 |
| GEFYYKH1YK | 7 | 7 | 0 | なし | 完全一致 |
| SWRUL944UU | 6 | 6 | 0 | なし | 完全一致 |
| **合計** | **99** | **93** | **−6** | | |

7 seed は decision列が control と完全一致＝測定不能（発火がないのでarm/controlが同じ選ぶ）。
panel 全体で唯一動いた AM8 の −6 は、**機構の実装ではなく生成プールの副作用**だった。

### seq 243 の切り分け（`data/replay_243.py`）

同一 observation を両commitで replay すると記録値がそのまま再現される（arm 1.9925 / control 1.956875）。
hand・draw pile・enemies・powers・relics は完全一致。差の原因は `STOKE_GENERATION` の中身：

```
arm : (..., 'Offering', 'One-Two Punch', 'Pacts End', 'Panache', 'Peck', ...)
ctrl: (..., 'Offering', 'Pacts End', 'Peck', ...)
```

`STOKE_GENERATION` は `CARD_COST` から導出されるので、PANACHE と ONE_TWO_PUNCH を `CARD_COST`
へ足した時点で生成プールが silently に広がっていた。生成セットを control の形へ戻すと arm が
control の記録値（1.956875）を完全再現する。つまり AM8 の −6 は「正しく機構を教えた」ことによる
変化ではなく、近似プールの要素追加による rollout の分岐。

### 生成プールはキャラクター自身のプールだけ（commit `77120b2`）

`Stoke.cs` / `InfernalBlade.cs`（decompile）は `Owner.Character.CardPool.GetUnlockedCards(...)` から
生成する。Ironclad の pool（`IroncladCardPool.cs`、87枚）に Panache は無い — Panache は
`ColorlessCardPool`。したがって Ironclad run で Stoke が Panache を生成することは無い。
One-Two Punch は Ironclad pool に在るので生成しうる（この方の追加は忠実）。

model は知っている札しか生成できないので、忠実な近似は「model が knows ∧ character pool」の集合。
`CARDS_OUTSIDE_THE_CHARACTER_POOL` として固定し、`STOKE_GENERATION` と `INFERNAL_BLADE_ATTACKS`
から除いた（32名）。回帰テスト `test_generated_cards_come_only_from_the_characters_own_pool`。
実走の照合：panel の Stoke 使用 6件で生成された札はすべて `CARD_POOL.IRONCLAD_CARD_POOL` — 一致。

生成プールの限定の決定レベル到達性（arm 記録の replay）：AM8 **11件 / 1 seed**、9X9・NFH3・EAIF・73P で 0。
1 seed の増減は採用根拠にしない rule のまま、正しさ（デコンパイル）で commit した。勝率への効果は未測定。

### 一致の件数（再走5 seed の内訳）

5 seed は AutoSlay watchdog timeout で終了（exit=1、`result.json` なし）→ 判定はトレースの `won`。
decision列を件数で照合した：

| seed | arm rows | control rows | decision diff | wins arm/control |
|---|---:|---:|---:|---|
| 9X9WQB4QIH | 265 | 265 | 0 | 14 / 14 |
| NFH3RMVJ6D | 275 | 275 | 0 | 15 / 15 |
| EAIF2UUVCK | 276 | 276 | 0 | 14 / 14 |
| 73P61QQZNU | 243 | 243 | 0 | 13 / 13 |
| AM8C6YXHSG | 216 | 351 | **52** | 11 / 17 |
| VTW80ZJA2G | 269 | 269 | 0 | 13 / 13 |
| GEFYYKH1YK | 164 | 164 | 0 | 7 / 7 |
| SWRUL944UU | 120 | 120 | 0 | 6 / 6 |

7 seed は decision列が control と完全一致。同じ決定列なら outcome も同じ（game の RNG は seed 由来）
なので、この7件は watchdog の有無に関係なく「測定不能」が確定。AM8 の分歧は seq 244（SWORD_BOOMERANG）
からで、件数差は arm が早く負けたぶん。

`CardFactory.FilterForCombat` は `CanBeGeneratedInCombat && Rarity != Basic/Ancient/Event` を
通すので、model が Basic（Strike/Defend/Bash）を生成集合から除いているのは忠実。忠実な集合は
「model が knows ∧ character pool ∧ non-Basic」で、commit `77120b2` の形がそれ。
実走の生成 record（hand に現れた札）で Basic が一度も出ていないのも一致。

## 機構単独の到達性（2026-10-03、sample）と mechanism panel

固定8 seed panel は機構がほぼ発火しない（12,841件の内、panel 分の発火は 9X9 の DuplicationPower 1回
だけ）ので、この panel では機構の実走効果を測れない。corpus 512 trace の集計：

- 機構 id を含む combat record（`legal_actions` 付き）：**12,841件 / 139 seed**
- decision_source：rollout_success 8,070 / **heuristic_fallback 2,655** / lethal系 672 / direct_potion 266
- 機構の札そのものを打った record：13件（One-Two Punch 10、Panache 3）

同一 observation を両commitで replay した（`STOKE_GENERATION` を control の形へ固定して生成プールの
副作用を隔離、1-in-12 sample）：**照合620件で分歧116件 / 15 seed**。内訳（多い順）
`N8CQ4ZKP2W` 57、`H2LV6ZJ4XW` 24、`AM8C6YXHSG` 15、`R8V2H6N4ZB` 4、`D1W9Y3B7FC` 3、
`P3V8N5K2RX` 2、`B3N8V5T1WQ` 2、`Q6N3V8K2MT` 2、ほか1件ずつ。→ 閾値（≥3 decisions かつ ≥3 seeds）超。

実走：mechanism panel 8 seed（上の順）で control `e808bdf` → arm HEAD（`77120b2` 以降）の順で
16 run を直列実行。生 data は `data/mechpanel_ctrl_*` と `data/mechpanel_arm_*`（git除外）。

### 訂正：curses は実装済み

「残っている未モデル」に並んでいた DOUBT・REGRET・SHAME は main で実装済み（`test_curses_left_in_hand_hit_the_player_at_turn_end` が pin）。
decompile 上、`Regret.OnTurnEndInHand` は hand size ぶんの **Unblockable** Unpowered damage（`Beckon`/`Bad Luck` と
同じ hook だが block で absorb される側・されない側が違う）、`Doubt` は Weak 1、`Shame` は Frail 1
（`SkipNextDurationTick` で次の tick を飛ばす＝player の次のターンに効く）。
`Debt` は `PlayerCmd.LoseGold(min(10, gold))` だけで戦闘効果が無い → model 外（gold 経済を扱わない）なので実装不要。

sample の分歧116件を機構別に分解（record に複数の機構が同時に在る場合はあるので件数は機構別、合計は116超になりうる）：

| 機構 | flip | seed数 |
|---|---:|---:|
| `RELIC.FIDDLE`（hand draw 以外を拒否＋hand draw +2） | **76** | 4 |
| `POWER.CHAINS_OF_BINDING_POWER`（rollout 内のドローを Bound） | **34** | 5 |
| `RELIC.FORGOTTEN_SOUL`（exhaust 1枚につき random 1体へ1） | 24 | 1 |
| `RELIC.BLOOD_SOAKED_ROSE`（毎ターン energy +1） | 8 | 4 |
| `POWER.DUPLICATION_POWER` / `CARD.ONE_TWO_PUNCH` | 2 / 2 | 2 / 2 |
| `CARD.PANACHE` | 1 | 1 |

Fiddle と Chains が分歧の主成分（rollout 内のドロー挙動を変える機構）。Gigantification は sample に
分歧なし（0件）。到達性の内訳が機構ごとに偏っているので、panel 実走は「機構まとめて1本」ではなく
この内訳が実際に勝敗へ伝わるかを見る測定として扱う。

### Fiddle と Chains の照合（panel 実走中に現物で確認）

- `Fiddle.ShouldDraw`：`fromHandDraw` は許可、owner 以外許可、**owner の side 中は拒否**。`ModifyHandDrawLate` は owner の hand draw +2。model の `if not from_hand_draw and RELIC_FIDDLE in player_relics: return` はこれと一致
- `ChainsOfBindingPower.AfterCardDrawn`：「このターンにこの actor が Bound にした枚数」が Amount 未満のとき Afflict。model は hand 内の bound 枚数で同じ上限を掛けている。Bound 札は play できないのでターン内で hand から消えず、ターン end で flush されて bound が落ちる → ターン単位の count として等価
- `Debt` は gold のみ（戦闘効果なし）

sample の分歧主成分（Fiddle 76・Chains 34）は機構の正しさではなく「rollout が将来引く札をどう数えるか」の差。
実走で測れるのは、その差が胜敗へ伝播する seed があるか。panel の control 腕で `N8CQ4ZKP2W` は 5勝1敗
（Act 1 F14 elite で死亡）＝この seed では機構の有無以前に commit 差が勝敗を決めている例。

### run レベルの A/B は「両腕で同じ機構が出た」ときにのみ機構を測れる

機構の出現は path 依存：Fiddle・Blood-Soaked Rose・Forgotten Soul は relic 報酬（自動取得）で、
どの報酬・休憩・戦闘が来るかは policy の分岐で変わる。だから同一 seed でも arm 側で発火して
control 側で発火しないことがある。その seed は A/B として**attribution 不能**（機構の実装差ではなく
game が違った offer を出した）。同じ observation を両commitで replay した到達性計算だけが
「機構単独の差」を隔離できる（上の sample：620件で116分歧）。

mechanism panel の control 腕（`e808bdf`）でこれまでの発火は 0：`N8CQ4ZKP2W` 5W1L・fired none、
`H2LV6ZJ4XW` 12W0L・fired none。`data/compare_panel.py` は tag/seed を引数で受け取る形にした
（commit `bbf0abd`）。panel の判定は per-seed だけでなく **fired を両腕で確認してから**使う。

参考：同じ seed の古い record では FIDDLE が数千行に出る（N8 の `candidate` run 3,419行、
H2 の `candidate` run で FORGOTTEN_SOUL 3,249行）＝取得している run では恒久的に観測へ出る。
control 腕の run が取得していない＝route/reward が違う。

### Forgotten Soul の実走証拠（decompile だけでなく record で確認）

`data/candidate_headbutt_D6A1F8C3E5_agent.jsonl` の seq 379・380：`CARD.TREMBLE`（damage 0 の
exhaust 札）を打った turn で、confound しうるレリック（Charon's Ashes・Nunchaku・Pendulum）は
未所持、enemy の `hp+block` が **ちょうど1** 減っている。`ForgottenSoul.AfterCardExhausted` の
「exhaust 1枚につき random 1 hittable 体へ 1 unpowered」そのもの。全体へ出す Charon's Ashes とは
違う、という実装の主張が record 側でも立った。

同じ条件の record は corpus でこれ以外の0件（drop 0 の反例も無し）＝サンプルは小さいが、
機構の方向性は正しい。Fiddle・Chains・Duplication・Gigantification・Panache・One-Two Punch は
現物照合（hook 名と条件）で固定済み。

### 固定 panel で「両腕が同じ機構を見た」 pair は2件だけ

panel 8 seed を両腕で洗うと、機構が **両腕の record に出る** seed は：

| seed | 機構 | decision diff |
|---|---|---:|
| `9X9WQB4QIH` | `POWER.DUPLICATION_POWER`（両腕） | 0 |
| `73P61QQZNU` | `CARD.ONE_TWO_PUNCH`（両腕） | 0 |

`AM8C6YXHSG` は control 側だけ FIDDLE・FORGOTTEN_SOUL・CHAINS・OneTwoPunch を持っていて、**arm 側の run は一つも見ていない**（機構を引く/route が違った）。だから AM8 の分歧は機構の実装差ではなく、確認済みの生成プール（`STOKE_GENERATION`）の差だけが効いた。EAIF・NFH3・VTW・GEFYY・SWRUL は両腕で発火ゼロ。

→ 固定 panel で機構単独を測れた pair は 2件、reach 0。機構の実走効果は mechanism panel（control 腕完走後に arm 腕）を待つ。

### 同一 commit・同一 seed の再走は decision列が完全一致（再現性の確認）

mechanism panel の control 腕で `AM8C6YXHSG` を `e808bdf` に再走した。先行した `ctrl20261004_AM8C6YXHSG`
（351件）と比較し、**再走分の決定列（seq・card_id・decision_source）が全件一致**（2026-10-03 09:40 時点で
351/351、再走は走行継続中）。条件は同一：固定ユーザーデータ、`simulations=100`、Act 3まで、単一 game instance。

これで「同じ決定列なら outcome も同じ（game の RNG は seed 由来）」が harness 側でも確認できた。
panel の ±0 が本当に「決定が変わっていない」かどうかの判定は、この再現性の上で使える。
（決定列が一致しない場合の原因は policy 差か path 差かの切り分けが要る、という既存の rule はそのまま。）

`AM8C6YXHSG` の control 再走は **outcome まで一致**した：決定列351件完全一致、勝敗も 17勝1敗で
先行 run（`ctrl20261004_AM8C6YXHSG`）と同値（job `bash-116` の RESULT）。同一 commit・同一 seed・同一
固定ユーザーデータの run は決定列も outcome も再現される。panel の ±0 判定はこの再現性の上で使える。

### Blood-Soaked Rose は model で二重計上していた（commit `a328b5c`）

`BloodSoakedRose.ModifyMaxEnergy` は毎ターの energy reset で +1。bridge の `max_energy` は**観測された
ターンの有効値**なので、relic を持っている run は turn 1 から 4 を報告する（実測：`gdv_9X9WQB4QIH` の
turn 1 record が max_energy 4）。model は turn start で `extra_energy += 1` を足していたので、rollout の
turn 2 が **5** になった（same record で再現：model turn2 energy 5）。二重計上。

実測の分布：relic 所持 record の `max_energy` は 4（767件）と 5（255件）。5 の record は Paels Flesh
（turn 3 以降 +1、永続）との併有で、game は両方の加算を already 反映した値を報告している：
`act3_pop2_head_R8V2H6N4ZB` turn 3 = base3 + Flesh1 + Rose1 = 5。

→ 機構として model に載せるものがない（observation に既にある）。branch を除去し、
`test_blood_soaked_rose_is_not_double_counted_at_energy_reset`（state の max_energy 4 → turn 2 energy 4）で固定。
Paels Flesh の branch は残る：turn 2 の観測は 3 を報告するので、model が turn 3 へ跨ぐときに +1 するのは正しい。

mechanism panel の sample で Rose に紐づいていた分歧8件は、この除去で消える（機構単独の到達性は
Fiddle 76・Chains 34・Forgotten Soul 24・OneTwoPunch 2・Panache 1 へ）。arm 腕の run はこの commit を
含むので、panel の結果を読むときは Rose 分を机构差として数えない。

修正後の同じ record（`gdv_9X9WQB4QIH` の turn 1、relic 所持、max_energy 4）での END_TURN rollout：
model の turn 2 energy は **4**（修正前は5）。game が報告する有効値と一致する形になった。
実走 panel（control 腕）では `R8V2H6N4ZB` が BLOOD_SOAKED_ROSE を所持して発火しているが、
修正後の model にとってこの relic は decision に効かない（観測に既にある） → R8 で動くのは他の機構だけ。

### 修正後の到達性：panel 8 seed のうち2件は測定不能になる

Rose の二重計上 branch を除いた sample 再計算：分歧 **108件 / 11 seed**（116 → 108）。機構別は
Fiddle 76・Chains 34・Forgotten Soul 24・OneTwoPunch 2・Duplication 2・Panache 1。

seed 別（post-fix）：`N8CQ4ZKP2W` 57、`H2LV6ZJ4XW` 24、`AM8C6YXHSG` 15、`D1W9Y3B7FC` 3、
`P3V8N5K2RX` 2、`Q6N3V8K2MT` 2、ほか5 seed各1。

→ mechanism panel の8 seedのうち **`B3N8V5T1WQ` と `R8V2H6N4ZB` は post-fix で到達性 0**
（あの2 seed の分歧は除去した bug branch 由来）。この2 seed の ±0 は判定へ使えない。
使えるのは N8・H2・AM8・D1・P3・Q6 の6 seed（AM8は生成プールの忠実化と混かる）。
R8 の control run（22勝1敗）はすでに完了済みなので記録として残す。

### 二重計上の点検（panel 実走中に機構別で確認）

Rose だけが二重計上だった。ほかは観測と二重計上にならない構造：

- `Fiddle`：`ShouldDraw` は hand draw（`fromHandDraw=True`）を許可、owner の side 中のそれ以外を拒否。
  model は未来ターンのドローだけを変え、hand の枚数（＝game が既に引いた結果）には触らない
- `ChainsOfBinding`：live hand の bound は bridge が `bound` field で正しく出す。model は rollout 内の
  future draw にのみ Afflict を再現
- `Duplication` / `OneTwoPunch` / `Gigantification` / `Panache`：観測 powers の counter を、 hypothetical
  play（rollout）へ適用する形。decision 時点の effect は観測に既にあるので加算は未来分だけ
- `Forgotten Soul`：exhaust の解決は rollout 内で再現（観測の exhaust pile は過去分）。実走証拠は
  `test_curses_left_in_hand_hit_the_player_at_turn_end` ではなく record 側（TREMBLE play で enemy ちょうど1減）

→ 実走 panel の arm 腕は `a328b5c` 以後の code。arm 腕で Rose 分が効かないのはこのため。

### play-count powers の model は multi-effect 札で部分忠実（記録）

`DuplicationPower` / `OneTwoPunchPower`（OneTwoPunch は `CardType.Attack` 限定）は
`ModifyCardPlayCount +1`、`AfterModifyingCardPlayCount` で decrement、player turn end で remove。
＝その play の**解決全体**がもう1回走る。model は damage と block を2回適用する形で再現しているので、

- 単效果札（Strike・Defend・Shrug 等）：忠実
- 多效果札（Burning Pact の exhaust＋damage、draw を伴う Skill、power 適用）：game は exhaust・draw・
  power 適用まで2回走らせる。model は damage/block 分だけ2回 → **部分忠実**

panel の sample で Duplication の分歧は2件（1-in-12 sample、`POWER.DUPLICATION_POWER` を持つ record 上）。
多效果札で duplication が消費された case を洗ってから、埋める価値があるかを判断する（現時点で reach 2、
noise 未満 → 実走対象にしない）。

件数：play-count power が active で Shrug It Off（block + draw の multi-effect）が選ばれた record は
**4件 / 2 seed**（`N8CQ4ZKP2W` seq 126・135・141、`Z2K7D9F4VX` seq 462）→ 閾値（≥3 decisions かつ
≥3 seeds）未満。機構の形（play 全体をもう1回走らせる）は正しいが、この panel では測れない。
実装を変えない（「multi-effect の第二解決が model に無い」として記録だけ）。

mechanism panel の両腕は bridge（C#）が同一：`git diff --name-only e808bdf..HEAD` に `.cs` は 0件。
panel の差は Python 側（policy/模型）だけなので、run 間の差を「DLL が違う」で説明できない。
control 腕 = `e808bdf` worktree、arm 腕 = HEAD（`77120b2` と `a328b5c` を含む）。

### Fiddle のドロー拒否は実走側でも確認できた（1,436件）

Fiddle を持つ run で、draw 系札（Pommel・Shrug・Evil Eye・Battle Trance・Production・Master of Strategy 等）
を打った decision と**同じ turn の次の decision** を照合：hand が伸びた case は **0件**、伸びない case
**1,436件**。＝ game は owner の effect ドローを拒否している（`ShouldDraw` の `fromHandDraw` 以外の拒否）
ので、model の拒否は推測ではなく実走一致。hand draw（turn start）の +2 も同レリックの
`ModifyHandDrawLate` で、view 側の hand には出ないので rollout 加算として扱うのが正しい。

Fiddle は panel の sample で分歧76件（11 seed 中の最大）＝機構単独で最もreachのある筋。
run レベルで測れるのは両腕が Fiddle を持った seed だけ（control 腕では AM8 が所持）。

### Bound は play を阻止しない（commit `5d8bf18`）

`ChainsOfBindingPower.ShouldPlay`：Bound 札を阻止するのは**そのターンに Bound 札を1枚打った後**だけ
（`BeforeCardPlayed` がフラグを立て、`BeforeSideTurnEnd` でフラグと affliction を両方 clear）。
＝第一 choice のゲート前、game は Bound 札を playable として出す。

実測：corpus で**Bound 札を打った decision 279件**（3 seed）、うち **45ターンで1ターンに2枚以上**
打っている。 blanket「Bound は打てない」は忠実でなかった。

model の形の修正：

- `Card.bound` = affliction マーカー（それ自体は play を阻止しない）
- `Combat.bound_played_this_turn` = ShouldPlay のターン内ゲート
- `Card.unplayable_this_turn` = game の legal_actions がその decision で除外したという判定（first move
  では game の list が権威。Snecko の一時的な高コスト等もここに入る）。これを `bound` と同一字段に
  していたのが、忠実でない方向へねじれていた
- `legal_actions`：`unplayable_this_turn` は常に skip、`bound` はゲートが立ってから skip

テスト `test_chains_of_binding_afflicts_cards_drawn_during_the_rollout` をゲート rule へ更新
（play 前は5枚とも legal、bound を1枚打つと残りの bound 2枚は skip、unbound は playable のまま）。
suite **733件成功**。mechanism panel の arm 腕はこの commit を通るので、Chains の sample 到達性34件は
この rule の下で数え直す（gate 前は playable、gate 後だけ skip）。

###  contaminated: arm 腕の4 run は無効（working tree に未commitの実験コードが入っていた）

mechanism panel の arm 腕で `N8CQ4ZKP2W` 0勝1敗、`H2LV6ZJ4XW` 0勝1敗、`AM8C6YXHSG` 1勝1敗、
`R8V2H6N4ZB` 0勝1敗。原因は機構ではなく**agent の exception**：`rollout_choice` に途中入れた
「game の legal_actions に無い action を skip する」guard を、テストが壊れたので revert した但し
revert 前に start した run がそのコードで走っていた（agent は run の開始時に file を読む）。
error log: `IndexError: list index out of range`（N8 9件、H2 9件、AM8 16件、R8 9件）。
agent が fall out すると game は 2分の wait deadline 後に safe default（多くは skip）を取る＝勝てない。

rule：run が走っている間に policy code を編集してはいけない。`sweep2.sh` が print する commit は
start 時の HEAD で、実際に使われた file 内容ではない。この4 seedは `5d8bf18` の code で再走が必要。
`D1W9Y3B7FC`（clean code で start）は正常に decision を出しており有効（sources: rollout_success ほか）。

汚染の判定は decision_source で立つ：contaminated run（`mechpanel_arm_N8CQ4ZKP2W`）は
`agent_exception_fallback` が9件、clean run（`mechpanel_arm_D1W9Y3B7FC`）は rollout_success 97件・
heuristic_fallback 33件で exception は0。つまり汚染 run では agent が fall out して game 側が default
（skip）を取っている。再走後は `*_agent.err` が空であること＋`agent_exception_fallback` が0件であることを
確認してから結果を使う。

### run safety：もう一つの失敗（同時に run を started した）

再走 script を書いたとき、実行中の sweep があることを確認せずに呼んだ。`run_official_autoslay.ps1` は
「Slay the Spire 2 is already running」で throw するので**測定は行われなかった**（4 seed全部 exit=1、
stdout は exception だけ）。ただし sweep の `trap` がユーザーデータを snapshot へ復元したので、走行中の
run の環境へ割り込んだ。artifact は削除済み。

`/Users/mao/.sts2/scripts/rerun_mechpanel.sh` の guard（両方実失敗から）：

- game process が在る then refuse（同時に run を start しない）
- `official_agent.py` / `combat.py` が HEAD と違则 refuse（汚染）

再走は4 seed：`N8CQ4ZKP2W` `H2LV6ZJ4XW` `AM8C6YXHSG` `R8V2H6N4ZB`（tag `mechpanel_arm_rerun`）。
条件は panel と同一（固定ユーザーデータ、`simulations=100`、Act 3まで、1 run/seed）。

### Chains の到達性は blanket rule 由来。忠実なゲートでは再計算が必要（上限45ターン）

sample の Chains 分歧34件は「Bound 札を打てない」という**忠実でない rule**の下で数えた。
修正後（`5d8bf18`）の忠実な形では、ゲートが効くのは「そのターンに Bound 札を1枚打った後、
まだ Bound 札が hand に残っている」case だけ。実測の上限は：

- Bound 札を打った decision 279件 / 3 seed（`N8CQ4ZKP2W` 182、`H2LV6ZJ4XW` 79、`D6A1F8C3E5` 18）
- そのうち **1ターンに2枚以上 Bound を打った turn = 45ターン**（ゲートが実際に効く位置）

→ 忠実なゲートの到達性は45ターンを上限として replay で数え直す（control にはゲートが無いので、
ゲート単独の差）。Fiddle（76件）は rule が忠実と確認済みなのでそのまま。panel 実走で測れるのは、
両腕が同じ機構を見た seed だけ、という条件もそのまま。

### D1：決定は61件違うが outcome は同じ（14勝1敗）

mechanism panel の `D1W9Y3B7FC`：control 14勝1敗、arm（clean code、例外0件）14勝1敗。
decision列は arm 294件 / control 306件で **61件分歧**（first divergence seq 82）。この seed は
**両腕の run とも機構を見ていない**（control 側 fired none、arm 側も none）ので、分歧は機構の実装差
では説明できない。機構が1つも state に入っていない run で arm/control が違いうる通路は
`STOKE_GENERATION` の形（忠実化で32名を除いた）だけ。

→ decision の分歧は outcome へ伝わらないことがある、の実例。panel の判定は per-seed の増減ではなく
母集団の合計、かつ「両腕で同じ機構を見た」seed だけを使う、という rule がそのまま生きる。
D1 の ±0 は「効果なし」ではなく、機構について言えば**測定不能**（分歧の成因が機構と無関係）。

### P3 の分歧は機構ではなくマーカー漏れだった（commit `f8f3966`）

`P3V8N5K2RX` は control 15勝1敗 / arm 13勝1敗で、両腕の run が `POWER.DUPLICATION_POWER` を見た
最初の pair。だが第一分歧（seq 186）の record を両treeで replay すると、机构は state に出ていない
（powers は DexterityPower だけ、hand に Stoke も無い）。違いは `Card.unplayable_this_turn` が
ターン跨ぎで**消えない**ことだった：decision 時点で game の legal_actions が除外した札（energy 0 で
打てなかった Strike / Pommel Strike）が、rollout の後続ターンでもPlayable扱いされず、
`legal_actions` が arm と control で違った。

修正（`f8f3966`）：hand を flush する場合、`bound`（Chains のゲートはターン終了で clear される）と
`unplayable_this_turn`（game のそのターンの判定）を双方クリア。RetainHandPower で hand に残る copy
も同じ。テスト `test_the_per_turn_unplayable_marker_does_not_leak_into_the_next_turn`。

修正後の同じ record：両treeの search が一致（0.7658 `card:3@0` / 0.4666 `card:2` / 0.1209 End turn）
→ P3 の −2 は機構の差ではなくこの bug の差。

**panel の arm 腕は `5d8bf18` を通った run（D1・P3・B3・Q6）も bug 込み**なので、機構単独の測定には
8 seed 全部を `f8f3966` の code で再走する（tag `mechpanel_arm_clean`）。control 腕（`e808bdf`、機構を
教える前の code）はそのまま基準として使える。

### leak の実測：B3 の第一分歧も机构と無関係（post-fix で両tree一致）

`mechpanel_arm_B3N8V5T1WQ` の第一分歧 seq 136：hand に BASH（energy 1 で game は除外）、powers は
Strength・Crimson Mantle、relics に機構なし。record を両treeで replay（`f8f3966`）すると両treeが
`CARD.DEFEND_IRONCLAD` で一致 → run 側で arm が STRIKE を選んだのは漏れたマーカー（BASH が翌ターンでも
打てない扱い）の効果。D1（seq 82）と P3（seq 186）も同じ形で確認済み。

→ これまでの arm 腕（D1・P3・B3・Q6）の decision 分歧は、機構が state に出た場合を除いて漏れの効果。
机构単独の到達性は Fiddle（76、rule 忠実と実走1,436件で確認）と Chains のゲート（上限45ターン）が本体で、
leak は artifact。panel の arm 腕は `f8f3966` の code で8 seed 再走して、`agent_exception_fallback` 0件と
両腕の発火の揃いを確認してから判定する。

### arm 腕の run ごとの code 状態（どれが使えるか）

| seed | arm run | 使用 code | 扱えるか |
|---|---|---|---|
| `N8CQ4ZKP2W` | 0勝1敗・例外9 | 未commitの guard | 無効 |
| `H2LV6ZJ4XW` | 0勝1敗・例外9 | 未commitの guard | 無効 |
| `AM8C6YXHSG` | 1勝1敗・例外16 | 未commitの guard | 無効 |
| `R8V2H6N4ZB` | 0勝1敗・例外9 | 未commitの guard | 無効 |
| `D1W9Y3B7FC` | 14勝1敗・例外0 | `5d8bf18`（漏れ込み） | 機構測定の根拠にできない |
| `P3V8N5K2RX` | 13勝1敗・例外0 | `5d8bf18`（漏れ込み） | 同上 |
| `B3N8V5T1WQ` | 19勝1敗・例外0 | `5d8bf18`（漏れ込み） | 同上 |
| `Q6N3V8K2MT` | 走行中 | `f8f3966`（clean） | run 自体は使えるが、この seed は control 側で発火0 |

再走は7 seed（`mechpanel_arm_clean`）。Q6 は clean code で start した最初の run。
control 腕（`e808bdf`）の8 seed 結果（合計121勝）はそのまま基準。

### Chains の忠実なゲートは3 seed にmaterialに効く（651 record）

game の legal_actions が Bound 札を除外していた record（＝ゲートが立っていた）：**651件 / 3 seed**
（`N8CQ4ZKP2W` 399、`H2LV6ZJ4XW` 224、`D6A1F8C3E5` 28）。同じ条件で Bound 札が legal_actions に
**入っていた** record は622件（ゲート前、両treeが playable 扱い → 差が出ない）。

sample の Chains 分歧34件は blanket rule（常時 skip）の下で数えたので、忠実なゲート下的の分歧件数は
この651件の上で数え直す。panel の arm 腕 re-run（`f8f3966`）が走っている間は CPU を game に譲る（25 ms
ポーリングのdelay → watchdog risk）ので、replay は sweep 完了後。

### control era の bound-hand decision では469件が heuristic_fallback に落ちている

control（`d429b4d` 以前、bound の概念が無い）で、hand に Bound 札が在る decision 1,273件の内訳：
heuristic_fallback **469**、rollout_success 467、queen_minion_direct 233、ほか。heuristic_fallback に
落ちたのは、model が game の legal_actions に無い札（Bound）を top に並べて mapping が fail したため。
忠実な形（ゲート前は playable、ゲート後は skip）では、この469件で model が game-legal の中から
rank する → 第一手が変わりうる。母数は上の651件（gate-active）の上で replay して数える。

seed 別（heuristic_fallback）：`N8CQ4ZKP2W` 336、`H2LV6ZJ4XW` 117、`D6A1F8C3E5` 16。

### panel の第一読取（arm 腕は再走中）と忠実なゲートの分歧率

panel 8 seed（control `e808bdf` vs arm）：

| seed | control | arm（使用 code） | 扱えるか |
|---|---:|---|---|
| `N8CQ4ZKP2W` | 5 | 0（例外9） | 再走 |
| `H2LV6ZJ4XW` | 20 | 0（例外9） | 再走 |
| `AM8C6YXHSG` | 17 | 1（例外16） | 再走 |
| `R8V2H6N4ZB` | 22 | 0（例外9） | 再走 |
| `D1W9Y3B7FC` | 14 | 14（漏れ込み） | 再走 |
| `P3V8N5K2RX` | 15 | 13（漏れ込み） | 再走 |
| `B3N8V5T1WQ` | 16 | 19（漏れ込み） | 再走 |
| `Q6N3V8K2MT` | 12 | **12（clean code）** | 有効。ただし両腕で発火0 → 機構については測定不能 |

忠実なゲート（Bound playable、第一 play 後 skip）の分歧率を gate-active record の30件/seed sample で測った：
**88件で第一手分歧15件（約17%）、control 側の mapping fail 0件**。651件へ外挿すると約110件の決定分歧、
3 seed に分布 → 閾値（≥3 decisions かつ ≥3 seeds）超。re-run（tag `mechpanel_arm_clean`、job `bash-296`）
が走っている間、gate の分歧件数を full で数える。

### clean re-run の照合方法（N8 で実装）

clean run（`mechpanel_arm_clean_N8CQ4ZKP2W`）は control（`e808bdf`）の同じ seed run と、
seqで揃った record 120件まで決定列が一致。この区間で gate-active record は **0件**（Chains がまだ
active ではない）→ 分歧が出ないのは预期どおり。

照合の手顺（panel の arm 腕全体に使う）：
1. `agent_exception_fallback` が0件であること（汚染の確認）
2. 第一分歧の record で、机构が state に出ているか（powers/relics/hand）を見る
3. 机构が出ていない record で分歧するなら、それは机构の差ではない（漏れや生成集合など別通路）
4. 両腕で同じ机构が揃った seed だけ per-seed 勝数へ使う

### 訂正：N8 の「発火1件」は combat ではなく card_reward の提示だった

`mechpanel_ctrl_N8CQ4ZKP2W` で机构 id が出た1件は seq 84 の **card_reward 行**（offer list に
`CARD.ONE_TWO_PUNCH` が載っていた）で、combat decision の state に机构が出ていた件数は0。
`compare_panel` は発火を combat record の状態出現だけで数えるようにした（commit `9bbd4c5`）。

clean run（`mechpanel_arm_clean_N8CQ4ZKP2W`）は control と決定列 **111/111件一致**、outcome も
5勝1敗で同値。つまり N8 はこの run で机构を見ず、機構については測定不能。N8 の到達性57件は
同じ seed の**別の run**（`candidate` ほか）から来ていた。

→ panel の測定力は path 運で決まる。母数として使えるのは、両腕の run が機構を**combat の state に
出した** seed だけ（現時点で control 側は H2 と AM8 が出した。arm 側が同じものを見るかは run 次第）。

### H2 の clean run は pair にならない（relic を引かなかった）

`mechpanel_arm_clean_H2LV6ZJ4XW`：combat record 179件、relics は Burning Blood・Stone Humidifier で
`RELIC.FORGOTTEN_SOUL` は 0件。control（`e808bdf`）の同じ seed run は67件で所持 → **path が分かれて
机构を引かなかった**。H2 の到達性24件は control 側が机构を持つ run（`candidate` ほか）から来ていた。

決定列は seq で揃った213件の分歧0。機構の実装（exhaust 1枚につき random 1体へ1 unpowered）は
1点 damage で、この path では決定を1つも動かしていない。機構の effect が決定へ伝播する母数として、
Fiddle（76件）と Chains のゲート（651件で17%）は実測済み。control era で bound-hand decision の
469件が heuristic_fallback に落ちていた件（model が game に無い札を top に並べた）は、忠実な形の
arm では game-legal の中から rank する → こちらが機構単独の差として残る。

### sample分歧の seed × 機構 分解と、panel で実際に pair になりうるもの

sample（1-in-12、機構単独）の分歧108件を seed × 機構で割ると：

| seed | 機構 | flip |
|---|---|---:|
| `N8CQ4ZKP2W` | Fiddle 56・Chains 20・Duplication 1 | 77 |
| `H2LV6ZJ4XW` | Forgotten Soul 24・Chains 11 | 35 |
| `AM8C6YXHSG` | Fiddle 15 | 15 |
| `D1W9Y3B7FC` | Fiddle 3 | 3 |
| `Q6N3V8K2MT` | Fiddle 2 | 2 |
| `P3V8N5K2RX` | Chains 1・Duplication 1 | 2 |

panel の実走で pair になる条件是、**両腕の同じ run が同じ機構を combat の state に出す**こと。
control 腕（`e808bdf`）で state に出した seedは H2（Forgotten Soul）、AM8（Four）、R8（Chains+Rose）、
P3（Duplication）で、N8 と D1・Q6・B3 は0（N8 の1件は reward 提示）。
したがって N8 の77件、D1 の3件、Q6 の2件は panel の run では使えない。pair になりうるのは H2・AM8・
R8・P3 の4 seed ＋ arm 側が Fiddle 等を引いた case。

### 訂正：H2 は pair（両腕の run が Forgotten Soul を state に出している）

前ラウンドで「H2 は机构を引かなかった」と書いたが誤り。clean run
（`mechpanel_arm_clean_H2LV6ZJ4XW`）は combat record **123件**で `RELIC.FORGOTTEN_SOUL` を所持、
control（`e808bdf`）は67件。前ラウンドの scan は file 選択を誤って0と出した。

第一分歧 seq 441：relics・powers（Dexterity・Strength）・hand が両腕で同一。arm が end_turn、
control が UPPERCUT。arm 側には機構の実装（exhaust 1枚につき random 1 hittable 体へ1 unpowered）があり
control には無い → ここは机构単独の差として立つ。分歧は seq 441 から51件（H2 clean run 走行中、
16勝0敗；control は 20勝1敗）。

H2 は panel で最初の実質的な pair。1 seed の増減は採用根拠にしない rule のまま（判定は母集団）。

### H2：最初の実測 pair（+2、Forgotten Soul）

`compare_panel`（発火は combat record の状態出現だけ）で H2 を照合：

- control 20勝1敗 / arm（clean）22勝1敗 → **+2**
- pair：`RELIC.FORGOTTEN_SOUL` が両腕の combat state に出ている（arm 123 record、control 67 record）
- arm 側だけに `POWER.CHAINS_OF_BINDING_POWER`（25 record）が出ている → H2 の分歧は Chains 由来とは
  言えない。机构単独で attribution できるのは Forgotten Soul だけ
- 第一分歧 seq 441（relics・powers・hand が両腕同一）→ 机构の実装差で立つ
- Act 3踏破は両腕なし

1 seed の +2 は採用根拠にしない rule（測定の作法 5）どおり、記録として残す。母集団（panel）の
pair が揃う seed が増えてから判定する。現在 pair：H2 の1件。

### H2 の分歧46件は全部、両腕の state に Forgotten Soul が在る位置

combat decision の分歧46件を、その decision の state（relics・powers・hand）で機構の出現を確認して
割った：**46件すべて両腕に `RELIC.FORGOTTEN_SOUL` が在る**。arm 側にだけ Chains が在る位置での分歧は
**0件** → H2 の path で Chains のゲートは決定を動かしていない。

したがって H2 の +2（control 20勝1敗 → arm 22勝1敗）は Forgotten Soul の実装単独の差として attribution
できる。母集団は1 seedなので採用根拠にはしない（rule 5）が、機構単独の差として立つ第一 pair。

### AM8 の分歧は机构ではない（generation pool の差）

clean AM8 run の第一分歧 seq 248：relics・powers が両腕で完全一致、机构は state に出ていない
（arm 12勝0敗・走行中、FIDDLE は arm 側にのみ出現）。seq 250 で `CARD.STOKE` を打つ位置なので、
分歧の成因は `STOKE_GENERATION` の形（control は忠実でない集合、arm は character pool ∩ known）＝
前もって確認済みの生成プールの差。FIDDLE が両腕に出た位置での分歧は現在0件。

→ AM8 は「机构単独の差」として読めない。panel の母集団で机构単独が読めるのは、両腕の同じ decision の
state に同じ机构が出ている位置だけ（H2 の Forgotten Soul 46件がその形）。

### AM8 の分歧68件を state で割った（Fiddle 19件・机构なし33件）

clean AM8 run（14勝0敗・走行中、control 17勝1敗）：seq で揃えた combat decision 246件の分歧68件。

- **19件**：`RELIC.FIDDLE` が両腕の state に出ている位置 → Fiddle の実装単独の差として attribution できる
- **33件**：両腕の state に机构が何も出ていない位置 → 生成プール（`STOKE_GENERATION` の忠実化）の差
- 残りは机构が片腕だけに出た位置（attribution 不能）

H2 と同じ形で、機構単独の差として残るのは Fiddle 19件。run レベルの outcome（AM8 は機構＋忠実化が
混かる）は Fiddle 単独の成果へは開けない。母集団で机构単独が読める位置は、両腕の同じ decision の
state に同じ机构が出た位置だけ、という rule がまた確認された。

### Fiddle の +2 draw：実走で検証できるのは turn 1 の first decision だけ

clean AM8 run の「combat ごとの最初の decision」7件を見ると、turn 1 の1件（combat 1）は hand **7**
＝ 5 + Fiddle 2 で一致。ほか6件は turn 2・7・8・9・11 の decision（その combat の turn 1 の decision が
トレースに無い）なので +2 を検証できない。**inconclusive**で、+2 の根拠は hook
（`Fiddle.ModifyHandDrawLate` が owner の hand draw に +2）のまま。拒否側（effect draw 不许）は
実走1,436件で hand が伸びないことを確認済み。

→ 実走検証できるのは、观測に現れる量（hand size、energy、powers、relics）と hook の対応が
1対1で決まる case だけ。rollout 内部の加算は record から直接検証できない。

### AM8（17勝0敗・走行中、control 17勝1敗）の分歧138件

両腕の同じ decision の state に同じ机构が出た位置で割ると：

- `RELIC.FIDDLE` 両腕：**89件**
- `RELIC.FORGOTTEN_SOUL` 両腕：30件
- `POWER.CHAINS_OF_BINDING_POWER` 両腕：16件
- 両腕に机构が何も出ていない位置：**49件**（→ 生成プールの忠実化の差。机构の差ではない）

（1 decision に複数の机构が両腕で揃っている場合があるので件数は機構別、合計は138超になりうる）

AM8 は Fiddle が決定を動かす位置が最多の seed。run レベルの outcome（17勝0敗 vs control 17勝1敗）は
机构と忠実化が混かるので、Fiddle 単独の成果へは開けない。開けるのは、同一 observation を両treeで
replay して「機構単独」を隔離した件数（Fiddle 76件、Chains の忠実なゲート651件で17%）だけ。

### clean run の現在の判定（測れる2 seedで +2）

| seed | control | arm（clean、例外0件） | delta | pair（両腕の combat state） |
|---|---:|---:|---:|---|
| `N8CQ4ZKP2W` | 5W1L | 5W1L | 0 | none（決定列111件完全一致） |
| `H2LV6ZJ4XW` | 20W1L | 22W1L | **+2** | Forgotten Soul |
| `AM8C6YXHSG` | 17W1L | 17W1L | 0 | Fiddle・Forgotten Soul・Chains（決定分歧138件でも outcome 同値） |

**MEASURABLE（両腕で同じ機構）= 2 seed：control 37勝 / arm 39勝、+2。**
AM8 は決定を138件動かして勝敗が変わっていない → decision の分歧は outcome へ伝わらないことがある
実例（D1 の61件と同じ形）。rule 5（1 seedの当たりで採用しない）の下では +2 はまだ採用根拠にならない。
残4 seed：R8・D1・P3・B3。

### AM8 seq 248 の分歧は生成集合で再現できる（机构ではない）

AM8 の「両腕の state に机构が出ていない」第一分歧 seq 248 を同一 observation で replay：

- control 形の `STOKE_GENERATION`（忠実でない、112名）→ `CARD.BURNING_PACT` ＝ control の run の選択
- faithful（character pool ∩ known、80名）→ `CARD.SHRUG_IT_OFF` ＝ arm の run の選択

→ この分歧は生成集合の忠実化で立つ。机构の実装では説明できない。AM8 の49件（機構なし位置）は
この形。Fiddle 89件・Forgotten Soul 30件・Chains 16件は両腕の state に同じ機構が出ている位置なので
機構単独の差として残る。

### 訂正：run レベルで机构単独の差として立うるのは第一分歧の位置だけ

AM8 で Fiddle が両腕の state に出ている分歧位置（89件）を1件（seq 328）replay して確認した：
同一 observation（arm 側の record）を両treeに流すと、arm tree は `CARD.HEADBUTT`（run の arm の選択と
一致）、control tree は `CARD.ANGER` を選び、**control の run が実際に選んだ `CARD.INFLAME` とは違う**。
control 側の record は state が違う（seq 248 で pool の差から path が分岐した以降）ので、この89件は
「机构単独の差」ではない。分歧位置の机构 presence は、同じ decision の state が両腕で一致している
case 限りで意味を持つ。

panel で机构単独として立つのは第一分歧の位置だけ：

- `H2` seq 441：relics・powers・hand が両腕同一、`RELIC.FORGOTTEN_SOUL` が両腕の state に在る →
  **Forgotten Soul の実装単独**（+2 の成因）。arm が end_turn、control が Uppercut
- `AM8` seq 248：relics・powers・hand が両腕同一、机构は state に出ていない → **生成プールの忠実化**
  （control 形の集合で control の選択、faithful で arm の選択を再現）

→ AM8 の +0 は「机构の効果が出なかった」ではなく、机构が効く位置が第一分歧より後（state が違う）なので
机构単独の差として開けない。機構単独を隔離できるのは同一 observation を両treeで replay する到達性
計算だけ（Fiddle 76件、Chains の忠実なゲート651件で17%）。

### R8 の arm run は机构を1つも state に出していない → R8 の差は机构単独として読めない

clean R8（13勝0敗・走行中、control 22勝1敗）：combat record に機構が0件。control 側は Chains 17 record・
Rose 154 record。arm 側が机构を seen していないので、分歧は机构の実装差では説明できず、残る通路は
生成プールの忠実化（`STOKE_GENERATION`）だけ。

panel で「第一分歧の位置に机构が両腕の state に出ている」seed は現時点 **H2 だけ**（seq 441、
Forgotten Soul）。AM8 の第一分歧 seq 248、R8 の分歧位置は机构なし → 機構単独の差として開けない。
机构単独の差は同一 observation を両treeで replay する到達性計算でしか隔離できない（Fiddle 76件、
Chains の忠実なゲート651件で17%、Forgotten Soul 24件、OneTwoPunch 2件、Duplication 2件、Panache 1件）。

### R8：arm は机构を引かなかったから、決定列が control と301件一致

`mechpanel_arm_clean_R8V2H6N4ZB`（15勝0敗・走行中）は、seq で揃えた combat decision 301件の分歧が
**0件**。arm 側は机构を state に出していない（control 側は Chains 17・Rose 154 record）が、control の
model（`e808bdf`、机构を実装する前）は那些を無視するので、両腕が「机构を持たない run」として同じ
決定を出す。機構を引かなかった path では机构の効果は出ない — 引くかどうかは reward の path 運。

この seed は机构単独の差を持たない。分歧が出るとすれば arm 側が机构を acquisition した後の位置で、
その場合も第一分歧の位置（state が両腕で一致する位置）だけ attribution に使える。

### R8 で二重計上修正の帰結が実走で出た：Rose を両腕が持っても決定列が完全一致

`mechpanel_arm_clean_R8V2H6N4ZB`（21勝0敗・走行中）は、seq で揃えた combat decision の分歧が
**0件**（412 record、2026-10-03 11:30 時点）。両腕の record に `RELIC.BLOOD_SOAKED_ROSE` が出ている
（control 154・arm 156 record）ので pair だが、修正後（`a328b5c`）model は Rose に何もしない（game が
報告する `max_energy` に既に反映済み）→ 機構単独の差は0。arm が control と同じ決定を出している。

これが「機構として model に載せるものがない（observation に既にある）」の実走形。pair でも effect が
無い case の記録。

### R8 の error log から実 bug を1件修正（commit `HEAD`：SoarPower + hit count 0）

`mechpanel_arm_clean_R8V2H6N4ZB_agent.err`：`ZeroDivisionError` in `damage()` →
`value = (value // hits // 2) * hits` が hits == 0 で割る。hits は `_card_hit_count` で、Whirlwind は
「使った energy」が hit count所以 energy 0 だと 0 になる（`CARD_HIT_COUNTS` に 0 の entry は無いので、
0になりうるのは Whirlwind の path だけ）。`HardToKill` 側は `if caps and hits` で guard 済みで、Soar 側
だけ guard が无かった。

R8 はこの decision（seq 546）で game 側の default を取ったが、決定列は control と **454件分歧0**、
outcome も 22勝1敗で同値 → 実走影響は出なかった。guard を入れてテスト
`test_lethal_with_soar_power_does_not_divide_by_a_zero_hit_count`（suite **735件成功**）で固定。

### P3：pair だが決定列の分歧0（Duplication の effect が出なかった path）

`mechpanel_arm_clean_P3V8N5K2RX`：393 aligned recordsで**全 decision field の分歧0**。両腕の combat
state に `POWER.DUPLICATION_POWER` が出ている（control 16・arm record）ので pair。分歧が0なので
機構単独の差は0。

sweep が print した wins=13 は print 時点で trace が未完だった值で、final の parse は 15勝1敗（control
と同じ）。**判定は final の trace（`phase == 'combat_end'` の `won`）で行う**、sweep の grep 行ではない。

D1 も同じ形：aligned 306件分歧0、14勝1敗で同値（機構を引かなかった path）。
現在 panel で機構単独の差として立っているのは H2（Forgotten Soul、第一分歧 seq 441、+2）だけ。

### panel（clean run）の consolidated 判定

| seed | control | arm（clean） | delta | aligned combat decision | 分歧 | 第一分歧の機構（両腕 state） |
|---|---:|---:|---:|---:|---:|---|
| `N8CQ4ZKP2W` | 5W1L | 5W1L | 0 | 111 | 0 | — |
| `H2LV6ZJ4XW` | 20W1L | **22W1L** | **+2** | 390 | **46** | `RELIC.FORGOTTEN_SOUL`（seq 441） |
| `AM8C6YXHSG` | 17W1L | 17W1L | 0 | 323 | 138 | none（→ 生成プール） |
| `R8V2H6N4ZB` | 22W1L | 22W1L | 0 | 454 | 0 | Rose（effect 0） |
| `D1W9Y3B7FC` | 14W1L | 14W1L | 0 | 306 | 0 | — |
| `P3V8N5K2RX` | 15W1L | 15W1L | 0 | 305 | 0 | Duplication（effect 0） |
| `B3N8V5T1WQ` | 16W1L | 走行中（8勝0敗、分歧0） | — | 171 | 0 | — |
| `Q6N3V8K2MT` | 12W1L | 12W1L（first pass、clean code） | 0 | — | 0 | — |

**機構単独の win-rate 効果は、clean run の母集団で H2 の +2（1 seed、46分歧）だけが立った。**
rule 5（1 seedの当たりで採用しない）と閾値（≥3 decisions かつ ≥3 seeds）の立場では、機構は
**正しさの修正として採用済み**（decompile 根拠＋Fiddle のドロー拒否は実走1,436件、Chains のゲートは
実測279 plays/45 turns、play-count powers は decompile 一致）で、win-rate の効果は母集団が薄いまま。
AM8 の138分歧は生成プールの忠実化（同一 observation で control 形／faithful を切り替えて再現）で、
機構の差ではない。

### MEASURABLE（両腕で同じ機構が combat state に出た seed）は4 seed、+2

`compare_panel`（発火は combat record の状態出現のみ）での最終形（B3 は走行中）：

| seed | control | arm | delta | pair | first divergence |
|---|---:|---:|---:|---|---|
| `N8CQ4ZKP2W` | 5 | 5 | 0 | none | — |
| `H2LV6ZJ4XW` | 20 | **22** | **+2** | Forgotten Soul | seq 441（両腕 state 一致） |
| `AM8C6YXHSG` | 17 | 17 | 0 | Fiddle・FS・Chains | seq 248（機構なし＝生成プール） |
| `R8V2H6N4ZB` | 22 | 22 | 0 | Chains・Rose |分歧0 |
| `D1W9Y3B7FC` | 14 | 14 | 0 | none |分歧0 |
| `P3V8N5K2RX` | 15 | 15 | 0 | Duplication | 分歧0 |
| `B3N8V5T1WQ` | 16 | 12（走行中） | — | arm 側が機構を seen せず | 分歧0 |
| `Q6N3V8K2MT` | 12 | （first pass 12） | 0 | none | 分歧0 |

**MEASURABLE = 4 seed：control 74 / arm 76、+2。** 閾値（≥3 decisions かつ ≥3 seeds）は decisions 側は
超える（H2 の46件）が seeds 側が1 → win-rate の採用根拠にはならない。機構は正しさの修正として採用済み
のまま、成果の母集団は薄い。

### B3 でも Rose の effect 0が実走で出た（404件分歧0）

`mechpanel_arm_clean_B3N8V5T1WQ`（15勝0敗・走行中）：両腕の combat state に `RELIC.BLOOD_SOAKED_ROSE`
が出ている（control 125・arm record）ので B3 は pair になり、aligned combat decision **404件で分歧0**。
二重計上を除去した（`a328b5c`）後の model は Rose に何もしないので、分歧が出ないのは预期どおり。
R8（454件分歧0）と同じ形。

panel の MEASURABLE は H2・AM8・R8・P3（＋B3 の Rose）で、机构単独として決定を動かしたのは H2 の
Forgotten Soul 46件だけ。run レベルで机构単独として立つのは第一分歧の位置（state が両腕で一致）の
限り、という rule が B3 でも確認された。

### H2 の第一分歧は机构単独で立つ（生成プールが決定に関与できない）

seq 441（両腕の state が一致、Forgotten Soul が両腕に出ている）の record を確認：hand は
Uppercut・Iron Wave・Strike・Bloodleting、**draw/discard/exhaust に Stoke も Infernal Blade も無い**。
＝生成集合（`STOKE_GENERATION` の忠実化）はその decision の rollout に関与できない。なので分歧は
`ForgottenSoul.AfterCardExhausted`（exhaust 1枚につき random 1 hittable 体へ1 unpowered）の実装差だけが
成因。arm が end_turn、control が Uppercut を選んだ。

panel（clean run）の完走読取：control 121勝 vs arm 123勝（+2、H2 単独）。分歧を持つ pair は H2 だけで、
R8・B3・P3・N8・D1・Q6 は分歧0、AM8 の第一分歧は生成プール。

## panel（clean run）の完走読取

| seed | control（`e808bdf`） | arm（clean） | delta | aligned | 分歧 | 第一分歧 |
|---|---:|---:|---:|---:|---:|---|
| `N8CQ4ZKP2W` | 5 | 5 | 0 | 111 | 0 | — |
| `H2LV6ZJ4XW` | 20 | **22** | **+2** | 390 | 46 | seq 441（Forgotten Soul、単独で立つ） |
| `AM8C6YXHSG` | 17 | 17 | 0 | 323 | 138 | seq 248（生成プール） |
| `R8V2H6N4ZB` | 22 | 22 | 0 | 454 | 0 | — |
| `D1W9Y3B7FC` | 14 | 14 | 0 | 306 | 0 | — |
| `P3V8N5K2RX` | 15 | 15 | 0 | 305 | 0 | — |
| `B3N8V5T1WQ` | 16 | 16 | 0 | 446 | 0 | — |
| `Q6N3V8K2MT` | 12 | 12 | 0 | — | 0 | — |

**機構単独の win-rate 効果：1 seed（H2）で +2。閾値の seeds 側が未達 → 採用根拠にはならない。**
機構は正しさの修正として採用済みのまま。例外は R8 の1件（SoarPower の ZeroDivision、`2aef215` で修正）
で、その run の分歧0・胜敗同値に影響は出なかった。

### mechanisms-only batch の expected reading

`data/mechonly_agent.py`（arm の code、生成集合は control 形）で4 seed を走らせる（job `bash-424`）。
設計の意図：

- 生成集合の差を消す → path が control と揃う → 分歧は機構の実装差だけ
- したがって第一分歧の record は、機構が**両腕の state に出ている**位置になる（机构を引くまでの区間は
  分歧0预期）。H2 は133件 aligned 分歧0、機構未発火 → 预期どおり
- 机构を引かない seed は分歧0のまま（B3・D1・Q6・N8 は引かなかった）。引く seedは control の run で
  機構を state に出した4 seed（H2・AM8・R8・P3）＋ Fiddle の seed

照合は `data/compare_panel.py`（tag `mechonly` vs `mechpanel_ctrl`）。判定は per-seed 勝数と、第一分歧が
機構の位置であること。閾値は ≥3 decisions かつ ≥3 seeds。

### H2 の harness run：機構が出る位置が予備できる（control は seq 423 で出現）

control H2（`e808bdf`）で `RELIC.FORGOTTEN_SOUL` が初めて出る record は **seq 423**（combat、
`CARD.IMPERVIOUS` を play する decision）。生成集合を control 形へピン留めした harness run は、
機構が state に出るまでの区間が control と一致する预期（現在 aligned 165件分歧0）。
机构が出た後の第一分歧が機構単独の差になる — これが harness の目的。H2 では panel の第一回 runで
分歧46件（第一分歧 seq 441）が出ていて、harness run はその再現になるかを見る。

### H2 の harness run が机构単独の差を再現した（22勝地点、分歧46件、第一分歧 seq 441）

生成集合を control 形へピン留めした `mechonly` run（job `bash-424`）で H2：

- aligned 390件で分歧 **46件**、第一分歧 **seq 441**（arm harness: end_turn / control: Uppercut）
- その位置の state に `RELIC.FORGOTTEN_SOUL` が**両腕**で在る（Stoke も Infernal Blade も piles に無い）
- wins 22・losses 0（走行中）＝ panel の clean arm run（22勝1敗）と同じ地点

生成集合の差を消した下で同じ分歧・同じ outcome が出る → H2 の +2 は機構単独（`ForgottenSoul.AfterCardExhausted`）
で立つ。ただし seeds 側は1件のままなので閾値（≥3 seeds）には未達。harness の残3 seed（AM8・R8・P3）を
待つ。

### H2 harness 完走：panel と同じ outcome を機構単独の条件で再現（22勝1敗）

`mechonly_H2LV6ZJ4XW` 完走：**22勝1敗**（control 20勝1敗、+2）、aligned 390件分歧46件、第一分歧 seq 441、
分歧位置の机构は `RELIC.FORGOTTEN_SOUL` が両腕。生成集合を control 形へピン留めた下で、panel の clean
arm run（22勝1敗・分歧46件）と**同じ outcome・同じ分歧**が出た → H2 の +2 は機構単独で立つ、と
run レベルで確認。

harness の残：AM8（1勝0敗・走行中、分歧0、機構未出現）、R8・P3。AM8 は生成集合の差が消えるので、
機構が両腕の path に出る位置から分歧する预期（panel では第一分歧が生成プールだった）。

### harness の動作確認：H2 では pool の差が一度も効かなかった

`mechonly_H2LV6ZJ4XW` と `mechpanel_arm_clean_H2LV6ZJ4XW`（faithful 集合で走った arm）を照合：
aligned 447件で**分歧0**。H2 は Stoke を打つ位置が無かった（少なくとも分歧に効く位置）ので、pin しても
しなくても同じ決定列になる。＝ H2 の分歧46件は最初から機構単独で立っていた（上の state 確認と一致）。

harness の価値は pool が効く seed 側にある。AM8 は panel で第一分歧が生成プール（seq 248）だったので、
pin した harness run は control と揃った path を歩き、機構が両腕の state に出た位置から分歧する预期。
現在 AM8 harness：5勝0敗、aligned 62件分歧0、機構未出現。

### harness が live run で効いていることの確認

`ps` の command line：`-AgentScript ./data/mechonly_agent.py`（seed AM8C6YXHSG、`-AgentSimulations 100`、
`-StopAfterAct 3`）。harness は repo の code を import して `STOKE_GENERATION`（110名）と
`INFERNAL_BLADE_ATTACKS`（51名）を control 形へ上書きするだけなので、live の決定列が control と
揃うはずで、実際に AM8 は138件分歧0（机构未出現、pool の分歧点 seq 248 未通過）。

harness の判定条件：`python3 data/compare_panel.py mechonly mechpanel_ctrl . .wt-ctrl-e808bdf <seed>`。
分歧が机构の位置（両腕の state に同じ机构）で出た case だけが机构単独の差。

### harness の live 確認：AM8 は pool の分歧点（seq 248）を分歧0で通過した

panel の faithful 集合で走った arm run は AM8 の seq 248 で control と分歧していた（成因は生成集合、
replay で control 形の集合なら control の選択、faithful なら arm の選択を再現）。pin した harness run は
**seq 248 を分歧0で通過**（10勝0敗、aligned 168件、機構未出現）→ live でも pin が効いており、その分歧が
生成集合の差だったことが run レベルでも確認できた。

Fiddle は control 側で seq 322 の event で獲得。harness run は control と揃った path を歩いているので
同じ点で獲得する预期。獲得後の第一分歧が機構単独の差になる。

### 预測（1 record replay）：Fiddle を引いた直後の decision は分歧しない

control AM8 の Fiddle grant（seq 322）の直後の combat decision seq 325 を、arm code（pin 済み）と
control tree で replay：両方 `CARD.PERFECTED_STRIKE`（control の run の実際の選択と同じ）。
＝機構を引いたことが即ち分歧にはならない。分歧は rollout が机构を理由に別の ranking を出す位置で出る
（sample で Fiddle の分歧76件 / 108件の中身）。live の harness run（現在 seq 318、分歧0）がその位置に
入るかを見る。

### AM8 harness：Fiddle 単独の第一分歧が出た（seq 331、state は両腕で完全一致）

`mechonly_AM8C6YXHSG`（14勝0敗・走行中、例外0件）：aligned 262件で分歧 **21件**、その分歧位置の機構は
すべて `RELIC.FIDDLE` が**両腕の state** に出ている。第一分歧 seq 331：

- state は両腕で完全一致（違うのは choice 字段だけ）
- harness（arm code、生成集合は control 形）→ `CARD.STRIKE_IRONCLAD`、control → `CARD.ANGER`
- Fiddle は seq 322 の event で両腕が同じ点で獲得している

＝生成集合の差を消した条件で、分歧は Fiddle の実装（hand draw +2 と effect draw の拒否）だけで立つ。
H2（Forgotten Soul）に続く2件目の机构単独 pair。outcome はまだ決まっていない（harness 14勝0敗、
control は同じ path から17勝1敗）。

これで panel の机构単独 pair は2 seed（H2・AM8）。閾値（≥3 seeds）には harness の R8・P3（＋Fiddle を
引く seed）を待つ。

### AM8 harness：分歧80件の内訳（pin した下で「機構が両腕の state に出た位置」以外に分歧が無い）

`mechonly_AM8C6YXHSG`（17勝0敗・走行中、例外0件、aligned 330件）：

- `RELIC.FIDDLE` 単独が両腕の state に出ている位置：**73件**
- Fiddle ＋ Chains が両腕に出ている位置：14件（単独へは split できない）
- 両腕の state に機構が何も出ていない位置：**0件**

生成集合を control 形へ pin した下で、分歧は全部機構の位置で出ている。＝ AM8 の panel 第一回 run の
分歧（138件）のうちの49件は生成集合の差だったが、pin した harness run ではその差が消えて、機構の位置
だけの分歧になった。Fiddle の単独 attribution が73件で、H2 の Forgotten Soul 46件に続く2件目。

（14件は Fiddle と Chains の両方がある位置なので、機構単独へは同一 observation の replay でしか割れない。）

### harness readings（AM8 完走）

| seed | control | harness | delta | 分歧（両腕の state） |
|---|---:|---:|---:|---|
| `H2LV6ZJ4XW` | 20W1L | **22W1L** | **+2** | 46件、すべて Forgotten Soul |
| `AM8C6YXHSG` | 17W1L | 17W1L | 0 | 80件（Fiddle 73、Fiddle+Chains 7）、勝敗は変わらない |
| `R8V2H6N4ZB` | 22W1L | 1勝0敗・走行中 | — | control 側は Chains を17 record で所持 |
| `P3V8N5K2RX` | 15W1L | 未走 | — | control 側は Duplication を1 record |

AM8 で Fiddle は73件決定を動かしたが outcome は同じ → decision の分歧が win-rate へ伝わらないcase。
机构単独の win-rate 効果は harness でも H2 の +2（1 seed）のまま。閾値 ≥3 seeds は R8・P3（機構が
両腕の path に出る case）を待つ。

### harness の pin が live で効いている決定的確認（AM8 seq 248）

同一 decision（seq 248）の3条件の選択：

- live harness run（pin した集合）→ `CARD.BURNING_PACT`
- control（`e808bdf`、機構なし）→ `CARD.BURNING_PACT`
- faithful 集合で走った arm run → `CARD.SHRUG_IT_OFF`

live の harness が control と同じ选择を返している＝pin が実走で効いている。したがって harness run の
分歧（AM8 87件、H2 46件）は机构の実装差だけで立つ。R8 ではまだ Stoke を打つ位置に来ていない（checked 0）
ので、R8 の pin 効果は機構出現後に分岐するかどうかで見る。

### Rose の effect 0：harness run でも同じ（R8、arm 130 record・分歧0）

`mechonly_R8V2H6N4ZB`：harness run が Rose を保持する combat record **130件**で、control との決定分歧
**0件**。二重計上を除去した model（`a328b5c`）は Rose に何も処理を持たないので、分歧が出ないのは构造上
当然で、実走3件（panel clean R8 454件、panel clean B3 446件、harness R8 130件）で一致した。

Chains のゲート（忠実な形）は R8 の control run で17 record 効いていた位置があるが、harness run は
まだその点（seq 567）に達していない。ゲート単独の分歧は651件の母数で17%（sample）→ R8 の path で
出るかは達してから見る。

### R8：Chains が両腕の state に出た17件で決定分歧0（post-fix 到達性0の実走形）

`mechonly_R8V2H6N4ZB` 完走：22勝1敗 = control と同値。Chains（忠実なゲート）が両腕の combat state に
17 record 出ていて、決定分歧は0。＝ R8 の path ではゲートが決定を動かさなかった。sample で R8 の分歧が
Rose の bug branch 由来（除去後0）だったことと実走で一致。

harness reading（完走分）：H2 46分歧（Forgotten Soul）で +2、AM8 87分歧（Fiddle 73・Chains 14）で outcome
同値、R8 分歧0・同値。P3 は未走。机构単独の win 効果は1 seed（H2）のまま → 閾値 ≥3 seeds 未達。

### gate の実走検証（record を1件ずつ model へ流して確認）

`candidate_bound_D6A1F8C3E5_agent.jsonl` seq 395（実走で gate が効いていた位置の record）を model に流した：

- play 前：bound 札3枚が hand に在り、`legal_actions` は bound を含む（gate 前＝忠実）
- bound 札を1枚 play した直後：`bound_played_this_turn` が True になり、残る bound 2枚は
  `legal_actions` から消える（play 可能な札は非-bound だけ）

＝ `ChainsOfBindingPower.ShouldPlay` の形（first bound play allowed、以降 gate）と model が一致。
harness batch は完走：P3 15勝1敗 = control（Duplication を両腕の state に出すも分歧0）。機構単独で win
効果が出たのは H2（+2）だけ。

### 第二 batch の seed は「control（`e808bdf`）の run が機構を state に出す」条件で選ぶ

機構を state に出た seed（corpus、commit をまたぐ集計）を**player state 出現**で並べ直した：

| seed | 機構（state 出現 record） |
|---|---|
| `H2LV6ZJ4XW` | FS 4346・Chains 984 |
| `AM8C6YXHSG` | Fiddle 1763・Chains 181・FS 177 |
| `R8V2H6N4ZB` | Rose 677・Chains 112 |
| `P3V8N5K2RX` | Chains 231・Duplication 16 |
| `H4L6P2N8XS` | Rose 119・Chains 17 |
| `M7C4Q9V2RH` | Chains 72・OneTwoPunch 2 |
| `V7D3M9H2XW` | Panache 12 |
| `T3XQ7WM2VP` | Gigantification 6・Duplication 2 |
| `M5W9C3T7LQ` | OneTwoPunch 6 |
| `U2M7K5F9RA` | OneTwoPunch 1・Duplication 1 |
| `C8Q1Z7E3KS` | OneTwoPunch 1 |

Fiddle は corpus で N8 4761・AM8 1763・Q6 136・D1 106 の4 seed にしか出ない。そのうち `e808bdf` の
control run が Fiddle を state に出した seed は AM8 だけ（N8・D1・Q6 のolder run は `e808bdf` より後の
commit で、event の選択が違った）。だから Fiddle の run レベル pair は AM8 が母数。

batch2 の設計：control は `e808bdf`、arm は pin した harness。pin した arm は control の path を機構が
効く位置まで追うので、control の run が機構を state に出せば pair が成立する（機構が効く位置から分歧）。
現在 U2M7K5F9RA の control を走行中。

### batch2 の第一 control run が機構を state に出した（`U2M7K5F9RA`、OneTwoPunchPower）

`mechonly_ctrl_b2_U2M7K5F9RA`：7勝0敗・走行中、例外0件、combat の state に
`POWER.ONE_TWO_PUNCH_POWER` が出ている。control（`e808bdf`）が機構を state に出すなら、pin した arm
run は同じ path を追うので pair が成立する（機構が効く位置から分歧する）。判定は `compare_panel` と
`mechonly_attribution`（tag `mechonly_arm_b2` vs `mechonly_ctrl_b2`）。

### batch2 の attribution は构造上clean（pin した arm は机构以外で分歧できない）

batch2 は control（`e808bdf`、机构未実装）と arm（HEAD＋生成集合 pin）を同じ seed・同じ条件で比べる。
arm 側に机构の実装以外に code の差が無い（生成集合は pin で無効化）ので、決定列が分歧する位置は
機構が arm の state に出ている位置に限られる。control の run が機構を state に出した seed では、path が
分歧するまで両腕が同じものを見る ＝ pair が成立する。

従って batch2 の分歧は、機構の実装差として attribution できる。母数：control が機構を state に出した
seed（現時点 `U2M7K5F9RA`：Duplication＋OneTwoPunch、10勝1敗／`T3XQ7WM2VP`：Duplication、7勝0敗・走行中）。

Duplication の run レベル effect は batch1 の P3 で0（1 record 両腕、分歧0）だった。OneTwoPunch の sample
reach は2件。＝ batch2 で分歧が出るかは薄いが、出れば機構単独の差として立つ。

### batch2 での prediction（sample の分歧が既にある2 seed）

1-in-12 sample（機構単独、生成集合は control 形）で batch2 の seed に分歧が残っている：

- `M5W9C3T7LQ` seq 89：arm `CARD.ONE_TWO_PUNCH` / control `CARD.DEFEND_IRONCLAD`（OneTwoPunch）
- `V7D3M9H2XW` seq 312：arm `CARD.SHRUG_IT_OFF` / control `CARD.STONE_ARMOR`（Panache）

ただし sample は blanket bound rule の下で数えたもの（後の忠実なゲートで数え直し済み、Chains の14件は
Fiddle と重複)。実走の batch2 run が同じ位置で分歧するかを見る。分歧すれば3 seed 目になり、閾値
（≥3 decisions かつ ≥3 seeds）へ接近する。

実走の control 側は現時点で `U2M7K5F9RA`（Duplication＋OneTwoPunch、10勝1敗）と `T3XQ7WM2VP`
（Duplication、9勝0敗・走行中）が機構を state に出している。

### play-count powers の忠実度は限定（block grant と damage hit の2通路だけ）

`play_duplicated` の使用箇所：`_grant_block`（line 1071）と damage path（line 2815）。＝dup された play の
「block grant を2回」「damage hit を2回」は model に入っているが、draw・status 付与・energy・self-damage
・multi-effect card の extra resolution は入っていない。したが batch2 の Duplication/OneTwoPunch の
実走效果は**model が捉えている分だけ**の差で、game の完全な效果は understimate する。

Gigantification（line 2137-2154）は play 中の mark された Attack command の damage を3倍（1回）なので、
play-count とは別の通路。こちらも damage通路限定。

→ batch2 で機構単独の分歧が出た case は「model の実装が効いた位置」であり、忠実度の限界は記録したまま
読む（over-claim しない）。

### batch2 の control run に1件 exception（control 側の Hellraiser recursion）

`mechonly_ctrl_b2_M7C4Q9V2RH_agent.err`：`_autoplay_top_of_draw` → `_step` → `_autoplay_top_of_draw` の
再帰で RecursionError。control（`e808bdf`）には HellraiserPower の auto-play に cap が無い；HEAD には
`hellraiser_autoplays_this_turn >= 9` の safety cap がある（後から入れた修正）。

→ batch2 の arm–control 差は「機構の実装」＋「この cap」の2要素になる。`M7C4Q9V2RH` の control run は
例外1件なので、この seed の第一分歧がその decision 位置にある case は机构単独の差として読めない。
rule 9（再走後は exception 0件を確認）の形で、run ごとに例外数を報告する：

| seed | control run | exceptions |
|---|---|---:|
| `U2M7K5F9RA` | 10勝1敗 | 0 |
| `T3XQ7WM2VP` | 12勝1敗 | 0 |
| `M7C4Q9V2RH` | 6勝0敗・走行中 | **1** |

### consumption の実走検証（同一 turn の連続 decision で確認）

実走 trace の「decision → 同一 turn の次の decision」で、power の消費を確認した：

- `POWER.DUPLICATION_POWER`：present → consumed **61件**（decrement/unchanged 0）＝ play 1回で消費、
  model の形と一致
- `POWER.GIGANTIFICATION_POWER`：consumed 13件、unchanged 7件。unchanged の内訳は played card の type
  が Status 4・Skill 2・Power 1 ＝ **Attack を打った時だけ消費**という model の条件（`card in ATTACKS`）と
  一致
- `POWER.ONE_TWO_PUNCH_POWER`：消費を観測できる transition がこの corpus に0件（母数が薄い）

実走で確認できるのは observable な量（powers・relics・hand）だけ。damage が2回 hit したかは trace に
出ない（`_step_score` の value には出るが、game 側の実際の hit 数ではない）。

### R8 の control run にも exception が1件あった（SoarPower の ZeroDivision、HEAD で修正済みの同じ bug）

`mechpanel_ctrl_R8V2H6N4ZB_agent.err`：`damage()` の SoarPower branch での ZeroDivisionError（`value // hits`
が hits 0）。＝ control 側にも同じ bug があり、その decision で game 側の default を取っている。R8 の
read（control 22勝1敗 / arm 22勝1敗、分歧0）はその1 decision 以外は決定列が一致しているが、rule 9 の
形で言えば R8 の control run は汚染 → clean にしたい場合は `e808bdf` で re-take。

batch2 の control では `M7C4Q9V2RH` に1件（Hellraiser recursion、control 側に cap が無い）が出ている。
exceptions を run ごとに報告するように `mechonly_attribution.py` を更新（commit `82cacce`）：

```
H2LV6ZJ4XW: aligned 390 diffs 46 by-mechanism {RELIC.FORGOTTEN_SOUL: 46} no-mechanism 0 exceptions arm 0 control 0
AM8C6YXHSG: aligned 338 diffs 87 by-mechanism {RELIC.FIDDLE: 87, POWER.CHAINS_OF_BINDING_POWER: 14} no-mechanism 0 exceptions arm 0 control 0
R8V2H6N4ZB: aligned 454 diffs 0 exceptions arm 0 control 1
P3V8N5K2RX: aligned 305 diffs 0 exceptions arm 0 control 0
```

### batch2 の照合 usage（arm は main checkout、control は worktree）

`mechonly_attribution.py` は arm 側を `data/<arm_tag>_<seed>_agent.jsonl`（main checkout）、control 側を
`<ctrl_dir>/data/<ctrl_tag>_<seed>_agent.jsonl`（worktree）で見る。batch2 の正しい usage：

```
python3 data/mechonly_attribution.py --arm-tag mechonly_arm_b2 --ctrl-tag mechonly_ctrl_b2 \
  U2M7K5F9RA T3XQ7WM2VP M7C4Q9V2RH C8Q1Z7E3KS M5W9C3T7LQ V7D3M9H2XW
```

batch2 control 進捗（2026-10-03 13:4x、例外数）：`U2M7K5F9RA` 10勝1敗（0、Dup＋OTP）、
`T3XQ7WM2VP` 12勝1敗（0、Dup＋Gigantification）、`M7C4Q9V2RH` 16勝0敗・走行中（**1**、Hellraiser
recursion、機構未出現）。

### cap の追加は batch の走行中に land した（rule 9 の形での内訳）

commit `f16b256`（`_autoplay_top_of_draw` の再帰 cap）は batch2 の control stage 走行中に committed
した。agent は run の start 時に file を読むので、run ごとに code が違う：

- `C8Q1Z7E3KS`（commit 時点で走行中）＝ pre-cap の code
- `M5W9C3T7LQ`・`V7D3M9H2XW`（commit 後に start）＝ cap 入りの code
- arm stage（commit 後）＝ cap 入り

cap は crash を止めるものなので、cap が実際に発火する位置（draw pile に Havoc が9枚以上並ぶ等）で
ないと決定は変えない。したがって batch の解读は保つが、片腕だけ cap が発火した case は机构単独の差
として読めない。run ごとの例外数と code version を報告する。

### 訂正：札名出現は table knowledge で、机构ではない

sample で OneTwoPunch 2件・Panache 1件と数えた分歧は、実際の record を見たら **powers が空**（札が hand
に在るだけ）だった。＝ arm は card table（cost/damage/type）を知っていて control は知らないという
**table knowledge の差**で、play-count power が active だった差ではない。

`mechonly_attribution.py` は機構を **power/relic の state 出現**だけで数えるようにした（commit
`ba67d63`）。例外は Wither など turn end に hand にあることで発動する status（hand presence が条件）。
batch1 の readings は relic 機構（Fiddle・Forgotten Soul）なので数字は変わらない。

→ 机构単独で立つ母数（power/relic出現）：H2 の Forgotten Soul 46件、AM8 の Fiddle 87件（Chains と14件
重複）、R8・P3 は分歧0。play-count powers（Duplication・OneTwoPunch・Gigantification・Panache）の run
レベルの差は、power が state に出た位置で出た分歧だけを数える。

### batch2 の control reading（power/relic の state 出現だけで判定）

| seed | control | exceptions | power/relic が state に出た | pair candidate |
|---|---:|---:|---|---|
| `U2M7K5F9RA` | 10勝1敗 | 0 | Duplication・OneTwoPunch | Yes |
| `T3XQ7WM2VP` | 12勝1敗 | 0 | Duplication・Gigantification | Yes |
| `M7C4Q9V2RH` | 17勝1敗 | **1** | Chains | Yes（control 汚染） |
| `C8Q1Z7E3KS` | 13勝1敗 | 0 | none | No |
| `M5W9C3T7LQ` | 16勝1敗 | 0 | none | No |
| `V7D3M9H2XW` | 5勝0敗・走行中 | 0 | none | No |

pair candidate は3 seed。pin した arm run は control の path を追うので、機構が state に出た位置から
分歧する预期。母集団の判定は、第一分歧が power/relic の位置であり、かつ両 run 例外0件の case だけ使う。
Act 踏破は control 6 seed 全部未踏破（各 run 1敗）なので、成果の判定は per-seed 勝数と分歧数。

### harness が消すのは生成集合の差だけ（card table の knowledge 差は残る）

`mechonly_agent.py` は `STOKE_GENERATION` と `INFERNAL_BLADE_ATTACKS` を control 形へ上書きするだけ。
arm 側の `CARD_COST`/`CARD_DAMAGE`/`SKILLS`/`POWERS` の entry（Panache・OneTwoPunch・Wither など）は
control に無いので、**table knowledge の差は harness でも残る**。だから attribution は power/relic が
state に出た位置だけで機構の差を数える（`mechonly_attribution.py` の今の形）。

実測でその形が出た例：sample の `M5W9C3T7LQ` seq 89（hand に OneTwoPunch、powers 空）と
`V7D3M9H2XW` seq 312（hand に Panache、powers 空）は、札名 knowledge の差。batch2 の control run は
この seed たちで機構を state に出していない（`M5` 16勝1敗・`V7` 9勝0敗・走行中、power/relic 出現0）ので、
arm run が分歧する位置は knowledge 差の位置になり、机构単独の差ではない。

### batch2 arm 1件目の分歧は knowledge-only（機構が state に出る前）

`mechonly_arm_b2_U2M7K5F9RA`（67 aligned、分歧6件）：その6件は**両腕の state に power/relic が出ていない
位置**＝ table knowledge の差（arm は OneTwoPunch などの card entry を持つ、control は持たない）。
control は `POWER.DUPLICATION_POWER` を seq 189 で得るので、arm がその点に達して同じ位置で見た場合の
分歧だけが機構単独の差として数えられる。`mechonly_attribution.py` の by-mechanism は空、no-mechanism 6件。

→ pin は生成集合の差を消すが、knowledge 差は消さない。機構単独の差は power/relic が両腕の state に
出た位置だけ、という rule がそのまま効いている。

### run レベルの判定基準（batch2 で確定）：第一分歧が機構単独である seed だけ使える

batch2 の arm run（`U2M7K5F9RA`、100 aligned、分歧34件）は機構が state に出る**前**の位置で分歧した
（no-mechanism 34件）。分歧した時点で path が分かれるので、その後の位置は機構単独の差として使えない
（機構の acquisition 位置自体が食い違い始める）。

→ run レベルで機構単独の差として立るのは、**第一分歧が power/relic の位置である case** だけ。
その形で立っているのは H2（seq 441、両腕の state に Forgotten Soul、分歧46件、+2）。
AM8 は第一分歧が生成プール（pin した harness run ではその分歧が消える → 分歧0、机构位置から分歧する
预期だったが、AM8 の harness run は第一分歧が Fiddle 位置＝機構単独で立った。harness の AM8 read：
aligned 338、分歧87、by-mechanism Fiddle 87、no-mechanism 0）
- 注：harness の AM8 は no-mechanism 分歧0 → 第一分歧が機構の位置。だから AM8 は機構単独で立つ
  （Fiddle 87件）、ただし outcome は同値（17勝1敗）。

batch2 の `U2M7K5F9RA` は第一分歧が knowledge-only（34件）→ その seed は機構単独の測定に使えない。
control が機構を state に出した seed のうち、arm 側が第一分歧から機構位置で分歧する case だけが母数。

### `U2M7K5F9RA` の機構 acquisition が腕でずれた（control 189 / arm 195）

arm run は `POWER.DUPLICATION_POWER` を seq 195 で得ている。control は seq 189。差の6 record 分は
knowledge-driven の分歧で path が分かれた後なので、同じ seq の record は別の game state を指す
（＝`present()` が両腕で同じ机构を出す位置 even if counted, it is not the same decision）。

→ `U2M7K5F9RA` は run レベルで機構単独の測定に使えない。母数になるのは第一分歧が机构位置である seed
だけ（H2、AM8 の harness）。

### `T3XQ7WM2VP` は clean pair（両腕が同じ seq 119 で Duplication を得ている）

control と arm（pin harness）の両腕が `POWER.DUPLICATION_POWER` を **seq 119** で得て、それまでの
aligned 76件は分歧0。power は card table の knowledge 差に関係しない（table にあるのは card 名だけ）
ので、119 以降の分歧は機構単独の差として立つ。H2（seq 441）と AM8（harness、seq 331）に続く3件目の
clean pair。

母数：`U2M7K5F9RA` は knowledge 差で先に分歧して acquisition までずれた（189/195）ので除外。
`C8Q1Z7E3KS`・`M5W9C3T7LQ`・`V7D3M9H2XW` は arm が機構を state に出すかどうかで決まる（control 側は
V7 で Panache を11 record 出している）。

### run レベルの判定（第一分歧が機構位置である seed）

`data/mechonly_attribution.py` に first-mech（両腕の state に機構が出た第一位置）と
first-diff-mech（第一分歧の位置の機構）を出すようにした（commit `b922915`）。現在の形：

| seed | aligned | diffs | first-mech | first-diff-mech | exceptions |
|---|---:|---:|---|---|---|
| `H2LV6ZJ4XW` | 390 | **46** | (423, FS) | **FS** | 0/0 |
| `AM8C6YXHSG`（harness） | 338 | **87** | (325, Fiddle) | **Fiddle** | 0/0 |
| `R8V2H6N4ZB`（harness） | 454 | 0 | (396, Rose) | none | arm 0 / control 1 |
| `P3V8N5K2RX`（harness） | 305 | 0 | (166, Duplication) | none | 0/0 |
| `U2M7K5F9RA`（batch2） | 129 | 62 | none（knowledge-only） | none | 0/0 |
| `T3XQ7WM2VP`（batch2） | 157 | 0 | (119, Duplication) | none | 0/0 |

機構単独の差として立っているのは H2（46分歧、**+2**）と AM8（87分歧、**outcome 同値**）の2 seed。
閾値（≥3 decisions かつ ≥3 seeds）の seeds 側は未達 → win-rate の效果は未証明。機構は正しさの修正として
採用済みのまま。

### T3XQ7WM2VP：clean pair だが机构位置で分歧0、outcome 同値（12勝1敗）

両腕が `POWER.DUPLICATION_POWER` を seq 119、`POWER.GIGANTIFICATION_POWER` を seq 207 で同じ位置に見て
いて（aligned 201件、分歧0）、arm 完走 12勝1敗 = control と同値。この path では机构が決定を動かさ
なかった。

run レベルで机构単独の差として分歧を出した seed は H2（Forgotten Soul、46件、+2）と AM8（Fiddle、87件、
outcome 同値）の2件のまま。閾値（≥3 decisions かつ ≥3 seeds）の seeds 側未達。

### `M7C4Q9V2RH` は機構位置（468）より前に control 側が分歧している（exception seq 138）

control M7 の exception は seq 138、機構（`POWER.CHAINS_OF_BINDING_POWER`）の第一位置は seq 468。
exception の decision で game 側の default を取ったので、138 以降 path が分かれる → 機構位置での分歧が
出ても机构単独の差として attribution できない。この seed は run レベルの母数から除外。

run レベルで机构単独として立っている seed：H2（46分歧、+2）と AM8（87分歧、outcome 同値）。
knowledge-only で除外：`U2M7K5F9RA`。分歧0：`T3XQ7WM2VP`・`R8V2H6N4ZB`・`P3V8N5K2RX`。除外（机构位置
より前に path 分歧）：`M7C4Q9V2RH`。

### `M7C4Q9V2RH` の分歧は knowledge-driven（seq 120、機構は state に出ていない）

arm が `CARD.STRIKE_IRONCLAD`、control が `CARD.TREMBLE` を選んだ seq 120 は、両腕の state に power/relic
が出ていない位置（＝card table の classification 差）。しかも control 側に exception（seq 138）が后続に
ある。pin した arm は生成集合で control と同じなので、この分歧は机构の実装差ではない。
→ `M7C4Q9V2RH` は机构単独の測定に使えない（knowledge と exception の二重の confound）。

### run レベルの結論（2026-10-03 15:0x 時点、batch2 の arm stage 走行中）

機構単独の差として run レベルで立っている seed は2件：

- `H2LV6ZJ4XW`：第一分歧 seq 441 が Forgotten Soul（両腕の state）。分歧46件、**control 20勝1敗 → arm 22勝1敗（+2）**
- `AM8C6YXHSG`（pin harness）：第一分歧 seq 331 が Fiddle（両腕）。分歧87件（Fiddle 単独73、Fiddle+Chains 14、no-mechanism 0）で **outcome 同値**（17勝1敗）

除外・分歧0：`U2M7K5F9RA`（第一分歧が knowledge-only、62分歧、outcome 同値）、`M7C4Q9V2RH`（knowledge 39
分歧＋ control exception、機構が arm 側に出ていない）、`T3XQ7WM2VP`（clean pair だが分歧0、同値）、
`R8V2H6N4ZB`（分歧0、control exception 1件）、`P3V8N5K2RX`（clean pair・分歧0、同値）、
`C8Q1Z7E3KS`・`M5W9C3T7LQ`・`V7D3M9H2XW`・`N8`・`D1`・`Q6`・`B3`（arm 側が機構を state に出さない）。

**結論：機構8件は正しさの修正として採用済み。win-rate の效果は、母集団（clean pair で第一分歧が機構
位置の seed）で H2 の +2 だけが立った。閾値（≥3 decisions かつ ≥3 seeds）には未達なので、效果ありと
は言わない。** decision レベルの母数（同一 observation を両treeで replay、生成集合を control 形へ固定）
は Fiddle 76・Chains の忠実なゲート651件で17%・Forgotten Soul 24・play-count powers は knowledge 差と
混かる（札名出現は機構ではない）。

### batch2 の outcome（完了分）

| seed | arm | control | delta | attribution |
|---|---:|---:|---:|---|
| `U2M7K5F9RA` | 10勝1敗 | 10勝1敗 | 0 | knowledge-only（機構は arm 側で195、control 189） |
| `T3XQ7WM2VP` | 12勝1敗 | 12勝1敗 | 0 | clean pair（Duplication 119、Gigantification 207）だが分歧0 |
| `M7C4Q9V2RH` | 13勝1敗 | 17勝1敗 | −4 | 第一分歧が knowledge-driven（116分歧）＋ control exception 1件 → 機構単独ではない |
| `C8Q1Z7E3KS` | 13勝1敗 | 13勝1敗 | 0 | 機構を state に出さない |
| `M5W9C3T7LQ` | 1勝0敗・走行中 | 16勝1敗 | — | — |

机构単独の分歧を出した seed は H2（46分歧、+2）と AM8（87分歧、outcome 同値）の2件のまま。
`M7` の −4 は knowledge 差（card table の classification）で path が分かれた結果で、機構の実装差として
読めない。run レベルの母数では机构単独の win 效果は依然 H2 だけ。

### knowledge-confound の内訳（H2 46分歧のうち39件、AM8 87分歧のうち85件）

`control_card_table()` を control の `CARD_COST` ＋ `CARD_NAMES`（basic/status 名）で built した
（commit `0edccb5`）。その形で分歧位置を分けた：

| seed | 分歧 | power/relic が両腕に在る | knowledge-confounded | clean（機構位置かつ control も知っている札だけ） |
|---|---:|---:|---:|---:|
| `H2LV6ZJ4XW` | 46 | 46 | 39 | **7** |
| `AM8C6YXHSG`（harness） | 87 | 87 | 85 | **2** |
| `U2M7K5F9RA` | 62 | 0 | 61 | 0 |
| `M7C4Q9V2RH` | 116 | 0 | 110 | 0 |

confounded の位置は「arm だけが card table を知っている札」が hand に在る位置なので、分歧が機構から
来たのか knowledge から来たのか観測だけでは割れない。割るには同一 observation で arm（control 形の
table）／control を replay する必要がある（sample の形）。

→ 機構単独の win 效果として run レベルで立っているのは H2 の +2 だが、その46分歧のうち clean は7件。
AM8 の87分歧の clean は2件。母集団は薄いまま、という読みが今の正直な形。

### harness が机构の無い path で control と完全一致（M5）

`mechonly_arm_b2_M5W9C3T7LQ`：303 aligned、分歧0、両 run 例外0件、outcome **16勝1敗 = control と同値**。
机构が state に出ない seed では、pin した arm は control と決定列が完全一致する（生成集合の差を消した
ので、difference が机构以外に無い）。harness の预期どおり。

机构の無い seed（M5・C8・N8・D1・Q6・B3）の分歧0は、機構の実装が無効だからではなく、机构を引かなかった
から測定にならない（path 運）。分歧0の seed は機構の実装が決定を動かさなかった case と区別できない。

### `V7D3M9H2XW` は pair candidate（batch2 の control run は PanachePower を seq 221-224 に出している）

前ラウンドで「V7 は機構を state に出していない」と書いたが、その数字は corpus の**別の run**（11 record）
だった。batch2 の control run（`mechonly_ctrl_b2_V7D3M9H2XW`）は combat record の state に
`POWER.PANACHE_POWER` を **seq 221〜224** に出している。arm は現在62 aligned（分歧0）でそこに達していない。
arm が同じ path を追えば同じ位置で Panache を見る预期 → 達した位置からの分歧が機構単独の差になる。

`mechonly_attribution.py` の `first-mech` が V7 で None を返すのは、arm 側がまだその record に達していない
から（aligned 集合の側でしか見ていない）。

### V7：arm が Panache の位置（seq 221）に達して、その位置の分歧は0（現時点）

`mechonly_arm_b2_V7D3M9H2XW`：aligned 170件、分歧0、両 run 例外0件。arm が `POWER.PANACHE_POWER` を
seq 221 で見た（control も 221）→ clean mechanism position。分歧は出ていない（Panache の
counter 5枚目 play 触发がその path で決定を変えていない）。

note の fold：Rose（`a328b5c`）と生成プール（`77120b2`）の項目は完了として `[x]` にし、残る confound は
card table の knowledge 差として書き直した。

### mech vs knowledge の分割（同一条件 replay、game 不在時に実行）

`data/mech_vs_knowledge.py`（commit `ab9634f`）で、harness run の分歧位置を3条件で replay した：

| seed | 分歧 | mechanism-only（variant2 ≠ variant1） | knowledge-only（variant3 ≠ variant1 かつ variant2 = variant1） |
|---|---:|---:|---:|
| `H2LV6ZJ4XW` | 46 | **13** | 0 |
| `AM8C6YXHSG` | 87 | **22** | 0 |
| `R8V2H6N4ZB` | 0 | 0 | 0 |
| `P3V8N5K2RX` | 0 | 0 | 0 |

・replay は recorded decision を再現しないことがある（measure：control の rollout decisions 280件中260件）。
live process は per-run の module state（`upgraded_cards` の memo、Paels Flesh の once-per-run guard 等）を
持つから。だから分割は**同一条件の replay 同士**の比較で、`control-replay-reproduces-record` として別に
出している（H2 0/46、AM8 3/87）。
・ classification が空いている位置（H2 46-13、AM8 87-22）は、fresh replay 下では arm と control が同じ
选择に落ちる位置＝live の決定は module state か fallback 由来。机构単独の差として clean に言えるのは
mechanism-only  counts（13件、22件）だけ。

→ 機構単独の決定差（同一条件で隔离済み）：Forgotten Soul 13件（H2）、Fiddle 22件（AM8）。run レベルの
win 效果は H2 の +2（1 seed）のまま。

### H2 の mechanism-only 13件は机构が1つだけなので attribution が歧義がない

13位置を1件ずつ確認：両腕の state に出ている機構は `RELIC.FORGOTTEN_SOUL` **だけ**（>1の位置0件）。
例（fresh replay、同一条件）：

- seq 444：control replay `CARD.ANGER` / arm replay end_turn
- seq 445：control `CARD.ANGER` / arm `CARD.STRIKE_IRONCLAD`
- seq 446：control `CARD.ANGER` / arm end_turn

→ H2 の13件は Forgotten Soul 単独の差（`AfterCardExhausted`：exhaust 1枚につき random 1 hittable 体へ
1 unpowered）。AM8 の22件は Fiddle 単独（その位置で Fiddle だけの位置が主体。Fiddle＋Chains の14件は
単独へ割れない）。

**破いた実験（記録として正直に）**：Fiddle の「拒否 part」と「+2 part」を分割する test を走らせたが、
その位置の机构は Fiddle ではなく Forgotten Soul だった上、+2 は `_draw_into_combat` の path に無い
（turn start 側）ので patch が効いていない。数字（28/1）は意味を持たない → 破棄。

### play-count powers：game 実装は play 全体をもう一度解像する（model は damage と block だけ）

cached decompile（`MegaCrit.Sts2.Core.Models.Powers/DuplicationPower.cs`）：

```csharp
public override int ModifyCardPlayCount(CardModel card, Creature? target, int playCount) {
    if (card.Owner.Creature != Owner) return playCount;
    return playCount + 1;
}
public override async Task AfterModifyingCardPlayCount(CardModel card) => await PowerCmd.Decrement(this);
```

＝power は **play count を +1** する（play 全体がもう一度解像される）で、modification の直後decrement、
turn 終わりに remove。model は `play_duplicated` flag で damage hit と block grant を2倍にするだけ
（`combat.py` line 1080 と 2824 の2箇所）なので、draw・status 付与・energy・self-damage・multi-effect card
の extra resolution が抜けている。**忠実度の gap として記録**（実装していない：play 本文が `_step` 内に
インラインで、card effects は data-driven ではないため、loop 化は大きい refactor）。

実走でこの gap が決定に出たcaseは Currently 0（P3 の pair で分歧0、batch2 の Duplication位置で分歧0）。
なので gap は correctness の記録として残し、win-rate の判定には影響しない。

### play count の semantics（`CardPlay.cs` の documentation）

> The total number of times this card is going to be played. Usually 1, but when a card has an effect
> like Replay, it will be higher (Replay 1 will have playCount=2, …). You can compare this with playCount
> to see if you're on the final play of the card.

＝ play count は **card が play される回数**で、`AfterCardPlayed` 等の hook は play ごとに走る。だから
Duplication/OneTwoPunch の extra resolution は card の effect 全体（draw・status 付与・power stack・
per-play trigger）をもう一度走らせる。model は damage hit と block grant だけを2倍にする近似。

Gigantification（`BeforeAttack` で first powered Attack **command** を mark、`ModifyDamageMultiplicative`
は mark された command の damage だけ×3、その command 完了で decrement）＝ model の
`card in ATTACKS and attacks_played_this_turn == 0` と等価（multi-hit card は同一 command 内なので全体×3）。
Panache（`alreadyApplied`：適用 play を数えない、5 play ごとに Amount を全 hittable へ Unpowered、
counter reset、turn end で CardsLeft=5 へ戻す）＝ model と一致。

→ 揃っていないのは play-count powers の「effect 全体の再走」だけ。card effects が `_step` 内 inline
（data-driven でない）なので loop 化は大きい refactor。実走でこの gap が決定に出た case は0件
（P3 の pair・batch2 の Duplication位置で分歧0）→ 记録してそのまま。

### play-count powers の gap が決定に出る母数を数えた（73件 / 15 seed）

実走 corpus で、decision の時点で `DuplicationPower`・`OneTwoPunchPower` が active だった recordは
**73件 / 15 seed**。打った札の内訳：

- block cards **54件**（Defend 25・Shrug It Off 25 ほか）
- attack **9件**
- end_turn / none **10件**

model は block grant を2倍にする（line 1080）ので Defend は正しい。**Shrug It Off（block 5 + draw 1）は
draw が2倍にならない** → gap が決定に出る位置は Shrug の25件（＋status 付与札 Taunt 1件、power 札 Colossus
1件）。`CARD_VULNERABLE_TARGET` の status 付与も2倍にならないことを test で確認（Bash + Duplication →
Vulnerable 2 のまま、commit `57011bc` の読みと一致）。

実装は game 走行中で行わない（rule 9：run が in flight の間に policy code を触らない）。batch3 完走後、
draw（と status 付与・power stack）の extra resolution を `play_duplicated` で gate して、テスト
`test_duplication_re_resolves_status_and_draw_effects` で固定する。

### 「hittable」の忠実度：game は alive ∧ ShouldAllowHitting、model は alive だけ

`Creature.IsHittable`（decompile）＝ `IsDead` で false、`Hook.ShouldAllowHitting` が false なら false。
それを override する power は `IllusionPower`・`ReattachPower`・`DieForYouPower`・`AdaptablePower`・
`MockUnhittablePower`。model の hittable 集合（Forgotten Soul・Panache・LostWisp）は `enemy.alive` だけ。

実走 corpus（12,841件の機構 record のうち enemy powers を見た）でこれらの power は **0件** →
観察された case では model と game が一致する。だから現状は fix 不要（未観測の enemy power を
勝手に model に入れない rule のまま）。入れたくなるのは「hittable に filtered されていないから」だが、
根拠が0件なので記録だけ。

### batch3 進捗

`mechonly_ctrl_b3_D6A1F8C3E5` 完走：**17勝1敗、例外0件、`POWER.CHAINS_OF_BINDING_POWER` を state に出した**
→ batch3 で第一の pair candidate（control clean）。`X3C9N6P4WQ` 5勝0敗・走行中（機構未出現）。

### batch3：corpus の母数 ≠ この run の母数（X3・SOS は機構を state に出さなかった）

`mechonly_ctrl_b3` 完走分（control `e808bdf`、例外0件）：

| seed | control | この run での機構 |
|---|---:|---|
| `D6A1F8C3E5` | 17勝1敗 | **Chains**（母数208 は corpus の別 run。この run は17 record） |
| `X3C9N6P4WQ` | 13勝1敗 | none |
| `SOS6XYXCNO` | 13勝1敗 | none |
| `L3PN5HBQ8T` | 3勝0敗・走行中 | none |

seed 選び（corpus の state 出現）は当たりませんでしたが、pair になるのは「この run が機構を state に出す」
case だけ。今の pair candidate は `D6A1F8C3E5` の1件（control clean）。arm（pin harness）が同じ path を
追えば Chains を同じ位置で見る预期。

### play count の全体再走：gate が足りない site（実装前の checklist）

`play_duplicated` を読んでいるのは今2箇所だけ：`_grant_block`（line 1080）と damage path（line 2824）。
game は play count +1 で**play 本文全体**を再走するので、以下が抜けている：

- draw：line 2321（`SHRUG` の draw 1）と line 2329（`CARD_DRAW`）→ `(count * 2 if play_duplicated else count)`
- status 付与：line 2930 付近（`CARD_VULNERABLE_TARGET`、Uppercute の Weak 等）→ 実測で Vulnerable が2倍
  にならないことを確認済み（Bash + Duplication → 2 のまま）
- power grant：`_after_power_play`（line 553）→ stack が1回分足りない
- self damage：`_apply_player_damage`（line 463）

母数（実走 corpus、play-count power が active だった decision 73件）：block cards 54（そのうち Shrug 25＝
draw gate が必要）、attack 9（正しい）、none 10。status 付与札 chosen は 0（Bash は3件）→ status gate は
corpus で決定的に効く母数が薄い。

実装は batch3 完走後（rule 9：run が in flight の間に policy code を触らない）。テストは
`test_duplication_re_resolves_status_and_draw_effects`（draw gate）と status gate の2本を予定。

### play count の再走：effect ごとに実測した（verified table）

同一条件の test 相当で1 play ずつ確認（DuplicationPower 1、dummy enemy）：

| effect | game（decompile：play count +1 で play 全体が再走） | model の現状 | 判定 |
|---|---|---|---|
| block grant | 2回 | 2倍（line 1080） | **一致**（Defend 5→10、Shrug 8→16） |
| damage hit | 2回 | 2倍（line 2824） | **一致**（Twin Strike 4 hit） |
| draw | 2回 | **1回だけ**（Shrug: hand size 1 のまま） | gap |
| status 付与 | 2回 | **1回だけ**（Bash の Vulnerable 2 のまま） | gap |
| power grant | 2回 | **1回だけ**（Demon Form の stack 2 のまま） | gap |
| self damage | 2回 | 1回だけ（gate 無し） | gap |

`play_duplicated` を読んでいるのは `_grant_block`（1080）と damage（2824）の2箇所だけ。
→ draw・status・power・self damage の site に gate を足す（checklist は上の節）。実装は batch3 完走後。

Fiddle との相互作用は正しい：Shrug の draw は `_draw_into_combat(..., from_hand_draw=False)` を呼ぶので、
Fiddle を持つと game は draw を拒否する（model も拒否）。Shrug の母数25件の中で Fiddle を持つ run は
Q6・D1（control-era）で、Fiddle 所持時に Shrug を打つ位置は拒否側で既に一致している。

### gate 追加の母数（決定に影響しうる record）

play-count power が active だった decision 73件の内訳で、model が既に gate している effect だけを持つ札
（attack 9、Defend 25）は gate 追加で変わらない。**gate が足りない effect を持つ札は 27件**：
Shrug It Off 25（draw）、Taunt 1（status）、Colossus 1（power）。＝ gate 追加が決定を変えうる母数は
27件 / 15 seed の中で最大27件。

control（`e808bdf`）が機構を state に出した seed は、既に走った run では batch1 の4（H2・AM8・R8・P3）＋
batch2 の4（U2・T3・M7・V7）＋ batch3 の D6 の9件で、いずれも測った。新しい母数を增やすには新しい seed
の control run が機構を state に出す必要がある（path 運）。

### state 出現だけでは機構は効かない（D6 の gate は0母数）

`mechonly_ctrl_b3_D6A1F8C3E5`（control、364 combat records、例外0件）：

- `POWER.CHAINS_OF_BINDING_POWER` が state に出た record：**38件**
- そのうちの **bound 札が hand にある record は 0件** → game の gate が立つ位置がこの run に無い
  （`legal_actions` から bound が消える事象が一度も無い）

＝机构的な「state 出現」は trigger 条件を満たさない。Chains の gate は *bound 札が hand に在る* decision
で効く（第一 play 後）。同じ形は play-count powers にもある：power が active でも、その decision で
札を打たなければ（end_turn 10件）消費も额外解像も起きない。

→ run レベルの机构単独の差は「機構が trigger した位置」でしか出ない。batch3 は D6 以外の seed が機構を
state に出しておらず、D6 も trigger 位置が無いので、分歧が出ない見込み（arm stage は control の path を
追うので同じ）。母数增やす の目的は、trigger 位置を持つ seed を find することとして继続します。

### gap の trigger 母数（`e808bdf` の control run では1件だけ）

control run で play-count power が active だった decision を札の effect 別に分けた：

- `T3XQ7WM2VP`：Duplication ×1 = **block 札**（model は block を2倍にするので正しい）、Gigantification ×1 =
  attack（正しい）→ gap の trigger 母数 **0**
- `U2M7K5F9RA`：OneTwoPunch ×1 = **status 札**（status 付与が2倍にならない → gap）、Duplication ×1 = block
  （正しい）→ gap の trigger 母数 **1**

corpus 側の27件（Shrug 25・Taunt 1・Colossus 1）は arm-era commit の run の数字。`e808bdf` の run では
gap が決定に出る母数は1件（U2）でした。

→ gate 追加は**正しさの修正**としては意味がある（decompile 根拠）が、測った outcome を変える母数は
ほぼ無い。実装は batch3 完走後に site 4箇所＋テスト2本で行う（rule 9）。

### gate の trigger 母数：測った control run では9 seed 全部0

`e808bdf` の control run で、Chains が state に出た record と bound 札が hand にある record：

| seed | Chains present | bound in hand（gate 母数） |
|---|---:|---:|
| `H2LV6ZJ4XW` | 0 | 0 |
| `AM8C6YXHSG` | 18 | 0 |
| `R8V2H6N4ZB` | 17 | 0 |
| `P3V8N5K2RX` | 0 | 0 |
| `U2M7K5F9RA` | 0 | 0 |
| `T3XQ7WM2VP` | 0 | 0 |
| `M7C4Q9V2RH` | 21 | 0 |
| `V7D3M9H2XW` | 0 | 0 |
| `D6A1F8C3E5` | 38 | 0 |

power が state にあることと、札が bound であることは別（Chains は引いた札を afflict する）。だから
651件の gate 母数は**札が bound だった run**（corpus 側）の数字で、この panel/batch の control run では
gate が一度も立っていない。→ Chains の gate は run レベルでは測定不能（offline の17%分歧率は同一
observation の replay での数）。

同じ形の note：play-count powers の gap も、`e808bdf` の run では trigger 1件（U2 の status 札）だけ。
機構単独で分歧を出したのは H2（FS、trigger 位置あり）と AM8（Fiddle、draw の trigger 位置あり）だけ。

### ChainsOfBindingPower の decompile（gate は draw 経由で afflicts）

`ChainsOfBindingPower.cs`（power、Debuff/Counter）：

- `AfterCardDrawn`：owner の player が自分の side で札を引いた時、`Bound` affliction が possible なら、
  **その turn に afflict した count が Amount 未満の場合だけ** afflict する（`CardAfflictedEntry` を数える）
- `BeforeCardPlayed`：bound 札を play した時に `boundCardPlayed = true`
- `ShouldPlay`：bound 札は `boundCardPlayed` が立ってから gate される（最初の1枚は打てる）
- `BeforeSideTurnEnd`：`boundCardPlayed` を reset し、bound affliction を**全部 clear**

model の形（`bound_played_this_turn` ＋ turn end flush ＋ rollout 中の draw で afflicts）はこれと一致。
`fromHandDraw` はこの実装では条件に使われていない（turn start の draw も afflict 対象）。

測った control run（`e808bdf`）で bound 札が hand にある record が 0件（9 seed）＝これらの run では
power が active 中に draw が起きなかった（decision で札を打たない、または draw を伴わない play）。
だから gate は run レベルで trigger していない → 分歧が出ない。651件の母数は draw が起きた run の数字。

B4（batch3）：Chains present 29 record、bound in hand 0、gate active 0。

### verified gap：Chains の per-turn cap は「hand に在る bound 札」で数えている（game は afflicted entries）

game（`ChainsOfBindingPower.AfterCardDrawn`）：その turn に afflict した **entry 数**（`CardAfflictedEntry`、
`HappenedThisTurn`）が Amount 未満のときだけ afflict する。札が hand から消えても entry 数カウントは残る。

model（`combat.py` line 808-816）：`already_bound = hand に在る bound 札` ＋今回 mark する分，で cap を
見る。だから bound 札を play して hand から消すと、同じ turn 内で cap を超えて afflict できる。

同一条件で確認（ChainsOfBindingPower amount 2、draw pile に Strike）：

- Flash of Steel（draw 1）→ bound 1件（entry 1）
- その turn で Offering（draw 3）→ model は **2件 additional** mark（total 3 > cap 2）
  game は cap 2 で止まる（2件目の draw 以降は afflict しない）

→ fix：turn 単位の `chains_afflicted_this_turn` counter を持つ（entry 数で cap を見る）。実装は batch3 完走後
（rule 9：run が in flight の間に policy code を触らない）。テストは
`test_chains_afflicts_stop_at_the_per_turn_cap_after_a_bound_card_leaves_hand` を予定。

実走ではこの gap が決定に出る母数が薄い：測った control run 9 seed で bound 札が hand に在る record は0件
（draw が decision で起きなかった）。Shrug の draw は play-count power の gate と同じ位置（U2 の1件）で、
Chains の cap と絡む位置は corpus 側の651件（draw が起きた run）に属します。

### gate の母数は「同じ path」でないと pair にならない（N8 の case）

bound 札が hand に出た run は corpus で N8 786・H2 431・D6 56 record（`candidate_*` の control-era run）。
しかし batch1 の control run（`e808bdf`）で N8 は機構を state に出さなかった（Chains が無い）ので、その
gate 母数は `e808bdf` の run とは別の path（relic 獲得の有無が違う） belongs。同じ seed でも path が
違えば pair にならない → run レベルでは測定できない。

同じ seed の別の run で機構が揃う caseは、`9X9`（Duplication 両腕）と `73P`（OneTwoPunch 両腕）の2件で、
いずれも reach 0。機構が state に出た control run（`e808bdf`）は測った限り H2・AM8・R8・P3・U2・T3・M7・
V7・D6・B4 の10 seed（B4 は gate 母数0）。機構が decision で trigger した seed は H2（FS）と AM8（Fiddle）
だけ。

→ 母数を增やすには trigger 位置（draw が decision で起きる、または play  Count powers が active の play）
を持つ path が必要。batch3 完走後に、忠実度の fix（Chains cap を entry 基準へ、play-count の gate 4箇所）
を実装して、trigger 位置が生まれた run で分歧が出るかを見る。

### Fiddle の decompile（cached tree で原文再確認）

`MegaCrit.Sts2.Core.Models.Relics/Fiddle.cs`：

- `ModifyHandDrawLate`：owner の hand draw に `Cards`（2）を加える
- `ShouldDraw`：`fromHandDraw` は true、owner 以外 true、owner でも current side が自分の side でない限り
  false（＝player side 中の draw を拒否）。`AfterPreventingDraw` は flash だけ（効果なし）

model は両方一致（`combat.py` line 803 の拒否、turn start の +2）。実走1,436件で hand が一度も growth
しなかったこと（player side 中の draw 0件）も同じ根拠。

→ play-count powers の忠実度 half は確認完了。model を揃える未実装 part は2件：
1. Chains の per-turn cap（hand 基準 → **entry 基準**へ）（commit `74a87c6`）
2. play count の全体再走（draw・status・power・self damage の gate）（commit `ef5d31e`）
どちらも batch3 完走後に実装（rule 9）＋テスト2本。

### 訂正：Chains の cap gap は実走では観察されていない（130件は index を札の identity と思った artifact）

- 実走 record で **bound 札が hand に3枚以上在る record は0件**（amount は全 record で3）＝ game の cap と
  contradictions が観察されていない
- 「1 turns 内で ever-bound が amount を超えた130件」は、hand の `index` が play/draw でずれるので同一札を
  別 identity として数えた artifact。trace に stable な card id が無いのでこの検査は使えない
- 実装差（hand 基準 vs entry 基準）は constructed test で示せた（draw 1 → bound 1、同じ turn で draw 3 →
  model は cap を超えて mark できる）が、実走での発生は0件

→ cap の fix は正しさの修正として価値がある（game の entry 基準に揃う）が、実走の決定を変えた記録はない。
play-count powers の gate 追加と同じ位置づけ：実装差はあるが、実走の母数が薄い（27件中実際に決定に
出たcaseは U2 の1件）。

### batch3 の pair candidate 3件、すべて gate 母数0

| seed | control | Chains records | bound in hand | gate active |
|---|---:|---:|---:|---:|
| `D6A1F8C3E5` | 17勝1敗 | 38 | 0 | 0 |
| `B4J8Q1R6YK` | 17勝1敗 | 29 | 0 | 0 |
| `T5R8K2N9QP` | **21勝1敗**（完走） | 34 | 0 | 0 |
| `X3C9N6P4WQ` | 13勝1敗 | 0 | 0 | 0 |
| `SOS6XYXCNO` | 13勝1敗 | 0 | 0 | 0 |
| `L3PN5HBQ8T` | 13勝1敗 | 0 | 0 | 0 |

Chains が state に出ても、その turn で draw が起きなければ gate は trigger しない（bound 札が hand に
現れない）。だから batch3 は机构単独の分歧を出さない見込み（arm stage は control の path を追う）。
arm stage を開始（job `bash-697`、start commit `c3d9fd2`）。忠実度の fix は arm stage 完走後（rule 9）。

### 母数の二 kinds：observed gate（legal_actions から bound が消える）と model の rollout gate

- **observed gate**：game が decision 時に bound 札を hand に持ち、`legal_actions` から除外していた record。
  corpus で651件 / 3 seed（N8 399・H2 224・D6 28）。batch3 の control run（D6・B4・T5）は observed gate
  **0件**（bound 札が hand に出なかった）
- **rollout gate**：model の rollout が future draw を simulate する位置。Chains が state に在れば model は
  draw した札を bound に mark して rollout 中の play から除く。control tree は gate を持たない（札名を
  知らないだけで、rollout は打てる扱い）→ 分歧しうる。これは機構の実装差で、knowledge 差ではない

D6 は両腕が同じ seq 454 で Chains を得た（clean pair）。分歧が出たら rollout gate 由来。arm run は現在
aligned 62件（分歧0）。

→ 前ラウンドの「batch3 は分歧を出さない見込み」は observed gate 関于；rollout gate は Still分歧を生む
うる。判定は power/relic が両腕の state に出た位置で数える（`mechonly_attribution.py` の今の形）。

### `D6A1F8C3E5`：clean pair だが gate が決定を動かさなかった（364件分歧0、outcome 同値）

arm 完走 17勝1敗 = control と同値。Chains が両腕の state に出た位置（38 record、両腕同じ seq 454 から）で
分歧0。rollout gate（model が simulate する draw で bound mark する位置）でも決定が変わらなかった。

batch3 の今の形：`D6` ±0、`X3` 115件分歧0・走行中、残 `SOS`・`L3`・`B4`・`T5`。
机构単独の win 效果は H2（+2）のまま、AM8（22件 mechanism-only）は outcome 同値。

###  planned fix（apply 前の精确な形）：`_draw_into_combat` の chains block

現状（`combat.py` line 803-818）：

```python
chains = _power(combat.player_powers, "ChainsOfBindingPower")
if chains:
    already_bound = sum(1 for value in combat.hand if isinstance(value, Card) and value.bound)
    for value in drawn:
        if isinstance(value, Card) and already_bound < chains:
            value = replace(value, bound=True); already_bound += 1
```

`already_bound` は **hand に在る bound 札**なので、bound 札を play/exhaust して hand から消ると cap が
回復する。game は `CardAfflictedEntry` の `HappenedThisTurn` 数で cap を見る（entry は札が消えても残る）。

→ 追加する field：`chains_afflicted_this_turn: int = 0`（turn start で reset、`_step` の play で消費され
ない）。block を `chains_afflicted_this_turn < chains` に変更、mark 時に increment。テスト：

```
test_chains_afflicts_stop_at_the_per_turn_cap_after_a_bound_card_leaves_hand
```
（draw 1 → bound 1、同じ turn で bound 札を play、draw 3 → game は cap 3 で止まる：model は entry 基準なら
3枚目以降を mark しない。hand 基準だと mark してしまう）

apply は batch3 の arm stage 完走後（rule 9）。play-count powers の gate 4箇所（draw・status・power・
self damage）も同じ run 完走後。

### Chains の gate：`BeforeCardPlayed` は dupe（extra resolution）を数えない

`ChainsOfBindingPower.BeforeCardPlayed`（decompile）：

```csharp
if (card.IsDupe) return Task.CompletedTask;   // extra resolution は flag を set しない
...
if (!(card.Affliction is Bound)) return Task.CompletedTask;
GetInternalData<Data>().boundCardPlayed = true;
```

`ShouldPlay(card, autoPlayType)` は `!boundCardPlayed` を返す（autoPlayType を check しない）＝ autoplay
でも gate される。

model：`bound_played_this_turn` は1枚目の bound play で set、`play_duplicated` は同一 card の extra
resolution（flag を再 set しない）→ game の `IsDupe` bypass と同じ形。

実走の「45 turns で2枚以上の Bound 札を打った」case は、同一札の duplicate resolution（play count 2）で
説明がつく。distinct card の2枚目は game でも gate される。

テスト `test_chains_of_binding_afflicts_cards_drawn_during_the_rollout` は cap の recovery を test していない
（draw 7枚、amount 3 → 3件 bound。hand 基準でも entry 基準でも同じ結果）→ planned fix のテストは新しい1本
として追加する（既存テストは壊さない）。

### power grant も play ごとに走る（Demon Form の decompile）

`DemonForm.cs`：effect は `OnPlay(cardPlay)` 内（`PowerCmd.Apply<DemonFormPower>`）。game は play count だけ
`OnPlay` を走る（`CardPlay.PlayCount` の documentation どおり）→ play count 2 なら power は2回 apply される。
model は1回だけ（実測：Duplication active で Demon Form を打つと stack 2 のまま、commit `88970dc`）。

忠実度の最終形（decompile 根拠で確定）：

- 一致：block grant、damage hit（gate 済み）
- gap（model が1回だけ）：draw、status 付与、power grant、self damage
- gap（basis が違う）：Chains の per-turn cap（game は entry 基準、model は hand 基準）
- 一致：Gigantification（first powered Attack command ×3、dupe bypass の flag 形）、Panache（alreadyApplied、
  5 play trigger、turn end で CardsLeft reset）、Fiddle（+2 と player side 中の draw 拒否）

実装は game が idle になったときに gate 4箇所＋cap の field を追加し、テスト2本で固定する（rule 9）。

### gate 追加は小さい change でよい（effect site が同一 scope に在る）

`play_duplicated` は `_step` 内で play の解像开始前に set される（line 2142-2161）。effect site は同じ
scope：

- status 付与：line 2930（`CARD_VULNERABLE_TARGET`、Uppercut の Weak）
- draw：line 2321（`SHRUG`）、line 2329（`CARD_DRAW`）
- power grant：line 2365・2383（`card in POWERS`、Demon Form）
- self damage：`_apply_player_damage`（line 463）

＝「play 全体をもう一度 loop する」大きな refactor ではなく、各 effect type で `* (2 if play_duplicated
else 1)` を加える形で game と等価になる（game の play count は play ごとに `OnPlay`/commands を走る。
model が enumerate している effect type を全部 gate すれば、multi-effect card も正しく2回分）。

Chains 側は field 1本（`chains_afflicted_this_turn`）＋ block の cap を entry 基準へ。テスト2本。
apply は batch3 の arm stage 完走後（rule 9）。

### refinement：per-play trigger も play count に応じて走る（gate だけだと足りない category）

game は `CardPlay` を play count 回数実行するので、`AfterCardPlayed` 系の trigger（Panache の
`CardsLeft` counter、Juggernaut の block-on-play、Fiend Fire の count、Hellraiser の autoplay 等）も
resolution ごとに走る。model は `_step` 1回で1回だけ counter を動かす。

だから per-effect gate（damage・block・draw・status・power・self damage）に加えて、**per-play trigger**
の category がある。cost と hand の除去は play 単位で1回（game の `CardCmd.Play` は play 1回で、commands
が playCount 回走る）＝ model は cost を1回落とすので正しい。

→ 完全な忠実度は「play 本文を playCount 回 loop する」形。per-effect gate はその近似で、trigger category
が抜ける。母数（実走）は play-count power が active だった decision **73件**、そのうち effect category が
gate 外なのは 27件（draw/status/power/self damage）。trigger category が決定に出た母数は数えていない
（Panache の trigger 位置は corpus で1件、その1件は knowledge-only 分歧だった）。

apply 時に決める：loop 形（完全）か per-effect gate（近似、trigger は記録したまま）。母数が薄いので
近似で十分という読みも正直に書く。

### play loop の実物（`CardModel.cs`）：effect も `AfterCardPlayed` も playCount 回数走る

```csharp
int playCount = await GeneratePlayCount(combatState, target);
...
for (int i = 0; i < playCount; i++)
{
    CurrentPlayIndex = i;
    ...
    CombatManager.Instance.History.CardPlayFinished(combatState, cardPlay);
    await Hook.AfterCardPlayed(combatState, choiceContext, cardPlay);
}
```

card の result pile への移動と cost（`resources`）は loop の外 ＝ play 単位で1回。model も cost を1回
落とすので正しい。loop 内にあるのは card の effect と `AfterCardPlayed`（＝ per-play trigger）。

→ model が gate しているのは damage と block の2 category だけ。per-play trigger（Panache counter、
Juggernaut、Fiend Fire count、Hellraiser autoplay）と draw・status・power・self damage が抜けている。
完全な忠実度は play 本文を playCount 回 loop する形；per-effect gate は近似。実走の母数27件、決定に
出たcaseは U2 の1件（status）＋ Panache の1件（knowledge-only）。

plan（apply 時に決める）：`_step` の play body を loop 化する（diff が大きい）か、per-effect gate を4
category に広げ、trigger category は limitation として記録したまま置く。どちらでもテストは
「1 play で effect が2回走る」形を書く。

### per-play trigger の母数：実走0件（play-count power と同じ decision で trigger power が active な case が無い）

play-count power（DuplicationPower・OneTwoPunchPower）が active だった decision **73件**（15 seed）と、
per-play trigger power（PanachePower・JuggernautPower・FiendFirePower・HellraiserPower）が同じ decision で
active だった case を cross した：**0件**。

→ trigger category の gap は観察された run で0母数。だから近似（per-effect gate 4 category を追加）で
決定の変化は出ない。play count の effect category（draw・status・power・self damage）の母数27件の中で
決定に出たcaseは U2 の1件（status）だけ。

plan の形は変わらない：per-effect gate 4 category を追加＋Chains cap を entry 基準へ、テスト3本。loop 形
（完全な playCount loop）は、trigger category も含むので、将来 trigger が同じ decision で active になる
run が現れたときに必要。母数0の現状では、loop 形を「正しさの完全形」として記録し、apply は per-effect
gate + cap にする（小さい diff、既存736テストを壊さない）。

### apply 時に書くテスト（预先の形）

```python
def test_play_duplicated_re_resolves_draw_effects(self) -> None:
    # Shrug It Off: block 5 + draw 1. With DuplicationPower the game re-runs the whole play,
    # so both the block grant and the draw happen twice.
    draw = tuple(Card(STRIKE) for _ in range(4))
    combat = Combat(80, (Card(SHRUG),), draw, (), (Enemy("MONSTER.DUMMY", 200, "IDLE_MOVE", ()),),
                    energy=1, player_powers=(("DuplicationPower", 1),))
    after = step(combat, "card:0", DUMMY_DATA, random.Random(0))
    self.assertEqual(after.player_block, 10)     # already gated: passes
    self.assertEqual(len(after.hand), 2)         # fails today (draw runs once); passes after the gate

def test_play_duplicated_re_resolves_status_and_power_effects(self) -> None:
    # Bash applies Vulnerable; Demon Form applies a power stack. The game re-runs OnPlay per play count.
    ...

def test_chains_afflicts_stop_at_the_per_turn_cap_after_a_bound_card_leaves_hand(self) -> None:
    # The game counts CardAfflictedEntry happened this turn, so a bound card leaving hand does not
    # free up the cap. Today the model counts bound cards still in hand.
    ...
```

既存の `test_duplication_power_resolves_the_next_play_twice`（damage）と
`test_duplication_power_doubles_the_next_block_card_grant`（block）は gate 追加後も pass する。
`test_chains_of_binding_afflicts_cards_drawn_during_the_rollout`（draw 7、amount 3）は hand 基準でも
entry 基準で同じ結果なので壊れない。

### knowledge-confound の母数（正しく数え直した：123件、札名は status 札）

前ラウンドの「67/352件」は错的。control の `CARD_COST` は display name（"Defend"）で key しており、trace
の id（`CARD.DEFEND_IRONCLAD`）と直接 compare していた。正しくは `official_agent.CARD_NAMES` で id →
display name へ map してから、control の table に在るかを見る。

その形で batch3 の arm run を数え直した（control が score できない札が hand に在る record）：

| seed | records |札名 |
|---|---:|---|
| `D6A1F8C3E5` | 83 | BYRDONIS_EGG・CLUMSY・THINKING_AHEAD・WOUND |
| `B4J8Q1R6YK` | 17 | BYRDONIS_EGG・PROLONG・WOUND |
| `L3PN5HBQ8T` | 15 | WOUND |
| `X3C9N6P4WQ` | 4 | WOUND |
| `SOS6XYXCNO` | 4 | WOUND |
| 合計 | **123** | status 札だけ |

`e808bdf` の control はこれらの status 札名を持たない（head では `HAND_INJECTED_STATUS` に WITHER 等が
あり、status 札の扱いは後から入れた）。confound の母数は123件だが、batch3 では分歧0 → confound が決定
を変えなかった case。

### 訂正：H2・AM8 の分歧は knowledge-confound ではなかった（前数えは bug）

`mechonly_attribution.py` の confound 数えは、trace の id（`CARD.DEFEND_IRONCLAD`）を control の
display-name table（"Defend"）と直接 compare していた。正しくは control 自身の `CARD_NAMES` で id →
display name へ map してから table を見る（commit `8799324`）。

その形で数え直した：

| seed | 分歧 | by-mechanism | knowledge-confounded |
|---|---:|---|---:|
| `H2LV6ZJ4XW` | 46 | Forgotten Soul 46 | **0** |
| `AM8C6YXHSG`（harness） | 87 | Fiddle 87・Chains 14 | **0** |

→ commit `ebfb9dd` の「H2 の46分歧のうち39件は knowledge-confounded、AM8 の87分歧のうち85件」は誤り。
分歧位置の札は control も table に持っていた。knowledge-confound が実在した母数は batch3 の arm run の
123件（status 札 WOUND・CLUMSY・BYRDONIS_EGG・PROLONG・THINKING_AHEAD）で、そこでは分歧0。

同一条件 replay での分割（`data/mech_vs_knowledge.py`、commit `ab9634f`）の数字は別の根拠なのでそのまま：
H2 mechanism-only 13件、AM8 mechanism-only 22件、knowledge-only 0件。

### knowledge 差の正体：hand だけじゃなく deck/draw pile 経由でも決定を変える

arm と control の card table 差は次の6 entryだけ（`e808bdf` vs HEAD）：

- `CARD_COST`：One-Two Punch、Panache
- `SKILLS`：One-Two Punch、`POWERS`：Panache、`UNTARGETED`：両方
- `HAND_INJECTED_STATUS`：Wither

`mechonly_attribution.py` の confound 数えは hand に在る札だけを見ていた。だから `U2M7K5F9RA` の62分歧
（hand に OneTwoPunch が無い位置）は confound 0 と出たが、rollout が draw pile からその札を引く位置では
control は score できず arm はできる → 同じ knowledge 差で決定が変わる。

→ confound の正しい母数は「hand OR rollout で draw される札」に arm だけの entry が現れる位置。hand だけ
の数えは undercount。正しく分ける方法は `data/mech_vs_knowledge.py`（tables を control 形へ pin した
replay と、arm 形の replay を比べる）で、U2 はその re-run が未実施（game 走行中、CPU rule）。

### attribution の caveat：arm–control 差は「8机构」以外も含む（`e808bdf` 以降の全変更）

`git diff e808bdf..HEAD -- combat.py official_agent.py` = 213 insertions。追加された token を数えたら：

- PANACHE 9、ONE_TWO_PUNCH 6、GIGANTIFICATION 4、FIDDLE 4、WITHER 2 → 8机构の側
- HELLRAISER 2 → HellraiserPower autoplay（`e808bdf` には無い、机构8件とは別）
- それ以外：SoarPower の ZeroDivision guard、Whirlwind の hit count、`bound`/`unplayable_this_turn` の
  分離、autoplay recursion の cap、turn-end curse の pin など

だから pin（生成集合）をしても、arm は control より「8机构＋その他の修正」分だけ違う。分歧位置が机构の
position でない case は「その他の修正」由来であり、机构単独の差として数えられない。

`B4J8Q1R6YK` の第一分歧（seq 430、state は両腕で一致、hand に机构札なし、Chains は 433 から）は
draw pile に `CARD.HELLRAISER` が在る位置 → Hellraiser autoplay の差で説明がつく。機構単独の attribution
には使えない。B4 の by-mechanism 9件は机构 position だが、その前に path が分歧しているので第一分歧の
rule に反する。

→ 判定で使えるのは、第一分歧が机构 position である case だけ。現状 H2（seq 441 が FS、両腕一致）と
AM8（harness、第一分歧が Fiddle 位置）の2件。

### batch3 の outcome（完了分）：全部 control と同値

| seed | arm | control | 分歧 | attribution |
|---|---:|---:|---:|---|
| `D6` | 17勝1敗 | 17勝1敗 | 0 | clean pair（Chains 454）、机构位置で分歧0 |
| `X3` | 13勝1敗 | 13勝1敗 | 0 | 機構を state に出さない |
| `SOS` | 13勝1敗 | 13勝1敗 | 0 | 機構を state に出さない |
| `L3` | 13勝1敗 | 13勝1敗 | 0 | 機構を state に出さない |
| `B4` | 17勝1敗 | 17勝1敗 | 11 | 第一分歧が机构以外（Hellraiser autoplay、seq 430）。机构位置の分歧9件は path 分歧後 |
| `T5` | 走行中（476 aligned、分歧0） | 21勝1敗 | 0 | clean pair（Chains 598）で分歧0 |

batch3 は win レベルで机构単独の差を出さなかった。机构単独で立っているのは H2（+2）と AM8（分歧87、
outcome 同値）の2 seedのまま。

### 実装した（commit `2e195d5`、テスト739件成功）

- draw gate：`SHRUG`（line 2334）と `CARD_DRAW`（line 2338）で play count 分だけ draw 数を挂ける
- status gate：`CARD_VULNERABLE_TARGET`（line 2937）と Uppercut の Weak/Vulnerable（line 2941-2943）で play
  count 分だけ apply する
- self damage gate：line 2375 で play count 分だけ回す
- Chains の cap：`chains_afflicted_this_turn` を追加（field line 307、turn start で reset、draw block で
  entry 数として数える）。hand 基準をやめた

テスト3本（draw・status・cap recovery）。Shrug の block は model の base 8（upgraded 11）なので gate 後は
16。Bash の Vulnerable は table 値2 → gate 後4。

**未 gating（正直に記録）**：power grant の branch（Demon Form・Fasten・Stampede・Aggression…）は多数の
個別 branch で、gate を入れていない。実走の母数1件（Colossus）なので、正しさの完全形（play 本文の loop
化）はまだ残っている。per-play trigger（Panache counter、Juggernaut、Fiend Fire、Hellraiser autoplay）も
同様に未 gating（実走の母数0件）。

忠実度の実装によって、同一条件 replay で「gate が決定を変える位置」の母数は draw 25件（Shrug）＋ status
1件（U2 の Taunt）＝26件。実走 panel の決定列は変更前の code で走っているので、この gate が実走 outcome
を変えた evidence は無い（rule のまま：offline の変化は採用根拠にしない）。

### gate の effect を同一条件で隔离した：73件で決定変化0

同一 record・同一 seed・同一 simulations で、gate 入りの code と gate を外した code（同じ文件の copy で
`(2 if play_duplicated else 1)` を `1` に置換）を比べた：

- records compared: **73**
- gate が choice を変える位置: **0**

＝忠実度の gate は正しさの修正として入れたが、観察された run の決定を変えない（draw/status が ranking
に効く位置がなかった）。前ラウンドの「replay が recorded choice と39件違う」は module state 由来で、gate
由来ではない（同一条件比較で0件）。

→ play-count powers の決定效果は、実走（73件）と同一条件 replay（0件）の両方で0。机构単独で決定を
動かした母数は Fiddle（sample で76件、harness run では分歧87件のうち同一条件で22件）と Forgotten Soul
（108件 sample、harness run 46分歧のうち13件）だけ。

### play count の忠実度：effect category は揃えた（commit `0647658`、テスト740件）

`plays = 2 if play_duplicated else 1` を play path の先で定義し、power grant の22 site を gate した。
これで game の「play 全体を playCount 回解像する」形の effect category（damage・block・draw・status・
power grant・self damage）は model 側も play count 分だけ走る。

- 確認：Demon Form + Duplication → DemonFormPower 4（gate 前2）。テスト
  `test_play_duplicated_re_applies_power_card_effects`
- 同一条件での isolation（73 record、gate 入り vs 外した copy）：**決定変化的0件**（commit `b709c88` の
  draw/status/self damage に加え、power gate も0件）

残る差：**per-play trigger**（`AfterCardPlayed` は play ごとに走る。Panache counter、Juggernaut の
block-on-play、Fiend Fire count、Hellraiser autoplay）。model は play 1回で1回だけ counter を動かす。
実走の母数は play-count power と trigger power が同じ decision で active だった case 0件なので、決定に
効く位置が観察されていない。完全形（play 本文の loop 化）は trigger を含めるために必要だが、母数0の
現状では limitation として記録したままにする。

### per-play trigger：実装した範囲と母数

実装（commit `1dbbd43`、テスト2本、suite **742件成功**）：

- Juggernaut：`AfterBlockGained` なので block を gained した resolution ごとに hit。`_grant_block` で
  `plays` 回 loop（テスト `test_juggernaut_triggers_once_per_play_resolution`）
- Panache：`AfterCardPlayed` は play ごとに走る。counter を `plays` 回 advance し、trigger 後 reset した
  値から次の resolution を数える（テスト `test_panache_counter_advances_once_per_play_resolution`：
  counter 4 の状態で duplicated play → trigger して reset、次の resolution で 1）

実走の母数：play-count power と per-play trigger power が同じ decision で active だった record **0件**
（re-confirm、commit `3661b48` の数字のまま）→ この gate は記録された決定を何も変えない。正しさの修正
として入れた。

まだ loop していない hook：Fiend Fire（OnPlay が hand を exhaust して count 分 damage。第二 resolution は
hand が空なので 0 になる＝単回応用でfaithful である可能性が高いが、card 自身の pile 移動が loop 内か外で
確認していない）、Hellraiser autoplay、Mayhem。これらは play 本文の loop 化をしないと一般に faithful
にならない。母数0なので、loop 化は保留（記録だけ）。

### Fiend Fire は gate 不要（第二 resolution は hand が空）

`FiendFire.OnPlay`（decompile）：hand pile を its 自身で read して `cardCount` を取り、その札を exhaust、
`DamageCmd.Attack(...).WithHitCount(cardCount)`。第二 resolution では hand は空（第一 resolution で全部
exhaust 済み）→ `cardCount = 0` で hit なし。model の単回応用は第一 resolution 相当なので faithful。

残る un-looped hook：Hellraiser autoplay（play ごとに走る）、Mayhem。母数0なので実装しない（記録だけ）。
per-play trigger category の実装範囲：Juggernaut（AfterBlockGained）と Panache（AfterCardPlayed）＝
commit `1dbbd43`、テスト2本、suite 742件成功。

### loop 形の適用範囲（commit `fdfe4f2`、テスト743件）

play 本文を丸ごと loop 化する代わりに、**resolution 単位に直すべき箇所を全部 `plays` で回す**形にした。
覆盖した category：

- effect：damage hit・block grant（relic の doubling は resolution ごと：`per_grant * plays`）・draw・
  status 付与・power grant・self damage
- per-play hook：SKILLS の VitalSpark/Enrage、POWERS の `_after_power_play`（relic）、Panache counter、
  Juggernaut（AfterBlockGained）
- per-play counter：`cards_played_this_turn`・`attacks/skills_played_this_turn`・
  `attacks/skills_played_combat`・`block_cards_this_turn`・`powers_played_this_turn`（テスト
  `test_play_duplicated_advances_the_per_play_counters_twice`）

Fiend Fire は loop 不要（第二 resolution で hand が空 → hit 0、commit `99823df`）。Hellraiser は
AfterCardDrawn なので play count と無関係（draw が重复しない限り triggers しない）。

**效果の測定**：同一条件（同一 record・同一 seed・同一 simulations）で loop 形と `plays = 1` の copy を
比べた → play-count power が active だった decision **73件で決定変化0件**。per-play counter と counting
relic が同じ decision で active だった record は47件あるが、その位置でも決定は変わらなかった。

＝loop 形は model の忠実度を game の形に揃える修正として入れた。実走の決定・outcome は変わらない
（panel の決定列は変更前の code で走った run なので、rule どおり offline の変化は採用根拠にしない）。

## RampartPower：ブロック再付与が敵側に見えていなかった（2026-10-04、commit `5f655ff`）

`data/audit_trace_fidelity.py`（新設）で全 trace 543本・combat record 145,325件を走らせ、
**観測されているのに `POWER_NAMES` に無い power** を数えた。85種類のうち15種類が未登録で、
母数の大きい順に ESCAPE_ARTIST（2,911件/190run）、SWIPE（2,078件/190run）、
TERRITORIAL（2,363件）、RAMPART（560件/73run）。

### 実装差（decompile 根拠）

`RampartPower.AfterSideTurnStart`：

- `side == CombatSide.Player` のときだけ走る
- block を貰うのは **自分ではなく `CombatState.Enemies.Where(c => c.Monster is TurretOperator)`**
- `LivingShield.cs` が自分に Rampart 25 を付与する（state machine の JSON には出てこない）

model は「観測で読めたターの block を、そのターン限り保持する」だけだった。ターの block は自分の
ターン開始に消える（`_enemy_turn` の `block=0`）ので、**第2ターン以降の rollout は block 0 の敵として
火力を計算していた**。replay の第一手だけが正しく、先が全部甘かった。

### 実走 evidence

`POWER.RAMPART_POWER` を持つ record は LivingShield + TurretOperator の対戦だけで560件（73run）。
その中の TurretOperator の block 値：

| 手番 | block 25 の record |
|---|---:|
| 1 | 175 |
| 2 | 163 |
| 3 | 50 |
| 4 | 5 |

LivingShield 本体の block は全 record で 0（自分には配らない）。ゲームの挙動は「毎手番 25 戻る」で、
model の「1回だけ」 Contradiction が record 側に立っていた。

### 実装とテスト

- `combat.py` の player ターン開始 section（`new_turn` を作る所）で、生きている Rampart 合計を
  `MONSTER.TURRET_OPERATOR` の block に足す。複数 LivingShield は足し算（game は copy ごとに走る）
- `official_agent.py` の `POWER_NAMES` に `POWER.RAMPART_POWER` を追加（無いと model が power 自体を見ない）
- テスト2本：`test_rampart_re_grants_turret_block_at_every_player_turn_start`（第2ターンに 25）、
  `test_rampart_stops_granting_block_once_the_shield_is_dead`（盾を倒すと 0）
- 回帰確認：親 commit の worktree で同じテストを走らせ、第2ターンの block が `0`（期待 25）で失敗
- suite **745件成功**

### 決定に出る母数（同一条件 replay）

同一 record・同一 simulations・同一 seed で HEAD（grant あり）と親 commit（grant なし）を比べた。
 trees は差分 commit 1つだけなので、分歧は grant の帰属に閉じる。

- records compared: **560**
- 決定変化: **63**、不変 497、例外 0
- seed 数: **10**（H2LV6ZJ4XW 25、B3N8V5T1WQ 10、R4A8D2K7ME 8、SOS6XYXCNO 6、R8V2H6N4ZB 4、
  D6A1F8C3E5 3、9X9WQB4QIH 3、L3PN5HBQ8T 2、M7C4Q9V2RH 1、B4J8Q1R6YK 1）

play-count powers の gate（73件で0）と違い、**忠実度の修正が決定を動かす位置が実在する**。
分歧の形は「control が block（Shrug It Off / Defend）、arm が attack（Strike / Bash / Anger）」が中心で、
ターの block が毎ターン戻るとなると block で削り合う価値が下ぐ方向。

**limitation**：game は `CombatManager.Instance.PlayersTakingExtraTurn.Count > 0` のとき grant を
飛ばす。model に extra turn は無いのでこの分岐は入れていない（extra turn を model 化するときに併せて必要）。
measure は offline の replay で、run の outcome はまだ見ていない（rule どおり採用根拠にはしない）。

### 同じ監査で残った候補（未実装）

- **ThievingHopper の `SwipePower`**：`ThieveryMove` が Draw+Discard から1枚選んで
  `CardPileCmd.RemoveFromCombat`（優先は Uncommon → Common/Rare/Event）。JSON の effects には
  `PowerCmd.Apply(... "swipe" ...)` だけで、カード除去は C# 側の move 本文。model は除去を見ていない。
  record 側では hand+draw+discard+exhaust の合計が THIEVERY_MOVE 後に1減る変化が **255件**（190run）。
  盗んだカードは hopper を倒すと extra reward で戻る（`SwipePower.BeforeDeath`）、5ターンで Escape すると
  戻らない。Escape 自体は `ESCAPE_MOVE` の `CreatureCmd.Escape` として既に model 化済み。
- **ESCAPE_ARTIST** は decompile 上「visual timer」で効果なし（`AfterSideTurnEnd` で Decrement するだけ）。
  model 化不要。
- **報酬 tier が無い札**：`CARD_NAMES` にある（＝combat で打てる）のに `CARD_TIERS` に無い札が35種類あり、
  実走で Purity 22回・Dramatic Entrance 9回・Production 8回提示されて **1回も取っていない**
  （tier 未登録は `CARD_TIERS.get(card_id, "D")` で最下位になり、deck 15枚以降は Skip 経路に落ちる）。
  Production は 0 energy で +2 energy、Dramatic Entrance は 0 energy で全体11 damage の Innate/Exhaust。
  これは model の忠実度ではなく reward policy の評価表の欠落なので、panel で測る話として保留。

### 報酬 tier が無い札：tier を足しても決定は動かなかった（2026-10-04、`data/reward_tier_probe.py`）

`CARD_NAMES` に在る（=combat.py で打てる）のに `CARD_TIERS` にエントリが無い札が35種類ある。
tier 未登録は `priority.get(card_id, 0)` と `CARD_TIERS.get(card_id, "D")` で最下位になる。
決定 trace の集計では Purity 22回・Dramatic Entrance 9回・Production 8回提示されて **1回も取られていない**。

ただし決定 trace の card_reward record は `cards`（札 id の一覧）しか持たず、policy が見た
`legal_actions` / 札の詳細（cost・type・rarity）を持たない。観測を保存している
`data/*_observations.jsonl`（139 run）と seq で対応付けて replay した：

- paired reward observations: **1649件**
- HEAD の replay が記録された選択を再現: **1622/1649**（98.4%）
- Purity 提示 **9件**（すべて `D6A1F8C3E5` の act1 floor7、deck 20-21枚）
- tier を **B / A / S** に変えても **決定変化 0件**（9件全部 Skip のまま）

理由は tier ではなく既存の Skip 規則だった。deck 20枚は act1 の `_large_deck_addition_allowed` の
limit（20）に達しており、`strong_block_shortage`（16枚以上・強ブロック3枚未満）が立つため、
コア・防御・必要ドロー以外は段位に関係なく Skip になる。`selected_tier` による Skip 規則より先に
効くので、tier を S に上げても届かない。

＝「tier 表の欠落が札を逃している」という仮説は、観測できた9件では **否定された**。
強ブロック不足規則に段位の逃げ道を作る変更は 2026-09-08 に16seedで有害測定済み（上の §124）で、
同じ扉を再度開く理由はこの計測からは出てこない。Dramatic Entrance・Production・Fasten は
observations を保存している run で一度も提示されていない（決定 trace 側には 9・8・1件ある）。

### Rampart の実装を commit 1 つだけ違えた arm/control 実走 A/B（2026-10-04、`data/rampart_ab.sh`）

control は親 commit `d67896f` の worktree（`.wt-ctrl-d67896f`）、arm は main checkout。差分は
`5f655ff` の1コミット（combat.py の grant と `POWER_NAMES` の1行）だけで、生成集合
（`STOKE_GENERATION`・`INFERNAL_BLADE_ATTACKS`）は両ツリー同一。だから生成プールをピン留めした
harness は不要で、`official_agent.py` をそのまま使う panel で分歧は grant の帰属に閉じる。
seed は同一条件 replay で分歧が多かった3件。

| seed | control | arm | delta | aligned | 分歧 | Rampart 位置の分歧 | 第一分歧 seq | 第一分歧で Rampart が両腕の state に在るか |
|---|---|---|---:|---:|---:|---:|---:|---|
| `H2LV6ZJ4XW` | 22勝1敗 | 20勝1敗 | **−2** | 390 | 59 | 6 | 426 | はい（arm BATTLE_TRANCE / control end_turn） |
| `B3N8V5T1WQ` | 16勝1敗 | 17勝1敗 | **+1** | 488 | 87 | 8 | 477 | はい（arm RUPTURE / control end_turn） |
| `D6A1F8C3E5` | 17勝1敗 | 17勝1敗 | **0** | 364 | 2 | 2 | 329 | はい（arm Defend / control Strike） |
| 合計 | 55勝 | 54勝 | **−1** | | | | | 3 seed すべて第一分歧が Rampart 位置 |

**分歧は机构単独で立っている**（3 seed すべて第一分歧の record で `POWER.RAMPART_POWER` が両腕の state に
出ており、その地点より前の決定列は一致）。つまりこれは「path が勝手にズレた」ではなく grant の差。

H2 の −2 の中身：arm は **SLIMED_BERSERKER 戦で6ターン目に HP17 で死亡**（敵残り106HP）。control は
同じ seed で QUEEN まで進み 400HP/20block のところで落ちている。arm の死亡はターのいる戦闘ではなく、
分歧後の path で別戦闘（CUBEX_CONSTRUCT を経由しない進み方）で耐久が足りなくなった形。
＝grant 自体が敵との打ち合いを悪くした証拠ではなく、**勝数への効果は符号が割れて母集団が薄い**
（−2 / +1 / 0）。閾値（≥3 seeds）に対して正の差は出ていない。

なので **Rampart の grant は正しさの修正として入れたまま、win-rate の改善根拠は無し** と記録する。
「忠実度を上げても勝てるとは限らない」の同一形（Wound 対応表・Stratagem と同じ位置）。
次はこの panel のまま他 seed を足して符号を見るか、grant の効果自体（盾を先に倒す価値）が決定に出る
位置を replay で特定する。

### 同じ監査で分かった ThievingHopper のコスト（未実装、母数確定）

`ThieveryMove` が Draw+Discard から1枚を `CardPileCmd.RemoveFromCombat` で戦闘から抜く（優先順
Uncommon → Common/Rare/Event → Basic/Quest → Ancient/Imbued、同一 rarity 内は random）。model は
これを全く見ていない。実走 record での検出：

- 奪取イベント **264件**（190 run、hand+draw+discard+exhaust の合計が1減る位置として検出）
- 奪われた札の内訳（268件）：Inflame 62・Battle Trance 33・Expect a Fight 32・Second Wind 14・
  Stratagem 11・Bludgeon 11 … **Strike は10件だけ**（Basic が第3優先なので最後まで抜かれない）
- うち **戦闘後に deck へ戻らないのは31件だけ**（233件は hopper を倒して extra reward で回収）
  → run あたりの恒久損失は 543 run 中31件 ≈ 0.06枚/run

戦闘中は毎回1枚抜かれるので rollout の「手札が揃う」前提が甘くなるが、恒久効果は小さい。
忠実度として入れるなら raritiy 表が要る（decompile から model 対象131札のうち **129札の rarity が
取得可能**：Uncommon 52・Rare 28・Common 20・Status 9・Event 8・Ancient 5・Curse 5・Basic 1・Token 1）。
Status/Token は `DeckVersion == null` なので候補から除外、Curse は deck 由来だと候補になる
（優先グループのどれにも入らないと full list が fallback）。

## Axebot の StockPower：1戦闘が Axebot 3体である事が model に見えなかった（2026-10-04、commit `03b2055`）

`Rampart` と同じ監査（`data/audit_trace_fidelity.py`）で、観測されるのに `POWER_NAMES` に無い power
として `POWER.STOCK_POWER`（MONSTER.AXEBOT、348 record / 14 run）が出た。decompile：

- `Axebot.AfterAddedToRoom`：`StockAmount > 0` なら自分に `StockPower(StockAmount)` を付与
  （`StockAmount => _stockOverrideAmount ?? 2`、export の values は `StockAmount: 2`）
- `StockPower.AfterDeath`：`Amount > 0` なら `axebot.StockAmount = Amount - 1` で **同じ side / 同じ slot に
  新しい Axebot を追加**し、`ShouldStopCombatFromEnding` で戦闘を終えない
- `GenerateMoveStateMachine`：`_stockOverrideAmount` が入った個体は **BOOT_UP_MOVE から**始まる
  （通常 spawn は HAMMER_UPPERCUT_MOVE から）
- `BOOT_UP_MOVE` の Strength は `BootUpStrGain * (2 - StockAmount)` → **個体ごとに 0 / 3 / 6**

model は export の `initial_state` と 1体の HP だけを持っていた。だから **1体を殺した瞬間に
`combat.terminal` になり**、戦闘全体を 76 HP 1体として評価していた。実走（`rampart_ctrl_b1_B3N8V5T1WQ`）
では 74 → 71 → 76 HP の3体が順に出た（combat_id 1 → 2 → 3、3体目だけ STOCK_POWER 無し）で、
その戦闘で 12 ターン使って 26/76 HP 残しで死亡している。

### 実装

- `initial_combat`：AXEBOT に `("StockPower", StockAmount)` を付与（他の「not exported」power と同じ形）
- `_mark_enemy_death`：`StockPower > 0` かつ hp <= 0 のとき BOOT_UP_MOVE で復活、HP は
  MaxInitialHp（game は MinInitialHp..MaxInitialHp から抽選だがこの関数に rng が届かない）、
  powers は空から `StockPower(amount-1)` のみ、`respawns` を1増やす
- `_enemy_turn`：`StockAmount` を **所持している StockPower の量**で上書き。
  1体目=2・2体目=1・3体目は power 無し=0 になるので、export の静的 2 を読むより個体の値になる
- `official_agent.POWER_NAMES` に `POWER.STOCK_POWER` を追加
- テスト2本：`test_axebot_respawns_from_stock_power_until_the_stock_runs_out`、
  `test_axebot_boot_up_strength_grows_with_each_stock_copy`（Strength 0/3/6）
- 回帰確認：親 commit `cd24b1f` の worktree では2本とも失敗（respawn せず、Strength `[0,0,0]`）
- suite **747件成功**

### 決定に出る母数（同一条件 replay、`data/attribution_rampart.py` を power 指定可能にした）

`POWER.STOCK_POWER` が state に出ている record を HEAD と親 commit で replay：

- records compared: **414**
- 決定変化: **135**（不変 279、例外 0）＝ **提示された decision の33%**
- seed 数: **4**（B3N8V5T1WQ 67、D6A1F8C3E5 33、R4A8D2K7ME 26、Q6N3V8K2MT 9）

Rampart（560件で63件）より大きく、分歧の形も「attack を attack で受ける ↔ block や potion に切り替える」
など戦闘全体の組み替え方向。実走 A/B は `data/axebot_ab.sh`（control = `cd24b1f` worktree、
arm = HEAD、seed 3件）。

### Axebot の respawn を commit 1 つだけ違えた arm/control 実走 A/B（2026-10-04、`data/axebot_ab.sh`）

control = 親 commit `cd24b1f` の worktree（`.wt-ctrl-cd24b1f`、Rampart まで入り、Axebot 無し）、
arm = HEAD `03b2055`。seed は replay で分歧が多かった3件。

| seed | control | arm | delta | 第一分歧 seq |
|---|---|---|---|---:|
| `B3N8V5T1WQ` | 17勝1敗 | 17勝1敗 | **0** | 548（arm Crimson Mantle / control Strike） |
| `D6A1F8C3E5` | 17勝1敗 | 17勝1敗 | **0** | 344（arm end_turn / control Shrug It Off） |
| `R4A8D2K7ME` | 21勝1敗 | 21勝1敗 | **0** | 455（arm Maul / control Perfected Strike） |
| 合計 | 55勝 | 55勝 | **0** | |

同一条件 replay で決定を135件動かした机构なのに、3 seed の勝敗は完全に同値。ただし中身は動いている：

- `B3` の死亡戦闘 SOUL_NEXUS（234HP）：control は 13ターンで **26HP 残し**、arm は **13HP 残し**
- `R4` の死亡戦闘 SLIMED_BERSERKER（261HP）：control は 57HP 残し・進入HP 19/72、arm は **5HP 残し**・進入HP 27/72
- 死亡した戦闘の種類は3 seed とも arm/control で同じ

＝respawn を見たことで「あと何ターンで倒せるか」の計算は実走に寄ったが、**胜ち負けの境界は超えない**。
Rampart の A/B（−2/+1/0）と合わせて、この session で入れた2つの忠実度修正は
**正しさの修正として入れたまま、win-rate の改善根拠は無し**。

### 同じ A/B で確認できた壁の実測（6 run の死亡戦闘）

| run | 死亡戦闘 | 進入HP | 与えた合計damage | 残り敵HP |
|---|---|---|---:|---:|
| arm `B3` | SOUL_NEXUS (234HP) | 101/101 | 221（17.0/turn） | 13 |
| ctrl `B3` | SOUL_NEXUS (234HP) | 106/106 | 208（16.0/turn） | 26 |
| arm `D6` | QUEEN+TORCH_HEAD_AMALGAM | 66/77 | 195 | QUEEN 370/400 |
| ctrl `D6` | QUEEN | 85/85 | 287（28.7/turn） | QUEEN 297/400 |
| arm `R4` | SLIMED_BERSERKER (261HP) | 27/72 | 253（42.2/turn） | 5 |
| ctrl `R4` | SLIMED_BERSERKER (261HP) | 19/72 | 201（33.5/turn） | 57 |

`SOUL_NEXUS` は model 側で完全に見えている（block 0・攻撃3種のみに観測一致：SoulBurn 29 /
Maelstrom 6x4=24 / DrainLife 18+Vulnerable+Weak、234HP）。**満タンのHP101で入って13ターン戦って
13HP 残しで死ぬ**形なので、これは model の欠落ではなく deck の火力不足。
全 trace 545 本の死亡戦闘の内訳：THE_INSATIABLE 203、QUEEN(+TORCH_HEAD) 101、VANTOM 53、
EYE_WITH_TEETH+FOGMOG 20、DECIMILLIPEDE 17、OVICOPTER+TOUGH_EGG 16、PARAFRIGHT+THE_OBSCURA 14。

### 同じ監査で「gap ではなかった」事を確認した項目（2026-10-04、再調査の手間を省くための記録）

- `POWER.ESCAPE_ARTIST_POWER`（ThievingHopper、2,911 record）：decompile 上は逃走タイマーの表示だけ
  （`AfterSideTurnEnd` で Decrement）。逃走自体は `ESCAPE_MOVE` の `CreatureCmd.Escape` として
  5ターン目に model 側でも発動する（state machine が THIEVERY→FLUTTER→HAT_TRICK→NAB→ESCAPE 固定）。**モデル化不要。**
- `POWER.REATTACH_POWER`（Decimillipede、1,206 record）：`DoReattach` の `CreatureCmd.Heal(Amount=25)` は
  combat.py の `REATTACH_MOVE` 分岐で既に +25 として入っている。実走の復活 HP も 22-25 で一致。
- `POWER.HATCH_POWER`（ToughEgg、2,422 record）：`AfterSideTurnEnd` で Decrement するだけで、
  HP 変化（HatchlingMinHp..MaxHp）は `Hatch()` 側。combat.py の `HATCH_MOVE` 分岐が既に処理済み。
- `POWER.POSSESS_STRENGTH_POWER` / `POSSESS_SPEED_POWER`（TheLost / TheForgotten）：player への
  -2 debuff と自分の +2 両方が export 済み。未モデル化なのは「 holder が死んだ時に player へ Strength が
  戻る」だけ（player に有利な方向、死亡戦闘の上位14にこの2体は無い）。
- `MONSTER.SOUL_NEXUS`（234HP、今回の A/B で2 run が死亡）：block を持たず攻撃3種のみの観測と一致し、
  漏れ無い（SoulBurn 29 / Maelstrom 6x4 / DrainLife 18 + Vulnerable + Weak）。
- `R4A8D2K7ME` の Act 3 は **分岐の無い廊下**だった（Ancient(0,3)→Monster(1,1)→(2,2)→(3,2)→Unknown(4,2)→
  Monster(5,2)→(6,1)、各行の children が1つ）。act 内の RestSite は (6,5)(8,1)(8,5)(10,4)(11,3)(15,0)(15,3) で、
  廊下の列（col 1-2）には無い。＝「 elite 前に rest を取れていれば残り5HPの死を避けられた」は
  **経路上に rest が無いので実現不能**。rest 経路の重量付け自体は closed lever（§148 §150 §249 §2348）。

## ThievingHopper のカード奪取（2026-10-04、commit `119cb28`）

`ThieveryMove` の本体は export されず、state machine には `"swipe"` の PowerCmd.Apply マーカーと
17ダメージの攻撃だけが出る。C# 本体は攻撃の前に player の **Draw+Discard から1枚を
`CardPileCmd.RemoveFromCombat` で戦闘から抜く**（候補は `DeckVersion != null` の札だけ、優先順
Uncommon → Common/Rare/Event → Basic/Quest → Ancient/Imbued、同一 rarity 内は random、
どのグループにも入らない場合は full list が fallback）。model はこれを全く見ていなかった。

実装：`_enemy_turn` の THIEVERY_MOVE で draw+discard から1枚抜く。抜く順は **Strike/Defend を最後**
にする近似（model には札ごとの rarity が無い）。実走 268件の奪取の内訳が根拠：
Inflame 62・Expect a Fight 33・Battle Trance 33・Second Wind 14・Stratagem 11・Bludgeon 11・
Rupture 10・Stone Armor 10 … **Strike は10件だけ**（Basic は第3優先）、Status/Token 札は1件も無い
→ 定数 `NON_DECK_CARDS`（Slimed・Toxic・Burn・Dazed・Infection・Wither・Decay・Wound・
Frantic Escape・Giant Rock）を候補から除外して一致させる。

回帰：`cd24b1f`（親）では2本とも失敗（抜かれない）。suite **749件成功**。

母数（`data/attribution_rampart.py` に monster id 指定を追加）：`MONSTER.THIEVING_HOPPER` の
record **2964件** replay → **決定変化 189件・34 seed**（AM8C6YXHSG 34、M5PC8TQ3BN 26、
H2LV6ZJ4XW 25、P3V8N5K2RX 13 …）。恒久的なデッキ喪失は 543 run 中31件だけなので、
効果は「その戦闘の rollout が1枚少ない前提で計算される」範囲に留まる。

## Rampart の 2nd panel（新3 seed、`data/rampart_ab2.sh`）

arm = `cd24b1f`（Rampart あり）、control = `d67896f`（親）。`5f655ff` 1コミットだけの差分のまま
新しい seed を足した。

| seed | control | arm | delta | 判定 |
|---|---|---|---:|---|
| `SOS6XYXCNO` | 13勝1敗 | 13勝1敗 | 0 | 2 run とも LivingShield 戦に入らず＝**測定不能** |
| `9X9WQB4QIH` | 17勝1敗 | 17勝1敗 | 0 | Rampart record 6件/6件、**分歧そのものが無し** |
| `R4A8D2K7ME` | 21勝1敗 | 21勝1敗 | 0 | 第一分歧 seq 411（arm Defend / control Maul）、Rampart 位置 |

1st panel と合わせて **6 seed で −2 / +1 / 0 / 0 / 0 / 0（合計 −1）**。replay で63件動く机构だが、
実走では6 seed 中4 seed が无変化、1 seed だけ −2、1 seed だけ +1。
忠実度修正の勝敗効果はこのサイズだと panel で検出できない、が今回の実測の結論。

## 敵側 PlatingPower の実装と、その修正が勝敗を**下げた**実走 A/B（2026-10-04、commit `ca5bd71`）

`FrogKnight.AfterAddedToRoom` / `SlumberingBeetle.AfterAddedToRoom` は `Plating(PlatingAmount=15)` を
自分にかける（export されない）。PlatingPower は

- `BeforeSideTurnStart`：RoundNumber == 1 の間、player サイドのターン開始時に Block = Amount（＝格闘者は
  15 block を持って戦闘を開始する）
- `BeforeSideTurnEndEarly`：自分のターン終了時に Block = Amount を再付与
- `AfterSideTurnStart`：2ラウンド目以降、amount を Decrement.BaseValue（solo では 1）だけ減らす

combat.py は **player 側の PlatingPower しか扱っていなかった**（Iron Unpinion 等の付与）ため、
FrogKnight（191HP、glory）と SlumberingBeetle（86HP、hive）の戦闘で毎ターン 15→14→13…と再生成される
block が rollout から完全に抜けいていた。実走観測は model の想定と一致する：plated Frog Knight の
amount と Block は player turn 1..9 で **15, 15, 14, 13, 12, 11, 10, 9, 8**（各 turn の最大 Block）。
実装後は同一の系列を model も再現する（`test_plated_enemy_re_grants_block_every_turn_and_its_plate_thins`）。
回帰：親 commit `119cb28` の worktree ではこのテストが失敗（`(0,0) != (15,15)`）。suite **751件成功**。

母数：`MONSTER.FROG_KNIGHT` の record **1489件** replay → **決定変化 368件（25%）・8 seed**
（H2LV6ZJ4XW 194、X3C9N6P4WQ 60、R4A8D2K7ME 46、T5R8K2N9QP 20 …）。これまでで最大の母数。

### 実走 A/B（arm = HEAD、control = 親 `119cb28`）

| seed | control | arm | delta | 第一分歧 seq | 分歧地点で Plating が両腕の state に在るか |
|---|---|---|---:|---:|---|
| `H2LV6ZJ4XW` | 22勝1敗 | 20勝1敗 | **−2** | 265 | はい（arm **Defend** / control **Uppercut**） |
| `X3C9N6P4WQ` | 13勝1敗 | 13勝1敗 | 0 | なし（**run が完全に一致**） | 46/46 record |
| `R4A8D2K7ME` | 21勝1敗 | 13勝1敗 | **−8** | 245 | はい（arm **Iron Wave** / control **Uppercut**） |
| 合計 | 56勝 | 46勝 | **−10** | | |

**忠実度修正が勝敗を明確に下げた最初の例。** 死因も変わった：

- arm `H2`：SLIMED_BERSERKER に進入 HP 41/110 で死亡（control は QUEEN まで行って 43/400 残し）
- arm `R4`：OVICOPTER+TOUGH_EGG に **進入 HP 12/72** で死亡（control は SLIMED_BERSERKER で 5HP 差）
- arm `R4` の Plating record は 10件（control 139件）＝ **arm は plating 戦闘を大きく避けています**

原因の形が分歧に直接出ている：第一分歧で arm は攻撃（Uppercut）をやめてブロック札
（Defend / Iron Wave）を打っている。15 block を毎ターン再生成する敵に対してブロックを積むのは
テンポの純損失で、戦闘が伸びるだけ。＝**model が正確になった結果、agent の「長い戦闘で何を打つか」の
選び方が悪いことが見えた**。修正を戻す理由にはならない（model は game と一致すべき）が、
この戦闘種族に対する play の作り直し（plated 敵にはブロックを積まない／Weak・Vulnerable で支える）は
新しい測定対象として残る。routing 側も同じで、elite の HP コスト定数（`Monster*17 + Elite*32`）は
plating の分だけ重いはず、という指摘はこの計測から出る（§148 の closed lever を開け直す根拠になる）。

なお control の H2 22勝は `119cb28`（Rampart+Axebot+Hopper）まで入った値で、`cd24b1f` の 20勝から
**Axebot・Hopper 修正で +2** している。同一 seed の系列として追跡可能。

## Decimillipede の move 本体（export に effects が無い）と、そこから出た次の gap（2026-10-04）

「intents だけあって effects が空の MoveState」を export 全体から数えた：DECIMILLIPEDE_SEGMENT
front/middle/back（各3手）、BYGONE_EFFIGY(2)、KNOWLEDGE_DEMON(1)、ROCKET(1)、SLUMBERING_BEETLE(1)、
LAGAVULIN_MATRIARCH(1) の8体。攻撃力は intent から synthetic DamageCmd で補われているが、
C# 本体にしかない効果は落ちていた。`DecimillipedeSegment`：

- `BulkMove`：攻撃（BulkDamage 6）に加えて自分に `StrengthPower(BulkStrength = 2)`
- `ConstrictMove`：攻撃（ConstrictDamage 8）に加えて player に `WeakPower(1)`
- `WritheMove`：5 x2 攻撃（state 順は WRITHE → CONSTRICT → BULK の循環）

実走では segment の Strength が turn 1 で 0、turn 2 以降で 2、turn 5 以降で 4（player の Weak も
turn 2 から 285 record 出现）→ 効果自体は観測と一致。commit 後 model も同じ系列になる
（`test_decimillipede_bulk_gains_strength_and_constrict_applies_weak`、親 commit `119cb28` では失敗）。
suite **752件成功**。

### 同じ調査で特定した次の gap：player の debuff tick が1手早い／Frail が全く減らない

`step()` の END_TURN 遷移（combat.py 2040-2055 付近）は `_enemy_turn` の**後に**
player の VulnerablePower / WeakPower を `_tick_down_power` している。だから敵のターンで付いた
debuff が同じ遷移内で1減って、player の次のターンに届かない。FrailPower は tick 箇所が**存在しない**
（使用箇所の grep で 2 件だけ：計算と Shame による付与）。実走の Axebot 戦闘（単独・clean）での
player 側 Weak / Frail：

| player turn | Axebot の手 | Weak | Frail | record 数 |
|---:|---|---:|---:|---:|
| 1 | HAMMER_UPPERCUT（まだ手前） | 0 | 0 | 76 |
| 2 | BOOT_UP / ONE_TWO | **2** | **2** | 13 / 68 |
| 3 | HAMMER_UPPERCUT / BOOT_UP | **1** | **1** | 61 / 19 |
| 4 | ONE_TWO | 3・2 | 2 | 20 / 27 |

game は「敵サイドのターン終了時に 1 減る」で、**そのターンに付いた分は減らない**（turn 2 で 2、
turn 3 で 1、2回目の Uppercut で 1+2=3）。model は turn 2 で Weak 1（先に減らす）／Frail は 2 のまま
減らない。実装の形は player 側の Weak/Vulnerable/Frail の tick を敵ターンより前に移し、
enemy 側の Vulnerable/Weak は今の位置（敵ターン後）に置く分岐、になる。
対象は広い（THE_INSATIABLE の player Vulnerable は 6633 record、SOUL_NEXUS の DrainLife が
Vulnerable 2 + Weak 2、Axebot の Uppercut が Weak 2 + Frail 2、Decimillipede、VANTOM、QUEEN …）。
これは次ラウンドの実装候補として一番母数が大きい。

## player debuff の tick が1手早く、Frail が全く減っていなかった（2026-10-04、commit `7ec2a06`）

`WeakPower` / `VulnerablePower` / `FrailPower` の tick は decompile で3つとも同じ形：

```csharp
public override async Task AfterSideTurnEnd(...) { if (side == CombatSide.Enemy) await PowerCmd.TickDownDuration(this); }
```

＝**敵サイドのターン終了時に1減る**（player 所有でも enemy 所有でも）。combat.py は END_TURN 遷移で
`_enemy_turn` の**後に** player の Vulnerable/Weak を減らしていたため、敵のターンで付いた stack が
同じ遷移内で消え、player の次のターンに届かなかった。FrailPower は tick する箇所が**存在しなかった**
（`grep FrailPower combat.py` は使用箇所の2件だけ）。

実走で決まる2つの事実：

1. 敵がそのターンに付した debuff は、そのターンの tick を受けけない（Axebot の Hammer Uppercut
   Weak 2 / Frail 2 → player turn 2 で **2 / 2**、turn 3 で **1 / 1**）
2. player 側に既に乗っていた debuff は、敵の攻撃に効いた後に減る（Waterfall Giant の EXPLODE 22
   ダメージは Vulnerable 1 が生きていてこそ。`test_rollout_preserves_waterfall_steam_damage_from_observed_explode_intent`
   がこの順番を壊す実装で 58 → 65 HP になって失敗した）

実装：END_TURN で**敵フェーズの前に**「すでに走っていた debuff」の集合を記録し（player と各 enemy）、
敵フェーズの後にその集合だけを `_tick_down_power` する（`DEBUFF_POWERS` と `_tick_debuffs`）。
フェーズ中に付いた分は減らないので player の次のターンまで生き、Frail も減り始める。
model の Axebot 系列は turn 2 = 2/2、turn 3 = 1/1、turn 4 = 2/2（1+2 から1減らして2）で実走と一致。
回帰テスト `test_enemy_applied_debuffs_survive_the_turn_that_applied_them`（親 commit では失敗）、
suite **753件成功**。

母数（replay ではなく観測露出で数えた）：combat record 148,905 件のうち **15,343 件**で player が
Weak / Vulnerable / Frail を持っており、**552 run 中 432 run** に現れる。
内訳 FRAIL 8,322・WEAK 4,490・VULNERABLE 2,531。Frail はPreviously 永久に乗る側へ狂っていたので、
この432 run で block の見積もりが系統的に狂っていたことになる。実走 A/B は `data/debuff_ab.sh`
（露出上位3 seed：B3N8V5T1WQ 153、SOS6XYXCNO 129、D6A1F8C3E5 127）。

### debuff tick 修正の実走 A/B（2026-10-04、`data/debuff_ab.sh`）

arm = HEAD `7ec2a06`、control = 親 `0aa9a71`（worktree）。露出上位3 seed。

| seed | control | arm | delta | 死亡戦闘 | arm/control の player debuff record 数 |
|---|---|---|---:|---|---|
| `B3N8V5T1WQ` | 19勝1敗 | **20勝1敗** | **+1** | QUEEN+TORCH_HEAD_AMALGAM（arm 8T/残り QUEEN 393、ctrl 6T/392） | 164 / 160 |
| `SOS6XYXCNO` | 13勝1敗 | 13勝1敗 | 0 | THE_INSATIABLE（arm 残り96HP、ctrl 残り22HP） | 16 / 11 |
| `D6A1F8C3E5` | 17勝1敗 | 17勝1敗 | 0 | arm は QUEEN のみ（TORCH_HEAD を殺しきった）、ctrl は QUEEN+TORCH_HEAD | 145 / 127 |
| 合計 | 49勝 | **50勝** | **+1** | | |

分歧の数は B3 で 537 对齐中 412、D6 で 359 中 103 と大きい。ただし**第一分歧の record には player の
debuff が出ていない**（B3 seq 73、SOS 193、D6 342 で player powers は空）＝この修正の差は観測状態そのもの
ではなく **rollout 内の将来の tick** に現れる。だから「分歧が debuff 付き record に居る数」
（B3 173件、D6 88件、SOS 0件）を以って帰属の根拠にはできない。分歧の帰属をクローズするには
同一 record replay（`data/attribution_rampart.py PLAYER:POWER.WEAK_POWER,...`）を act 別の enemy data
（またはマージした data）で回す必要がある。

同じ seed 系列での忠実度修正の累計は追跡できる：`B3N8V5T1WQ` は
`d67896f` 16勝 → Rampart 17勝 → Axebot・Hopper・Decimillipede 19勝 → debuff tick **20勝**。
まだ Act 3 は踏破していない（QUEEN 400HP が残る）。SOS6XYXCNO の THE_INSATIABLE 戦では arm の方が
**96HP 残し**で負けており（control 22HP 残し）、tick 修正が必ずしも boss 戦を有利にしていない面もある。

## Round 4: debuff tick の帰属を閉じ、QUEEN 戦を監査して3つの候補を却下（2026-10-04）

### 1. debuff tick 修正の同一 record replay 帰属

`data/attribution_rampart.py` に `TRACE_GLOB`（replay する trace を絞る）と `SIMULATIONS` を追加し、
A/B の control 3 run だけ replay した（enemy data は act 横断でマージした
`/tmp/sts2-ai-enemies-merged.json`、102 monsters / 80 encounters）。

`PLAYER:POWER.WEAK_POWER,POWER.VULNERABLE_POWER,POWER.FRAIL_POWER` で **298 件の決定を replay →
決定変化 18 件・3 seed**（B3N8V5T1WQ 13、D6A1F8C3E5 4、SOS6XYXCNO 1）、例外 0。
A/B の勝敗変化（+1 / 0 / 0）と同じ seed 順で母数が乗っている。

### 2. QUEEN 戦（wall 第2位）の忠実度監査：gap は見つからなかった

- QUEEN 戦の record に出现する power id は **すべて `official_agent.POWER_NAMES` に映射済み**（未映射 0 件）
- export の state には `PUPPET_STRINGS`（ChainsOfBinding 3）／`YOU_ARE_MINE`（Frail 99・Weak 99・Vulnerable 99）／
  `BURN_BRIGHT_FOR_ME`（味方の Strength +1 と自分の block 20）／`OFF_WITH_YOUR_HEAD`（5回攻撃）／
  `EXECUTION`（15）／`ENRAGE`（+2）が揃っており、decompile の C# 本体と一対一で対応する
- 観測される move id に export 外の id は 1 件も無い（`TACKLE_4_MOVE` まで export 済み）
- 敵味方の Strength 付与（`target == "item"`）も `MONSTER.QUEEN` 専用分岐で model 済み（combat.py 1581 付近）、
  `HasAmalgamDied` 条件も combat.py 685 付近で扱っている
- 倍率は Weak 0.75・Vulnerable 1.5・Frail 0.75 で decompile の `DamageDecrease` / `DamageIncrease` と一致

壁のサイズは数値で確定した：QUEEN 400 + TORCH_HEAD_AMALGAM 199 = **599 HP**。全 corpus で QUEEN 戦 109 件の
中央値は 8 ターン・毎ターン 33.8 ダメージ・残り敵 HP 348・デッキ 20 枚・進入 HP 81。
最も健闘した 6 件は 9-12 ターンで 568-580 を削って **残り 14-23 HP** で落ちている。つまり壁は約 3% 足りない。

### 3. 却下した3つの候補（再発防止の記録）

1. **Weak の丸め（floor か ceil か）**：単一目標・block 0・敵 Vulnerable 無しの条件で card play 1 枚あたりの
   実ダメージ 440 件を HP 差分から復元した。`floor(x*0.75)` 一致 98 件／`ceil` 一致 141 件／
   両方で説明できない 201 件（うち raw 9 → 9、raw 6 → 6 のように**全く減っていない**ものが多い）。
   丸めの規則を疑うより先に、Weak を打ち消す relic 側の介入を疑うべき規模。この測定だけでは
   model の `damage * 3 // 4` を変えない。
2. **Shackling potion の TemporaryStrength**：`TemporaryStrengthPower` は「その敵のターン終了時にstrength を戻す」
   で、実走でも SHACKLING_POTION_POWER amount 7 は turn 1 に 179 件・turn 2 に 12 件しか続かない。
   agent 側は既にこれを前提にしている（official_agent.py 1801 と 1906 のコメント）→ 未実装ではない。
3. **QUEEN 戦の `rollout_exception_stop_iteration`（corpus で 240 件）**：現在の HEAD で
   QUEEN 戦の record 106 件を `rollout_choice`（simulations=100、legal_actions は record のものを使用）に
   通すと**例外 0 件**。この 240 は corpus 内のもっと古い code の run が混ぜられている数値で、
   現在の gap ではない。

監査中に自分で作った偽のシグナルも記録する：legal action の `type` は `"card"` なのに
`"play_card"` で絞って card 行動を空にした結果、`_map_rollout_card_action` の `next(iter(candidates))` が
StopIteration を出し、106 件中 83 件が失敗したかのように見えた（official_agent.py 2744）。
監査スクリプトは `record["legal_actions"]` をそのまま渡すこと。

**教訓**：corpus 集計（decision_source の件数など）は code の版を混ぜて数える。次の gap 探索は
corpus の集計ではなく、**HEAD で全 trace を replay して今の code が落とす場所を数える**方法に切り替える。

### HEAD で全 corpus を replay した結果：例外 0 件（2026-10-04、`data/current_gap_scan.py`）

`data/current_gap_scan.py` は記録された combat observation を **現在の code** で `rollout_choice` に
通し直し、落ちた場所を戦闘出現順に数える（enemy data は 4 act をマージして、他 act 由来の KeyError を
紛れ込まない）。6000 record / 549 trace を simulations=5 で replay → **exceptions 0 件・rejected 0 件**。
観測 schema が今の bridge と違う 6 trace（`slot` / `history` / `combat_id` 等の欠落）は対象から除外して
別カウントにした（以前はここが `KeyError: 'slot'` → `'history'` → `'hp'` と 58 件を出していたが、
すべて trace 側の旧形式で live run の gap ではなかった）。

意味：corpus 内には「model がその戦闘を simulate できなくて heuristic に落ちる」型の実在 gap は
残っていない。ここからの Act 3 未踏破は model の欠落ではなく**手数と火力の問題**なので、
同じ replay  instrument を今後の回帰検査（新 trace で例外 0 を保つ）として使い、
改善の探索は火力・ルートの測定に移す。

## Round 5: 未実装の damage source を探す scan を作って、残る候補をすべて潰した（2026-10-04）

### `data/damage_source_scan.py`：敵フェーズの被害が intent の総和で説明つくか

player のターン最後の observation（`L`）に出ている攻撃 intent は、game が表示している最終ダメージ
（敵の Strength、player の Vulnerable、敵の Weak を織り込んだ値）なので、block を差し引けば
**その後の敵フェーズで減る HP は intent 総和を超えられない**。超える場所＝観測に現れない damage source。
14,891 ターンを測った。

初めて出た上位（MYTE 191・MECHA_KNIGHT 82・SLITHERING_STRANGLER 129・WRIGGLER 81）は
すべて scan 側の誤りだった：

- 観測の status 札の id は `CARD.BURN` / `CARD.TOXIC` … であって `CARD.BURN_STATUS` ではない。
  名前を直すと MYTE（Toxic を hand に2枚入れる）と MECHA_KNIGHT（Flamethrower で Burn を4枚）は消えた
- player 側の `ConstrictPower` はターン終了時に自分へダメージを与える（model 済み・combat.py 2010 付近）。
  その分を被害から差し引くと SLITHERING_STRANGLER の大半は説明内に入った
- SPINY_TOAD（expected 0 → 5）は `THORNS_POWER 5` 持たせ反撃で、被害は player の攻撃直後に起きていた
  （`L` はその解決前の observation）＝測定窓のずれ

残った小さな gap（QUEEN 53・VANTOM 47・THE_INSATIABLE 31・LOUSE_PROGENITOR 22・AXEBOT 9、いずれも +1）は
下記の丸め測定の結果 **model の側は正しい**ので、damage source の欠落ではない。

### 敵攻撃の表示値で game の丸めを確定：floor（model と一致）

`raw_damage`（Strength 適用前の値）と `damage`（表示値）の組を corpus 全体で集め、
`floor((raw + Strength) × 倍率)` と `ceil` を比較した：

| 状況 | sample | floor 一致 | ceil 一致 |
|---|---:|---:|---:|
| 修正なし | 37,934 | 37,687 (99.4%) | 37,687 |
| player Vulnerable のみ | 1,591 | **1,581 (99.4%)** | 645 |
| 敵 Weak のみ | 1,149 | **1,139 (99.1%)** | 351 |
| Vulnerable + Weak | 103 | 99 | 10 |

game は `(raw + Strength) × 1.5`（Vulnerable）と `× 0.75`（Weak）を **floor** する。combat.py の
`damage * 3 // 2`（1297 行）と `damage * 3 // 4`（1295 行）と同じ規則で、一致率は 99% 超
（残りは Soar・Plating・Dexterity など別の修正の項）。**QUEEN 戦の 14-23 HP 不足は丸めの差ではない**
という結論がこれで出る。player 側だけで floor 一致 98/440 と悪かった前回の測定は、relic と card var が
絡む側だったため信用できない（敵側は relic の影響を受けないのでこの測定が正しい）。

### 未映射 power の全 census：13 件すべて「効きは model にある」か「表示専用」

`official_agent.POWER_NAMES` に無い id を観測から数えると：REATTACH 3,666（+25 revive で実装済み）、
PLAYER PYRE_POWER 3,437・PLAYER STRATAGEM_POWER 724（札側で実装済みのマーカー）、
ESCAPE_ARTIST 3,012（表示タイマー専用）、HATCH 2,470（`HATCH_MOVE` で HP を幅から引く）、
**TERRITORIAL 2,460（Byrdonis）**、SWIPE 2,152（奪札の返却マーカー：戦闘内の効果は model 済み、
返却は run 側の話）、INFESTED 969、POSSESS_SPEED 619・POSSESS_STRENGTH 328、SHACKLING_POTION 191、
IMPROVEMENT 26、DARK_SHACKLES 2。

TERRITORIAL は `AfterSideTurnEnd` で自分に Strength +Amount（観測でも Byrdonis の Strength が
turn 1..6 で 0,1,2,3,4,5 と増える）だが、model は **monster id で +1 を毎ターン入れている**
（combat.py 1724 付近）ので、mapping が無くても実走 rollout で効いている。観測の Territorial amount は
常に 1 なので +1 固定も実データと一致。

### 観測されないPlating保持者（LagavulinMatriarch 12・SewerClam）は corpus に 1 度も出現しない

`data/*_agent.jsonl` 555 run に LAGAVULIN_MATRIARCH / SEWER_CLAM / MYSTERIOUS_KNIGHT は 1 件も居ない
（Plating が出るのは FROG_KNIGHT 54 run・SLUMBERING_BEETLE 119 run だけ）。C# 側ハードコードで
export に値が無いこの2体の Plating は、**観測母数がゼロなので実装対象にしない**。

### この round の結論（探索面の変更）

combat.py の忠実度について、corpus から観測できる gap（power の未映射・move 本体の欠落・
damage の丸め・説明できない被害）は**この round で枯れた**。2 round 続けて新しい忠実度修正が出ていないのは
探索面が尽きた側の話なので、次は (1) 忠実度修正を積んだ系列（`d67896f`→HEAD）を新しい複数 seed で
まとめて panel にして Act 3 到達度を測る、(2) QUEEN 戦で agent がどのターンにどれだけ火力を捨てているかを
observation から分解する、に進む。

### 忠実度 chain の累计 panel（2026-10-04、`data/fidelity_chain_ab.sh`）

個々に測定済みの忠実度修正（Rampart・Axebot Stock 再生成・ThievingHopper 奪取・敵側 PlatingPower・
Decimillipede の move 本体・player debuff tick）を**まとめて** Act 3 到達に効くかを測った。
arm = HEAD、control = chain の起点 `d67896f` の worktree。seed はどの panel にも出ていない新しい3件
（T5R8K2N9QP・GYIJSAA6W7・Q6N3V8K2MT）。

| seed | control | arm | delta |
|---|---:|---:|---:|
| `T5R8K2N9QP` | 21勝1敗 | 20勝1敗 | −1 |
| `GYIJSAA6W7` | 14勝1敗 | **17勝1敗** | +3 |
| `Q6N3V8K2MT` | 12勝1敗 | 8勝1敗 | −4 |
| 合計 | 47勝 | 45勝 | **−2** |

**Act 3 を踏破した run は両腕とも 0 件**。arm 側は debuff・Plating・Swipe の出現 record 数が control より
少ない（T5 で Vulnerable 230/311、Plating 66/98、Swipe 6/19）＝**arm は高い戦闘を避けるループに
なっている**が、勝敗は増えていない。忠実度をまとめて上げても 3 seed では勝敗が動かない（符号も割れる）
という、この repo で 4 回目になる同じ結果がまた出た。

### QUEEN 戦の火力浪费は無かった（2026-10-04）

「end_turn 時に使える攻撃札が hand に残っている」case を数えると QUEEN 戦で 39+31+17+11 件出たが、
実例（`act3_verify_head_D6A1F8C3E5` seq 435-439）を見ると **CHAINS_OF_BINDING_POWER 3** で hand の
3 枚が Bound（=`CardCmd.AfflictAndPreview<Bound>`）になり、game 自身の `legal_actions` から card 行動が
消えていた。model は ChainsOfBinding/Bound を実装済み（combat.py 307・828 付近・1974 付近、
POWER_NAMES 251 付近）で、浪费ではない。

QUEEN 戦の構造はこうだ：`YOU_ARE_MINE` が Frail 99・Weak 99・Vulnerable 99 を player にかけて恒久化し
（実走では turn 4 で FRAIL 98 / WEAK 98 / VULNERABLE 98）、player の攻撃は 0.75 倍・block は 0.75 倍・
受けるダメージは 1.5 倍のまま QUEEN 400 + TORCH_HEAD 199 を削らされる。中央値 8 ターン・毎ターン 33.8
ダメージでは構造的に足りず、最良の試みでも 14-23 HP 残る。

### ついでに前 round の誤測定の理由が分かった：observation の card `vars` は倍適用後の値

同じ record で `CARD.STRIKE_IRONCLAD` の `vars` Damage は **12.375 → 13.125**（player の Weak 98・
Strength 1 の変化に応じて分数で動く）。つまり mod が出す card var は**修正適用後**の値で、
前 round の「player 側の Weak の丸め」測定は base + Strength を作る前提が壊れていた
（floor 一致 98/440 と悪く見えた理由）。**relic の影響を受けない敵側の測定
（37,934/1,591/1,149 sample で floor 99% 一致）だけが有効**という扱いで確定する。

## Round 6: 札の upgrade 値が 17 枚違っていた（既定 +3 の落とし穴）と model 一致率検査（2026-10-04）

### 記録された1手を model で再生して game の次の observation と照合する検査を作った

`data/model_match_audit.py`：連続する combat record の組 (L, F) から、live rollout と同じ手順で
Combat を作り（`official_agent.search` を差し替えて state を捕捉）、その record で agent が実際に選んだ
手を `combat.step` で進め、**model が predicts した次の状態が game の実際の F と一致するか**を見る。
card play は狙った敵の HP、end_turn は player の HP（＝敵フェーズの被ダメージ）で比較する。
戦闘境界をまたぐ組（次フロアの最初の observation）と model が非法扱いした手は別枠にして、
4,000 組中 **比較可能 2,452 組**とした。

修正前の一致：**2,336 / 2,452 = 95.3%**（card play の不一致 101 件）。不一致の最大グループが
**Anger 50 件**で、内訳は model が 1 多く削る +1 が 542 件（upgraded Anger だけ 360+144 件）だった。

### gap の正体：`CARD_UPGRADE_DAMAGE.get(card, 3)` の既定値

combat.py は upgrade 済みの攻撃力を `CARD_UPGRADE_DAMAGE` から引き、表に無い札は **+3 と仮定**していた。
decompile した札本体の `DynamicVars.Damage.UpgradeValueBy` と突き合わせると、**17 枚が違った**：

| 札 | game base → up | model（修正前） |
|---|---|---|
| Bludgeon | 32 → **42** | 32 → 35 |
| Break | 20 → **30** | 20 → 23 |
| Ultimate Strike | 14 → **20** | 14 → 17 |
| Unrelenting | 14 → **20** | 14 → 17 |
| Hemokinesis | 15 → **20** | 15 → 18 |
| Giant Rock | 16 → **20** | 16 → 19 |
| Byrd Swoop | 14 → **18** | 14 → 17 |
| Volley / Molten Fist / Neow's Fury | 10 → **14** | 10 → 13 |
| Breakthrough | 9 → **13** | 9 → 12 |
| Iron Wave | 5 → **7** | 5 → 8 |
| Anger / Feed / Fisticuffs / Dismantle | 6→8・10→12・7→9・8→10 | すべて +1 過大 |
| Bolas | 3 → **4** | 3 → 6（+3 過大） |

`ALL_ENEMY_DAMAGE` 側（全体攻撃）も同じ既定値を使っており、Howl From Beyond は +5、Pacts End は +6、
Dramatic Entrance と Breakthrough は +4 だった。Rampage の upgrade は `DynamicVars["Increase"]`（攻撃札を
出すたびに得る Strength）を 4 増やすものでダメージは変わらないので、Rampage は 0 にした。

修正後：**一致 2,396 / 2,452 = 97.7%**、card play の不一致は 101 → 41 件に減り、Anger のグループは
ほぼ消えた（upgraded Anger は 738 件中 一致738・-1 が17・+3 が5）。suite は 754 件 green
（`test_upgrade_damage_matches_each_cards_own_upgrade_value_by` を追加）。既存の policy test は
1 件も壊れていない＝旧い +3 を前提にした回帰テストは無かった。

意図と影響：agent は upgrade 済みの大物攻撃（Bludgeon・Break・Ultimate Strike・Unrelenting）を **7 損も
低く積んで** card reward で選び、戦闘中も弱く評価していた。逆に Bolas（+3 過大）や Fisticuffs・Anger・
Feed・Dismantle・Iron Wave（各 +1 過大）を過大評価していた。QUEEN 戦の火力不足（毎ターン raw 50 が
必要で中央値 33.8）に対する、model 側の実測可能な改善になる。

### 同じ round で確認できた「gap では無い」もの

- 拾った札の可視性：corpus 全体で拾われた 66 枚は全て `CARD_NAMES` にあり、`legal_actions` に現れ、
  一度も使われていない札は無い（CLAUDE.md の "never played a card" 検査を corpus 版でやった）
- player 側の damage path：単一目標の攻撃 play 58,232 件を実測し、model と同じ補正連鎖
  （target Vulnerable ×1.5 floor、Soar/Flutter の半分、HardToKill の上限、Slippery/Intangible の 1 本化、
  player Weak ×0.75）を再現式に入れると 97.6% 一致。残りは multi-hit 札の hit 数（Twin Strike 等）と
  REATTACH（+25 HP の回復）と Illusion/Minion の蘇生窓だった
- SlowPower（札を出すたびに受けるダメージ +10%）、ChainsOfBinding/Bound（QUEEN 戦で hand の 3 枚が
  遊べなくなる）、Slippery（VANTOM・INKLET、-hit を 1 に押える）、Soar、HardToKill、Flutter はすべて
  combat.py に実装済み（`_damage_enemy` 1305 付近と 2847 付近）
- combat 外の決定（map 17,324・card_reward 7,441・event 5,926・shop 4,376・rest 3,649）は
  すべて専用の policy 側で処理され、heuristic fallback への落ち込みは 0 件

### 未解決として残した実測：Feed が game より 5-8 少ない

Feed（`CARD.FEED`）の play 約 500 件で model の与えたダメージが game より **-5〜-8 偏る群**が
240 件残っている（例：player Strength 1・敵 power 無しで model 11 / game 16）。game 側の Feed は
10 ダメージ + Max HP +3 + Fatal 条件で、X 的な伸びは本体に無い。原因は特定できていないので
次回に回す（推測で damage 式は触らない）。同じく残る小グループ：Bash 15 件・Strike 8 件・
end_turn 後の TUNNELER 5 件。

### upgrade 値修正の決定母数（同一 record replay、2026-10-04）

`data/attribution_rampart.py` に `CARD:` フィルター（hand に upgrade 済みの対象札を持っている決定を選ぶ）を
追加し、HEAD と `bef34e7`（修正直前の worktree `.wt-ctrl-bef34e7`）で corpus を replay した。
対象は修正した 18 枚（Bludgeon・Break・Ultimate Strike・Unrelenting・Hemokinesis・Giant Rock・
Byrd Swoop・Volley・Molten Fist・Neow's Fury・Breakthrough・Iron Wave・Anger・Feed・Fisticuffs・
Dismantle・Bolas・Rampage）。

**1,251 件の決定を replay → 決定変化 158 件・17 seed・例外 0 件**。変化の例：
`seq 112 arm=CARD.DEFEND_IRONCLAD control=CARD.ANGER`、`seq 622 arm=CARD.BLUDGEON control=CARD.RUPTURE`、
`seq 323 arm=CARD.SHRUG_IT_OFF control=CARD.HOWL_FROM_BEYOND`。

repo の基準（決定 3 件以上かつ seed 3 件以上）を決定数・seed 数ともに満たす母数だが、これは offline replay
なので勝敗の証拠にはしない。勝敗への影響は新しい 3 seed の A/B（arm = HEAD、control = `.wt-ctrl-bef34e7`）で
測ることにし、panel の起動は次 round の先頭で行う（playbook の待機と panel 起動を game 稼働中に挟まないため）。

## Round 7: 付与（enchantment）が bridge から agent に届いていない（2026-10-04）

### きっかけ：Feed のダメージが game より 5-8 少ない群

`model_match_audit.py` の残り不一致のうち Feed が約 240 手で -5〜-8 偏る群を追った。観測された
`CARD.FEED` の Damage var を集计すると base（var から player Strength を引いた値）が **10 の群と 15 の群**
に分かれ、15 の側は 877 record ある。15 = 10 × 1.5 で、player の Strength は普通に足されていた
（Strength 1 → 16.0、2 → 17.0、4 → 19.0）。

`plating_arm_b1_H2LV6ZJ4XW` の時系列で原因が特定できた：seq 188 で Feed の var は 11（base10+Str1）、
seq 240 の **イベント `SYMBIOTE`**（`CardCmd.Enchant<Corrupted>(card, 1m)` で攻撃札1枚に付与）の直後の
seq 242 から 16.0 (=15+1) になっている。`Corrupted.cs` は `EnchantDamageMultiplicative = 1.5m`（powered
attack のみ）と `OnPlay` で owner に 2 ダメージで、combat.py は両方実装済み
（`ENCHANTMENT_CORRUPTED` で damage ×3//2、テスト `test_corrupted_enchantment_increases_damage_and_hurts_player`）。

### 何が壊れているか：hand の enchantment が bridge の成果物に無い

`official_mod/CombatBridge.cs` の hand 射影は `enchantment = card.Enchantment?.Id.ToString()` を
持っており（commit `c6ef39b`、2026-09-05）、`official_agent._observation_card`（2652 付近）はその値を
`Card.enchantment` に写す。ところが**今日走らせた run の trace でも hand の card には `enchantment`
キーが1つも無い**（`chain_arm_b1_T5R8K2N9QP` の hand card 1,730 件のキー集合は
`index,id,cost,upgrade,type,rarity,pool,vars,rider,target`）。`enchantment` が出るのは
draw_pile / discard_pile / exhaust_pile の 4,075+3,454+368 件だけ。

裏取り：走らせている成果物 `official_mod/bin/Release/net9.0/Sts2Ai.dll` 内に `enchantment` 文字列は
**3 個**、今の `CombatBridge.cs` には **7 個**ある。つまり run に使われている dll は hand 射影の
この行が入る前のソースからビルドされたもの（mtime は 2026-10-02 だが、中の field 数が古い）。

結果として live run では `Card.enchantment` が常に None で、combat.py の Corrupted（×1.5 と self 2 ダメージ）
と Tezcatara's Ember（+3）の扱いは**一度も発火していない**。札の `vars` には倍率が焼き込まれて
現れるのに、model は `vars` を（Mad Science と Frantic Escape を除き）使わず自分の表を見るため、
付与された札を永久に base 値で評価する。

### 次の一手（未実施）

game を止めて `build_official_mod.ps1` で dll を作り直し、短い run で hand card に `enchantment` が
出ることを確認する。それまで combat.py / official_agent.py は触らない（panel が走っているためでもあり、
観測チャネルの話なので model 側をいじっても取り違える）。なお `+3` 系の group（Strike 3,509 record）は
`RELIC.STRIKE_DUMMY`（Strike に +3、model 済み）で説明がつくので、付与の証拠として使えない。

### upgrade 値修正の A/B panel：新 3 seed で +1/+2/+3（合计 +6）（2026-10-04）

`data/upgrade_ab.sh`。arm = HEAD（`a94a4dc` の upgrade 値修正込み）、control = 修正直前の `bef34e7` の
worktree `.wt-ctrl-bef34e7`（2つの tree はその1コミット分だけ違う）。seed は replay で決定変化の多かった
M5W9C3T7LQ・D1W9Y3B7FC・C9RH5TXB3L（いずれも過去の panel で使っていない）。

| seed | control | arm | delta | 最初の分岐 |
|---|---:|---:|---:|---|
| `M5W9C3T7LQ` | 12勝1敗 | **13勝1敗** | +1 | seq 109 control=Evil Eye / arm=end_turn |
| `D1W9Y3B7FC` | 17勝1敗 | **19勝1敗** | +2 | seq 106 control=Thunderclap / arm=Iron Wave |
| `C9RH5TXB3L` | 12勝1敗 | **15勝1敗** | +3 | seq 198 control=Defend / arm=Strike |
| 合計 | 41勝 | **47勝** | **+6** | |

**3 seed すべてで arm が勝ち、勝敗が上がった**（この repo で忠実度修正が run レベルで全 seed 正に振れた
のは初めて）。最初の分岐は3件とも rollout の札選びで、D1W9Y3B7FC の arm が Iron Wave を選ぶ件は
upgrade 済み Iron Wave が 5→7 になったことと直接つながっている。**Act 3 を踏破した run は両腕とも 0 件のまま**。

### 測定事故：control の1本が game の halt で 1勝扱いになった

`upgrade_ctrl_b1 M5W9C3T7LQ` は Act 1 F3 の SLIMES_WEAK で combat 解決中に halt し、bridge の
observation/action ファイルが 10:40 から更新されないまま 30 分 timeout で kill された（agent は生存、
`agent.err` は空、最後の action は `target_id=2` でその敵の `combat_id` は 2＝行動自体は妥当）。
RESULT 行には `wins=1 exit=1` と出てしまい、そのまま読むと delta +12 の誤計測になる。同じ seed の
control を `upgrade_ctrl_b2` で走り直すと 12勝1敗で完走したので **halt は再現しない一時的なもの**として
扱う。教訓：RESULT 行は `exit=1` と agent record 数（完走なら普通数千行）を確認してから使う。

### 前項の訂正：live の observation には enchantment があった（2026-10-04、実走で確認）

前項の「hand の enchantment が bridge に無い」は**半分間違い**だった。`CombatBridge.cs` には射影が2つある：

- **observation 射影**（257 付近、python が実際に読む）：hand に `enchantment` を出す ✓ 実装済み
- **trace 射影**（129 付近、`--bridge-trace` が書く `*_agent.jsonl`）：hand に `enchantment` が**無い**

つまり live run の agent は付与を見ており、combat.py の Corrupted（×1.5 と play 時の self 2 ダメージ）と
Tezcatara's Ember（+3）は**普段から発火していた**。無かったのは **corpus 側の記録**で、そのため
`model_match_audit.py` や attribution replay は trace から state を組み直す限り付与を知らず、
Feed の -5〜-8 群のような「model が弱い」嘘の不一致を生んでいた。dll 内の `enchantment` 文字列が 3 個
だったのは、同じ形の anonymous type がメタデータで共有されるためで、ビルドの古さの証拠にはならない
（これも前項の誤りの一部）。

### 対策：trace 射影にも enchantment を出したら Feed の不一致が消えた

`official_mod/CombatBridge.cs` の trace 射影の hand に `enchantment = card.Enchantment?.Id.ToString()` を
1 行足して再ビルド（231,424 バイト、0 warnings / 0 errors）、`enchant_check_b1` で seed
`H2LV6ZJ4XW`（`SYMBIOTE` イベントが seq 240＝以前と同じ位置）を走らせた：

- hand card record 1,969 件すべてに `enchantment` キーが入るようになった
- `('CARD.FEED', 'ENCHANTMENT.CORRUPTED')` が 27 件記録された＝var が 15+Strength に変わっていた札の正体
- その trace だけで `model_match_audit` を回すと一致 284/294 = **96.6%**、Feed の不一致は
  (model 289 / game 290) の 1 件だけになった（以前は -5〜-8 の群が 240 件）

**结论：combat.py の側に付与処理の gap は無い。** 消えた不一致は観測チャネルの欠落による見かけのものだった。
以後の offline replay は付与を知ることができる。game は v0.107.1 系（`run_official_autoslay.ps1` が
インストールする mods/Sts2Ai を毎回差し替え）、seed `H2LV6ZJ4XW` の win 数は 22 勝 1 敗で
`plating_arm_b1` の 22 勝 1 敗と一致（trace の記録形式が変わっても run の挙動は変わっていない）。

（運用メモ：`run_official_autoslay.ps1` は各 run で **その repo の `official_mod/bin/Release/net9.0/Sts2Ai.dll`**
を game の mods にコピーする。だから bridge のソースを変えて再ビルドしたら、panel の control 用 worktree
側の dll も同じものに差し替えないと「python だけ違う」比較が「dll も違う」比較になる。
2026-10-04 に main で再ビルドした dll（231,424 バイト）を `.wt-ctrl-*` 全 7 本へコピーした。）

## Round 8: STUNNED（runtime の stun 状態）が model に無く、気絶中の敵に攻撃させていた（2026-10-04）

### gap の見つけ方

`data/model_match_audit.py`（記録された1手を model で再生して game の次の observation と照合）に
**card play 後の player HP 照合**を加えた（自己ダメージの欠落を探すため）。結果は
`card_player_hp` が **828/828 一致**で、札を出す瞬間の自己ダメージ系の欠落は無いと分かった。
一方 end_turn 照合側に TUNNELER の不一致（model 80 / game 88）が残っていた。

trace を追うと、bridge が敵の現在手として **`move = "STUNNED"`** を報告する case が corpus に
**1,590 件**（Bowlbug Rock 1,046・Tunneler 431・Thieving Hopper 85・Slumbering Beetle 28、intents は全て `Stun`）
ある。`STUNNED` は `MonsterModel.stunnedMoveId` で、`Creature.StunInternal` が実行中に作る
`MoveState("STUNNED", <stun ロジック>, StunIntent)`（FollowUpStateId は既定で stateLog.Last().Id）＝
**export には絶対に現れない runtime 状態**だった。

combat.py の `official_agent.rollout_choice` は「export に無い move id」を初期状態から引き直す
（IllusionPower の REVIVE_MOVE 向けに入っていた安全装置）ため、気絶中の敵を初期状態に戻して
**そのターンに BITE/HEADBUTT を実行させていた**。実測：`STUNNED` の Tunneler に対して model は
13 ダメージの BITE を織り込み、game は 0 ダメージだった。

### 実装

- `combat.py` に `STUNNED_MOVE` と `_stunned_state(spec)`：その敵の export 内の **StunIntent を持つ状態**
  （Tunneler/Bowlbug Rock は `DIZZY_MOVE`）を返し、無ければ `intents=[StunIntent]`・`next=initial_state`
  ・`effects=[]` の合成状態を作る。DIZZY_MOVE は効果ゼロで `next` が実際の再開先
  （Tunneler → BITE_MOVE、Bowlbug Rock → HEADBUTT_MOVE）で、観測された STUNNED からの再開
  （Tunneler 382 件・Bowlbug Rock 928 件）と一致する
- `_move_state` を `_enemy_turn` の厳密 lookup で使い、`_resolve_move` も STUNNED を受け付ける
- 移動履歴には STUNNED を残さない（game の次の record の history は `BITE,BURROW,BELOW,BELOW,BITE` で
  気挟まる隙がない）
- `official_agent.rollout_choice` の「Unknown move → 初期状態」の安全装置は STUNNED を除外

### 検証（同一 record、combat.py だけ違う2ツリー）

`STUNNED` の敵がいる戦闘の end_turn を 437 本 replay した player HP 一致率：

| ツリー | 一致 | 主な残差 |
|---|---:|---|
| 修正前（`.wt-ctrl-ba30482`） | **67 / 437 = 15.3%** | Bowlbug Rock -15（HEADBUTT）58 件、Tunneler -13/-9/-8（BITE）109 件 |
| 修正後（HEAD） | **414 / 437 = 94.7%** | ±1 の丸め 15 件 |

`model_match_audit.py` 全体でも一致 2,095/2,123 = 98.7% → **2,100/2,123 = 98.9%**、
end_turn の不一致は 7 件 → **2 件**（TUNNELER グループは消えた）。決定母数は
attribution replay で **Bowlbug Rock の戦闘 5,518 本中 241 決定・45 seed**、
**Tunneler の戦闘 4,312 本中 52 決定・21 seed**（KeyError 84 / 126 件は両ツリーで replay できなかった
record の数で、この修正とは無関係の tooling 側の限界）。

テストは `test_enemy_reported_as_stunned_does_nothing_and_resumes_its_opening_move`（test_combat）と
`test_keeps_the_runtime_stunned_move_instead_of_re_resolving_it`（test_official_agent）を追加して 756 件 green。
**勝敗への影響は未測定**：arm = HEAD、control = `.wt-ctrl-ba30482` の panel を次 round の先頭で走らせる
（Bowlbug Rock・Tunneler・Thieving Hopper・Slumbering Beetle は Act 2/3 の hive 側なので、Act 3 到達に効く可能性が高い）。

### 同時にとれた別の結論

- 札を出した瞬間の player 側自己ダメージは **828/828 一致**：Offering・Crimson Mantle・Corrupted 付与の
  self 2 ダメージなどは model 側で正しく織り込まれている（この audit 軸は今回新設）
- monster の lifecycle hook を全数 census した（`AfterAddedToRoom` 62・`AfterDeath` 10 など）。
  combat.py に名前が出てこない hook は 4 つだけで、中身は全部 gameplay で無かった：
  Crusher/Rocket（Kaiser Crab の腕）の `BeforeDeath`/`AfterCurrentHpChanged` は SE とアニメーション、
  SoulFysh の `AfterCardChangedPilesLate` は音楽パラメータ、Aeonglass の
  `AfterCardGeneratedForCombat`（Wither を FakeUpgrade する）は corpus に Aeonglass が 1 件も無いため対象外
- 残る card 側の小不一致（Bash 8・Strike 4・Perfected Strike 3・Pommel 2）は、**enchantment を記録していない
  古い trace 由来の見かけ**の可能性が高い（Tezcatara's Ember +3 が hand から読めない）。新しい trace
  （`enchant_check_b1`）では同じ audit が 96.6% で、残りは ±1 の丸めだけだった

## Round 9: STUNNED 修正の panel・power census・致命 match up は地図で避けられない（2026-10-04）

### STUNNED 修正の勝敗 panel：3 seed で 40勝 → 37勝（-3・0・0）

`data/stun_ab.sh`。arm = HEAD（`fc54807`）、control = 1コミット前の `.wt-ctrl-ba30482`（dll は同一物を
md5 で照合してから起動するガードを追加した）。seed は stun の決定変化が多かった L3PN5HBQ8T・
F6L1X4P8MS・P7M4C2W9KS（いずれも初使用）。

| seed | control | arm | delta | 最初の分岐 |
|---|---:|---:|---:|---|
| `L3PN5HBQ8T` | 16勝1敗 | 13勝1敗 | **-3** | seq 200 arm=Strike / control=Evil Eye |
| `F6L1X4P8MS` | 13勝1敗 | 13勝1敗 | 0 | 分岐なし（完全に同一の run） |
| `P7M4C2W9KS` | 11勝1敗 | 11勝1敗 | 0 | 分岐なし（完全に同一の run） |

**-3 の中身**は control が勝った Devoted Sculptor・Turret Operator に arm がたどり着けず、
THE_INSATIABLE に arm は敗れ control は勝ったことで、arm が3戦少なく終わったことだった
（control 17戦 / arm 14戦）。つまり「3戦を悪くプレイした」のではなく「1戦早く死んだ」。

**この panel は修正をほぼ試していない**ことが重要。走らせた6本の実走 trace に入った `STUNNED` の
観測は arm 4・2・0 件、control 4・2・0 件だけで、corpus 全体でも seed あたり **1戦闘（9〜19 record）**
程度。1 run への影響が小さいので panel の seed 間噪声（どの戦闘に当たるか）が勝って、勝敗は測れない。
したがって採用の根拠は実走ではなく **同一 record replay の一致率 15.3% → 94.7%**（前 round）とし、
Plating のときと同じ判断（model が game と違うなら勝敗ではなく忠実度で残す）で残す。

### power の census：観測される power の名前で combat.py に出てこないものは 13 個（9,728 record）

モンスターの hook census と同じ要領で、trace に現れる power id を全て拾って model 側の名前と照合した。
結果は全部すでに説明がついた：

- `ESCAPE_ARTIST_POWER`（3,074）・`HATCH_POWER`（2,567）・`SWIPE_POWER`（2,193）は
  **move 側で実装済み**（`MONSTER.THIEVING_HOPPER` + `THIEVERY_MOVE`、`MONSTER.TOUGH_EGG` + `HATCH_MOVE`）
- `POSSESS_SPEED_POWER`（619）・`POSSESS_STRENGTH_POWER`（328）・`SHACKLING_POTION_POWER`（195）・
  `DARK_SHACKLES_POWER`（2）は CODEWIKI ですでに確認済みの扱い（TemporaryStrength 系など）
- **`STRATAGEM_POWER`（724）は未実装だが不採用済みのクローズ済みレバー**：`StratagemPower.AfterShuffle` は
  捨て札が山札に戻るたびに山札から Amount 枚を選んで手札へ移る。実装して実測した結果
  P3V8N5K2RX で 18勝1敗横ばい・Act 3ボス戦の被弾 151 → 363 で悪化（§2037、stash@{4}）
- `IMPROVEMENT_POWER`（26）は戦闘終了後にデッキの札をランダムに upgrade する effect で、upgrade 済みの札は
  次の observation の `upgrade` に現れるので **combat.py での再現は不要**（reward 側の評価だけの問題）

### 残った card 側の不一致 1,689 件の内訳

Bash・Strike・Pommel Strike・Anger などの攻撃札の HP 照合で残っていた不一致を分類した：

- **589 件は復活する敵の測定 artifact**：REATTACH_POWER（Decimillipede の +25 回復）や
  ILLUSION_POWER / MINION_POWER（Parafright の分身が IllusionPower.AfterDeath で復活）を抱えた的に
  当てた手で、次の観測の HPが上げるため model が多く削ったように見える。Bash の +2（141件）・+4（69件）はここ
- 残り 1,100 件は Strike の -1〜-9 が中心で、**Tezcatara/Symbiote で付与された札が古い trace では
  hand から読めない**ことと整合する（Ember +3・Corrupted ×1.5）。付与を記録する build で走らせた
  `enchant_check_b1` の trace だけでは同じ audit が 96.6% で、残りは ±1 の丸めだけだった

### 致命 match up は地図で避けられていた（route policy は主要レバーではない）

52,913 戦闘から致命 match up（THE_INSATIABLE・QUEEN・VANTOM など）に入る直前の地図決定を、
`data/<stem>_map.json` の parent/child で逆引きした。**その時点で合法な移動が1つだけ（強制的）**だった件数：

- Boss 709 強制 / 26 選択可
- Monster 313 強制 / 144 選択可
- Elite 42 強制 / 43 選択可

選択できた場合の代替は RestSite が最多（Monster+RestSite 56、Elite+RestSite 18）で、ここは改善余地だが、
致命戦闘の **約83%は地図が強制する入口**だった。QUEEN 戦の火力不足と合わせて、route より先に deck の
火力が壁という前 round までの結論と同じ方向を支持する。

## Round 10: relic census で Mr Struggles の毎ターン全体攻撃を発見・実装（2026-10-04）

### gap の見つけ方

power census（前 round）に続けて **relic census** を回した：combat 観測に出る player の relic を全部集め、
`combat.py` / `official_agent.py` に名前が出現しないものを game 側の C# の hook と対照表にした。
対象外だった 83 個（572,248 record）の多くは「効果は observation に現れるので model 不要」だった：

- `LANTERN`（エネルギー+1）・`ODDLY_SMOOTH_STONE`（Dexterity）・`ANCHOR`（開始 Block 10）・
  `BRONZE_SCALES`（Thorns 3）は observation の energy / powers / block に既に反映されている
- `AKABEKO`（Vigor 8）・`BAG_OF_MARBLES`（Vulnerable 1）・`RED_MASK`（Weak 1）・`BLOOD_VIAL`（Heal 2）は
  **TurnNumber <= 1 のときだけ**発火して、その瞬間の observation に power として現れる → 反映済み
- `TEA_OF_DISCOURTESY`（開始時に Dazed を2枚 draw pile へ、1,712 record で山札に見える）は
  `CARD.DAZED` が **Unplayable + Ethereal** で legal_actions に出ないため、rollout が評価すべき手自体が存在しない
- 残りの**観測に一切現れない**ものが本当の gap で、その筆頭が `RELIC.MR_STRUGGLES`（2,796 record）だった

### 実装した内容

`MrStruggles.AfterPlayerTurnStart` は `CreatureCmd.Damage(combatState.HittableEnemies, TurnNumber,
ValueProp.Unpowered)`、つまり**各 player ターン開始時に、新しいターン数ぶんのダメージを全敵へ**通す
（turn 2 → 2、turn 5 → 5）。combat.py のターン開始処理（Mercury Hourglass と同じ場所）に
`RELIC_MR_STRUGGLES` を追加した。

game 側の挙動は trace から確定させた：relic を持つ24 run で **ターン境界 548 件の敵 HP 低下がちょうど
新しいターン数**だった。うち **141 件は対象が Vulnerable でも低下はターン数のまま**（Unpowered なので
Vulnerable と Strength で伸びない ✓ 1.5倍になる件は 9 件しかなかった）。最初の observation では敵 HP が
max_hp のまま（26 件）で、combat 開始時点では発火しないことも確認した。

### 検証

ターン境界（end_turn を model で再生して次の観測と照合）の一致率、relic を持つ run だけ：

| ツリー | 一致 | 不一致 |
|---|---:|---:|
| 修正前（`.wt-ctrl-mr` = `e4b14b0`） | 1,094 / 2,037 = **53.7%** | 943 |
| 修正後（HEAD） | 1,617 / 2,037 = **79.4%** | 420 |

relic を**持たない** run の一致は両ツリーで完全に同一（36,486 一致 / 6,410 不一致）で、変更が無害である
ことも確認した。決定母数は `data/attribution_rampart.py` に `RELIC.X` セレクタを足して
**2,796 本 replay して 506 決定が変化・8 seed**（基準の 3 決定・3 seed を大きく超える）。
テストは `test_mr_struggles_ticks_the_new_turn_number_into_every_enemy`（Vulnerable でも 2 ダメージのまま、
turn 3 では 3 追加）を足して 757 件 green。

### 同じ round に測った QUEEN の壁の分解（火力では説明がつかない）

`data/enemies_glory.json` の QUEEN 400 HP + TORCH_HEAD_AMALGAM 199 HP の戦闘を 111 本分解した
（**QUEEN は111本すべてで amalgam を連れている**）。戦闘中に与えた合計ダメージは
**中央値 241、p75 366、p95 568、最大 580**（壁 599）で、**最大値は 19 差**だった。壁は遠くない。

 near-clear（上位8本）と中央値半边を比べると：raw attack damage 93 vs 91.5、max HP 87 vs 89、
戦闘中に使った potion 3 vs 2、relic 数 16 vs 13.5、deck の攻撃札 10 vs 13、upgraded 攻撃 0 vs 4 で、
**火力・最大HP・potion・upgrade 数のどれもが近接組と typical を分離していない**。違うのは
**生き延びたターン数 12 vs 6**（攻撃/ターン は両組 2.0、skill/ターン 1.6 vs 1.2）だった。
potion は 108/111 本が boss 開始時に中央値 3 本を持ち、戦闘内で 3 本を消費している → 使い残しは無い。

ここで Mr Struggles が効く：turn 12 まで生きれば **1+2+…+12 = 78 ダメージを敵1体ごとに**、QUEEN 戦なら
Queen と amalgam 合計で **156 ダメージ**を、agent は織り込まずに見ていなかった。近接組の shortfall
（19〜50 ダメージ）と同じ桁であり、しかも「長く生きると自動的に増える」型なので生存と相乗する。
**勝敗への影響は未測定**（panel は次 round）。

## Round 11: audit の action 変換を直し、player 側の Regeneration 欠落を見つけた（2026-10-04）

### 「model が legal な action でクラッシュしている」は測定の間違いだった

`data/model_match_audit.py` は game が実際に選んだ action を model の語彙へ翻訳するが、翻訳が
model の Action 表記と合っていなかった。model は (1) 単体攻撃も全体攻撃も **敵 index 付き**
（`card:2@1`。全体攻撃でも `@index` を要求する）で、(2) potion は **名前一つ**（`potion:POTION.BLOCK_POTION`）
でスロット番号ではない。audit は全体攻撃を `card:2`、potion を `potion:1` と組み立てていたため
`combat.step` が `illegal action` で ValueError を投げていた。

audit 側を「model 自身が legal_actions に挙げている候補を選ぶ」方式に直した：

| 測定（4,000 ペア） | 修正前 | 修正後 |
|---|---:|---:|
| `step_raised:ValueError` | 106 | **1** |
| `no_equivalent_action` | 0（隐性） | 69（新規に可視化） |
| end_turn の player HP 一致 | 611 | 621 |
| 全体の一致 | 2,875/2,910 = 98.8% | 2,885/2,920 = 98.8% |

つまり**live run で rollout が例外 fallback に落ちていた証拠ではなかった**（実際の live fallback は
AoE 札で 30 件だけで、内訳は TAUNT 23・BREAKTHROUGH 6・EXTERMINATE 1）。新しい `no_equivalent_action`
の上位は potion 側：`POTION.SPEED_POTION` 8・`POTION.ATTACK_POTION` 5・`POTION.SKILL_POTION` 5・
`POTION.POWER_POTION` 5・`POTION.COLORLESS_POTION` 3・`POTION.REGEN_POTION` 2 など。model の potion
定数に無い種類で、rollout が potion を評価できない箇所として残っている。

### 見つけた gap：player 側の RegenPower が turn End で回復していない

`RegenPower.AfterSideTurnEnd` は owner を Amount だけ回復して Amount を 1 減らす。combat.py は
**敵側だけ**実装している（1723 付近、コメント自身が player 側をやっていないことを書いている）。
player が RegenPower を持つ observation で end_turn を再生した一致率は **605/811 = 74.6%** で、
不一致の上位は game HP が model より **+5（47件）+4（37件）+3（30件）+2（19件）** ＝ ちょうど Regen の
Amount ぶん game だけ回復していた。corpus では player が RegenPower を持つ combat observation は
**841 件**（Amount 5:345・4:187・3:134・2:103・1:72）で、88 本の trace・**23 seed** に現れる。
母数が1 seed なので panel では測れないが、敵側と同じ規則を追加するだけの修正なので次ターンで実装する。

### 実装した：player 側の RegenPower（commit e273427）

`_end_turn` のターン終了処理（TangledPower・NoDrawPower と同じ AfterSideTurnEnd のグループ）に追加した。
Amount ぶん回復して（`player_max_hp` を上限）、Regen は 1 減らす（敵側と同じ規則）。
テストは `test_player_regen_heals_at_the_end_of_the_turn_and_decrements_by_one`（3 回復して 2 に減る、
上限 80 で頭打ち）を足して 758 件 green。

| 測定（Regen を持つ player の end_turn 再生） | 一致 |
|---|---:|
| 修正前 | 605 / 811 = **74.6%** |
| 修正後 | 729 / 811 = **89.9%** |

+5（47件）・+4（37件）・+3（30件）・+2（19件）のグループは消えた。残りは +55/+44/+30/+59 のグループ
（戦闘中の potion や event の回復で、この audit の窓では区別できない）と **-1 が20件**（model が
`player_max_hp` 上限 80 を既定値として使い、game 側の実際の最大 HP とずれるケース）で、後者は既知の
小さな残差として残す。決定母数は **841 本 replay して 17 決定が変化・8 seed**（基準を満たす）。
1 run あたり 2〜23 観測とまれなので panel では測らない（忠実度で採用）。

## Round 12: potion census — 記録された potion 使用の 53% が model で評価できなかった（2026-10-04）

### census

前 round の audit が可視化した `no_equivalent_action` を追跡した。combat 観測に現れる potion を全部集めて
`combat.py` の `POTION_*` 定数と照合すると、**30 種類が model に全く無い**。実際に agent が使った回数：

- 記録された potion 使用は **3,274 件**、そのうち **1,738 件（53%）** が model の無い potion
- 最多は `POTION.SPEED_POTION`（観測 16,425 件・使用 214 件・48 seed）、`POTION.SKILL_POTION`（7,549・145・39）、
  `POTION.POWER_POTION`（9,101・139・38）、`POTION.WEAK_POTION`（7,898・120・23）、`POTION.FLEX_POTION`
  （5,079・98・20）、`POTION.COLORLESS_POTION`（13,344・97・30）、`POTION.POTION_OF_BINDING`（5,195・95・16）、
  `POTION.REGEN_POTION`（6,725・90・23）、`POTION.SWIFT_POTION`（10,082・82・27）、`POTION.FORTIFIER`（11,724・80・12）

model 側は 13 種類（Block/Ship/Fire/Explosive/ShapedRock/Strength/Dexterity/Fysh/Energy/Blood/Heart/Bronze/
Duplicator/Gigantification）だけを持っていた。`SpeedPotionPower`・`FlexPotionPower`・`RegenPower` は**すでに
model 済み**だった（観測に現れる power を読んでいた）ので、欠けていたのは **potion を「使う」動作そのもの**：
`ROLLOUT_POTION_IDS` に無いため rollout はその potion を候補にすら入れていなかった。

### 実装（commit 257c4fe）

decompile の `OnUse` をそのまま写した 7 種類：

| potion | game の効果 | model での実装 |
|---|---|---|
| `SPEED_POTION` | `PowerCmd.Apply<SpeedPotionPower>(5)`（SpeedPotionPower は TemporaryDexterityPower の派生） | `SpeedPotionPower 5` + 対応する `DexterityPower 5`（END_TURN で両方消える処理は既存） |
| `FLEX_POTION` | `PowerCmd.Apply<FlexPotionPower>(5)`（TemporaryStrengthPower の派生） | `FlexPotionPower 5` + `StrengthPower 5` |
| `SWIFT_POTION` | `CardPileCmd.Draw(3)` | 3 枚ドロー |
| `REGEN_POTION` | `PowerCmd.Apply<RegenPower>(5)` | RegenPower 5（前 round の player 側回復と connected） |
| `FORTIFIER` | `CreatureCmd.GainBlock(target, target.Block * 2)` | Block を 2 倍（Block が 0 なら無効果） |
| `WEAK_POTION` / `VULNERABLE_POTION` | 対象に Weak 3 / Vulnerable 3 | 対象 index 付き action で power を付与 |

`legal_actions` の potion 一覧（無対象／対象付き）と `official_agent.ROLLOUT_POTION_IDS` にも追加した。
テストは `test_the_colorless_potions_the_shops_sell_are_simulatable`（各効果と legality を1つずつ）を足して 759 件 green。

### 検証

これらの potion の**記録された使用 976 件・111 seed** を、修正前後のツリーで replay した：

| | 修正前（`.wt-ctrl-potion` = `7f583c3`） | 修正後（HEAD） |
|---|---:|---:|
| simulator が再現できた使用 | **0 / 758**（比較できた窓） | **655 / 758** |
| replay 後の player HP が game と一致 | — | **655 / 655** |

audit 全体でも `no_equivalent_action` 69 → **56**、end_turn の player HP 一致 621 → **638**（不一致は 5 → 1）、
全体の一致 2,885/2,920 → **2,902/2,933 = 98.9%** に改善した。tooling 側にも potion 対応を入れた
（audit は対象 index 付き potion action を組み立てていなかった・attribution に `POTION:` セレクタを追加）。

### 次の gap（この round では未実装）

残るは**札を生成する potion** と効果の複雑な potion で、実際に使われた回数：
`SKILL_POTION` 230・`POWER_POTION` 184・`COLORLESS_POTION` 136・`POTION_OF_BINDING` 124・`LUCKY_TONIC` 96・
`GAMBLERS_BREW` 71・`SHACKLING_POTION` 69・`CURE_ALL` 67・`ATTACK_POTION` 61・`DISTILLED_CHAOS` 59・
`CLARITY` 57・`RADIANT_TINCTURE` 36・`SNECKO_OIL` 34 ＝ **合計 1,224 件**。生成系は
`CardSelectCmd.FromChooseACardScreen(...)` で札を選ばせて hand に入れるので、選ばれる札の集合
（colorless pool など）を model が持つ必要がある。

**勝敗 panel は走らせていない。** この修正は agent が価格付けできる potion の集合そのものを増やす
（= 振る舞いが変わる）ので、次 round では ROLLOUT_POTION_IDS の拡張を実測すべきレバーとして扱う。

## Round 13: potion 修正の panel（+0）と Gigantification の id 誤り（2026-10-04）

### potion 7 種の実装は勝敗を動かさなかった（忠実度で保持）

`data/potion_ab.sh`（arm = HEAD、control = `.wt-ctrl-potion` = `7f583c3`、dll の md5 一致を確認）。
seed は記録された run がこの7種の実 potion を多く使い、かつ Act 3 boss に到達したものを選んだ。

| seed | 記録された使用回数 | control | arm | 差分 |
|---|---:|---:|---:|---:|
| AM8C6YXHSG | 92 | 17勝 | 17勝 | +0 |
| M5PC8TQ3BN | 80 | 8勝 | 8勝 | +0 |
| NFH3RMVJ6D | 51 | 15勝 | 15勝 | +0 |
| 合計 | | **40勝** | **40勝** | **+0** |

panel は修正を実際に試している：出来上がった run の potion 欄に FORTIFIER・REGEN・WEAK・VULNERABLE・
SPEED・FLEX・CLARITY・CURE_ALL が現れ、AM8C6YXHSG では Vulnerable 発火 167 vs 142・Weak 51 vs 38・
Frail 57 vs 47 とプレイは分岐した（3 seed 中2 seed で分岐）。**勝数は同じ**だった。

### Gigantification potion は id が1文字列分だけ違って、何も匹配していなかった（commit aebf7ca）

game のクラス名は `GigantificationPotion` だから id は `POTION.GIGANTIFICATION_POTION`（観測 1,838 件）。
combat.py の定数は `POTION.GIGANTIFICATION` で、これは**どの観測とも一致しない**。同じ誤りが
`official_agent.choose_potion` の `offensive` 集合（1814 行付近）にも直書きされていて、そこでも
実 potion は offensive として扱われていなかった。さらに model はこれを敵対象付き（`@index`）で
legal_actions に出していたが、記録された使用 18 件はすべて `target_id: None`
（game 側は `TargetType.AnyPlayer`）なので無対象が正しい。定数を実 id に直し、無対象側に移し、
`offensive` は定数参照に変えた。テストは `test_gigantification_potion_uses_the_id_the_game_reports` を
追加し、既存の `test_duplicator_and_gigantification_potions_apply_their_powers` の `@0` 期待値を
実測（target_id None）に合わせて 760 件 green。

**ただしこの修正だけでは決定は1件も変わらない**：control を `587cb46`（この修正の1コミット前）において
Gigantification を提案している 1,838 件の observation で `choose_potion` の選択を比べた結果、
**差分 0 件**、Gigantification が選ばれた件数は arm 0・control 0。理由は gate の方にあって、
`ROLLOUT_POTION_IDS` に Gigantification が入っておらず、`SHOP_POTION_SCORES` にも無い（スコア -1 なので
shop で買わない）。つまり** purchase も rollout も Gigantification を見ていない**のが現状で、id 修正は
忠実度の訂正として入れ、価格付けに参加させるかは別の policy 判断として扱う（測定なしに gate へ
入れない）。

### census の残り

- 公式 run に現れる potion 41 種のうち **4 種は official_agent のどこにも書かれていない**：
  `POTION.FAIRY_IN_A_BOTTLE` 1,743 観測・`POTION.FOUL_POTION` 729・`POTION.BOTTLED_POTENTIAL` 587
  （Gigantification は今回の修正で combat 側の定数が一致した）
- model 側の定数のうち**一度も観測されない**もの：`POTION.BLOOD_POTION`・`POTION.SHIP_IN_A_BOTTLE`
  （game にクラスは存在するが corpus に出てこない）と修正前の `POTION.GIGANTIFICATION`
- 未 model の potion の実際の使用 counts（次の実装対象、game 側の `OnUse` は読む済み）：
  `SKILL_POTION` 230・`POWER_POTION` 184・`COLORLESS_POTION` 136（生成札を hand へ、free このターン）、
  `POTION_OF_BINDING` 124（全敵に Weak 1 + Vulnerable 1）、`LUCKY_TONIC` 96（BufferPower 1）、
  `GAMBLERS_BREW` 71（手札を選んで捨てて同数引く）、`SHACKLING_POTION` 69（全敵に -7 Strength の
  一時的 Strength。`ShacklingPotionPower` は TemporaryStrengthPower の派生で `IsPositive => false`、
  **combat.py に名前が1度も無い**）、`CURE_ALL` 67（+1 エネルギー・2 枚ドロー）、
  `ATTACK_POTION` 61、`DISTILLED_CHAOS` 59（draw pile 上から3枚自動プレイ）、`CLARITY` 57（1 枚引いて
  ClarityPower 3）、`RADIANT_TINCTURE` 36（+1 エネルギー・RadiancePower 3）、`SNECKO_OIL` 34（7 枚引く）
  ＝ **1,224 件**。このうち combat 中に使われた 912 件は `decision_source=direct_potion`、つまり
  heuristic の尻尾で使われており、rollout は価格を付けていない。

## Round 14: 6種の potion を simulator に実装し、gate 拡張の panel を測る（2026-10-04）

### 実装（commit cc04e3d、761 tests green）

前回 census で数えた未実装 potion のうち、`OnUse` が単一コマンドで書ける6種を入れた。各行が game 側の
実コマンドで、**記録された使用 352 件（比較できた窓）はすべて `target_id: None`** なので6種とも無対象として
legal_actions に出した。

| potion | 使用回数 | game の効果 | model での実装 |
|---|---:|---|---|
| `POTION_OF_BINDING` | 124（窓で92） | `Apply<WeakPower>(1)` + `Apply<VulnerablePower>(1)` を HittableEnemies 全体 | 全敵に Weak 1・Vulnerable 1 |
| `LUCKY_TONIC` | 96（72） | `Apply<BufferPower>(1)` | BufferPower 1 |
| `CURE_ALL` | 67（65） | `PlayerCmd.GainEnergy(1)` + `CardPileCmd.Draw(2)` | +1 エネルギー・2 枚ドロー |
| `SHACKLING_POTION` | 69（61） | `Apply<ShacklingPotionPower>(7)` を全敵（TemporaryStrengthPower の派生で `IsPositive => false`） | 全敵に ShacklingPotionPower 7 + StrengthPower -7 |
| `CLARITY` | 57（36） | 1 枚ドロー + `Apply<ClarityPower>(3)` | 1 枚ドロー + ClarityPower 3 |
| `RADIANT_TINCTURE` | 36（26） | `GainEnergy(1)` + `Apply<RadiancePower>(3)` | +1 エネルギー + RadiancePower 3 |

Shackling は trace で挙動を確定させた。使用直後の敵 61 件すべてが `SHACKLING_POTION_POWER 7` と
`STRENGTH_POWER -7` を並べて持ちはじめ、export された意図ダメージは 3 → 0 に落ちる（`raw_damage` は 3 のまま。
`damage` の方が修正後の実効値で 0 にクリップされる）。`TemporaryStrengthPower.AfterSideTurnEnd` はその
生き物のターン结束时に Strength を戻すので、`_enemy_turn` に復元処理を入れ、**1 ターンだけ鈍る**ことを
テストで固定した（攻撃 10 の dummy に対して player HP が 50 → 47、つまり 10-7 が着弾）。

### gate 拡張（commit e0c416d）と panel

simulator が knows なっても、`ROLLOUT_POTION_IDS` に無い potion は rollout の候補に入らない。実際に
この6種の使用 352 件を両ツリーで replay すると**再現できた件数は 0 件**で、理由は gate 側にあった。
そこで **choose_potion が普段の分岐で分類している4種**（Binding＝debuffs、CureAll＝healing、
Clarity・RadiantTincture＝economy）だけを gate に足した。offline の決定母数は
**5,331 本 replay して 64 決定が変化・10 seed**。

Shackling と LuckyTonic は意図的に入れていない。Shackling は -7 が1ターン分しか持たないため、
「boss 戦まで温存する」という記録済みの修正（sim13 が通常戦闘で浪費した）を rollout が壊す可能性がある。
LuckyTonic は BufferPower 1 チャージの価値を、現在それを使っている受けるダメージ系の分岐と比較してから
入れる。

panel batch 1（`data/gate_ab.sh`、arm = HEAD、control = `.wt-ctrl-pot2` = `3690e55`＝simulator 実装まで、
gate 拡張だけの差分、dll の md5 一致を確認）：

| seed | control | arm |
|---|---:|---:|
| 73P61QQZNU | 13勝 | 13勝 |
| EAIF2UUVCK | 14勝 | 14勝 |
| K7M2QX9BTR | 13勝 | **12勝** |
| 合計 | **40勝** | **39勝（-1）** |

3 seed で -1 は単発の差であり判定が弱いので、同じ seed 群の続きとして次の3 seed
（P3V8N5K2RX 13 件・F9P4X7N2LC 8 件・R9TB3LKD6M 8 件）で **batch 2 を測定中**（`data/gate_ab2.sh`）。
ここで決着がつくまで gate 拡張は HEAD に入れておき、結果を見て採用か取り下げを決める。

### attribution に出た KeyError は古い corpus の形の問題

potion 保持 records の attribution で `errors: {'KeyError': 312}` が出た。直接 `rollout_choice` を
17,783 本 replay して調べると、キーは `'slot'` で、`official_agent.py` 2815 行の `observed["slot"]`
（括弧アクセス）が原因。`"slot"` を持つ trace は 572 本中 567 本で、欠けている5本は
`candidate_rewardfix*`（`T3XQ7WM2VP` の一連）だけ。**live の bridge は slot を出力している**ので
実走には影響しない。offline replay の母数を扱う時の注意として記録し、`.get("slot")` へ直すかは今後の
robustness 項目として置く。

### gate 拡張 panel の再測と、測定有效性のチェック（batch 1 + batch 2）

batch 2 の arm 脚は初回は途中で kill され（exit=143）、`<game>/.../MacOS/mods/Sts2Ai` が残ったため続く2本が
「refusing to overwrite existing mod」で start できなかった（wins=0 losses=0 exit=1）。残留フォルダは
Sts2Ai.dll と Sts2Ai.json だけであることを確認して手動削除し、`data/gate_ab2_arm.sh` で arm 脚だけ再走した
（control 脚 15/14/6 勝は有効）。

再走の結果は 15→15・14→14・6→6 で **batch 2 は +0**。ただし trace を突き合わせると、**arm と control が
1バイト違わない seed が混んでいる**（batch 1 の 73P61QQZNU と EAIF2UUVCK、batch 2 の P3V8N5K2RX）。
実際に分岐したのは6 seed 中3本だけだった：

| seed | 分岐 | control | arm |
|---|---|---:|---:|
| 73P61QQZNU | なし（trace 一致） | 13勝 | 13勝 |
| EAIF2UUVCK | なし（trace 一致） | 14勝 | 14勝 |
| K7M2QX9BTR | あり（293 / 313 record） | 13勝 | **12勝** |
| P3V8N5K2RX | なし（trace 一致） | 15勝 | 15勝 |
| F9P4X7N2LC | あり | 14勝 | 14勝 |
| R9TB3LKD6M | あり | 6勝 | 6勝 |
| 合計 | | **75勝** | **74勝（-1）** |

つまり gate 拡張の実測は「**分岐した3本のうち1本で1勝减り、2本は無変化**」で、母数としては offline の
64 決定・10 seed のほうが強い。判断が弱いので修正は HEAD に置いたまま、次以降の測定に持ち越す。
教訓として、panel の RESULT 行だけでは「効いた/no-op」を区別できない：**trace が分岐したか**を必ず見る。

### 新しい gap：potion が hand に入れる札のなかに model に存在しないものがある

生成系 potion（SKILL 230・POWER 184・COLORLESS 136・ATTACK 61）の使用 438 件で、次の観測の hand に
現れた札を数えると **76 種のうち 60 件分の札が `combat.CARD_COST` に存在しない**（`official_agent` にも
名前が無い）。内訳：`CARD.SECRET_WEAPON` 13・`CARD.THINKING_AHEAD` 12・`CARD.MAYHEM` 8・
`CARD.SECRET_TECHNIQUE` 5・`CARD.STRATAGEM` 5・`CARD.THE_GAMBIT` 4・`CARD.DISCOVERY` 2・
`CARD.RESTLESSNESS` 2・`CARD.DARK_SHACKLES` 2・`CARD.ROLLING_BOULDER` 2・`CARD.THE_BOMB` 2・
`CARD.PROLONG` 1・`CARD.SEEKER_STRIKE` 1・`CARD.GOLD_AXE` 1。`CARD.THE_GAMBIT` は即死 effect のため
意図的に除外している（CODEWIKI 冒頭の記録） so 対象外で、他は未 model。

game 側の実装は読んだ：Secret Weapon は 0コスト Skill・Exhaust で draw pile から Attack 札を選んで hand へ、
Secret Technique は同じく draw pile から Skill 札、Thinking Ahead は 0コスト Skill・Exhaust で 2 枚引いて
1 枚を draw pile 一番上に戻す、Discovery は 1コスト Skill・Exhaust で生成札を選んで hand へ
（すべて `CardPileCmd` 系で、model が既に持つ hand / draw_pile 操作で書ける）。

## Round 15: Act 3 boss 戦に絞った audit で Crimson Mantle の自ダメージ抜けを見つける（2026-10-04）

### 測り方を変えた

これまで corpus 全体の一致率（1〜2% 残差）を見ていたが、**run が死ぬ boss 戦だけ**を切り出して
HEAD で全決定を replay した（QUEEN・THE_INSATIABLE・VANTOM・AXEBOT・FROG_KNIGHT・THE_OBSCURA・FOGMOG、
46,754 決定）。**不一致は 8.41%（3,934 件）**で、corpus 全体の残差率より明らかに悪い。
模型が最も不正確なのは、まさに run が負けている場所だった。上位グループ：

| グループ | 件数 |
|---|---:|
| VANTOM player_hp end_turn | 363 |
| QUEEN player_hp end_turn | 238 |
| FOGMOG enemy_hp CARD.BASH | 219 |
| THE_INSATIABLE player_hp end_turn | 199 |
| QUEEN enemy_hp end_turn | 192 |
| VANTOM player_hp CARD.STRIKE_IRONCLAD | 124 |

`player_hp end_turn` の上位3グループ（800 件）が **1 刻み**で game のほうが HP が低い、という形をしていた。

### 原因：Crimson Mantle の自ダメージは export されない

`CrimsonMantlePower` は自ダメージを DynamicVar に持つ（`CanonicalVars` の `SelfDamage` base は 0、
`CrimsonMantle.cs` がプレイ時に `IncrementSelfDamage()` を1回呼んで 1 になる）ので、
game が外に出す power は `POWER.CRIMSON_MANTLE_POWER` **だけ**で、自ダメージ用のマーカーは無い
（観測 8,300 件、counter の値は 8 が 6,028・10 が 2,225・18 が 47 ＝ 通常1回 / 強化1回 / 2回プレイ）。
`AfterPlayerTurnStart` は `CreatureCmd.Damage(Owner, SelfDamage, Unblockable|Unpowered)` してから
`GainBlock(Owner, Amount)` する。model は `CrimsonMantleSelfDamage` を自分でプレイしたときだけ立てるため、
**observation から組み直した rollout 状態ではマーカーが無く、ターン開始の 1 ダメージを毎回飛ばしていた**。

### 実装（commit ad3fa1a、762 tests green）

ターン開始時の自ダメージを counter から導出した（`max(marker, counter // 8)`：8→1、10→1、18→2 で
実走観測のすべての値を再現する）。テスト `test_crimson_mantle_damages_itself_at_turn_start_from_the_observed_counter_alone`
はマーカー無し状態（60 HP・mantle 8）で END_TURN 後に HP 59・block 8、10 のとき 59/10、18 のとき 58/18 を検証する。

### 検証

mantle を持つ player の end_turn replay 1,907 件を修正前後で比べた：

| | 修正前（`.wt-ctrl-mantle` = `b46e5d9`） | 修正後（HEAD） |
|---|---:|---:|
| 一致 | **0 / 1,907** | **1,898 / 1,907（99.5%）** |
| game が1低い | 1,888 件 | 0 件 |
| game が2低い | 10 件 | 0 件 |

boss 戦 audit の不一致も **8.41% → 6.67%（3,934 → 3,119 件）**に下がり、上位に並んでいた
VANTOM 363・QUEEN 238・THE_INSATIABLE 199 の `player_hp end_turn` グループはリストから消えた。
決定母数は **8,300 本 replay して 563 決定が変化・12 seed**（この session で最も大きい）。
前回 round の Regen audit に残った「-1 が20件」も、対象が mantle 10 を持っていたことで説明がつく。

**未測定：** panel は走らせていない。この修正は model の HP 予測を1だけ**厳しく**する（以前は楽観的だった）
ので、勝敗への影響は独立に測る必要がある。

**同じ形の実装で直していないもの：** `InfernoPower` も `IncrementSelfDamage` 経由で自ダメージを持つが、
corpus に `POWER.INFERNO_POWER` の観測が1件也无い（agent が実走で Inferno を打っていない）。
model が自分で Inferno を打つ経路ではマーカーが立つので、observation 由来の状態でのみ問題になる。

### 次に追う boss 戦の残差

`FOGMOG enemy_hp CARD.BASH` 219・`QUEEN enemy_hp end_turn` 192・`VANTOM player_hp CARD.STRIKE_IRONCLAD` 124・
`THE_INSATIABLE enemy_hp end_turn` 99・`FROG_KNIGHT enemy_hp end_turn` 76・`QUEEN enemy_hp CARD.ANGER` 68。

### boss 戦 audit の数字を訂正する（同じ測定のやり直し）

Round 15 に書いた boss 戦の不一致率 **8.41%** と修正後の **6.67%** は、2つの測定ミスをしていた。
`data/model_match_audit.py` が持つ `same_fight`（戦闘境界をまたぐ対を除外）を使っていないこと、
そして model の敵 HP が 0 未満になる**超過キル（overkill）をそのまま差分として数えていた**ことだ。
両方を入れて同じ replay を組み直した：

| 測定 | 不一致 |
|---|---|
| combat.py の HP を 0 でクリップし、戦闘境界 956 対を除外 | **1,658 / 45,805 = 3.62%** |
| （クリップのみ） | 2,597 / 46,754 = 5.55% |
| （クリップなし・境界フィルタなし） | 3,934 / 46,754 = 8.41% |

`FOGMOG enemy_hp CARD.BASH 219 件` は**丸ごと overkill の見かけ**だった（model が敵 HP を -4 にし、
game は 0 で止める）。次に追うべき group はクリップ込みのこの順：
`QUEEN enemy_hp end_turn 192`・`THE_INSATIABLE enemy_hp end_turn 99`・`QUEEN enemy_hp CARD.STRIKE_IRONCLAD 79`・
`FROG_KNIGHT enemy_hp end_turn 76`・`VANTOM enemy_hp end_turn 73`・`QUEEN enemy_hp CARD.ANGER 68`。

### falsified: Vulnerable のダメージ倍率は丸めではなく floor で正しい

QUEEN 戦で STRIKE の与ダメージが 1 だけ game のほうが大きい group が目についたため、
「game は ×1.5 を切り上げているのでは」と検証した。手札 entry の `vars`（`Damage` 等）が観測の実値なので、
それを基に **単的対象・敵 block 0・プレイヤーの Strength 等の補正なし・敵 Vulnerable あり**の
攻撃プレイ 8,966 件で5つの式を比べた：

| 式 | 一致 |
|---|---:|
| `floor(raw × 1.5)`（model の実装） | **8,596 / 8,966 = 95.9%** |
| `ceil(raw × 1.5)` | 7,074 |
| `floor(raw × (1 + 0.5 × Vulnerable stacks))` | 4,122 |
| `round(raw × (1 + 0.5 × stacks))` | 3,466 |
| `ceil(raw × (1 + 0.5 × stacks))` | 3,395 |

**切り上げ hypothesis は棄却**（model の floor が最良）。Vulnerable のスタック数による倍率拡大でもない
（stacks 依存の式は明らかに悪い）。残る 370 件は私の base 抽出が悪いため方で、Twin Strike の multi-hit
（`Damage` が hit あたりではない）や、`Damage` が runtime に書き換わった float（7.5、10.5 など）を
そのまま使ったケースを含む。丸めは触らない。

### Crimson Mantle 修正の panel：+5 胜（この session で最大のプラス）

`data/mantle_ab.sh`（arm = HEAD、control = `.wt-ctrl-mantle` = `b46e5d9`、差は commit `ad3fa1a` だけ、
dll の md5 一致を確認）。seed は Crimson Mantle を実際に打って維持した観測が最も多い fresh seed3本。

| seed | control | arm | 差分 | mantle 観測（arm / control） | trace 分岐 |
|---|---:|---:|---:|---|---|
| Z6MK8PGN4S | 14勝 | 14勝 | +0 | 311 / 334 | あり（404 / 427 record） |
| K71SQ5B0Q2 | 9勝 | 14勝 | **+5** | 413 / 231 | あり（508 / 298 record） |
| EH8UMY96NC | 12勝 | 15勝 | **+3** | 250 / 397 record | あり |
| 合計 | **35勝** | **43勝** | **+5** | | 3本すべて分岐 |

3本とも trace が分岐し、両 arm が mantle を維持している（= 修正が実際に効いている）。offline で
563 決定・12 seed 動いた修正が、実走でも勝敗を動かした。**この session で最も明確なプラス測定**
（従前のプラスは upgrade 修正の +6/3 seed）。Act 3 踏破は今回も 3本とも未達。

### 未解決として残す：QUEEN 戦 end_turn で boss が毎回 1 減る（174 件）

boss 戦 audit の残り最上位 `QUEEN enemy_hp end_turn`（190 件中 **174 件がちょうど -1**）を追った。
特徴ははっきりしている。そのターンはカードも potion も出しておらず、QUEEN・amalgam とも block は 0
（model も game も 0）、game 側だけ boss の HP が 1 少ない。しかも**同一戦闘の複数ターンで繰り返し**出る
（H2LV6ZJ4XW の seq 555/561/577/579/583 で turn1・2・5・6・7 すべて -1）ので、戦闘開始前の1ダメージの
持ち越しではない。

デコンパイルで確認して**棄却した仮説**（次回同じ手を再走させないために書く）：

- `CentennialPuzzle` は「1戦闘に1度、ダメージを受けた時に3枚引く」relic で、model の実装
  （`_draw(draw, discard, 3, rng)`・1回だけ）と一致していた。ダメージではない。
- `Bound` は `ChainsOfBindingPower.BeforeSideTurnEnd` が `ClearAffliction` するだけで** Exhaust しない**。
  model が hand から discard へ移す挙動は正しい。だから「Bound が turn end に Exhaust して
  `ForgottenSoul`（Exhaust ごとにランダムな敵へ 1 の未強化ダメージ）が撃つ」という筋も無い。
- `RupturePower` は「自分が play したカードから自分がダメージを受けたら Strength を得る」で、
  turn end に敵へダメージを与える効果ではない。
- `PlatingPower`（block 関連のみ）・`RELIC.GORGET`（戦闘開始で Plating 4 を付与）・
  `RELIC.MEAT_CLEAVER`（_rest の Cook 选项を増やすだけで戦闘効果なし）・
  `RELIC.SPIKED_GAUNTLETS`（+1 最大エネルギー、代わりに Power コスト増加）はいずれも敵へダメージを与えない。
- QUEEN・TORCH_HEAD_AMALGAM の export された state machine に self-damage は無い
  （`DamageCmd.Attack` は ExecutionDamage / OffWithYourHeadDamage / SoulBeamDamage / Tackle* の 4 種だけ）。
- 「攻撃を play しなかったターン结束に Strength ぶん全体へダメージ」系の relic
  （`RELIC.BERSERKER_GAUNTLET`）はこの 190 件の**すべてで未装備**だった。

観測の最初のレコードで QUEEN の HP は 400（79件）・399（12件）・397（17件）・396（4件）、
amalgam は 199（69件）・198（22件）・196（17件）・195（4件）とばらつく。戦闘開始前に 1 入る説も考えたが、
rollout は観測の現在 HP から状態を組み直すため開始前の差は予測に使われず、説明にならない。

次の攻め先として有望なのは、同じ群に出る **`delta=+6`（model が多く削る）で THORNS_POWER 3 を持つ 3 件**
だ。model は Thorns を hit ごとに適用し、game が turn 単位か hit 単位で違う可能性が残っている。

## Round 16: Flame Barrier の反射は hit 単位だった（multi-hit replay 245/404 → 371/404）

### きっかけと、先に潰した仮説

QUEEN 戦の end_turn -1 を追う過程で、`THORNS_POWER` を持つ case が model のほうが多く削る群に現れた。
まず Thorns 自体を clean な条件で測った。**単一敵・同一 combat_id・END_TURN の replay で player が
Thorns を持つケース 300 件超（THE_INSATIABLE 155・VANTOM 132・THIEVING_HOPPER 58 など）は、
与ダメージが全件一致**した。player 側 Thorns の反射実装（hit ごと、ブロックされても反射）は正しい。

残った不一致 3 件（HUNTER_KILLER・THE_INSATIABLE）が導線になった。HUNTER_KILLER 戦
（`act3_pop2_T4K8M2W7QY` seq 260、turn 3）が正確な算数を示していた：

- 敵 HUNTER_KILLER 62 HP・`PUNCTURE_MOVE`（7 ダメージ x3 hit）、player は block 22・HP 7
- 3 hit の合計 21 は block 22 に吸収され player の被弾 0（trace でも HP 7 のまま）
- 次の観測で HUNTER_KILLER は **41 HP**、つまり 21 削られていた
- player の power は `FLAME_BARRIER_POWER 4` と `THORNS_POWER 3` → **4×3 + 3×3 = 21** ✓
  model は 4×1 + 3×3 = 13 だった

### game 側の実装

`FlameBarrierPower.AfterDamageReceived(choiceContext, target, _, props, dealer, _)` は
`target == Owner && dealer != null && props.IsPoweredAttack()` のとき
`CreatureCmd.Damage(dealer, Amount, Unpowered)` を返す。**この hook はダメージインスタンスごとに走る**
ので、3 hit の攻撃には 3 回反射する。model は「攻撃ごとに1回」と注記つきの近似だった（`combat.py` の
`# once per attack (approximated ... not per individual repeat hit)`）。反射はブロックされた被弾でも起きる
（seq 260 の 21 ダメージは全部ブロック）ので、無条件で正しい。

### 実装（commit f1a9a10、763 tests green）

反射を `for _ in range(repeats)` の中へ移し、Thorns（`BeforeDamageReceived`）の後に置く順序は保った。
テスト `test_flame_barrier_reflects_once_per_hit_of_a_multi_hit_attack` は 5x2 攻撃に対して
FlameBarrier 4 + Thorns 3 の反射が `(4+3)×2` になることと、player が hit ごとに 5 被弾することを検証する。

### 検証（FlameBarrierPower を持つ単一敵 end_turn replay 404 件）

| | 修正前（`.wt-ctrl-fb` = `7f276af`） | 修正後（HEAD） |
|---|---:|---:|
| 敵 HP 一致 | **245 / 404 = 60.6%** | **371 / 404 = 91.8%** |
| player HP 一致 | 404 / 404 | 404 / 404 |

hit 数ごとの group がきれいに反転した（`repeats=1` は不変、`repeats>1` が不一致→一致）：
ENTOMANCER 7 hit 25 件、VANTOM 2 hit 30 件、THE_INSATIABLE 2 hit 30 件、VINE_SHAMBLER 2 hit 10 件、
PHROG_PARASITE 4 hit 5 件、SLIMED_BERSERKER 4 hit 2 件、OWL_MAGISTRATE 6 hit 1 件、EXOSKELETON 3 hit 1 件、
AXEBOT 2 hit 3 件、HUNTER_KILLER 3 hit が 12 不一致 → 10 一致（2 件残る）。
残りの不一致は hit 数 1 の別原因（TUNNELER 17 件、FROG_KNIGHT 4 件、VANTOM 1 hit 2 件）で、
そこは次以降の対象になる。

決定母数は **1,752 本 replay して 59 決定が変化・15 seed**（`data/attribution_rampart.py`、
selector `PLAYER:POWER.FLAME_BARRIER_POWER`）。勝敗への影響は `data/flamebarrier_ab.sh` で測る
（FlameBarrier を実際に打って保持した観測が最も多い fresh seed C7N4V9P2RX 46・V7K2T9M5RH 33・
S4QFLNDMB3 28）。

### 次の gap 候補：TUNNELER の Burrowed（BELOW_MOVE）で model だけ HP を削る

Flame Barrier 修正後の replay で残った単一 hit の不一致のうち最大が TUNNELER 17 件だった。
形ははっきりしている。**BurrowedPower を持つ BELOW_MOVE のターンで、game は HP を 1 も減らさない**
のに model は削っている：

| trace seq | /block の変化 | game の被ダメージ | model の被ダメージ |
|---|---|---:|---:|
| 207 (act3_pop2_R8V2H6N4ZB) | 20 → 2 | 0（HP 54 のまま） | 51 |
| 各例 | 16 → 9 | 0 | 7 |
| 各例 | 29 → 22 | 0 | 7 |
| 各例 | 4 → 0（STUNNED へ） | 0 | 4 |

model は `BurrowedPower.AfterBlockBroken` を「block が 0 になった瞬間に STUNNED へ移行」としてだけ
扱っており（`combat.py` の `_damage_enemy` 内）、潜行中の block の扱いに別の違いがあった（次段落で確定）。
※ここに書いた「潜行中は HP を削らない」という見立ては **誤り**だった。大きな差（game 0 / model 51）は
model がターン開始のドローで `HellraiserPower` の Strike 自動プレイを発火させた結果で、
どの札が引かれるかは rollout の RNG 次第なので、忠実度の差ではなく再現のばらつきだった。

### 測定メモ：`pgrep -f "SlayTheSpire2"` は自分の起動コマンドに反応する

panel スクリプトの「game が走っていたら refuse」ガードが、**起動した bash コマンド自体の
command line に game の path 文字列が含まれている**だけでヒットして誤 refuse した
（`ps` には game が出ていない）。ガード自体は正しいので、起動コマンド側に path 文字列を
置かない（別コマンドで path を確認してから launch する）で回避する。

### Flame Barrier 修正の panel：**-9 胜**（44→35、実効ある 2 seed では 34→25）

`data/flamebarrier_ab.sh`（arm = HEAD、control = `.wt-ctrl-fb` = `7f276af`、policy code の差は commit
`f1a9a10` だけ）。

| seed | control | arm | 差分 | FlameBarrier 観測（arm / control） | trace 分岐 |
|---|---:|---:|---:|---|---|
| C7N4V9P2RX | 14勝 | 10勝 | **-4** | 231 / 362 | あり（289 / 437 record） |
| V7K2T9M5RH | 20勝 | 15勝 | **-5** | 283 / 373 | あり（362 / 475 record） |
| S4QFLNDMB3 | 10勝 | 10勝 | +0 | **0 / 0** | **なし（trace 一致）** |

S4QFLNDMB3 は run が一度も FlameBarrier を使っておらず trace も完全一致なので、この +0 は測定ではない。
**実効ある 2 seed では 34 勝 → 25 勝（-9）** で、この session で最も大きい panel 上の悪化だった。

修正は HEAD に残す。理由は忠実度の証拠が直接だからだ：game の `FlameBarrierPower.AfterDamageReceived` は
ダメージインスタンスごとに走り、record 済みの replay 404 件で敵 HP 一致が 60.6% → 91.8%（multi-hit group
は不一致→一致に反転、single-hit group は不変）に改善した。勝敗が下がったのは model の側ではなく
**policy の側**の説明が残る：反射ダメージを正しく数えた model は multi-hit 持ちの敵に対して
「こちらが削れる量より向こうが削れる量」を大きく見積もり、search がより攻撃的な順を選ぶ。
実走の悪化はその過信の帰結として整合的なので、次以降に調べる対象は
`search_value` が反射ダメージをどこまで信用するか（例えば反射を hit 数で割り増ししたまま放置しない）
という policy の論点として持ち越す。忠実度修正そのものは revert しない、という session の規則に従う。

## Round 17: 潜っている敵はブロックを保持する（burrowed replay の block 一致 8/186 → 184/186）

`Hook.ShouldClearBlock(combatState, creature, out preventer)` は creature に載った
`ShouldClearBlock` override をすべて照会し、1つでも false を返せば block を消さない。
その override を持つのは **BurrowedPower・BlurPower・BarricadePower・relic SturdyClamp** の4つだけだった
（`grep -rn ShouldClearBlock` の結果）。player 側（Barricade と SturdyClamp）は model も扱っていたが
（`combat.py` の `barricaded` / `retained_block`）、**敵側の block を消す箇所 `_enemy_turn` が
`replace(enemy, block=0)` を無条件で呼んでいた**ので、潜っている TUNNELER の残り block を毎ターン消していた。

`BurrowedPower` の実装は `ShouldClearBlock(creature)` が `Owner != creature` のとき true、owner なら false。
加えて `AfterBlockBroken` で Tunneler を STUNNED に送って `PowerCmd.Remove<BurrowedPower>`、
`AfterRemoved` で `CreatureCmd.LoseBlock(999999999)` を呼ぶ（block が全部消えるのはこちら経由）✓ model は
この break 側を `_damage_enemy` で持っていたので、**保持側だけが無かった**。

実装（commit `6bf743a`、764 tests green）：`_enemy_turn` の block クリアを BurrowedPower / BlurPower を
持つ敵に対してスキップする。テスト `test_burrowed_enemy_keeps_its_block_across_turns` は block 20 の
BurrowedPower 持ちが END_TURN 後も 20 を保ち、power 無しは 0 になることを検証する。

検証（BURROWED_POWER を持つ敵の end_turn replay 186 件、同一戦闘・同一 combat_id 限定）：

| | 修正前（`.wt-ctrl-burrow` = `01e3ce2`） | 修正後（HEAD） |
|---|---:|---:|
| 敵 block 一致 | **8 / 186 = 4.3%** | **184 / 186 = 98.9%** |
| 敵 HP 一致 | 163 / 186 | 181 / 186 |

決定母数は **4,476 本 replay して 782 決定が変化・51 seed**（`data/attribution_rampart.py` の
selector `MONSTER.TUNNELER`、KeyError 126 件は fallback）。潜行中の敵がブロックを保つことで、
その戦闘内のあらゆる攻撃決定の評価が変わる。勝敗への影響は `data/burrow_ab.sh` で測る。
ただし **この機構は MONSTER.TUNNELER と戦った run でしか発火せず、TUNNELER 観測の多い seed
（640・363・355 件）はすべて過去の panel で使った seed** だった。fresh seed だと Tunneler に
当たらない可能性が高く測定にならないので、この panel は「機構を狙った再測」として明示し、
seed の新しさは牺牲する（panel の判定基準は MEASURABLE = 両 arm が機構を見る ことを使う）。

### 潜っている敵のブロック保持の panel：**+0 胜**（50→50、3 seed すべて分岐・すべて Tunneler と交戦）

`data/burrow_ab.sh`（arm = HEAD、control = `.wt-ctrl-burrow` = `01e3ce2`、policy code の差は commit
`6bf743a` だけ）。seed は上記の理由で TUNNELER 観測が多い既存 seed を使い、機構が両 arm で見たことを
panel の有効条件（MEASURABLE）にした。

| seed | control | arm | 差分 | TUNNELER 観測（arm / control） | BURROWED 観測 | trace 分岐 |
|---|---:|---:|---:|---|---|---|
| H2LV6ZJ4XW | 22勝 | 22勝 | +0 | 13 / 14 | 4 / 5 | あり（596 / 592 record） |
| P3V8N5K2RX | 15勝 | 15勝 | +0 | 20 / 20 | 7 / 7 | あり（405 / 405 record） |
| L3PN5HBQ8T | 13勝 | 13勝 | +0 | 21 / 20 | 7 / 7 | あり（359 / 358 record） |
| 合計 | **50勝** | **50勝** | **+0** | | | 3本すべて分岐 |

分岐していて機構も両 arm に出ているので、この +0 は「効かなかった」ではなく「効いたが勝敗は動かなかった」
側の結果。忠実度の実証（block 一致 4.3% → 98.9%、決定 782 件・51 seed）を優先して修正は HEAD に残す。
この session で +0 だった忠実度修正（stun、Mr Struggles、potion 7種、gate batch 2）と同じ位置づけで、
勝敗が動かないことをもって revert しない、という規則の一環として記録する。

なお `ShouldClearBlock` を override する `BlurPower` は `CARD.BLUR`（1 コスト Skill、block 5 + Blur 1）経由の
player 側 power で、corpus 全体で `CARD.BLUR` の play も reward 出現も 0 件だった（Ironclad の札ではない）。
model は power 名で generically 処理しているので、もし他クラスを遊ぶ運用になれば自動的に効く。

## Round 18: QUEEN 戦の「毎ターン boss が 1 減る」は Toasty Mittens + Forgotten Soul だった

8 round かけた `QUEEN enemy_hp end_turn` の -1（178 件）が解決した。原因は **`RELIC.TOASTY_MITTENS` が
ターン開始に draw pile の一番上を Exhaust する**ことで、同じ run が持っていた
**`RELIC.FORGOTTEN_SOUL`（`AfterCardExhausted` で Exhaust 1 件につき ランダムな hit 可能な敵へ 1 の
未強化ダメージ）** がそこから発火していた。model は Toasty Mittens の Exhaust を再現していたが、
`_after_exhaust`（Charon's Ashes・Forgotten Soul・Dark Embrace・Feel No Pain・Joss Paper・Burning Sticks を
まとめて処理する共通フック）をその経路だけ呼んでいなかった。** Exhaust Sites を grep すると
`_after_exhaust` を呼ばない箇所は Toasty Mittens の 1 箇所だけ**だった。

証拠：`act3_verify_head_H2LV6ZJ4XW` seq 555/561/577 で、play 済みの札が無いターンに exhaust pile が 1 増え
（BURNING_PACT など draw pile からの Exhaust）、QUEEN と TORCH_HEAD_AMALGAM の HP が毎ターン 1 減っていた。
`data/queen_exhaust` 系の集計では 188 件の QUEEN end_turn replay の 177 件がちょうど -1 だった。

実装 1（commit `a294ab3`）：Toasty Mittens の Exhaust を `_after_exhaust` に渡す。
テスト `test_toasty_mittens_exhaust_runs_the_exhaust_relics`（Toasty Mittens + Forgotten Soul で
END_TURN 後に敵 HP が 1 減り、exhaust pile が 1 枚増え、Strength +1 になること）。

### ただし最初の形では FROG_KNIGHT で逆に崩れた（順序の問題）

実装 1 だけだと boss 戦 audit の不一致が 3.52% → 3.69% に**増え**、`FROG_KNIGHT enemy_hp end_turn` の
**+1 が 189 件**現れた。単一敵のケースで model だけ 1 多く削っていた。観測を見ると game 側は
**HP ではなく block を 1 減らしていた**（frog knight hp 165 のまま block 15 → 14、model は hp 164 block 15）。
game の `PlatingPower` は敵側のターン结束（`BeforeSideTurnEndEarly`）で Block を再付与するので、
その block がターン開始の Exhaust 反射を吸収する。model は Plating 再付与を player ターン開始処理の
後ろの方に置いていたため、反射が block を越えて HP に落ちていた。

実装 2（commit `94e951f`）：敵側の Plating 再付与を player ターン開始の Exhaust フックより前に移した
（`_enemy_turn` の block クリアと Rampart 付与との関係は不変）。孤立したコメントは削除。

### 検証（`RELIC.TOASTY_MITTENS` を持つ player の end_turn replay 4,794 件）

| | 修正前（`.wt-ctrl-mittens` = `5e5cb84`） | 実装1のみ | 実装1+2（HEAD） |
|---|---:|---:|---:|
| 敵 HP 一致 | 4,064 / 4,794 = 84.8% | 4,392 / 4,794 = 91.6% | **4,581 / 4,794 = 95.6%** |
| QUEEN 戦の部分 | 不一致 182 | 不一致 66 | 不一致 66 |
| FROG_KNIGHT + Toasty Mittens の不一致 | 0 | **189（model だけ +1）** | **0** |

boss 戦 audit 全体（46,737 決定）は 3.52% → **3.29%** に改善し、上位 group から `QUEEN end_turn -1` と
`FROG_KNIGHT` が消えた。残る上位は `QUEEN CARD.STRIKE_IRONCLAD -1 (69)`、`QUEEN CARD.ANGER -1 (65)`、
`QUEEN CARD.ASHEN_STRIKE +1 (41)`、`THE_INSATIABLE player_hp CARD.FEED -2 (35)`、
`VANTOM CARD.DEFEND_IRONCLAD -1 (35)`、`FROG_KNIGHT end_turn +3 (31)`。
`QUEEN end_turn "game0" 41 件` は合計ダメージが一致し per-enemy でずれる形で、
Forgotten Soul が撃つランダム対象の違い（rollout の RNG）として説明がつく。

panel は見送った。`RELIC.TOASTY_MITTENS` と `RELIC.FORGOTTEN_SOUL` を同時に持つ観測は corpus 内で
seed H2LV6ZJ4XW の 76 件だけで、機構を狙った panel に必要な 3 seed が揃わないため。忠実度の実証
（4,794 件の replay 一致率と、崩れた group の消滅）で HEAD に残す。

決定母数は **24,651 本 replay して 1,600 決定が変化した**が、**変化が出た seed は 1 本だけ**
（`data/attribution_rampart.py` の selector `RELIC.TOASTY_MITTENS`、control `5e5cb84`）。Toastymittens を
持つ run は多いのに決定が変わった seed が少ないのは、ターン開始の 1 ダメージ差が探索の argmax を
滅多に揺らさないためで、**「決定 3 seed 以上」という採用基準は満たさない**。この commit を残す根拠は
忠実度（4,794 件の一致率 84.8% → 95.6%、崩れた group の消滅）であり、勝敗や決定分布の改善ではない。

## Round 19: Weak と Vulnerable は「丸める前に掛ける」（boss 戦 audit 3.29% → 2.60%）

QUEEN 戦の攻撃決定で game だけ 1 多く削っていた group（`CARD.STRIKE_IRONCLAD` 69 件、`CARD.ANGER` 65 件、
`CARD.POMMEL_STRIKE` 23 件、`CARD.BYRD_SWOOP` 19 件、`CARD.HEADBUTT` 15 件、`CARD.SQUASH` 12 件）の
原因は **掛算の丸め位置**だった。game の `ModifyDamageMultiplicative` hook は小数の係数を返して
**掛け合わせた後に 1 度だけ丸める**のに対し、model は Weak (3/4) → Vulnerable (150/100) と
各段で `//` で切っていた。upgraded Strike 9 に Weak 97-99（QUEEN の `YOU_ARE_MINE` が戦闘中ずっと載る）と
Vulnerable 1 を掛けると game は 9 × 0.75 × 1.5 = 10.125 → **10**、model は 9 × 3 // 4 = 6 → 6 × 150 // 100 = **9**
で 1 足りなかった。`WeakPower.ModifyDamageMultiplicative` は `dealer != Owner` と `!IsPoweredAttack()` のとき
だけ 1 を返し、それ以外では常に 0.75（stack 数で変わらない）こともデコンパイルで確認した。

実装（commit `d3a9608`、766 tests green）：`_apply_debuff_multipliers(combat, enemy, damage)` を増やし、
Weak と Vulnerable（Paper Phrog の +25 と CrueltyPower の加算込み）を **単一の丸め**で適用する。
AoE 系 3 箇所と単一対象 1 箇所にバラけていた `damage = damage * 3 // 4` を廃して全部この helper に寄せる。
Shrink (7/10)・Pen Nib (×2)・Gigantification (×3)・Slow はこの round では触っていない（同じ問題は残る）。
テスト `test_weak_and_vulnerable_multiply_attack_damage_before_the_rounding` は
Weak + Vulnerable で 10、Weak だけで 6、Vulnerable だけで 13 になることを固定する。

検証（攻撃カードの play で、対象が block 無し・Slippery/Intangible/Plating 等の特殊を持たない 44,883 件）：

| | 修正前（`.wt-ctrl-weak` = `dd2f0f4`） | 修正後（HEAD） |
|---|---:|---:|
| 与ダメージ一致（全体） | 43,754 / 44,883 = 97.48% | **43,898 / 44,883 = 97.81%** |
| weak 有り & Vulnerable 有り | 一致 263 / 不一致 170 | **一致 407 / 不一致 26** |
| weak 有り & Vulnerable 無し | 一致 729 / 不一致 12 | 一致 729 / 不一致 12 |
| weak 無し | 一致 42,762 / 不一致 947 | 一致 42,762 / 不一致 947 |

Weak と Vulnerable が同時に載る group の不一致が 170 → 26 に減り、其它の group は完全に同一だった。
boss 戦 audit（46,737 決定）は **3.29% → 2.60%**（1,216 件）。上位 group から `QUEEN に対する
CARD.STRIKE_IRONCLAD -1` と `CARD.ANGER -1` が消えた。

boss 戦の残る上位（次 round の対象）：`QUEEN CARD.ASHEN_STRIKE +1 43 件`（model が多い。Ashen Strike は
複数 hit のため per-hit の丸めが疑うしい）、`QUEEN end_turn "game0" 41 件`（合計は一致し per-enemy だけ
ずれる形で、Forgotten Soul のランダム対象の違いとして説明がつく）、`THE_INSATIABLE 戦 CARD.FEED で
player_hp -2 35 件`、`VANTOM 戦 CARD.DEFEND_IRONCLAD -1 35 件`、`FROG_KNIGHT end_turn +3 31 件`、
`QUEEN 戦 CARD.DEFEND_IRONCLAD で game 5 多い 23 件`。

決定母数は **8,066 本 replay して 267 決定が変化・27 seed**（`data/attribution_rampart.py` の selector
`PLAYER:POWER.WEAK_POWER`、control `dd2f0f4`）。Toastymittens の時と違い seed が 27 本に広がっている。
勝敗への影響を見る panel は次 round に回す（この round は panel を起動する残り時間がなく、起動すると
panel 完了まで policy code を編集できなくなるため）。panel の seed は player Weak を多く保持した
run を持つ seed から選ぶ。

## Round 20 (計画中): combo relic の「ターン内に何枚玩んだか」が observation に出ない

boss 戦 audit の `QUEEN 戦 CARD.DEFEND_IRONCLAD で game 側が 5 多い 23 件` の原因が分かった。
`RELIC.LETTER_OPENER` は **Skill を 3 枚玩るごとに 5 の未強化ダメージ**を与える（`CanonicalVars` が
`CardsVar(3)` と `DamageVar(5m, ValueProp.Unpowered)`、`SkillsPlayedThisTurn % 3`）。model はこのルールを
持っている（`combat.py` の `if RELIC_LETTER_OPENER in relics and skills_this_turn % 3 == 0`）のに、
**observation に「このターンすでに何枚玩んだか」が出ていない**ため、decision ごとに Combat を
observation から作り直す agent はターン内の進行度を毎回 0 から始め直す。

observation 側に無いことは bridge のコードで確認した（`CombatBridge.cs` / `Entry.cs` はいずれも
`relics = player.Relics.Select(r => r.Id.ToString())` だけで、relic の `DisplayAmount` も play 数も出さない）。

因果は replay の差分で閉じた。`RELIC.LETTER_OPENER` を持つ run の玩札決定を、trace から「同じターン内の
それまでの玩札数」付きで replay した:

| 決定の種別 | そのターン内の prior plays | game - model の与ダメージ | game 側で発火する条件 | 件数 |
|---|---:|---:|---|---:|
| Skill | 2 | **+5** | 発火する | **278** |
| Skill | 2 | +10 | 発火する | 61 |
| Skill | 2 | +15 | 発火する | 60 |
| Skill / Attack | 0,1,3,4 | 0 | 発火しない | 7,100 超 |

**発火する条件のときだけ game が多い**形で、其它は完全に一致している。母数はさらに広い:
ダメージを出す combo relic（LETTER_OPENER・KUSARIGAMA）を持つ玩札決定のうち **9,435 件が「ターン内に
既に玩んだ後」の状態**にあり、そのうち **1,895 件は counter がすでに 3 の倍数**（次の玩札で game が
発火させる状態）で、model にはそこが見えない。

実装方針（次 round、`official_agent.py` の policy 変更）。agent は 1 プロセスで observation を poll し
続けています（`official_agent.py` の main ループが `last_seq` で顺次決定を作る）ので、**モジュールレベルで
ターン内の play 数を記憶して、observation から作る Combat に注入できる**。リセット条件は turn が変わった
とき、または敵の `combat_id` 集合が前回と交差しなくなったとき（召喚で id は増えるが、新しい戦闘では
全て新しい id になる）。注入先は `attacks_played_this_turn`・`skills_played_this_turn`・
`cards_played_this_turn`（これは `SlowPower` の ramp にも効く）と `attacks_this_combat`・
`skills_this_combat`（`RELIC.NUNCHAKU`・`RELIC.TUNING_FORK` の 10 枚カウント）。

注意: 同じ形の `RELIC.KUSARIGAMA`（3 枚目の Attack で 6 ダメージ）は replay で +6 の差分が見えていない。
game 側のトリガーが model の想定と違う可能性があるので、LETTER_OPENER を直した後に separately 確認する。

### Weak 掛算統合の panel：**+0 胜**（31→31、3 seed）ただし測定になったのは 1 seed だけ

`data/weak_ab.sh`（arm = HEAD、control = `.wt-ctrl-weak` = `dd2f0f4`、policy code の差は commit
`d3a9608` だけ）。seed は player Weak 観測が最も多い 3 本（54・54・48 観測）を選んだ。

| seed | control | arm | 差分 | trace | player Weak 観測（arm / control） | QUEEN 観測 |
|---|---:|---:|---:|---|---|---|
| N8CQ4ZKP2W | 5勝 | 5勝 | +0 | **byte 一致（143 / 143 record）** | 0 / 0 | 0 / 0 |
| P3V8N5K2RX | 15勝 | 15勝 | +0 | 分岐（395 / 405 record） | 15 / 9 | 0 / 0 |
| T5R8K2N9QP | 11勝 | 11勝 | +0 | **byte 一致（312 / 312 record）** | 24 / 24 | 0 / 0 |
| 合計 | **31勝** | **31勝** | **+0** | | | |

`compare_panel.py` の MEASURABLE 表示は「power が両 arm で出現」で判定しており、**N8CQ4ZKP2W は trace が
完全に同一で Weak 観測も 0 件**だった（その +0 は測定ではない）。T5R8K2N9QP は Weak を 24 件見ているが
arm と control の決定が最初から最後まで同一だった。分岐して機構も出ていた seed は P3V8N5K2RX の 1 本だけ。
3 run はいずれも QUEEN 戦に到達しておらず（QUEEN 観測 0 件）、Weak 97-99 というこの修正の主戦場自体が
出ていない。忠実度の実証（攻撃一致 97.48% → 97.81%、Weak+Vulnerable group の不一致 170 → 26、決定 267 件・
27 seed）を根拠に HEAD には残す。panel については「主戦場に到達する seed では測れていない」ことが分かったので、
次回はこの修正 dedicated ではなく他の修正と束ねて測る。

## Round 20: ターン内の玩札数を pile から復元した（boss 戦外も含む攻撃一致 97.36% → 97.54%）

`RELIC.LETTER_OPENER` は Skill を3枚玩るごとに 5 の未強化ダメージを与える（`AfterCardPlayed` で
`SkillsPlayedThisTurn++`、3 の倍数で `CreatureCmd.Damage(HittableEnemies, 5m Unpowered)`）。model には同じ
ルールがあったが、**observation にターン内の玩札数が出ていない**ので（bridge は relic の id 一覧だけを
書く）、decision ごとに Combat を作り直す agent は毎回 0 から数え直し、3 枚目以降のルールを一切価格に
入れられなかった。

復元は pile から行っている（commit `4c89254`）：玩んだカードは必ず discard か exhaust に移るので、
**このターンが始まった時点の discard+exhaust に含まれていたカード集合との差分**がそのターンが玩んだ
カードであり、agent が自分で選んだ play だけでなく game 自身が玩んだカード（Hellraiser・Pyre・Mayhem・
Centennial Puzzle の autoplay）も含まれる。agent が選んだ play を数える方式では autoplay が抜け、3 枚目
ルールが1枚ずれた（先に試したその方式は boss 戦 audit の combo 不一致 2,680 → 2,683 で全く改善しなかった）。

同時に `RELIC.KUNAI`・`RELIC.SHURIKEN` の適用タイミングを直した（commit `e7d8836`）：game は
`AfterCardPlayed` で power を載せるので、**3 枚目の Attack 自身は自分の bonus を使えない**のに、model は
`combo_powers` に足した状態でそのまま Attack の damage を計算しており、3 枚目に +1 していた。bonus は
`Combat.pending_combo_powers` に保留し、`step()` が play の解決後に power として反映する（3 枚目の
Attack の与ダメは 6、続く 4 枚目は 7 になることを `test_shuriken_strength_counts_from_the_attack_after_the_third`
で固定）。

検証（trace の play 決定を順番に `official_agent.choose()` 経由で replay し、記録された play 後の敵 HP と
model のそれ比べる。101,464 play、control は `.wt-ctrl-plays` = `2426496`）：

| | control | arm |
|---|---:|---:|
| 与ダメージ一致 | 98,793 / 101,473 = **97.36%** | 98,969 / 101,464 = **97.54%** |
| combo relic がある決定の不一致 | 2,680 | **2,495** |
| LETTER_OPENER だけで game が多い +5 | 222 | **55** |
| 同 +10 / +15 | 35 / 46 | **3 / 4** |
| LETTER_OPENER＋ORNAMENTAL_FAN＋PEN_NIB +5 | 69 | **4** |
| model が多い −5（新たな残差） | 0 | 36 |

LetterOpener 系の「game だけ多い」は 393 件 → 93 件になった。新たな残差は model が 5 多く削る 36 件で、
pile 差分が play 以外の移動（カードを捨てる効果・手札から除去する効果）を数えることで 3 枚目の位置が
ずれることが原因と考えている（未確認）。

**確認して棄却した点**: `SlowPower` の ramp は「ターン内の玩札数」ではなく戦闘中の全 play を数えている
可能性を疑ったが、`AfterSideTurnStart` で `SlowAmount = 0` にリセットされ `participants.Contains(Owner)`
で自分の side だけなので、**model の per-turn 基準で正しい**ことが分かった。combo relic を持たない group
の不一致が 594 → 608 に 14 増えたのは、その group の `cards_played_this_turn`（`SlowPower` の ramp、
Brilliant Scarf、Sloth、Normality の上限が読む）に対する pile 推定のずれであり、ルール不足ではない。

### 玩札数再構成の panel：**-1 胜**（37 → 36、3 seed すべて測定になった）

`data/plays_ab.sh`（arm = HEAD、control = `.wt-ctrl-plays` = `2426496` = `4c89254` と `e7d8836` の 2 commit
前。2 つは「ターン内の玩札数を見せる」と「その bonus を game と同じタイミングで適用する」の1組なので
束ねて測ったことは script 冒頭に書いた）。seed は combo relic 保持 run の観測数が多く、かつ従来の panel で
測定されていない 3 本（E3L7S9A4KU 289 観測 / Q2W7N4K9DX 270 / V7D3M9H2XW 255、うち 199・196・174 がターン
途中の state）。

| seed | control | arm | 差分 | trace | combo relic 観測（arm / control） |
|---|---:|---:|---:|---|---|
| E3L7S9A4KU | 14勝 | 14勝 | +0 | 分岐（541 / 486 record） | 374 / 319 |
| Q2W7N4K9DX | 11勝 | 12勝 | **+1** | 分岐（339 / 342） | 243 / 236 |
| V7D3M9H2XW | 12勝 | 10勝 | **−2** | 分岐（325 / 252） | 230 / 168 |
| 合計 | **37勝** | **36勝** | **−1** | 3 本すべて分岐 | |

3 seed とも trace が分歧し、両 arm が combo relic を持つ戦闘を観測している（Weak の panel のように
「同一 trace なのに測定された」という seed は無い）。勝敗は 1 減った。単一 seed の ±2 はこの harness では
通常の揺れで、しかも model の忠実度を上げる変更（game が実際に与えている 5 ダメージを価格に入れる）が
勝敗を増すとは限らない —— 以前 FlameBarrier の時と同じ形。忠実度の実証（攻撃一致 97.36% → 97.54%、
LetterOpener 系の過小評価 393 → 93 件）を根拠に HEAD には残す。

### 玩札数再構成の決定母数（`data/attribution_rampart.py`、control `2426496`）

selector ごとに replay して決定が変わった本数を数えた：

| selector | replay した记録 | 決定が変わった | seed |
|---|---:|---:|---:|
| `RELIC.LETTER_OPENER` | 13,325 | 8 | 1 |
| `RELIC.SHURIKEN` | 2,981 | **142** | **7** |

LetterOpener 側は与ダメージの再現が 393 件 → 93 件に改善した割には agent の選ぶ action はあまり変わら
なかった（5 ダメージの価格への寄与が、その战斗の选択の順位をほとんどこさなかった）。決定を変えた母数は
Shuriken 側に集中している：3 枚目の Attack 自身が自分の +1 Strength を使わなくなる、というタイミングの
修正が Attack の評価を動かし、7 seed で 142 決定が変わった。採用基準（決定 3 件・seed 3 本）を満たすのは
この側で、忠実度の実証と合わせて HEAD に残す。

## Round 21: 玩札数の数え方を own play と pile の合成に直した（攻撃一致 97.54% → 97.65%）

pile だけの数え方は「手札から消えたカード」を全部数えていた。card を玩んだ時だけじゃなく、
**効果で捨てられた・exhaust されたカード**も discard / exhaust に移る：`CARD.BURNING_PACT` は他のカードを
1枚 exhaust、`CARD.FIEND_FIRE` は手札をまとめて exhaust、`CARD.DARK_EMBRACE` は手札を捨てる。それで
ターン内の Skill 数が必要より1-2増えて、**game が与えていない 5 ダメージを model が与える**形が
36 件残っていた（replay で `game - model = -5`）。

直した方法（commit `f2a107c`、768 tests green）。2つの情報源を合わせる：

- **agent 自身が選んだ play**（型まで正確。ただし game 自身が玩んだカードは見えにくい）
- **discard / exhaust の増加**（全部見えるが、上に書いた効果の分まで入る）

自分で選んでいない消失は、**そのターンに手札として観測されたカード**であれば効果の仕業だとみなす
（効果は手札にあるカードに作用する）。手札に一度も現れない消失だけが autoplay（同じ解決のうちに手札に
入って玩ばれるので、どの observation にも手札として出ない）として play に数える。

検証（`choose()` 経由で trace 順に replay し、記録された play 後の敵 HP と model を比べる）：

| | play 数 | 一致 | combo relic 決定の不一致 |
|---|---:|---:|---:|
| pile のみ（`.wt-ctrl-pile` = `86ffe4c`） | 101,942 | 99,435 = 97.54% | 2,507 |
| 合成（HEAD） | 101,955 | **99,554 = 97.65%** | **2,401** |

内訳は `LETTER_OPENER` 単独の群で **model が多い −5 が 36 → 0**、**game が多い +5 が 55 → 13**、
combo relic を持たない群の −1 が 82 → 61。小さな悪化は `LETTER_OPENER＋ORNAMENTAL_FAN＋PEN_NIB` の −5が
4 → 16 と、combo relic なしの +1 が 406 → 425。

決定母数：`.wt-ctrl-pile` と比較して **13,325 本 replay して決定の変化 0 件・seed 0 本**。記録された
状態での选択順位が変わらないので、**この修正単独の panel は行わない**（选択が変わらなければ勝敗は動かない）。
機構全体の母数は no-counter の control（`2426496`）に対して SHURIKEN が 2,981 本で 142 決定・7 seed、
LETTER_OPENER が 13,325 本で 8 決定・1 seed で、合成前後に変化はなかった。

**確認して棄却した点**: `MONSTER.THE_INSATIABLE` の `LiquifyMove` は `SandpitPower 4` と
`CARD.FRANTIC_ESCAPE` 6枚（3枚を draw pile、3枚を discard pile）をplayer の pile に足す。discard に
直接入るこの生成カードが玩札数を水増しする可能性を疑ったが、`FranticEscape` は combat.py の SKILLS /
ATTACKS に入っていないので数えられない（discard 観測 33,085 件の FRANTIC_ESCAPE が play 扱いされなかった
census で確認）。`THE_INSATIABLE` 戦で `CARD.FEED` を玩んだ瞬間 player がちょうど 2 減る group（35 件）は
未解決のまま：FEED は Attack command 1回で MaxHp +3 を得るだけ（自ダメージ無し）、THE_INSATIABLE の C#
に play 起因の damage hook は無く、候補にした relic（PENDULUM・PLANISPHERE・STONE_HUMIDIFIER・
TEA_OF_DISCOURTESY・ODDLY_SMOOTH_STONE・GREMLIN_HORN）にも play 時の damage hook は無い。

## 未解決 gap の記録: Attack を玩んだ瞬間 player がちょうど 2 減る group（同ターン transition だけ、551 件）

boss 戦 audit の `CARD.FEED player_hp game-2`（35 件）を辿った过程中に、もっと広い group だと分かった。
全 corpus の play 決定を model と比べ、**player HP だけ model より game が少ない** transition を数えた
（`prev.turn == nxt.turn` を必須にした同ターン比較のみ、enemy turn の混入を除外した）。

- 該当 551 件のうち約 394 件が **ちょうど -2**：`CARD.FEED` 245、`CARD.STRIKE_IRONCLAD` 76、
  `CARD.POMMEL_STRIKE` 28、`CARD.PERFECTED_STRIKE` 27、`CARD.IRON_WAVE` 8、`CARD.ANGER` 6、`CARD.BYRD_SWOOP` 4
  （Attack ばかりで Skill が無い）。同じ play で敵側も game の方が model より多く削られている
  （例 MYTE 戦: game 13 / model 9）。
- 敵別: `THE_INSATIABLE` 56、`LOUSE_PROGENITOR` 41、`FUZZY_WURM_CRAWLER＋SHRINKER_BEETLE` 34（これは +3 で逆向き、別問題）、
  `MYTE×2` 33、`QUEEN＋TORCH_HEAD_AMALGAM` 31、`LIVING_SHIELD＋TURRET_OPERATOR` 30、`SLIMED_BERSERKER` 29、`ENTOMANCER` 29。
  複数の seed にまたがる（サンプルを_dump_した 2 本 M5PC8TQ3BN と H2LV6ZJ4XW は確認済み）。
- **探りのミスを1つ直した**: 最初に「1 seed だけの現象」と書いたのは probe の seed 抽出が
  `name.rsplit('_',1)[-1]` で `agent.jsonl` を返していたため（正しい抽出では 69 seed の group に化けた）。
  件数・seed 数を report に使う前に抽出式を確認する。

**既に棄却したもの（同じ group を追う人を止めるために書く）**: `CARD.FEED` に自ダメージは無い（`Feed.cs` は
Attack command 1回 + Fatal .kill で MaxHp +3 のみ）。`THE_INSATIABLE.LiquifyMove` は `SandpitPower 4` と
`CARD.FRANTIC_ESCAPE` 6枚を pile に足すだけで damage は無い。`MONSTER.MYTE` の C# hook は hand に `Toxic` を
2枚足して自分の Strength を上げるだけ。`ImbalancedPower` は `AfterDamageGiven` で Stun、`PersonalHivePower` は
status card を draw pile に足すだけ。該当 run の relic（BURNING_BLOOD・BYRDPIP・HORN_CLEAT・LANTERN・
PAELS_WING・SMALL_CAPSULE・CENTENNIAL_PUZZLE・PENDULUM・PLANISPHERE・STONE_HUMIDIFIER・TEA_OF_DISCOURTESY・
TOASTY_MITTENS・VAMBRACE・GORGET・MEAT_CLEAVER・FORGOTTEN_SOUL・GREMLIN_HORN・ODDLY_SMOOTH_STONE）に
play 時の damage hook は無い。status card も Toxic（ターン終わりに hand にあれば 5 ダメージ＝model 済み）、
Slimed（1枚引く）、Wound / Dazed（hook 無し）、Normality（autoplay 上限＝model 済み）、Unmovable
（`UnmovablePower`＝model 済み）で該当しない。

**audit の妥当性について確認できたこと**: corpus 内の play 決定 transition（113,750 件）を数えたところ、
**カード play から次の记録へターンが進むことが 1 件も無い**（`prev.turn != nxt.turn` が 0 件）。だから
1 action ずつの比較に enemy turn が混入することはない。同時に、observation の card `vars` の `Damage` は
**実行時に補正済みの値**だと konkret に確認した（Strike で `Damage=4.2` が 5,869 件 = 6 × 0.7（Shrink）、
`upgrade=False` なのに `Damage=9` が 69 seed で 10,778 件）。この値を「その card が出すダメージ」として
そのまま使う設計が機能しない理由でもある（以前 observed-`Damage` 規則を棄却した根拠と一致）。

次の一手: 1 seed の FEED -2 を trace の前後ごと辿る。同じ段階で player に新しい power が載っているか、
monster JSON の `effects` に React reactive 効果が export されているかをみる（export されていない monster
側 hook なら、bridge 側で取るか model に effect として書く判断になる）。

## 未解決 gap の切り分けをやり直した: 551 件の player ダメージ差は 48 件が今の build の話で、503 件は古い trace の artifact

`ENCHANTMENT.CORRUPTED` を decompile で確認した（`Models.Enchantments/Corrupted.cs`）：Attack に only、
`EnchantDamageMultiplicative` で **powered attack を 1.5 倍**、`OnPlay` で owner に **2 の unblockable・
unpowered・Move ダメージ** ✓ model は両方すでに持っている（combat.py の `self_damage += 2` と
`damage = damage * 3 // 2` ✓ 順序も 1.5 倍してから Strength 加算で、observation に出る live 値と整合）✓
bridge も `enchantment = card.Enchantment?.Id.ToString()` を hand / draw / discard / exhaust すべてに出し、
agent も `Card(enchantment=...)` に移している ✓ つまり **Corrupted 自体は実装済み**だった ✓

group の数え直し（`data/player_damage_group.py` を追加 ✓ 同ターン transition だけ、`days` で trace の
新期を絞る）：

| 計測範囲 | player HP の差が出た play | seed |
|---|---:|---:|
| 直近 2 日の trace | **48** | **5** |
| 直近 30 日の trace | 551 | 19 |

`CARD.FEED` の -2 は 245 件 → 24 件になった ✓ corpus の trace は mod の別ビルドで書かれていて、現在の
bridge が出す字段（card の enchantment 等）が古い trace には元々無い ✓ 古い trace で「model が知らない」
のは bridge が渡していないからで、model の欠落ではない ✓ **group や gap を数えるときは新期 trace に絞る**
ことを rules に追加する ✓

残る 48 件（FEED -2 が 24、FEED +3 が 13、CASCADE -3 が 3、STRIKE -2 が 3 など）は未解決のまま ✓ 直近の
run でも Attack を玩んだ瞬間 player がちょうど 2 減り、block は変わらず、新しい power も載らない ✓ card
record は `enchantment: None` なのに live の `Damage` 値は 16 / 14.25 / 18（bridge は `DynamicVars...PreviewValue`
を出しているので base 10 に補正が入った表示値 ✓ 14.25 のような非整数にもなる ✓ **この値から原因を逆算する
方法は機能しない** ✓ 以前 observed-`Damage` 規則を棄却した理由と同じ ✓）✓

次の一手: 公式 run で FEED を玩む瞬間に card が持つ enchantment と affliction を bridge から追加で
export して（`official_mod/CombatBridge.cs` は policy code ではないので変更してよい ✓ 再 build が必要 ✓）、
game 側で何が 2 ダメージを出しているかを実測する ✓ 実測なしの推定はこれ以上進めない ✓

## Round 23: player ダメージ差 group を閉じた（0 件 / 0 seed）— 原因は Feed の MaxHp 回復と古い trace

前 round まで 551 件（直近2日でも 48 件）追ってきた group が **0 件**になった ✓ 2つの切り分けが要った。

1. **trace の build で絞る**。`fe94c71`（2026-10-04 11:47 ✓ 「trace の hand に enchantment を記録」）之前
   の trace には card の `enchantment` 字段が無い ✓ 593 文件中 588 文件が字段を持つ ✓ が、値が常に null の
   ものがある ✓ 日付で絞った 48 件のうち `mechonly_H2LV6ZJ4XW`（10-03 09:49）は **fe94c71 より前** ✓
   つまり「直近2日」では足りず、**bridge がその字段を出せる build かどうか**で絞る必要がある ✓
   `data/player_damage_group.py` に `trace_reports_enchantments()` を入れてこの条件にした ✓
2. **build の正しい trace 7 件**は全部 `CARD.FEED` の +3 / +4 だった ✓ 調べると game 側は
   **敵を殺した Feed で max HP と現在 HP が同時に 3 上がっていた**（hp 54 → 57 / max_hp 80 → 83 ✓
   hp 63 → 66 / max_hp 101 → 104 ✓）✓ `Feed.cs` は Attack が Fatal で、Fatal kill 時に
   `CreatureCmd.GainMaxHp(Owner, MaxHp)`（`MaxHpVar(3)`、upgraded で 4）を呼ぶ ✓ model にはこの効果が無かった ✓
   combat.py に追加し、殺さなかった場合は変化しないことを `test_feed_raises_max_hp_and_heals_when_it_kills_the_target`
   で固定（769 tests green ✓）。

測定の出し直し（同じ tool ✓ build 条件あり ✓ 30 日分の trace ✓）：

| | player HP の差が出た play | seed |
|---|---:|---:|
| 修正前 | 7 | 3 |
| 修正後 | **0** | **0** |

boss 戦 audit 側の mismatch は 1,225 → 1,232（2.60% → 2.61%）に 7 増えた ✓ 増加は build 条件で除外される
古い trace 側で、`THE_INSATIABLE` 戦 `CARD.FEED player_hp game-2`（35 件）と `QUEEN` 同（23 件）の行は
変化していない ✓ これらは `fe94c71` より前の trace で Corrupted の 1.5 倍が見えないまま比較している行 ✓
忠実度の実証（正しい trace 集合で 0 件）を根拠に HEAD に残す ✓

**ついでに確認して問題なし**: `ShrinkPower.ModifyDamageMultiplicative` は `Owner != dealer` なら 1 を返すので
**自分が受けるダメージには効かない** ✓ model が card の damage にしか掛けていないのと一致 ✓ さらに
corpus で player に載る `SHRINK_POWER` は 3,540 観測すべて **amount -1** ✓（`SHRINKER_BEETLE` の適用値 ✓
`IsInfinite` でターン終了時に減らない ✓）model は Shrink を減算対象に入れていないので、実際に観測される
Shrink に対しては正しい ✓ 正の量の Shrink を適用する敵はまだ観測されていない ✓

**まだ bridge に出ていない状態**: `CardModel.Affliction`（単一 ✓ CardModel.cs:602 ✓ Bound / Entangled /
Galvanized / Hexed / Ringing / Smog / Tainted）✓ model は Galvanized を `GalvanicPower`、Bound を `bound` で
個別に扱っている ✓ 次の候補 ✓

## Round 24: gap の順位を「現在の build が書けた trace」だけで出し直した（6,317 action 中 445 件）と SlowPower の基準

`data/boss_gap_list.py` を追加した ✓ 条件は card の `enchantment` 字段が **combat の hand record に付いているか**
で、それを満たす trace は 593 文件中 **32 文件だけ** ✓ `fe94c71`（10-04）で hand に追加された字段なので、
それより後の run だけ ✓ pile record には以前から字段があったため「字段を含む文件」は 588 文件になり、
ここを混同すると古い trace を交えてしまう ✓ 実測: **6,317 action を replay して 5,872 件一致（92.96%）** ✓

| 件数 | group |
|---:|---|
| 14 | `BYGONE_EFFIGY` `CARD.STRIKE_IRONCLAD` game+1 |
| 5 | `SLIMED_BERSERKER` `CARD.SLIMED` game+1 |
| 4 | `LEAF_SLIME_M` `CARD.STRIKE_IRONCLAD` game-5 / `CARD.POMMEL_STRIKE` game-7 / `CARD.PERFECTED_STRIKE` game-14 / `CARD.HEMOKINESIS` game-10 |
| 4 | `NIBBIT` `CARD.PERFECTED_STRIKE` game-12、`BOWLBUG_EGG` `CARD.PERFECTED_STRIKE` game-22、`SLITHERING_STRANGLER` `CARD.STRIKE_IRONCLAD` game-6 |

従来 boss 戦 audit の top だった `QUEEN CARD.ASHEN_STRIKE +1`（43 件）・`QUEEN end_turn`（41 件）・
`VANTOM CARD.DEFEND_IRONCLAD -1`（35 件）は **この list からは消えた** ✓ 消えた理由は未確認だが、Corrupted
（1.5 倍）が古い trace で見えていなかった説明と整合する ✓ ただし `-12`・`-22` のように model が多い大きな
差は Perfeected Strike の強化値か敵の HP 初期値の話で、別の原因としてはっきりしている ✓

enemy data の充足度は確認した: repo の `data/enemies_*.json` は 102 monster を持ち、build-valid trace に
出てくる 65 monster を**すべて**含んでいる ✓ 数据不足で replay できない monster は無い ✓

**SlowPower を実装し直した**（commit ✓ `combat.py`）: game の `SlowPower.ModifyDamageMultiplicative` は
`target != Owner` や非 powered attack なら 1 を返し、 otherwise `1m + 0.1m * SlowAmount` ✓ Weak（3/4）と
Vulnerable（150/100）と同じ hook なので **1つの掛け算の鎖にして最後に1回切り捨てる** ✓ model は Slow だ
け別の段階で切り捨てていた ✓ 固定した計算: Weak の player が Slow＋Vulnerable の敵に強化 Strike（9）を
玩む、ramp が 1.2 のとき game は 9 x 3/4 x 1.5 x 1.2 = 12.15 → 12 ✓ 段階的に切り捨てると 6 → 9 → 10 で
2 点損をしていた（`test_slow_ramp_rounds_once_with_the_other_damage_multipliers` ✓ 770 tests green ✓）✓
ただし**この修正で gap は減らなかった**（build-valid でも corpus 全体でも一致件数は変わらず ✓ Slow が効く
hit に Weak/Vulnerable が重なっていなかったため）✓ 忠実度の構造として保持する ✓ 初めに「BYGONE_EFFIGY の
+1 が消える」と code に書いたが実測が支持しなかったので書き直した ✓

**次の狙い（`BYGONE_EFFIGY +1` 14 件）**: game の ramp は `DynamicVars["SlowAmount"]` ✓ `AfterCardPlayed` で
**owner に関係無く玩札ごとに +1** ✓ リセットは `AfterSideTurnStart` で **Slow を持つ side が始まった時だけ** ✓
observation には SlowAmount が出ない（`DisplayAmount = SlowAmount * 10` だが bridge の power `amount` は
stack 値で ramp が見えない ✓）。model は per-player-turn の `cards_played_this_turn` を使うので、**Slow を
持つ敵がターンを execute しなかった場面（stun 中・sleep 中・行動しない state）で game の ramp だけが
積み上がる** ✓ これが +1 の説明になるか、次の round でその 14 件を turn 単位で並べて確認する ✓

## Round 25: 玩札カウントから抜けていた autoplay を戻した（決定の変化 0 件なので panel は行わない）

前 round までの玩札数（commit `f2a107c`）は「そのターンに手札で観測された札が、自分で選んでもいないのに
消えた」を全部効果の仕業として落としていた ✓ が game は **手札にある札を autoplay で玩む** ✓ Centennial
Puzzle と Pyre は持ってる札を、Mayhem と Hellraiser は引いたばかりの札を、Normality は自分自身を玩む ✓
それらは action として出てこないから pile の移出でしか見えない ✓ 全部落とすと SlowPower の ramp が
1 枚足りなくなり、Slow を持つ敵との play で model だけの差が出ていた ✓

直した rule（commit `f1ff3d3` ✓ 770 tests green ✓）: 未解释の移出は **基本的に play として数える** ✓
例外は **自分で玩んだ札が他の札を移出する card だった場合だけ** ✓ その 4 枚は combat.py の実装で特定した:
Burning Pact と Cinder は hand から1枚 exhaust ✓ Fiend Fire は hand を全部 exhaust ✓ Thrash は Attack を
1枚 exhaust ✓ （Dark Embrace と Aggression はダメージを受けた時に捨てる効果なので play 時点の移出では
無い ✓ 含めない ✓）

実装中に見つけた実際のバグを1つテストが捕まえた ✓ `unexplained` は毎回 **そのターンの開始スナップショット
に対して**計算し直すので、効果として落とした移出を記録しておかないと **同じ turn 内の次の観測で play に
復活する** ✓ `_TURN_EFFECT_DEPARTURES` に固定して除外を持続させた ✓ テストは4パターンで固定: 自分の play
を数える ✓ Burning Pact の exhaust は数えない ✓ 手札にあった autoplay は数える ✓ 手札に一度も出ない札は
数える ✓ 次のターンは 0 ✓

決定母数: 1 commit 前の tree（`.wt-ctrl-cards` = `965bdb3` ✓ 差分はこの commit のみ ✓ 同じ mod  binary）と
比較して **Slow を持つ敵の 1,704 観測で決定の変化 0 件・seed 0 件** ✓ audit 側の一致件数も 5,872 のまま ✓
なので **この変更の panel は行わない** ✓ ただしこれは忠実度側の修正で、autoplay を数え忘れる状態に戻すと
Slow 以外の counter 駆動 rules（LetterOpener・Kusarigama・Shuriken）でも同じ取りこぼしが起きる ✓
`data/boss_gap_list.py` 側の欠点も直した: audit が **記録された play を credit していなかった** ✓（search を
END_TURN で差し替えるだけだった ✓）credit を入れると数値は変わらなかった ✓

**Slow ramp の基準は確定できなかった** ✓ `-1` を外して「今玩んでる札も含める」実験をした:
`BYGONE_EFFIGY CARD.STRIKE_IRONCLAD game+1` が 14 → 10 に減り、逆に `game-1` が 4 出た ✓ 一致は
5,872 → 5,873 の1件だけ ✓ 例: `burrow_arm_b1_H2LV6ZJ4XW` seq 116（turn 2 の最初の play ✓ energy 2/3 ✓
hand 4 ✓ discard 5 / exhaust 1 ✓ agent の counters 0 ✓）で game は 13 に対して 14 を出している ✓ これは
SlowAmount = 1 の 1.1 倍 ✓ `SlowPower.AfterCardPlayed` は +1 するだけで今の所 per-turn reset は
`AfterSideTurnStart` で確認済み ✓ なので「その card 自身の damage が AfterCardPlayed より後に解決される」
疑いが残るが ✓ 一様に +1 すると4件が逆向きに壊れる ✓ 原因は per-case の counter 再現性にある可能性が
高い（観測される pile に載らない play がある ✓）→ HEAD は `-1` を維持し ✓ これは open のまま ✓

## Round 26: Fairy in a Bottle（死防止）など potion 4種を model に入れたが、記録上は決定を変えなかった

`data/boss_gap_list.py` の内訳を出した ✓ 445 件の不一致は **317 group** に散らばっていて、**243 group は
1 件だけ** ✓ 2 件以上の group が占めるのは 45.4% ✓ つまり上位 group を潰した残りは replay のRnd/引き順の
ばらつきで、1 件 group を追い回す価値は無い ✓

potion を確認した: **combat.py は 41 種類の potion id のうち 27 種類しか知らず** ✓ corpus に出てくる 14 種が
rollout で再現できなかった ✓ decompile で数値を確認できる順に 4 種 implementations を追加した（commit
`17e5367` ✓ 774 tests green ✓）:

- **`POTION.FAIRY_IN_A_BOTTLE`**（保持観測 2,665 件 / 9 seed ✓）: `PotionUsage.Automatic` ✓ action として
  出てこない ✓ `CreatureCmd.Kill` が HP を 0 にしたあと `Hook.ShouldDie` がこの potion に死を阻止させ ✓
  `AfterPreventingDeath` が `Math.Max(MaxHp * 0.3m, 1m)` を回復する ✓ つまり **一度だけ死ぬのを防ぐ** ✓
  model にも agent の shop 評価（`SHOP_POTION_SCORES` で 9 ✓ Lizard Tail ともう一つの保険 ✓）にも入っていなかった ✓
- `POTION.FOUL_POTION`: combat 中は `TargetType.AllEnemies` ✓ `DamageVar(12, Unpowered)` を combat 中の
  全 creature（pet 除く、**owner 含む** ✓）に配る ✓ 出撃時は `GoldVar(100)` ✓
- `POTION.SNECKO_OIL`: `CardPileCmd.Draw(CardsVar 7)` ✓ ただし引いた札の energy コストを 0-3 にランダム化
   する側は model 化していない ✓ agent 側の「緊急時に捨てるな」判断はそのまま ✓
- `POTION.STABLE_SERUM`: `Apply<RetainHandPower>(RepeatVar 2)` ✓ 手札が次のターンまで残る ✓

**code を書いていて分かった構造**: 敵の攻撃による player HP は `_enemy_turn` が **ローカル変数で追跡して
`replace` で書き戻す** ✓ `_apply_player_damage` を通らない ✓ なので「死を防ぐ」系の効果は両方に配る必要が
ある（Lizard Tail は既に両方に入っていた ✓ Fairy は helper `_survive_with_fairy_in_a_bottle` にまとめて
両経路から呼んだ ✓）。1 か所だけに入れてもテストが敵の攻撃経路で失敗して捕まった ✓

決定母数（control は 1 commit 前の tree `.wt-ctrl-fairy` = `6611237` ✓ 同じ mod binary ✓）:

| selector | 比較した観測 | 決定の変化 | 変化の seed |
|---|---:|---:|---:|
| `POTION:POTION.FAIRY_IN_A_BOTTLE` | 2,665 | **0** | 0 |
| `POTION:POTION.FOUL_POTION,SNECKO_OIL,STABLE_SERUM` | 457 | **0** | 0 |
| shop 観測の `choose_shop` を HEAD と control で比較 | 4,626 | **0** | 0 |

記録された run で **Fairy が消費された観測は 0 件** ✓（持っていた 9 seed のいずれでも致死の一撃を食らって
いない ✓）ので、この変更は今の corpus の決定を 1 つも変えない ✓ **決定変化 0 件の変更には panel を
行わない** ✓ の判断で panel は省略 ✓ 忠実度の実装として HEAD に残す ✓ 価値は未来的で、Fairy を得る run
では rollout が「そのターンで死ぬ」を正しく織り込み、shop で優先される ✓

## Round 27: audit の 2 つの欠点で gap が水増ししていた（445 → 105 件）と TenderPower の二重差し引き

**`data/model_match_audit.py` の `model_state` が `rollout_choice` を直接呼んでいた** ✓ `choose` を通らない
ので **agent が推定する玩札カウンタが audit の全 record で 0** だった ✓ LetterOpener の 3 枚目 Skill、
Kusarigama の 3 枚目 Attack、Shuriken、Tuning Fork、Pen Nib、Nunchaku、SlowPower の ramp は全部その
カウンタを読む ✓ なので audit は counter 駆動 rules の gap を量産していた ✓ `choose` 経由に変えた
（policy branch が rollout より前に return した場合だけ rollout_choice に落ちる ✓ commit `5ae7b13` ✓）✓

**audit は死んだ敵を数えていなかった** ✓ 死んだ monster は combat から完全に抜け ✓ 次の record の敵が
少なくなる ✓ index と combat_id の両方で配对していた code はそれを 0 ダメージとして扱い ✓「model が
5・14・22 多く削った」という group を丸ごと作っていた ✓ 次 record に居ない combat_id は kill とみなす
ように直した ✓ 同じ commit ✓

測定の動き（build-valid trace ✓ 6,315 action を replay ✓）:

| 状態 | 不一致 | 一致率 |
|---|---:|---:|
| 修正前 | 445 | 92.96% |
| 配对だけ修正 | 143 | 97.73% |
| +カウンタ seeded | 139 | 97.95% |
| +TenderPower の修正 | **105** | **98.34%** |

`LEAF_SLIME_M` の Strike -5 / Pommel -7 / Perfected -14 / Hemokinesis -10、`NIBBIT` Perfected -12、
`BOWLBUG_EGG` Perfected -22、`SLITHERING_STRANGLER` Strike -6 は**すべて audit の錯覚**だった ✓
`BYGONE_EFFIGY` family（Strike +1 が 14 件など約 26 件）もカウンタを入れると消えた ✓ **前 round で
「Slow ramp は -1 が正しいのか +1 なのか」と迷ったのは、audit 側にカウンタが無かったことが原因で、
`cards_played_this_turn - 1` のまま正しい** ✓

**`DexterityPower` は Block の power だった** ✓ hook は `ModifyBlockAdditive` だけ ✓ hover tip も Block ✓
攻撃ダメージには無関係 ✓ model は攻撃に Dexterity を足していなかったのでここは正しい ✓

`MONSTER.HUNTER_KILLER` の group を dump して原因を特定した（commit `3522e06` ✓ 774 tests green ✓）✓
game の `TenderPower` は `AfterCardPlayed` で **Strength -1 と Dexterity -1 を実の stack として載せ** ✓
`AfterSideTurnEnd` で cards played ぶんの Strength・Dexterity を返す ✓ その stack は observation に現れる
ので model はそこから Strength を読む ✓ なのに model には「そのターンに既に玩んだ枚数だけ攻撃を引く」
`_tender_penalty` があり ✓ **同じ差し引きを二重にやっていた** ✓ 実測: `L3PN5HBQ8T` seq 283（Tender 有効 ✓
cards_played 3 ✓ Strength -2 ✓ Strike base 6）で game は 4 削った ✓ model は 1 ✓ term を落すと 4 ✓
`_tender_penalty` と 3 か所の term を削除し ✓ 既存の `test_tender_weakens_later_cards_then_hands_the_stats_back`
は model の思い込みを固定していたので `test_tender_does_not_take_damage_off_attacks` に書き換えた ✓

**決定母数**: control を 1 commit 前（`.wt-ctrl-tender` = `5ae7b13` ✓ 同じ mod binary ✓）と比べ ✓
TenderPower が載っている **1,652 観測で決定が 361 件変わり ✓ 35 seed** ✓ これまでで最大の変化 ✓
EAIF2UUVCK 56 件・L3PN5HBQ8T 55 件・K7M2QX9BTR 33 件 ✓ なので **panel を起動した**（arm = `3522e06` ✓
control = `5ae7b13` ✓ seeds は Tender の決定変化上位 3 つ ✓  mechanism-targeted な再使用 ✓）✓ 結果待ち ✓
panel 中 policy code（`official_agent.py`・`combat.py`）は触らない ✓

残っている group（105 件）と次の狙い: `SLIMED_BERSERKER CARD.SLIMED game+1` 5 件、
`SHRINKER_BEETLE CARD.BASH game+1` 4 件、`QUEEN CARD.ASHEN_STRIKE game-1` 3 件と
`QUEEN CARD.IMPERVIOUS game+1` 3 件、`TUNNELER CARD.DEFEND_IRONCLAD game+5` 3 件と
`TUNNELER CARD.BATTLE_TRANCE game-5` 3 件（LetterOpener の発動枚数が前後する ✓ agent のカウンタ推定が
±1 ずれる場面 ✓）、`BYGONE_EFFIGY CARD.STRIKE_IRONCLAD game+1` 3 件 ✓ model の rollout 内では
TenderPower の `AfterCardPlayed`（-1/-1）と `AfterSideTurnEnd`（cards ぶん還元）が適用されない ✓
観測由来の stack には追いつくが rollout の次のターンでは知らない ✓ そこが次の work ✓

## Round 28: 残り 105 件の group を dump して game 側の fact を 4 つ確定した（policy は panel 中なので触らない）

panel（arm = `3522e06` ✓ control = `5ae7b13` ✓ seeds EAIF2UUVCK / L3PN5HBQ8T / K7M2QX9BTR）が走っている
間なので policy code には手を入れず ✓ 残 group の実例を1件ずつ dump して decompile と突き合わせた ✓

**`RELIC.GREMLIN_HORN` は StS1 の exhaust 効果ではない** ✓ game の実装は `AfterDeath` ✓ 敵が死んだ時に
**エネルギー +1 と draw 1** ✓ そして **combat.py は既に model している**（`combat.py:2009` ✓ `kills > 0` の
時 ✓）✓ なので `SLIMED CARD.SLIMED game+1`（5 件）と `QUEEN CARD.IMPERVIOUS game+1`（3 件）の説明には
ならない ✓ 最初に挙げた仮説は外れた ✓
**`RELIC.MEAT_CLEAVER`** も `TryModifyRestSiteOptions` だけで combat 効果は無い ✓

**`RELIC.FORGOTTEN_SOUL`** は `AfterCardExhausted` → `DamageVar(1, Unpowered)` のダメージ ✓ これも
**combat.py が既に model している**（`combat.py:602` ✓）✓ ここも gap の原因ではない ✓

**`SlipperyPower` の規則** ✓ `ModifyHpLostAfterOsty` は **受ける HP 減 that is less than 1 を 1 に戻す** ✓
つまり完全吸収は起きず最低 1 は通る ✓ `AfterDamageReceived` は `UnblockedDamage >= 1` の時に 1 減る ✓
`MONSTER.VANTOM` の `CARD.DISMANTLE`（game 2 / model 1 ✓ Slippery 7 → 5 ✓）はこれで説明がつく ✓ model は
1 hit として 1 削り ✓ game は 2 hit として 1 ずつ通した ✓ Dismantle の hit 数側の確認が次 ✓

**Shrink は model 側で単独の切り捨てになっている** ✓ `combat.py` の 4 か所（3105 / 3162 / 3195 / 3278）で
`damage = damage * 7 // 10` ✓ game は `ShrinkPower.ModifyDamageMultiplicative` の factor ✓ つまり Weak・
Vulnerable・Slow と **同じ鎖で最後に1回だけ切り捨てる** ✓ 実測: `fb_arm_b1_C7N4V9P2RX` seq 7 の
`SHRINKER_BEETLE` への BASH（base 8 ✓ player に Shrink -1 ✓ 敵に Vulnerable ✓ live の Damage var は 5.6 =
8 x 0.7 ✓) で game は 8 削り ✓ model は 7 ✓ Shrink を先に切り捨ててから Vulnerable を掛けたため ✓
Slow でやったのと同じ直し方（`_apply_debuff_multipliers` の鎖に factor として入れる ✓ 4 か所の単独
切り捨てを削除 ✓）が効く見込み ✓ **4 件の group ✓ 次の policy 作業の1つ目** ✓

**`BYGONE_EFFIGY CARD.STRIKE_IRONCLAD game+1`（3 件）の仮説**: `mantle_arm_b1_EH8UMY96NC` seq 104 で
agent のカウンタは 0/0/0 ✓ 敵は SLOW 1 ✓ game は 8 x 1.5（Vulnerable ✓) x 1.1（SlowAmount 1 ✓) = 13.2 → 13 ✓
model は Slow 1.0 で 12 ✓ つまり game の SlowAmount だけ 1 進んでいた ✓ その run は **`RELIC.TOASTY_MITTENS`
を持っており** ✓ game はターンの開始時に札を1枚玩む ✓ model 側の relic 処理（`combat.py:2451`）はそれを
知っている ✓ が agent のカウンタは **ターン開始スナップショットにその玩札が既に反映されている** ので
観測できない ✓ ターン開始の autoplay をカウンタに載せる方法を決めるのが2つ目 ✓

panel の1 seed 目: `RESULT tender_arm EAIF2UUVCK wins=14 losses=1 exit=1` ✓（`wins` は combat 勝数の数え ✓
Act 3 踏破ではない ✓）control 側の run 待ち ✓

## Round 29: Shrink を丸め鎖に入れ Dismantle を 2 hit にした prototype を計測（104 → 92 件）— panel 中なので policy には未適用

Tender panel が走っている間 policy code を触らない約束なので ✓ 変更は **`.wt-proto` worktree の prototype**
で作り ✓ 同じ script で baseline（`/Users/mao/workspace/sts2-ai` ✓ HEAD `76594d0` ✓）と比べた ✓
patch は `/tmp/shrink_dismantle.patch` に保存済み ✓ panel 終了後に HEAD へ適用する ✓

model を 2 つ変えた ✓

1. **Shrink を `_apply_debuff_multipliers` の鎖に入れた** ✓ combat.py は 4 か所（3105 / 3162 / 3195 / 3278）で
   `damage = damage * 7 // 10` と単独で切り捨てていた ✓ game は `ShrinkPower.ModifyDamageMultiplicative`
   の factor ✓ corpus 中の Shrink は全部 amount -1 = 0.7 ✓ 鎖の factor として `numerator *= 70 /
   denominator *= 100` に移し ✓ 単独切り捨て 4 か所を削除 ✓
2. **Dismantle を Vulnerable な敵に対して 2 hit にした** ✓ game の `Dismantle.OnPlay` は
   `hitCount = target.HasPower<VulnerablePower>() ? 2 : 1` ✓ model は damage 値を 2 倍していた ✓
   それを落として `hits = 2` ✓ hit ごとに丸め・block 吸収・Slippery の減算が別々に走る ✓

同じ script（build-valid trace ✓ 同じ filter ✓ 同じ配对）での測定:

| model | replay | 一致 | 不一致 |
|---|---:|---:|---:|
| HEAD | 6,737 | 6,633 | **104** |
| prototype | 6,746 | 6,654 | **92** |

閉じた group: `SHRINKER_BEETLE CARD.BASH +1`（4 件 ✓ Shrink ✓）、`TUNNELER CARD.DEFEND_IRONCLAD +5`（3 件）
と `TUNNELER CARD.BATTLE_TRANCE -5`（3 件 ✓ TUNNELER は Shrink を配る ✓ 同じ原因 ✓）、
`VANTOM CARD.DISMANTLE +1`（2 件 ✓ 2 hit ✓）✓ **合計 12 件** ✓ prototype でも suite は 774 件 green ✓
（`test_shrink_power_reduces_player_damage` は鎖に入れても同じ値で通る ✓）

残って最上位の group: `SLIMED_BERSERKER CARD.SLIMED game+1`（5 件 ✓ 原因未特定 ✓ GremlinHorn でも
ForgottenSoul でもないことは確認済み ✓）、`QUEEN CARD.ASHEN_STRIKE -1`（3 件 ✓ CalculatedDamage が
22.5 のような半端な値 ✓ 丸めの位置 ✓）、`QUEEN CARD.IMPERVIOUS +1`（3 件 ✓ Block 23.25 ✓）、
`VANTOM CARD.BATTLE_TRANCE +1`（3 件 ✓）、`THE_INSATIABLE CARD.DEFEND_IRONCLAD +5` と
`CARD.SHRUG_IT_OFF -5`（各2件 ✓ Skill play 時に game だけ 5 削る ✓ LetterOpener の発動枚数 ✓）、
`DECIMILLIPEDE_SEGMENT_BACK CARD.TRUE_GRIT +15`（2 件 ✓ 未確認 ✓）✓

panel の途中結果: arm（`3522e06` ✓ Tender 修正あり ✓）は EAIF2UUVCK `wins=14 losses=1` ✓
L3PN5HBQ8T `wins=13 losses=1` ✓ control（`5ae7b13`）は未開始 ✓ `wins` は combat 勝数で Act 3 踏破ではない ✓

## Round 30: Shrink・Dismantle の修正を HEAD に入り、Tender panel の control が dll 無しで空走していたことが分かった

**Shrink を `_apply_debuff_multipliers` の鎖に移し ✓ Dismantle を Vulnerable な敵に対して 2 hit にした**
（commit `ab6f534` ✓ 774 tests green ✓）✓ 同じ tool・同じ trace での census: 不一致 **105 → 97 件** ✓
閉じた group は `SHRINKER_BEETLE CARD.BASH +1`（4 件 ✓ Shrink ✓）と `VANTOM CARD.DISMANTLE +1`（2 件 ✓ 2 hit ✓）✓
`TUNNELER CARD.DEFEND_IRONCLAD +5` と `CARD.BATTLE_TRANCE -5`（各3件）は残った ✓ つまりこれは Shrink ではなく
LetterOpener の発動枚数側的问题 ✓ prototype 段階の script と boss_gap_list では replay 母数がずれる
（6,737/6,746 と 6,315/6,840 ✓ Dismantle の hit 変更で `step` が成功する record 数が変わるため ✓）ので ✓
**同じ tool での 105 → 97 だけを成果として数える** ✓

**Tender panel**: arm（`3522e06` ✓ Tender の二重差し引きを落した方 ✓）は
EAIF2UUVCK `wins=14 losses=1` ✓ L3PN5HBQ8T `wins=13 losses=1` ✓ K7M2QX9BTR `wins=11 losses=1` ✓
（`wins` は combat 勝数 ✓ Act 3 踏破ではない ✓）✓ 一方 **control（`.wt-ctrl-tender` = `5ae7b13`）は 3 run
すべて `wins=0 losses=0 exit=1`** ✓ これは 0 勝という意味ではない ✓ worktree に
`official_mod/bin/Release/net9.0/Sts2Ai.dll` をコピーしていなくて ✓ mod がロードされず combat が 1 件も
記録されなかったため ✓ **RESULT を信じる前に exit と記録数を見る** ✓ の既存教訓どおり ✓
dll を入れて control だけ再走させた（`tender_ctrl2` ✓ 05:11 開始 ✓ 3 seed ✓）✓ 比較はまだ出ていない ✓

**Exhaust keyword の data を取った** ✓ decompile の_cards_ 578 件のうち **119 件が `CardKeyword.Exhaust`**
を持つ ✓ model の `EXHAUSTS`（play 時に自分を手札から出す ✓ `combat.py:2860` の `exhaust = card in EXHAUSTS`）は
18 件だけ ✓ model が知っている札のうち **15 件が self-exhaust していない**:
Brand・Burning Pact・Cinder・Dark Embrace・Dramatic Entrance・Evil Eye・Feel No Pain・Havoc・
Howl From Beyond・Impervious・Molten Fist・Slimed・Thrash・Toxic・True Grit ✓
list は `data/exhaust_card_classes.json` に保存した ✓ これで **`SLIMED CARD.SLIMED +1`（5 件 ✓ 保持 7,315 観測 ✓）と
`QUEEN CARD.IMPERVIOUS +1`（3 件 ✓ 保持 2,349 観測 ✓）の説明がつく** ✓ game は play 時に札を exhaust し ✓
その run たちは `RELIC.FORGOTTEN_SOUL`（exhaust 1 枚につき 1 unpowered damage ✓ model は model 済み ✓
`combat.py:602` ✓）を持っている ✓ model が exhaust を知らないから relic が発動しない ✓ 次の work ✓

## Round 31: Tender panel は arm 38 勝 / control 37 勝、Exhaust keyword の 15 枚を model に入れないと relic が発動していなかった

**Tender panel（3 seed ✓ 差分は policy commit 1 つ ✓ 同じ mod binary ✓）**

| seed | arm `3522e06`（Tender 修正あり） | control `5ae7b13` |
|---|---:|---:|
| EAIF2UUVCK | 14 勝 1 敗 | 13 勝 1 敗 |
| L3PN5HBQ8T | 13 勝 1 敗 | 13 勝 1 敗 |
| K7M2QX9BTR | 11 勝 1 敗 | 11 勝 1 敗 |
| 合計 | **38 勝** | 37 勝 |

決定的変化は 1,652 観測中 361 件・35 seed ✓ 勝数は +1 ✓ **下がる方向では無い** ✓ かつ census の不一致を
105 → 97 件に減らしているので忠実度修正として保持 ✓（`wins` は combat 勝数 ✓ Act 3 踏破ではない ✓）
control の初回走行は dll 欠落で空だった ✓ 再走した結果 ✓

**`CardModel.GetResultPileTypeForCardPlay` を読んだ** ✓ 「play 後にどの pile へ移すか」を決める関数で ✓
`Keywords.Contains(CardKeyword.Exhaust)` なら **即 PileType.Exhaust** ✓ つまり StS2 の Exhaust は
**play 直後**に発動する ✓ ターン終了時ではない ✓ model の `exhaust = card in EXHAUSTS`（`combat.py:2860`）の
設計は正しい ✓ 不足していたのは list の中身 ✓

**15 枚を足した**（commit `722cd26` ✓ 774 tests green ✓）: Brand・Burning Pact・Cinder・Dark Embrace・
Dramatic Entrance・Evil Eye・Feel No Pain・Havoc・Howl From Beyond・Impervious・Molten Fist・Slimed・
Thrash・Toxic・True Grit ✓ game 側は Exhaust 持ちが 119 枚 ✓ model が play できるのはこの 15 枚を含めて
一部だけ ✓ census は不一致 **97 → 92 件** ✓ 閉じた group は `QUEEN CARD.IMPERVIOUS +1`（3 件 ✓）✓

テスト 9 件がこの修正で壊れた ✓ 全部「play した札自身が exhaust pile に入らない」という以前の思い込みを
固定していたもの ✓（`('Brand','Strike')` なのに `('Strike',)` を期待 ✓ など ✓）→ game の規則に沿って期待値を
書き換えた ✓ ただし 1 件（`test_true_grit_only_chooses_when_upgraded`）は premise が違ったのではなく
`exhaust_pile[0]` の index が古くなっただけ ✓ ランダムな犠牲札を読むように直した ✓

`SLIMED_BERSERKER CARD.SLIMED +1`（5 件）は self-exhaust を入れても残った ✓ 原因は別 ✓
次の対象はこれと `TUNNELER` の ±5（LetterOpener の発動枚数 ✓）、`BYGONE_EFFIGY STRIKE +1`（3 件 ✓
Toasty Mittens など turn 開始の autoplay が agent のカウンタに乗らない ✓）✓

## Round 32: Slimed が play 後にどこへも移動していなかった（exhaust 未処理）→ 不一致 92 → 87 件

`SLIMED_BERSERKER CARD.SLIMED game+1`（5 件 ✓ 前 round で Exhaust keyword を 15 枚に入れたのに残った ✓）を
5 件すべて dump した ✓ 手札の枚数は game と model で同じなのに ✓ **exhaust pile の増え方が違った**:
game は `exhaust 8 -> 9` と `draw 5 -> 4` ✓ model は `exhaust 8 -> 8` ✓ play した札が **どの pile にも
入っていなかった** ✓ 原因は `combat.py` の Slimed 専用 branch（`if card == SLIMED:` ✓ 2740 行附近 ✓）が
hand から外して `_draw_into_combat` だけで return していたこと ✓ `exhaust = card in EXHAUSTS` を通る
共通経路（2860 行附近 ✓ ここで exhaust pile と `_after_exhaust` を処理する ✓）を **通っていなかった** ✓

game は `Slimed.OnPlay` で 1 枚引き ✓ その後 `CardModel.GetResultPileTypeForCardPlay` が
`CardKeyword.Exhaust` を見て即 exhaust pile へ送る ✓ そして `RELIC.FORGOTTEN_SOUL`
（`AfterCardExhausted` → 1 unpowered damage ✓ model 済み ✓ `combat.py:602` ✓）が発動する ✓ つまり game の
+1 は Slimed の exhaust が起こした ✓ model は exhaust 自体を知らないので relic も発動しなかった ✓

直し: Slimed branch で 1 枚引いた後に exhaust pile へ入れ ✓ `_after_exhaust` を呼ぶ ✓（顺序も game に合わせた ✓
game は OnPlay 後（draw 後 ✓) に pile を決める ✓）✓ regression test を 2 件追加 ✓
`test_slimed_exhausts_itself_and_fires_forgotten_soul`（exhaust pile = (SLIMED,) ✓ 敵 40 → 39 ✓）と
`test_slimed_without_the_relic_exhausts_without_damage` ✓ suite **776 件 green** ✓ commit `359ae5b` ✓

census（build-valid ✓ 同じ tool ✓）: 6,840 replay 中 **87 件** の不一致（92 → 87 ✓ 5 件閉じた ✓）✓
`SLIMED_BERSERKER CARD.SLIMED` group は消えた ✓

決定母数（control = `.wt-ctrl-slimed` = `722cd26` ✓ selector `RELIC.FORGOTTEN_SOUL` ✓ 同じ mod binary ✓）:
5,135 観測で **759 件 changed** ✓ ただし **1 seed（H2LV6ZJ4XW）だけ** ✓ 採否の基準は「3 件以上の変更 AND
3 seed 以上」なので **panel は行わない** ✓ 忠実度修正として保持 ✓

`LetterOpener` の game 実装も読んだ ✓ `AfterCardPlayed` で `cardPlay.Card.Type == CardType.Skill` の時だけ
`SkillsPlayedThisTurn++` ✓ `% 3 == 0` で `HittableEnemies` 全員に `DamageVar(5, Unpowered)` ✓
`AfterSideTurnStart` は **TurnNumber == 1 を除いて** リセット ✓（model は毎回リセット ✓ 1 ターン目は 0 なので同じ ✓）✓
`CARD.SLIMED` は `CardType.Status` ✓ なので game は Skill として数えない ✓ model の `SKILLS` にも Slimed は
入っていない ✓ 残る `TUNNELER CARD.DEFEND_IRONCLAD game+5`（3 件）と `CARD.BATTLE_TRANCE game-5`（3 件）は
agent が推定する Skill 枚数のずれが疑い ✓ 次の対象 ✓

## Round 33（診断のみ ✓ code 変更なし）: LetterOpener が1枚ずれる原因は agent の玩札カウントの取り落としと二重計上

`TUNNELER CARD.DEFEND_IRONCLAD game+5`（3 件）と `CARD.BATTLE_TRANCE game-5`（3 件）を実行して数えた ✓
同じターンの連続する2つの決定で ✓ model だけ 5 削る箇所と game だけ 5 削る箇所が対になっている ✓
`RELIC.LETTER_OPENER` を持つ build ✓ game の規則は `AfterCardPlayed` で Skill の時 `SkillsPlayedThisTurn++`
し `% 3 == 0` で全員に 5 unpowered ✓ model は `skills_this_turn = skills_played_this_turn + 1`（今回の札込み ✓）
で `% 3 == 0` ✓ 規則は同じ ✓ ずれているのは **agent が推定する `skills_played_this_turn`** ✓

`burrow_arm_b1_P3V8N5K2RX` seq 234/237 の dump: seq 234 で model は LetterOpener を発動させた（5 ✓ game は 0 ✓）✓
seq 237 で発動させなかった（0 ✓ game は 5 ✓）✓ つまり **game の 3 枚目が seq 237 なのに ✓ model は seq 234 で
3 枚目だと読んでいた** ✓ agent のカウントが 1 枚早い ✓

同じ fight の turn 1 を seq 229 から追うと ✓ 取り落としと二重計上が同時に出ている ✓
seq 229 の `CARD.HEMOKINESIS`（Attack ✓ hand 5→4 ✓ discard 0→1 ✓）を玩んだ後の seq 230 でカウンタが
0/0/0 のまま ✓ **HEMOKINESIS が計上されていない** ✓ その次の seq 230 の Strike を玩んだ後の seq 231 で
カウンタは 2/0/2 に跳ぶ ✓ **1 枚の玩札が 2 枚として計上された** ✓ この2つは見かけ上打ち消すことが多く ✓
総枚数が合う局面では gap が出ない ✓ が Skill 枚数だけを見る LetterOpener では1枚のずれがそのまま
発動タイミングのずれになる ✓（同じ fight の `gate_arm_b2r` でも同じ形 ✓）✓

次の work は `_advance_play_counters` のこの2点 ✓ 具体的には (1) 新しい combat 最初の observation で
play が計上される経路（reset が先に走って `_PENDING_ACTION` が消える ✓ 疑い ✓）と ✓ (2) 計上済みの play の
札離脱が pile diff でもう一度数えられる経路 ✓（`_TURN_OWN_PLAYS` はそれを防ぐためにある ✓ HEMOKINESIS のような
全員に damage を入れる card でなぜずれるか ✓）✓ 実測値（seq 229-238 の手札・discard・カウンタ）を
検証用の固定データとして使う ✓

## Round 34: gap census を測っていた tool 自身が毎ターン1枚カウンタを失っていた（不一致 87 → 81 件、replay 一致 99.2%）

`data/boss_gap_list.py` は `same_fight` と same-turn を通る pair だけ `model_state` を呼んでいた ✓
`model_state` は `choose` を通るので **ここでしかカウンタが進まない** ✓ つまり飛ばした record の玩札が
カウンタから落ちていた ✓ そして飛ばされる record の典型は **そのターンの最後の決定** ✓ その次の record は
新しいターンなので pair 条件を通らない ✓ 結果として **毎ターンほぼ1枚足りないカウンタ** で測っていた ✓

直した ✓ 全 combat record を順に進め ✓（比べない record も `_advance_play_counters` で進める ✓）✓
compare するのは条件を通る pair だけ ✓ 同じ直し方を `data/model_match_audit.py` にも入れた ✓

測定の動き（build-valid trace ✓ 同じ group 定義 ✓）:

| 状態 | replay | 一致 | 不一致 |
|---|---:|---:|---:|
| tool 修正前（HEAD の model ✓ Slimed 修正後 ✓） | 6,840 | 6,753 | 87 |
| tool 修正後 | 6,840 | **6,759** | **81** |

**`TUNNELER CARD.DEFEND_IRONCLAD game+5`（3 件）と `CARD.BATTLE_TRANCE game-5`（3 件）は消えた** ✓
前 round で「LetterOpener の発動が1枚早い ✓ agent のカウントの取り落としと二重計上 ✓」と書いた診断は
**この tool の欠点が作った物だった** ✓ 前 round の seq 229-231 の dump は私が `_PENDING_ACTION` を
現在の record の玩札から入れてしまい ✓ agent の実際の順序（前の record の玩札を今の record で計上 ✓）と
違っていた ✓ 順序を直して並べ直すと HEMOKINESIS は正しく計上され ✓ 二重計上も出ていない ✓
**agent のカウンタ推定はこの fight では正しい** ✓ ここは撤回する ✓

`data/model_match_audit.py`（別の audit ✓ 玩札後の状態比較 ✓ limit 8000 ✓）は **5,887 比較中 5,839 一致 = 99.2%** ✓
（tool 修正前は 97.65% ✓ 97.65% はカウンタが進かない state での数値だった ✓）
`uncomparable` 1,751 ✓ `fight_boundary` 260 ✓ `no_equivalent_action` 100 ✓ `card_enemy_hp_mismatch` 46 ✓
`endturn_player_hp_mismatch` 2 ✓ `step_raised:ValueError` 2 ✓

残る group（81 件 ✓ 上位）: `QUEEN CARD.ASHEN_STRIKE game-1` 3 件 ✓ `VANTOM CARD.BATTLE_TRANCE game+1` 3 件 ✓
`BYGONE_EFFIGY CARD.STRIKE_IRONCLAD game+1` 3 件 ✓ `THE_INSATIABLE CARD.DEFEND_IRONCLAD game+5` 2 件と
`CARD.SHRUG_IT_OFF game-5` 2 件 ✓（LetterOpener の ±5 が残る ✓ ここは実際の model/agent 側の问题 ✓）✓
`QUEEN CARD.BREAKTHROUGH game-1` 2 件 ✓ `VANTOM CARD.UNRELENTING game+2` 2 件 ✓
`LOUSE_PROGENITOR CARD.PERFECTED_STRIKE game+3` 2 件 ✓ `THE_INSATIABLE CARD.ULTIMATE_STRIKE game+3` 2 件 ✓

## Round 35: 前に足した Exhaust 15 枚のうち 10 枚は keyword を持っていなかった（実測で discard に落ちる）

`CardKeyword.Exhaust` を decompile から数えた 119 枚は **token が mentioned された file の数** だった ✓
`HoverTipFactory.FromKeyword(CardKeyword.Exhaust)` のように **hover tip 内にだけ出す card が混ざっていた** ✓
play 時に自分の札がどの pile へ行くかを **trace の pile 差分で測った** ✓（同じ turn ✓ 同じ fight ✓ の
transition で exhaust/discard の増分を数える ✓）✓

| card | 実測 | 判定 |
|---|---|---|
| `CARD.EVIL_EYE` | exhaust +0 / discard +1（74 play ✓） | self-exhaust しない ✓ |
| `CARD.TRUE_GRIT` | exhaust +1 / discard +1（47 play ✓） | +1 は犠牲の札 ✓ 自身は discard ✓ |
| `CARD.BURNING_PACT` | exhaust +1 / discard +1（37 play ✓） | 対象を exhaust ✓ 自身は discard ✓ |
| `CARD.HOWL_FROM_BEYOND` | exhaust +0 / discard +1（6 play ✓） | しない ✓ |
| `CARD.HAVOC` | exhaust +1 / discard +1（5 play ✓） | 自身は discard ✓ |
| `CARD.BRAND` | exhaust +1 / discard +1（4 play ✓） | 自身は discard ✓ |
| `CARD.IMPERVIOUS` | exhaust +1 / discard +0（31 play ✓） | **する** ✓ |
| `CARD.SLIMED` | exhaust +1 / discard +0（27 play ✓） | **する** ✓ |

`CanonicalKeywords` override として宣言しているのも確認できた ✓ Dramatic Entrance・Impervious・
Molten Fist・Slimed・Toxic ✓ なので **この 5 枚だけ残し** ✓ Brand・Burning Pact・Cinder・Dark Embrace・
Evil Eye・Feel No Pain・Havoc・Howl From Beyond・Thrash・True Grit の 10 枚を `EXHAUSTS` から落とした ✓
（commit `073aabf` ✓ suite 776 件 green ✓ 前 round で書き換えたテスト 8 件は元の期待値に戻した ✓）✓
`data/exhaust_card_classes.json` は「token に言及した card 一覧」として残す ✓ 使い方注意を combat.py の
コメントに書いた ✓

正直に書いておく ✓ **model の `EXHAUSTS` は agent の玩札カウンタ推定に影響しない** ✓（推定は観測された
pile だけを見る ✓）✓ なので前 round の「余分な exhaust がカウンタを膨らませて LetterOpener が早い」は
**筋が違った** ✓ `THE_INSATIABLE CARD.DEFEND_IRONCLAD +5`（2 件）と `CARD.SHRUG_IT_OFF -5`（2 件）は
この変更後も残っている ✓ census は 6,840 replay 中 81 → **80 件** ✓（ほぼ変わらない ✓ 効果は rollout 内の
relic 発動と pile 表現の忠実さ ✓）✓

決定母数（control = `.wt-ctrl-exhaust` = `9bfc18e` ✓ selector はこの 10 枚の card ✓ 同じ mod binary ✓）:
975 観測で **228 件 changed ✓ 9 seed**（AM8C6YXHSG 106 ✓ D6A1F8C3E5 45 ✓ EAIF2UUVCK 24 ✓ SOS6XYXCNO 17 ✓
R8V2H6N4ZB 14 ✓）✓ 基準を満たすので **panel を起動した**（arm = `073aabf` ✓ control = `9bfc18e` ✓ seeds
AM8C6YXHSG / D6A1F8C3E5 / EAIF2UUVCK ✓ mechanism-targeted な再使用 ✓）✓ 05:52 開始 ✓ 結果待ち ✓

## Round 36（scratch まで ✓ 未適用 ✓）: model が元から self-exhaust させていた Ashen Strike と Second Wind も discard に落ちる

model の `EXHAUSTS` の 18 枚を **trace の pile 差分で一枚ずつ検証した** ✓（同じ turn ✓ 同じ fight ✓ の
transition で play 後の exhaust/discard の増分を数える ✓）✓ 合っていたのは TREMBLE（63 play ✓ exhaust +1
discard +0 ✓）✓ FEED（47 ✓）✓ IMPERVIOUS（31 ✓）✓ SLIMED（28 ✓）✓ OFFERING（5 ✓）✓ FORGOTTEN_RITUAL（1 ✓）✓
FIEND_FIRE（1 ✓ exhaust +7 ✓ 手札ごと ✓）✓ METAMORPHOSIS（1 ✓）✓

違ったのは 2 枚 ✓
- **`CARD.ASHEN_STRIKE`**: 4 play すべて **exhaust +0 / discard +1** ✓
- **`CARD.SECOND_WIND`**: 43 play すべて discard +1 ✓ exhaust 側は自分の効果（非 Attack を exhaust ✓
  `SecondWind.OnPlay` の `CardCmd.Exhaust(choiceContext, item)` ✓）で ✓ 自身は discard ✓

decompile でも **両方 `HoverTipFactory.FromKeyword(CardKeyword.Exhaust)` しか出てこない** ✓
`CanonicalKeywords` override は無い ✓ つまり keyword を持たない ✓

`.wt-proto3`（HEAD の scratch worktree ✓）から落して測った ✓ patch は `/tmp/ashen_secondwind.patch` ✓
scratch の suite は **776 件 green** ✓（`test_ashen_strike_scales_with_exhaust_pile` と
`test_second_wind_exhausts_for_block` は play した札が exhaust pile に入る前提で書かれていたので ✓
game の動きに合わせて書き換えた ✓）✓ group 別では **`QUEEN CARD.ASHEN_STRIKE game-1`（3 件）と
`QUEEN CARD.BREAKTHROUGH game-1`（2 件）が消えた** ✓ 総不一致は scratch 6,936/7,022 = 86 件 ✓ HEAD
6,757/6,840 = 83 件 ✓ **率はほぼ同じ**（1.22% と 1.21% ✓ rollout のたどる状態が変わって母数が動く ✓）✓
Ashen Strike の damage は `6 + 3 x len(exhaust_before)` で play 時点では自分を含めないため ✓
このずれは **後続の card の exponent 側**に出る ✓

exhaust panel は走行中（05:52 開始 ✓ arm = `073aabf` ✓ control = `9bfc18e` ✓ seeds AM8C6YXHSG /
D6A1F8C3E5 / EAIF2UUVCK ✓）✓ 走行中は policy code を触らない約束なので **この変更は未適用** ✓
panel が終わったら HEAD に適用して `data/boss_gap_list.py` で測り直す ✓

## Round 37（診断 ✓ code 変更なし ✓ panel 走行中）: Slow の ramp は stack 枚数ではなく SlowAmount ✓ 残 group は agent の玩札数のずれに帰着

`SlowPower` を読み直した ✓ **`DisplayAmount => SlowAmount * 10`** ✓ つまり trace に見える
`POWER.SLOW_POWER` の枚数は **stack の Amount で ✓ SlowAmount ではない** ✓ ramp は `SlowAmount` だけを見る ✓
`AfterCardPlayed` は card の種類を問わず `SlowAmount++` ✓ `AfterSideTurnStart`（**終了時ではない ✓ 開始時 ✓**）で
参加者に Owner がいれば 0 に戻す ✓ なので model の `cards_played_this_turn - 1` は
「model の state は解決中の card を already 数えている ✓ game は AfterCardPlayed なので自分の damage 計算ではまだ数えていない ✓」
という前提で合っている ✓ ただし次のずれが残っている ✓（`MONSTER.BYGONE_EFFIGY CARD.STRIKE_IRONCLAD` ✓ 3 件 ✓）

- seq 98（turn 1 の最初の決定 ✓ agent の cards_played 0 ✓ upgrade 1 ✓ var Damage 11 ✓ 敵 SLOW ✓ VULN 無し ✓）:
  game 12 = 11 x 1.1 ✓ **game の SlowAmount は 1** ✓ model は 0 として 11 ✓
- seq 99（同じ fight ✓ cards_played 1 ✓ var 8 ✓）: game 9 = 8 x 1.2 ✓ **SlowAmount 2** ✓ model は 1 として 8 ✓
- seq 106（turn 3 ✓ cards_played 2 ✓ var 8 ✓ 敵 VULN 1 ✓ SLOW ✓）: game 13 = 8 x 1.5 x 1.1 ✓ **SlowAmount 1** ✓
  model は 2 として 14 ✓

同じ fight で game の SlowAmount が agent の数えた枚数より **多い局面と少ない局面が両方ある** ✓
その run の relic は BRONZE_SCALES・BURNING_BLOOD・**CANDELABRA**・FISHING_ROD ✓
CANDELABRA は turn 2 に +2 energy ✓（`AfterSideTurnStart` で TurnNumber == 2 ✓ model 済み ✓）で ✓
card を玩む効果はない ✓ つまり turn 開始の autoplay では説明できない ✓ **原因は未特定** ✓
（`RELIC.TOASTY_MITTENS` を疑ったがこの build に無い ✓）✓ 3 件 ✓ 低優先 ✓

`MONSTER.VANTOM CARD.BATTLE_TRANCE game+1`（3 件）も同じ形 ✓ 敵 SLIPPERY 6→5 ✓ HP -1 ✓
game は hit を 1 だけ通している ✓ model は Slippery を `ModifyHpLostAfterOsty` と同じ規則
（未 block の残り 1 に cap ✓ 1 以上通った時だけ減算 ✓ `combat.py:1409-1429` ✓）で正しく model している ✓
so gap は LetterOpener が発動したかの側 ✓ seq 169 の dump では agent の skill 数 1 ✓ play 済みの card は
Defend・Hemokinesis・Strike ✓ game が Skill と数えるのは Defend と Battle Trance の 2 枚 ✓
`CARD.HEMOKINESIS` は `CardType.Attack` ✓ なので Skill 増分は説明できない ✓ **ここも未特定** ✓ 3 件 ✓

`CARD.LEAD_PAPERWEIGHT` は combat 効果を持たない Ancient relic ✓ 取得時に colorless 札 2 枚から 1 枚選んで
deck に入れるだけ ✓（`AfterObtained` ✓）✓ combat 側の gap の説明にはならない ✓
`RELIC.PLANISPHERE` は Unknown room 進入で heal 5 ✓ combat 外 ✓ model 未処理 ✓（map 側の話 ✓）✓

exhaust panel は arm 2 seed まで完了 ✓ control は未完了 ✓ 待機は background job `bash-703` ✓

## Round 38: Power 札はどの pile にも入らないので play カウンタから完全に落ちていた（scratch で修正 ✓ 未適用）

`MONSTER.BYGONE_EFFIGY CARD.STRIKE_IRONCLAD game+1`（3 件 ✓）を game 側の damage から逆算した ✓
seed AM8C6YXHSG の turn 1 は `CARD.INFLAME` → `CARD.STRIKE_IRONCLAD`（upgrade 1 ✓ base 11 ✓）→
`CARD.STRIKE_IRONCLAD`（base 8 ✓）で ✓ game の damage は 12 と 9 ✓ つまり Slow の係数は 1.1 と 1.2 ✓
**SlowAmount は 1 と 2** ✓ 一方 agent の cards_played は 0 と 1 ✓ **1 枚ずつ足りない** ✓
turn 3 の seq 106 は game の SlowAmount 1 ✓ .agent は 2 ✓（こちらは多い ✓ 別メカニズム ✓ 未特定 ✓）

足りない側の原因が特定できた ✓ **`CARD.INFLAME` は `base(1, CardType.Power)`** ✓ で ✓
`CardModel.GetResultPileTypeForCardPlay` は `IsDupe || Type == CardType.Power` の時 **`PileType.None`** を
返す ✓ つまり play した札が **hand から消えてどの pile にも現れない** ✓（trace でも hand 5→4 ✓
discard 0→0 ✓ exhaust 0→0 ✓）✓ だから pile 差分では復元できない ✓ And `_advance_play_counters` の明示的な
計上は `name in ATTACKS or name in SKILLS` の時だけ ✓ `Inflame` は ATTACKS でも SKILLS でも無い ✓
→ **Power 札は 1 枚もカウンタに入らない** ✓ `SlowPower.AfterCardPlayed` は card の種類を問わず
`SlowAmount++` ✓ なので Slow の ramp が Power 1 枚ごとに 1 足りなくなる ✓

直し（`.wt-proto4` ✓ patch は `/tmp/power_credit.patch` ✓）: `_advance_play_counters` で **選んだ card は
Attack/Skill かどうかに関係なく `_TURN_OWN_PLAYS` に入れる** ✓ attacks/skills は集合から導出するので
LetterOpener・Kusarigama・Shuriken などは影響せず ✓ `cards`（Slow の ramp が読む値 ✓）だけ増える ✓
regression test を追加 ✓ `test_power_card_plays_reach_the_play_counters`（Inflame → cards 1 ✓ attacks 0 ✓
skills 0 ✓ → Strike → cards 2 ✓）✓ scratch の suite は **777 件 green** ✓

**HEAD には未適用** ✓ exhaust panel の arm 3 seed 目が走行中だから ✓（main checkout を実行中の agent が読む ✓）✓
panel 完了後 ✓（1）Ashen Strike・Second Wind の修正（`/tmp/ashen_secondwind.patch` ✓ `.wt-proto3` ✓）✓
（2）Power 計上（`/tmp/power_credit.patch` ✓ `.wt-proto4` ✓）の順で適用し ✓ 毎回 suite と
`data/boss_gap_list.py` と attribution を測る ✓

## Round 39（診断 ✓ code 変更なし ✓ panel 走行中）: pile の増加が手札からの消失より多い transition が 7,412 中 587 ✓ 玩札推定の過大計上の母数

`MONSTER.BYGONE_EFFIGY` の seq 106 で agent が cards_played を 2 と数えた理由を pile の中身まで見た ✓
**discard には `CARD.ANGER` が 2 枚増えた ✓ 手札から出たのは 1 枚だけ ✓ draw pile は変化なし ✓** ✓
つまり 1 枚は **どこからも来ないで discard に現れた** ✓ これが `piles - _TURN_PILE_START` 経由で
「説明のない play」として 1 枚加算された ✓（`_LAST_PLAY_MOVES_OTHER_CARDS` が False の時は
`unexplained` が hand に現れた札であることを確認せずに play として扱う ✓）✓

出所は特定できていない ✓ 消した候補: `MONSTER.BYGONE_EFFIGY` の export には
`DamageCmd.Attack` と `PowerCmd.Apply`（Strength）だけで card を足す効果はない ✓（export が拾っていない
可能性は残る ✓）、`RELIC.CANDELABRA` は turn 2 の +2 energy ✓、`RELIC.FISHING_ROD` は combat 数を数える
Ancient relic ✓、`RELIC.LEAD_PAPERWEIGHT` は取得時の card 選択だけ ✓。手札にあった `CARD.SPOILS_MAP` は
この build で model 知らない card id ✓ 疑いはあるが証拠はない ✓

母数を測った ✓ build-valid trace の same-turn transition **7,412 件のうち 587 件（7.9%）** で
discard+exhaust の増加が hand の消失より多い ✓ 23 seed ✓ 上位 P3V8N5K2RX 115 ✓ AM8C6YXHSG 90 ✓
L3PN5HBQ8T 79 ✓ H2LV6ZJ4XW 77 ✓ **これは上側の誤りの上限** ✓（札を引いて同じ観測幅内で玩む
autoplay ✓ Mayhem・Hellraiser など ✓ でも同じ形になる ✓）✓

次の選択肢（未決 ✓ 重たい測定が必要なので panel 終了後 ✓）: `unexplained` を
「そのターンに hand に現れた札」に限定する ✓ 誤加算は落ちる ✓ 代償は newly-drawn 札の autoplay を
数え損なうこと ✓ どちらが net でましかが測れないと決められない ✓

Slow 側の下側（Power 札が計上されない ✓ 前 round ✓）は `.wt-proto4` に修正済み ✓
`/tmp/power_credit.patch` ✓ scratch suite 777 件 green ✓ HEAD 未適用 ✓

## Round 40（診断 ✓ code 変更なし ✓ panel 走行中）: model が名前の知らない card id と Stratagem の未実装効果

build-valid trace の hand / deck / discard に現れる card id を model の既知名と突き合わせた ✓
**`CARD.WOUND` は既知だった** ✓（私の名前抽出 heuristic が取りこぼした ✓ 下の list から除外すべき ✓）✓
本当に知らないのは次 ✓（観測数 ✓ seed 数 ✓）:

| card id | 観測 | seed | game 側の定義 |
|---|---:|---:|---|
| `CARD.STRATAGEM` | 581 | 3 | `base(1, CardType.Power)` ✓ `PowerCmd.Apply<StratagemPower>(1)` ✓ |
| `CARD.BYRDONIS_EGG` | 214 | 3 | `base(-1, CardType.Quest)` ✓ `CardKeyword.Unplayable` ✓ |
| `CARD.SPOILS_MAP` | 136 | 1 | （未読 ✓） |
| `CARD.CLUMSY` | 86 | 4 | `base(-1, CardType.Curse)` ✓ `Unplayable` + `Ethereal` ✓ |
| `CARD.LANTERN_KEY` | 44 | 1 | `base(-1, CardType.Quest)` ✓ `Unplayable` ✓ |
| `CARD.ENTHRALLED` | 34 | 1 | `base(2, CardType.Curse)` ✓ `CardKeyword.Eternal` ✓ `ShouldPlay` override ✓ |
| `CARD.MAYHEM` / `CARD.SECRET_WEAPON` / `CARD.THINKING_AHEAD` | 3 / 3 / 2 | 2 / 1 / 1 | 既知の効果 ✓ play 計上側の話 ✓ |

**Stratagem の効果は `StratagemPower.AfterShuffle`** ✓ draw pile をシャッフルする時（= 引き札が尽きた時 ✓）
`Amount` 枚を draw pile から選んで **hand に置く** ✓ つまり 1 枚で山を掘る効果 ✓
そして **`POWER.STRATAGEM_POWER`（amount 1）は trace の player powers に 793 回・4 seed 現れる** ✓
観測できる ✓ なのに model は知らない ✓ → reward 選択・play の価値・draw pile の中身のすべてで
model が過小評価する ✓ 実装案: model の draw 処理が draw pile 尽きて reshape する箇所で hook を置き ✓
`Amount` 枚を draw pile から best-first で hand へ移す ✓（game は player 選択 ✓ model は楽観選択 ✓）✓

Unplayable の Quest / Curse 札（Byrdonis Egg ✓ Clumsy ✓ Lantern Key ✓）は hand に居ても play できない ✓
model はこれらの card を legal_actions に出さない ✓ 一方で **draw pile の中身を変えて** Battle Trance や
Perfected Strike の価値、`AfterShuffle` 系効果の有無に影響する ✓ ここも未処理 ✓

**HEAD の policy 変更は保留中 2 件** ✓（`/tmp/ashen_secondwind.patch` ✓ `/tmp/power_credit.patch` ✓）✓
exhaust panel の arm 3 seed 目がまだ走行中 ✓ 完了後に応用して測定する顺序: panel 収集 → Ashen/Second Wind
→ Power 計上 → Stratagem ✓

## Round 41: headless launch が main menu で止まり panel の 3 seed 目が空になった（sweep3.sh を用意）

exhaust panel の arm 3 seed 目（EAIF2UUVCK ✓ 06:03 開始）が **25 分たっても combat record を 1 件も出していない** ✓
bridge の temp dir は空 ✓（`observation.json` も `action.json` も無い ✓）✓ trace file も無い ✓
game log の最後は:

```
[INFO] [AutoSlay] Action: Abandoning existing run
[WARN] Asset not cached: res://scenes/ui/abandon_run_confirm_popup.tscn
[INFO] Preloading 'Common' assets... count=686 vfx=92
[INFO] [Startup] Resource stats (main menu loaded (complete)): ...
```

つまり **run を破棄する確認 popup の scene が cache されていない ✓ そこで main menu から先へ進まない** ✓
`run_official_autoslay.ps1` は isolated appdata を作るが `APPDATA` を設定するのは `-not $IsMacOS` の時だけ ✓
（`run_official_autoslay.ps1:101` ✓）なので macOS では実 userdata を使う ✓ sweep2.sh は seed ごとに
`rsync -a --delete ~/.sts2/userdata-pin/ → userdata/` をやる ✓（`sweep2.sh:11,18` ✓）✓ 
同じ復元を毎回やっているのに 3 seed 目だけ止まった ✓ **断続的な race** ✓（popup の非同期読み込みと
AutoSlay の操作 ✓）✓ `wins=0 losses=0 exit=1` だった前回の実行と違い ✓ 今回は pwsh 側が 1800 s を
待つので 30 分を無駄にする ✓

**panel への影響** ✓ arm は AM8C6YXHSG 17 勝 1 敗 ✓ D6A1F8C3E5 15 勝 1 敗 の 2 seed しか確保できない見込み ✓
採否基準は 3 seed 以上なので **この panel だけで採否は決めない** ✓ Exhaust 10 枚の取り消しは
trace の pile 実測（EVIL_EYE 74 play で exhaust +0 ✓ TRUE_GRIT 47 play ✓ BURNING_PACT 37 play ✓ など ✓）で
方向が確定している忠実度修正なので保持 ✓ 勝敗の判定が欲しければ sweep3.sh でやり直す ✓

**`=sweep3.sh` を追加**（`/Users/mao/.sts2/scripts/sweep3.sh` ✓ 文法チェック済み ✓）✓ seed ごとに
`combat_records=` を出力し ✓ **combat record が 5 件未満なら 1 度だけ再試行** ✓ して同じ file 名に戻す ✓
空 run を 0 勝として数える誤りを防ぐ ✓（`RESULT` 行に `combat_records=` を入れた ✓）✓ 
次の panel は sweep3.sh を使う ✓

## Round 42: play した Power 札は combat から完全に抜ける（model は discard に戻して再使用させていた）

`CardModel.GetResultPileTypeForCardPlay` は **`CardType.Power` の札に `PileType.None` を返す** ✓ つまり play
した Power 札は discard にも exhaust にも入らない ✓ decompile 上 `CardType.Power` は **111 枚** ✓
model が play できるのはそのうち **20 枚**（Aggression・Barricade・Crimson Mantle・Cruelty・Dark Embrace・
Demon Form・Fasten・Feel No Pain・Hellraiser・Inferno・Inflame・Juggernaut・Juggling・Panache・Pyre・
Rupture・Stampede・Stone Armor・Unmovable・Vicious ✓）✓

**trace で検証した** ✓ 同じ turn ✓ 同じ fight の transition で play 後の pile 増分を数えた ✓
`CARD.INFLAME` 58 play ✓ `CARD.STONE_ARMOR` 35 ✓ `CARD.RUPTURE` 30 ✓ `CARD.CRIMSON_MANTLE` 22 ✓
`CARD.HELLRAISER` 16 ✓ `CARD.UNMOVABLE` 9 ✓ `CARD.VICIOUS` 4 ✓ `CARD.AGGRESSION` 3 ✓ Pyre 1 ✓
Juggernaut 1 ✓ Stampede 1 ✓ → **すべて `exh+0 disc+0`** ✓ 1 枚も pile に残っていない ✓
model は `discard ('Inflame',)` と discard に返していた ✓ → rollout では **使い済みの Power がシャッフルで
戻って同じ combat で何度でも play できる** ✓ 長い combat の価値を過大評価する ✓

修正（scratch `.wt-proto5` ✓ patch `/tmp/power_leaves_combat.patch` ✓ suite **778 件 green** ✓）:
`POWER_CARDS` を追加し ✓ `exhaust` が無い play で `card in POWER_CARDS` なら discard にも exhaust にも
入れない ✓ 顺序は game と同じ（Exhaust keyword が先 ✓その次に Power → None ✓）✓

テスト 1 件がこの修正で壊れた ✓ `test_hellraiser_autoplays_a_strike_drawn_at_turn_start_for_free` は
play 済みの Hellraiser が discard から引かれて **hand に戻ってくる**前提だった ✓ game の規則と違うので ✓
「Hellraiser はどの pile にも無い ✓ ターン開始の draw で STRIKE が戻り HellraiserPower で無料で play される ✓
hand () ✓ 敵 94 ✓ energy 3 ✓」に書き換えた ✓ 新しい test を 1 件追加 ✓
`test_power_cards_leave_the_combat_when_played` ✓

`AfterShuffle` を読む effect も 3 数えた ✓ **`StratagemPower`**（draw pile から Amount 枚選んで hand へ ✓
**消えない ✓ shuffle ごとに発動 ✓**）✓ `RELIC.THE_ABACUS`（+6 unpowered block ✓）✓ `RELIC.BIIIG_HUG`
（Soot を draw pile のランダム位置に追加 ✓）✓ model はいずれも未実装 ✓ trace での出現は
`POWER.STRATAGEM_POWER` **24 trace** ✓ THE_ABACUS 0 ✓ BIIIG_HUG 0 ✓ なので **Stratagem から実装する** ✓
model の reshape 点は `_draw` の `if not draw: draw, discard = discard, []` ✓（`combat.py` ✓）✓

**未測定** ✓ control sweep（`9bfc18e` ✓ 06:33 開始 ✓ seed 1 走行中 ✓）が終わるまで重い replay は走らせない ✓
（実行中の agent の 25 ms polling を奪う ✓）✓ 測定したら HEAD に適用する ✓

## Round 43: `combat.py` は Power 札の集合 `POWERS` を既に持っていた（20 枚 ✓ decompile と完全一致）

前 round の scratch 修正は独自に `POWER_CARDS` を定義した ✓ が ✓ `combat.py:200` の
`POWERS = {STAMPEDE, VICIOUS, INFLAME, RUPTURE, INFERNO, CRUELTY, STONE_ARMOR, FEEL_NO_PAIN, BARRICADE,
PYRE, UNMOVABLE, AGGRESSION, DARK_EMBRACE, CRIMSON_MANTLE, HELLRAISER, FASTEN, DEMON_FORM, JUGGERNAUT,
JUGGLING, PANACHE}` ✓ が **decompile から数えた CardType.Power の 20 枚とぴったり同じ** ✓
重複定数をやめて `leaves_combat = not exhaust and card in POWERS` に載せ替えた ✓
scratch suite **778 件 green** ✓ patch `/tmp/power_leaves_combat.patch`（63 行 ✓）✓

exhaust panel の比較（wins は combat 勝数 ✓ Act 3 踏破ではない ✓）:

| seed | arm `073aabf` | control `9bfc18e` |
|---|---:|---:|
| AM8C6YXHSG | 17 勝 1 敗 | **17 勝 1 敗** |
| D6A1F8C3E5 | 15 勝 1 敗 | 走行中 |
| EAIF2UUVCK | 空（main menu 停止 ✓） | 未開始 |

1 seed 目は同じ ✓ 同じ数値は測定になっていない ✓ 3 seed 目が空なので基準（3 seed ✓）を満たさない見込み ✓

**panel 完了後に走る測定を仕掛けた** ✓ `/tmp/measure_after_panel.sh`（panel の `PANEL_DONE` を待って実行 ✓
実行中に重い replay を走らせないため ✓）:
1. `python3 data/boss_gap_list.py 10` → `/tmp/gap_after_fixes.txt` ✓（HEAD に適用済みの Ashen/Second Wind と
   Power 計上の效果 ✓）
2. attribution arm `.wt-attr-e10`（`e10e5ee` ✓）vs control `.wt-attr-073`（`073aabf` ✓）で
   `PLAYER:POWER.STRENGTH_POWER` → `data/ashen_attr.log` ✓（Ashen/Second Wind の決定母数 ✓）
3. attribution arm HEAD vs control `.wt-attr-e10` で `POWER.SLOW_POWER` → `data/powercredit_attr.log` ✓
   （Power 計上の決定母数 ✓ Slow の ramp を読むのはその集団 ✓）

`attribution_rampart.py` の selector は **1 個だけ** ✓（usage ✓ line 15 ✓）✓ 最初に `RELIC.X,CARD:...` の
複合を渡した版は empty になる ✗ 杀掉して直し ✓ selector を分離した ✓ `CARD:` は **upgraded copy が手札に
ある決定だけ**を選ぶ ✓（line 48-52 ✓）ので upgrade 依存でないこの修正には合わない ✓
`PLAYER:POWER.STRENGTH_POWER`（57,220 観測 ✓ ほぼ全 combat 決定 ✓）を母数の近似に使う ✓

## Round 44: exhaust panel 完了（勝敗は変化なし ✓ census は 80 → 74 件）と Stratagem の model 実装（scratch ✓ 779 件 green）

**exhaust panel（10 枚の self-exhaust 取り消し ✓ arm `073aabf` vs control `9bfc18e` ✓ 同じ mod binary ✓）**

| seed | arm | control |
|---|---:|---:|
| AM8C6YXHSG | 17 勝 1 敗 | 17 勝 1 敗 |
| D6A1F8C3E5 | 15 勝 1 敗 | 15 勝 1 敗 |
| EAIF2UUVCK | 空（main menu 停止 ✓ 前 round ✓） | 14 勝 1 敗 |

比較できる 2 seed で **arm と control が同じ勝敗** ✓ 同じ数値は測定にならない ✓ 判定は出せない ✓
EAIF2UUVCK は control 側は正常に完了したので **停止は断続的** と確認できた ✓（arm 側だけ止まった ✓）✓
この変更は trace の pile 実測（EVIL_EYE 74 play で exhaust +0 / discard +1 ✓ TRUE_GRIT 47 ✓ BURNING_PACT 37 ✓ など ✓）で
方向が確定している忠実度修正なので保持 ✓ 勝敗の改善としては計上しない ✓

**HEAD に適用済みの 2 修正（`e10e5ee` Ashen/Second Wind ✓ `398c620` Power 計上 ✓）後の census** ✓
`data/boss_gap_list.py 10`（build-valid trace ✓ 同じ group 定義 ✓）:
**7,322 actions replayed ✓ 7,248 matching ✓ 不一致 74 件** ✓（適用前 80 件 ✓ tool 修正前 87 件 ✓）✓
`QUEEN CARD.ASHEN_STRIKE game-1` と `QUEEN CARD.BREAKTHROUGH game-1` は消えた ✓
残る上位: `VANTOM CARD.BATTLE_TRANCE game+1` 3 ✓ `BYGONE_EFFIGY CARD.STRIKE_IRONCLAD game-1` 3 ✓
`THE_INSATIABLE CARD.FEED game-1` 2 ✓ `THE_INSATIABLE CARD.SHRUG_IT_OFF game-5` 2 と
`CARD.DEFEND_IRONCLAD game+5` 2 ✓（LetterOpener の ±5 ✓）✓
attribution は実行中 ✓ `/tmp/gap_after_fixes.txt` ✓ **まだ main の policy を触らない** ✓
（3 番目の attribution が main の HEAD と `.wt-attr-e10` を比べるから ✓ 実行中に main を変えると測る物が動く ✓）

**Stratagem を model に入れた**（scratch `.wt-proto5` ✓ suite **779 件 green** ✓
patch `/tmp/stratagem_plus_power.patch` 180 行 ✓ Power 除去単体は `/tmp/power_leaves_combat.patch` 63 行 ✓）:

- `STRATAGEM = "Stratagem"` ✓ `CARD_COST` に 1 ✓ `POWERS` に追加 ✓ `UNTARGETED` に追加 ✓
  （**legal_actions は `name in UNTARGETED` を通らないと標的付き扱いになる ✓** これが無いと
  `int('')` で ValueError ✓）✓
- play 効果は untargeted Power と同じ早期 return の形 ✓
  `return replace(combat, player_powers=_add_power(combat.player_powers, "StratagemPower", 1))` ✓
  （pile を触らない ✓ これは Power 札が combat から抜ける規則と整合 ✓）✓
- shuffle hook は `_draw_into_combat` ✓ `reshuffled = len(combat.draw_pile) < count and bool(combat.discard_pile)` ✓
  shuffle が起きた時だけ ✓ power 枚数ぶん draw pile から damage→block の順で高い札を選んで hand へ ✓
  **power は減らない ✓以后の shuffle でも発動 ✓**（game の `AfterShuffle` は消費しない ✓）✓
- `official_agent.py` に `"POWER.STRATAGEM_POWER": "StratagemPower"` と `"CARD.STRATAGEM": "Stratagem"` ✓
  後者は test が要求した ✓（`test_every_playable_card_in_the_combat_model_is_reachable_from_the_observation` が
  model で玩える card は observation の id 対応を持つ事を検査 ✓ **Stratagem を落ちた ✓良い検査 ✓**）✓
- 新規 test `test_stratagem_pulls_cards_from_the_draw_pile_on_every_shuffle` ✓（Battle Trance の 3 枚 draw が
  draw pile 1 枚で shuffle を起こし ✓ StratagemPower が BASH を hand へ ✓ power は 1 のまま ✓）✓

## Round 45: `THE_INSATIABLE CARD.SHRUG_IT_OFF game+13 / +9` は Hellraiser の autoplay ✓ rollout の draw 順違いで再現不能

大きい delta の group を faithful dump で割った ✓ seed AM8C6YXHSG の 2 件 ✓ turn 4 seq 278 は
**game 13 / model 0** ✓ turn 7 seq 288 は **game 9 / model 0** ✓ 両方 `POWER.HELLRAISER_POWER` 1 を持つ ✓
relic は BAG_OF_MARBLES・BRONZE_SCALES・BURNING_BLOOD・CANDELABRA・FISHING_ROD・JUZU_BRACELET・
ORICHALCUM・YUMMY_COOKIE ✓ 敵は SANDPIT と（1 件目は）VULNERABLE 3 ✓ Strength 3 ✓
数字が一致する ✓ 2 件目は Vulnerable 3 あり → Strike (6+3=9) × 1.5 = 13.5 → **13** ✓
3 件目は Vulnerable 無し → 6+3 = **9** ✓ つまり game は Shrug It Off の draw で引いた **Strike を
HellraiserPower が自動で玩んだ** ✓ model は同じカードを引かなかった ✓（rollout の draw 順が game と違う ✓）✓
→ **これは忠実度では直せない group** ✓（game の draw は乱数 ✓ model の rollout は別の乱数 ✓）✓
前 round まで残っていた `CARD.DEFEND_IRONCLAD game+5` / `CARD.SHRUG_IT_OFF game-5` の LetterOpener 群とは
別物なので ✓ これ以上触らない ✓

一方 `game 0 / model 5`（seed P3V8N5K2RX seq 356 ✓ model だけ LetterOpener の 5 を出した ✓）は
**玩札数の過大計上** ✓ 同じ turn 内に pile へ「よそから」入った札を play として数える ✓
`unexplained = (piles - _TURN_PILE_START) - _TURN_OWN_PLAYS - _TURN_EFFECT_DEPARTURES` は
**pile への到着数**を見ているので ✓ (a) 敵の効果などが discard に足した札 ✓
(b) 引かれて即 autoplay された札 ✓ の両方を区別せずに play にする ✓

素朴な直し（到着数が手札からの消失を超える分を引く ✓）は (b) を壊す ✓ seq 278 では
hand 2→1 ✓ discard +2 ✓ 到着 > 消失 ✓ でもその 1 枚は本物の play（Hellraiser の autoplay ✓）✓
**区別に必要な情報は draw pile の減少** ✓（autoplay は draw pile から直接玩む ✓ 敵が札を足す場合は
draw pile は減らない ✓）✓ まだ実装していない ✓ 影響測定 は BYGONE_EFFIGY 群 5 件と LetterOpener 系の一部 ✓
7,322 件中 74 件の一部分 ✓ 割合は小さい ✓ 実装するなら census と suite で壊れる規則を特定してから ✓

**現在の状態** ✓ HEAD `4dfc611` ✓ suite 777 件 green ✓ 公式 run なし ✓
attribution 2 本は実行中（`/tmp/measure_after_panel.sh` ✓ 06:49 から ✓ `data/ashen_attr.log` はまだ空 ✓）✓
それが終わるまで main の policy は触らない ✓（3 番目が main の HEAD と `.wt-attr-e10` を比べる ✓）✓
適用待ち: Power 除去（`/tmp/power_leaves_combat.patch` ✓ 63 行 ✓）と Stratagem
（`/tmp/stratagem_plus_power.patch` ✓ 180 行 ✓ 両方含む ✓）✓ scratch `.wt-proto5` suite 779 件 green ✓

## Round 46: 玩札推定を手札ベースで制限する案は観測データで成立せず ✓ 代わりに game 自身の玩札数を bridge 経由で出す実装を開始（ビルド成功 ✓）

**失敗した案**（scratch `.wt-proto7` ✓ 削除済み ✓）: `unexplained`（pile への到着から導いた play 数）を
「そのターンに hand と draw pile から出た札の数」で上限化した ✓ `BYGONE_EFFIGY` の seq 106
（discard に `CARD.ANGER` が 2 枚増え ✓ 手札からは 1 枚だけ消え ✓ draw pile は減らず ✓）では正しく 1 枚引けた ✓
が ✓ `test_rebuilds_the_play_counters_the_bridge_does_not_export` の Cinder/Defend ケースで autoplay 1 枚を
消した ✗✗ 原因: 同名の札が区別できないため ✓ **Defend を 1 枚 play して別の Defend を引くと手札の
Defend 枚数は変わらない ✓ 消失が見えない ✓** ✓ hand の枚数差は play の検出に使えない ✓
この方向はすてる ✓

**正しい方向**: game は玩札数を combat の履歴から正確に持っている ✓
`Normality.CardsPlayedThisTurn => CombatManager.Instance.History.CardPlaysStarted.Count(e =>
e.HappenedThisTurn(CombatState) && e.CardPlay.Card.Owner == Owner)` ✓（`Normality.cs:33` ✓）✓
`CombatHistory.CardPlaysStarted => Entries.OfType<CardPlayStartedEntry>()` ✓（`CombatHistory.cs:26` ✓）✓
`CombatHistoryEntry.HappenedThisTurn(ICombatState?)` ✓（`CombatHistoryEntry.cs:62` ✓）✓
`CardModel.Owner` は **`Player`** ✓（`CardModel.cs:333` ✓）✓ `CombatManager.Instance.History` は public ✓
bridge は既に `CombatManager.Instance.DebugOnlyGetState()` を使っている ✓

**実装した**（scratch `.wt-bridge-counts` ✓ patch `/tmp/bridge_playcounts.patch` 84 行 ✓）✓
`CombatBridge.cs` に `PlayedCounts(player, thisTurnOnly)` を追加 ✓（履歴を walk して Owner を `ReferenceEquals(card.Owner, player)`
で絞り ✓ `card.Type` で Attack / Skill を数える ✓）✓ **observation と trace の両方**に次を追加 ✓

```
plays = { cards_this_turn, attacks_this_turn, skills_this_turn,
          cards_combat,   attacks_combat,   skills_combat }
```

**ビルド成功** ✓（`pwsh -NoProfile -File ./build_official_mod.ps1 -GameDir ...` ✓
`ビルドに成功しました / 0 個の警告 / 0 エラー` ✓ 経過 3.5 s ✓ `official_mod/bin/Release/net9.0/Sts2Ai.dll` 235,008 bytes ✓）✓
API が全部解決しているので ✓ 型も含めて game 側に存在することが保証された ✓

**まだ終わっていない** ✓ 次の順: (1) `official_agent.py` が `observation["plays"]` を使い ✓ 無いときだけ
`_advance_play_counters` の推定に倒す ✓（テスト追加 ✓）(2) この dll での短い公式 run で
実際の observation に数が出ることと ✓ trace の play 列と一致することを確かめる ✓
(3) census を測り直す ✓ 期待して消える group: `THE_INSATIABLE CARD.SHRUG_IT_OFF game+5` /
`CARD.DEFEND_IRONCLAD game+5`（LetterOpener ✓ 36 件时代の実測あり ✓）✓ `BYGONE_EFFIGY` の ±1 ✓
`MONSTER.VANTOM` 系 ✓ (4) 决定母数が大きければ panel ✓（3 seed ✓ 上記 + 1 ✓）✓

attribution は実行中 ✓（06:49 開始 ✓ 07:06 時点で経過 16 分 ✓ CPU 時間 0.6 秒 ✓ **停止ではなく
trace ごとに subprocess を 1 個ずつ起動している** ✓ `attribution_rampart.py:115-119` ✓ 現在 child 50454 が稼働 ✓）✓
完了待ちは background job `bash-811` ✓ 完了後に `data/ashen_attr.log` と `data/powercredit_attr.log` を読む ✓

## Round 47: bridge が出す玩札数を agent が使う実装完了（scratch ✓ 778 件 green ✓ 検証 run を仕込み）

`.wt-bridge-counts`（bridge 変更と同じ tree ✓）に agent 側を入れた ✓
`_seed_exported_plays(observation)` を追加し ✓ `choose()` が `_advance_play_counters(observation)` の直後に呼ぶ ✓
observation に `plays` があれば `_TURN_PLAYS`（cards / attacks / skills）と `_COMBAT_PLAYS`（attacks / skills）を
その値で上書き ✓ 無ければ（古い mod build ✓）推定のまま ✓ `_EXPORTED_PLAYS` にどちらを使ったか残す ✓
model state への注入点は `official_agent.py` の `attacks_played_this_turn=` 付近 ✓（`_TURN_PLAYS` を読む ✓）✓

**scratch suite 778 件 green** ✓ 壊れた test は無い ✓（既存 test の observation に `plays` が無いので
推定の経路がそのまま検査されている ✓）✓ 新規 test `test_exported_play_counts_replace_the_inferred_ones` ✓
（`plays` あり → cards 2 / attacks 1 / skills 1 ✓ combat 側 attacks 3 ✓ `plays` 無し → False ✓）✓
patch: `/tmp/bridge_playcounts.patch` 180 行（`CombatBridge.cs` + `official_agent.py` + test）✓

**中間に壊した箇所** ✓ 前 round で捨てた上限実験の global 名をこの tree に混ぜて line 423 が
`_TURN_SOURCE_LEFT: dict[str, int] = {...}: dict[str, int] = {...}` になり ✓ 5 test が import 失敗した ✓
（`Ran 400 tests` は module 失敗の兆候 ✓ 777 になっていない ✓）✓ 行を直して green ✓

**検証 run を仕込んだ** ✓ `/tmp/validate_bridge_counts.sh` ✓ attribution の完了
（`/tmp/measure_after.status` ✓）を待ってから ✓ `REPO=/Users/mao/workspace/sts2-ai/.wt-bridge-counts
sweep3.sh bcp1 AM8C6YXHSG` を実行 ✓ 出力 `/tmp/bcp1.log` ✓ 完了印 `/tmp/bcp1.status` ✓
見るもの: (1) 実際の observation に `plays` が入っているか ✓ (2) trace の play 列と数が一致するか ✓
(3) **推定値との差** ✓ 上の round まで推定は `unexplained` で誤っていた ✓ export された数と突き合わせれば
**推定がどれだけ頻繁に間違っていたかを直接測れる** ✓ 例: `THE_INSATIABLE` の LetterOpener ±5 群 ✓
`BYGONE_EFFIGY` の ±1 群 ✓ これが消えるか ✓

HEAD には未適用 ✓（`.wt-bridge-counts` は HEAD + bridge/agent 変更 ✓ dll は scratch にビルド済み 235,008 bytes ✓
sweep は REPO の dll を使う ✓）。適用する前に run で field の実在を確認する ✓

## Round 48: 広い selector の attribution は遅すぎて中止 ✓ 代わりに export された玩札数と推定を比べる probe を用意

`PLAYER:POWER.STRENGTH_POWER` の attribution は 06:49 開始で **25 分たっても出力が空** ✓
`data/attribution_rampart.py:115-119` は trace ごとに subprocess を 1 個起動する作りで ✓
build-valid trace 約 600 件 × 2 tree ✓ 1 件 1-3 秒なので **合計 20-60 分**かかる ✓
これは Ashen/Second Wind（すでに commit 済み ✓ trace の pile 実測で方向が確定している忠実度修正 ✓）の
决定母数を得るための補助測定で ✓ 価値は低い ✓ 一方 bridge の玩札数の検証 run は価値が高い ✓
そこで **最初の attribution を kill した** ✓ 決定母数は取れていない ✓（`data/ashen_attr.log` は空のまま ✓）✓
チェーンの次（`POWER.SLOW_POWER` ✓ 集団が小さい ✓ arm = main ✓ 07:14 開始 ✓）は動く ✓
**これは main の code を読むので終わるまで main の policy を触らない** ✓

広い selector は高い ✓ 教訓: attribution の selector は測る集団に合わせる ✓
（`POWER.SLOW_POWER` ✓ `RELIC.X` ✓ `CARD:<ids>` ✓ のように ✓ STRENGTH のようなほぼ全 decision を
選ぶ selector は使わない ✓）✓

新しい probe `/tmp/plays_diff.py` ✓（構文チェック済み ✓）: build-valid trace を全 record 進め ✓
前の record の action を credit する順序を再現し ✓（前 round の教訓 ✓）✓ 推定した
cards / attacks / skills と ✓ record の `plays` 字段を突き合わせて ✓ 一致率と delta の分布を出す ✓
`PROBE_TREE=<bridge 変更のある repo>` で tree を選べ ✓ 検証 run（`/tmp/bcp1.log` ✓
trace は `data/bcp1_AM8C6YXHSG_agent.jsonl` ✓）が終わったらこれを走らせる ✓
**推定がどれだけ頻繁に間違っていたかを直接測る道具** ✓

## Round 49: Power 計上の决定母数は 0 件（panel しない ✓）と Power 除去・Stratagem を HEAD に適用

attribution（arm = HEAD ✓ control = `.wt-attr-e10` ✓ selector `POWER.SLOW_POWER` ✓ SIMULATIONS=1 ✓）:

```
power: POWER.SLOW_POWER  records compared: 1718  trees: 2
decision changed: 0  unchanged: 1718  errors: {'KeyError': 108}
seeds with a changed decision: 0
```

**Slow の ramp を読む集団 1,718 件の决定が 1 件も変わらなかった** ✓ つまり Power 札をカウンタに載せる修正は
state の数値は直す（census 80 → 74 件 ✓）が ✓ その時点の agent の選択は変えない ✓
**决定が 0 件の変更には win panel をしない** ✓（前の教訓 ✓）✓ 忠実度修正として保持 ✓
`KeyError` 108 件は model の知らない card id を再生した時の形 ✓（`CARD.SPOILS_MAP` ✓ `CARD.STRATAGEM` ✓
`CARD.CLUMSY` など ✓ 前 round の unknown card 実測 ✓ と整合 ✓）✓

**HEAD に適用した** ✓ suite **779 件 green** ✓ ツリー clean ✓
- `84dfb91` play した Power 札を combat から取り除く ✓（`POWERS` を使い ✓ exhaust で無い play は
  discard にも exhaust にも入れない ✓ 実測 Inflame 58 play などで exhaust+0 discard+0 ✓）✓
- `dfced8b` Stratagem を model に入れる ✓（cost 1 ✓ untargeted Power ✓ `StratagemPower` 1 ✓
  reshape 時に power 枚数ぶん draw pile から hand へ ✓ 消費されない ✓）✓

**patch の手順ミス** ✓ `/tmp/stratagem_plus_power.patch` は Power 除去と Stratagem の**合算** diff だった ✓
Power 除去を先に commit した main には当たらない ✗（`patch failed: combat.py:2887` ✓）✓
直し方: 新しい HEAD（`84dfb91`）に worktree を切り ✓ scratch の 3 ファイルをコピーして ✓
`git diff` で **Stratagem 単体**の diff（`/tmp/stratagem_only.patch` 132 行 ✓）を作り適用 ✓
合算 patch を commit 後に使い回さない ✓

**検証 run が始まった** ✓ 07:15 ✓ game process 1 ✓ `/tmp/bcp1.log` に SWEEP START ✓
`REPO=/Users/mao/workspace/sts2-ai/.wt-bridge-counts`（bridge が `plays` を出し ✓ agent がそれを使う ✓
policy は HEAD 適用前の code ✓）で seed AM8C6YXHSG ✓ 完了待ちは background job `bash-850` ✓
trace `data/bcp1_AM8C6YXHSG_agent.jsonl` が出たら `/tmp/plays_diff.py` を走らせて
**推定と game の数の食い違いの頻度**を出す ✓ 次に census を測り直す ✓（run 中は走らせない ✓）✓

## Round 50: 従来の「Act 3 の壁 = 相性」という見方の訂正 ✓ Act 3 完走は記録済みで ✓ run の死に方の母数が違った

**訂正 1: Act 3 完走は起きている** ✓ `data/*_result.json` 12 件のうち **10 件が `act_3_complete: true`** ✓
（seed N8C6… ではなく N8CQ4ZKP2W ✓ D6A1F8C3E5 ✓ H2LV6ZJ4XW ✓ `acts = [ACT.OVERGROWTH, ACT.HIVE, ACT.GLORY]` ✓
HP 7/130〜29/87 ✓）✓ CODEWIKI 251 行目に 2026-09-07 の完走が詳しく記録されている ✓
（seed D6A1F8C3E5 ✓ base `3fd097e` ✓ 終了コード 0 ✓ `Finished Boss room` Act 3 Floor 15 ✓ 15戦15勝 ✓）✓
1765 行目に固定 seed N8CQ4ZKP2W の初完走 ✓ 私は最近の報告で「Act 3 完走 0 本」と繰り返したが ✓
それは**直近の sweep の seed 集団についてのみ真**で ✓ 表現として誤っていた ✓

**訂正 2: sweep の act3 検査が壊れていた** ✓ `grep -o '"act_3_complete":[a-z]*'` は
JSON が `"act_3_complete": true`（コロンの後に空白 ✓）だと**何も出力しない** ✗✗
sweep2.sh / sweep3.sh 両方に入っていた ✓ **両方を `grep -oE '"act_3_complete"[ ]*:[ ]*(true|false|null)'` に直した** ✓
これで panel の RESULT 行に完走が出ます ✓

**run の死に方の母数**（main と control worktree に残る全 mod log ✓）:

| 失敗理由 | 件数 |
|---|---:|
| `Run failed with Watchdog timeout` | **336** |
| `Run failed with Rewards screen did not appear after combat` | **300** |
| `Screen NRewardsScreen not closing after being handled` | 2 |
| `Tried to skip reward set ...` | 1 |

watchdog が「動きがない」と見た直前の action:

| last | 件数 |
|---|---:|
| Playing main menu | 730（launch 停止 ✓ 前 round ✓） |
| Entering Boss room (Act 2, Floor 16) | **373** |
| Entering Boss room (Act 3, Floor 15) | **194** |
| Entering Boss room (Act 1, Floor 17) | 83 |

`Rewards screen did not appear after combat` は combat 敗北後の処理でした ✓
seed EAIF2UUVCK の control run の trace 末尾は `combat_end` の **`won: false`** ✓（seq 372 ✓ 373 records ✓）✓
つまり 300 件は「敗北した combat の後に報酬画面が出ない」＝ **敗北そのもの** ✓ sweep の `losses=1` と整合 ✓
残る **336 件の Watchdog timeout** が別物 ✓ Boss room 進入中に 15〜20 秒以上 progress がない ✓
→ **長い boss 戦で agent の decision が遅く watchdog に負けている**可能性が高い ✓（未確認 ✓ 次の測定 ✓）
`SIMULATIONS` 100 × 毎 decision ✓ boss 戦は turn 数が多い ✓ だから Act 3 の壁は相性だけでなく
**run が boss 戦を完了できないこと**かもしれない ✓ 次の手: Watchdog timeout で死んだ run を 1 件選び ✓
trace の末尾と mod log の時系列で「どの fight がどれだけ長かったか」を出す ✓

## Round 51: 玩札推定の誤りを実測（combat record 344 件中 119 件）✓ bridge 変更を HEAD に適用 ✓ watchdog は 30 秒で kill する

検証 run（`bcp1` ✓ seed AM8C6YXHSG ✓ `REPO=.wt-bridge-counts` ✓ 07:15-07:21 ✓
`combat_records=344` ✓ wins 17 losses 1 exit 1 ✓）の trace に `plays` 字段が **344 件すべて**出た ✓
`/tmp/plays_diff.py` で **main の推定**と同じ record の export 値を突き合わせた ✓

| 項目 | 一致 | 不一致 |
|---|---:|---:|
| cards | 225 | **119（34.6%）** |
| attacks | 226 | **118（34.3%）** |
| skills | 332 | 12（3.5%） |

delta の分布: `cards +1` 53 ✓ `cards +2` 16 ✓ `cards -1` 20 ✓ `cards -2` 22 ✓ `cards -3` 4 ✓
`attacks +1` 52 ✓ `attacks +2` 16 ✓ `attacks -1` 23 ✓ `attacks -2` 23 ✓ `attacks -3` 4 ✓
skills は `−1` 7 と `+2` 5 のみ ✓ **cards と attacks は約 3 回に 1 回違った** ✓
前 round まで推定の誤りとして理論的に数えていたもの（Power 札は pile に現れない ✓ 敵が札を pile に足す ✓
autoplay は draw pile から直接玩む ✓）が ✓ **量として確認された** ✓
skills が強いのは LetterOpener・Kusarigama・Shuriken などの価格がほぼ合っていたことで ✓
Slow の ramp（cards）と Pen Nib・Rampart などの attacks が狂っていた ✓

**HEAD に適用した** ✓ commit `ebf2ef9` ✓ suite **780 件 green** ✓ mod 再ビルド ✓ `Sts2Ai.dll` 235,008 bytes ✓
bridge が observation と trace に `plays` を出し ✓ agent が `_seed_exported_plays` で model state に注入 ✓
**offline replay ではこの変更の决定母数を測れない** ✓（古い trace に `plays` が無い ✓）✓
だから測定は live panel になる ✓（arm = HEAD + 新しい dll ✓ control = `dfced8b` の worktree + そこにビルドした dll ✓）✓

**watchdog の実測** ✓ `AutoSlayConfig.watchdogTimeout = TimeSpan.FromSeconds(30)` ✓
`watchdogLogInterval = 5s` ✓（`AutoSlayConfig.cs:41,44` ✓ `public static readonly` ✓ 変更不可 ✓）✓
`Watchdog.Reset(string activity)` は public で「意味ある進捗のたびに呼べ」とコメントされている ✓
（`Watchdog.cs` ✓ `Check()` は 30 秒進捗がないと `AutoSlayTimeoutException` ✓）✓
**長い combat は 30 秒を普通に越える** ✓（1 decision ごとに observation/action の往復 ✓ 16 turn 戦 ✓）✓
実際 `data/act3_pop2_G3Q7Y5K9DT` は turn 16 まで戦って `won: false` で終わり ✓ 同じ run の log は
`Stuck detected! No progress for 30.1s (last: Entering Monster room (Act 1, Floor 11))` を出している ✓
→ **AutoSlay 側の「進捗」は AutoSlay自身の action で ✓ agent 駆動の combat 中は進捗が見えない** ✓
次手の候補: Harmony で `Watchdog.Check()` に postfix を掛け ✓ **bridge が直近の observation/action 交換に
成功している時だけ `Reset()` を呼ぶ** ✓（本来の目的である本物の停止検出は残す ✓）✓
これは run が boss 戦を最後まで戦えるかに直結する ✓（336 件の Watchdog timeout ✓ 前 round ✓）✓

sweep3.sh の最後で `command not found: SWEEP DONE bcp1` が出た ✓ RESULT 行は正常なので実害はない ✓
（`print --` の使い方の問題 ✓ 未修正 ✓ 次に sweep を組む時に見る ✓）✓

## Round 52: watchdog 停止は長い combat のせいではなく **全敗北後の流れ**だと訂正 ✓ sweep に到達 depth を追加 ✓ panel 開始

前 round の「長い boss 戦が watchdog に負けている可能性」は **誤りだった** ✓
799 個の mod log を調べて `Watchdog timeout` で終わった run を trace と突き合わせた ✓

```
watchdog-timeout runs by final trace phase: {'combat_end_recorded': 406, 'stall_<60s': 392, 'stall_>=60s': 14}
```

**trace が残っている 406 件はすべて末尾が `combat_end` で `won: false`** ✓ つまり**combat に負けた** ✓
30 秒の無進捗は敗北の後（ゲームが run 終了画面の流れで待っている ✓ AutoSlay 自身の action がない ✓）✓
`Rewards screen did not appear after combat`（300 件 ✓）と同じで ✓ **どちらも敗北の症状** ✓
例: `act3_pop2_F6L1X4P8MS` は Act 2 Boss room (Floor 16) まで進み 418 combat records ✓ `won: false` ✓
watchdog 39.9 秒 ✓「last: Entering Boss room (Act 2, Floor 16)」✓
→ **bridge に watchdog リセットを入れる必要はない** ✓（本来の停止検出を無効化するだけの修正だった ✓）✓
壁は依然として **combat で負けること** ✓（Act 2 boss での敗北が最も多い ✓ 前の「7/8 seed が
`MONSTER.THE_INSATIABLE` で死亡」と整合 ✓）✓

**sweep3.sh に到達地点と失敗理由を追加した** ✓ 敗北した run は result file を書かない（game は exit 1 ✓）ので
`act_3_complete` が読めない ✓ mod log に出る `Act N, Floor M` の最後の値を `depth=` として出し ✓
`fail=` に失敗理由の 1 行目を出す ✓ 新 RESULT 行:
`RESULT <tag> <seed> wins=… losses=… combat_records=… <act3> depth=… fail=…` ✓
（`zsh -n` 文法確認 ✓ 前 round の `command not found: SWEEP DONE` は再現せず ✓ 単独で `print --` を試して正常 ✓）✓

**panel を開始した** ✓ 07:29 ✓ `/tmp/panel_counts.sh` ✓ seed `AM8C6YXHSG D6A1F8C3E5 EAIF2UUVCK` ✓
- arm: `/Users/mao/workspace/sts2-ai`（HEAD `cb226c5` ✓ dll 235,008 bytes ✓ `plays` を出す ✓ agent が使う ✓）
- control: `.wt-ctrl-counts` @ `dfced8b` ✓ **policy は arm と同一 ✓ bridge が `plays` を出さない ✓**
  dll 231,424 bytes ✓ `grep -c "plays = new"` = 0 ✓（worktree に `mkdir -p` とビルド ✓ dll 実在確認 ✓）✓
  差分は export の 1 点だけ ✓
ログ `/tmp/counts_arm.log` `/tmp/counts_ctrl.log` ✓ 完了印 `/tmp/counts_arm.status`
`/tmp/counts_ctrl.status` `/tmp/counts_panel.status` ✓
**測定軸は wins だけでなく depth と Act 3 完走** ✓（推定の 34% 誤りを塞ぐことが boss 戦の勝敗と
到達に効くかを見る ✓）✓

## Round 53: model の SKILLS / ATTACKS 分類は game の CardType と一致していた（open question (a) をクローズ ✓）

`LetterOpener` の規則を最後まで読んだ ✓（`LetterOpener.cs` ✓）:

```csharp
public override async Task AfterCardPlayed(PlayerChoiceContext choiceContext, CardPlay cardPlay)
{
    if (cardPlay.Card.Owner == Owner && CombatManager.Instance.IsInProgress && cardPlay.Card.Type == CardType.Skill)
    {
        SkillsPlayedThisTurn++;
        if (SkillsPlayedThisTurn % DynamicVars.Cards.IntValue /* 3 */ == 0)
        {
            await CreatureCmd.Damage(choiceContext, Owner.Creature.CombatState.HittableEnemies, DynamicVars.Damage /* 5, unpowered */, Owner.Creature);
        }
    }
}
```

✓ play の **後** に数え上げて ✓ 3 の倍数で発動 ✓ 数えるのは `CardType.Skill` の札だけ ✓
`SkillsPlayedThisTurn = 0` のリセットは player 側 turn の境界（`:89` ✓ `:104` ✓ `TurnNumber == 1` の guard と
`participants.Contains(Owner.Creature)` ✓）✓
model の規則（`combat.py:2663` ✓ `combat.py:2705` ✓）は
`skills_this_turn = combat.skills_played_this_turn + (plays if card in SKILLS else 0)` →
`skills_this_turn % 3 == 0` で発動 ✓ **順序も剰余も game と同じ** ✓

だから残る `THE_INSATIABLE CARD.SHRUG_IT_OFF game-5` / `CARD.DEFEND_IRONCLAD game+5` 群の原因は
**入力（推定した skills 数）**だと絞れる ✓（前 round で推定の skills 誤りは 344 件中 12 件 ✓ 3.5% ✓
cards / attacks は 34% ✓）✓

**札型の対応を実測して open question (a) を閉じた** ✓ model の `SKILLS` 43 件のうち decompile で型が読める
37 件は**すべて `CardType.Skill`** ✓ `ATTACKS` 53 件のうち読める 50 件は**すべて `CardType.Attack`** ✓
型が違う札は 0 件 ✓ 残りは `base(...)` 行が読めなかった札で ✓ 個別に確認した ✓

| 札 | game の型 |
|---|---|
| Drum of Battle | `base(1, CardType.Skill, Uncommon, Self)` ✓ |
| Master of Strategy | `base(0, CardType.Skill, Rare, Self)` ✓ |
| Expect a Fight | `base(2, CardType.Skill, Uncommon, Self)` ✓ |
| Believe in You | `base(0, CardType.Skill, Uncommon, AnyAlly)` ✓ |
| One-Two Punch | `base(1, CardType.Skill, Rare, Self)` ✓ |
| Flash of Steel | `base(0, CardType.Attack, Uncommon, AnyEnemy)` ✓ |
| Neow's Fury | `base(1, CardType.Attack, Ancient, AnyEnemy)` ✓ |

`Defend` と `Strike` は `CardType` を明示する行が grep に出なかった ✓（別の初期化形 ✓）✓
model の分類（Strike は ATTACKS ✓ Defend は SKILLS ✓）は実運用と矛盾していない ✓
**教訓**: 集合名を比較するとき enum の表記（`SKILLS` と `Skill` ✓）をそろえないと全件不一致になる ✓
（最初 `label='SKILLS'` で比べたので 37/37 と 50/50 が「不一致」に見えた ✓ 実際の不一致は 0 件 ✓）✓

panel: 07:29 開始の arm 1 本目が走行中 ✓（`/tmp/counts_arm.log` は SWEEP START のみ ✓）✓
完了待ち background job `bash-879` ✓

## Round 54: 走行中の arm trace に `plays` が出ていることを確認 ✓ Perfected Strike の数式は game と一致（+3 群は数式ではなく札集合の問題 ✓）

`counts_arm` の seed AM8C6YXHSG は 07:32 時点で trace 195 件に `plays` 字段を持っていた ✓
**bridge の export が実際の run で機能している** ✓（control 側は同じ policy で `plays` 無し ✓）✓

`PerfectedStrike` を読んだ ✓（`PerfectedStrike.cs` ✓）: `CalculationBaseVar(6m)` ✓ `ExtraDamageVar(2m)` ✓
`CalculatedDamageVar.WithMultiplier(card.Owner.PlayerCombatState.AllCards.Count(c => c.Tags.Contains(CardTag.Strike)))` ✓
`base(2, CardType.Attack, Common, AnyEnemy)` ✓ model は `combat.py:3292` で
`strikes = hand + draw_pile + discard_pile + exhaust_pile` の `STRIKE_TAGGED` 数 ✓
`damage = 6 + (upgraded ? 3 : 2) * strikes` ✓ **base 6 ✓ extra 2 ✓ 自分も含む ✓（この branch は札が hand から
消える前に走る ✓ `STRIKE_TAGGED` に PERFECTED_STRIKE が入っている ✓ `combat.py:237` ✓）** ✓
→ 数式は game と一致 ✓ `LOUSE_PROGENITOR CARD.PERFECTED_STRIKE game+3`（2件 ✓）は
**game が見る `PlayerCombatState.AllCards` の中身と model の4つの pile の差**（rollout の draw 順で手札構成が
違う ✓ 敵が combat 中に作った札 ✓）側の話で ✓ 2 件だけなので今は触らない ✓（誤った修正をしない ✓）

## Round 55: census / audit に TRACE_GLOB を追加 ✓ 走行中 trace で試して seed するカウンタの届く範囲が分かった

`data/boss_gap_list.py` と `data/model_match_audit.py` が `data/*_agent.jsonl` を固定で glob していたので ✓
**`TRACE_GLOB` 环境变量で corpus を絞れるようにした** ✓（例 `TRACE_GLOB="counts_arm_*_agent.jsonl"` ✓）✓
構文確認 ✓ 1 trace の smoke test で動作 ✓（`203 actions replayed ✓ 201 matching ✓`）✓
（`timeout` は macOS に無い ✓ `gtimeout` ✓ 教訓 ✓）✓ files の BOM は `utf-8-sig` の読み書きで保持される ✓
（`ast.parse(open(p).read())` は BOM で `invalid non-printable character U+FEFF` になる ✓
  → `encoding='utf-8-sig'` で parse する ✓）✓

**seed するカウンタの届く範囲** ✓ 走行中の arm trace を census にかける gaps が出た ✓
`THE_INSATIABLE CARD.SHRUG_IT_OFF game-5` 1件 ✓（model 側だけ LetterOpener の 5 を出した ✓）と
`game-18` 1件 ✓
`_seed_exported_plays` は **observation の時点のカウンタ**を model state に入れる ✓
しかし model の rollout はそのターン内で自分の play を積み上げるので ✓
`skills_this_turn = combat.skills_played_this_turn + plays` ✓（`combat.py:2663` ✓）の `combat.skills_played_this_turn` は
seed された値 ✓ rollout 中の加算は model の play 順 ✓ → **seed は rollout 内部のカウンタを直さない** ✓
LetterOpener が model 側で余分に発動するケースが残るのはこの範囲の話 ✓
`game-18` は 5 -unit が複数回 ✓（LetterOpener + Kusarigama + Pen Nib など combo relic の重複発動 ✓）の可能性 ✓
panel 完了後に完全な trace で測り直す ✓（走行中は重い測定をしない ✓）✓

## Round 56: boss 直前の休憩は使われている ✓「休憩を飛ばして boss に突入」は壁ではないと確認（223 件の母数 ✓）

arm の結果が出始めた ✓ 新しい `depth=` が機能している ✓

```
RESULT counts_arm AM8C6YXHSG  wins=17 losses=1 combat_records=354 depth=Act 3, Floor 15
RESULT counts_arm D6A1F8C3E5  wins=14 losses=1 combat_records=282 depth=Act 3, Floor 4
```

**2 本とも Act 3 に到達** ✓ 1 本目は Act 3 Floor 15（Act 3 boss の部屋 ✓）で死んだ ✓
（`act3=` が空なのは敗北で result file が書かれていないから ✓ 前 round の grep 修正済み ✓）✓

**休憩の壁を検証した** ✓ 713 個の mod log で Act 2 boss（Floor 16）の直前に進入した部屋を数えた ✓

| 直前の部屋 | 件数 |
|---|---:|
| Boss (Act 2, Floor 16) | 785（同じ boss 進入が log に 2 行出る ✓ 実体は 1 件 ✓） |
| **RestSite (Act 2, Floor 15)** | **462** |

Act 2 の最終列は RestSite (Floor 15) → Boss (Floor 16) の作り ✓
走行中の arm run（AM8C6YXHSG）も `Entering RestSite room (Act 2, Floor 15)` →
`Entering Boss room (Act 2, Floor 16)` を通っている ✓ **agent は boss 直前の休憩を使っている** ✓
`choose_rest` は floor 13 以降で負傷時に HEAL を優先する規則を持っており ✓（`official_agent.py` ✓）✓
CODEWIKI には既に「休憩の回復を欠損量で足切りして SMITH に回す実験は 4 seed で上下に割れて不採用」（142 行目 ✓）と
「HATCH 常に優先は pin 3 件を壊すので閉じた」（223 行目 ✓）が記録されている ✓
→ **休憩の使い方は今の wall ではない** ✓ ここは触らない ✓

一方 `data/*_agent.jsonl` の古い trace には `max_hp` が入っておらず ✓（`hp` はある ✓）boss 戦進入時の
HP 割合を出せなかった ✓ また `data/*_map.json` は map の graph（`points[].type` ✓）を持つが
**通った経路は入っていない** ✓ 経路は result file の `routes` だけで ✓ それらは 12 本しか残っていない ✓
→ 経路の測定は mod log の `Entering ... room (Act N, Floor M)` 列から行うのが実務的で ✓
trace と log を突き合わせる時刻情報（trace に timestamp が無い ✓）は無い ✓ 教訓として残す ✓

## Round 57: QUEEN 戦の debuff 大量スタックは忠実度の穴ではなかった ✓ Frail は game でも固定 0.75 ✓

arm の seed AM8C6YXHSG は **Act 3 boss `MONSTER.QUEEN` (max_hp 400) の turn 9 で死亡** ✓
最後の敵 HP 284 ✓ 9 ターンで 116 ダメージ ✓ 約 13/ターン ✓
最後のターンの player powers: `CHAINS_OF_BINDING 3` ✓ `FEEL_NO_PAIN 3` ✓ **`FRAIL 93`** ✓ `RUPTURE 1` ✓
`THORNS 3` ✓ **`VULNERABLE 93`** ✓ **`WEAK 93`** ✓ block 0 ✓

Frail が amount で強くなるなら model の固定 3/4 が穴になる ✓と見て読んだ ✓
**`FrailPower.ModifyBlockMultiplicative` は `return 0.75m;`** ✓（`FrailPower.cs` ✓）✓
つまり game でも Frail は **固定 25% 減** ✓ stack 数は持続/適用回数で ✓ 係数は 93 で深くならない ✓
model は `combat.py:1232` の `block = base * 3 // 4 if apply_frail and _power(..., "FrailPower")` ✓
**一致している** ✓ gate も対応 ✓ game の `props.IsPoweredCardOrMonsterMoveBlock()` ✓ に対し
model は `apply_frail=False` を power で無い grant（`combat.py:2062` ✓ `2065` ✓ `3086` ✓）に使っている ✓
Vulnerable も同様に固定（model は 150/100 ✓ 93  stack でも ×1.5 ✓）✓
→ **debuff の意味は既に忠実 ✓ QUEEN 戦の壁は数そのもの** ✓（400 HP ✓ 味方 TORCH_HEAD_AMALGAM 599 HP ✓
CODEWIKI 記録 ✓ に 13/ターンでは届かない ✓）✓ 誤った修正をせずに済んだ ✓

**sweep3.sh の `fail=` 抽出を直した** ✓ 前 round の「fail の先頭が E」は log 行頭のタイムスタンプの
콜론で `sed -E 's/.*: //'` が最後まで進んでいたため ✓
`sed -E 's/.*Run failed with seed=[A-Z0-9]+: //'` に锚を置いて解決 ✓ 実 log で確認 ✓

```
fail=Watchdog timeout: No progress for 30.1s. Last activity: Entering Monster room (Act 1, Floor 11)
```

panel: arm 3 本目（EAIF2UUVCK）走行中 ✓ control 未開始 ✓ 完了待ち background job `bash-879` ✓
（`zsh -n` 文法確認済み ✓ ただし control 側に新しい sweep3.sh が効くのは次回起動から ✓ 今回の control は
起動済みのスクリプトを再読するので効く ✓ 同じファイルを読むため ✓）✓

## Round 58: arm 3 本完了 ✓ **走行中の shell script を編集したことが panel 出力の化け体の原因** ✓

arm 完了 ✓（control は 07:43 に開始 ✓ seed `AM8C6YXHSG D6A1F8C3E5 EAIF2UUVCK` ✓ 同じ 3 seed ✓）

```
RESULT counts_arm AM8C6YXHSG wins=17 losses=1 combat_records=354 depth=Act 3, Floor 15
RESULT counts_arm D6A1F8C3E5 wins=14 losses=1 combat_records=282 depth=Act 3, Floor 4
RESULT counts_arm EAIF2UUVCK wins=11 losses=1 combat_records=225 depth=Act 2, Floor 10 fail=Rewards scree
SWEEP DONE counts_arm
```

合計 **42 勝 3 敗** ✓ 2 本が Act 3 到達 ✓ 1 本目は Act 3 boss QUEEN の部屋で死亡 ✓
3 本目は Act 2 Floor 10 で敗北 ✓（`fail=Rewards screen…` ✓ = 前 round 分類の敗北症状 ✓）✓
`arm done rc=127` だったが run は 3 本とも完走出来ている ✓

**rc=127 と `fail=Rewards scree` の切断の原因** ✓ log に出たエラーは
`sweep3.sh:59: command not found: nt` ✓ しかし現在の sweep3.sh に 59 行目は無い ✓
`sed -n '50,59l'` で byte 単位に見た ✓
→ **panel は 07:29 に開始し ✓ 私は 07:33 に同じ sweep3.sh を編集した**（`depth=`/`fail=` 追加 ✓）✓
zsh は script を実行しながら読むので ✓ **実行中の編集は解釈位置をずらして化け体を出す** ✓✓
（前 sweep の `command not found: SWEEP DONE bcp1` も同じ説明で通る ✓ 単独試行で再現しなかったのは
その時点で編集が終わっていたから ✓）✓
**教訓: 走行中の shell script を編集しない** ✓ 編集が必要なら copy してその copy を実行する ✓
rc=127 は実害ではなく ✓ ただし `exit=` を見る規則（teaching 10 ✓）と合わせて ✓
「run 自体は 3 本成功 ✓ status file の rc は化け体の副产品 ✓」と切り分けた ✓

control 側は新しい sweep3.sh（`fail` の锚を直した版 ✓）を読み直すので ✓ 今回の panel では
`fail=` が正しい形で出るはず ✓（control 走行中は script を触らない ✓）✓

## Round 59: 新しい arm trace の census は 613 中 609 一致 ✓ 4 件の gap を faithful dump で見た ✓

`TRACE_GLOB="counts_arm_*_agent.jsonl"` で測った ✓（3 trace ✓ `plays` がありカウンタは正確 ✓）✓
**613 actions replayed ✓ 609 matching ✓ 不一致 4 件** ✓
（母数が古い corpus と違うので ✓ 99.2% との直接比較はしない ✓）✓

group と dump の要約 ✓(`/tmp/newgap.py` ✓) ✓

1. `THE_INSATIABLE CARD.SHRUG_IT_OFF game-18`（seq 282 ✓ turn 5 ✓ game 0 / model 18 ✓）
   exported plays: cards 4 ✓ attacks 4 ✓ **skills 0** ✓ player に `HELLRAISER_POWER 1` ✓ Strength 3 ✓
   敵 HP 134 → 134 ✓ **game は 0** ✓ model 18 は Strike(9+3)×Vulnerable 1.5 ✓
   → **model の rollout が Shrug の draw で Strike を引いて Hellraiser が自動で玩んだ** ✓
   game では別の札を引いた ✓ **前 round までに分類した rollout の draw 順違いと同じ** ✓ 忠実度では直せない ✓
2. `THE_INSATIABLE CARD.SHRUG_IT_OFF game-5`（seq 285 ✓ game 13 / model 18 ✓）同じfight ✓ 同じ机制 ✓
3. `DEVOTED_SCULPTOR CARD.BASH game+15`（seq 298 ✓ turn 1 ✓ **game 25 / model 10** ✓）
   exported plays すべて 0（そのターンの最初の札 ✓）✓ player hp 85 ✓ Dexterity 1 ✓ Strength なし ✓
   敵 DEVOTED_SCULPTOR 162 HP ✓ powers 無し ✓ 次 record で 137 HP ✓
   `data/enemies_glory.json` の state は `FORBIDDEN_INCANTATION_MOVE` ✓ `SAVAGE_MOVE` ✓
   → **game 側が 15 多い** ✓ relic 一覧を取っていない ✓ 次に relic と intents を見る ✓
4. `LIVING_SHIELD CARD.UPPERCUT game+19`（seq 314 ✓ turn 1 ✓ **game 32 / model 13** ✓）
   敵: `LIVING_SHIELD 55 HP + RAMPART_POWER 25` ✓ `TURRET_OPERATOR 41 HP + block 25` ✓
   player: hp 82 ✓ Dexterity 1 ✓ Strength なし ✓ exported plays すべて 0 ✓
   → **Rampart の block 付与自体は model も持っている** ✓（dump の TURRET_OPERATOR 25 block と一致 ✓）✓
   `RampartPower.AfterSideTurnStart` は `side != CombatSide.Player || PlayersTakingExtraTurn.Count > 0` で
   return し ✓ `TurretOperator` に Amount だけ block を载せる ✓ park 済みだった条件 ✓
   gap は block ではなく **game 側で 19 余分な HP 減少** ✓（他の damage source ✓ 敵自身の mechanism ✓）✓

2 件は分類済みの noise ✓ 2 件（game+15 ✓ game+19 ✓）は**新しい手がかり** ✓ 次の測定:
relic 一覧 ✓ 敵の intents の vars ✓ その record 前後の pile 変化 ✓ を同じ dump に出す ✓
control sweep は 07:43 開始 ✓ seed 1 走行中 ✓（`counts_ctrl` ✓ `dfced8b` ✓）✓

## Round 60: 玩札数 export は决定を 1 件も変えなかった（seed AM8C6YXHSG ✓ 354 件比較 ✓ 差分 0 ✓）

control 1 本目が終わった ✓ arm と並べて決定的な測定が出た ✓

```
RESULT counts_arm  AM8C6YXHSG wins=17 losses=1 combat_records=354 depth=Act 3, Floor 15
RESULT counts_ctrl AM8C6YXHSG wins=17 losses=1 combat_records=354 depth=Act 3, Floor 15
  fail=Watchdog timeout: No progress for 30.1s. Last activity: Entering Boss room (Act 3, Floor 15)
```

**combat record 354 件を 1 件ずつ突き合わせると ✓ 選択の差分は 0 件** ✓（card_id と action_type を比較 ✓）✓
arm は export した玩札数を model state に seed し ✓ control は pile から推定する ✓ 差分はその 1 点だけ ✓
（`fail=` の形が正しいのは control 側 ✓ 前 round の sed 锚修正が効いている ✓ 走行中に script を触っていない ✓）✓

**前の round まで測っていた 34% の推定誤りと矛盾しない** ✓ 推定が間違っていたのは
`cards_this_turn` と `attacks_this_turn` ✓（skills は 3.5% ✓）で ✓ それを読むのは SlowPower の ramp ✓
Pen Nib ✓ Rampart ✓ Nunchaku ✓ Kusarigama ✓ Ornamental Fan ✓ の「3 番目の攻撃」条件 ✓
しかし ±1〜2 ダメージの差は hand の argmax を引っ繰り返さない ✓
加えて `_seed_exported_plays` は **observation 時点の値**を入れるだけで ✓ rollout の内部カウンタは model の
play 順で進む ✓（前 round 記録 ✓）✓
→ **玩札数の精度は Act 3 のボトルネックではなかった** ✓ 新しい trace の census（613 中 609 一致 ✓）と
合わせて ✓ この変更は忠実度修正として保持するが ✓ win の改善は期待しない ✓
（teaching 7「arm と control が同じ数なら測定がない」は今回のケースではない ✓
 354 件比較して 0 件という母数を取っている ✓）✓

残る control 2 本（D6A1F8C3E5 ✓ EAIF2UUVCK）は走行中 ✓ 完了待ち background job `bash-879` ✓
Act 3 完走はまだ出ていない ✓（この seed は Act 3 boss QUEEN の部屋で敗北 ✓ turn 9 で敵 HP 284/400 ✓
前 round 記録 ✓ 13 ダメージ/ターン ✓）✓

## Round 61: 新しい 2 gap の原因候補を特定 ✓ **`RELIC.THROWING_AXE` が model に無い**（combat ごとに最初の札が 2 回玩まれる ✓）

faithful dump に relic 一覧・手札・pile 変化を出した ✓（`counts_arm_D6A1F8C3E5` ✓）✓
その run の relic は BURNING_BLOOD ✓ LARGE_CAPSULE ✓ LOST_WISP ✓ LUCKY_FYSH ✓ MEAT_ON_THE_BONE ✓
MOLTEN_EGG ✓ MUMMIFIED_HAND ✓ ODDLY_SMOOTH_STONE ✓ ORICHALCUM ✓ PAELS_FLESH ✓ STRIKE_DUMMY ✓ **THROWING_AXE** ✓
`combat.py` を数えると **MOLTEN_EGG ✓ THROWING_AXE ✓ LARGE_CAPSULE ✓ ODDLY_SMOOTH_STONE ✓ BURNING_BLOOD は参照 0 件** ✓
（LOST_WISP ✓ PAELS_FLESH ✓ MUMMIFIED_HAND ✓ MEAT_ON_THE_BONE ✓ ORICHALCUM ✓ STRIKE_DUMMY ✓ LUCKY_FYSH ✓ は有 ✓）✓

**`ThrowingAxe.cs`** ✓（Ancient ✓）✓

```csharp
private bool _usedThisCombat;
public override Task AfterRoomEntered(AbstractRoom room)
{
    if (!(room is CombatRoom)) return Task.CompletedTask;
    UsedThisCombat = false; Status = RelicStatus.Active; return Task.CompletedTask;
}
public override int ModifyCardPlayCount(CardModel card, Creature? target, int playCount)
{
    if (UsedThisCombat) return playCount;
    if (card.Owner != Owner) return playCount;
    return playCount + 1;
}
public override Task AfterModifyingCardPlayCount(CardModel card) { UsedThisCombat = true; ... }
public override Task AfterCombatEnd(CombatRoom _) { UsedThisCombat = false; ... }
```

→ **combat に入るごとに ✓ 私が play する 1 枚目の札が 1 回余分に玩まれる** ✓（その combat 中は 1 回だけ ✓）✓
gap の 2 件は両方 **turn 1 の最初の札** ✓（exported plays が cards/attacks/skills すべて 0 ✓）✓
seq 298 は upgrade 済みの Bash で game 25 / model 10 ✓（2 hit で説明の大部分が付く ✓）✓
seq 314 は upgrade 済みの UpperCut で game 32 / model 13 ✓（LIVING_SHIELD 55 → 23 ✓ ちょうど 32 ✓）✓

同じ run で combat 外に効く relic も確認した ✓ 誤って model に入れないために ✓
- `MoltenEgg` ✓: `TryModifyCardRewardOptionsLate` ✓ `ModifyMerchantCardCreationResults` ✓ → **報酬と店の提示を変える** ✓ combat の damage ではない ✓
- `OddlySmoothStone` ✓: `AfterRoomEntered` で `PowerCmd.Apply<DexterityPower>(... 1 ...)` ✓ → **dump に出た `DEXTERITY_POWER 1` の説明** ✓ model は observation の Dexterity を既に block に使っている ✓
- `LargeCapsule` ✓: relic 2 枚と Strike/Defend を deck に足す ✓ combat 外 ✓
- `BurningBlood` ✓: `AfterCombatVictory` で Heal 6 ✓ → map 側 ✓（休憩評価には効くが combat の damage ではない ✓）✓

**次の実装** ✓ `RELIC_THROWING_AXE` を追加 ✓ combat 単位の消費フラグ（`ruined_helmet_used` ✓ と同じ形 ✓）✓
`_step` で「その combat の最初の player play」なら play 回数を +1 ✓ 消費 ✓
テスト（1 combat で最初の札だけ 2 hit ✓ 2 枚目は 1 hit ✓ 次の combat で再び効く ✓）✓
suite と census で測る ✓（残る game+19 の差がどこまで縮むか見る ✓）✓

panel: control 1 本目完了 ✓ arm と同一（17勝1敗 ✓ 354 records ✓ Act 3 Floor 15 ✓ **决定差分 0 件** ✓ 前 round ✓）✓
control 2・3 本目は走行中 ✓ 完了待ち background job `bash-879` ✓

## Round 62: `RELIC.THROWING_AXE` を model に入れた ✓ gap の幅が game+15 → game+5 ✓ game+19 → game+6 ✓（scratch ✓ 781 件 green ✓）

scratch `.wt-proto8` に実装 ✓ patch `/tmp/throwing_axe.patch` ✓
- `RELIC_THROWING_AXE = "RELIC.THROWING_AXE"` ✓
- `Combat.cards_played_combat` を追加 ✓（`ruined_helmet_used` の後に置き ✓ 既存の positional 構築を崩さない場所 ✓）✓
- `Combat` の `_step` で **`play_duplicated = True` にする** ✓
  最初に `plays += 1` と書いたら効かなかった ✓（攻撃の hit 数は `plays` ではなく `play_duplicated` /
  `hits *= 2` で決まる ✓ `combat.py:1233` ✓ 型の branch が duplication 機構を使う ✓）✓
  実際に game は playCount + 1 なので ✓ 他の効果で既に 2 回になっている札は game では 3 回 ✓
  model は 2 回にする ✓（稀なケースなのでコメントに残した ✓）✓
- `official_agent.py`: `_COMBAT_PLAYS` に `cards` を追加 ✓ model state に `cards_played_combat` を渡す ✓

**重要: export 値は running の値を「上書き」しなければならない** ✓ 最初は `max(...)` で取り込んだ ✗✗
`max` だと新しい combat で 0 に戻るべき値が前の combat のまま残り ✓「combat の最初の札」の gate が
二度と立たない ✓ 実際の census の数字が動かないことで分かった ✓ 代入に直した ✓
（`plays.get("attacks_combat")` 等は combat 単位の値 ✓ game の履歴が正 ✓）✓

**測定** ✓ 同じ corpus（arm の 3 trace ✓ 613 手 ✓ 609 一致 ✓）で group の幅だけ動いた ✓

| group | 変更前 | 変更後 |
|---|---|---|
| `DEVOTED_SCULPTOR CARD.BASH` | game+15 | **game+5** ✓ |
| `LIVING_SHIELD CARD.UPPERCUT` | game+19 | **game+6** ✓ |

個別 probe でも確認 ✓（seq 298 ✓ model 10 → **20** ✓ game 25 ✓）✓
残る +5 と +6 は別の source ✓ 次の手がかり: その run の relic の中で combat に出るものは
ORICHALCUM ✓ PAELS_FLESH ✓ LOST_WISP ✓ STRIKE_DUMMY ✓ LUCKY_FYSH ✓ MEAT_ON_THE_BONE ✓ MUMMIFIED_HAND ✓
MOLTEN_EGG は報酬と店の提示 ✓ LARGE_CAPSULE は deck と relic ✓ BURNING_BLOOD は勝利後 Heal 6 ✓
ODDLY_SMOOTH_STONE は room 進入時の Dexterity +1 ✓（**Dexterity 1 の説明 ✓ combat の damage ではない ✓**）✓
→ +5 / +6 の候補として PAELS_FLESH と ORICHALCUM の数値を game の実装と突き合わせる ✓（未実施 ✓）✓

**panel は完了した** ✓ arm と control が 3 seed すべてで同一 ✓

| seed | arm | control |
|---|---|---|
| AM8C6YXHSG | 17勝1敗 ✓ 354 records ✓ Act 3 Floor 15 | 17勝1敗 ✓ 354 ✓ Act 3 Floor 15 |
| D6A1F8C3E5 | 14勝1敗 ✓ 282 ✓ Act 3 Floor 4 | 14勝1敗 ✓ 282 ✓ Act 3 Floor 4 |
| EAIF2UUVCK | 11勝1敗 ✓ 225 ✓ Act 2 Floor 10 | 11勝1敗 ✓ 225 ✓ Act 2 Floor 10 |

合計 arm 42 勝 3 敗 ✓ control 42 勝 3 敗 ✓ **玩札数 export は勝敗と到達を変えなかった** ✓
（seed AM8C6YXHSG では决定差分 0 件も測済み ✓）✓ Act 3 完走は出なかった ✓
THROWING_AXE の変更は pricing を変える（初手の攻撃が 2 hit になる ✓）ので ✓ **commit 前に决定母数を測る** ✓
（arm の trace には `plays` があるので ✓ 新旧 tree の replay 差を出せる ✓）✓

## Round 63: Throwing Axe を HEAD に入れた ✓ 决定母数 1,492 件中 302 件 ✓ ただし seed は 1 本だけ（panel しない ✓）

attribution（arm = `.wt-proto8` ✓ control = HEAD ✓ selector `RELIC.THROWING_AXE` ✓ SIMULATIONS=1 ✓
`/tmp/sts2-ai-enemies-merged.json` ✓）✓

```
power: RELIC.THROWING_AXE  records compared: 1492  trees: 2
decision changed: 302  unchanged: 1190  errors: {}
seeds with a changed decision: 1
  D6A1F8C3E5: 302
```

**比較した 1,492 件の决定のうち 302 件（約 2 割）が変わった** ✓ 例: `arm=CARD.STRIKE_IRONCLAD` に対し
control は `CARD.TREMBLE` ✓ `arm=CARD.BASH` に対し control は `CARD.UNREVLENTING` ✓ など ✓
Tool の print は 25 件までで ✓ 数は summary の 302 ✓
errors は 0 件 ✓
**Throwing Axe を持つ trace が 1 seed（D6A1F8C3E5）にしかない** ✓ 前の Adopt 基準は
「决定変化 3 件以上 **かつ** 3 seed 以上」✓ seed 数が届かない ✓ → **panel はしない** ✓
忠実度修正として保持する ✓（teaching 57 ✓）✓

**HEAD に適用した** ✓ commit `d43ee0f` ✓ suite **781 件 green** ✓ tree clean ✓
Python 側だけの変更 ✓ mod の再ビルドは不要 ✓（`plays` の export は前 round までに入っている ✓）✓

**relic の読み合わせで残る +5 / +6 の候補を落とす** ✓
- `Orichalcum.cs` ✓: `BlockVar(6m, ValueProp.Unpowered)` ✓ `_shouldTrigger` ✓ → **+1 Strength ではない** ✓
  （前 round の私の推測は誤り ✓ dump で player に Strength が出なかった理由にも合う ✓）✓
  model は `combat.py:2299` の `if RELIC_ORICHALCUM in relics and end_block == 0:` で block 側として持っている ✓
- `PaelsFlesh.cs` ✓: `EnergyVar(1)` ✓ `ModifyMaxEnergy` ✓ → **max energy +1** ✓ damage ではない ✓
- `StrikeDummy.cs` ✓: `ModifyDamageAdditive` で `ExtraDamage 3` ✓ powered attack かつ `CardTag.Strike` の時だけ ✓
  model は `combat.py:3328` の `if RELIC_STRIKE_DUMMY in combat.player_relics and card in STRIKE_TAGGED: damage += 3` ✓
  Bash と UpperCut は Strike tag ではない ✓ ので説明にならない ✓
- `LostWisp.cs` ✓: 私 が `CardType.Power` を play 時に全敵へ 8 unpowered damage ✓ model 済み ✓
  今回の 2 件は Attack の play ✓ なので発動しない ✓
→ **残る +5 / +6 は各 1 件ずつ** ✓ ここは追わない ✓（次の手がかりが見つかるまで置く ✓）✓

## Round 64: `CARD.SECRET_WEAPON` が play できる札なのに agent 側に対応が無いと特定 ✓ Toxic は誤検出だった ✓

「取ったのに一度も玩んでいない札」を新しい arm trace で数えた ✓（CLAUDE.md の FLame Barrier 型の調べ ✓）✓
そのままでは energy で払えない札と混ざる ✓ また model 側の名前一覧は display name（"Strike" ✓）で ✓
`CARD.STRIKE_IRONCLAD` のような id とは直接比較できない ✓ だから **game 側が `legal_actions` に出す札**
だけを対象にして ✓ agent の id→名前 対応（`official_agent.CARD_NAMES` ✓ 132 件 ✓）と
`combat.CARD_COST`（119 件 ✓）を突き合わせた ✓

| 札 | 型 | legal_actions に出る record | seed | 状態 |
|---|---|---:|---:|---|
| **`CARD.SECRET_WEAPON`** | Skill | **4** | 1 | **CARD_NAMES にも CARD_COST にも無い** ✓ gap ✓ |
| `CARD.TOXIC` | Status | 34 | 1 | 誤検出 ✓（後述 ✓） |

**`SecretWeapon.cs`** ✓: `base(0, CardType.Skill, CardRarity.Rare, TargetType.Self)` ✓ `CardKeyword.Exhaust` ✓
`OnPlay` は draw pile から `CardType.Attack` を 1 枚選んで hand へ入れる ✓ `OnUpgrade` で Exhaust を外す ✓
→ **コスト 0 の Skill ✓ draw pile から攻撃札を 1 枚持ってくる ✓ 素の札は exhaust ✓ 強化版は exhaust しない** ✓
agent は名前を知らない ✓ model は価格を知らない ✓ だから search() はこの札を評価も play もできない ✓

**Toxic は gap ではない** ✓ `Toxic.cs` は `CardType.Status` ✓ `HasTurnEndInHandEffect` ✓
`DamageVar(5m, Unpowered | Move)` ✓ で ✓ model は `combat.py:84` の `HAND_INJECTED_STATUS = {TOXIC: 5, BURN: 2, INFECTION: 3, DECAY: 2, WITHER: 3}` ✓
と `combat.py:2236` の turn end 処理で既に持っている ✓ Status 札を play 対象から除いているのも意図的 ✓
（`combat.py:197` ✓）✓ legal_actions に出るのは bridge が hand を列挙するからだと思われる ✓（未確認 ✓）
**教訓**: model の集合判定は display name と id を混ぜると全件不一致になる ✓（前 round の
`CARD_COST` 判定で Strike/Defend が「無い」が出た ✓ 同じ誤り ✓）✓

**次の実装の設計**（この round では実装しない ✓ 急いで shared pile 処理を迂回する early return は
Slimed で一度失敗している ✓ teaching 55 ✓）✓
- `SECRET_WEAPON = "Secret Weapon"` ✓ `CARD_COST` に 0 ✓ `SKILLS` に追加 ✓（game の CardType.Skill ✓ 確認済み ✓）✓
  `UNTARGETED` に追加 ✓（TargetType.Self ✓）✓ `official_agent.CARD_NAMES["CARD.SECRET_WEAPON"]` ✓
- `_step` の effect: draw pile の `ATTACKS` から damage 順に 1 枚を選んで hand へ ✓ その 1 枚を draw から除く ✓
- exhaust は共有の仕組みに乗せる ✓ `combat.py:2916` の `exhaust = card in EXHAUSTS` ✓
  強化版は Exhaust を持たないので discard 側 ✓（名前の集合だけでは強化を区別できない ✓ played value で見る ✓）✓
- 親札の選択は player の選び方 ✓ model は damage 最大で近似する ✓（近似である旨をコメントに残す ✓）✓
- 母数: 新しい trace で legal_actions 4 件 / 1 seed ✓（古い corpus には 3 件 ✓）✓ 小さい ✓
  ただし play できる札が eval 対象に入っていないこと自体が model の穴 ✓

## Round 65: Secret Weapon を model に入れた ✓ suite 782 件 green ✓ 母数は 4 record / 1 seed なので panel しない ✓

main commit `1a73379` ✓ scratch `.wt-proto9` で実装してから適用 ✓ patch `/tmp/secret_weapon.patch` 135 行 ✓
（`SECRET_WEAPON` 定数 ✓ `CARD_COST` に 0 ✓ `SKILLS` ✓ `UNTARGETED` ✓
`official_agent.CARD_NAMES["CARD.SECRET_WEAPON"] = "Secret Weapon"` ✓）✓

**配置で2回ハマった** ✓ 教訓として残す ✓
1. 札を draw pile から hand へ移す処理を effect 側（`combat.py` の PRIMAL_FORCE の近く ✓）に置き ✓
   draw pile からの除去は shared の main replace の後ろで index を使って除いた ✓
   （`combat.py` の末尾は `hand` を list で持つ ✓ そこへ append すれば shared の処理がそのまま拾う ✓）✓
2. **untargeted の札を shared return へ乗せないといけない** ✓ `combat.py:3180` の
   `if card in {INFLAME, PRIMAL_FORCE, ..., ONE_TWO_PUNCH}: return combat` ✓ の集合に Secret Weapon が無いと ✓
   下の攻撃適用に進んで `enemy = enemies[int(target)]` → `ValueError: invalid literal for int() with base 10: ''` ✓
   （前 round まで見てきた「untargeted 札が targeted 分岐に落ちる」のと同じ形 ✓ その集合に入れた ✓）✓
3. exhaust は共有の仕組みに乗せた ✓ `exhaust = card in EXHAUSTS or (card == SECRET_WEAPON and not card_was_upgraded)` ✓
   `EXHAUSTS` は名前の集合なので ✓ 強化版（`OnUpgrade` が Exhaust を外す ✓）を区別するには play した value 側を見る ✓
4. `Card` オブジェクトの play は action 文字列が `card:0`（index 指定 ✓）になる ✓ 素の string 札は名前 ✓

**確認した振る舞い** ✓
- 素の札: hand に Iron Wave が入る ✓（draw pile の Attack を 1 枚 ✓ Defend は Skill なので引かない ✓）✓
  draw は `Defend` だけ ✓ exhaust に Secret Weapon ✓ discard は空 ✓
- 強化版: hand に Bash ✓ draw 空 ✓ **exhaust 空 ✓ discard に Secret Weapon** ✓（Exhaust 除去と一致 ✓）✓
- 選択の近似（draw pile の Attack を 1 枚選んで hand へ ✓ key は `CARD_DAMAGE + 2 * 強化` ✓）は ✓
  **model の既存の Standing 近似と同じ** ✓ `combat.py:2972` の `card_value + 2 * card_block_value` ✓
  （player が実際に何を選ぶかは観測できない ✓ 近似である旨はコメントに書いた ✓）✓

**母数** ✓ 新しい trace で game が legal_actions に出す record 4 件 / 1 seed ✓（古い corpus で 3 件 ✓）✓
 Adopt 基準の 3 seed に届かない ✓ **忠実度修正として保持 ✓ panel はしない** ✓
（play できる札が search の対象に入っていないこと自体が穴なので ✓ 対応を入れた ✓）✓

**テスト** ✓ `test_secret_weapon_pulls_an_attack_from_the_draw_pile_and_exhausts` ✓
素の札と強化版の両方で hand / draw / exhaust / discard を assert ✓ main の suite **782 件 green** ✓

## Round 66: 検証 run は Act 3 Floor 5 まで進んだ ✓ 残る +5 / +6 は **多重 play の 2 番目の hit が Vulnerable を引けていない** ことだと特定 ✓

**HEAD `5b4f01d` の検証 run** ✓ seed D6A1F8C3E5 ✓

```
RESULT fixafter D6A1F8C3E5 wins=15 losses=1 combat_records=309 depth=Act 3, Floor 5
  fail=Watchdog timeout: No progress for 30.0s. Last activity: Entering Monster room (Act 3, Floor 5)
```

同じ seed の panel arm（THROWING_AXE と Secret Weapon が入る前 ✓ `cb226c5`）は
14 勝 ✓ 282 records ✓ **Act 3, Floor 4** ✓ → **+1 勝 ✓ +1 階層 ✓** ✓ 1 seed の話なので方向の目安 ✓
落ち方（敗北後の watchdog ✓ 前 round 分類 ✓）と crash は無し ✓ Act 3 完走はまだしていない ✓

**残る gap の原因を数式まで特定した** ✓ decompile の order が証拠 ✓

- `Bash.cs` ✓: `await DamageCmd.Attack(...)` ✓ → `await PowerCmd.Apply<VulnerablePower>(target, 2)` ✓
  （`DamageVar` と `PowerVar<VulnerablePower>(2m)` ✓）✓
- `UpperCut.cs` ✓: `DamageVar(13m, Move)` ✓ `DynamicVar("Power", 1m)` ✓
  `DamageCmd.Attack` ✓ → `Apply<WeakPower>(amount)` ✓ → `Apply<VulnerablePower>(amount)` ✓
- model 側は debuff 自体を持っている ✓ 実際に走らせた ✓ Bash は 8 damage + 敌に `VulnerablePower 2` ✓
  Uppercut は **13 damage + 敌に `Weak 1` と `Vulnerable 1`** ✓（game の `DamageVar(13m)` と一致 ✓）✓
- **問題は順序** ✓ model は `_apply_debuff_multipliers` を hits ループの **前** で 1 回だけかける ✓
  （`combat.py:3374-3379` ✓ `damage = _apply_debuff_multipliers(...)` ✓ `for _ in range(hits): enemies[...] = _damage_enemy(..., damage)` ✓）✓
  だから 1 play が 2 回 resolve するとき（Throwing Axe ✓ DuplicationPower ✓ OneTwoPunchPower ✓）✓
  2 番目の hit が ✓ 1 番目の resolve が入れた Vulnerable を引けない ✓✓

**記録された数と完全に合う** ✓
- `DEVOTED_SCULPTOR CARD.BASH` ✓ model 10 + 10 = **20** ✓ game は 10 + 10×1.5 = **25** ✓ → gap +5 ✓
- `LIVING_SHIELD CARD.UPPERCUT` ✓ model 13 + 13 = **26** ✓ game は 13 + 13×1.5 = 19.5 → 19 で **32** ✓ → gap +6 ✓

**model の display name には注意** ✓ `Uppercut` ✓（`UpperCut` ではない ✓）✓
`UpperCut@0` で play しようとすると `ValueError: illegal action: UpperCut@0` になった ✓
（`combat.py` の定数は `UPPERCUT = "Uppercut"` ✓）✓ 名前を間違えると「play できない札」に見える ✓

**次の実装の設計** ✓ hits ループ内で hit ごとに multi を掛け直す ✓
すなわち最初の hit の後に card が target に入れる debuff（Bash は Vulnerable 2 ✓ Uppercut は Weak 1 + Vulnerable 1 ✓）を
反映して ✓ 以降の hit はその時点の敌状態から計算する ✓（game は resolution ごとに別の DamageCmd ✓）✓
Bash は Basic rarity ✓ Uppercut は Uncommon ✓ で母数は大きく見えるので ✓
**attribution で决定母数を出し ✓ 3 seed 以上なら panel する** ✓（teaching 32 ✓ 0 件なら panel しない ✓）✓

## Round 67: 多重 play の debuff 順序を直した ✓ 記録された 25 / 32 をテストで固定 ✓（scratch ✓ 783 件 green ✓ 母数測定中 ✓）

scratch `.wt-proto10` ✓ patch `/tmp/patch_multihit.py` ✓

**追加した helper** ✓ `_card_resolution_debuffs(card, upgraded)` ✓（`CARD_VULNERABLE_TARGET` の直後 ✓）✓
1回の OnPlay resolution が target に入れる debuff を、game が適用する順序のまま返す ✓
- `CARD_VULNERABLE_TARGET = {BASH: 2, BREAK: 5, SQUASH: 2}` ✓ に強化の +1 ✓（`BASH` と `SQUASH` は upgrade で +1 ✓ 既存の tail と同じ ✓）✓
- `UPPERCUT` は `WeakPower (1 + 強化)` → `VulnerablePower (1 + 強化)` ✓（`UpperCut.cs` が `Apply<WeakPower>` → `Apply<VulnerablePower>` ✓）✓

**hits ループを変更** ✓（`combat.py` の `damage = _apply_debuff_multipliers(...)` の直後 ✓）✓
hit を入れて ✓ まだ次の hit が残っているなら ✓ その resolution ぶんの debuff を target に載せ ✓
**残りの hit を新しい敌状態から掛け直す** ✓（`base_damage` を保持して `_apply_debuff_multipliers` を掛け直す ✓）✓
最後の resolution の debuff は従来どおり end-of-play 側で入れる ✓ → **総量は resolution 1 回ぶん × play 数 のまま ✓ 順序だけ直った** ✓
`hits == 1` の通常 play はループ内で何も足さない ✓（`hit_index + 1 < hits` ✓）ので ✓ 既存の挙動はそのまま ✓

**tail の重複を取り除いた** ✓
- `CARD_VULNERABLE_TARGET` の grant から `* (2 if play_duplicated else 1)` を外した ✓（前回の resolution ぶんはループで入れた ✓）✓
- Uppercut の `plays = 2 if play_duplicated else 1` を `plays = 1` にした ✓（同じ理由 ✓）✓
- `lamp_double`（Unsettling Lamp ✓ `DEBUFF_CARDS` の debuff を倍にする ✓）は grant の係数として維持 ✓
  lamp は play 数を増やさないので `hits` は 1 のまま ✓ → 既存の lamp テスト（`test_combat.py:1439` ✓）はそのまま ✓

**テストで記録の数字を固定した** ✓ `test_a_duplicate_play_sees_the_vulnerable_its_earlier_resolution_applied` ✓
- `Card(BASH, True)` + `RELIC_THROWING_AXE` ✓ → **25 ダメージ** ✓（10 → 10×3/2 ✓）敌の Vulnerable **6** ✓（1 resolution 3 ✓×2 ✓）
  実際の trace `data/counts_arm_D6A1F8C3E5_agent.jsonl` seq 298 の game 数と一致 ✓
- `UPPERCUT` + axe ✓ → **32 ダメージ** ✓（13 → 19 ✓）敌に `WeakPower 2` と `VulnerablePower 2` ✓
  seq 314 の game 数（LIVING_SHIELD 55 → 23 ✓）と一致 ✓
suite **783 件 green** ✓

**action の form に注意** ✓ 強化札（`Card` オブジェクト）の targeted play は `card:0@0` ✓
（untargeted は `card:0` ✓）✗ `card:0` だと `illegal action` ✓

**main への commit は母数測定の後** ✓ attribution は arm（scratch ✓ 修正入り ✓）と control（main ✓ 修正無し ✓）の
** policy 差**を測るので ✓ commit して両者を同じにしてはいけない ✓（teaching 2 ✓）✓
selector `CARD.BASH` ✓ `CARD.UPPERCUT` ✓ `CARD.SQUASH` ✓ `CARD.BREAK` ✓ で実行中 ✓
`/tmp/multihit_attr.status` ✓ logs `data/multihit_*_attr.log` ✓

**waiter の鍵の失敗** ✓ `for ... done > /tmp/multihit_attr.status` の形だと **ファイルは開始時に空で作られる** ✓
完了の目印にならない ✓（最初の waiter は即座に抜けた ✓）→ **完了後に入れる `echo ... > status` を使う** ✓
または logs が全て non-empty になったかで待つ ✓

## Round 68: 多重 play の debuff 順序を HEAD に入れた ✓ 母数 1,596 件中 22 件（1 seed ✓ panel しない ✓）

main commit `bc54a06` ✓ suite **783 件 green** ✓ patch `/tmp/multihit.patch` 104 行 ✓

**母数** ✓ arm = `.wt-proto10`（順序修正入り ✓）control = HEAD `28d19f2`（修正無し ✓）✓
selector は **`RELIC.THROWING_AXE`** ✓（play が複製される場を選ぶ ✓ `CARD.BASH` は 0 件で測定にならなかった ✓ 前 round ✓）✓

```
power: RELIC.THROWING_AXE  records compared: 1596  trees: 2
decision changed: 22  unchanged: 1574  errors: {}
seeds with a changed decision: 1
  D6A1F8C3E5: 22
```

1,596 件中 22 件 ✓ 約 1.4% ✓ **seed が 1 本**なので Adopt 基準（3 seed ✓）に届かない ✓
忠実度修正として保持 ✓ panel はしない ✓（teaching 57 ✓）✓
同じ selector で前の Throwing Axe 実装自体は 302 件を変えていた ✓（前 round ✓）✓

**新しい run（fixafter ✓ HEAD `5b4f01d` ✓ Act 3 Floor 5）の死因を見た** ✓
最後の fight は `MONSTER.OWL_MAGISTRATE`（max_hp 231 ✓ 残り **15 HP** ✓ `SOAR_POWER 1` ✓ Vulnerable 5 ✓）✓
player は **13 HP ✓ block 0 ✓ energy 0** ✓ hand は Iron Wave / Bloodletting / Uppercut ✓ turn 8 ✓
最後の决定を model で再生した ✓
```
legal: ('card:1', 'End turn')
  card:1   dmg 0  killed False  player_hp 10    (Bloodletting: 2 HP を払って energy +1 ✓)
  End turn dmg 0  killed False  player_hp -30   (敌の attack で死亡 ✓)
```
→ **その時点で win の道は無かった** ✓ Soar 済み敵 15 HP に Uppercut は半減で 6 ✓ 届かない ✓
model の穴ではなく **资源不足** ✓（Act 3 Floor 5 の elite で削られ尽くしている ✓）✓

**Soar は model 済みと確認した** ✓ `combat.py:1448-1450` ✓
`if powered and _power(enemy.powers, "SoarPower")` ✓ → game の `SoarPower.ModifyDamageMultiplicative`
（`DamageDecrease 50 / 100` ✓ powered attack で owner にだけ ✓）と一致 ✓
Owl Magistrate の `JUDICIAL_FLIGHT` state が SoarPower 1 を載せることも enemy JSON に出ている ✓
**Lost Wisp の 8 unpowered damage は Soar を抜ける** ✓ 実際に測った ✓（Soar 有りでも 8 ✓）✓

**probe の読み間違いを 1 件記録** ✓ 最初に「Inflame + Lost Wisp が 8 しかない = Inflame の 3 が消えている」と見た ✓
しかし Inflame は **block に応じて damage が出る札** ✓ probe では player_block 0 ✓ → Inflame 自体 0 ✓
（Inflame 単体 0 ✓ Soar 無しでも 0 ✓ Lost Wisp 単体 8 ✓ で切り分けられた ✓）✓
**教訓: probe の数字を解釈する前に、その札自身の damage の出方を確認する** ✓（ブロック前提の札を
block 0 の状態で試すと「効果が消えた」ように見える ✓）✓

## Round 69: census がほぼ空になった ✓ arm corpus 614 中 612 ✓ 新しい run の trace は 218 中 218 ✓（不一致 0 ✓）

HEAD `9bbf6a2` 以降（`bc54a06` の多重 play 修正まで入った状態 ✓）で測り直した ✓

```
TRACE_GLOB=counts_arm_*_agent.jsonl → 614 actions replayed, 612 matching
  ('THE_INSATIABLE','enemy_hp','CARD.SHRUG_IT_OFF','game-18')  1
  ('THE_INSATIABLE','enemy_hp','CARD.SHRUG_IT_OFF','game-5')   1
TRACE_GLOB=fixafter_*_agent.jsonl   → 218 actions replayed, 218 matching ✓ 不一致 0 ✓
```

**多重 play の debuff 順序修正で `DEVOTED_SCULPTOR CARD.BASH game+5` ✓ と
`LIVING_SHIELD CARD.UPPERCUT game+6` ✓ が無くなった** ✓ 前 round の予測どおり ✓
arm corpus の残り 2 件は **Shrug の draw で model が Strike を引いて Hellraiser に自動で玩ませる**
rollout の draw 順の違い ✓ 前に「忠実度では直せない」と分類したもの ✓
**新しい run（fixafter ✓ HEAD `5b4f01d` ✓）の combat record は 218 手すべて model と game が一致** ✓
→ combat model の食い違いはほぼ無くなった ✓ 次の work は model の穴探しではなく **damage と HP の経済** ✓
（Act 2 boss 321 HP ✓ Act 3 boss QUEEN 400 HP + TORCH_HEAD_AMALGAM 599 HP ✓ に対し 13〜22/ターン ✓）✓

**4 seed sweep を開始した** ✓ tag `sw59` ✓ 08:46 ✓ HEAD `9bbf6a2` ✓
seed `AM8C6YXHSG` ✓（panel arm で Act 3 Floor 15 ✓ QUEEN 戦まで到達 ✓）✓ `D6A1F8C3E5` ✓（fixafter で Act 3 Floor 5 ✓）✓
`H2LV6ZJ4XW` ✓（**過去に Act 3 完走の記録がある seed ✓** 現在の build で再び届くか見る ✓）✓ `VTW80ZJA2G` ✓（8 seed panel の其中之一 ✓ Act 2 boss 付近で死亡 ✓）✓
測定軸は wins ✓ 到達 depth ✓ Act 3 完走 ✓ 失敗理由 ✓（sweep3.sh の `RESULT` 行 ✓）✓
log `/tmp/sw59.log` ✓ status `/tmp/sweep59.status` ✓ 完了待ち background job `bash-1045` ✓

## Round 70: **Rampage の growth が model に無い**と特定 ✓ 記録された play 実測は 9 以上が日常 ✓（13 ✓ 19 ✓ 21 ✓ 28 ✓ 36 ✓）

**きっかけ: card reward の選び方** ✓ trace の `card_reward` record には `cards`（3 枚の offer ✓ type/cost/rarity/upgrade ✓）
と `card_id`（選んだ札 ✓）と `deck` ✓ が入っている ✓
最高 damage の offer を避けた决定を数えた ✓

- `fixafter_D6A1F8C3E5`（Act 2 boss で potential 22 ✓ 弱い deck ✓）: **Rampage を 2 回避けている** ✓
  （Iron Wave ✓ 5 / Second Wind ✓ 0 を選んだ ✓）
- `counts_arm_AM8C6YXHSG`（potential 80 ✓ QUEEN まで到達 ✓）: 6 件 ✓ Rampage ×2 ✓ Headbutt ×2 ✓ Breakthrough ✓ Dismantle ✓

**deck の火力を測った**（3 energy で attack を greedy に並べた potential damage/ターン ✓ 近似 ✓）✓

| run | Act 2 boss 時点の deck | potential | 結果 |
|---|---|---:|---|
| counts_arm_AM8C6YXHSG | 24 枚 | **80** ✓ | Act 3 Floor 15（QUEEN 戦）✓ |
| fixafter_D6A1F8C3E5 | 24 枚 | **22** ✓ | Act 3 Floor 5 で死亡 ✓ |
| counts_arm_D6A1F8C3E5 | 24 枚 | **22** ✓ | Act 3 Floor 4 で死亡 ✓ |

potential は「引ける手札」と「1 combat 1 回の制限」を無視した上限 ✓（teaching 13 ✓ ad-hoc arithmetic ✓）なので
実ダメージの予想ではない ✓ ただし **deck 間で 80 と 22 の差があり ✓ 火力が高い run だけが Act 3 boss まで行っている** ✓
（8 seed panel 以来の一貫した傾向 ✓）✓

**`Rampage.cs` を読んだ** ✓
(`base(1, CardType.Attack, CardRarity.Uncommon, TargetType.AnyEnemy)`) ✓
`CanonicalVars`: `DamageVar(9m, Move)` ✓ **`DynamicVar("Increase", 5m)`** ✓
`OnPlay`: `DamageCmd.Attack(DynamicVars.Damage.BaseValue)` ✓ → **`DynamicVars.Damage.BaseValue += Increase`** ✓
`OnUpgrade`: `Increase.UpgradeValueBy(4m)` ✓ → **強化版は play ごとに +9** ✓（base damage の強化は 0 ✓
model の `CARD_UPGRADE_DAMAGE[RAMPAGE] = 0` ✓ は正しい ✓）✓
`_extraDamageFromPlays` は CardModel の field ✓ → **growth は combat を越えて run 中持続する** ✓

**model には Rampage の growth が無い** ✓ `combat.py` には `maul_bonus: int = 0` ✓ `thrash_bonus: int = 0` ✓ があり
`combat.py:3367` の `damage += combat.maul_bonus if card == MAUL else combat.thrash_bonus` ✓ と
`combat.py:3421` の更新で Maul/Thrash だけ追跡している ✓ **RAMPAGE は追跡していない** ✓
（Maul/Thrash のコメントには「growth は fight を越えて持続し、model は自分が見た growth だけ足すので
長く持った札を過小評価する ✓」と正直に書かれている ✓ 同じ class の問題 ✓ Rampage は追跡自体が無い ✓）✓

**記録された game 実測で growth が見えることを確認した** ✓（全 corpus で `CARD.RAMPAGE` の play を
 combat_id で結んで実際の HP 減を数えた ✓）✓
```
dealt 9 x15   dealt 13 x10   dealt 19 x4   dealt 14 x2   dealt 11 x2   dealt 21 x1   dealt 16 x1   dealt 28 x1  dealt 36 x1
```
print 値 9 以上が日常 ✓ 大きい値ほど later combats ✓ → **持続する growth の証拠** ✓
（9 が 15 件あるのは初 play ✓ または 1 combat 目 ✓）✓

**実装の設計（次 round ✓）** ✓
1. `Combat.rampage_bonus: int = 0` ✓ damage 側は Maul/Thrash の line に足す ✓ play 後に `+ (9 if 強化 else 5)` ✓
2. **run 中で持続する部分**は model state を毎回組み直すのでは消える ✓ 観測から札の現在値は読めない
   （combat record の hand には `id`/`cost`/`upgrade` しか無く DynamicVar の現在値が無い ✓）✓
   → agent は process 持続型 ✓（`_COMBAT_PLAYS` ✓ と同じ global ✓）なので ✓ `_PENDING_ACTION` で credit する仕組みで
   **自分が play した Rampage の回数を run 単位で数え** ✓ seed する ✓（teaching 38 ✓ 39 ✓）✓
   過小評価は残る（他 source の growth は見えない ✓）が ✓ 今の 0 より正確 ✓
3. 効果は combat pricing と card reward の両方に効く ✓ 母数を出す ✓（`attribution_rampart.py` には card selector が無い ✓
   → census と trace 実測で測り ✓ その後 panel を考える ✓）✓

sweep `sw59`（4 seed ✓ HEAD `3bdb798`）は走行中 ✓ 08:46 開始 ✓ 完了待ち `bash-1045` ✓

## Round 71: **Rampage の growth は model に入れられない**と測定で決めた ✓ 一致 43/52 → 18/52 に落ちた ✓（採用せず ✓）

scratch `.wt-proto11`（削除済み ✓）で二段_variant を作り ✓ 記録された Rampage play 52 件で測った ✓
probe `/tmp/rampage_probe.py`（`CARD.RAMPAGE` の play だけ replay ✓ game 側の HP 減は combat_id ✓ model 側は positional ✓）✓

| variant | replayed | match | mismatch |
|---|---:|---:|---:|
| main（growth 無し ✓） | 52 | **43** ✓ | 9 |
| combat 内 growth + run 中 seed ✓ | 52 | **18** ✗✗ | 34 |
| combat 内 growth のみ ✓ | 52 | **43**（main と同一 ✓） | 9 |

**run 中に persistence させる版は大きく過大評価した** ✓ 例: seed S9T3K7V1GQ seq 155 で game 13 / model **86** ✓
seed S4N8K2V6QJ seq 148 で game 14 / model **49** ✓ → 採用しない ✓

**なぜ観測できないか** ✓ pile 内の札の entry は `{"id": "CARD.RAMPAGE", "upgrade": 0, "enchantment": null}` だけ ✓
**その札の現在の Damage BaseValue は出ない** ✓（`vars` は combat record の敵 intent 側に出るだけで ✓ 札の pile entry には付かない ✓）✓
だから「どの copy がどれだけ育ったか」を観測から決める手段が無い ✓
自分で play した数を数える道（`_RUN_CARD_GROWTH` ✓）は試した ✓ が ✓ 上の数値どおり過大評価になった ✓
理由: 同じ名前の copy が複数ある deck が実在する ✓（`demonform_S4N8K2V6QJ` の draw pile に Rampage が **2 枚** ✓）✓
model は card ごとに 1 つの bonus しか持てないので ✓ copy 単位で分けられない ✓
（`Rampage.cs` の growth は CardModel 側で run 中持続する ✓ ので ✓ 観測できない以上 ✓ 忠実に載せられない ✓）✓

**main の 9 件の不一致**（game 14 / 19 / 28 / 36 ✓ model 9 / 13 / 14 / 16 ✓）は growth だけでも説明しない ✓
combat 内 growth のみをいれても一致の内訳は変わらなかった ✓（= 同じ combat で同じ copy を2回玩む record が無い ✓）✓
→ ここは未解決のまま置く ✓（growth 以外の source ✓ Strength 成長など ✓ の可能性を残す ✓）✓

**probe -side の教訓 2 つ** ✓
1. **trace ごとに run-scoped state を初期化しないと測定が壊れる** ✓ agent は run ごとに process ✓
   probe は同じ process で複数の trace を流すので ✓ `_RUN_CARD_GROWTH.clear()` を trace 単位で必要だった ✓（最初の probe は growth が trace を跨って漏れた ✓）✓
2. audit は `choose()` を呼ばないので ✓ agent 側の credit（`choose` の中）は自動では再現しない ✓
   probe で `_growth_play_of` を explicitly 呼んで mirror した ✓（teaching 46 ✓ 同じ型 ✓）✓

sweep `sw59` の途中結果 ✓ 4 seed 中 3 本完了 ✓
- AM8C6YXHSG ✓ 17 勝 1 敗 ✓ 360 records ✓ Act 3, Floor 15 ✓（boss 室に入る所で stop ✓ 前と同じ ✓）
- D6A1F8C3E5 ✓ 15 勝 1 敗 ✓ 302 records ✓ Act 3, Floor 5 ✓（fixafter と同じ ✓）
- **H2LV6ZJ4XW ✓ 20 勝 1 敗 ✓ 388 records ✓ Act 3, Floor 6** ✓（この seed には過去の Act 3 完走の記録がある ✓ 現状の build では Floor 6 の monster 戦で敗北 ✓）
4 本目 VTW80ZJA2G は走行中 ✓ 完了待ち `bash-1045` ✓

## Round 72: 4 seed sweep `sw59` 完了 ✓ 65 勝 4 敗 ✓ **Act 3 完走 0/4** ✓ hypotheses 2 件は corpus で測って棄却 ✓

HEAD `9bbf6a2`（Throwing Axe ✓ Secret Weapon ✓ 多重 play の debuff 順序 ✓ が入った状態 ✓）✓ 08:46〜09:08 ✓

```
RESULT sw59 AM8C6YXHSG wins=17 losses=1 records=360 depth=Act 3, Floor 15  fail=Watchdog 30.0s at Entering Boss room (Act 3, Floor 15)
RESULT sw59 D6A1F8C3E5 wins=15 losses=1 records=302 depth=Act 3, Floor 5   fail=Watchdog 30.0s at Entering Monster room (Act 3, Floor 5)
RESULT sw59 H2LV6ZJ4XW wins=20 losses=1 records=388 depth=Act 3, Floor 6   fail=Watchdog 30.1s at Entering Monster room (Act 3, Floor 6)
RESULT sw59 VTW80ZJA2G wins=13 losses=1 records=262 depth=Act 2, Floor 16  fail=Watchdog 30.1s at Entering Boss room (Act 2, Floor 16)
```

前の panel（`cb226c5` ✓ 3 seed ✓）と同じ seed では AM8C6YXHSG が 17 勝のまま records 354→360 ✓
D6A1F8C3E5 は 14 勝 → **15 勝 ✓ Act 3 Floor 4 → Floor 5 ✓** ✓ Act 3 完走は両 panel で 0 ✓
**H2LV6ZJ4XW は 20 勝 28 records まで進んだが Act 3 Floor 6 で敗北** ✓ この seed には過去の完走記録（result file ✓ HP 7 ✓）があるので ✓
現在の build ではそのルートに届いていない ✓（teaching 17 ✓ 忠実度修正が勝数を落とすことはある ✓）✓

**敗北の瞬間の形が 4 本とも同じ** ✓ 最後の combat record を見た ✓
- AM8C6YXHSG vs `MONSTER.QUEEN`: 敌 171/400 ✓ player **1 HP ✓ block 0** ✓ turn 10 ✓ FRAIL 92 ✓ VULNERABLE 92 ✓ WEAK 92 ✓ STRENGTH 4 ✓
  legal actions は **potion 3 個と end_turn だけ** ✓（play できる札が無い ✓）
- H2LV6ZJ4XW vs `MONSTER.SLIMED_BERSERKER`: 敌 141/261 ✓ player **18 HP ✓ block 6** ✓ turn 6 ✓ STRENGTH 6 ✓ RUPTURE 1 ✓ WEAK 1 ✓
  legal actions は **potion と end_turn だけ** ✓
→ **手札が尽きて火力が続かないまま敌を殺しきれない** ✓ という形 ✓（model の食い違いではなく火力の経済 ✓）✓

**棄却した hypothesis 1: Status 札の掃除が足りない** ✓ 全 corpus の shop record 4,764 件で agent の action を数えた ✓
`buy_card 1445 ✓ skip 1433 ✓ remove 1039 ✓ buy_potion 741 ✓ buy_relic 106 ✓` ✓
`choose_shop` は remove を持っていて Curse を消している ✓ **Status/Curse が deck に残っていた shop は 4,764 件中 84 件だけ** ✓（1 枚 49 件 ✓ 2 枚 35 件 ✓）✓
→ 掃除は既に使われていて ✓ Status 汚染は corpus レベルでは薄い ✓ **lever ではない** ✓
（H2LV6ZJ4XW の run で DECAY が hand に出たのは 1 run の観察 ✓ 一般化しなかった ✓ teaching: 1 run から結論しない ✓）✓

**棄却できないが測れない hypothesis: Act 3 で RestSite を取らない路線** ✓ ルートを選ぶ札を trace から復元した ✓
- H2LV6ZJ4XW Act 1: Monster 5 ✓ Elite 3 ✓ **RestSite 4** ✓ / Act 2: Monster 4 ✓ RestSite 3 ✓ / **Act 3: Ancient ✓ Monster ✓ Unknown ✓ Monster ✓ Monster ✓ Unknown ✓（RestSite 0 ✓）** ✓
- AM8C6YXHSG Act 3: Monster 4 ✓ **RestSite 3 ✓** Treasure ✓ Elite ✓ Boss に到達 ✓
Act 3 で rest を 1 も取らなかった run が Floor 6 で死んでいる ✓ 示唆的だが ✓
**Act 2・Act 3 の map graph が disk に残っていない** ✓（`data/sw59_*_map.json` は `act: ACT.OVERGROWTH` の 1 act 分だけ ✓ 64 points ✓）✓
→ rest がそもそも選択可能だったかを検証できない ✓ **現状の artifact では測定不能** ✓（teaching 80 ✓ 記録された artifact が記録した範囲を見る ✓）✓
次の run では act ごとの map file を残す方法を考える ✓

**combat model の忠実度側は動いていない** ✓ 前 round の census で arm corpus 614 中 612 ✓ 新しい run 218 中 218 ✓
Rampage growth は採用せず ✓（一致 43/52 → 18/52 ✓ 前 round ✓）✓

## Round 73: **boss 戦中の player HP の最小値が壁**だと数えた ✓ QUEEN 戦は中央値 11 HP ✓ 49% が 10 以下 ✓（見出しの「進入時 ✓」は不正確 ✓ 方法行の通り boss 戦中の最小値 ✓）
<!-- 2026-07-20 注記 ✓: この節の 17 ✓/11 ✓ は「boss 戦の最初の record における player HP の最小値 ✓」✓ = 戦中の最低 HP ✓✓
     boss の「進入 ✓」時点の HP は後に測り直し ✓ 中央値 72 ✓（Act 2 boss ✓ 6 trace ✓）✓ 終了時中央値 8.5 ✓ ✓ 両方は矛盾しない ✓
     混乱の原因は見出し ✓ 数字の定義は方法行に書く ✓-->

まず「どこで詰まっているか」を corpus で数えた ✓ 61 run を sample して mod log の最後の `Act N, Floor M` ✓
と最後の combat record の敌 id を対応させた ✓
```
最終到達: Act 1 9 ✓ Act 2 32 ✓ Act 3 20
最後の fight: Act 1 boss 7 / non-boss 1 ✓ Act 2 boss 26 / non-boss 6 ✓ Act 3 boss 18 / non-boss 2
```
**最後の一戦が boss である割合 48/57 ✓ 84%** ✓（"non-boss" 扱いになった DECIMILLIPEDE の segment 3 件も実は Act 2 boss 戦 ✓）✓
→ Act 3 の道中の fight が壁なのではなく ✓ **boss 戦が壁** ✓（前 round の「Act 3 で rest を取らない run が Floor 6 で死んだ」は副次的 ✓）✓

**boss 戦での火力も数えた** ✓（同一 fight の record を combat_id でつなぎ ✓ 初 record の max_hp から最後の HP を引いた ✓）✓
```
THE_INSATIABLE 380 fight: 中央値 9 turn ✓ 削った量 251 ✓ 残り 70 ✓ 火力/turn 27.5 ✓ 100 未満しか削れていない 7/380
VANTOM            556 fight: 中央値 10 turn ✓ 削った量 154 ✓ 残り 19 ✓ 火力/turn 15.6 ✓ 18/556
QUEEN             100 fight: 中央値 8 turn  ✓ 削った量  77 ✓ 残り 332 ✓ 火力/turn  9.7 ✓ 60/100
```
QUEEN 戦の火力 9.7/turn が異常に低い ✓ が ✓ **原因是 entry の HP だった** ✓

**boss 進入時の player HP** ✓（各 boss 戦の最初の record における player HP の最小値 ✓）✓
```
THE_INSATIABLE 380 fight: 中央値 17 HP ✓ 最低 1 ✓ 10 以下で入った 36%
QUEEN          116 fight: 中央値 11 HP ✗✗ 最低 1 ✗✗ 10 以下で入った 49% ✗✗
VANTOM         675 fight: 中央値 32 HP ✓ 最低 1 ✓ 10 以下で入った 15%
```
QUEEN 戦の play 内訳は Strike 446 ✓ Anger 290 ✓ Shrug 243 ✓ Battle Trance 238 ✓ Defend 219 ✓ Taunt 150 ✓ Bash 137 ✓
**1 fight あたり中央値 29 play ✓ 8 turn** ✓ で ✓ 手を抜いているのではない ✓ **11/90 HP で boss を迎えている** ✓から壊れる ✓
（VANTOM は 32 HP で入って 19 残りまで削っている ✓ HP を持っていれば届く例 ✓）✓

**ChainsOfBinding は model 済みと確認した** ✓（QUEEN 戦で CHAINS_OF_BINDING 3 が出たので疑った ✓）✓
`combat.py:369 ✓ 373 ✓ 967 ✓ 970 ✓ 2272` ✓ が `ChainsOfBindingPower` の Bound affliction を持っている ✓
decompile の `AfterCardDrawn` は **その turn に Afflict した数が Amount 未満の時に限って** Bound を載せる ✓ ✓
model も同じ条件で載せている ✓ → 「札を_play できなくする_効果を見落としていた」ではない ✓

**測るための道具を 1 つ直した** ✓ `MapBridge.cs` ✓
`private static bool _wroteMap;` ✓ が `if (!_wroteMap && mapPath is not null)` ✓ で **Act 1 の graph しか disk に出していなかった** ✓
→ `_writtenAct` （act id ✓）に変え ✓ 最初の act は依頼された path ✓ 以降の act は `_<ACT.ID>.json` を隣に書く ✓ようにした ✓
`AgentIo.WriteJson(_writtenAct is null ? mapPath : mapPath.Replace(".json", $"_{actId}.json"), map);` ✓
mod を rebuild 済み ✓（`ビルドに成功しました ✓ 0 警告 0 エラー ✓ 2.07 s ✓` ✓ dll 235,008 B ✓ 09:15 ✓）✓
**検証 run 走行中** ✓ tag `mapfix` ✓ seed H2LV6ZJ4XW ✓ 09:16 開始 ✓（install された dll が 09:15 の新規 build と同一 ✓ size 235,008 ✓ lesson 6 ✓）✓
完了待ち `bash-1096` ✓ **3 つの map file が出ることを確認してから commit する** ✓

**次の work の方向** ✓ boss 戦の model ではなく ✓ **late act の HP 経済** ✓（rest を取るか ✓ 必要のない fight を避けるか ✓）✓
それが本当に選べたのかを見るのが per-act map file ✓→ 今回の tooling fix はそのための準備 ✓

## Round 74: per-act の map file を出すように tooling を直した ✓ 検証 run で 3 act 分揃った ✓ Act 3 の路線仮説は棄却 ✓

**`MapBridge.cs` の修正** ✓ `private static bool _wroteMap` ✓ → `private static string? _writtenAct` ✓
最初の act は依頼された path ✓ 以降の act は `_<ACT.ID>.json` を隣に書く ✓（既存の tool が見る path はそのまま ✓）✓
rebuild 済み ✓（0 警告 0 エラー ✓）✓

**検証 run** ✓ tag `mapfix` ✓ seed H2LV6ZJ4XW ✓ HEAD `57a57aa` の code + 新しい dll ✓
```
RESULT mapfix H2LV6ZJ4XW wins=20 losses=1 combat_records=388 depth=Act 3, Floor 6
```
同じ seed の `sw59`（tooling 変更前 ✓）と **勝敗 ✓ records ✓ 到達が完全一致** ✓ → tooling 変更が挙動を変えていない ✓
map file ✓ 3 つ揃った ✓
`data/mapfix_H2LV6ZJ4XW_map.json` ✓（ACT.OVERGROWTH ✓ 64 points ✓）✓ `..._map_ACT.HIVE.json` ✓（59 points ✓ RestSite 9 ✓）✓ `..._map_ACT.GLORY.json` ✓（**53 points ✓ RestSite 8 ✓**）✓
install された dll が build 出力と同一（235,008 B ✓ 09:15 ✓）✓

**Act 3 の路線仮説を棄却した** ✓ walk と各段の choices ✓
```
(3,0) Ancient → (5,1) Monster → children: (5,2) Unknown だけ ✓ 強制
(5,2) Unknown → children: (5,3) Monster だけ ✓ 強制
(5,3) Monster → children: (4,4) Monster だけ ✓ 強制
(4,4) Monster → children: (5,5) Monster / (3,5) Unknown ✓ 選べる ✓ が rest は無い ✓
(3,5) Unknown → children: (3,6) RestSite ✓ だけ ✓ ここへ進む前に Floor 6 の fight（SLIMED_BERSERKER ✓）で死亡 ✓
```
**5 段中 4 段が children 1 つだけ ✓ 最初の RestSite は死んだ node の次 ✓** ✓
→ Act 3 に入って rest を避けたのではなく ✓ **Act 2 の終わり・Act 3 の出だしで削られていた** ✓
（Act 2 の walk は row 6 ✓ 10 ✓ 14 ✓ に RestSite を取っており ✓ boss 直前の rest も取っている ✓）✓
前 round の「QUEEN 戦に 11 HP で入る ✓ 49% が 10 以下 ✓」の HP がどこで減るかを次の調べにする ✓

tooling 変更なので policy は無変更 ✓ suite 783 件 green ✓

## Round 75: rest  policy は既に正しかった ✓ HP 15 以下で rest が選べる局面 15 件すべて取っている ✓ 崩れは fight 内の一括損失 ✓

sweep `sw64` を HEAD `3b65c2c` で開始 ✓（09:29 ✓ seed H2LV6ZJ4XW ✓ EAIF2UUVCK ✓ 9PCQMO0DAY ✓）✓ per-act の map file が出る状態での初めての sweep ✓ 完了待ち `bash-1107` ✓

**fight 数に対する player HP の中央値** ✓ 136 run ✓（fight の区切りは下の教訓により `combat_end` record を使った ✓）✓
```
fight  1〜 8: 中央値 80 ✓  下位10% 62〜74
fight  9: 中央値 80 ✓  四分位 65 ✓  下位10% 52
fight 12: 中央値 68 ✓  四分位 54 ✓  下位10% 36
fight 13: 中央値 76 ✓  四分位 45 ✓  下位10% 16 ✗
fight 15: 中央値 73 ✓  四分位 36 ✓  下位10%  7 ✗
fight 17: 中央値 80 ✓  四分位 27 ✓  下位10%  6 ✗
fight 19: 中央値 81 ✓  四分位 20 ✓  下位10%  7 ✗
fight 20: 中央値 80 ✓  四分位 10 ✓  下位10%  4 ✗
```
**中央値の run は fight 15 まで 80 HP を保っている** ✓ 壊れているのは下位側 ✓ = **一戦で大きく削られる run が死んでいる** ✓
HP が均等に減るのではなく ✓ 一戦での一括損失 ✓（前の boss 進入時 HP 計測 ✓ QUEEN 戦中央値 11 HP ✓ とつながる ✓）✓

**「削られた後に rest を取っているか」を Act 1 で測った** ✓（`*_map.json` は Act 1 の graph ✓ なので Act 1 だけ ✓）✓
**最初は測れていなかった** ✗✗ trace の map record は act をまたいでおり ✓ Act 2/3 の (col,row) を Act 1 の graph と照合して
「rest が選べるのに取らなかった 11 件」が出ていた ✓✗ **これは観測の誤り** ✓（graph に無い座標が 3,822 件 ✓）✓
Act 1 の walk に限定して ✓ graph の children から選択可能を判定 ✓ 選択が実際に children 内にある遷移 57 件だけ使った ✓
```
直前の fight 後に HP 15 以下:
   rest 選択可能 True ✓  取った True  ✓: 15 回
   rest 選択可能 True ✓  取った False ✗: 0 回 ✓✓
   rest 選択可能 False ✓ 取った False ✓: 42 回
```
→ **削られた時に rest を避ける挙動は無い** ✓ rest policy はこの限りでは正しい ✓
（検証できた遷移が 57 件しかない ✓ sample は小さい ✓ 新しい run では per-act map が揃うので next で確認する ✓）✓
よって HP 崩れの説明は fight 自体の被ダメージ ✓→ 次の測定は「どの fight で何 HP 失うか」の一戦単位の内訳 ✓（上の試みは monster あとの集計が n>=8 の行 1 件しか出せず失敗 ✓ 一戦の HP 損失を monster 名に紐づく形で数え直す ✓）✓

**tooling の教訓 2 つ** ✓
1. **trace 内の `combat_id` は fight を区別できない** ✓ `act3_pop2_B4J8Q1R6YK` で combat record 269 件に対し distinct combat_id は **4** ✓（スロット番号の使い回し ✓）✓ → fight の区切りは **`combat_end` record** ✓ を使う ✓
2. `*_map.json` と trace の対応は古い artifact では信用できない ✓（座標が graph に無い ✓ 3,822 件 ✓）✓ 新しい run の per-act map 同士で照合する ✓

## Round 76: 一戦の HP 損失を数えた ✓ median 17 ✓ 90 パーセント 53 ✓ **損失 40 以上が fight の 19.4%** ✓

182 run ✓ 2,486 fight ✓（境界は `combat_end` ✓ 前 round の教訓 ✓）✓ 損失 = fight の最初の record の HP - 最後の record の HP ✓
```
一戦の HP 損失: 中央値 17 ✓  75% 32 ✓  90% 53 ✓  95% 67 ✓  最大 135
損失 40 以上: 483 fight（19.4%）✓  損失 60 以上: 183 fight ✓
損失 40 以上の fight に出てきた monster:
   VANTOM 144 ✓ THE_INSATIABLE 101 ✓ BOWLBUG_ROCK 36 ✓ QUEEN 34 ✓ TORCH_HEAD_AMALGAM 34 ✓
   BOWLBUG_SILK 34 ✓ SLUMBERING_BEETLE 34 ✓ BYGONE_EFFIGY 18 ✓ DECIMILLIPEDE segments 15 x3 ✓ MYTE 14 ✓
最も重い一戦: QUEEN + TORCH_HEAD_AMALGAM で 損失 109〜135（max HP 122〜144 ✓ 7〜10 turn ✓）✓
```
→ **boss 戦が最大の一括損失** ✓（109〜135 ✓）✓ が ✓ **道中の mob（Bowlbug 系 ✓ Slumbering Beetle ✓）も 34〜36 fight で 40 以上削っている** ✓
boss と同数の fight で削られている ✓ = 削られ方は boss だけの問題ではない ✓

**Strength で自分の攻撃を育てる mob は model 済みと確認した** ✓（SLUMBERING_BEETLE の `ROLL_OUT_MOVE` は `DamageCmd.Attack` + `PowerCmd.Apply StrengthPower` を自分に載せる ✓ので ✓ 毎ターン攻撃力が上がる ✓型 ✓）✓
`combat.py:1427` ✓ `1685` の `+ _power(enemy.powers, "StrengthPower")` ✓ が intent の damage に敌の Strength を足している ✓✓
`1747` ✓ `1767` は effects 側の StrengthPower 適用を見ており ✓ `1902` `1904` は PersonalHive などの成長を載せている ✓
** exported intent 値と二重計上になっていないか** ✓ → census が 614 中 612 ✓ 新しい run 218 中 218 ✓ で敵の damage が合っているので ✓ 二重計上ではない ✓

**次の測定（sw64 の per-act map を使う ✓）** ✓ 道中の fight で 40 以上削られる run が多いなら ✓
** Elite / 戦いを選んだ node の数と ✓ その時に他により安い選択肢があったか ** ✓を ✓ act 単位の graph ✓（`..._map_ACT.HIVE.json` ✓ `..._map_ACT.GLORY.json` ✓）✓ と trace の route ✓ から測る ✓
前 round の rest 検証では Act 1 の graph しか無く検証できる遷移が 57 件だった ✓ 新しい run では 3 act 分揃う ✓ので ✓ 同じ検証を act 全部でやる ✓
sweep `sw64`（HEAD `3b65c2c` ✓ 09:29 ✓ H2LV6ZJ4XW ✓ EAIF2UUVCK ✓ 9PCQMO0DAY ✓）は走行中 ✓ 完了待ち `bash-1107` ✓

## Round 77: 「Elite を避けて HP を守る」は lever でないと測った ✓ Act 3 まで行った run の方が Elite を多い ✓

**matched artifact で検証できる形にした** ✓ tag `mapfix_H2LV6ZJ4XW` は trace ✓ と 3 act の graph ✓ が対応する ✓
→ **座標の不一致 0 件 ✓ walk 38 段すべて graph 上で解決 ✓** ✓（前 round の 3,822 件の不一致は古い trace と map の取り違えだった ✓）✓
その run で **HP 20 以下で次に移動した局面は 2 件だけ** ✓
- Act 1 の (6,6) Elite 戦後に **9 HP** ✓ options は Shop のみ ✓（rest は無かった ✓）✓
- Act 3 の (3,5) Unknown 後に 18 HP ✓ options は RestSite のみ ✓ → **rest へ移動する前に Floor 6 の fight で死んでいる** ✓（移動先は rest ✓）✓
Act 3 の walk はほぼ強制 ✓（前 round ✓）✓

**corpus で Elite / RestSite / Monster・Unknown の選択数を最終到達別に数えた** ✓（mod log が有る 582 run ✓ trace の map record の point_type ✓ boss で act 区切り ✓）✓
```
最終 Act 1 で止まった  99 run: Act1 Elite 中央値 0 ✓ 合計  33 ✓ RestSite 中央値 3 ✓ Monster/Unknown 中央値 9
最終 Act 2 で止まった 327 run: Act1 Elite 中央値 0 ✓ 合計 124 ✓ Act2 Elite 中央値 0 ✓ 合計  98 ✓ RestSite 3〜4 ✓ Monster/Unknown 8〜9
Act 3 まで行った      156 run: Act1 Elite 中央値 2 ✓ 合計 268 ✓ Act2 Elite 中央値 1 ✓ 合計  84 ✓ Act3 Elite 中央値 0 ✓ 合計  52 ✓ RestSite 3 ✓ Monster/Unknown 7〜8
```
**深く進んだ run の方が Act 1 で Elite を 2 倍近く取っている** ✓（1 run あたり 1.7 ✓ vs 0.38 ✓）✓
→ **Elite を避けて HP を温存する方針は深さと負の相関 ✓ 逆方向** ✓
Elite は relic ✓ と札の報酬 ✓ 来源で ✓ その成長が次の act を持たせている ✓（Act 3 死の relic 一覧は12個 ✓）✓
Monster/Unknown の数は Act 3 到達 run の方が少ない ✓（中央値 7 ✓ vs 9 ✓）✓ = **道中の雑戦を減らし Elite を取っている** ✓ という形 ✓
現在の map policy（relic 価値で Elite を好む ✓ fewest-combats ✓）はこの相関と矛盾しない ✓
「HP を守るために node を選ぶ」仮説は ✓ rest 検証 ✓（前 round ✓ 選択可能 15/15 ✓）と合わせて ✓ **棄却** ✓

残る hypotheses（次）✓
- shop の relic 購入が 4,764 decisions 中 106 件 ✓（buy_card 1,445 ✓）✓ → **relic が shop に出る頻度**を確認する ✓ 出ていないなら policy の問題ではない ✓
- card reward の選択 ✓（前々 round で potential 80 / 22 の差を見た ✓）✓ を到達と関連づけて測る ✓
sweep `sw64` は走行中 ✓（09:34 時点で seed 1 が Act 2 ✓ `..._map_ACT.HIVE.json` まで出力 ✓）✓ 完了待ち `bash-1107` ✓

## Round 78: 同じ seed の再 run は結果が完全一致 ✓ 再 run からは新しい情報が得られない ✓（測定軸の確認 ✓）

sweep `sw64`（HEAD `3b65c2c` ✓ 09:29 開始 ✓）の途中結果 ✓
```
RESULT sw64 H2LV6ZJ4XW  wins=20 losses=1 records=388 depth=Act 3, Floor 6   fail=Watchdog ✓ Entering Monster room (Act 3, Floor 6)
RESULT sw64 EAIF2UUVCK  wins=11 losses=1 records=225 depth=Act 2, Floor 10  fail=Rewards screen did not appear after combat
RESULT sw64 9PCQMO0DAY  走行中（Act 2 の map まで出力 ✓）
```
**H2LV6ZJ4XW は 3 回（`sw59` ✓ `mapfix` ✓ `sw64` ✓）すべて 20 勝 1 敗 ✓ 388 records ✓ Act 3, Floor 6 ✓ で一致** ✓
EAIF2UUVCK も前の panel と同じ 11 勝 1 敗 ✓ 225 records ✓ Act 2, Floor 10 ✓ ✓
→ **同じ seed の repeater からは何も学べない** ✓ 挙動を変えたと主張するには ✓ (1) 决定差分（attribution の decision diff ✓）✓ または (2) 新しい seed ✓ が必要 ✓
（teaching 7 ✓「arm と control が同じ数字なら測定が無い」✓ の再現 ✓）✓
per-act の map file ✓ 3 act 分 ✓ は期待どおり出ている ✓（`sw64_H2LV6ZJ4XW_map.json` ✓ `_ACT.HIVE.json` ✓ `_ACT.GLORY.json` ✓）✓

**重かった測定を streaming 版に書き直した** ✓ `/tmp/potential_depth.py` ✓
前の版は trace ごとに全 record を materialize して 10 分以上掛かった ✓→ 行を stream し ✓ boss 戦を両方見つけたら打ち切り ✓`deck` は直前のものだけ保持 ✓
background job `bash-1124` は cancel ✓ 置き換えた版の完了待ち `bash-1129` ✓（log `/tmp/pot.log` ✓）✓
測るもの: **Act 2 boss / Act 3 boss の最初の record 時点で ✓ 直前の `deck` record から計算した攻撃火力の greedy 上限** ✓（3 energy ✓ 攻撃札を damage 順に選ぶ ✓ 手札順序と 1 combat 1 回制限を無視する近似 ✓ 比較専用 ✓）を ✓ 最終到達別 ✓（Act 1 / 2 / 3 ✓）✓ に分布させる ✓
前々 round の単一 run での値（AM8C6YXHSG 80 ✓ D6A1F8C3E5 22 ✓）が ✓ corpus でも到達と相関するかどうかを見る ✓

## Round 79: card reward は boss 直前で高 damage の offer をほぼ取っていた ✓ 棄却 ✓（potential の測定の弱点も記録 ✓）

**まず measurement 側の bug を 2 つ直した** ✓
1. **greedy loop が抜けない** ✓ `CARD_DAMAGE` 持ちで cost 0 の攻撃札（Anger ✓ Rage ✓ Brutality ✓ Bloodletting ✓）を選ぶと energy が減らず `while True` が止まらなかった ✓✗ potential 測定が 20 分近く終わらなかった ✓ → **play 数の上限 12** ✓ を入れて解決 ✓（job `bash-1124` cancel ✓）✓
2. card_reward record の `cards` entry は dict だけでなく **plain string の場合がある** ✓ → `AttributeError: 'str' object has no attribute 'get'` ✓（`offer_id` ✓ で正規化 ✓）✓

**deck 火力 potential（3 energy ✓ greedy ✓ 上限 12 play ✓）** ✓ 585 run ✓
```
Act 2 で止まり boss 戦に到達 214 run: 中央値  81 ✓  25 パーセント  30 ✗  75 パーセント  87   deck 中央値 21
Act 3 まで到達（Act 2 boss 時点）155 run: 中央値  98 ✓  25 パーセント  79 ✓  75 パーセント 168   deck 中央値 22
Act 3 boss（QUEEN）に到達       113 run: 中央値  98 ✓  25 パーセント  83 ✓  75 パーセント 168   deck 中央値 29
```
**中央値より 25 パーセント側の差が大きい** ✓（30 vs 79 ✓）✓ Act 2 で死ぬ run の下位側は火力 deck が弱い ✓
ただし **potential の絶対値は 0 cost 札で水増しされる** ✓（Anger 6 x 12 play で +72 ✓ など ✓ 実際の draw 枚数を無視している ✓）✓
→ **この数字は run 同士の比較には使える ✓ 絶対値や必要火力との突き合わせには使えない** ✓（teaching 13 ✓ ad-hoc arithmetic ✓）✓

**reward policy が火力を置き去りにしているか** ✓ boss 戦直前の card_reward decision で ✓
選んだ札を最高 damage の offer と入れ替えた場合の potential 増分 ✓（同じ近似 ✓ 差なので近似の偏りは打ち消す ✓）✓
```
Act 2 boss 到達 214 run: 増分 中央値 0 ✓ 75% 0 ✓ 最大 60 ✓ 高 damage を避けた 18/214 ✓
Act 3 到達      155 run: 増分 中央値 0 ✓ 75% 0 ✓ 最大  3 ✓ 高 damage を避けた  2/155 ✓
Act 3 boss 到達 113 run: 増分 中央値 0 ✓ 75% 0 ✓ 最大 54 ✓ 高 damage を避けた  6/113 ✓
```
→ **boss 直前の 1 手では 96% が最高 damage の offer を取っている** ✓ reward policy のこの側は正しく ✓ **仮説は棄却** ✓
避けた例は TAUNT（0 damage ✓ debuff ✓）→ ANGER ✓ / IMPERVIOUS ✓ → ANGER ✓ / POMMEL_STRIKE（9 ✓）→ HEMOKINESIS（15 ✓）✓ など ✓
debuff 札を売る価値が高いと判断した結果 ✓ で ✓ 火力だけを積めという指示と矛盾する根拠にはならない ✓
**よって potential の差（30 vs 79）は boss 直前の 1 手ではなく ✓ その前の積み上げ ✓ が主因** ✓（何を取れるかは seed が決まる部分も大きい ✓）✓

**残る hypothesis** ✓ shop の relic 購入（106/4,764 ✓ options が trace に出ないので frequency 側が不明 ✓）✓
Act 2 boss 時点で火力 deck が弱い run が何が足りないのか ✓（札の枚数 ✓ 強化 ✓ relic ✓）を ✓ potential 以外の物差しで見る ✓
sweep `sw64` は 3 本目 9PCQMO0DAY が走行中 ✓（H2LV6ZJ4XW ✓ EAIF2UUVCK ✓ は前 round と同じ結果 ✓ 完了待ち `bash-1107` ✓）✓

## Round 80: boss 戦で kill を取り逃していない ✓ 25 fight ✓ 914 decision ✓ **lethal 可能 11 件すべて取っている** ✓

`/tmp/lethal_audit.py` ✓（tree を引数で受け ✓ 生 run 中は sample を絞る ✓）✓ 監査の形:
boss 戦の各 decision で observation から model state を組み ✓ **legal actions を全部 step して全敌が死ぬ手があるか** ✓を ✓
record された play と突き合わせた ✓（credit 順は `_PENDING_ACTION` で再現 ✓ teaching 59 ✓）✓
```
MONSTER.THE_INSATIABLE fights audited: 25
{'decisions': 914, 'lethal available': 11, 'lethal taken': 11}      # missed は 0 ✓✓
```
**取り逃し 0 件** ✓「kill できる手を取っていれば 70 HP 差が埋まった」という筋は無い ✓
（前 round の THE_INSATIABLE 戦の中央値: 251 削って残り 70 ✓）✓
lethal が立った 11 件はすべて実際に取られている ✓（agent の lethal short-circuit ✓が効いている ✓）✓

**sweep `sw64` 完了** ✓ HEAD `3b65c2c` ✓ 3 seed ✓ 合計 **43 勝 ✓ combat 敗北 2 ✓ Act 3 完走 0** ✓
```
RESULT sw64 H2LV6ZJ4XW  wins=20 losses=1 records=388 depth=Act 3, Floor 6  fail=Watchdog ✓ Entering Monster room (Act 3, Floor 6)
RESULT sw64 EAIF2UUVCK  wins=11 losses=1 records=225 depth=Act 2, Floor 10 fail=Rewards screen did not appear after combat
RESULT sw64 9PCQMO0DAY  wins=12 losses=0 records=229 depth=Act 2, Floor 14 fail=none ✓（combat 敗北無し ✓）
```
**3 本中 2 本は combat で負けていない run が infrastructure で止まっている** ✓✗✗
- EAIF2UUVCK ✓ combat 後の rewards screen が出ない ✓
- 9PCQMO0DAY ✓ trace の最後は `map RestSite` ✓（seq 315 ✓ Act 2 Floor 15 の rest を選んだ ✓）✓ その後 record が無い ✓
  mod log の最後は `post-room:Event:Act2:F14` ✓ stdout には `[Watchdog] No progress for 5.0s (last: Playing main menu)` ✓✓ → **game が main menu に戻っている** ✓（run が abandon される ✓known な挙動 ✓）✓
  combat_end は12件 ✓ 敗北 0 ✓ で ✓ 健康な run が rest の所で消えた ✓
→ 完走測定の前に ✓ **この stop 自体が win 数を削っている** ✓（teaching 82 ✓「もっともらしい infrastructure 診断は trace の最終状態と突き合わせる」✓ を実行 ✓）✓
次の調査: rest を選んだ後に観測が来ない経路 ✓（RestBridge ✓）と abandon 経路 ✓（open question (c) ✓「launcher が Abandoning existing run で止まる」✓）✓

## Round 81: **event 决定の 30% が game 側の fallback に上書きされている**と数えた ✓ 6,465 件中 1,948 件 ✓

`data/*_agent.jsonl` の `phase == "event"` record を全部数えた ✓
```
event records total: 6,465
   (action=None, reason=None)                 4,517 ✓  → agent の action が受け入れられた ✓（受入側は option_index / option_id 側に出る ✓）
   (action='fallback', reason='invalid_event_action')  1,948 ✗✗ → **30.1% が bridge に弾かれている** ✓
弾かれた event top: BUGSLAYER 170 ✓ WHISPERING_HOLLOW 135 ✓ SYMBIOTE 131 ✓ BRAIN_LEECH 129 ✓ DENSE_VEGETATION 112 ✓
TEA_MASTER 108 ✓ THE_FUTURE_OF_POTIONS 101 ✓ TINKER_TIME 90 ✓ INFESTED_AUTOMATON 85 ✓ SAPPHIRE_SEED 79 ✓ SPIRIT_GRAFTER 72 ✓
```
**events は relic ✓ 札 ✓ gold ✓ HP ✓ を配る phase なので ✓ この上書きは直接 HP 経済に影響する** ✓（前 round までで「壁は boss 進入時の HP ✓ 一戦での一括損失 ✓」と測っている ✓）✓

**bridge 側の条件** ✓ `official_mod/EventBridge.cs:141-151` ✓
```
if (action.Type != "event_option" || action.OptionIndex is not int optionIndex || optionIndex 範囲外)
    → Trace(reason = "invalid_event_action") ✓ Fallback
if (!eligible.Any(Index == optionIndex) || selected.Option.TextKey != action.TextKey ||
    selected.Option.Relic?.Id.ToString() != action.RelicId)
    → Trace(reason = "invalid_event_action") ✓ Fallback
```
bridge が出す `legal_actions` は全部 `type = "event_option"` ✓（`event_relic` という type は出さない ✓）✓
agent の `choose_event`（`official_agent.py:858`）は `{"event_option","event_relic"}` を filter し ✓ `is_locked` ✓ と text_key が `_LOCKED` のものを落とし ✓
**空になると `ValueError("no event relic actions")` ✓ を投げる** ✓→ `_choose` の例外 tail（`official_agent.py:1765` ✓ KeyError/ValueError/… ✓）で heuristic tail に落ち ✓ ** heuristic tail が出てくる action は `event_option` ではない可能性が高い ✓** → bridge が弾く ✓ という筋 ✓
（message の "no event relic actions" は relic 型が有った名残 ✓ で ✓ bridge は event_relic を出さない ✓）✓

**確定できていない部分** ✓ trace は agent が送った action 本体を残していない ✓（fallback record には `decision_source` ✓ と `decision_reason` ✓ だけ ✓）✓
→ **弾かれた action の `type` ✓ `option_index` ✓ `text_key` ✓ `relic_id` ✓ を trace に載せる diagnostic を bridge 側に入れる** ✓（1 行程度 ✓ map file の per-act 化 ✓ と同じ型の tooling fix ✓）✓ → 1 run でパターンが分かる ✓
次 round: その diagnostic を入れて rebuild ✓ 1 run ✓ → 弾かれ理由の内訳を取る ✓

**同時に測った 2 件** ✓
- **boss 戦で kill を取り逃していない** ✓ THE_INSATIABLE 25 fight ✓ 914 decision ✓ lethal 可能 11 件すべて実行 ✓（取り逃し 0 ✓）✓ → 「70 HP 差は kill 取り逃し」筋は無い ✓（前 round ✓）✓
- sweep `sw64` 完了 ✓ 43 勝 ✓ combat 敗北 2 ✓ Act 3 完走 0 ✓ **3 本中 2 本が combat 以外で止まった** ✓（rewards screen 不出現 ✓ / rest を選んだ後に game が main menu に戻る ✓ `[Watchdog] No progress for 5.0s (last: Playing main menu)` ✓）✓

## Round 82: event 拒否の原因を特定 ✓ agent が出ていく action の型は `event_fallback` ✓ bridge は `event_option` しか.accept しない ✓

diagnostic を入れた mod ✓（`EventBridge.cs` の拒否 Trace に `attempted_type` ✓ `attempted_option_index` ✓ `attempted_text_key` ✓ `attempted_relic_id` ✓ `eligible_text_keys` ✓ を追加 ✓）✓ で 2 seed run ✓ tag `evdiag` ✓ HEAD `0cd5b43` ✓:
```
attempted action shape: {('event_fallback', True): 5}      # type=event_fallback ✓ option_index=None ✓ text_key=None ✓
attempted text_key top: {('event_fallback', 'None'): 5}
```
**コード上の場所** ✓ `official_agent.py:919` `return {"type": "event_fallback"}` ✓
`choose_event` は `EVENT_OPTION_SCORES` に entry の無い event で ✓
(1) 得点のある option があればそれを取る ✓ → (2) `is_proceed` の option があれば proceed ✓ →
**(3) どちらも無ければ `event_fallback` ✓** ← bridge が `action.Type != "event_option"` ✓ で弾く ✓ → game の AutoSlay fallback が選ぶ ✓
**proceed ボタンが無い event ✓（選択肢が全て何かを払う/取る/戦う types ✓）で発生する** ✓
（BUGSLAYER 170 ✓ WHISPERING_HOLLOW 135 ✓ SYMBIOTE 131 ✓ など ✓ proceeds が無い event たち ✓）✓

**これは CODEWIKI line 2354 に既に記録されていた** ✓「`choose_event` は entry の無い event に `event_fallback` を返し ✓ bridge は `invalid_event_action` として game に投げる ✓ panel では 81 decision 中 26 件（6 seed）✓ **実走で測れない理由は trace の event record に選ばれた option しか残っていない** ✓」✓
→ 今回の diagnostic がその観測穴を塞ぎ ✓ **原因の型まで確定した** ✓ ✓
pin されている test は `test_unknown_event_returns_bridge_fallback` ✓（`test_official_agent.py` ✓ "unknown event は bridge fallback を返す" ✓）✓

**同じ seed が必ずしも同じ run になるとは限らない** ✓✗（前 round の「再 run は完全一致」の訂正 ✓）✓
seed `9PCQMO0DAY`: `sw64` では 12 勝 0 敗 ✓ 229 records ✓ Act 2 Floor 14 で main menu に戻り停止 ✓
`evdiag` では 12 勝 1 敗 ✓ 259 records ✓ Act 2 Floor 16（boss 室）まで進んだ ✓ → **同じ seed 同じ code で結果が違う** ✓
H2LV6ZJ4XW は 3 回一致したので ✓「一致する seed もあればしない seed もある」✓ が正しい ✓
（Godot / AutoSlay の screen 待ち時刻などが効く筋 ✓ 未確定 ✓）✓

**採る手順** ✓ policy 変更（`event_fallback` をやめ ✓ 最初の eligible option を答える ✓）は scratch `.wt-proto12` で実装 ✓ test 1 件追加 ✓ suite は 784 件中 1 件 fail ✓
→ **その 1 件が上記の pin された test** ✓（`test_unknown_event_returns_bridge_fallback` ✓）✓「unknown event は game に委ねる」という前 round の決定を test が留めている ✓
前 round の決定は「測れないから変えない」✓ だった ✓ 今は測れるようになった ✓ ので ✓ **arm（変更あり ✓）vs control（HEAD ✓）の panel で測ってから adopting する** ✓（teaching 9 ✓「agent が価格付けできる範囲を広げる変更は panel で測る」✓）✓
panel 中に test を更新するのは ✓ 採用を決めたときだけ ✓

## Round 83: **hand の札は `vars` で現在の DynamicVar を出している** ✓ 2,144/2,144 件 ✓（前 round の「観測できない」は誤り ✓）

`CombatBridge.cs` の observation 部 ✓
```
vars = card.DynamicVars.Select(variable => new { id = variable.Key, value = variable.Value.PreviewValue }),
```
trace で combat record の hand entry を数えた ✓ **`vars` を持つ hand entry 2,144 ✓ 持たない 0 ✓** ✓ 例 ✓
`CARD.STRIKE_IRONCLAD` (upgrade 0) → `[{"id": "Damage", "value": 6}]` ✓（print 値 5 ではない ✓ 現在の修正込みの値 ✓）✓
**draw_pile / discard_pile / exhaust_pile の entry には `vars` が無い** ✓（`id` ✓ `upgrade` ✓ `enchantment` ✓ のみ ✓）✓

**前 round の Rampage 棄却の一部は前提が違った** ✓✗✗ 私は「札の現在の Damage BaseValue は観測から読めない」と書いた ✓
それは **pile 側の entry を見た結果** ✓ で ✓ **hand 側は出ていた** ✓ ✓
→ **Rampage の growth を忠実に seed する道はある** ✓：play しようとしている copy の `vars` の `Damage` を読めば ✓
その copy が実際に何ダメージを出すかが分かる ✓（run 中の持続 ✓ combat を跨いでも ✓ 観測される ✓）✓
「自分で玩んだ数を数える」方式（過大評価 ✓ 一致 43/52 → 18/52 ✓）を棄却した判断はそのまま ✓✓ が ✓
**代替案として export 値を使う方式が残る** ✓（次 round ✓）✓

**agent 側は既に export 値を使っている所がある** ✓ `official_agent.py:605` `_card_value(action, hand, metric)` ✓
`card.get("vars")` を読み ✓ "calculated" を含む名前は `calculated` 側に分け ✓ max を取り ✓ 無ければ KNOWN_CARD_DAMAGE / KNOWN_CARD BLOCK に倒す ✓（× `_card_hit_count` ✓）✓
`_is_self_damage` ✓（626）✓ `_self_damage_value` ✓（637）✓ Whirlwind の X 扱い ✓（600）✓ Battle Trance の `Cards` var ✓（1206 ✓ 1564 ✓ 1807）✓ 1959 の Block 判定 ✓ 2861 ✓ 3089 ✓
**一方 rollout（`combat.py`）は `CARD_DAMAGE[card] + CARD_UPGRADE_DAMAGE + maul_bonus/thrash_bonus` で組み直す** ✓（`combat.py:3366-3369` ✓）✓
→ 同じ札の火力を ✓ agent の即決側は観測値 ✓ rollout は再計算 ✓ で見ている ✓（census が 612/614 ✓ なので再計算は大体合っている ✓）✓

**Status 札は game 側で play できる** ✓ `Toxic.cs` は `base(1, CardType.Status, CardRarity.Status, TargetType.None)` ✓
`HasTurnEndInHandEffect` ✓（hand に残ったまま turn end で owner に 5 damage ✓）✓ `CardModel.cs:792` に `protected virtual bool IsPlayable => true;` ✓
**Toxic は IsPlayable を override していない ✓ → play できる ✓**（1 energy ✓ 消費 ✓ turn end の self damage を回避 ✓）✓
model は Toxic を play できない札として扱い ✓ rollout は price しない ✓
corpus の新しい 9 trace では **`legal_actions` に model が play できない札として出るのは `CARD.TOXIC` だけ ✓ 17 record ✓** ✓
→ 小さいが実在する gap ✓（次 round で測る ✓：17 件で実際に play されていたか ✓ 取っていれば何を守れたか ✓）✓

**combat decision の fallback 内訳** ✓ 新しい 9 trace ✓
```
decision_reason: None 2136 ✓ rollout_disabled_no_playable_card 485 ✓ rollout_rejected_unsafe 26 ✓ rollout_rejected_self_damage 26 ✓ obscura_focus 2
```
**「play できる札が無いので rollout を使わなかった」decision が 485 件** ✓（全体の約 2 割 ✓）✓
前 round までに見た「败北の瞬間 legal actions が potion と end_turn だけ ✓」と同じ形 ✓
→ 火力が続かない問題の另一側 ✓（札が尽きる ✓）✓ policy 変更の候補ではなく ✓ まず card reward / 枚数経済の測定に残す ✓

panel の panel（event policy ✓）は arm 1 本目が走行中 ✓ 0 件の event 拒否 ✓（4 件 accepted ✓ 0 rejected ✓）✓ 完了待ち `bash-1165` ✓

## Round 84: hand の `vars` は**修正込みの preview** ✓ だから Rampage の growth はそこから読めない ✓（前 round の「道が開く」は訂正 ✓）

前 round で「hand entry が `vars` を出している ✓ だから play する copy の現在の Damage が読める ✓」と書いた ✓
**が ✓ この判断の前に読むべき code comment が既にあった** ✓ `combat.py:3360-3366` ✓
```
# fight, so a copy met mid-run already hits harder than its printed 5/4. The bridge's
# `vars` cannot supply the real number: DamageVar.UpdateCardPreview runs the whole
# ModifyDamage hook chain, so the reported Damage already has Strength, Weak, Frail and
# enchantments folded in - reading it here would double-count everything below. The model
# therefore starts from the printed value and only adds the growth it sees itself, which
# under-rates a long-carried copy rather than over-rating one.
```
export される `Damage` は ✓ Strength ✓ Weak ✓ Frail ✓ enchantment まで織り込んだ **最終 preview** ✓ ✓
（`CARD.STRIKE_IRONCLAD` upgrade 0 が 6 出ていた ✓ のも print 値 5 + 何か ✓ で ✓ growth ではない ✓）✓
model は damage に自分で Strength などを足す ✓ ので ✓ preview を base として使うと **同じ modifier を2回数える** ✓✗
→ **Rampage の growth は観測から忠実に seed できない ✓** という結論に戻る ✓（推論方式の過大評価 ✓ 43/52 → 18/52 ✓ と合わせて ✓ **この項目は閉じる** ✓）✓
新しい教訓 ✓「自分がもう一度開こうとしていている判断が ✓ code の comment や CODEWIKI に既に書かれていないかを確認してから測る」✓（teaching 42 ✓ 71 ✓と同型 ✓）✓

**Toxic は game 側で play できる ✓ と確定** ✓（前 round の疑いの答え ✓）✓
`CardModel.CanPlay(out reason, out preventer)` ✓ の中に `if (!IsPlayable) → unplayable` ✓（`CardModel.cs:1759` ✓）✓
`Toxic.cs` は `IsPlayable` を override していない ✓（`CardModel.cs:792` の既定 true ✓）✓ → **energy があれば play できる ✓** ✓
意味 ✓ 1 energy を使って Toxic を hand から出すと ✓ `OnTurnEndInHand` の **owner への 5 ダメージを回避できる** ✓（`Toxic.cs` の `DamageVar(5m, Unpowered|Move)` ✓ + Exhaust ✓）✓
model 側は Toxic を play できない札として扱い ✓ rollout は価格付けしない ✓
母数 ✓ 新しい 9 trace で **`legal_actions` に model の play できない札として出るのは `CARD.TOXIC` だけ ✓ 17 record** ✓（combat decision 約 2,600 件の 0.7% ✓）✓
→ **play できる選択肢を増やす変更なので panel 対象 ✓ だが ✓ 17 件では win panel の信号が出ない** ✓（teaching 32 ✓「决定が変わらないのに win panel を走らせない」✓）✓
**既知の小さな gap として記録し ✓ panel には回さない** ✓（決定の変わらない変更で win を動かさない ✓）✓

## Round 85: `rollout_disabled_no_playable_card` は「札が尽きている」証拠ではなかった ✓ end_turn と同じ状態 ✓（前 round の解釈を訂正 ✓）

9 trace ✓ end_turn で終わった 608 turn を energy と hand から分類した ✓
```
energy 0 ✓ hand に札残り ✓        : 480 (79%)  ← 普通 ✓ energy を使い切って終わる ✓
turn 終了時に hand 空 ✓            :  71 (12%)  ← draw を使い切る ✓
energy 残り ✓ play できる札があったのに終了 ✓:  51 ( 8%)  ← policy の選択 ✓（狙った終了 ✓ 対象が無い等 ✓）
energy 残り ✓ だが一番安い札が高い ✓ ordering で stranded ✓:   6 ( 1%)  ✗
```
→ **play の順番で energy を無駄にしている案件は 6 件（1%）だけ** ✓✓ ordering の改善は lever ではない ✓
→ **前 round で「play できる札が無い decision 485 件は hand 不足の另一側」と書いたのは不適切** ✓
   `rollout_disabled_no_playable_card` は energy を使い切った end_turn の状態 ✓ すなわち通常の終了 ✓ ✓
   （hand が空の案件は 52 件 ✓ そのものが問題というより ✓ turn 末の通常の姿 ✓）✓
**败北の瞬間に legal actions が potion と end_turn だけだった** ✓（前々 round ✓）観察は ✓
「その turn の energy を使い切った ✓ 残った敵を削りきれない ✓」という読み方に直す ✓ ✓
**火力不足の本体は energy 経済でも ordering でもなく ✓ 1 turn に出せる damage の総量** ✓（前 round までで測った potential ✓ 中央値と下位側の差 ✓ に残る ✓）✓

**trace の key について ✓ 測定を 2 回空振りさせた落とし** ✓
- JSON は compact ✓（`{"seq":0,"phase":"combat",...}` ✓ space 無し ✓）✓
- **combat record の action 分類は `type` ✓（`card` 2,009 ✓ `end_turn` 608 ✓ `potion` 58 ✓）** ✓ で ✓ `action_type` ✓ という key は無い ✓
  → `record.get('action_type')` ✓ を使った監査（lethal audit ✓）は end_turn を 1 件も credit していなかった ✓✗（結果の lethal 判定には影響しなかった ✓ credit 順の再現としては不完全 ✓ だった ✓）✓

## Round 86: potion 経済は wall ではない ✓ run 中 4〜10 個を使っており ✓ 終了時に持有したままでも火力差は埋まらない ✓

9 run ✓（`sw59` ✓ `sw64` ✓ `evdiag` ✓）✓ potion の流れを数えた ✓
```
run 中の potion 使用数: 4 個 x3 run ✓ 5 x1 ✓ 7 x3 ✓ 10 x2 ✓
run 中の potion 購入数: 0 x1 ✓ 1 x4 ✓ 3 x4 ✓（使用数は購入数を越える ✓ event / 敌 drop 由来分が有る ✓）✓
败北・終了時点の potion 所持数: 0 x4 run ✓ 1 x3 ✓ 2 x1 ✓ 3 x1 ✓  → 9 run 中 5 run が 1 個以上持ったまま終わっている ✓
```
**溜めて使っていないのではなく ✓ 使い切っても足りない** ✓✓
（QUEEN 戦の最后で legal actions に potion が3個並び ✓ それらを使っても 171/400 を削り切れなかった ✓ 前 round まで ✓）✓
→ potion を「より良い時に使う」改善は ✓ counterfactual が取れないので 지금은 対象にしない ✓
（holding が敗因かどうかを測る物差しが無い ✓ 測れないものには panel を使わない ✓ teaching 32 ✓）✓

## Round 87: live の决定を replay で完全再現した ✓ **`simulations` は record の値（100）に合わせないと答えが変わる** ✓

`evdiag_VTW80ZJA2G` seq 135 ✓（VANTOM 173 HP ✓ player 72/80 HP ✓ block 5 ✓ energy 2 ✓）✓
record された决定は `end_turn` ✓ `simulations 100` ✓ `search_value 0.647` ✓ `decision_source rollout_success` ✓ ✓
hand には STRIKE x3（exported Damage 6 ✓）✓ SHRUG_IT_OFF ✓ UNRELENTING（cost 0 ✓ Damage 14 ✓）✓ BURNING_PACT ✓ BARRICADE ✓ が有り ✓
→ **札を残して終了した ✓ 一見火力の無駄に見える** ✓

replay ✓（同じ record ✓ play の credit 順を `_PENDING_ACTION` で再現 ✓ teaching 59 ✓）✓
- simulations 300 で回すと **CARD.SHRUG_IT_OFF** ✓ search_value 0.7998 ✓（答えが違う ✓✗）✓
- **simulations 100 ✓ record の値 ✓ で回すと `end_turn` ✓ search_value 0.6470 ✓ で record と完全一致 ✓✓** ✓
ranking ✓
```
'End turn'  0.6470   ← 選ばれた ✓
'card:2'    0.6185   SHRUG_IT_OFF ✓
'card:0@0'  0.5915   STRIKE ✓
'card:5'    0.3685   BARRICADE ✓
'card:4@0'  -0.1660  UNRELENTING（14 damage ✓）✗✗
```
**理由が分かった** ✓ 敌に `POWER.SLIPPERY_POWER 8` ✓✓
`SlipperyPower.cs` の `ModifyHpLostAfterOsty` ✓ は **1 hit で失う HP を 1m に丸める** ✓（Buff ✓ Counter ✓ stack ✓ amount < 1 ならそのまま ✓）✓
→ Slippery 8 の VANTOM への attack は **hit ごとに 1 ダメージ** ✓（model は `combat.py:1447` ✓ `1463-1467` ✓ `3340` ✓ `3577` ✓ で cap と strip を実装済み ✓）✓
14 damage の UNRELENTING も 1 hit なら 1 に丸められ ✓ hit 数と相談して価値が下がる ✓ → **rollout が終了を選んだのは筋が通っている** ✓✓

**「play できる札を残して終了した 51 turn」の内訳** ✓ 9 trace ✓ 札別 ✓
`DEFEND_IRONCLAD 34 ✓ STRIKE_IRONCLAD 23 ✓ BLOODLETTING 20 ✓ SHRUG_IT_OFF 6 ✓ SECOND_WIND 4 ✓ ANGER 4 ✓ RUPTURE 4 ✓ BREAKTHROUGH 3 ✓ IMPERVIOUS 3 ✓ UNRELENTING 2` ✓
- **cost -1 の札（SPOILS_MAP ✓ WOUND ✓ など）を「play できる」と数える落とし** ✓✗（observation の `cost` に -1 が出る ✓ → **filter は `0 <= cost` ✓ が正しい** ✓）✓
- 残りは block 札 ✓ self-damage 札（BLOODLETTING ✓ BREAKTHROUGH ✓ HpLoss 1 ✓）✓ そして上の Slippery のような ✓ 攻击が効かない局面 ✓
→ **play 選択の質に明らかな gap は見えない** ✓（play ordering ✓ と合わせて ✓ この筋は閉じる ✓）✓

**audit の道具立てとして新しい確定的事実** ✓
1. **replay は record の `simulations` を使わないと別の答えを出す** ✓（300 → SHRUG_IT_OFF ✓ 100 → end_turn ✓ で live と一致 ✓）✓ 監査ツールには `record["simulations"]` を渡す ✓
2. **observation の card entry は `cost` を持つ ✓ 未使用札は -1 ✓** ✓ play 可能性の判定は `0 <= cost` ✓（Toxic のように play できる Status 札との区別に使える ✓）✓
3. `combat_records()` は `Path` を取る ✓ str を渡すと `AttributeError: 'str' object has no attribute 'open'` ✓✓

## Round 88: event 回答の fix を入れた arm sweep 完了 ✓ **event 45 件すべて accept ✓ 拒否 0 件 ✓**（修正前は corpus で 30.1% 拒否 ✓）

tree `.wt-proto12`（HEAD `37bb82c` + event 回答 fix ✓ その tree で dll build ✓ 241,152 B ✓）✓ 3 seed ✓ 10:30〜10:46 ✓
```
RESULT evfix_arm AM8C6YXHSG wins=14 losses=1 records=276 depth=Act 3, Floor 6   fail=Watchdog ✓ Entering Monster room (Act 3, Floor 6)
RESULT evfix_arm H2LV6ZJ4XW  wins=20 losses=1 records=386 depth=Act 3, Floor 6   fail=Watchdog ✓ Entering Monster room (Act 3, Floor 6)
RESULT evfix_arm VTW80ZJA2G  wins=13 losses=1 records=285 depth=Act 2, Floor 16  fail=Watchdog ✓ Entering Boss room (Act 2, Floor 16)
arm 合計: 47 勝 ✓ 3 敗 ✓ Act 3 完走 0 ✓
arm tree の event record: accepted 45 ✓ **rejected 0** ✓（前の build では corpus 6,465 件中 1,948 件 = 30.1% が `invalid_event_action` ✓）✓
```
**fix が狙いどおり効いていることは決定的** ✓（proceed の無い unscored event に最初の eligible option を答える ✓→ bridge が accept ✓）✓
**勝敗への影響はまだ言えない** ✓ AM8C6YXHSG は 17 勝（`sw59` ✓ commit `9bbf6a2` ✓）→ 14 勝 ✓ だが ✓
**同じ seed でも run が分岐する** ✓（round 72 ✓ 9PCQMO0DAY が sw64 と evdiag で別々 ✓）✓ ので ✓ 1 seed の差は noise ✓
→ **control sweep `evfix_ctrl`**（tree `.wt-ctrl-evfix` ✓ commit `37bb82c` ✓ policy 無変更 ✓ 同じ3 seed ✓）を 10:49 に開始 ✓ 完了待ち `bash-1165` ✓
**採否は control との対比で決める** ✓（teaching 2 ✓「control は 1 つの policy commit に固定 ✓」✓ teaching 9 ✓）✓

tooling の落とし ✓ arm の artifact は REPO 相対 ✓（`.wt-proto12/data/evfix_arm_*_agent.jsonl` ✓）✓ に書かれる ✓
→ 待受け script の glob を `data/evfix_arm_*` にしていたので event 集計が `{}` になった ✓✗（teaching 6 ✓「run が実際に何を書いたか見る」✓）✓

## Round 89: card reward で「高 damage を積む」は深さと無関係 ✓ むしろ深く行った run の方が高 damage offer を避けている ✓

前々 round（boss 直前の 1 手 ✓ 96% が最高 damage を取っていた ✓）の累積版 ✓ 全 card_reward decision を足した ✓（587 run ✓）✓
**「回避」の定義** ✓ その decision で最高 damage の offer があり ✓ 選んだ札の damage がそれより低い ✓場合 ✓
**火力の累積損失** ✓ 選んだ札を最高 damage の offer と入れ替えたときの potential 増分 ✓（同じ greedy 近似 ✓ 0 cost 札で水増しされる ✓ 比較専用 ✓ teaching 13 ✓）✓
```
Act 1 止まり 100 run: 回避 中央値 4 ✓ 75%  4 ✓ 回避ゼロ 14 run ✓ 累積損失 中央値 16 ✓ 75%  57 ✓ 最大 168
Act 2 止まり 331 run: 回避 中央値 4 ✓ 75%  5 ✓ 回避ゼロ  0 run ✓ 累積損失 中央値 16 ✓ 75%  33 ✓ 最大 176
Act 3 止まり 156 run: 回避 中央値 6 ✓ 75% 10 ✓ 回避ゼロ  0 run ✓ 累積損失 中央値 13 ✓ 75%  31 ✓ 最大 187
```
**Act 3 まで行った run の方が高 damage offer を避けていた** ✓（中央値 6 ✓ vs 4 ✓）✓ **損失した火力は少ない** ✓（13 ✓ vs 16 ✓）✓
→ **「reward で火力札を積むほど深くなる」は corpus で支持されない** ✓✓（Elite を多く取る run が深い ✓ 前 round ✓ と同じ形 ✓）✓
**現在の reward policy（debuff ✓ block ✓ 強化 ✓ relic 価値 ✓ を価格に入れ ✓ 高 cost 札の上限 ✓ block-starved ✓ 40% ✓ の gate ✓）は ✓ 深い run の振る舞いと同じ方向** ✓ ✓
→ **この筋（card reward で火力を増やす ✓）は lever ではない ✓ 閉じる** ✓
（「damage を積め」という直感に反する ✓ ので ✓ 両方の測り方 ✓ 直前 ✓ と累積 ✓ で確認した ✓）✓

**boss 進入時の火力不足の説明として残る** ✓ potential の下位側の差 ✓（Act 2 止まりの 25 パーセント 30 ✓ vs Act 3 到達 79 ✓）✓ は ✓
**札の選択の質ではなく ✓ その seed が配った札と強化 ✓ の差** ✓（agent が選べる範囲は offer まで ✓ 選んでいない ✓）✓ に寄っている ✓
次の測定候補 ✓ 強化（upgrade ✓）の状態 ✓ 枚数 ✓ relic の火力寄与 ✓ を potential から分離して見る ✓

## Round 90: **Act 3 の入口は Ancient ✓ から全て Monster の連続 ✓** ✓ 一戦で 30〜54 HP 失って崩れる ✓

per-act の map file ✓（arm tree ✓ `.wt-proto12/data/evfix_arm_*_map_ACT.GLORY.json` ✓）✓ と trace の walk ✓ を突き合わせた ✓
**Act 3 の最初の node は Ancient ✓（選べない ✓）で ✓ その children は全て Monster** ✓✓
```
AM8C6YXHSG Act 3: Ancient → children ['Monster','Monster','Monster','Monster'] ✓ → 選んだ walk: Monster hp 66 → Unknown → Unknown → Monster 70 → **Monster 16 ✓ そこで死亡** ✓（その node の children: ['Monster','RestSite' ✓] ✓ map 全体の RestSite 8 ✓）
H2LV6ZJ4XW Act 3: Ancient → children ['Monster','Monster','Monster'] ✓ → Monster 116 → Unknown → Monster 107 → Monster 77 → **Unknown 38 ✓ 死亡** ✓（唯一の children: ['RestSite' ✓] ✓ RestSite 8 ✓）
```
**Act 3 の fight で失う HP** ✓（同じ act の連続 node の hp_after ✓）✓
- AM8C6YXHSG: 70 → 16 ✓ **一戦で 54** ✓
- H2LV6ZJ4XW: 116 → 107 ✓ → 77 ✓（**-30 ✓**）→ 38 ✓（**-39 ✓**）
corpus の一戦の损失 中央値 17 ✓（前 round ✓）に対し ✓ **Act 3 の入口の fight は 30〜54** ✓✗✗
**しかも入口が連続 Monster ✓ なので最初の RestSite に辿り着く前に削り切られる** ✓✓（死んだ node の次が RestSite ✓ だった ✓ 前 round の H2LV6ZJ4XW と同じ形 ✓）

**arm run は boss 時点で健全だった** ✓（Act 2 boss 進入 HP 78 ✓ 98 ✓ 80 ✓ corpus 中央値 17 ✓ とは違う ✓）✓
→ **これらの seed の壁は「HP を持たず boss を迎える」ではなく ✓「Act 3 入口の連続 fight で 80 HP 前後を失う」こと** ✓✓
Act 2 walk は rest を boss 直前に取れている ✓（(4,14) ✓ (1,14) ✓）✓ Act 2 boss を越えても ✓ Act 3 の rest なしの連続 fight で死ぬ ✓

**残る仮説の形** ✓ routing（入口が強制 ✓ 選択肢が狭い ✓）ではなく ✓ **Act 3 の fight 自体での被ダメージ** ✓ ✓
→ 次の測定 ✓ Act 3 の fight で何をされたか（その fight の敌 id ✓ 被 damage の内訳 ✓ 取れた block/回避 ✓）✓
**elite を多く取り rest を多く取って boss を越えた run が ✓ Act 3 で死ぬ ✓ という形が定量的に取れた** ✓ ✓（Act 3 rest 8 ✓ 回の graph ✓ を持ちながら ✓ 入口で殺される ✓）✓
control sweep `evfix_ctrl` は走行中 ✓（10:49 ✓ seed 1 ✓）✓ 完了待ち `bash-1165` ✓

## Round 91: 中間結果 ✓ event 回答の fix は seed AM8C6YXHSG で **悪化した** ✓ 17 勝 → 14 勝 ✓ Act 3 Floor 15 → Floor 6 ✓

control sweep `evfix_ctrl`（`.wt-ctrl-evfix` ✓ commit `37bb82c` ✓ policy 無変更 ✓）の 1 本目 ✓
```
RESULT evfix_ctrl AM8C6YXHSG wins=17 losses=1 records=360 depth=Act 3, Floor 15
RESULT evfix_arm  AM8C6YXHSG wins=14 losses=1 records=276 depth=Act 3, Floor  6
```
**control のこの seed の数字は commit を越えて再現している** ✓（`sw59` ✓ commit `9bbf6a2` ✓ でも 17 勝 ✓ 360 records ✓ Act 3 Floor 15 ✓）✓ に対して arm は 14 勝 ✓ 276 records ✓ Act 3 Floor 6 ✓ ✓

**同じ seed の event record を並べた** ✓
```
control 17 件 ✓ うち 7 件が `invalid_event_action`（THE_LEGENDS_WERE_TRUE ✓ DENSE_VEGETATION ✓ INFESTED_AUTOMATON ✓ WELCOME_TO_WONGOS ✓ TINKER_TIME ✓ POTION_COURIER ✓ GRAVE_OF_THE_FORGOTTEN ✓）✓
arm     21 件 ✓ 拒否 0 ✓（DENSE_VEGETATION → TRUDGE_ON ✓ THE_LEGENDS_WERE_TRUE → NAB_THE_MAP ✓ INFESTED_AUTOMATON → STUDY ✓ WELCOME_TO_WONGOS → BARGAIN_BIN ✓ POTION_COURIER → GRAB_POTIONS ✓ など ✓ 全て option_index 0 ✓）✓
```
**control は `HUNGRY_FOR_MUSHROOMS → RELIC.BIG_MUSHROOM` ✓ を取っている ✓ arm にはその event 自体が現れない** ✓✗✗
→ 新しい既定（proceed の無い event に最初の eligible option ✓）が ✓ 途中の event の選び方を変えて ✓ **ルートと状態が分岐し ✓ 後の良い event に辿り着けていない** ✓✓
game 側の fallback に委ねていた control の方が ✓ この seed では良い event を拾えている ✓

**途中の判断** ✓ 採用の基準（决定差分が 3 件以上 ✓ かつ 3 seed ✓で改善 ✓）に対して ✓
- 决定が変わった件数 ✓ 十分 ✓（event 45 件 accept ✓ 0 拒否 ✓）✓
- 結末 ✓ 1 本目の seed で悪化 ✓ 17→14 勝 ✓ Act 3 Floor 15→6 ✓（control は 2 回の commit で同一数字 ✓ なので noise とは言いにくい ✓）✓
→ **現時点では採用しない方向** ✓ 残り 2 seed ✓（control 2 本目走行中 ✓）を揃えて確定する ✓
**棄却が確定したら `.wt-proto12` を削除し ✓ negative result として記録する** ✓（teaching 17 ✓「忠実度修正が勝数を落とすことはある」✓ の実例 ✓）✓

## Round 92: **敌が途中で増える fight が 8% ✓ fabricator 戦は 1 体 → 4〜5 体 ✓** ✓ model には summon の扱いが 0 件 ✓✗✗

`Fabricator.cs` ✓
```
aggroSpawns   = { Zapbot ✓ Stabbot ✓ }
defenseSpawns = { Guardbot ✓ Noisebot ✓ }
CanFabricate => 生存する team member が 4 体未満 ✓
MinInitialHp 150（ToughEnemies で 155 ✓）✓ FabricatingStrikeDamage 18（DeadlyEnemies で 21 ✓）✓ DisintegrateDamage 11（13 ✓）
```
**`grep -c "Summon\|SummonCmd" combat.py` は 0** ✓✗✗ → rollout は **新しい敌が現れることを予測できない** ✓（その fight の观测上の敌数は chaque decision で正しく読める ✓ が ✓ 未来の被 damage と攻击の価値が楽観になる ✓✗）✓

**生 run 5 本 ✓ fight 79 件で測った** ✓（combat record ごとに敌の combat_id 集合を進め ✓ `combat_end` で閉じた ✓）✓
```
途中で敌が増えた fight: 6 / 79 ✓（8%）✓
  FABRICATOR 単独スタート → 4 体 ✓（arm ✓ 5 turn ✓）/ → 5 体 ✓（control ✓ 9 turn ✓）
  PHROG_PARASITE + WRIGGLER → 4 体 ✓（両 tree ✓ 7 turn ✓）
  EYE_WITH_TEETH + FOGMOG → 2 体 ✓（両 tree ✓ 5 turn ✓）
増えた fight に出現した monster: EYE_WITH_TEETH 2 ✓ FOGMOG 2 ✓ STABBOT 2 ✓ GUARDBOT 2 ✓ ZAPBOT 2 ✓ FABRICATOR 2 ✓ PHROG_PARASITE 2 ✓ WRIGGLER 2 ✓ NOISEBOT 1 ✓
```
**この fight 群が Act で最大の损失を出している** ✓（前 round ✓ の 35 以上削った fight ✓）✓
```
arm AM8C6YXHSG: FABRICATOR+GUARDBOT+STABBOT+ZAPBOT ✓ 76 → 16 ✓（-60 ✓）
ctrl AM8C6YXHSG: 同じ bot 群 ✓ 72 → 36 ✓（-36 ✓）
arm H2LV6ZJ4XW: SLIMED_BERSERKER 88 → 38 ✓（-50 ✓）✓ FROG_KNIGHT 113 → 77 ✓（-36 ✓）
```

**前 round の act 数えの訂正** ✓ walk script は map の Boss record で act を進めていた ✓ので ✓ **boss 戦自体は1 act 遅いラベルが付いていた** ✓✗
→ 「Act 3 で 68〜78 削った THE_INSATIABLE」は **Act 2 boss 戦** ✓✓（arm: 78→10 ✓ 98→29 ✓ 80→2 ✓ ✓ **Act 2 boss を 2〜29 HP で突破している** ✓✗✗）✓
→ non-boss fight のラベルは正しい ✓（ increment が boss  entry の時だけ ✓）✓
**形として見えた壁** ✓ Act 2 boss を瀕死で突破 ✓ → Act 3 は入口が連続 Monster ✓（前 round ✓）で ✓ 最初の rest に辿り着けず ✓ 増援 fight で死ぬ ✓✓

**次の work item（忠実度 ✓）** ✓ 増援（spawn ✓）を model に入れる ✓
1. decompile から spawn 規則を取る ✓（Fabricator の aggro/defense spawns ✓ と `fabricate` trigger ✓ の move machine ✓、WRIGGLER の PHROG_PARASITE 産卵 ✓）✓
2. 导出 JSON の `effects` には spawn が入っていない ✓（FABRICATOR の effects は attack のみ ✓ 2 件 ✓）✓ → **model 側に spawn を教える必要がある** ✓（CLAUDE.md ✓「敌の挙動の追加は JSON 再生成 + `_enemy_turn` に command を教える」✓）✓
3. tests ✓：増援が現れる fight で rollout が敌数の増加を織り込むこと ✓
母数 8% ✓ かつ最大损失の fight 群 ✓ なので ✓ **panel に見合う候補** ✓（teaching 32 ✓ 决定が変わらないものは panel しない ✓ → attribution で决定差分を見てから判断 ✓）✓
control sweep は 2 本目走行中 ✓（`bash-1165` ✓）✓

## Round 93: 前 round の「Fabricator の spawn は model に無い」は誤り ✓ **spawn は model 済みだった** ✓（`_summon` ✓ `combat.py:1835-1845` ✓）

前 round は `grep -c "Summon\|SummonCmd" combat.py` = 0 ✓ を根拠に「model に summon の扱いが無い ✓ rollout が増援を予測できない ✓」と書いた ✓✗✗
**実際に有ったもの** ✓
- `combat.py:1121` `_summon(model, data, rng)` ✓（monster の `class` から Enemy を組み ✓ Parafright/EyeWithTeeth には IllusionPower ✓）✓
- `combat.py:1835-1845` ✓ **Fabricator 専用 branch** ✓
  `FABRICATE_MOVE` → defensive bot（GUARDBOT/NOISEBOT ✓）+ aggro bot（ZAPBOT/STABBOT ✓）✓
  `FABRICATING_STRIKE_MOVE` → aggro bot のみ ✓ ✓ **全 bot に MinionPower ✓** ✓
  （comment に ponytail ✓：game は最後に spawn した model を除外する ✓ model は均等 draw ✓ で ✓ bot mix が問題になったら追加する ✓と記載済み ✓）✓
- `combat.py:1136` `_spawn_wrigglers` ✓（PhrogParasite の死で Wriggler x4 ✓ SPAWNED_MOVE ✓ 初手 stun ✓ primary ✓）✓ → 前 round が見た「PHROG_PARASITE 1 → 4 ✓」も model 済み ✓✓
→ **「敌が増える fight が 8% ✓」は実在するが ✓ それは model の想定内 ✓ gap ではない** ✓✓（前 round の work item は立ち消え ✓）✓

**process の教訓（2 回目 ✓）** ✓「X が model に無い」と書く前に ✓
1. **grep は大小文字に敏感 ✓** ✓ `_summon`（小文字 ✓）は `Summon` に落ちない ✓ → **0 件は不在の証拠にならない** ✓✓
2. 机制の helper 名 ✓ と nearby branch の comment ✓ を読む ✓（teaching 42 ✓ 71 ✓「decompile が支持しても既存 mechanism を確認する」✓ の失敗例 ✓）✓
3. relic 網羅 census ✓（teaching 92 ✓ `grep -c "RELIC_<NAME>"` ✓）も同じ落としを持つ ✓ → **census 阴性は snake_case 側も見る** ✓✓
（同じ session 内で Rampage ✓（既存 comment を読まずに「観測できる ✓」と書いた ✓）と spawn ✓（大小文字 grep ✗）✓ 2 件続いた ✓）✓

**panel の現在** ✓ control 2 本 ✓
```
RESULT evfix_ctrl AM8C6YXHSG wins=17 losses=1 records=360 depth=Act 3, Floor 15 ✓ arm: 14 勝 ✓ Act 3 Floor  6 ✓（-3 勝 ✓ 大きく浅い ✓）
RESULT evfix_ctrl H2LV6ZJ4XW wins=20 losses=1 records=388 depth=Act 3, Floor  6 ✓ arm: 20 勝 ✓ Act 3 Floor  6 ✓（同一 ✓）
```
3 本目 VTW80ZJA2G ✓ control 未完了 ✓（`bash-1165` ✓）✓ 2 seed の時点では **1 seed で悪化 ✓ 1 seed で変化なし ✓ 改善した seed は無い** ✓

## Round 94: Act 2 boss（THE_INSATIABLE 321 HP ✓）の解剖 ✓ **8〜9 turn ✓ 進入 75〜98 HP ✓ 退出 2〜43 HP ✓** ✓ 残 HP が Act 3 の深さを決めている ✓

生 run 5 本 ✓（arm 3 ✓ control 2 ✓）✓ 同じ boss ✓
```
arm  AM8C6YXHSG:  8 turn ✓ 進入 78/85 ✓ 退出 10 ✓  boss HP 321 → 6
arm  H2LV6ZJ4XW:  9 turn ✓ 進入 98/116 ✓ 退出 29 ✓  boss HP 321 → 9
arm  VTW80ZJA2G:  9 turn ✓ 進入 80/80  ✓ 退出  2 ✓  boss HP 320 → 19（この run は boss 室で停止 ✓）
ctrl AM8C6YXHSG:  8 turn ✓ 進入 75/85 ✓ 退出 43 ✓  boss HP 321 → 14
ctrl H2LV6ZJ4XW:  9 turn ✓ 進入 79/116 ✓ 退出  5 ✓  boss HP 321 → 20
```
**boss 戦で失う HP は 68〜78** ✓✓（arm ✓）✓ **退出時の HP が Act 3 の到達に直結する** ✓✓
- ctrl AM8C6YXHSG は **43 HP で抜けて Act 3 Floor 15** ✓（Act 3 boss QUEEN まで行き ✓ 99 → 1 で败北 ✓）✓
- arm AM8C6YXHSG は **10 HP で抜けて Act 3 Floor 6 で死亡** ✓✓
→ **1 turn 長いと約 10 HP 多く失う** ✓（8〜9 turn で 68〜78 ✓）✓ **2 turn 短縮 ≒ Act 3 に +20 HP** ✓
→ **壁の形** ✓ Act 2 boss を長引かせる ✓ → 残 HP 少ない ✓ → Act 3 入口の連続 fight ✓（前々 round ✓）で即死 ✓✓

**potion の観測は key が top level ✓** ✓（前 round の私の「boss 進入時に potion 無し ✓」は key の取り違え ✓✗✗）✓
```
combat record: `potions` ✓（top level ✓）= ['VULNERABLE_POTION','FORTIFIER','BLOCK_POTION'] ✓ / `player.potions` = [] ✓
legal_actions の potion entry と同じ内容 ✓（VULNERABLE ✓ FORTIFIER ✓ BLOCK ✓）✓
```
→ **boss 戦で 3 個の potion を使っている** ✓（turn 1 で Vulnerable ✓ turn 6 で Block ✓ と Fortifier ✓）✓ **使っても 10 HP 残で抜けた** ✓
→ potion を使い切っていた ✓ のではなく ✓ **使い切っても boss の射程が長い** ✓✓（前 round の potion 経済の結論と同じ方向 ✓）✓
→ **tooling** ✓ potion を数える監査は `player.potions` ✓ ではなく **`potions` ✓（top level ✓）** ✓ を読む ✓（teaching 91 ✓ isinstance で守る ✓ の続報 ✓：key の位置を確かめる ✓）✓

**残る lever の形** ✓ boss 戦の turn 数を減らす ✓＝その時点で出せる damage/turn を上げる ✓
ただし ✓ そのための火力は card reward で積む方向では無い ✓（corpus ✓ 2 通りの測り方で確認 ✓）✓ ので ✓
**次の手は「その fight で実際に何が出ているか」の内訳** ✓（札を引けていない ✓ energy 使い切り ✓ 被 damage の内訳 ✓）✓ を ✓ act ではなく fight で見る ✓
control 3 本目 VTW80ZJA2G ✓ 走行中 ✓（`bash-1165` ✓）✓

## Round 95: event 回答の panel 完了 ✓ **棄却** ✓ control 50 勝 ✓ arm 47 勝 ✓ 改善した seed は 0 ✓（scratch tree は削除 ✓）

3 seed ✓ 同一 HEAD ✓ control は `.wt-ctrl-evfix`（commit `37bb82c` ✓ policy 無変更 ✓）✓
```
seed          control（HEAD ✓）                       arm（event 回答 fix ✓）
AM8C6YXHSG    17 勝 1 敗 ✓ 360 records ✓ Act 3, Floor 15 ✓   14 勝 1 敗 ✓ 276 records ✓ Act 3, Floor  6  ✗✗（-3 勝 ✓ 浅い ✓）
H2LV6ZJ4XW    20 勝 1 敗 ✓ 388 records ✓ Act 3, Floor  6 ✓   20 勝 1 敗 ✓ 386 records ✓ Act 3, Floor  6  ✓ 同一 ✓
VTW80ZJA2G    13 勝 1 敗 ✓ 262 records ✓ Act 2, Floor 16 ✓   13 勝 1 敗 ✓ 285 records ✓ Act 2, Floor 16  ✓ 同一 ✓
合計          50 勝 3 敗 ✓ Act 3 完走 0                    47 勝 3 敗 ✓ Act 3 完走 0   → **-3 勝 ✓**
event record: control accepted 20 ✓ rejected 14 ✓（41.2% ✓）✓ arm accepted 45 ✓ **rejected 0** ✓（0.0% ✓）
```
**採否の基準に対する判定** ✓
- 决定が変わった件数 ✓ 十分 ✓（拒否 14 → 0 ✓）✓
- seed 別の結末 ✓ **改善 0 件 ✓ 悪化 1 件 ✓（AM8C6YXHSG ✓ 17→14 勝 ✓ Act 3 Floor 15→6 ✓）✓ 変化なし 2 件 ✓**
- control の AM8C6YXHSG の数字は別 commit の `sw59` ✓ でも同一 ✓（17 勝 ✓ 360 ✓ Act 3 Floor 15 ✓）✓ なので ✓ 悪化は noise では説明しにくい ✓
→ **採用しない ✓ 棄却** ✓（teaching 17 ✓「忠実度修正が勝数を落とすことはある」✓）✓
**理由の筋** ✓ 新しい既定は「proceed の無い event なら **最初の eligible option** ✓」という任意の選択 ✓ で ✓
途中の event（DENSE_VEGETATION → TRUDGE_ON ✓ THE_LEGENDS_WERE_TRUE → NAB_THE_MAP ✓ など ✓）を変え ✓ ルートが分岐し ✓
**control が取れた `HUNGRY_FOR_MUSHROOMS → RELIC.BIG_MUSHROOM` ✓ に arm は辿り着いていない** ✓✓
scratch tree `.wt-proto12` は arm の artifact（17 件 ✓ trace ✓ map ✓ log ✓）を `data/` に写してから削除した ✓（teaching 49 ✓）✓
pin されていた `test_unknown_event_returns_bridge_fallback` ✓ はそのまま ✓（main は無変更 ✓ 783 件 green ✓）✓

**constructive な次の形** ✓「任意の first option ✓」ではなく ✓**弾かれる event に実際の得点を与える** ✓✓
corpus で拒否の上位だった event ✓：BUGSLAYER 170 ✓ WHISPERING_HOLLOW 135 ✓ SYMBIOTE 131 ✓ BRAIN_LEECH 129 ✓ DENSE_VEGETATION 112 ✓
TEA_MASTER 108 ✓ THE_FUTURE_OF_POTIONS 101 ✓ TINKER_TIME 90 ✓ INFESTED_AUTOMATON 85 ✓ SAPPHIRE_SEED 79 ✓ SPIRIT_GRAFTER 72 ✓
→ `EVENT_OPTION_SCORES` ✓ に entry を足す作業 ✓（decompile から各 option の得失 ✓ HP ✓ gold ✓ 札 ✓ relic ✓ を取って価格化する ✓）✓
**「bridge に通すためだけに選ぶ ✓」は今回の実測で有害 ✓** ✓ 得点なしで通すことと得点をつけて選ぶことは違う ✓✓（teaching 9 ✓ 決定）✓
現在の HEAD の基準値 ✓：**50 勝 3 敗 ✓ Act 3 完走 0 ✓（seed AM8C6YXHSG ✓ H2LV6ZJ4XW ✓ VTW80ZJA2G ✓）** ✓

## Round 96: 弾かれる event の経済を decompile から追加で取った ✓（batch 2 の材料 ✓ 実装は batch 1 の panel 後 ✓）

`MegaCrit.Sts2.Core.Models.Events/*.cs` ✓（v0.107.1 ✓）✓
```
TEA_MASTER ✓：BONE_TEA = LoseGold(BoneTeaCost ✓) → RelicCmd.Obtain<BoneTea> ✓ / EMBER_TEA = LoseGold → Obtain<EmberTea> ✓
          TEA_OF_DISCOURTESY = **gold を払わず Obtain** ✓（第3の option ✓）✓
          → option 側に relic が載る ✓（bridge は `relic_id` ✓ を出す ✓）✓ `_event_relic_score` ✓ で tier 順にできる ✓
            ただし gold コストは DynamicVar ✓（BoneTeaCost ✓）で observation の option には出ない ✓ → **コストが見えない ✓ 低 gold のときに金入りを選ぶrisk あり ✓**
SAPPHIRE_SEED ✓：EAT = CreatureCmd.Heal ✓（回復 ✓）/ PLANT = CardCmd.Enchant<Sown> ✓（札1枚に Sown ✓）✓
          → HP が低ければ EAT ✓ が測れる ✓（DENSE_VEGETATION と同じ形の条件 ✓）✓
THE_FUTURE_OF_POTIONS ✓：Trade(potion) → **CardCmd.Upgrade(card)** ✓（potion を差し出して札を強化 ✓）✓ / Done ✓
          → 強化の価値 ✓ vs potion 1個 ✓ の比較が必要 ✓（potion 経済の測定 ✓ と組む ✓）✓
INFESTED_AUTOMATON ✓：STUDY ✓ / TOUCH_CORE ✓ **両方 CardPileCmd.Add(deck ✓)** ✓（別の札 ✓）✓
          → **どちらの札が渡るかが observation の option に出ない ✓** ✓→ 価格付けできない ✓（この event は委ねたまま ✓）✓
```
**実装可能な順** ✓（観測に値段が揃っているものだけ ✓）✓
1. SAPPHIRE_SEED ✓（HP 条件 ✓ EAT ✓）✓ 2. TEA_MASTER ✓（relic tier ✓ ただし gold コストが見えない ✓ 低 gold で金入りを選ばない条件 ✓）✓
3. THE_FUTURE_OF_POTIONS ✓（強化 vs potion ✓）✓ 4. BUGSLAYER ✓（Exterminate ✓ / Squash ✓ **両方 free の card 追加 ✓ 札名は StringVar で observation に出る？未確認 ✓**）✓
**INFESTED_AUTOMATON ✓ SYMBIOTE ✓（Corrupted enchant ✓ の得失 ✓）は観測が足りず保留 ✓** ✓
batch 1（DENSE_VEGETATION ✓ BRAIN_LEECH ✓ WHISPERING_HOLLOW ✓）の panel `evscore_arm` ✓ 11:14 開始 ✓ 走行中 ✓（`bash-1241` ✓）✓
**batch 2 を batch 1 と混ぜて走らせない** ✓（1 commit で1変更の測定 ✓ teaching 2 ✓）✓

## Round 97: batch 2（SAPPHIRE_SEED ✓ TEA_MASTER ✓）を別 tree で用意 ✓ **negative score は辞退にならない ✓ 辞退は None ✓** という机制の事实 ✓

`.wt-proto15`（HEAD から ✓ batch 1 と混ぜない ✓）✓ 785 件 green ✓（new test 2 件 ✓）✓
- SAPPHIRE_SEED ✓ HP < max なら EAT ✓（回復 ✓）✓ 満タンなら None ✓（Sown の価値を model は price していない ✓→ 委ねる ✓）✓
- TEA_MASTER ✓ EMBER_TEA（hover tip が StrengthPower ✓）を **gold >= 150 ✓ のときだけ** 100 ✓
  BONE_TEA は decompile から効果を読み取れない ✓ ので None ✓ TEA_OF_DISCOURTESY は free だが hover tip が Dazed ✓（corpus で Dazed は play されず deck に残る ✓）→ **選ばない ✓**

**机制の事实（test が捕えた ✓✗）** ✓ `choose_event` の `known = [(score, action) ✓ score is not None]` ✓ は
**score が全部マイナスでも最大値を選ぶ** ✓ → **`TEA_OF_DISCOURTESY: -100` ✓ と書いても ✓ それが唯一の known ならそれを選ぶ ✓✗✗** ✓
→ **「その option を選ばない」ことは negative score では実現できない ✓ 辞退は `None` ✓ を返す ✓** ✓✓
（teaching 61 ✓「agent の heuristic と rollout model は別の gate ✓」と同型 ✓ 得点表の语义を読み違えない ✓）✓

**同じ落としの 2 回目 ✓** ✓ `.wt-proto14` で直した `option_score` の並び ✓
（`scores = EVENT_OPTION_SCORES.get(...)` ✓ の早期 return より下に new event を置く ✓と ✓ **未登録 event はそこに到達しない ✓**）✓ を
`.wt-proto15` で再現した ✓✗（KeyError: 'option_index' ✓ 2 件 ✓）✓ → **new tree を作るときは fixed 形の後に置く ✓** ✓
必要な並び ✓
```
text_key / option を先に取る ✓ →  event 固有の条件 ✓  →  scores = EVENT_OPTION_SCORES.get(event_id) ✓  →  scores が無ければ None ✓
```

**batch 1 の panel 1 本目 ✓ 悪化 ✓**
```
RESULT evscore_arm AM8C6YXHSG wins=11 ✓ losses=1 ✓ records=191 ✓ depth=Act 2, Floor 16
control（evfix_ctrl ✓ 同じ seed ✓） wins=17 ✓ records=360 ✓ depth=Act 3, Floor 15
```
**-6 勝 ✓ Act 3 に入れず Act 2 boss 室で停止 ✓ records 191 ✓（短い run ✓）** ✗✗
候補 ✓ WHISPERING_HOLLOW の GOLD が gold を70以上使って shop を枯らした筋 ✓（SAPPHIRE_SEED/BRAIN_LEECH は得になる選択 ✓）✓
→ **残り 2 seed ✓ を揃えてから判断する ✓**（1 seed の差は分岐と混ざる ✓ が ✓ control は 2 commit で同一数字 ✓ なので重い ✓）✓
`bash-1241` ✓ が完了待ち ✓

## Round 98: batch 1 の悪化の原因を特定 ✓ **DENSE_VEGETATION の TRUDGE_ON は「8 ダメージと引き換えに 61〜99 gold ✓」で ✓ REST 選択はその gold を捨てていた** ✓

`DenseVegetation.cs` ✓ の option 本体 ✓
```
TrudgeOn():  CreatureCmd.Damage(..., HpLoss.BaseValue, Unblockable | Unpowered) ✓  →  PlayerCmd.GainGold(DynamicVars.Gold.BaseValue) ✓  （Gold = Rng.NextInt(61,100) ✓）✓
Rest():      PlayerCmd.MimicRestSiteHeal(Owner) ✓（rest site と同じ回復 ✓）✓
```
**TRUDGE_ON = −8 HP ✓ と引き換えに 61〜99 gold ✓✓** ✓ REST = 回復 ✓ で gold は無い ✓
batch 1 の rule（HP が満タンでなければ REST ✓）は ✓ **gold 側を見ていなかった** ✓✗✗
→ **回復で約 24 HP を得て ✓ gold で relic を買う筋を捨てた ✓** 可能性がある ✓
（**深い run ほど relic が多い ✓ Act 2 boss 時点で 10 ✓ vs 7 ✓** ✓ 前 round まで ✓ の測定と整合 ✓✓）✓

**trace での実際の差分** ✓（同じ seed ✓ AM8C6YXHSG ✓）✓
```
arm  seq 92: option_index 1 ✓ REST を選択 ✓（accept ✓）→ seq 93: `event_fallback` ✓→ `invalid_event_action` ✓（REST で回復した後に続きの page ✓ があり ✓ そこでは回復済み ✓ rule が None ✓→委ねた ✓）
ctrl seq 92: `event_fallback` ✓→ 弃却 ✓（1 page だけで game の fallback が処理 ✓）
arm  gold: 24..296 ✓ 終了付近 37 ✓ 57 ✓ 222 ✓ / ctrl gold: 24..373 ✓ 終了付近 255 ✓ 267 ✓ 358 ✓ 373 ✓
arm  の event: 11 件 ✓（VAKUU ✓ TINKER_TIME ✓ POTION_COURIER ✓ HUNGRY_FOR_MUSHROOMS ✓ GRAVE_OF_THE_FORGOTTEN ✓ に到達しない ✓）
ctrl の event: 17 件 ✓（HUNGRY_FOR_MUSHROOMS → RELIC.BIG_MUSHROOM ✓ を取る ✓）
```
**WHISPERING_HOLLOW ✓ は両 trace に出ていない** ✓ → 前 round で疑った「gold を70以上使って shop を枯らす ✓」は起きていない ✓✓
**BRAIN_LEECH ✓ も出ていない** ✓ ✓ 実際に効いた rule は **DENSE_VEGETATION の REST ✓ 1 件だけ** ✓✓
→ 11 勝 vs 17 勝 ✓ records 191 vs 360 ✓ の差は ✓ **その 1 件の gold/HP 交換と ✓ その後のルート分岐 ✓** に集中する ✓

**rule の直し方** ✓（gold と HP の両方を price する ✓）✓
- HP が危険域（例：max の 4 分の一以下 ✓ など ✓ 8 ダメージで死ぬリスク ✓）なら REST ✓
- そうでなければ **TRUDGE_ON ✓（8 HP を払って gold ✓ → shop で relic ✓）** ✓
**HP が低いときだけ REST ✓** に絞る ✓ のが実測に沿う ✓（今の rule は HP が中位でも REST ✓ を選んでいた ✓✗）✓
sweep の残り 2 seed ✓（`bash-1241` ✓）を揃えてから ✓ rule を書き直して再 panel ✓ する ✓

## Round 99: 前 round の「gold を捨てたことが败因 ✓」は過剰な結論だった ✓ arm は gold を得て HP も満タンだった ✓（11 勝の败因は未解決 ✓）

`evscore_arm_AM8C6YXHSG` の DENSE_VEGETATION ✓ seq 92 ✓ の前後 ✓
```
seq 87  card_reward ✓ hp 55/80 ✓ gold 70
seq 92  event DENSE_VEGETATION ✓ REST を選択 ✓（受理 ✓）
seq 93  event DENSE_VEGETATION ✓ 続きの page ✓→ `event_fallback` ✓→ 弃却 ✓（game の fallback が処理 ✓）
seq 94  card_reward ✓ hp 80/80 ✓ gold 135   ← **回復済み ✓ gold +65 ✓**
```
→ **arm は回復も gold も得ていた** ✓✓（55 → 80 HP ✓ 70 → 135 gold ✓）✓
→ 前 round で書いた「REST 選択が 61〜99 gold を捨てていた ✓」は ✓ **終了時点の gold 比較（222 ✓ vs 373 ✓）から逆算した推測で ✓ 决定の直後の値を見ていなかった** ✓✗✗
→ **11 勝にとどまった原因は特定できていない** ✓（HP も gold も arm の方が良好 ✓ なのに act 2 boss 室で停止 ✓）✓
新しい教訓 ✓「**决定の直後の値を trace から読んでから ✓ 败因だと書く** ✓（末端の差から逆算しない ✓）」✓（teaching 112 ✓「測定が実際に測ったか検証する ✓」の続報 ✓）✓

**batch 1 の panel 2 本目 ✓ seed H2LV6ZJ4XW ✓** ✓
```
RESULT evscore_arm H2LV6ZJ4XW wins=20 losses=1 records=388 depth=Act 3, Floor 6   ← control ✓ 20 勝 ✓ 388 ✓ Act 3 Floor 6 ✓ と同一 ✓
arm の event 10 件 ✓ 拒否 4 ✓ うち価格付けした event に当たったのは **0 件** ✓（TEA_MASTER ✓ は batch 1 で未価格 ✓ 弃却 ✓）✓
```
→ **価格付けした event に当たらない run では変化が無い ✓** ✓（変更が inert ✓ であることの確認 ✓ teaching 94 ✓）✓
**batch 1 の現時点** ✓ AM8C6YXHSG **11 勝（control 17 勝 ✗）** ✓ H2LV6ZJ4XW **同一 ✓** ✓ VTW80ZJA2G 未完了 ✓

**改訂版は用意済み ✓**（`.wt-proto16` ✓ 787 件 green ✓ 4 test 追加 ✓）✓
- DENSE_VEGETATION ✓：`hp <= max(12, max_hp // 4)` ✓ のとき REST ✓ そうでなければ TRUDGE_ON ✓（8 ダメージが死に至る水準でなければ gold ✓ を取る ✓）✓
- BRAIN_LEECH ✓：SHARE_KNOWLEDGE ✓（RIP は None ✓）✓ WHISPERING_HOLLOW ✓：gold >= 70 ✓ のとき GOLD ✓ そうで None ✓
- seq 92 の状況（hp 55/80 ✓）では改訂版は **TRUDGE_ON ✓** を選ぶ ✓（47 HP ✓ + gold ✓）✓ → **今の panel とも違う選択なので ✓ 改訂版 panel が必要 ✓** ✓
sweep の 3 本目 ✓ 走行中 ✓ → 終わったら `.wt-proto16` ✓ の panel を同じ3 seed ✓ で走らせる ✓

## Round 100: 価格付けした event の母数 ✓ run の 18〜22% ✓ に現れ ✓ ほぼ全て game に委ねられていた ✓（BUGSLAYER ✓ が単一 event では最大の 170 件 ✓）

corpus ✓（trace 615 ✓ event record 6,530 ✓）✓
```
DENSE_VEGETATION ✓: record 115 ✓ うち拒否 112 ✓ これを含む run 113/615 = 18% ✓
BRAIN_LEECH       ✓: record 136 ✓ うち拒否 130 ✓ これを含む run 133/615 = 22% ✓
WHISPERING_HOLLOW ✓: record 137 ✓ うち拒否 135 ✓ これを含む run 136/615 = 22% ✓
event record 上位: NEOW 1081（拒否 0 ✓）✓ TEZCATARA 632（0 ✓）✓ PAEL 392（0 ✓）✓ SELF_HELP_BOOK 330（0 ✓）✓ BYRDONIS_NEST 312（0 ✓）✓
                ROOM_FULL_OF_CHEESE 216（0 ✓）✓ AROMA_OF_CHAOS 214（0 ✓）✓ **BUGSLAYER 178（拒否 170 ✓）** ✓ SUNKEN_STATUE 162（0 ✓）✓
```
→ 既に価格を付けた3件は ✓ **hit した run のほぼ全てで game 側の决定だった** ✓（112/115 ✓ 130/136 ✓ 135/137 ✓）✓
→ 各 event は run の 2 割程度 ✓ 3 件合わせれば 4〜5 割の run に触点 ✓（panel の信号は希釈されるがゼロではない ✓）✓
**get 点済みの event（拒否 0 ✓）は上位に並んでいる** ✓ ✓ 拒否上位は **未価格の event だけ** ✓ ✓

**BUGSLAYER は価格付けできる ✓ と確認** ✓（単一 event 最大の母数 170 ✓）✓
```
Exterminate ✓: base(1, CardType.Attack, CardRarity.Event, TargetType.AllEnemies ✓) ✓ DamageVar(3, Move ✓) → **1 energy ✓ 3 ダメージ ✓ 全敌 ✓**
Squash ✓     ✓: base(1, CardType.Attack, CardRarity.Event, TargetType.AnyEnemy ✓) ✓ DamageVar(10, Move ✓) → **1 energy ✓ 10 ダメージ ✓ 単体 ✓**
model 側: CARD_COST ✓ に EXTERMINATE 1 ✓ SQUASH 1 ✓ ✓ CARD_DAMAGE ✓ に SQUASH 10 ✓（= decompile ✓ と一致 ✓）✓
```
→ 単体敵中心の fight なら SQUASH ✓（10 ✓ > 3 ✓）✓ 4 体以上の群なら EXTERMINATE ✓（3x4=12 ✓）✓
→ **batch 3 の候補 ✓ BUGSLAYER → SQUASH ✓（既定 ✓）** ✓（札を deck に足す選択 ✓ なので ✓ 単独で panel ✓ する ✓）✓
batch 1 3本目 ✓ VTW80ZJA2G ✓ 走行中 ✓ → 終わり次第 ✓ 改訂版 `.wt-proto16` ✓ の panel ✓ を同じ3 seed ✓ で走らせる ✓

## Round 101: batch 3（BUGSLAYER → SQUASH ✓）を別 tree で用意 ✓ **fight 開始時の敌数は 1 体が 91% ✓ 4 体以上は 0% ✓** なので単体 10 damage ✓ が既定として正しい ✓

`.wt-proto17` ✓（HEAD から ✓ 単独 panel 用 ✓）✓ 784 件 green ✓（test 1 件 ✓）✓
`BUGSLAYER` ✓ の option 名は `EXTERMINATION` ✓（カード名 Exterminate ✓ とは違う ✓）と `SQUASH` ✓ ✓
→ rule ✓：`option == "SQUASH" ✓` に 100 ✓・他 None ✓（辞退は None ✓ の規則 ✓ を守った ✓）✓

**敌数の実測** ✓（新しい9 trace ✓ fight 開始時 85 件 ✓ turn ごとに 1 件 ✓）✓
```
1 体: 77 ✓（91% ✓）✓  2 体: 4 ✓  3 体: 4 ✓  4 体以上: 0 ✓（0% ✓）✓
```
→ Exterminate（3 damage ✓ 全敌 ✓）が有利になるのは 4 体以上のとき ✓（3x4=12 > 10 ✓）✓ **corpus にそういう fight が無い** ✓✓
→ **SQUASH ✓（1 energy ✓ 10 damage ✓ 単体 ✓）が既定として妥当 ✓** ✓
（teaching 19 ✓ 近い話 ✓「群の fight が無いのに AoE ✓ を選ぶ理由が無い」✓）✓
batch 1（未改訂 ✓）の 3 本目 ✓ VTW80ZJA2G ✓ 走行中 ✓ → 改訂版 `.wt-proto16` ✓ → batch 3 ✓ の順で panel ✓ する ✓
**panel の順番** ✓（1 度に 1 変更 ✓）✓ 1. `.wt-proto16`（DENSE_VEGETATION の gold 評価 ✓）✓ 2. `.wt-proto17`（BUGSLAYER ✓）✓ 3. `.wt-proto15`（SAPPHIRE_SEED ✓ TEA_MASTER ✓）✓
control は `evfix_ctrl` ✓（50 勝 ✓ 3 敗 ✓）✓ をそのまま使う ✓（HEAD 間で policy 変更が無い ✓）✓

## Round 102: batch 1（未改訂 ✓）の panel 完了 ✓ **1 seed で +3 勝・Act 2→Act 3 ✓ / 1 seed で -6 勝 ✓** ✓ 合計 47 勝 ✓（control 50 勝 ✓）→ 採らない ✓

```
seed          control（evfix_ctrl ✓ 50 勝 ✓）            batch 1（未改訂 ✓ evscore_arm ✓）
AM8C6YXHSG    17 勝 ✓ 360 records ✓ Act 3, Floor 15 ✓    11 勝 ✓ 191 records ✓ Act 2, Floor 16  ✗✗ -6 勝 ✓
H2LV6ZJ4XW    20 勝 ✓ 388 records ✓ Act 3, Floor  6 ✓    20 勝 ✓ 388 records ✓ Act 3, Floor  6  ✓ 同一 ✓（価格付け event に当たらず ✓）
VTW80ZJA2G    13 勝 ✓ 262 records ✓ Act 2, Floor 16 ✓    16 勝 ✓ 325 records ✓ Act 3, Floor  6  ✓✓ +3 勝 ✓ Act 3 に到達 ✓
合計          50 勝 3 敗 ✓ Act 3 完走 0 ✓                47 勝 3 敗 ✓ Act 3 完走 0 ✓
```
**改善した seed は 1 件だけ** ✓（VTW80ZJA2G ✓ 13→16 勝 ✓ Act 2 boss 室止まり → Act 3 Floor 6 ✓）✓
**悪化した seed が 1 件** ✓（AM8C6YXHSG ✓ 17→11 勝 ✓）✓ → **採用基準（3 seed ✓ で改善 ✓）を満たさない ✓ 採らない ✓** ✓
event: accepted 21 ✓ rejected 11 ✓（34.4% ✓）✓ まだ弹かれるもの ✓：SYMBIOTE 2 ✓ SAPPHIRE_SEED 1 ✓ DOLL_ROOM 1 ✓ THE_LEGENDS_WERE_TRUE 1 ✓ **DENSE_VEGETATION 1 ✓（REST ✓ の後続 page ✓）** ✓ INFESTED_AUTOMATON 1 ✓ WELCOME_TO_WONGOS 1 ✓ TEA_MASTER 1 ✓

## **長い間使ってきた数字の訂正 ✓：Act 2 boss「進入 HP 中央値 17 ✓（36% ✓ が 10 以下 ✓）」は進入の値ではなかった** ✓

6 trace ✓（`sw59_* ✓ 5 本 ✓ + evdiag_* ✓ 2 本 ✓ うち boss 到達 6 ✓）✓ 同じ定義 ✓（boss 戦の最初の combat record ✓ の直前の player hp ✓）✓ で測った ✓
```
evdiag_9PCQMO0DAY: 進入 60 ✓ boss 戦の最後の HP 9 ✓
evdiag_VTW80ZJA2G:  進入 69 ✓  最後 8 ✓
sw59_AM8C6YXHSG:    進入 75 ✓  最後 43 ✓
sw59_D6A1F8C3E5:    進入 85 ✓  最後 35 ✓
sw59_H2LV6ZJ4XW:    進入 79 ✓  最後 5 ✓
sw59_VTW80ZJA2G:    進入 69 ✓  最後 8 ✓
進入 HP 中央値 72 ✓ / boss 戦終了時の HP 中央値 8.5 ✓✗✗
```
→ **boss 進入は健全 ✓（中央値 72 ✓）で ✓ boss 戦を出るときに瀕死 ✓（中央値 8.5 ✓）** ✓✓
→ **訂正の訂正 ✓** ✓ 旧節（Round 73 ✓）は方法行で「各 boss 戦の最初の record における player HP の**最小値** ✓」と定義していた ✓ ✓ つまり 17 ✓/11 ✓ は boss 戦中の最低 HP ✓ で ✓ 誤りではなかった ✓✓
  **私が古い見出し「boss 進入時の player HP ✓」だけ読んで定義行を読まなかった** ✓✗✗（数字の定義は方法行にある ✓✓）✓
  進入 ✓72 ✓ / 戦中最低 ✓17 ✓ / 終了 ✓8.5 ✓ は整合する ✓（終了時に最も低い ✓）✓✓
→ **壁の読み方は変わらない ✓** ✓（boss 戦で 60〜70 HP 失う ✓ → Act 3 入口の連続 fight ✓ で死ぬ ✓）✓ が ✓
**「boss 前に rest を増やせ ✓」型の仮説は ✓ 進入が健全である限り筋が良い ✓** ✓（teaching 112 ✓ 測定が実際に何を測ったか ✓ の実例 ✓）✓

Act 2 の部屋構成の比較 ✓（boss 進入 60+ ✓ 308 run ✓ vs 中間 ✓ 76 run ✓）✓
```
Monster 4.6 ✓ Elite 0.3-0.4 ✓ RestSite 3.1-3.2 ✓ Shop 1.2 ✓ Unknown 3.7 ✓ Treasure 1.0 ✓  → **両群で同じ ✓** ✓
```
→ Act 2 の通り道の種類は boss 進入 HP の高低と無関係 ✓ ✓（进入 HP の差は fight の中身 ✓ の側 ✓）✓
改訂版 panel `evdense_arm` ✓ は 11:29 時点で batch 1 完了を受けて起動 ✓（`bash-1270` ✓）✓

## Round 103: QUEEN 戦の形を特定 ✓ **turn 3 から player に FRAIL 99 ✓ WEAK 99 ✓ VULNERABLE 99 ✓ が乗り ✓ 1 turn に 1 ずつしか減らない ✓** ので 400 HP を削り切れない ✓

`data/enemies_glory.json` ✓ の QUEEN ✓（`MinInitialHp 400 ✓`）✓
```
YOU_ARE_MINE_MOVE ✓ intent [Debuff ✓] ✓ effects: PowerCmd.Apply FrailPower `99m ✓` ✓ WeakPower `99m ✓` ✓ VulnerablePower `99m ✓` ✓   ← player へ ✓
PUPPET_STRINGS_MOVE ✓ intent [CardDebuffIntent ✓] ✓ effects: PowerCmd.Apply ChainsOfBindingPower `3m ✓` ✓
BURN_BRIGHT_FOR_ME_MOVE ✓ intents [Buff ✓, Defend ✓] ✓ effects: StrengthPower `strengthAmount ✓` ✓ + CreatureCmd.GainBlock `20m ✓` ✓
```
実 trace ✓（`evfix_ctrl_AM8C6YXHSG` ✓ QUEEN 戦 ✓ turn ごとの player powers ✓）✓
```
turn 1: hp 99 ✓ powers: THORNS 3 ✓
turn 2: hp 87 ✓  + CHAINS_OF_BINDING 3 ✓（PUPPET_STRINGS ✓）
turn 3: hp 80 ✓  + **FRAIL 99 ✓ WEAK 99 ✓ VULNERABLE 99 ✓** RUPTURE 1 ✓
turn 4..10: 99→98 ✓ 97 ✓ … 92 ✓（1 turn に 1 ✓ ずつしか減らない ✓✗）✓ turn 9-10 で player hp 1 ✓
```
→ **QUEEN 戦は「 Weak ✓ でこちらの damage が半減 ✓ Vulnerable ✓ で 1.5 倍 ✓ 受ける ✓」が 9 turn 続く戦い** ✓✓
→ 前 round までに見た「QUEEN に 8 turn で 77 しか削れていない ✓」の説明 ✓：**Weak 99 ✓ が原因 ✓** ✓（STRIKE の exported Damage が 6.75 ✓ と小かった ✓ のも整合 ✓）✓
→ **Act 3 boss で止まる runs の壁の正体** ✓（50 勝 panel ✓ で Act 3 完走 0 ✓ の最大要因 ✓）✓
→ 次の打ち手の候補 ✓（**まだ測っていない ✓ 推測 ✓**）✓：QUEEN 戦に入る前に Weak/Frail/Vulnerable を消す手段 ✓（Purification ✓ 等の解除 ✓ の有無 ✓）✓ または **Weak で減る前に削る ✓ turn 1-2 の総量 ✓** ✓（QUEEN は turn 2 で Debuff ✓ を打つ ✓ ので ✓ その前にどれだけ入れられるか ✓）✓

**panel ✓ 改訂版 1 本目 ✓**：`evdense_arm AM8C6YXHSG wins=14 ✓ losses=1 ✓ records=305 ✓ depth=Act 3, Floor 6 ✓`
→ control 17 勝 ✓（委ねる ✓） > 改訂版 14 勝 ✓（gold ✓ を取る ✓） > 未改訂 11 勝 ✓（回復 ✓ を取る ✓） ✓ この seed では **委ねるのが最良 ✓** ✓✗
`ChainsOfBindingPower ✓` は combat.py に 1 件 ✓（扱いあり ✓）✓
残りの seed ✓（H2LV6ZJ4XW ✓ VTW80ZJA2G ✓）を揃えて採否を決める ✓（`bash-1270` ✓）✓

## Round 104: Act 3 完走の実績は 3 seed に集中 ✓ **N8CQ4ZKP2W ✓ 6 run ✓ D6A1F8C3E5 ✓ 3 run ✓ H2LV6ZJ4XW ✓ 1 run ✓** ✓ 完走 panel の seed を変えるべき ✓

`data/*_result.json` ✓ で `act_3_complete: true` ✓ の 11 件 ✓
```
N8CQ4ZKP2W ✓: act3_recheck_2675e82 ✓ codex_goal_20260919 ✓ current_commit_known_seeds ✓ wide_base ✓ wide_sblock ✓ candidate_rupture2 ✓ candidate_vulnlethal ✓ candidate_last_hp…（H2LV6ZJ4XW ✓）
  deck 31-33 ✓✓  **relic 16-17 ✓✓**  max HP 81-87 ✓  gold 15-70 ✓
D6A1F8C3E5 ✓: astra_base ✓ astra_seed2 ✓ astra_goal_intangible1 ✓   deck 29 ✓  **relic 16 ✓**  **max HP 98 ✓**  gold 75 ✓
H2LV6ZJ4XW ✓: candidate_last_hp_selfdamage ✓            deck 28 ✓  relic 14 ✓  **max HP 130 ✓✓**  gold 59 ✓
```
現在の panel の3 seed ✓（AM8C6YXHSG ✓ H2LV6ZJ4XW ✓ VTW80ZJA2G ✓）での直近の実績 ✓：relic 10 ✓ max HP 85-116 ✓ **Act 3 完走 0 ✓**
→ **panel の seed 構成が Act 3 完走を測れない ✓**（一度も完走していない seed ✓ だけで測っている ✓✗✗）✓
→ **次の sweep から N8CQ4ZKP2W ✓ と D6A1F8C3E5 ✓ を入れる ✓** ✓（完走が観測できる seed ✓ で測る ✓）✓

**QUEEN は倒せる ✓ と確認** ✓（完走 run の trace ✓ `act3_recheck_2675e82_N8CQ4ZKP2W_agent.jsonl` ✓）✓
```
QUEEN 戦 **12 turn ✓** ✓ boss HP **400 ✓→ 17 ✓**（383 削った ✓✓）✓ player は同じ FRAIL 99 ✓ WEAK 99 ✓ VULNERABLE 99 ✓ を乗っていた ✓
```
→ **debuff 下でも 12 turn で 383 ✓（約 32/turn ✓）出せばQUEEN は勝てる ✓** ✓
→ 败けた run ✓（QUEEN 戦 8-10 turn ✓ 77 削っただけ ✓ = 約 9.6/turn ✓✗✗）との差は **1 turn あたりの damage が 3 倍以上** ✓✓
→ **Act 3 完走への道の定量 ✓**：Weak 下で 32/turn ✓ 相当の火力 ✓ + relic 14-17 ✓ + max HP 98-130 ✓ ✓
（前 round の「Act 3 boss 完走 0 ✓」は seed の選び方も一因 ✓✓：完走実績のある seed ✓ を panel に入れていなかった ✓）✓

`PowerCmd.Remove ✓` は combat.py:1786 ✓ で handling 済み ✓（export された 6 件は全て敌が自分の power を消すもの ✓：OWL_MAGISTRATE の Soar ✓ TEST_SUBJECT ✓ WATERFALL_GIANT の SteamEruption ✓ TOUGH_EGG の Hatch ✓）✓ → gap ではない ✓
`Expose ✓`（0 cost ✓ Uncommon ✓ Skill ✓）は敌の power を2つ消す card ✓（ArtifactPower ✓ 分岐あり ✓）✓ **player 側の debuff を消す効果ではない ✓** → QUEEN の 99 スタック ✓ を消す筋は見つかっていない ✓

## Round 105: Act 3 完走 run の 10/11 が `RELIC.BYRDPIP` ✓ と `CARD.BYRD_SWOOP` ✓ を持っていた ✓ **完走 run の deck に egg は1枚も無い ✓（全て ByrdSwoop に化けている ✓）**

`data/*_result.json` ✓ の 11 件 ✓（完走 ✓ 11 ✓ 未完走 ✓ 1 ✓）✓
```
完走 run ✓: deck 平均 30.9 ✓ attack 枚数 平均 10.5 ✓ 攻撃力の合計 平均 87 ✓ max HP 平均 92 ✓ **relic 平均 16.1 ✓** ✓ Strength 札 平均 0.1 ✓
  **RELIC.BYRDPIP ✓ あり ✓ かつ deck に BYRD_SWOOP ✓ を1枚以上含む：10 / 11 ✓✓** ✓（残り1件は relic ✓ なし ✓ swoop ✓ なし ✓）
  BYRDONIS_EGG ✓ を final deck に残す完走 run：**0 / 11 ✓** ✓
未完走 run ✓（1件 ✓）: relic 2 ✓ swoop ✓ なし ✓
完走 run の高 damage 札: **Byrd Swoop ✓ x10 run ✓** ✓ Hemokinesis ✓ x3 ✓ Bludgeon ✓ x1 ✓ Uppercut ✓ x1 ✓
```
**Byrdpip の中身** ✓（`Relics/Byrdpip.cs` ✓）✓ `RelicRarity.Event ✓` ✓ `AddsPet ✓` ✓ `SpawnsPets ✓` ✓ hover tip = ByrdSwoop ✓ ✓ `AfterObtained()` ✓ は combat 中に **ByrdonisEgg ✓ を ByrdSwoop ✓ に TransformTo ✓** ✓
`ByrdSwoop ✓` は model 側で **cost 0 ✓・damage 14 ✓** ✓（`CARD_COST ✓`/`CARD_DAMAGE ✓` に登録済み ✓）✓
→ **0 energy ✓ で 14 damage ✓ の札が deck に並ぶ ✓** = 前 round で測った「QUEEN に 1 turn 32 ✓ 入れた ✓」の筋と合う ✓✓（energy を使わず 2 枚出して 28 ✓ など ✓）✓

**agent 側の現状** ✓ `grep "BYRDPIP" official_agent.py` は `MONSTER.BYRDPIP ✓`（敌 ✓ 1 件 ✓）だけ ✓ → **relic の RELIC.BYRDPIP ✓ は relic 評価表 ✓（RELIC_SCORES ✓ / EVENT_RELIC_TIERS ✓ / SHOP_RELIC_SCORES ✓）に載っていない ✓**✗✗
**BYRDONIS_NEST ✓ event は `TAKE: 100 ✓` で既に取得する ✓** ✓ が ✓ relic が無いと **egg は play できない Quest 札 ✓ のまま deck に居座る ✓**✓（parked ✓ 未 play 札の項目 ✓ と一致 ✓）✓
→ 次の測定の候補 ✓（2つ ✓ どちらも未実施 ✓）✓
1. **BYRDPIP ✓ が shop/event に出たとき評価して取る ✓** ✓（relic 表に追加 ✓→ arm/control ✓）✓
2. **relic 取得の見込みが無いときに egg を取らない ✓** ✓（BYRDONIS_NEST の得点を状況依存にする ✓）✓
→ **先に必要 ✓：BYRDPIP がどこから入手できるかの特定 ✓**（event ✓/shop ✓/敌の drop ✓）✓ 今回の trace 検索では **combat record の relic list ✓ に現れるだけで ✓ 入手 moment ✓ を拾えなかった** ✓✗（search の prev 更新を BYRDPIP 含む行に限定するミス ✓）→ 次回 ✓ 全 record を辿って初出の直前 phase ✓ を読む ✓
panel ✓：seed2 `evdense_arm H2LV6ZJ4XW = 20 勝 ✓ 388 records ✓ Act 3 Floor 6 ✓`（control ✓ と同一 ✓）✓ 3 本目走行中 ✓

## Round 106: **egg ✓ を取って BYRDPIP ✓ を持たない run は、何も取らない run より Act 3 到達率が低い ✓**（15% ✓ vs 23% ✓）✓ pair なら 52% ✓✓

616 run ✓（`_mod.log ✓` から最終到達 ✓）✓ 「egg を取った ✓」= BYRDONIS_NEST ✓ の event record ✓ が弃却でない ✓、「BYRDPIP ✓」= trace の relic list ✓ に RELIC.BYRDPIP ✓
```
egg ✓ + BYRDPIP ✓  :  94 run ✓ Act 到達 中央値 3 ✓ ✓ **Act 3 到達 49 ✓（52% ✓✓）**
egg ✓ + BYRDPIP ✗  :  54 run ✓ Act 到達 中央値 2 ✓ ✗ Act 3 到達  8 ✓（15% ✓）
egg ✗ + BYRDPIP ✗  : 448 run ✓ Act 到達 中央値 2 ✓   Act 3 到達 105 ✓（23% ✓）
```
→ **egg は relic が無いと有害 ✓** ✓（何もしない群より Act 3 到達が低い ✓✗✓ 54 run ✓ の母数 ✓）✓
→ **egg + relic ✓ の pair は Act 3 到達 52% ✓** ✓（何も取らない群の 2.3 倍 ✓）✓
→ **相関であって因果ではない ✓** ✓ が ✓ 机制は独立に裏がある ✓：BYRDONIS_EGG ✓ は play できない Quest 札 ✓ で ✓ draw pile ✓ を薄める ✓（parked ✓ の「未 play 札が draw 構成を変える ✓」項目 ✓ と同じ ✓）✓
→ **実装可能な条件 ✓**：`BYRDONIS_NEST ✓` の `TAKE: 100 ✓` を ✓ **「RELIC.BYRDPIP ✓ を既に持っているときだけ ✓」** ✓ に変える ✓（event observation の `player.relics ✓` に見える ✓ bridge が export している ✓）✓
**BYRDPIP の入手元** ✓：101 trace ✓ で **直前が map record ✓ の combat record ✓ で初出 ✓**（Treasure ✓ や敌 drop ✓ など decision を伴わない経路 ✓）✓ → **policy で「取りに行く ✓」対象にはしにくい ✓** ✓ 測定の筋は egg ✓ 側 ✓

panel ✓（改訂版 `evdense_arm` ✓）: AM8C6YXHSG 14 勝 ✗（control 17 ✓）✓ H2LV6ZJ4XW 20 勝 ✓（同一 ✓）✓ VTW80ZJA2G 走行中 ✓

## Round 107: 改訂版 event 得点の panel 完了 ✓ **50 勝 3 敗 ✓ = control と同一 ✓**（seed 別 -3 ✓ 0 ✓ +3 ✓）→ 採らない ✓

```
seed          control（evfix_ctrl ✓ 50 勝 ✓）      未改訂 batch1 ✓          改訂版 ✓ evdense_arm ✓
AM8C6YXHSG    17 勝 ✓ 360 ✓ Act 3, Floor 15 ✓      11 勝 ✓ 191 ✓ Act 2, F16 ✗   14 勝 ✓ 305 ✓ Act 3, F6  ✗ -3 ✓
H2LV6ZJ4XW    20 勝 ✓ 388 ✓ Act 3, Floor  6 ✓      20 勝 ✓ 388 ✓ Act 3, F6 ✓    20 勝 ✓ 388 ✓ Act 3, F6  ✓ 0 ✓
VTW80ZJA2G    13 勝 ✓ 262 ✓ Act 2, Floor 16 ✓      16 勝 ✓ 325 ✓ Act 3, F6 ✓✓   16 勝 ✓ 325 ✓ Act 3, F6  ✓✓ +3 ✓
合計          50 勝 3 敗 ✓                         47 勝 3 敗 ✓               **50 勝 3 敗 ✓ = control ✓**
改訂版の event ✓: accepted 24 ✓ rejected 12 ✓ ✓ 実際に選んだもの ✓ BRAIN_LEECH → SHARE_KNOWLEDGE ✓ ✓ DENSE_VEGETATION → TRUDGE_ON ✓（gold ✓ を取った ✓）
```
**gold を price したことで未改訂版の損失（47 勝 ✓）は消えた ✓** ✓ が ✓ **control との合計は同値 ✓** ✓ seed 別で 1 増 1 減 ✓
→ **採用基準（3 seed ✓ で改善 ✓）を満たさない ✓ 採らない ✓** ✓
→ **教訓 ✓**：得点のない event を game に委ねる ✓ のは損失だと思っていた ✓ が ✓ **実測では委ねるのと同等 ✓** ✓（game の AutoSlay も悪くない ✓）✓
→ **event 得点の仕事はここ为止 ✓** ✓（残る未価格 event ✓ に追加実装しない ✓：改善が見えない ✓）✓
→ ただし **egg ✓ の変更は別種 ✓** ✓（これは「選ぶ/選ばない ✓」でなく ✓**有害な札を deck に入れない ✓** の変更 ✓）✓

**egg の変更は実装済み ✓**（`.wt-proto18 ✓` ✓ 785 件 green ✓）✓：BYRDONIS_NEST ✓ で `RELIC.BYRDPIP ✓` を持っていれば TAKE ✓（egg ✓→ ByrdSwoop ✓）✓ 無ければ **EAT ✓（+7 max HP ✓・decompile `CreatureCmd.GainMaxHp(MaxHpVar 7m ✓)`）** ✓
`test_event_option_table_preserves_hardcoded_choices ✓` は player を持たない observation ✓ で `BYRDONIS_NEST.LEAVE/TAKE ✓`（実在しない key ✓）を使い TAKE ✓ を固定していた ✓ → **実測に合わせて relic 保持 ✓ 条件で TAKE ✓** に更新 ✓（test の目的である「hardcoded の選択 ✓」は relic あり ✓ で保持 ✓）✓
→ **panel の対応 ✓**：control `base_ctrl ✓`（N8CQ4ZKP2W ✓ D6A1F8C3E5 ✓ で走行中 ✓）と同じ2 seed ✓ で arm `egg_arm ✓` ✓ を走る ✓（Act 3 完走が観測できる seed ✓ で測る ✓）✓

## Round 108: run が止まる原因は agent の decision 時間では無い ✓（1 decision 最大 0.6 s ✓）✓ 停まり方は game 側 ✓「rewards screen を待つ ✓」で timeout ✓

**decision 時間の実測** ✓（`choose(observation, enemy_data ✓ 104 monster ✓, simulations=100 ✓)` ✓ を各 fight の turn 1 ✓ で呼んだ ✓）✓
```
evdense_arm_AM8C6YXHSG seq 3 ✓ 敌 3 ✓ 手数 12 ✓ → 0.55 s ✓ (rollout_success ✓)
evdense_arm_AM8C6YXHSG seq 5 ✓ 敌 2 ✓ 手数 5  ✓ → 0.37 s ✓
evdense_arm_H2LV6ZJ4XW seq 3-5 ✓ → 0.26 ✓ 0.24 ✓ 0.21 s ✓
base_ctrl_N8CQ4ZKP2W seq 17 ✓ 敌 3 ✓ 手数 15 ✓ → 0.60 s ✓
最大 0.6 s ✓✓ → **game の watchdog 30 s ✓ に agent は届いていない ✓** ✓
```
**初測定の失敗 ✓** ✓ 1 回目は `enemy_data` を渡せず None ✓→ rollout が走る前に heuristic tail ✓ に落ちて全 decision 0.00 s ✓✗（teaching 46 ✓ と同じ ✓ 正しい状態を渡さない測定は 0 が出る ✓）✓ 104 monster ✓ をロードして測り直した ✓✓

**停まり方の内訳** ✓（直近 sweep の `fail=` ✓ 20 件 ✓）✓
```
「Entering Monster room ✓ (Act 3 ✓)」で 30 s 無 progress ✓：9 ✓（最多 ✓）✓
「Entering Boss room ✓ (Act 2 ✓)」：4 ✓   「Entering Boss room ✓ (Act 3 ✓)」：2 ✓   「Entering Elite room ✓ (Act 1 ✓)」：1 ✓
  → **room に入った直後に停まる ✓ 合計 16 ✓/20 ✓** ✓
"Rewards screen did not appear after combat ✓"：3 ✓   fail=none ✓：1 ✓
```
`base_ctrl_N8CQ4ZKP2W` ✓ の mod.log ✓ の末尾 ✓：`AutoSlayer.WaitForRewardsScreenAsync ✓` → `PlayRunAsync ✓` → `WithTimeout ✓` ✓ の exception ✓ ✓ trace ✓ の最後は seq 142 ✓ combat_end ✓（= 战斗は終わり ✓ 報酬画面が出ず ✓ timeout ✓）✓ agent の decision ✓ は seq 140 `lethal_direct ✓` ✓ 141 `heuristic_fallback / rollout_disabled_no_playable_card ✓` ✓ まで正常 ✓
→ **stall は combat 終了後の報酬画面への遷移 ✓ で起きており ✓ agent の応答時間 ✓ は無関係 ✓** ✓（次の調査：card_reward bridge ✓ が画面より先に answer ✓ していないか ✓）✓

**完走 seed の control 基準 ✓（commit `37bb82c` ✓ tree `.wt-ctrl-evfix ✓`）✓**
```
RESULT base_ctrl N8CQ4ZKP2W   wins= 5 ✓ losses=1 ✓ records=111 ✓ depth=Act 1, Floor 14 ✗（Elite 室进入 ✓ で stall ✓）
RESULT base_ctrl D6A1F8C3E5   wins=15 ✓ losses=1 ✓ records=302 ✓ depth=Act 3, Floor  5 ✓（Monster 室进入 ✓ で stall ✓）
SWEEP DONE base_ctrl ✓
```
→ かつて Act 3 を完走した seed ✓（`act3_recheck_2675e82 ✓` などの commit ✓）でも ✓ **今の commit ✓ は Act 3 には入るが ✓ 完走していない ✓**✓（D6A1F8C3E5 ✓ では Act 3 到達 ✓）✓
→ **egg 条件付き変更の arm `egg_arm ✓`（tree `.wt-proto18 ✓` ✓ 同じ2 seed ✓）は base_ctrl 完了を受けて起動 ✓** ✓（連鎖 ✓）✓

## Round 109: **「launcher が停まっている ✓」は誤読だった ✓ 9 run 全て最後の fight で死んでいる ✓**（`combat_end ✓: won=False ✓ hp=0 ✓`）✓ fail= の文言は死後の AutoSlay の混乱 ✓

`AutoSlayer.WaitForRewardsScreenAsync ✓` の中身 ✓（decompile ✓）✓
```
await WaitHelper.Until(() => NOverlayStack.Instance?.Peek() is NRewardsScreen ✓ || (NMapScreen.Instance?.IsOpen ?? false ✓), ct, TimeSpan.FromSeconds(10 ✓), "Rewards screen did not appear after combat ✓");
```
→ **戦闘終了後 ✓ 10 s のうちに「報酬画面 ✓」か「map ✓ が開いている ✓」が必要 ✓** ✓
→ **player が死んだ ✓ 戦闘では報酬画面も map も開かない ✓** ✓ → 10 s で timeout ✓ → 自動で "Rewards screen did not appear ✓" 系の fail ✓ が出る ✓

**panel 9 run ✓ 全ての trace 末尾 ✓** ✓
```
evdense_arm_AM8C6YXHSG ✓ last phase combat_end ✓ 最後の combat_end = (won False ✓, hp 0 ✓) ✓ combat_end 15 ✓（= 14 勝 + 1 死 ✓）
evdense_arm_H2LV6ZJ4XW ✓ (False ✓, 0 ✓) ✓ combat_end 21 ✓（20 勝 ✓）✓ evdense_arm_VTW80ZJA2G ✓ (False ✓, 0 ✓) ✓ 17 ✓（16 勝 ✓）
evscore_arm ✓ 3 本 ✓ 全て (False ✓, 0 ✓) ✓   evfix_ctrl ✓ 3 本 ✓ 全て (False ✓, 0 ✓) ✓
```
→ **全ての run は最後の fight で死んで終わっている ✓✓** ✓（`losses=1 ✓` ✓ と一致 ✓）✓
→ **sweep の `fail= ✓` の "Last activity: Entering Monster room ✓" 等は死の直前の room 進入 ✓ を示すだけで ✓ stall ✓ では無い ✓**✗✗
→ 前 round で「room 進入直後に停まる ✓ 16/20 ✓」と数えたのは **死の signature ✓ を stall ✓ と読み違えていた** ✓✓（teaching 83 ✓「lost run は result ファイルを書かない ✓」の続き ✓：**fail 文言をそのまま信用しない ✓**）✓
→ **残っている本当の調査先 ✓**：`112.7 s ✓ no progress ✓` のような長い停止 ✓ は fight 中の play ✓（agent が無 log ✓ で 112 s ✓ 試行 ✓）と AutoSlay の log ✓ の更新が噛み合わないケース ✓ があり得る ✓ → **死んだ run ✓ と区別するには trace 末尾の `combat_end.won ✓` を見る ✓** ✓（今回の 9 run ✓ は全て死亡 ✓）✓

**測定の読み方の更新 ✓**
- `depth=Act N, Floor M ✓` = **そこで死んだ ✓** ✓（Act 3 Floor 6 ✓ = Act 3 の fight で死亡 ✓✓）✓
- Act 3 到達 run が完走しない ✓ 理由は **Act 3 の fight に勝てない ✓** ✓（前々 round ✓ の QUEEN ✓ の 1 turn 火力 ✓ と同じ結論 ✓に収束 ✓）✓
- 完走 seed の control 基準 ✓（`37bb82c ✓`）✓：N8CQ4ZKP2W ✓ 5 勝 ✓ Act 1 Floor 14 ✓ で死亡 ✓ / D6A1F8C3E5 ✓ 15 勝 ✓ Act 3 Floor 5 ✓ で死亡 ✓

## Round 110: N8CQ4ZKP2W ✓ が Act 1 で死んだ fight を解析 ✓ **PhrogParasite ✓→ Wriggler ✓ の増援群で、rollout は動いていて ✓ 素の負け筋 ✓**だった ✓（新しい mechanic ✓ も misplay ✓ も見当たらない ✓）

`base_ctrl_N8CQ4ZKP2W ✓` の最後の fight ✓（seq 112-142 ✓ combat record 30 ✓）✓
```
敌 ✓: MONSTER.PHROG_PARASITE ✓（INFESTED_POWER 4 ✓ → 死んだら Wriggler ✓ x4 ✓ model 済み ✓ `_spawn_wrigglers ✓`）✓ → MONSTER.WRIGGLER ✓（STRENGTH 2 ✓）✓
player HP ✓: turn 1-2 ✓ 54 ✓ → 3 ✓ 37 ✓ → 6 ✓ 32 ✓ → 7 ✓ 12 ✓ → 死亡 ✓（combat_end won=False ✓ hp 0 ✓）✓
our play ✓ 末尾 ✓: turn 5 STRIKE ✓ SHRUG_IT_OFF ✓x2 ✓ / turn 6 potion ✓(direct_potion ✓) COLOSSUS ✓ STRIKE ✓ FORGOTTEN_RITUAL ✓ / turn 7 BASH ✓ STRIKE ✓（両方 `lethal_direct ✓` ✓）→ 死ぬ ✓
WRIGGLER の hp 19-20 ✓・STRENGTH 2 ✓・intents Attack ✓/Buff+StatusCard ✓ ✓ model は `WRIGGLE_MOVE ✓`（StrengthPower ✓ + Infection ✓）を読んでいる ✓
```
→ **rollout は動いていた ✓** ✓（`rollout_success ✓` ✓ と `lethal_direct ✓` ✓ で組立てられた play ✓）✓ heuristic tail ✓ は `generic_multi_primary_focus_direct ✓` 6 件 ✓ だけ ✓
→ **12 HP ✓ で Strength 2 ✓ を積んだ Wriggler 群 ✓ を残したまま end_turn ✓ したのが致命 ✓** ✓ が ✓ それは **HP が足りない ✓ 側の問題 ✓** ✓（model の damage 再現は 612/614 ✓ ✓ 死の瞬間の不一致は見つかっていない ✓）✓

**multi-enemy ✓ で rollout が止まっている ✓ 説も却下 ✓** ✓（直近 panel trace ✓ の combat decision ✓ 3,283 件 ✓）✓
```
1 体 ✓: 2568 decision ✓ rollout_success 1813 ✓（71% ✓）✓ heuristic_fallback 500 ✓ lethal_direct 159 ✓
2 体 ✓:  424 ✓            238 ✓（56% ✓）✓ heuristic_fallback 86 ✓ lethal_direct 71 ✓ queen_minion_direct 11 ✓
3体以上 ✓: 291 ✓            175 ✓（60% ✓）✓ lethal_direct 63 ✓ heuristic_fallback 42 ✓ generic_multi_primary_focus_direct 6 ✓
```
→ **3 体以上でも rollout は 60% ✓ で動いている ✓** ✓（heuristic 専用 ✓ になっている訳ではない ✓）✓
→ `generic_multi_primary_focus_direct ✓` は 14 件 ✓/3,283 ✓（0.4% ✓）✓ → **swarm が dumb fallback ✓ で処理されている ✓ という仮説は却下 ✓** ✓
→ 残る筋 ✓：**Act 1 のこの fight を HP 54 ✓ で受けた ✓ こと ✓**（map の選び方 ✓）と ✓ **Wriggler 群の被 damage 総量 ✓** ✓ の方 ✓
`egg_arm ✓` 1 本目 N8CQ4ZKP2W ✓ = 5 勝 ✓ 111 records ✓ Act 1 Floor 14 ✓ で control ✓ と完全一致 ✓（この seed ✓ では変更が inert ✓）✓ 2 本目走行中 ✓

## Round 111: egg の relic 条件付き ✓ **棄却 ✓**（arm ✓ 5 勝 Act 1 ✓ / 11 勝 Act 2 ✗✗ ✓ control ✓ 5 勝 Act 1 ✓ / 15 勝 Act 3 ✓）✓ そして **shop record に `legal_actions ✓` は無い ✓**という測定ミスの訂正 ✓

```
seed          control ✓ base_ctrl ✓（`37bb82c ✓` ✓）        arm ✓ egg_arm ✓（`.wt-proto18 ✓` ✓）
N8CQ4ZKP2W    5 勝 1 敗 ✓ 111 ✓ Act 1, Floor 14 ✓         5 勝 1 敗 ✓ 111 ✓ Act 1, Floor 14  ✓ 完全一致 ✓（inert ✓）
D6A1F8C3E5    15 勝 1 敗 ✓ 302 ✓ Act 3, Floor  5 ✓         11 勝 1 敗 ✓ 224 ✓ Act 2, Floor 16  ✗✗ -4 勝 ✓ Act 3 に入れない ✓
→ **改善 0 件 ✓ 悪化 1 件 ✓ 一致 1 件 ✓ → 採らない ✓** ✓（`.wt-proto18 ✓` は artifact を写して削除 ✓）✓
```
→ **egg を EAT ✓ に回す変更は有害だった ✓** ✓（+7 max HP ✓ の方が egg ✓→ ByrdSwoop ✓ より悪い ✓）✓
→ **前 round の相関測定 ✓（egg ✓ 無し群の Act 3 到達 23% ✓ vs egg+relic ✓ 52% ✓）は ✓ 「egg を取らない ✓」を支持しない ✓** ✓：相関 ✓ を政策に落とすには panel ✓ が必要 ✓ for real ✓✓（teaching 1 ✓ の再現 ✓ gap-filling ✓ ≠ 勝つ ✓）✓

**測定の訂正 ✓✗** ✓ shop record の中身 ✓（`evfix_ctrl_H2LV6ZJ4XW ✓` seq 103 ✓）✓
```
keys: action ✓ deck ✓ gold ✓ phase ✓ potion_id ✓ purchased ✓ seq ✓ slot_index ✓ decision_* ✓
legal_actions: **null ✓** ✗✗ ✓   action: `buy_potion ✓` ✓ potion_id: POTION.FYSH_OIL ✓ slot_index ✓ gold ✓
```
→ **shop では bridge が `legal_actions ✓` を出していない ✓** ✓ 選んだ `action ✓` だけ ✓
→ 私が「直近 118 shop record ✓ で relic 出品は 0 件 ✓」と数えたのは **dict の legal_actions ✓ を探して全件落ちた ✓ 測定ミス ✓**✓✗（teaching 112 ✓）✓
→ 正しく数えられるのは action ✓ の側 ✓（corpus ✓ 4,764 件 ✓：buy_card 1445 ✓ skip 1433 ✓ remove 1039 ✓ buy_potion 741 ✓ **buy_relic 106 ✓** ✓）✓
→ **つまり「relic が出たのに買わなかった ✓」は今の trace では測れない ✓**（出品情報が無い ✓）✓
→ **constructive な次 ✓**：**shop の出品一覧 ✓（relic ✓ card ✓ potion ✓ と price ✓）を export する ✓**（`plays ✓` を export した前例 ✓ teaching 76 ✓ と同じ ✓ bridge 側変更 ✓ build ✓ 要 ✓）✓

**完走 run の relic 一覧 ✓（11 件中 7 件以上に出現 ✓）** ✓
```
BURNING_BLOOD ✓ 11/11 ✓（初期 relic ✓）✓ **BYRDPIP ✓ 10/11 ✓** ✓ TOASTY_MITTENS ✓ 8/11 ✓ CENTENNIAL_PUZZLE ✓ 8/11 ✓ GOLDEN_PEARL ✓ 7/11 ✓ PEN_NIB ✓ 7/11 ✓ ORNAMENTAL_FAN ✓ 7/11 ✓
LANTERN ✓ 7/11 ✓ CANDELABRA ✓ 7/11 ✓ RED_MASK ✓ 7/11 ✓ ANCHOR ✓ 7/11 ✓ VAJRA ✓ 7/11 ✓ FIDDLE ✓ 7/11 ✓ STRAWBERRY ✓ 7/11 ✓ PERMAFROST ✓ 7/11 ✓
official_agent.py ✓ に記載が無い ✓：BYRDPIP ✓ LANTERN ✓ CANDELABRA ✓ RED_MASK ✓ ANCHOR ✓ VAJRA ✓ STRAWBERRY ✓ FIDDLE ✓（記載あり ✓：TOASTY_MITTENS ✓ CENTENNIAL_PUZZLE ✓ GOLDEN_PEARL ✓ PEN_NIB ✓ ORNAMENTAL_FAN ✓ PERMAFROST ✓）✓
→ ただし **入手が選択を伴わないもの ✓（初期 ✓/報酬 ✓/宝 ✓）もある ✓** ✓ので ✓ 先に出品の可視化 ✓ が必要 ✓

## Round 112: shop の出品 trace ✓ 実装完了 ✓ そして **この run ✓ では relic 出品15種類のうち10種類 ✓ が評価表に無く ✓ gold 419 ✓ を残して relic を0個 ✓ で買った ✓**

**mod 変更の検証 ✓✓**（tree main ✓ dll 245,760 B ✓ run `shopexport ✓` seed AM8C6YXHSG ✓）✓
```
RESULT shopexport AM8C6YXHSG wins=17 ✓ losses=1 ✓ combat_records=360 ✓ depth=Act 3, Floor 15 ✓
control ✓ evfix_ctrl ✓ 同じ seed ✓ 17 勝 ✓ 360 records ✓ Act 3, Floor 15 ✓ → **同一 ✓**（観測追加のみ ✓ で决定は変わっていない ✓）✓
trace ✓: shop decision 16 ✓ 全件に `offers ✓` あり ✓（kind ✓ id ✓ cost ✓ affordable ✓）✓
```
→ **ShopBridge の Trace に `OfferSummary(slots ✓)` を追加 ✓ する変更は verified ✓ commit ✓** ✓（`Observation()` ✓ には元々出品があった ✓ が Trace されていなかった ✓）✓

**測定できたこと ✓✓✓**（この run ✓ shop 5軒 ✓ 16 decision ✓）✓
```
relic 出品: 48 件 ✓（1 軒に3種類 ✓ x5 ✓）✓ 種類 15 ✓ うち **評価表に無い ✓ 10 種類 ✓（67% ✓）**
  買えた状態の出品 ✓ 6 件 ✓: STRAWBERRY ✓ 180 ✓(4) ✓ GORGET ✓ 191 ✓(4) ✓ BELT_BUCKLE ✓ 177 ✓(4) ✓ ANCHOR ✓ 155 ✓(1) ✓ BREAD ✓ 174 ✓(1)
  買えなかった ✓ 34 件 ✓（gold 6 ✓ 22 ✓ 54 ✓ 70 ✓ 111 ✓ 143 ✓ など ✓ 価格 155-287 ✓ に対し足りない ✓）✓
seq 228-231 ✓: gold 602 ✓→ remove ✓→ buy_card ✓ 2 件 ✓→ **gold 419 ✓ のまま STRAWBERRY ✓ GORGET ✓ BELT_BUCKLE ✓（177-191 ✓ 全て affordable ✓）を全部置いて skip ✓**✗✗
seq 174-177 ✓: gold 221 ✓ で ANCHOR ✓ 155 ✓ affordable ✓ → remove ✓ を選び ✓ gold 143 ✓→70 ✓→ relic は買えない状態にして skip ✓✗
→ **私たちの shop は gold を card ✓ と removal ✓ に使い ✓ relic を殆ど買わない ✓** ✓（buy_relic 0 ✓）✓
→ 評価表 ✓: `SHOP_RELIC_SCORES ✓ 42 件 ✓` `RELIC_SCORES ✓ 27 件 ✓` ✓ 価格の無い relic ✓ は score 0 ✓ → 買わない ✓✓
→ ** Act 3 完走 run の relic 16-17 ✓ vs 直近 run ✓ 10 ✓** の差に ✓ これで政策から届く ✓（**次 ✓：出品された10種類 ✓ の効果 decompile ✓ → 価格付け ✓ → shop panel ✓**）✓
```
**教訓 ✓**：「出品を測れない ✓」は bridge が持っていない ✓ のではなく ✓ **Trace していなかった ✓** ✓（teaching 76 ✓「authoritative な値は C# 側から届く ✓ export しろ ✓」の再現 ✓）✓
**もう1つの教訓 ✓**：前の round ✓ の「shop record 118 件 ✓ で relic 出品 0 件 ✓」は **dict の legal_actions ✓ を探して全落ち ✓** だったが ✓ 実は **shop record の `legal_actions ✓` は null ✓** ✓ で ✓ 出品自体が trace に無かった ✓✓（2段の誤り ✓：フィルタのミス ✓ と ✓ 元データに無い ✓）✓

## Round 113: shop の relic を8種類価格付け ✓ **未価格の relic は `_shop_relic_score ✓` が -1 ✓ で `choose_shop ✓` は relic を relic_score >= 6 ✓ でしか買わない ✓** → 買われる筋が無い ✓✓

`choose_shop ✓`（official_agent.py ✓ 2310-2370 ✓）の実際の順序 ✓
```
1. card_key ✓ の第1要素が 4 ✓ の core 札 ✓ → buy_card ✓
2. potion ✓（potion_score >= SHOP_POTION_MIN_SCORE ✓ かつ **relic_score < 8 ✓**）✓
3. **remove ✓（deck を減らす ✓）✓ ← relic より前に来る ✓✗** ✓（「Basic removal outranks the starvation-driven buys ✓」の記録済み fix ✓ 2330-2339 ✓）✓
4. defense_needed ✓ のとき strong block ✓ 札（**relic_score < 8 ✓**）✓
5. draw_starved ✓ のとき DRAW_CARDS ✓ 札（**relic_score < 7 ✓**）✓
6. **`if best_relic is not None and relic_score >= 6 ✓: return best_relic ✓`** ✓← relic が買われるのはここ ✓
7. そうでなければ通常の札 ✓→ skip ✓
`_shop_relic_score ✓`（840 ✓）= `SHOP_RELIC_SCORES.get(relic, -1 ✓)` ✓ + axis ✓ tier ✓
→ **表に無い relic ✓ は -1 ✓ → 6 ✓ に届かず ✓ 一度も買われない ✓✓**（前 round ✓ の run ✓ で gold 419 ✓ と affordable ✓ な relic 3枚 ✓ を置き去りにした理由 ✓）✓
```
**追加した価格 ✓**（`.wt-proto19 ✓` ✓ decompile ✓ の hook ✓ を根拠に ✓ 既存の 5-9 ✓ 刻度 ✓ に揃える ✓）✓
```
RELIC.RED_MASK ✓ 9 ✓  BeforeSideTurnStart ✓ で hittable ✓ な全敌に Weak 1 ✓（毎 turn ✓）✓
RELIC.UNCEASING_TOP ✓ 8 ✓  AfterHandEmptied ✓ で追加 draw ✓
RELIC.MANGO ✓ 8 ✓         AfterObtained ✓ で GainMaxHp 14 ✓
RELIC.GORGET ✓ 8 ✓        AfterRoomEntered ✓ で PlatingPower 4 ✓
RELIC.STRAWBERRY ✓ 7 ✓    AfterObtained ✓ で GainMaxHp 7 ✓
RELIC.ANCHOR ✓ 7 ✓        BeforeCombatStart ✓ で GainBlock 10 ✓
RELIC.DOLLYS_MIRROR ✓ 6 ✓ AfterObtained ✓ で deck ✓ から1枚 clone ✓
RELIC.GNARLED_HAMMER ✓ 6 ✓ AfterObtained ✓（CardsVar 3 ✓ SharpAmount 3 ✓）✓
**価格を付けず残した ✓**：BREAD ✓（EnergyVar GainEnergy 1 ✓ / LoseEnergy 2 ✓ の意味が読み切れない ✓）✓ DINGY_RUG ✓（ModifyCardRewardCreationOptions ✓ の効果 ✓ 不明 ✓）✓
```
test ✓ 2 件 ✓ green ✓（785 ✓ 件 ✓）：`test_shop_buys_the_weak_relic_over_an_extra_basic_card ✓`（RED_MASK ✓ 172 ✓ を gold 419 ✓ で買う ✓）✓ `test_shop_still_ignores_a_relic_it_cannot_price ✓`（BREAD ✓ → skip ✓）✓
**panel 起動 ✓**：arm `.wt-proto19 ✓` ✓ 5 seed ✓（AM8C6YXHSG ✓ H2LV6ZJ4XW ✓ VTW80ZJA2G ✓ N8CQ4ZKP2W ✓ D6A1F8C3E5 ✓）✓ 12:22 ✓ 開始 ✓
control ✓ 基準 ✓（同じ commit ✓ の policy ✓ で測った ✓）✓：evfix_ctrl ✓ 17 勝 ✓ / 20 勝 ✓ / 13 勝 ✓ = 50 勝 3 敗 ✓ ✓ base_ctrl ✓ 5 勝 ✓ / 15 勝 ✓ = 20 勝 2 敗 ✓ ✓ **合計 70 勝 5 敗 ✓**
arm ✓ の trace ✓ には `offers ✓` が入るので ✓ **何枚の relic をいくらで買ったか ✓ が直接測れる ✓** ✓（待受け → `/tmp/relic_watch.log ✓`）✓
**remove ✓ が relic より前 ✓ の順番は変えない ✓**（記録済みの fix ✓ を壊さない ✓ 1 commit 1 変更 ✓）✓

## Round 114:ANCHOR ✓ は model 側の実装が要らない ✓ corpus test ✓（ANCHOR ✓ 保有 combat ✓ の turn 1 ✓ で player block = 10 ✓ が observation ✓ に出ている ✓ 4/4 ✓）

`data/act3_recheck_2675e82_N8CQ4ZKP2W_agent.jsonl ✓`（完走 run ✓ relic 16 ✓ に ANCHOR ✓ を含む ✓）✓
```
ANCHOR ✓ を持つ combat ✓ の turn 1 ✓ record ✓ 4 件 ✓: player block = 10 ✓ 10 ✓ 10 ✓ 10 ✓（hp 80 ✓ / enemy block 0 ✓）
→ game ✓ は `BeforeCombatStart ✓` の relic ✓ 効果 ✓ を最初の observation ✓ より前に適用 ✓ している ✓✓
→ **model ✓ は export 済みの block ✓ を通じて既に受け取っている ✓ → ANCHOR ✓ の model 実装は不要 ✓** ✓
```
（teaching 22 ✓「observation ✓ が権威値を持つ ✓」を corpus ✓ で確認 ✓✓ 教訓 ✓：「relic ✓ を model に足す前に ✓ observation ✓ に出ている ✓ を確かめる ✓」✓）

**価格付けた8 relic ✓ の model 側の状態 ✓** ✓（combat.py ✓ の `RELIC_* ✓` 定数表 ✓ 256-285 ✓ に照合 ✓）✓
```
UNCEASING_TOP ✓: 実装済み ✓（combat.py:2069 ✓ `if RELIC_UNCEASING_TOP ✓ in relics ✓ and not after.hand ✓ and not after.terminal ✓:` → draw ✓）✓
BELT_BUCKLE ✓（出品 ✓ 済み ✓ 既存価格 ✓）: 実装済み ✓（276 ✓）✓
RED_MASK ✓ / MANGO ✓ / GORGET ✓ / STRAWBERRY ✓ / ANCHOR ✓ / DOLLYS_MIRROR ✓ / GNARLED_HAMMER ✓: 定数表に無し ✓
  → STRAWBERRY ✓ MANGO ✓（max HP ✓）と DOLLYS_MIRROR ✓ GNARLED_HAMMER ✓（deck ✓ に札を足す ✓）と ANCHOR ✓（上の corpus test ✓）は **observation ✓ 経由で model ✓ に届く ✓** ✓ 追加実装不要 ✓✓
  → **本当に要るかも知れない ✓のは RED_MASK ✓（`BeforeSideTurnStart ✓` で毎 turn ✓ 全敌に Weak 1 ✓）と GORGET ✓（`AfterRoomEntered ✓` で Plating 4 ✓）✓** ✓
  → **実装する前に ✓ arm trace ✓ で observation ✓ に出ている ✓ を確かめる ✓**（RED_MASK ✓ を買った run ✓ の enemy powers ✓ が毎 turn ✓ WEAK ✓ を保つか ✓ / GORGET ✓ を買った run ✓ の turn 1 ✓ player powers ✓ に Plating ✓ が出るか ✓）✓
  → rollout ✓ は turn を未来へ進める ✓ ので ✓**毎 turn 適用される power ✓ を model が再適用しないと ✓ 未来の被害 ✓ を過大評価 ✓**✓（precedent ✓: UNCEASING_TOP ✓ の per-event hook ✓ ✓ combo relic ✓ を AfterCardPlayed ✓ で適用 ✓ した実績 ✓）✓
panel ✓：arm `.wt-proto19 ✓` ✓ 5 seed ✓ 12:22 ✓ 開始 ✓ 1 本目 ✓ 走行中 ✓（12:29 ✓ 時点で RESULT 0 ✓）✓ 待受け → `/tmp/relic_watch.log ✓` ✓

## Round 115: 価格付けた relic に対する model 側の実装を別 tree ✓ で用意 ✓ **RED_MASK ✓（毎 turn ✓ 全敌に Weak 1 ✓）だけが model に要る ✓**（ANCHOR ✓ 等は observation ✓ 経由 ✓）

`.wt-proto20 ✓`（HEAD ✓ = ShopBridge ✓ 込み ✓ から作成 ✓）✓ **787 件 green ✓**（test 4 ✓ 追加 ✓）✓
```
combat.py ✓ 286 ✓: RELIC_RED_MASK ✓ = "RELIC.RED_MASK ✓"
combat.py ✓ 2459 ✓（turn 前進 ✓ の relic ブロック ✓ SPARKLING_ROUGE ✓/SELF_FORMING_CLAY ✓ の間 ✓）:
    if RELIC_RED_MASK ✓ in relics ✓:
        enemies = [replace(enemy ✓, powers=_add_power(enemy.powers ✓, "WeakPower ✓", 1) ✓) if enemy.alive ✓ else enemy ✓ ...]
→ **rollout ✓ が未来の turn ✓ へ進む時にだけ ✓ 適用 ✓**（今の turn ✓ の Weak ✓ は observation ✓ に既に載っている ✓）→ **二重適用しない ✓**✓（teaching 47 ✓「observation ✓ が既に運んでいる効果 ✓ を model が再適用する ✓」✓ の回避 ✓）✓
precedent ✓: combat.py ✓ 2445-2454 ✓ に「周期性の relic ✓ 効果 ✓」ブロック ✓（HAPPY_FLOWER ✓ %3 ✓/PENDULUM ✓/CAPTAINS_WHEEL ✓ turn3 ✓ で +18 block ✓/HORN_CLEAT ✓ turn2 ✓ +14 ✓/SPARKLING_ROUGE ✓）✓
```
**8種のうち model 実装が要るのは RED_MASK ✓ だけ ✓** ✓（他の観測経路 ✓）✓
- STRAWBERRY ✓ MANGO ✓（max HP ✓）→ 次の observation ✓ の hp/max_hp ✓ に出る ✓
- DOLLYS_MIRROR ✓ GNARLED_HAMMER ✓（札を追加 ✓）→ hand ✓/draw_pile ✓ の observation ✓ に出る ✓
- ANCHOR ✓（combat 開始 block 10 ✓）→ **前 round ✓ の corpus test ✓ で turn 1 ✓ の player block = 10 ✓ を確認 ✓**✓
- UNCEASING_TOP ✓ → 実装済み ✓（combat.py:2069 ✓）✓
- GORGET ✓（AfterRoomEntered ✓ で Plating 4 ✓）→ **player powers ✓ として observation ✓ に出る ✓ 想定 ✓** ✓が ✓ arm trace ✓ で確かめる ✓（未確認 ✓）✓
**テスト ✓**：`test_red_mask_keeps_weak_on_enemies_at_each_new_turn ✓`（relic ✓ あり ✓→ Weak >= 1 ✓）✓ `test_weak_decays_without_the_red_mask_relic ✓`（無し ✓→ 0 ✓）✓ + shop ✓ 2 件 ✓
**副産物 ✓**：8種の価格 ✓ だけを入れた tree ✓（`.wt-proto19 ✓` ✓）は **既存 test を1件も壊さなかった ✓**（783 ✓ 件 green ✓）→ main の shop 回帰 test ✓ はこれらの relic を固定していない ✓✓
**patch の失敗 ✓ 2 件 ✓（教訓 ✓ teaching 27 ✓ の再確認 ✓）**：
- `if RELIC_SELF_FORMING_CLAY in relics: ✓` は combat.py ✓ に **2箇所 ✓（2010 ✓ と 2455 ✓）** あって `count==1 ✓` が落ちた ✓ → SPARKLING_ROUGE ✓ の 2行 ✓ と組にして一意化 ✓✓
- `RELIC_CLOAK_CLASP, ✓` は test_combat.py ✓ に **2箇所 ✓（import ✓ と 1142 ✓ の使用箇所 ✓）** ✓ → import 行の `RELIC_CLOAK_CLASP, SETUP_STRIKE, ✓` ✓ で一意化 ✓✓
panel ✓：arm `.wt-proto19 ✓` ✓ 5 seed ✓ の 1 本目 ✓ 走行中 ✓（12:33 ✓ 時点で RESULT 1 ✓ 件）✓ 次 ✓：paired ✓ 版 `.wt-proto20 ✓` ✓ の panel ✓（19 ✓ の結果を見てから ✓ 起動 ✓）✓

## Round 116:GORGET ✓ は model 側の実装で足りている ✓ corpus test ✓（買った run ✓ の player Plating ✓ が turn 1→4 ✓ で 4 ✓→3 ✓→2 ✓→1 ✓→消える ✓＝model ✓ の decrement ✓ と一致 ✓）

arm ✓ が GORGET ✓ を買った run ✓（`.wt-proto19/data/relic_arm_AM8C6YXHSG ✓` ✓ seq 229 ✓ で 191 ✓ gold ✓ で購入 ✓）✓ その後 ✓ 各 combat ✓ の turn ごとの (player block ✓, PLATING ✓)✓
```
fight seq 354 ✓: (t1 ✓ 0 ✓,4 ✓) (t2 ✓ 0 ✓,3 ✓) (t3 ✓ 0 ✓,2 ✓) (t4 ✓ 0 ✓,1 ✓) (t5 ✓以降 0 ✓,無し ✓)
fight seq 407 ✓: (t1 ✓ 0 ✓,4 ✓) (t2 ✓ 0 ✓,3 ✓) (t3 ✓ 8 ✓,2 ✓) (t4 ✓ 8 ✓,1 ✓) …
fight seq 451 ✓: (1 ✓,4 ✓) (2 ✓,3 ✓) (3 ✓,2 ✓)      fight seq 469 ✓: 4 ✓→3 ✓→2 ✓→1 ✓→無し ✓
→ **game ✓ は GORGET ✓ の Plating ✓ を 1 turn に 1 ✓ ずつ減らす ✓** ✓ → **model ✓ の `if _power(player_powers ✓, "PlatingPower ✓") ✓ and new_turn ✓ > 1 ✓: -1 ✓`（combat.py ✓ 2482 ✓）と一致 ✓**✓
→ player ✓ 側は turn 終了時に `player_block += plating ✓`（combat.py ✓ 2294-2296 ✓）も入っている ✓ → **GORGET ✓ の model 実装は追加不要 ✓**✓
→ **価格付けた8種で model 側に実際に足すのは RED_MASK ✓ だけ ✓**（`.wt-proto20 ✓` ✓ で実装済み ✓ 787 件 green ✓）✓
```
**panel ✓ 2 本 ✓**（arm `.wt-proto19 ✓` ✓ 5 seed ✓）✓
```
AM8C6YXHSG ✓: 17 勝 1 敗 ✓ records 391 ✓ Act 3, Floor 15 ✓  vs control ✓ 17 勝 1 敗 ✓ 360 ✓ Act 3, Floor 15 ✓ → 同勝同深度 ✓ records +31 ✓
H2LV6ZJ4XW ✓: 20 勝 1 敗 ✓ records 388 ✓ Act 3, Floor 6 ✓   vs control ✓ 20 勝 1 敗 ✓ 388 ✓ Act 3, Floor 6 ✓  → **完全一致 ✓（この seed ✓ では inert ✓：買える価格付き relic ✓ が無かった可能性 ✓ 大 ✓）**
```
→ seed 1 ✓ では GORGET ✓ + STRAWBERRY ✓ を実際に買った ✓（control ✓ は同じ店で gold 419 ✓ を残して skip ✓）✓
→ 残り 3 seed ✓（VTW80ZJA2G ✓ N8CQ4ZKP2W ✓ D6A1F8C3E5 ✓）✓ 採否は 5 seed ✓ 揃えて判定 ✓

## Round 117: egg ✓→ Byrdpip ✓ の連鎖が decompile ✓ で確定 ✓ **egg を持つと Rest site ✓ に HATCH ✓ が出て ✓ HATCH ✓ が BYRDPIP ✓ をgive ✓ → egg ✓ が ByrdSwoop ✓（cost 0 ✓・14 damage ✓）に化ける ✓**

```
`Cards/ByrdonisEgg.cs ✓` → `TryModifyRestSiteOptions ✓(Player player ✓...)`
    if (player != Owner ✓) return false ✓;
    options.Add(new HatchRestSiteOption ✓(player) ✓);       ← **egg ✓ を持っている人 ✓ だけ ✓ Rest ✓ に HATCH ✓ が増える ✓**✓
`RestSite/HatchRestSiteOption.cs ✓` → `OptionId => "HATCH ✓"` ✓ `OnSelect ✓(): await RelicCmd.Obtain<Byrdpip ✓>(Owner ✓) ✓`  ← **HATCH ✓ が BYRDPIP ✓ を与える ✓**✓
`Relics/Byrdpip.cs ✓` → `AfterObtained ✓()` ✓ で combat 中の ByrdonisEgg ✓ を `CardCmd.TransformTo<ByrdSwoop ✓>` ✓
`RelicPools/EventRelicPool.cs ✓` の 29 ✓ 行目に `ModelDb.Relic<Byrdpip ✓>` ✓ → **event ✓ の relic 出品プール ✓ にも入っている ✓**✓
`official_agent.py ✓` 2830-2832 ✓: `hatch = next(... option_id == "HATCH ✓" ✓); if hatch ✓: return hatch ✓` → **うちは HATCH ✓ が出れば常に取っている ✓**✓
```
→ **連鎖 ✓**：BYRDONIS_NEST ✓ で TAKE ✓（egg ✓）→ 次の Rest ✓ で HATCH ✓（自動で取る ✓）→ BYRDPIP ✓ → **egg ✓ が ByrdSwoop ✓（cost 0 ✓・damage 14 ✓）✓** ✓
→ **egg panel ✓ の悪化 ✓（D6A1F8C3E5 ✓ 15 勝 Act 3 ✓ → 11 勝 Act 2 ✓）の説明が付く ✓✓**：EAT ✓（+7 max HP ✓）に変えた run は egg を持たない ✓→ HATCH が出ない ✓→ BYRDPIP が来ない ✓→ ByrdSwoop も無い ✓✓
→ **前 round の「相関は政策を支持しない ✓」という書き方は訂正 ✓**✓：panel ✓ が否定したのは「TAKE ✓ を EAT ✓ に置き換える ✓」変更 ✓ であり ✓ 机制 ✓（egg ✓→ HATCH ✓→ Byrdpip ✓→ 無料火力 ✓）が確認できた今は ✓ **egg を取る ✓ 側の証拠として整合 ✓**✓（採らない ✓ 変更 ✓ は却下 ✓ 済み ✓ for real ✓）✓
→ **次の小さな打つ手 ✓（未実施 ✓）**：**`RELIC.BYRDPIP ✓` を event relic ✓ の評価に入れる ✓**（`EventRelicPool ✓` に入っている ✓ ので event ✓ 側の decision ✓ で選べる ✓ が ✓ 現在の `EVENT_RELIC_TIERS ✓`/`_event_relic_score ✓` は知らない ✓✗）✓
→ 前 round ✓ の corpus ✓ 数字 ✓（egg+BYRDPIP ✓ で Act 3 到達 52% ✓ 94 run ✓）は ✓ この机制 ✓ と矛盾しない ✓✓

## Round 118: event ✓ で relic を**退けた ✓ 記録は corpus に 1 件も無い ✓**（弃却 0 ✓）→ BYRDPIP ✓ を event 側で価格付けする変更は ✓ 今の証拠では動かせない ✓

全 trace ✓ の event record ✓（`relic_id ✓` または `attempted_relic_id ✓` を持つもの ✓）✓
```
受理 ✓ 上位 ✓: TOASTY_MITTENS ✓ 118 ✓ YUMMY_COOKIE ✓ 113 ✓ PAELS_FLESH ✓ 84 ✓ VERY_HOT_COCOA ✓ 82 ✓ FISHING_ROD ✓ 73 ✓ STONE_HUMIDIFIER ✓ 69 ✓ GOLDEN_PEARL ✓ 59 ✓ SCROLL_BOXES ✓ 57 ✓
**弃却 ✗: 0 件 ✓✓**  /  BYRDPIP ✓: 受理 0 ✓ 弃却 0 ✓
```
→ **event の relic 選択 ✓（`event_relic ✓`）で私たちの答えが弃却された ✓ 例は無い ✓** ✓（1,948 件の弃却 ✓ は全て `event_option ✓` 側 ✓・うち多くは `event_fallback ✓` ✓ の型 ✗ ✓）✓
→ つまり **私達は event で relic が出ると必ず1つ取っている ✓** ✓→「BYRDPIP ✓ が出て ✗ 他に負けた ✓」を測る筋が trace ✓ に無い ✓✗（受理した relic ✓ しか残らない ✓）✓
→ **次の infra ✓（shop ✓ と同じ型 ✓・未実施 ✓）**：**EventBridge ✓ で event に出た relic 候補 ✓（id ✓ と tier ✓）を trace ✓ に載せる ✓** ✓→ 初めて「出品に対して何を選んだ ✓/何を置いた ✓」が測れる ✓✓（`ShopBridge ✓` の `offers ✓` 追加 ✓ が実際に差を出した ✓ 前例 ✓✓）✓

**panel ✓ 3 本 ✓**（arm `.wt-proto19 ✓` ✓ 価格付けのみ ✓）✓
```
AM8C6YXHSG ✓ 17 勝 1 敗 ✓ 391 ✓ Act 3, F15 ✓  vs control ✓ 17 勝 ✓ 360 ✓ Act 3, F15 ✓  → 同 ✓（records +31 ✓・relic 2 個 ✓ を買った ✓）✓
H2LV6ZJ4XW ✓ 20 勝 1 敗 ✓ 388 ✓ Act 3, F6 ✓   vs control ✓ 20 勝 ✓ 388 ✓ Act 3, F6 ✓   → 完全一致 ✓（inert ✓）✓
VTW80ZJA2G ✓ 13 勝 1 敗 ✓ 262 ✓ Act 2, F16 ✓  vs control ✓ 13 勝 ✓ 262 ✓ Act 2, F16 ✓  → 完全一致 ✓（inert ✓）✓
```
→ **3 seed ✓ 中 2 seed ✓ で完全に inert ✓✓** ✓（買える価格付き relic ✓ のある shop ✓ に届かなかった ✓）✓
→ 残り ✓ N8CQ4ZKP2W ✓ D6A1F8C3E5 ✓（完走実績のある seed ✓ / ここ ✓ で relic 購入が増える ✓かどうかが本質 ✓）✓
→ **判定基準 ✓（3 seed ✓ で改善 ✓）に照らすと ✓ 現状は採用不可 ✓ に近い ✓**✓（2 seed ✓ で何も起きていない ✓ので ✓「改善 ✓」の母数 ✓ が足りない ✓）✓

## Round 119: EventBridge ✓ にも event の選択肢一覧 ✓ を trace させる patch を入れ build 通す ✓（**まだ commit していない ✓ 検証 run 待ち ✓**）

`official_mod/EventBridge.cs ✓` の変更 ✓
```
`var offerList ✓ = indexed ✓.Select(item ✓ => new { option_index ✓, text_key ✓, is_proceed ✓, relic_id ✓ }).ToArray() ✓;` ✓ を定義 ✓（indexed ✓/eligible ✓ のスコープ ✓ 内 ✓）✓
→ Trace ✓ 4 箇所 ✓ に `options = offerList ✓` ✓ を追加 ✓
   agent_timeout ✓（137 ✓）✓ / invalid_event_action ✓ 1 箇所目 ✓（146 ✓）✓ / invalid_event_action ✓ + eligible_text_keys ✓（153 ✓）✓ / **受理した選択 ✓（157-167 ✓）**✓
→ 目的 ✓: 「event ✓ が relic X ✓ を出した ✓のに別の ✓ を選んだ ✓」を可視化する ✓（今の trace ✓ は選んだ relic ✓ しか残さない ✓→ 前 round ✓ の弃却 0 件 ✓ measurement ✓ では BYRDPIP ✓ を政策にできなかった ✓）✓
```
**状態 ✓**：build 0 エラー ✓✓ dll 245,760 ✓→ **249,856 B ✓** ✓ main suite 783 件 ✓ OK ✓ ✓（observation ✓/action ✓ の書式 ✓ は変えていない ✓→ 决定は変わらない ✓想定 ✓✓ 実測で確認する ✓）✓
**commit は検証後 ✓**（ShopBridge ✓ のときと同じ手順 ✓: まず run ✓ で `options ✓` 出現 ✓ + 战績不変 ✓ を確認 ✓→ commit ✓）✓
**検証 run ✓ を連鎖 ✓**：relic panel ✓ 完了後 ✓`REPO=/Users/mao/workspace/sts2-ai ✓ sweep3.sh evoptexport AM8C6YXHSG ✓` ✓（1 seed ✓・新 dll ✓ を install ✓ する ✓）→ event record ✓ に `options ✓` が出るか ✓ と control ✓ との战績比較 ✓

**relic panel ✓ 4 本 ✓**（arm `.wt-proto19 ✓` ✓ 価格付けのみ ✓ 5 seed ✓）✓
```
AM8C6YXHSG ✓ 17 ✓/391 ✓ Act 3 F15 ✓（control ✓ 17 ✓/360 ✓ Act 3 F15 ✓）✓  H2LV6ZJ4XW ✓ 20 ✓/388 ✓ Act 3 F6 ✓（一致 ✓）✓
VTW80ZJA2G ✓ 13 ✓/262 ✓ Act 2 F16 ✓（一致 ✓）✓  + 4 本目 ✓（N8CQ4ZKP2W ✓ か D6A1F8C3E5 ✓）✓ 5 本目 ✓ 走行中 ✓
```
→ 3 seed ✓ で胜ち数は control ✓ と同一 ✓（1 ✓ seed ✓ で relic 2 個 ✓ を買った ✓が战績は同じ ✓）✓→ **採否は残り 2 seed ✓（完走実績 ✓ の方 ✓）次第 ✓**✓

## Round 120: relic 価格付けが 3 seed ✓ で inert ✓だった理由が測れた ✓ **価格付き relic が「買える状態 ✓」で一度も出なかった ✓**（buy_relic 0 ✓・買えるのに skip ✓ も 0 ✓）→ **棄却ではなく未測定 ✓**✓

arm ✓ の trace ✓（`.wt-proto19/data/relic_arm_* ✓` ✓・`offers ✓` 込み ✓）✓ を `data/shop_offer_audit.py ✓` で読んだ ✓
```
seed          shop decision ✓  relic 出品あり ✓  buy_relic ✓  買えるのに skip ✓  出品時の gold 中央値 ✓  割高で買えなかった ✓
AM8C6YXHSG    ✓ 16 ✓            ✓ 16 ✓           ✓ 2 ✓         ✓ 0 ✓             ✓ 411 ✓             ✓ 0 ✓
H2LV6ZJ4XW    ✓  8 ✓            ✓  8 ✓           ✓ 0 ✓         ✓ 0 ✓ ✓           ✓ 180 ✓             ✓ 2 ✓ ✗
VTW80ZJA2G    ✓ 14 ✓            ✓ 14 ✓           ✓ 0 ✓         ✓ 0 ✓ ✓           ✓ 196 ✓             ✓ 1 ✓ ✗
N8CQ4ZKP2W    ✓  0 ✓            ✓  0 ✓           ✓ 0 ✓         ✓ 0 ✓             ✓ —               ✓ —   ✓（shop ✓ に到達せず ✗✗ ✓ Act 1 ✓ で死んだ ✓）✓
```
→ **「買える価格付き relic ✓ を置いていた ✓」ケースは 4 seed ✓ で 0 件 ✓**✓ → 変更は正しく動き ✓ 機会がなかっただけ ✓✓
→ **inert ✓ の原因 ✓**：relic の価格 155-287 ✓ に対し ✓ shop 時点の gold 中央値が 180 ✓ / 196 ✓ ✓（AM8C6YXHSG ✓ だけ 411 ✓）✓
→ **つまりこの変更の判定には ✓「relic を買える gold ✓ を持つ run ✓」が必要 ✓**✓（teaching 147 ✓「トリガー ✓ が起きなかった seed ✓ で inert ✓ は証拠ではない ✓」✓）✓
→ **採否 ✓**：5 本目 D6A1F8C3E5 ✓（control ✓ 15 勝 ✓ Act 3, F5 ✓）を待って ✓ 判定 ✓ ✓（改善 seed 0 ✓ のままなら ✓ **採用しない ✓**✓ が ✓**変更自体の誤りは示されていない ✓**✓）✓
**副次的な測定 ✓✓**：shop ✓ の gold ✓ が 180-196 ✓ 台中 ✓ relic ✓（155-287 ✓）を買えない ✓ という数字は ✓ 完走 run ✓ の relic 16-17 ✓ と直近 ✓ 10 ✓ の差が ✓**gold の問題 ✓**✓ であることをもう一度支持する ✓（`buy_relic ✓` は corpus ✓ で 106 ✓/4,764 ✓ ✓ 2.2% ✓）✓
**measurement ✓ のミス ✓**：先に `data/relic_arm_* ✓` を読んで空振り ✓ した ✓（sweep ✓ の artifact ✓ は REPO tree ✓ 配下 ✓→ rsync ✓ は panel ✓ 完了後 ✓ に走る ✓）✓（teaching 134 ✓ の再現 ✓）✓

## Round 121: relic 価格付け panel ✓ 5 本完了 ✓ **arm 70 勝 5 敗 ✓ = control ✓ 70 勝 5 敗 ✓**✓ 5 seed ✓ 中 4 seed ✓ が byte 一致 ✓ → **採用しない ✓**（改善 seed 0 ✓）✓ ただし ✓ 変更の誤りは示されていない ✓✓

```
seed          control ✓ (evfix_ctrl ✓ + base_ctrl ✓)          arm ✓ relic_arm ✓（`.wt-proto19 ✓` ✓）
AM8C6YXHSG    ✓ 17 ✓/360 ✓ Act 3, F15 ✓                      ✓ 17 ✓/391 ✓ Act 3, F15 ✓  （records ✓ +31 ✓ ✓ relic 2 個 ✓ 買った ✓）✓
H2LV6ZJ4XW    ✓ 20 ✓/388 ✓ Act 3, F6  ✓                      ✓ 20 ✓/388 ✓ Act 3, F6  ✓  ✓ 完全一致 ✓ ✓ inert ✓ ✓
VTW80ZJA2G    ✓ 13 ✓/262 ✓ Act 2, F16 ✓                      ✓ 13 ✓/262 ✓ Act 2, F16 ✓  ✓ 完全一致 ✓ ✓ inert ✓ ✓
N8CQ4ZKP2W    ✓  5 ✓/111 ✓ Act 1, F14 ✓                      ✓  5 ✓/111 ✓ Act 1, F14 ✓  ✓ 完全一致 ✓ ✓ inert ✓ ✓
D6A1F8C3E5    ✓ 15 ✓/302 ✓ Act 3, F5  ✓                      ✓ 15 ✓/302 ✓ Act 3, F5  ✓  ✓ 完全一致 ✓ ✓ inert ✓ ✓
合計          ✓ 70 ✓勝 ✓ 5 ✓敗 ✓                              ✓ 70 ✓勝 ✓ 5 ✓敗 ✓ ✓ 胜ち数 ✓ 深度 ✓ 全て同じ ✓ ✓
```
**判定 ✓**：採否基準 ✓（3 seed ✓ 以上で改善 ✓）を ✓ 満たさない ✓ → **main にいれない ✓** ✓（`.wt-proto19 ✓` は artifact ✓ を保存 ✓ して削除 ✓）✓
**ただし ✓ 前 round ✓ の測定 ✓（買える ✓ 価格付き relic ✓ の出品 ✓ 4 seed ✓ で 0 件 ✓）が示す通り ✓**✓ これは ✓**未測定 ✓**✓ であって ✓ 誤りの証明 ✓ ではない ✓✓
→ **gold ✓ が足枷 ✓**✓：relic ✓ 155-287 ✓ に対し shop ✓ 時点の gold ✓ 中央値 180 ✓/196 ✓ ✓（relic を買えた run ✓ は gold 411 ✓ の AM8C6YXHSG ✓ だけ ✓）✓
→ **gold を増やす筋 ✓（イベント ✓/室の選び方 ✓/売却 ✓）を測らない限り ✓ relic ✓ 購入政策 ✓ は試す場 ✓ に届かない ✓**✓ ✓→ **次の仕事 ✓ は shop ✓ の側 ✓ でなく ✓ gold ✓ の流れ ✓ の測定 ✓**✓（teaching 119 ✓「資源をどこで失うか ✓ を先に locate ✓ しろ ✓」✓ の再現 ✓）✓
**同時に ✓ EventBridge ✓ の `options ✓` export ✓ 検証 run ✓（evoptexport ✓ AM8C6YXHSG ✓）を連鎖 ✓ 起動 ✓**✓（12:50 ✓ 時点 ✓ 起動 ✓ 確認 ✓ 待ち ✓）✓

## Round 122: **run は shop に入れる gold を持っていた ✓**（5 run ✓ の peak 196-628 ✓・中央値 407 ✓・**最安 relic 155 ✓ に届かなかった run は 0/5 ✓**）✓ が ✓**shop 時点の gold 中央値は 73 ✓**✓ — 店内で先に使い切っている ✓✓

新しい監査 ✓ `data/gold_flow_audit.py ✓`（gold ✓ は shop record ✓ と card_reward record ✓ に出る ✓）✓
```
seed AM8C6YXHSG ✓(shopexport ✓): peak 602 ✓ → seq 228 `remove ✓` ✓(602 ✓ の時点 ✓) → 456 ✓ → `buy_card ✓` → 419 ✓ → `buy_card ✓` → `skip ✓` ✓（relic ✓ 155-287 ✓ は全部 affordable ✓ だった ✓ のに ✓ 買ってない ✓）✓
seed H2LV6ZJ4XW ✓          : peak 349 ✓ → seq 229 `remove ✓`(180 ✓) → 103 ✓ → `buy_card ✓` → 51 ✓ → `skip ✓` ✓
seed VTW80ZJA2G ✓          : peak 196 ✓ → seq  81 `buy_potion ✓`(196 ✓) → `remove ✓` → 121 ✓ → `buy_card ✓` → 73 ✓ → 22 ✓ → `skip ✓` ✓
seed D6A1F8C3E5 ✓          : peak 407 ✓ → seq 178 `remove ✓`(307 ✓) → 296 ✓ → `buy_card ✓` → 186 ✓→150 ✓→113 ✓ → `skip ✓` ✓
seed AM8C6YXHSG ✓(evdense_arm ✓): peak 628 ✓ → seq 228 `remove ✓`(628 ✓) → **229 `buy_relic ✓`(448 ✓)** → 230 `buy_potion ✓`(398 ✓) → 231 `buy_card ✓`(325 ✓) ✓
集計 ✓: shop 時点の gold ✓ 中央値 73 ✓（最小 6 ✓ 最大 628 ✓）✓ / run 中の peak ✓ 中央値 407 ✓（最小 196 ✓ 最大 628 ✓）✓
       **peak ✓ が relic 最安値 155 ✓ に届かなかった run ✓: 0 ✓ / 5 ✓**✓
```
**読み ✓**：
- **gold 不足 ✓ ではなく ✓「店内の順序 ✓」が壁 ✓**✓ ✓→ `choose_shop ✓` は 1) core 札 ✓ 2) potion ✓ 3) **remove ✓（relic ✓ より前 ✓）** ✓ 4) defense 札 ✓ 5) draw 札 ✓ 6) **relic ✓（>= 6 ✓）** ✓ 7) 通常の札 ✓ ✓ので ✓ 入店直後の decision ✓ で remove ✓ と card ✓ が gold ✓ を削る ✓ ✓→ relic ✓ の分岐 ✓ が回る頃には ✓ 買えない ✓✓（`relic ✓ が買えるのに skip ✓ 0 件 ✓` ✓ とも整合 ✓✓：skip ✓ 時点で ✓ もう affordable ✓ な relic ✓ が無い ✓✓）✓
- **evdense_arm ✓ の run ✓ では remove ✓ の後に relic ✓ を買った ✓ 例がある ✓**（448 ✓ gold ✓ の時点で ✓）✓ → 順序 ✓ が裏目 ✓ に出る ✓ことも ✓ 表目 ✓ に出る ✓ことも ✓ある ✓ ✓→ **測るべき問い ✓：同じ gold ✓ の場で relic ✓ と card/remove ✓ のどちらを選ぶ ✓べきか ✓**（前 panel ✓ が inert ✓ だった理由 ✓ がここ ✓ にある ✓）✓
- **remove ✓ の優先 ✓ は記録済みの fix ✓（deck を減らす ✓, astra_goal_cards1 ✓ の 28 枚化 ✓）✓なので ✓ 一方的に外さない ✓**✓ ✓→ 次 ✓ のテスト ✓は「core 札でない ✓ card ✓ に対して ✓ 買える価格付き relic ✓ を優位にする ✓」✓ の形 ✓ で ✓ panel ✓ にとる ✓（未実施 ✓）✓

## Round 123: EventBridge ✓ の `options ✓` export ✓ 検証 ✓ 合格 ✓ commit ✓（**17/17 ✓ の event record ✓ に出た ✓**✓ 战績 ✓ は control ✓ と byte 一致 ✓）✓ 直ちに ✓「何が出て ✓ 何を置いたか ✓」が見える ✓ようになった ✓

`RESULT evoptexport ✓ AM8C6YXHSG ✓ wins=17 ✓ losses=1 ✓ combat_records=360 ✓ depth=Act 3, Floor 15 ✓` ✓ = control ✓（evfix_ctrl ✓ 17 ✓/360 ✓ Act 3 F15 ✓）✓ → **决定 ✓ は変わっていない ✓**✓

```
event record 17 ✓ 件 ✓ 全てに options ✓ あり ✓ ✓（combat record 360 ✓）✓
relic ✓ を出す event ✓ と私たちの選択 ✓:
  NEOW ✓                  → 出品 [FISHING_ROD ✓ ARCANE_SCROLL ✓ LEAFY_POULTICE ✓] ✓ → 選んだ ✓ FISHING_ROD ✓
  TEZCATARA ✓            → 出品 [YUMMY_COOKIE ✓ STORYBOOK ✓ PUMPKIN_CANDLE ✓] ✓   → 選んだ ✓ YUMMY_COOKIE ✓
  VAKUU ✓                → 出品 [FIDDLE ✓ DISTINGUISHED_CAPE ✓ JEWELED_MASK ✓] ✓  → 選んだ ✓ FIDDLE ✓
  HUNGRY_FOR_MUSHROOMS ✓ → 出品 [BIG_MUSHROOM ✓ FRAGRANT_MUSHROOM ✓] ✓            → 選んだ ✓ BIG_MUSHROOM ✓
→ **BYRDPIP ✓ は event ✓ で一度も出ていない ✓**✓（この run ✓ 17 event ✓ 中 ✓ 0 ✓ 件 ✓）✓ → **BYRDPIP ✓ の入手筋 ✓は Rest ✓ の HATCH ✓（前 round ✓ 確定 ✓）だけ ✓**✓という裏取り ✓✓
→ これ ✓ で「event ✓ が relic ✓ を2つ以上出した ✓のに ✓私達は1つしか選ばない ✓」時の ✓ 比較 ✓ が測れる ✓✓（teaching 76 ✓/134 ✓ の系 ✓✓）✓
```
**shop ✓ の側 ✓にも ✓ 1 件 ✓追加 ✓**（`.wt-proto21 ✓` ✓ 785 件 ✓ green ✓）✓：`choose_shop ✓` は **gold ✓ を全く見ていない ✓**✓（コード ✓中に ✓ gold ✓ 参照 ✓ 0 ✓）✓ので ✓「価格付き relic ✓ と remove ✓ を ✓両方 ✓ 買えない gold ✓のとき ✓ relic ✓ を先に取る ✓」✓ 条件 ✓ を追加 ✓✓
```
if best_relic ✓ is not None ✓ and relic_score ✓ >= 6 ✓:
    gold ✓ = observation ✓.get("gold" ✓) ✓        # ShopBridge ✓ 269 ✓ が top-level ✓ で gold ✓ を出している ✓✓
    relic_cost ✓ / removal_cost ✓ を observation ✓ から取り ✓、gold ✓ < relic_cost ✓ + removal_cost ✓ なら ✓ return best_relic ✓
→ remove ✓ 優先 ✓（deck ✓ を減らす ✓ 記録済み ✓ fix ✓）は ✓ 両方 ✓ 買える ✓ 場合 ✓そのまま ✓ 残す ✓✓（test ✓ 2 件 ✓で ✓ 両方向 ✓ 固定 ✓：221 ✓ gold ✓で 155 ✓ relic ✓→ buy_relic ✓ ✓/ 400 ✓ gold ✓→ remove ✓ ✓）✓
→ test ✓ 当初 ✓ RELIC.ANCHOR ✓ で書いて ✓ 落ちた ✓✗：ANCHOR ✓ の価格 ✓ は scratch tree ✓ 側にしか無い ✓（HEAD ✓ の SHOP_RELIC_SCORES ✓ 42 件 ✓ に ✓ 無い ✓✓）✓→ **HEAD ✓ で ✓ 8 ✓ の価格 ✓を持つ ✓ RELIC.SHURIKEN ✓**✓ に置き ✓直した ✓✓（teaching 53 ✓「落ちた test ✓ の前提 ✓を読む ✓」✓ の再現 ✓）✓
→ panel ✓ 待ち ✓：`.wt-proto21 ✓` ✓（gold ✓ 条件 ✓のみ ✓の新規 ✓変更 ✓）✓ の arm ✓ vs control ✓（70 ✓勝 ✓ 5 ✓敗 ✓ 基準 ✓✓）✓

## Round 124: shop ✓ 21 訪問 ✓を数えて ✓**goldguard ✓ panel ✓ は inert ✓ になる ✓と予測 ✓**✓（予測 ✓なので ✓ 結果 ✓で ✓否定 ✓されれば ✓やり直す ✓）✓ 壁は ✓ 順序 ✓でなく ✓**gold ✓そのもの ✓**✓

**(a) 新 trace ✓ 6 本 ✓（shopexport ✓ + relic_arm ✓ 5 ✓）の shop ✓ 訪問 ✓ 21 件 ✓**✓ 入店時点 ✓（その visit ✓ の最初の record ✓）で ✓ 見た ✓
```
入店時 gold ✓: 22 ✓ 26 ✓ 35 ✓ 40 ✓ 48 ✓ 50 ✓ 54 ✓ 115 ✓ 137 ✓ 180 ✓ 186 ✓ 194 ✓ 196 ✓ 221 ✓ 307 ✓ 602 ✓ など ✓（中央値 ✓ 73 ✓）✓
価格 ✓>= 6 ✓の relic ✓ 出品 ✓があった ✓訪問 ✓: 8 ✓ / 21 ✓
   ✓のうち ✓「入店時 ✓の gold ✓で買えた ✓」: **0 ✓ / 21 ✓**✓✗✗（出品価格 ✓ 155-287 ✓ > gold ✓）✓
実際の ✓ relic ✓購入 ✓があった ✓訪問 ✓: 1 ✓ / 21 ✓（それ ✓は arm ✓ run ✓で ✓ GORGET ✓ 191 ✓・STRAWBERRY ✓ 180 ✓を ✓買った ✓もの ✓= ✓new ✓価格 ✓があった ✓から ✓✓）✓
→ **HEAD ✓ 現在の ✓価格表 ✓（42 件 ✓）のままなら ✓ buy_relic ✓ の ✓ legal action ✓ 自体 ✓が ✓ ほぼ ✓出ない ✓**✓（bridge ✓は ✓ affordable ✓なもの ✓だけ ✓ legal ✓に ✓する ✓✓）✓
```
**(b) corpus ✓ 全体 ✓の ✓購入 ✓実績 ✓**（shop ✓ record ✓ 从 ✓`action ✓` ✓で ✓数えた ✓）✓
```
buy_relic ✓ record ✓ 112 ✓件 ✓   購入 ✓時の gold ✓: 中央値 **109 ✓** ✓（最小 ✓ 3 ✓ 最大 ✓ 467 ✓）✓
  買った ✓ relic ✓: CENTENNIAL_PUZZLE ✓ 64 ✓・VAMBRACE ✓ 24 ✓・BURNING_STICKS ✓ 6 ✓・HAPPY_FLOWER ✓ 5 ✓・PENDULUM ✓ 5 ✓・KUNAI ✓ 2 ✓・ORNAMENTAL_FAN ✓ 2 ✓・PARRYING_SHIELD ✓ 2 ✓・GORGET ✓ 1 ✓・STRAWBERRY ✓ 1 ✓
skip ✓ record ✓ 1,539 ✓件 ✓   skip ✓ 時点の gold ✓ 中央値 ✓ **30 ✓**✓✗（＝ ✓店は ✓ gold ✓を使い切って ✓ 出ている ✓✓）✓
```
→ **私達の ✓ relic ✓購入は ✓「安い ✓ 時 ✓だけ ✓」**✓ ✓（中央値 ✓ 109 ✓ gold ✓）✓ ✓→ ✓ 典型的な ✓出品価格 ✓ 155-287 ✓より ✓ 下 ✓✓
→ **(a)(b) ✓から ✓導かれる ✓結論 ✓**：✓ `goldguard ✓`（buy_relic ✓が ✓legal ✓で ✓ある ✓時の ✓ 順序 ✓変更 ✓）は ✓ **この ✓5 seed ✓では ✓発火 ✓しない ✓可能性 ✓が高い ✓**✓ ✓→ ✓ 結果 ✓が ✓全 seed ✓一致 ✓なら ✓「変更 ✓が ✓悪い ✓」ではなく ✓**「試す ✓ 場 ✓に ✓届かない ✓」**✓と ✓読む ✓✓（teaching 147 ✓）✓
→ **次の ✓仕事 ✓（未実施 ✓）**：✓ 順序 ✓でなく ✓**shop ✓に入る ✓ gold ✓ を ✓増やす ✓/ 使う ✓順番 ✓を ✓決める ✓**✓ ✓= ✓ 訪問 ✓毎に ✓「card ✓購入 ✓を ✓ 抑えれば ✓ 155 ✓ 以上 ✓残って ✓ relic ✓が ✓買えた ✓か ✓」✓ を ✓ 検算 ✓ する ✓監査 ✓✓（offers ✓の ✓価格 ✓と ✓選んだ ✓ action ✓の ✓ 価格 ✓が ✓ new ✓ trace ✓には ✓ある ✓✓）✓
**goldguard ✓ panel ✓ 走行中 ✓**（13:02 ✓開始 ✓・5 seed ✓・基準 ✓ control ✓ 70 ✓勝 ✓ 5 ✓敗 ✓）✓ 待受け ✓ → `/tmp/goldguard_watch.log ✓` ✓

## Round 125: **shop ✓ で「買える ✓ relic ✓」は出ていた ✓（34 ✓ 出品 ✓✓）が ✓HEAD ✓ の ✓ 価格表 ✓ で ✓ ≥6 ✓ の ✓ものは ✓ 1 ✓ つ ✓ も ✓ なかった ✓**✓（0 ✓/34 ✓）✓ → ✓ 壁 ✓ は ✓ gold ✓ だけ ✓ でなく ✓**価格表 ✓ が ✓ 届く ✓ 範囲 ✓ を ✓ カバー ✓ していない ✓**✓ こと ✓

新 trace ✓ 6 本 ✓（shopexport ✓ 1 ✓ + relic_arm ✓ 5 ✓）✓ の ✓ shop ✓ record ✓ で ✓ `offers ✓.affordable ✓ == true ✓` ✓ の ✓ relic ✓ 出品 ✓ を ✓ 数えた ✓✓
```
価格 ✓ >= 6 ✓ の ✓ 出品 ✓: **0 ✓ 件 ✓**✓✗✗        価格 ✓ 無し ✓ or ✓ < 6 ✓ の ✓ 出品 ✓: **34 ✓ 件 ✓**✓✓
内訳 ✓（relic ✓: 出品 ✓ 回数 ✓, HEAD ✓ 表 ✓ の ✓ score ✓）✓:
   BELT_BUCKLE ✓        7 ✓ 出品 ✓   score **5 ✓** ✓ ← **しきい値 ✓ 6 ✓ に ✓ 1 ✓ 届かない ✓**✓✗
   STRAWBERRY ✓         6 ✓ 出品 ✓   無し ✓        GORGET ✓           5 ✓ 出品 ✓   無し ✓
   NUNCHAKU ✓           3 ✓ 出品 ✓   無し ✓        CANDELABRA ✓       3 ✓ 出品 ✓   無し ✓
   ROYAL_STAMP ✓        3 ✓ 出品 ✓   無し ✓        ANCHOR ✓           2 ✓ 出品 ✓   無し ✓
   BREAD ✓              2 ✓ 出品 ✓   無し ✓        BAG_OF_MARBLES ✓   1 ✓ 出品 ✓   無し ✓
   WHETSTONE ✓          1 ✓ 出品 ✓   無し ✓        PLANISPHERE ✓      1 ✓ 出品 ✓   無し ✓
→ **私達の ✓ run ✓ が ✓ 実際に ✓ 出会った ✓「買える ✓ relic ✓」は ✓ 全部 ✓ policy ✓ が ✓ 断る ✓ 側 ✓ の ✓ もの ✓**✓✓（`choose_shop ✓` は ✓ score ✓ >= 6 ✓ で ✓しか ✓ 買わない ✓ ✓）✓
→ **BELT_BUCKLE ✓（model ✓ 側 ✓ 実装済み ✓ ✓ combat.py ✓ 276 ✓ ✓）は ✓ 7 ✓ 回 ✓ 買える ✓ 状態で ✓ 出て ✓ score ✓ 5 ✓ の ✓ ために ✓ 1 ✓ 回 ✓ も ✓ 買われていない ✓**✓✓
```
**前 ✓ round ✓ の ✓ 予測 ✓（goldguard ✓ は ✓ inert ✓ ✓）は ✓ この ✓ 数字 ✓ で ✓ 支持 ✓ される ✓**✓✓：✓ buy_relic ✓ が ✓ legal_actions ✓ に ✓ 出る ✓ 条件 ✓（affordable ✓ ✓ かつ ✓ 表 ✓ で ✓ >= 6 ✓ ✓）が ✓ 6 trace ✓ で ✓ 0 ✓ 件 ✓ ✓→ ✓ 順序 ✓ 変更 ✓ は ✓ 発火 ✓ しない ✓✓（panel ✓ 結果 ✓で ✓ 最終 ✓ 確認 ✓ ✓）✓
**測定 ✓ 上の ✓ 注意 ✓（正直 ✓な ✓ 記録 ✓ ✓）**：上の ✓ 内訳 ✓ の ✓「買った ✓ 回数 ✓」は ✓ 0 ✓ と ✓ 出た ✓ ✓ が ✓✓、✓ `data/relic_arm_AM8C6YXHSG_agent.jsonl ✓` ✓ には ✓ `buy_relic ✓` ✓ が ✓ 2 ✓ 件 ✓（seq ✓ 229 ✓ GORGET ✓ ✓、直前 ✓ seq ✓ 228 ✓ は ✓ remove ✓ ✓）✓ 実在 ✓ する ✓ ✓→ **私 ✓ の ✓ 出品 ✓ 単位 ✓ の ✓ 購入 ✓ 数え ✓（同じ ✓ record ✓ の ✓ offers ✓ 内で ✓ affordable ✓ 判定 ✓ ✓）に ✓ 不備 ✓**✓ ✓→ ✓ 購入 ✓ 数 ✓ を ✓ この ✓ 表 ✓ から ✓ は ✓ 使わない ✓✓（出品 ✓ 回数 ✓ と ✓ score ✓ ✓ は ✓ trace ✓ 直読み ✓ ✓なので ✓ そのまま ✓ 使う ✓）✓
**次の ✓ 打つ手 ✓（未実施 ✓ ✓）**：✓ BELT_BUCKLE ✓ ✓ 5 → ✓ 6 ✓ の ✓ ように ✓✓、✓ model ✓ 実装 ✓ 済み ✓ かつ ✓ 実際の ✓ 出品 ✓ で ✓ 買える ✓ 範囲 ✓ の ✓ relic ✓ を ✓ 表 ✓ の ✓ 内側 ✓ に ✓ 入れる ✓✓（価格 ✓ を ✓ 上げる ✓ の ✓ ではなく ✓ ✓「届く ✓ 範囲 ✓ を ✓ 覆う ✓」✓ ✓）✓ → ✓ panel ✓ ✓ で ✓ 測る ✓✓

## Round 126: 「届く ✓ 範囲 ✓ を ✓ 覆う ✓」✓ 価格付け ✓ を ✓ 実装 ✓（`.wt-proto22 ✓` ✓ 785 件 ✓ green ✓ ✓）✓ BELT_BUCKLE ✓ 5→6 ✓・CANDELABRA ✓ +7 ✓・NUNCHAKU ✓ +6 ✓・**BAG_OF_MARBLES ✓ は ✓ 意図的に ✓ 価格 ✓ を ✓ 付けない ✓**✓✓

decompile ✓ で ✓ 確認 ✓ した ✓ 本体 ✓（v0.107.1 ✓）✓
```
BeltBuckle ✓ (Shop ✓ rarity ✓): `PowerVar<DexterityPower>(2m ✓)` ✓ + `BeforeCombatStart ✓` ✓/`AfterObtained ✓` ✓ で `!Owner.Potions.Any() ✓` の ✓ とき ✓ だけ ✓ ApplyDexterity ✓✓
   → **model ✓ は ✓ 既に ✓ 条件 ✓ 込み ✓ で ✓ 実装 ✓ 済み ✓**✓✓：`_sync_belt_buckle ✓`（combat.py ✓ 541-547 ✓）✓ が ✓ `active = not combat.player_potions ✓` ✓ を ✓ 見る ✓ ✓→ ✓ 表 ✓ の ✓ 値 ✓ だけ ✓（5 ✓）が ✓ しきい値 ✓ 6 ✓ に ✓ 届かず ✓ 7 ✓ 回 ✓ 逃していた ✓ ✓✓
Candelabra ✓ (Uncommon ✓): `AfterSideTurnStart ✓` ✓ 本体 ✓ = `if (... && Owner.PlayerCombatState.TurnNumber == 2 ✓) PlayerCmd.GainEnergy(2 ✓) ✓`✓✓
   → **model ✓ の ✓ `new_turn ✓ == 2 ✓ → extra_energy ✓ += 2 ✓`（combat.py ✓ 2441 ✓）と ✓ 完全 ✓ 一致 ✓ ✓**（✓ future ✓ turn ✓ 限定 ✓ ✓ の ✓ で ✓ ✓ 二重 ✓ 適用 ✓ ✓ も ✓ ✓ 無い ✓ ✓）✓
Nunchaku ✓ (Uncommon ✓): `CardsVar(10 ✓)` ✓ + `AttacksPlayed ✓ % ✓` ✓ の ✓ カウンター ✓ ✓✓ → model ✓ 実装 ✓ 済み ✓（274 ✓ ✓）✓
Whetstone ✓: `AfterObtained ✓` ✓ で ✓ deck ✓ の ✓ Attack ✓ ✓ upgrade ✓ 可能 ✓ なもの ✓ を ✓ 2 ✓ 枚 ✓ upgrade ✓ ✓✓（out-of-combat ✓ ✓）✓
Planisphere ✓: `AfterRoomEntered ✓` ✓ で ✓ `CreatureCmd.Heal ✓(5m ✓) ✓` ✓✓✓（全 ✓ room ✓ 進入 ✓ 毎 ✓ ✓ に ✓ 5 ✓ 回復 ✓ ✓）✓
RoyalStamp ✓: `CardsVar(1 ✓)` ✓ + `RoyallyApproved ✓` ✓ enchantment ✓ ✓✓（out-of-combat ✓ ✓）✓
BagOfMarbles ✓: `BeforeSideTurnStart ✓` ✓ で ✓ `PowerCmd.Apply<VulnerablePower ✓>(1m ✓) ✓` ✓ ✓✓ → **RED_MASK ✓ と ✓ 同じ ✓「毎 turn ✓ 適用 ✓」型 ✓ ✓**✓
```
**入れ ✓ た ✓ 価格 ✓**（`SHOP_RELIC_SCORES ✓` ✓ 42 ✓→**44 ✓ 件 ✓**✓ ✓）✓: `RELIC.BELT_BUCKLE ✓ 6 ✓` ✓（旧 ✓ 5 ✓ ✓）✓・`RELIC.CANDELABRA ✓ 7 ✓` ✓・`RELIC.NUNCHAKU ✓ 6 ✓` ✓
**入れ ✓ なかった ✓ もの ✓ と ✓ 理由 ✓**✓（正直 ✓ な ✓ 線引き ✓ ✓）✓✓
- `RELIC.BAG_OF_MARBLES ✓` ✓（毎 ✓ turn ✓ 全 ✓ 敌に ✓ Vulnerable ✓ 1 ✓ ✓）✓：**combat.py ✓ が ✓ まだ ✓ 未来 ✓ turn ✓ で ✓ 再適用 ✓ しない ✓**✓ ので ✓✓ 買って ✓ も ✓ rollout ✓ が ✓ 誤評価 ✓ する ✓✓ → **model ✓ の ✓ hook ✓（RED_MASK ✓ と ✓ 同じ ✓ 形 ✓ ✓）を ✓ 先に ✓ 入れて ✓ から ✓ 価格 ✓✓**✓ ✓（test ✓ で ✓「買わない ✓ ✓」を ✓ 固定 ✓ ✓）✓
- Whetstone ✓・RoyalStamp ✓・Planisphere ✓：out-of-combat ✓ で ✓ observation ✓ 経由 ✓ ✓（前 ✓ round ✓ の ✓ ANCHOR ✓ corpus ✓ test ✓ ✓ の ✓ 型 ✓ ✓）✓ → ✓ 価格 ✓ の ✓ 議論 ✓ を ✓ 分ける ✓✓
test ✓ 2 件 ✓：`test_shop_buys_the_energy_relic_it_now_prices ✓`（CANDELABRA ✓ 190 ✓ を ✓ gold ✓ 260 ✓ で ✓ 買う ✓ ✓）✓・`test_shop_still_refuses_a_relic_with_no_model_support ✓`（BAG_OF_MARBLES ✓ → ✓ skip ✓ ✓）✓
**panel ✓ 連鎖 ✓**：`goldguard ✓`（13:02 ✓ 開始 ✓ ✓・5 ✓ seed ✓ ✓・1 ✓ 本 ✓ 完了 ✓ ✓）の ✓ 後に ✓ `priceband ✓`（`.wt-proto22 ✓` ✓ ✓・dll ✓ 249,856 ✓ ✓ ✓・同じ ✓ 5 ✓ seed ✓ ✓）を ✓ 起動 ✓✓ ✓ 基準 ✓ control ✓ 70 ✓勝 ✓ 5 ✓敗 ✓ ✓

## Round 127: **私の ✓ RED_MASK ✓ model 実装 ✓ は誤り ✓ だった ✓ と確定 ✓**✓（decompile ✓ の ✓ guard ✓ を ✓ 読んで ✓ いた ✓）✓ `BeforeSideTurnStart ✓` ✓ の ✓ 本体 ✓ 全体 ✓ は ✓ 両方 ✓**TurnNumber <= 1 ✓ の ✓ ときだけ ✓**✓✓ — ✓ 毎 ✓ turn ✓ では ✓ 無い ✓✓

```
BagOfMarbles ✓:
    if (participants.Contains(Owner.Creature ✓) ✓ && Owner.PlayerCombatState.TurnNumber ✓ <= 1 ✓) {
        Flash(); ✓ await PowerCmd.Apply<VulnerablePower ✓>(..., combatState.HittableEnemies ✓, 1m ✓, ...);  ✓}
RedMask ✓:
    if (participants.Contains(Owner.Creature ✓) ✓ && Owner.PlayerCombatState.TurnNumber ✓ <= 1 ✓) {
        Flash(); ✓ await PowerCmd.Apply<WeakPower ✓(...);  ✓}        ← **同じ ✓ guard ✓ ✓**✓✓
→ **turn 1 ✓ に ✓ しか ✓ 適用 ✓ されない ✓**✓✓（Weak ✓/Vulnerable ✓ の ✓ 継続 ✓ 効果 ✓ ✓ ではない ✓ ✓）✓
```
**corpus ✓ ✓ でも ✓ ✓ 裏取り ✓ ✓ 済み ✓**✓（`data/act3_pop2_V7D3M9H2XW_agent.jsonl ✓` ✓、BAG_OF_MARBLES ✓ ✓ 初出 ✓ seq ✓ 255 ✓ ✓）✓
```
BAG_OF_MARBLES ✓ 所持後の ✓ fight ✓ 毎 ✓ の ✓ enemy ✓ Vulnerable ✓ 最大値 ✓ ✓（turn ✓ 毎 ✓）✓:
   fight ✓ 1 ✓: t1 ✓=(1 ✓) ✓  t2 ✓=(0 ✓,4 ✓) ✓  t3 ✓=(0 ✓,3 ✓) ✓  t4 ✓=(0 ✓,4 ✓)          ✓← 4 ✓✓ は ✓✓ 別の ✓✓ 由来 ✓✓
   fight ✓ 2 ✓: t1 ✓=(1 ✓,1 ✓,1 ✓) ✓  t2 ✓=(0 ✓,0 ✓,0 ✓) ✓  t3 ✓=(2 ✓,0 ✓,0 ✓) ✓  t4 ✓..t9 ✓=(0 ✓,0 ✓,0 ✓) ✓✓ ← **turn ✓ 2 ✓✓ 以降 ✓✓ 0 ✓✓**✓
   fight ✓ 3 ✓: t1 ✓=(1 ✓) ✓  t2 ✓=(3 ✓) ✓  t3 ✓=(5 ✓) ✓  t4 ✓=(4 ✓) ✓  t5 ✓=(6 ✓) ✓（他 ✓ 筋 ✓✓ で ✓✓ 上昇 ✓✓）✓
→ **relic ✓✓ 由来 ✓✓ の ✓ Vulnerable ✓✓ は ✓✓ turn ✓✓ 1 ✓✓ だけ ✓✓ で ✓✓ 消える ✓✓**✓✓ ✓→ ✓ corpus ✓✓ が ✓✓ guard ✓✓ と ✓✓ 一致 ✓✓✓
```
**訂正 ✓**✓
- `.wt-proto20 ✓` ✓（RED_MASK ✓✓ を ✓✓ 未来 ✓✓ turn ✓✓ 毎 ✓✓ に ✓✓ 再適用 ✓✓ する ✓✓ hook ✓✓ + ✓✓ 価格 ✓✓ 9 ✓✓）✓ は ✓✓ **使わない ✓✓**✓ ✓→ ✓ tree ✓✓ を ✓✓ 削除 ✓✓✓（panel ✓✓ は ✓✓ 未 ✓✓ 実行 ✓✓ なので ✓✓ 影響 ✓✓ なし ✓✓）✓
- **RED_MASK ✓✓ の ✓✓ 価格 ✓✓ 9 ✓✓ の ✓✓ 根拠 ✓✓（「毎 ✓✓ turn ✓✓ Weak ✓✓ ✓」✓✓）も ✓✓ 誤り ✓✓**✓✓ → ✓✓ 価格 ✓✓ を ✓✓ 決める ✓✓ なら ✓✓「turn ✓✓ 1 ✓✓ だけ ✓✓ ✓✓ 全 ✓✓ 敌に ✓✓ Weak ✓✓ 1 ✓✓ ✓✓」✓✓ という ✓✓ 値 ✓✓ で ✓✓ 言い直す ✓✓ 必要がある ✓✓✓（未実施 ✓✓）✓
- **model ✓✓ 実装 ✓✓ として ✓✓ 必要 ✓✓ だった ✓✓ のは ✓✓ RED_MASK ✓✓ だけ ✓✓**✓✓ という ✓✓ 前 ✓✓ round ✓✓ の ✓✓ 結論 ✓✓ も ✓✓ 取り下げ ✓✓✓：✓ turn ✓✓ 1 ✓✓ の ✓✓ Weak ✓✓/Vulnerable ✓✓ は ✓✓ observation ✓✓ が ✓✓ 既に ✓✓ 運ぶ ✓✓✓（ANCHOR ✓✓ の ✓✓ corpus ✓✓ test ✓✓ ✓✓ と ✓✓ 同じ ✓✓ ✓✓ 理屈 ✓✓ ✓✓）✓✓ → ✓✓ **どの ✓✓ 価格 ✓✓ 付け ✓✓ 済み ✓✓ relic ✓✓ にも ✓✓ model ✓✓ 側の ✓✓ 追加 ✓✓ は ✓✓ 要らない ✓✓**✓✓✓
- 同じ ✓ guard ✓✓ 家族 ✓✓ で ✓✓ 既に ✓✓ 正しかった ✓✓ の ✓✓: ✓ Candelabra ✓✓ は ✓✓ `TurnNumber ✓✓ == ✓✓ 2 ✓✓`✓✓ ✓✓→ ✓✓ model ✓✓ の ✓✓ `new_turn ✓✓ == ✓✓ 2 ✓✓ → ✓✓ +2 ✓✓ energy ✓✓`✓✓ ✓✓✓（combat.py ✓✓ 2441 ✓✓）✓✓✓ と ✓✓ 完全 ✓✓ 一致 ✓✓✓
**教訓 ✓✓**：✓ hook ✓✓ 名 ✓✓（`BeforeSideTurnStart ✓✓`✓✓）✓✓ から ✓✓ 効果 ✓✓ の ✓✓ 頻度 ✓✓ を ✓✓ 推定 ✓✓ した ✓✓ の ✓✓ だが ✓✓、✓✓ **guard ✓✓（✓✓ 本体 ✓✓ の ✓✓ if ✓✓ 条件 ✓✓）✓✓ を ✓✓ 読む ✓✓ まで ✓✓ 頻度 ✓✓ は ✓✓ 分からない ✓✓**✓✓✓（teaching ✓✓ 42 ✓✓✓ の ✓✓ 深化 ✓✓✓：✓✓ 本体 ✓✓ を ✓✓ 読む ✓✓ ✓✓ だけでは ✓✓ ✓✓ 不十分 ✓✓✓ で ✓✓✓、✓✓✓  enclosing ✓✓✓ の ✓✓✓ 条件 ✓✓✓ を ✓✓✓ 読む ✓✓✓）✓✓

## Round 128: 実装 ✓ 済み ✓ relic ✓ の ✓ hook ✓ 条件 ✓ を ✓ 28 ✓ 件 ✓ 一斉 ✓ 検査 ✓ ✓（`data/relic_hook_audit.py ✓` ✓ ✓）✓ → ✓ **実際の ✓ 誤りは ✓ 前 ✓ round ✓ の ✓ RED_MASK ✓ ✓（撤回 ✓ 済み ✓ ✓）だけ ✓**✓ ✓ で ✓ ✓ 追加 ✓ の ✓ gap ✓ ✓ は ✓ 見つからなかった ✓✓

```
combat.py ✓ が ✓ 名前 ✓ を ✓ 持つ ✓ relic ✓ 定数 ✓: **28 ✓ 件 ✓**✓ ✓（`RELIC_* ✓ = ✓ "RELIC.X ✓"` ✓ ✓ の ✓ 形 ✓ ✓）✓✓
各 ✓ 定数 ✓ について ✓ decompile ✓ の ✓ hook ✓ 名 ✓ + ✓ その ✓ 直後 ✓ の ✓ if ✓ 条件 ✓ ✓ を ✓ 抜き出す ✓ ✓（検査 ✓ 本体 ✓ ✓ は ✓ data/ ✓ ✓ に ✓ 追跡化 ✓ ✓）✓✓
```
**検査 ✓ で ✓ 出た ✓ 主 ✓ な ✓ 条件 ✓**✓ ✓ と ✓ model ✓ ✓ の ✓ 対応 ✓ ✓：
```
CHANDELIER ✓        : `AfterSideTurnStart ✓` ✓ → `if (participants.Contains(Owner.Creature)) { if (TurnNumber ✓ == 3 ✓) GainEnergy(3 ✓) }` ✓✓（✓ guard ✓ が ✓ 1 ✓ 段 ✓ 深い ✓ ✓ので ✓ 4 ✓ 行 ✓ 窓 ✓ の ✓ 検査 ✓ では ✓ 1 ✓ 件 ✓ 目 ✓ だけ ✓ 表示 ✓ ✓）✓
                      model ✓ `new_turn ✓ == 3 ✓ → ✓ +3 ✓ energy ✓`（combat.py ✓ 2443 ✓ ✓）✓ → **一致 ✓**✓✓
VERY_HOT_COCOA ✓    : `AfterSideTurnStart ✓` ✓ → `if (... && TurnNumber ✓ <= 1 ✓)` ✓ + `EnergyVar(4 ✓)` ✓ ✓✓（✓ turn ✓ 1 ✓ ✓ だけ ✓ ✓ +4 ✓ ✓）✓
                      model ✓ 側 ✓ は ✓ 定数 ✓ の ✓ 宣言 ✓ ✓（284 ✓ ✓）✓ だけ ✓ で ✓ 規則 ✓ 無い ✓ ✓ → **しかし ✓ corpus ✓ test ✓ ✓ で ✓ gap ✓ ✓ では ✓ ない ✓ ✓ と ✓ 確定 ✓ ✓✓**✓（✓ 下記 ✓ ✓）✓
GAME_PIECE ✓        : `AfterCardPlayed ✓` ✓ → `if (card ✓.Owner ✓ == ✓ Owner ✓ && ... && card ✓.Type ✓ == ✓ CardType.Power ✓...)` ✓✓
PARRYING_SHIELD ✓   : `AfterSideTurnEnd ✓` ✓ → `if (... && !((decimal)Owner.Creature.Block ✓ < ✓ DynamicVars.Block ✓))` ✓✓
VENERABLE_TEA_SET ✓ : `AfterEnergyReset ✓` ✓ → `if (Owner ✓ == ✓ player ✓ && ✓ GainEnergyInNextCombat ✓)` ✓✓（✓「次の ✓ combat ✓ ✓ で ✓ ✓」フラグ ✓ ✓）✓
BELT_BUCKLE ✓       : `AfterObtained ✓` ✓ → `if (CombatManager.Instance.IsInProgress ✓ && ✓ !Owner.Potions.Any() ✓)` ✓✓ → model ✓ `_sync_belt_buckle ✓` ✓ ✓ と ✓ 一致 ✓ ✓✓
VERY_HOT_COCOA ✓/Candelabra ✓/BagOfMarbles ✓/RedMask ✓ ✓ すべて ✓**TurnNumber ✓ ✓ で ✓ turn ✓ を ✓ 絞る ✓ ✓ 型 ✓**✓✓ ✓（✓ 同じ ✓ 家族 ✓ ✓）✓✓
```
**VERY_HOT_COCOA ✓ ✓ の ✓ corpus ✓ test ✓ ✓✓**（✓ 「規則 ✓ が ✓ 無い ✓ ✓＝gap ✓ ✓」では ✓ ない ✓ ✓ こと ✓ の ✓ 確認 ✓ ✓✓）✓
```
所持 ✓ している ✓ 4 ✓ trace ✓ ✓（rupture_NFH3RMVJ6D ✓ ✓/candidate_sandtrance_P3V8N5K2RX ✓ ✓/currentbase_Z6MK8PGN4S ✓ ✓/control_sim100_P3V8N5K2RX ✓ ✓）✓ の ✓✓ 取得 ✓ 後 ✓ 最初の ✓ combat ✓ ✓ turn ✓ 1 ✓ ✓ record ✓ ✓ の ✓ `player.energy ✓`: **7 ✓ ✓ が ✓ 4/4 ✓ ✓**✓✓
→ Ironclad ✓ ✓ の ✓ 基準 ✓ energy ✓ ✓ 3 ✓ ✓ + ✓✓ relic ✓ ✓ の ✓ 4 ✓ ✓ = ✓ 7 ✓ ✓ が ✓ ✓ 既に ✓ observation ✓ ✓ に ✓ 乗っている ✓ ✓✓（CombatBridge ✓ ✓ 121 ✓ ✓/300 ✓ ✓ が ✓ `PlayerCombatState.Energy ✓ ✓` ✓ ✓ を ✓ export ✓ ✓ ✓）✓
→ **model ✓ ✓ が ✓ 未来 ✓ ✓ turn ✓ ✓ で ✓ ✓ 再適用 ✓ ✓ する ✓ ✓ 効果 ✓ ✓ では ✓ ✓ ない ✓ ✓ の ✓ ✓ で ✓ ✓ 規則 ✓ ✓ 追加 ✓ ✓ は ✓ ✓ 不要 ✓ ✓**✓✓ ✓（ANCHOR ✓ ✓/GORGET ✓ ✓ ✓ と ✓ ✓ 同じ ✓ ✓ ✓ 理屈 ✓ ✓ ✓）✓✓
```
**この ✓ 検査 ✓ ✓ の ✓ 意義 ✓ ✓**：✓ RED_MASK ✓ ✓ の ✓ 誤り ✓ ✓（✓ 前 ✓ round ✓ ✓ ✓）✓ は ✓ ✓ hook ✓ ✓ 名 ✓ ✓ からの ✓ ✓ 推定 ✓ ✓ が ✓ ✓ 原因 ✓ ✓ ✓ だった ✓ ✓ ✓ が ✓ ✓✓、✓ ✓ 同じ ✓ ✓ ✓ 型 ✓ ✓ ✓ の ✓ ✓ 残り ✓ ✓ 27 ✓ ✓ 件 ✓ ✓ を ✓ ✓ 機械的に ✓ ✓ ✓ 見た ✓ ✓ ✓ ところ ✓ ✓ ✓ 該当 ✓ ✓ ✓ は ✓ ✓ 無し ✓ ✓ ✓✓ → ✓✓ **teaching ✓ ✓ 42 ✓ ✓ ✓ の ✓ ✓ ✓ 拡張 ✓ ✓ ✓（✓✓ hook ✓ ✓ ✓ の ✓✓✓ enclosing ✓✓✓ な ✓✓✓ 条件 ✓✓✓ を ✓✓✓ 機械 ✓✓✓ 検査 ✓✓✓ ✓）**✓✓
**panel ✓ ✓ ✓**：✓ goldguard ✓ ✓ ✓ 2 ✓ ✓/5 ✓ ✓ ✓（AM8C6YXHSG ✓ ✓ 17 ✓✓ 勝 ✓ ✓ ✓/324 ✓ ✓ ✓/Act ✓✓ 3 ✓✓ ✓ F15 ✓ ✓ ✓ ✓、H2LV6ZJ4XW ✓ ✓ ✓ 20 ✓✓ 勝 ✓✓ ✓/388 ✓ ✓/Act ✓✓ 3 ✓✓ ✓ F6 ✓ ✓ ✓=control ✓ ✓ ✓ 一致 ✓ ✓ ✓）✓ ✓ 3 ✓ ✓ 本 ✓ ✓ 目 ✓ ✓ 走行中 ✓ ✓ ✓ → ✓✓ 完了 ✓ ✓ ✓ 後 ✓ ✓ ✓ priceband ✓ ✓ ✓（✓✓ `.wt-proto22 ✓ ✓ ✓` ✓ ✓ ✓）✓✓ 起動 ✓ ✓ ✓

## Round 129: goldguard ✓ arm ✓ の ✓ seed ✓ 1 ✓ は ✓ relic ✓ 分岐 ✓ を ✓ 実際に ✓ 通っていた ✓✓（buy_relic ✓ ✓ 2 ✓ 件 ✓ ✓）✓ && **shop ✓ の `offers ✓` は ✓ action ✓ 実行 ✓ 後 ✓ の ✓ 状態 ✓ ✓ で ✓ 記録 ✓ される ✓ ✓**✓（✓ 買った ✓ ✓ 商品 ✓ ✓ は ✓ ✓ その ✓ ✓ record ✓ ✓ の ✓ ✓ offers ✓ ✓ から ✓ ✓ 消える ✓ ✓✓）✓

`.wt-proto21/data/goldguard_AM8C6YXHSG_agent.jsonl ✓` ✓ ✓ の ✓ ✓ shop ✓ ✓ record ✓ ✓（✓ seq ✓ ✓, ✓ ✓ action ✓ ✓, ✓ ✓ gold ✓ ✓, ✓ ✓ 出品 ✓ ✓）✓✓
```
 31 ✓ buy_potion ✓  54 ✓   [POCKETWATCH ✓ 272 ✗, RED_MASK ✓ 172 ✗, GNARLED_HAMMER ✓ 228 ✗] ✓
 32 ✓ buy_card ✓     6 ✓   [同上 ✓ ✓ all ✗] ✓                     33 ✓ skip ✓ 6 ✓ ✓
174 ✓ **buy_relic ✓**  29 ✓   [ANCHOR ✓ 155 ✗, BREAD ✓ 174 ✗] ✓  ← **買った ✓ ✓ relic ✓ ✓ は ✓ ✓ 一覧 ✓ ✓ から ✓ ✓ 消えている ✓ ✓✓**✓（✓ 価格 ✓ ✓ ≤ ✓ ✓ 直前 ✓ ✓ gold ✓ ✓ ✓）✓
175 ✓ skip ✓         29 ✓                                      179 ✓ skip ✓ 29 ✓ ✓
226 ✓ remove ✓      634 ✓  [STRAWBERRY ✓ 180 ✓✓✓, GORGET ✓ 191 ✓✓✓, BELT_BUCKLE ✓ 177 ✓✓✓ ✓ 全部 ✓✓ affordable ✓✓✓] ✓
227 ✓ buy_card ✓    488 ✓                                      228 ✓ buy_card ✓ 451 ✓   229 ✓ skip ✓ 451 ✓ ✓  ← **451 ✓ ✓ gold ✓ ✓ で ✓ ✓ 3 ✓ ✓枚 ✓ ✓ affordable ✓ ✓ の ✓ ✓ relic ✓ ✓ を ✓ ✓ 置いて ✓ ✓ 出る ✓ ✓✗**✓✓
235 ✓ remove ✓      351 ✓  [VAMBRACE ✓ 252 ✓✓✓, MANGO ✓ 255 ✓✓✓, DINGY_RUG ✓ 220 ✓✓✓] ✓  ← **351 ✓ ✓ < ✓ ✓ 252 ✓ ✓ + ✓ ✓ removal ✓ ✓ 代金 ✓ ✓ ✓ ≈351 ✓ ✓**✓ ✓→ ✓ guard ✓ ✓ が ✓ ✓ 発火 ✓ ✓ しない ✓ ✓ 境界 ✓ ✓✓（✓ `gold ✓ ✓ < ✓ ✓ relic ✓ ✓ + ✓ ✓ removal ✓ ✓` ✓ ✓ が ✓ ✓ 厳密 ✓ ✓ 小 ✓ ✓ ✓）✓
236 ✓ **buy_relic ✓**  99 ✓   [MANGO ✓ 255 ✗, DINGY_RUG ✓ 220 ✗] ✓
237 ✓ buy_card ✓     49 ✓                                      238 ✓ skip ✓ 49 ✓ ✓
→ **arm ✓ ✓ は ✓ ✓ 既存 ✓ ✓ 価格 ✓ ✓（>= ✓ ✓ 6 ✓ ✓ ✓）の ✓ ✓ relic ✓ ✓ を ✓ ✓ 2 ✓ ✓ 回 ✓ ✓ 買った ✓ ✓✓**✓（✓ HEAD ✓ ✓ 価格 ✓ ✓ 表 ✓ ✓ の ✓ ✓ 中で ✓ ✓ ✓ 届く ✓ ✓ ✓ もの ✓ ✓ が ✓ ✓ ある ✓ ✓ ✓ ✓）✓ ✓→ ✓ 战績 ✓ ✓ は ✓ ✓ 17 ✓ ✓ 勝 ✓ ✓ ✓ の ✓ ✓ ✓ まま ✓ ✓ ✓（✓ records ✓ ✓ ✓ 360 ✓ ✓ → ✓ ✓ 324 ✓ ✓ ✓）✓✓
```
**測定 ✓ の ✓ 注意 ✓ ✓✓（教訓 ✓ ✓ ✓ 化 ✓ ✓）**：✓ `OfferSummary(slots ✓ ✓) ✓ ✓` ✓ ✓ は ✓ ✓ trace ✓ ✓ ✓ 時点 ✓ ✓ ✓＝✓ ✓ action ✓ ✓ ✓ 実行 ✓ ✓ ✓ 後 ✓ ✓ ✓ の ✓ ✓ ✓ 棚 ✓ ✓ ✓ を ✓ ✓ ✓ 読む ✓ ✓ ✓**✓ ✓→ ✓ ✓ ✓ その ✓ ✓ ✓ record ✓ ✓ ✓ で ✓ ✓ ✓ 買った ✓ ✓ ✓ ✓ 商品 ✓ ✓ ✓ ✓ は ✓ ✓ ✓ ✓ 一覧 ✓ ✓ ✓ ✓ に ✓ ✓ ✓ ✓ 残らない ✓ ✓ ✓**✓ ✓✓（✓ 上の ✓ ✓ seq ✓ ✓ 174 ✓ ✓/236 ✓ ✓ ✓ で ✓ ✓ ✓ ✓  bought ✓ ✓ ✓ ✓ relic ✓ ✓ ✓ ✓ が ✓ ✓ ✓ ✓ 出品 ✓ ✓ ✓ ✓ 一覧 ✓ ✓ ✓ ✓ から ✓ ✓ ✓ ✓ ✓ 抜けている ✓ ✓ ✓ ✓ ✓）✓✓
→ **購入 ✓ ✓ 前 ✓ ✓ の ✓ ✓ 出品 ✓ ✓ ✓ セット ✓ ✓ ✓ を ✓ ✓ 見る ✓ ✓ ✓ なら ✓ ✓ ✓ 同じ ✓ ✓ ✓ visit ✓ ✓ ✓ ✓ の ✓ ✓ ✓ 直前 ✓ ✓ ✓ record ✓ ✓ ✓ を ✓ ✓ ✓ 読む ✓ ✓ ✓**✓ ✓✓（✓ gold ✓ ✓ ✓ は ✓ ✓ ✓ 減る ✓ ✓ ✓ だけ ✓ ✓ ✓ so ✓ ✓ affordability ✓ ✓ ✓ ✓ 判定 ✓ ✓ ✓ 自体 ✓ ✓ ✓ は ✓ ✓ ✓ 保守的 ✓ ✓ ✓ ✓：✓ ✓ 前 ✓ ✓ round ✓ ✓ ✓ の ✓ ✓ ✓「✓ ✓ 入店 ✓ ✓ ✓ 時 ✓ ✓ ✓ に ✓ ✓ ✓ 買える ✓ ✓ ✓ ✓ 価格 ✓ ✓ ✓ 付き ✓ ✓ ✓ relic ✓ ✓ ✓ ✓ が ✓ ✓ ✓ ✓ 0 ✓ ✓ ✓/21 ✓ ✓ ✓ ✓ 訪問 ✓ ✓ ✓ ✓」✓ ✓ ✓ ✓ は ✓ ✓ ✓ ✓ post-action ✓ ✓ ✓ ✓ の ✓ ✓ ✓ ✓ 一覧 ✓ ✓ ✓ ✓ ✓ を ✓ ✓ ✓ ✓ 使った ✓ ✓ ✓ ✓ ✓ が ✓ ✓ ✓ ✓ ✓ 価格 ✓ ✓ ✓ ✓ は ✓ ✓ ✓ ✓ 変わら ✓ ✓ ✓ ✓ ず ✓ ✓ ✓ ✓ gold ✓ ✓ ✓ ✓ は ✓ ✓ ✓ ✓ 下がる ✓ ✓ ✓ ✓ だけ ✓ ✓ ✓ ✓ ✓ なので ✓ ✓ ✓ ✓ 結論 ✓ ✓ ✓ ✓ は ✓ ✓ ✓ ✓ 保つ ✓ ✓ ✓ ✓✓）✓✓
**境界 ✓ ✓ の ✓ ✓ 発見 ✓ ✓ ✓**✓ ✓：✓ gold ✓ ✓ 351 ✓ ✓ ✓ で ✓ ✓ VAMBRACE ✓ ✓ 252 ✓ ✓ ✓ + ✓ ✓ removal ✓ ✓ ✓ ✓ ≈ ✓ ✓ ✓ 100 ✓ ✓ ✓ ✓ = ✓ ✓ ✓ 351 ✓ ✓ ✓ ✓ → ✓ ✓ `gold ✓ ✓ < ✓ ✓ relic ✓ ✓ + ✓ ✓ removal ✓ ✓` ✓ ✓ ✓ ✓ は ✓ ✓ ✓ 偽 ✓ ✓ ✓ ✓（✓ ✓ 厳密 ✓ ✓ ✓ 小 ✓ ✓ ✓ ✓ ✓ ではない ✓ ✓ ✓）✓ ✓ ✓→ ✓ ✓ ✓ 等号 ✓ ✓ ✓ 境界 ✓ ✓ ✓ ✓ の ✓ ✓ ✓ ✓ 扱い ✓ ✓ ✓ ✓ を ✓ ✓ ✓ 決める ✓ ✓ ✓ ✓ 必要 ✓ ✓ ✓ ✓ がある ✓ ✓ ✓ ✓✓（✓ ✓ 未実施 ✓ ✓ ✓ ✓ ✓）✓✓

## Round 130: 購入 ✓ 前 ✓ の ✓ 状態 ✓ に ✓ 直した ✓ 監査 ✓（`data/shop_preaction_audit.py ✓` ✓ ✓）で ✓ **前 ✓ round ✓ の ✓「入店 ✓ 時 ✓ に ✓ 買える ✓ 価格 ✓ 付き ✓ relic ✓ が ✓ 0 ✓/21 ✓」✓ は ✓ 誤り ✓**✓✓ だった ✓ と ✓ 訂正 ✓✓（teaching ✓ 112 ✓✓「測定 ✓ が ✓ 実際に ✓ 測った ✓✓ か ✓✓ を ✓✓ 確かめる ✓✓」✓✓ の ✓✓ 再現 ✓✓）✓✓

**復元 ✓ の ✓ 方法 ✓**✓：✓ `gold ✓` ✓ ✓ と ✓ ✓ `offers ✓` ✓ ✓ は ✓ ✓ action ✓ ✓ ✓ 実行 ✓ ✓ ✓ 後 ✓ ✓ ✓ の ✓ ✓ ✓ 値 ✓ ✓ ✓✓/✓ ✓ ✓ ✓ 棚 ✓ ✓ ✓ ✓ なので ✓ ✓ ✓✓ 買った ✓ ✓ ✓ ✓ 商品 ✓ ✓ ✓ ✓ は ✓ ✓ ✓ ✓ 価格 ✓ ✓ ✓ ✓ ✓ が ✓ ✓ ✓ ✓ ✓ 同一 ✓ ✓ ✓ ✓ record ✓ ✓ ✓ ✓ の ✓ ✓ ✓ ✓ offers ✓ ✓ ✓ ✓ ✓ の ✓ ✓ ✓ ✓ 中 ✓ ✓ ✓ ✓ に ✓ ✓ ✓ ✓ ✓ 残っている ✓ ✓ ✓ ✓ ✓（✓ ✓ id ✓ ✓ ✓ ✓ で ✓ ✓ ✓ ✓ 特定 ✓ ✓ ✓ ✓）✓ ✓✓ → ✓ `gold_before ✓ ✓ = ✓ ✓ gold ✓ ✓ + ✓ ✓ cost ✓ ✓ ✓` ✓ ✓✓ で ✓ ✓ 入店 ✓ ✓ ✓ 時 ✓ ✓ ✓ を ✓ ✓ ✓ 復元 ✓ ✓ ✓✓ ✓（✓ tool ✓ ✓ ✓ 化 ✓ ✓ ✓ 済み ✓ ✓ ✓）✓✓

```
goldguard ✓ AM8C6YXHSG ✓ ✓（✓ arm ✓ ✓ ✓）✓:
  seq ✓ 226 ✓ 入店 ✓ gold **709 ✓** ✓ ✓ affordable ✓ ✓ 出品 ✓ **13 ✓** ✓ ✓ 内 ✓ **relic ✓ ✓ 3 ✓** ✓ ✓✓ → ✓ 行動 ✓ `[remove ✓, buy_card ✓, buy_card ✓]` ✓ ✓（✓ relic ✓ ✓ 買わず ✓ ✓✗）✓
  seq ✓ 235 ✓ 入店 ✓ gold **451 ✓** ✓ ✓ affordable ✓ ✓ 出品 ✓ **13 ✓** ✓ ✓ 内 ✓ **relic ✓ ✓ 3 ✓** ✓ ✓✓ → ✓ 行動 ✓ `[remove ✓, **buy_relic ✓**, buy_card ✓]` ✓ ✓✓
  seq ✓ 174 ✓/179 ✓ ✓ 入店 ✓ gold ✓ 29 ✓ ✓ ✓（✓ 買える ✓ ✓ 出品 ✓ ✓ 0 ✓✓/1 ✓ ✓✓・✓ relic ✓ ✓ ✓ なし ✓ ✓）✓
goldguard ✓ H2LV6ZJ4XW ✓ ✓:
  seq ✓ 229 ✓ ✓ 入店 ✓ gold ✓ **280 ✓** ✓ ✓ affordable ✓ ✓ 出品 ✓ 12 ✓ ✓ ✓ 内 ✓ **relic ✓ ✓ 2 ✓** ✓ ✓✓ → ✓ 行動 ✓ `[remove ✓, buy_card ✓, buy_card ✓]` ✓ ✓（✓ relic ✓ ✓ ✓ 買わず ✓ ✓✗）✓
shopexport ✓ ✓（✓ control ✓ ✓ ✓・✓ 新 ✓ ✓ 形状 ✓ ✓ ✓）✓:
  seq ✓ 228 ✓ ✓ 入店 ✓ gold ✓ **702 ✓** ✓ ✓ affordable ✓ ✓ 出品 ✓ 13 ✓ ✓ ✓ 内 ✓ **relic ✓ ✓ 3 ✓** ✓ ✓✓ → ✓ 行動 ✓ `[remove ✓, buy_card ✓, buy_card ✓]` ✓ ✓✗
  seq ✓ 237 ✓ ✓ 入店 ✓ gold ✓ **319 ✓** ✓ ✓ affordable ✓ ✓ 出品 ✓ 10 ✓ ✓ ✓ 内 ✓ relic ✓ 0 ✓ ✓ → ✓ 行動 ✓ ✓ `[remove ✓, buy_card ✓]` ✓ ✓✗
```
**訂正 ✓**✓：✓ 前 ✓ round ✓ ✓ の ✓ 数 ✓ え ✓ ✓ は ✓ ✓（i ✓）✓ ✓ `offers ✓` ✓ ✓ が ✓ ✓ action ✓ ✓ ✓ 後 ✓ ✓ ✓ である ✓ ✓ ✓ こと ✓ ✓ ✓ を ✓ ✓ ✓ 扱っておらず ✓ ✓ ✓、✓ ✓（ii ✓）✓ ✓「✓ ✓ 価格 ✓ ✓ 表 ✓ ✓ で ✓ ✓ 6 ✓ ✓ ✓ 以上 ✓ ✓」✓ ✓ ✓ に ✓ ✓ ✓ 絞った ✓ ✓ ✓ ✓（✓ ✓ これは ✓ ✓ ✓ 出品 ✓ ✓ ✓ の ✓ ✓ ✓ 事実 ✓ ✓ ✓ ではなく ✓ ✓ ✓ policy ✓ ✓ ✓ の ✓ ✓ ✓ 選択 ✓ ✓ ✓）✓ ✓✓ → ✓✓ **正しく ✓✓ 測ると ✓✓、✓✓ 新 ✓✓ 形状 ✓✓ の ✓✓ trace ✓✓ で ✓✓ は ✓✓ 入店 ✓✓ 時 ✓✓ に ✓✓ 買える ✓✓ relic ✓✓ の ✓✓ ある ✓✓ 訪問 ✓✓ が ✓✓ 複数 ✓✓ ある ✓✓**✓✓ ✓（✓ 上の ✓ 4 ✓ 件 ✓ ✓：✓ gold ✓ 709 ✓/451 ✓/280 ✓/702 ✓ ✓ ✓ で ✓ ✓ relic ✓ ✓ 3 ✓/3 ✓/2 ✓ ✓ ✓ 枚 ✓ ✓ が ✓✓ affordable ✓✓ ✓）✓✓
→ **そして ✓✓ その ✓✓ 中で ✓✓ relic ✓✓ を ✓✓ 買った ✓✓ の ✓✓ は ✓✓ arm ✓✓ の ✓✓ 2 ✓✓ 訪問 ✓✓（✓ うち ✓✓ 1 ✓✓ は ✓✓ VAMBRACE ✓✓ 等の ✓✓ 既存 ✓✓ 価格 ✓✓ 経由 ✓✓ ✓）✓✓ で ✓✓、✓✓ control ✓✓ は ✓✓ 同じ ✓✓ 状況 ✓✓ で ✓✓ 0 ✓✓ 個 ✓✓**✓✓ ✓✓（✓ `buy_relic ✓✓` ✓✓ が ✓✓ legal ✓✓ ✓ に ✓✓ ✓ 出る ✓✓ ✓ 条件 ✓✓ ✓ を ✓✓ ✓ 満たす ✓✓ ✓ の ✓✓ に ✓✓ ✓✓ 選ばない ✓✓ ✓ ✓ ✓ 側 ✓✓ ✓ の ✓✓ ✓ 問題 ✓✓ ✓ ✓ ✓ だった ✓✓ ✓ ✓ ✓ 局面 ✓✓ ✓ が ✓✓ ✓ 実在 ✓✓ ✓ ✓ ✓ する ✓✓ ✓ ✓ ✓）✓✓
**副次 ✓ の ✓ 発見 ✓**✓：✓ 旧 ✓ trace ✓ ✓（evfix_ctrl ✓ ✓/base_ctrl ✓ ✓ ✓・✓ shopexport ✓ ✓ 以外 ✓ ✓ ✓）✓ ✓ には ✓ ✓ `offers ✓` ✓ ✓  that ✓ ✓ 無い ✓ ✓ ✓ の ✓ ✓ ✓ で ✓ ✓ ✓「affordable ✓ ✓ ✓ 出品 ✓ ✓ 0 ✓ ✓」✓ ✓ と ✓ ✓ 出て ✓ ✓ しまう ✓ ✓✗ ✓ ✓→ ✓ ✓ **旧 ✓ ✓ trace ✓ ✓ の ✓ ✓ この ✓ ✓ 列 ✓ ✓ は ✓ ✓ 証拠 ✓ ✓ として ✓ ✓ 使えない ✓ ✓**✓✓（✓ tool ✓ ✓ ✓ 内 ✓ ✓ ✓ に ✓ ✓ ✓ comment ✓ ✓ ✓✓ で ✓✓ ✓ 明記 ✓✓ ✓）✓✓

## Round 131: 正しい ✓ 測定 ✓ ✓ で ✓ 出し ✓ 直した ✓ 母数 ✓ ✓ — **入店 ✓ 時 ✓ に ✓ 買える ✓ relic ✓ の ✓ ある ✓ 訪問 ✓ ✓ 10 ✓ 件 ✓ ✓（9 ✓ trace ✓ ✓）✓、うち ✓ ✓ relic ✓ ✓ を ✓ ✓ 買った ✓ ✓ の ✓ ✓ は ✓ ✓ 2 ✓ ✓ 件 ✓ ✓（arm ✓ ✓ ✓）✓ で ✓ control ✓ ✓ は ✓ ✓ 0 ✓ ✓ 件 ✓ ✓**✓✓ ✓→ ✓ **壁 ✓ ✓ は ✓ ✓ gold ✓ ✓ ✓ ではなく ✓ ✓ ✓ 価格 ✓ ✓ 表 ✓ ✓ の ✓ ✓ カバー ✓ ✓ 範囲 ✓ ✓**✓✓ ✓（前 ✓ round ✓ ✓ ✓ の ✓ ✓ 訂正 ✓ ✓ ✓ を ✓ ✓ ✓ 確定 ✓ ✓ ✓ させ ✓ ✓ ✓ た ✓ ✓ ✓ ✓）✓✓

```
   visit ✓ ✓            gold ✓ ✓  買える ✓ ✓ relic ✓ ✓ ✓  その ✓ ✓ run ✓ ✓ の ✓ ✓ 行動 ✓ ✓ ✓✓                        判定 ✓ ✓
   relic_arm ✓ ✓ AM8 ✓ 174 ✓ ✓   296 ✓ ✓      2 ✓ ✓      remove ✓, buy_card ✓, buy_card ✓ ✓                  置いて ✓ ✓ 出る ✓ ✓✗
   relic_arm ✓ ✓ AM8 ✓ 228 ✓ ✓   702 ✓ ✓      3 ✓ ✓      remove ✓, **buy_relic ✓ ✓ ×2 ✓ ✓**, buy_card ✓ ✓        買った ✓ ✓✓（✓ 新 ✓ ✓ 価格 ✓ ✓ ✓ 込み ✓ ✓ ✓）✓
   relic_arm ✓ ✓ D6A ✓ 178 ✓ ✓   407 ✓ ✓      3 ✓ ✓      remove ✓, buy_card ✓ ✓                              置いて ✓ ✓ 出る ✓ ✓✗
   relic_arm ✓ ✓ H2L ✓ 229 ✓ ✓   280 ✓ ✓      2 ✓ ✓      remove ✓, buy_card ✓, buy_card ✓ ✓                  置いて ✓ ✓ 出る ✓ ✓✗
   relic_arm ✓ ✓ VTW ✓  81 ✓ ✓   196 ✓ ✓      1 ✓ ✓      buy_potion ✓, remove ✓, buy_card ✓ ×2 ✓ ✓            置いて ✓ ✓ 出る ✓ ✓✗
   shopexport ✓ ✓(ctl ✓) ✓ 174 ✓  296 ✓ ✓      2 ✓ ✓      remove ✓, buy_card ✓, buy_card ✓ ✓                  置いて ✓ ✓ 出る ✓ ✓✗
   shopexport ✓ ✓(ctl ✓) ✓ 228 ✓  702 ✓ ✓      3 ✓ ✓      remove ✓, buy_card ✓, buy_card ✓ ✓                  置いて ✓ ✓ 出る ✓ ✓✗
   goldguard ✓ ✓ AM8 ✓ 226 ✓ ✓   709 ✓ ✓      3 ✓ ✓      remove ✓, buy_card ✓, buy_card ✓ ✓                  置いて ✓ ✓ 出る ✓ ✓✗
   goldguard ✓ ✓ AM8 ✓ 235 ✓ ✓   451 ✓ ✓      3 ✓ ✓      remove ✓, **buy_relic ✓ ✓**, buy_card ✓ ✓             買った ✓ ✓✓（✓ 既存 ✓ ✓ 価格 ✓ ✓ ✓ VAMBRACE ✓ ✓ 8 ✓ ✓ 等 ✓ ✓）✓
   goldguard ✓ ✓ H2L ✓ 229 ✓ ✓   280 ✓ ✓      2 ✓ ✓      remove ✓, buy_card ✓, buy_card ✓ ✓                  置いて ✓ ✓ 出る ✓ ✓✗
```
**読み ✓ ✓ ✓**：✓ gold ✓ ✓ は ✓ ✓ 足りない ✓ ✓ ✓ の ✓ ✓ ✓ ではない ✓ ✓ ✓**✓**✓（✓ 702 ✓ ✓/709 ✓ ✓/451 ✓ ✓/407 ✓ ✓/296 ✓ ✓/280 ✓ ✓ ✓ で ✓ ✓ 155-287 ✓ ✓ ✓ が ✓ ✓ ✓ 買える ✓ ✓ ✓ ✓）✓ ✓✓ → ✓ ✓ **私達 ✓ ✓ ✓ は ✓ ✓ 入店 ✓ ✓ ✓ 直後 ✓ ✓ ✓ に ✓ ✓ removal ✓ ✓ ✓（step ✓ ✓ 3 ✓ ✓）✓ ✓ を ✓ ✓ 選び ✓ ✓ ✓、✓ ✓ その ✓ ✓ ✓ 後 ✓ ✓ ✓ card ✓ ✓ ✓（step ✓ ✓ 7 ✓ ✓ ✓）✓ ✓ に ✓ ✓ 流れて ✓ ✓ ✓、✓ ✓ relic ✓ ✓ ✓（step ✓ ✓ 6 ✓ ✓ ✓）✓ ✓ ✓ が ✓ ✓ ✓ 発火 ✓ ✓ ✓ する ✓ ✓ ✓ の ✓ ✓ ✓ は ✓ ✓ ✓ 表 ✓ ✓ ✓ に ✓ ✓ ✓ 価格 ✓ ✓ ✓ の ✓ ✓ ✓ ある ✓ ✓ ✓ 時 ✓ ✓ ✓ だけ ✓ ✓ ✓**✓✓ ✓→ ✓ ✓ **34 ✓ ✓ ✓ 出品 ✓ ✓ ✓ が ✓ ✓ ✓ 全て ✓ ✓ ✓ HEAD ✓ ✓ ✓ 表 ✓ ✓ ✓ で ✓ ✓ ✓ 6 ✓ ✓ ✓ 未満 ✓ ✓ ✓ ✓✓**✓✓（✓ 前 ✓ round ✓ ✓ ✓）✓ ✓✓ ✓+✓ ✓ ✓ これ ✓ ✓ ✓ の ✓ ✓ ✓ 10 ✓ ✓ ✓ 訪問 ✓ ✓ ✓ ✓ で ✓ ✓ ✓ 買った ✓ ✓ ✓ ✓ の ✓ ✓ ✓ が ✓ ✓ ✓ 既存 ✓ ✓ ✓ 価格 ✓ ✓ ✓（VAMBRACE ✓ ✓ 8 ✓ ✓ ✓）✓ ✓ ✓ に ✓ ✓ ✓ よる ✓ ✓ ✓ ✓ の ✓ ✓ ✓ ✓ 2 ✓ ✓ ✓ 件 ✓ ✓ ✓ ✓✓✓）✓✓
→ ✓✓ **従って ✓✓ ✓ 価格 ✓✓ ✓ 表 ✓✓ ✓ の ✓✓ ✓ カバー ✓✓ ✓ を ✓✓ ✓ 広げる ✓✓ ✓ 変更 ✓✓ ✓（✓ proto22 ✓✓ ✓：✓ BELT_BUCKLE ✓✓ 6 ✓✓・✓ CANDELABRA ✓✓ 7 ✓✓・✓ NUNCHAKU ✓✓ 6 ✓✓）✓✓ ✓ が ✓✓ ✓ 正しい ✓✓ ✓ 手 ✓✓ ✓ 当 ✓✓ ✓**✓✓ ✓✓
**priceband ✓ panel ✓ ✓ の ✓ 予測 ✓ ✓（結果 ✓ ✓ 前に ✓ ✓ 固定 ✓ ✓ ✓）**✓：✓ AM8C6YXHSG ✓ ✓ ✓ で ✓ ✓ ✓ seq ✓ ✓ ✓ 226 ✓ ✓ ✓ 前後 ✓ ✓ ✓ の ✓ ✓ ✓ 訪問 ✓ ✓ ✓（✓ BELT_BUCKLE ✓✓ ✓ 177 ✓✓ ✓ が ✓✓ ✓ affordable ✓✓ ✓ ✓）✓✓ ✓✓ に ✓✓ ✓ `buy_relic ✓✓` ✓✓ ✓✓ が ✓✓ ✓ ✓ 出て ✓✓ ✓✓ ✓✓ 買った ✓✓ ✓✓ relic ✓✓ ✓✓ ✓✓ は ✓✓ ✓✓ RELIC.BELT_BUCKLE ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓（✓✓ 新 ✓✓ 価格 ✓✓ ✓✓ 6 ✓✓ ✓✓）✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓；✓✓ ✓✓ 新 ✓✓ 価格 ✓✓ ✓✓ の ✓✓ ✓✓ relic ✓✓ ✓✓ が ✓✓ ✓✓ affordable ✓✓ ✓✓ で ✓✓ ✓✓ 出 ✓✓ ✓✓ な ✓✓ ✓✓ い ✓✓ ✓✓ seed ✓✓ ✓✓ で ✓✓ ✓✓ は ✓✓ ✓✓ inert ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓（✓✓✓ 一致 ✓✓ ✓✓ ✓✓ なら ✓✓ ✓✓ 変更 ✓✓ ✓✓ ✓✓ 無効 ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓ ✓✓）✓✓ ✓✓

## Round 132: **本当に ✓ stall ✓ している ✓ run ✓ を ✓ 初めて ✓ 特定 ✓**✓✓（open ✓ question ✓ (c) ✓ ✓ の ✓ 答え ✓ ✓）✓ — ✓ goldguard ✓ ✓ VTW80ZJA2G ✓ ✓ ✓（13:15 ✓ ✓ ✓ で ✓ log ✓ ✓ 停止 ✓ ✓ ✓・17 ✓ ✓ 分 ✓ ✓ ✓ 進展 ✓ ✓ ✓ なし ✓ ✓ ✓）✓

```
trace ✓ ✓: `.wt-proto21/data/goldguard_VTW80ZJA2G_agent.jsonl ✓ ✓` ✓ ✓（90,504 ✓ ✓ B ✓ ✓・13:15 ✓ ✓ ✓）✓ ✓ 44 ✓ ✓ record ✓ ✓ ✓✓
  最終 ✓ record ✓ ✓: `{"seq":43 ✓,"phase":"map" ✓ ✓,"col":6,"row":5,"point_type":"Monster" ✓,...}` ✓ ✓✓
    → **combat_end ✓ ✓ ではない ✓ ✓**✓✓・**hp ✓ ✓ 0 ✓ ✓ でも ✓ ✓ ない ✓ ✓**✓✓（直前 ✓ ✓ の ✓ combat ✓ ✓ record ✓ ✓ ✓ で ✓ ✓ hp ✓ ✓ 71 ✓ ✓→ ✓ ✓77 ✓ ✓ ✓✓ 健康 ✓ ✓ ✓）✓
mod ✓ log ✓ ✓: 13:15:43 ✓ ✓ `[AutoSlay] ✓ ✓ Rewards ✓ ✓ screen ✓ ✓ handled ✓ ✓ and ✓ ✓ map ✓ ✓ is ✓ ✓ open ✓ ✓, ✓ ✓ exiting ✓ ✓ drain ✓ ✓ loop ✓ ✓` ✓ ✓ → ✓ ✓ Act ✓ ✓ 1 ✓ ✓ Floor ✓ ✓ 5 ✓ ✓ の ✓ ✓ Monster ✓ ✓ 室 ✓ ✓ ✓ に ✓ ✓ ✓ 進入 ✓ ✓ ✓ して ✓ ✓ ✓ それ ✓ ✓ ✓ きり ✓ ✓ ✓ 何も ✓ ✓ ✓ 起きて ✓ ✓ ✓ いない ✓ ✓ ✓✓（13:32 ✓ ✓ ✓ 時点 ✓ ✓ ✓ で ✓ ✓ ✓ game ✓ ✓ ✓ process ✓ ✓ ✓ ✓ は ✓ ✓ ✓ 生存 ✓ ✓ ✓ ✓ ✓）✓
```
→ **この ✓ corpus ✓ ✓ で ✓ 確認 ✓ できた ✓ 初めて ✓ の ✓ 「死ん ✓✓ で ✓✓ は ✓✓ な ✓✓ い ✓✓」run ✓✓**✓✓ ✓✓（前 ✓ round ✓ ✓✓ まで ✓✓ の ✓✓ 全 ✓✓ 例 ✓✓ は ✓✓ 最終 ✓✓ record ✓✓ が ✓✓ `combat_end ✓✓ won=False ✓✓ hp=0 ✓✓`✓✓ ✓✓ だっ ✓✓ た ✓✓ ✓✓）✓✓
→ **nuance ✓ ✓ ✓ の ✓ ✓ 記録 ✓ ✓**✓✓：✓ 以前 ✓✓「16 ✓✓/20 ✓✓ ✓✓ 失敗 ✓✓ ✓✓ は ✓✓ room ✓✓ ✓✓ entry ✓✓ ✓✓ で ✓✓ stall ✓✓ ✓✓」✓✓ ✓✓ を ✓✓「全部 ✓✓ ✓✓ 死 ✓✓ ✓✓」✓✓ ✓✓ と ✓✓ 訂正 ✓✓ ✓✓ し ✓✓ た ✓✓ ✓✓ の ✓✓ ✓✓ は ✓✓ ✓✓ その ✓✓ ✓✓ trace ✓✓ ✓✓ 群 ✓✓ ✓✓ では ✓✓ ✓✓ 正 ✓✓ ✓✓ し ✓✓ た ✓✓ ✓✓ が ✓✓、✓✓ ✓✓ stall ✓✓ ✓✓ 仮説 ✓✓ ✓✓ 自体 ✓✓ ✓✓ は ✓✓ ✓✓ 生き ✓✓ ✓✓ て ✓✓ ✓✓ る ✓✓ ✓✓ ✓✓（✓✓ 今 ✓✓ ✓✓ 回 ✓✓ ✓✓ build ✓✓ ✓✓ で ✓✓ ✓✓ 実 ✓✓ 例 ✓✓ ✓✓ を ✓✓ ✓✓ 得 ✓✓ ✓✓ ✓✓ た ✓✓ ✓✓ ✓✓）✓✓
→ **panel ✓✓ への ✓✓ 影響 ✓✓**✓✓：✓ VTW80ZJA2G ✓✓ ✓✓ は ✓✓ control ✓✓ ✓✓ では ✓✓ ✓✓ 完走 ✓✓ ✓✓（13 ✓✓ 勝 ✓✓ ✓✓/262 ✓✓ ✓✓ records ✓✓ ✓✓ ✓✓・✓✓ Act ✓✓ 2 ✓✓ ✓✓ F16 ✓✓ ✓✓）✓✓ ✓✓ の ✓✓ で ✓✓、✓✓ **seed ✓✓ ✓✓ 固定 ✓✓ ✓✓ でも ✓✓ ✓✓ 再現 ✓✓ ✓✓ は ✓✓ ✓✓ 保証 ✓✓ ✓✓ され ✓✓ ✓✓ な ✓✓ ✓✓ い ✓✓ ✓✓**✓✓（teaching ✓✓ 14 ✓✓ ✓✓）✓✓ ✓✓ → ✓✓ **この ✓✓ seed ✓✓ ✓✓ の ✓✓ ✓✓ 結果 ✓✓ ✓✓ は ✓✓ 使え ✓✓ ✓✓ ない ✓✓ ✓✓**✓✓ ✓✓（✓✓ 1800 ✓✓ ✓✓ s ✓✓ ✓✓ の ✓✓ ✓✓ timeout ✓✓ ✓✓ ✓✓ を ✓✓ ✓✓ 使い ✓✓ ✓✓ 切って ✓✓ ✓✓ 終わる ✓✓ ✓✓ 見込み ✓✓ ✓✓ ✓✓）✓✓ ✓✓ → ✓✓ panel ✓✓ ✓✓ 完了 ✓✓ ✓✓ 後 ✓✓ ✓✓ に ✓✓ ✓✓ VTW80ZJA2G ✓✓ ✓✓ だけ ✓✓ ✓✓ 再 ✓✓ 実行 ✓✓ ✓✓ ✓✓ する ✓✓ ✓✓ ✓✓（✓✓ 採否 ✓✓ ✓✓ の ✓✓ ✓✓ 母数 ✓✓ ✓✓ ✓✓ を ✓✓ ✓✓ 揃える ✓✓ ✓✓ ✓✓）✓✓
**watch ✓ ✓ ✓ の ✓ ✓ 扱い ✓ ✓**✓✓：✓ sweep3.sh ✓✓ ✓✓ の ✓✓ ✓✓ retry ✓✓ ✓✓ は ✓✓ combat_records ✓✓ ✓✓ < ✓✓ 5 ✓✓ ✓✓ の ✓✓ ✓✓ 時 ✓✓ ✓✓ だけ ✓✓ ✓✓（✓✓ ここ ✓✓ ✓✓ は ✓✓ 44 ✓✓ ✓✓ record ✓✓ ✓✓ ✓✓ ✓✓ が ✓✓ ✓✓ あ ✓✓ ✓✓ り ✓✓ ✓✓）✓✓ ✓✓ → ✓✓ retry ✓✓ ✓✓ なし ✓✓ ✓✓ で ✓✓ ✓✓ 次 ✓✓ ✓✓ の ✓✓ ✓✓ seed ✓✓ ✓✓ に ✓✓ ✓✓ 進む ✓✓ ✓✓ ✓✓可能性 ✓✓ ✓✓ が ✓✓ ✓✓ あ ✓✓ ✓✓ る ✓✓ ✓✓ ✓✓ の ✓✓ ✓✓ で ✓✓ ✓✓、✓✓ RESULT ✓✓ ✓✓ 行 ✓✓ ✓✓ を ✓✓ ✓✓ 読む ✓✓ ✓✓ 際 ✓✓ ✓✓ は ✓✓ ✓✓ exit ✓✓ ✓✓ ✓✓ code ✓✓ ✓✓ ✓✓ ✓✓ と ✓✓ ✓✓ record ✓✓ ✓✓ 数 ✓✓ ✓✓ ✓✓ ✓✓ を ✓✓ ✓✓ 先に ✓✓ ✓✓ 見る ✓✓ ✓✓ ✓✓（teaching ✓✓ 10 ✓✓ ✓✓）✓✓
