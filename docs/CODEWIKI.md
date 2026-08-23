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
