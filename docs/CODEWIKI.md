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
rage_direct、kin_follower_direct、kin_follower_urgent_direct)、rollout系(rollout_success、
heuristic_fallback〈細分化するならheuristic_block/card/end_turn〉、agent_exception_fallback)。

**decision_reason固定値**(fallback時に併記): rollout_disabled_no_data/no_simulations/no_known_card、
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
main例外fallbackを計装済み。C#ブリッジ側のAgentAction/trace伝播は別コミットで実装する。

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
