# Act 3ボス戦の敗因分解 (T11, 2026-10-28)

- 作成: dsh agent (`sts2-ai/dsh`)。解析のみ。ゲーム未起動、main ツリーの源码・成果物は無変更。
- 入力: main `data/` の `*_agent.jsonl` 1289本と旧 `*_trace.jsonl`（`*_visible_trace.jsonl` を除く）582本、対応する mod log、`*_manifest.json` 617件、`enemies_*.json`。生成物はこのファイルと `act3_boss_fights.jsonl`（戦闘1行=1件の完全な台帳: ターン別の行動・火力・被ダメ・敵HP・telegraph）。main ツリーは読み取りのみ。
- 機構の根拠: `$TMPDIR/sts2-ai-decompiled`（v0.107.1 の macOS `sts2.dll` を ilspycmd でデコンパイルしたもの）。示す行番号はデコンパイル出力側の番号。

## 結論 (要約)

1. Act 3ボスに届いて負けた戦闘は **253本**（QUEEN_BOSS 245・TEST_SUBJECT_BOSS 7・AEONGLASS_BOSS 1）。届いて勝ったのは **21本**で、実体は 9 seed（N8CQ4ZKP2W のやり直しを含む）。manifest 側（結果が確定した公式run 617件のうち Act3ボスまで到達 112本）でもボス敗北 104本・踏破 8本。
2. QUEEN戦は **勝利に QUEEN自身の400HP削りだけが必要**。Torch Head Amalgam（199HP）は MinionPower による secondary で、QUEENが死ねば自動死亡、QUEEN生存中のみ存在できる（`CombatManager.cs:192`、`Creature.cs:245-268`、`TorchHeadAmalgam.cs:40-44`）。EVALUATION.md の「召喚物は別記」に該当するので、進捗は Queen 400に対する割合で測り、Amalgamは撃破/残HPを別に書く。
3. 火力が QUEEN に通っていない。agent形式のQUEEN敗北227本で、死んだ時点の Queen 残HP中央値 **328/400（削り18%）**、Queen を無傷で終えたのが 20本、300以上残したまま死んだのが130本。Amalgam を殺し切れた 139本のうち、その火力レートで QUEEN を殺し切るまで **5ターン以上**必要だったのが 100本、1-2ターンで済んだのは 14本だけ。Amalgam に殴りを吸わせているうちに自分が死ぬ構図（QUEEN へ通した火力の中央値 71、Amalgam に消えた分が中央値 154、敵ターンあたりの被ダメ 11.1、block で防いだ割合の中央値 31%）。
4. 死亡の引き金は Amalgam 側と QUEEN の burst で二分される。致死一手は Amalgam（BEAM/TACKLE系）86本、QUEEN側 OFF_WITH_YOUR_HEAD 112本 + EXECUTION 29本 = 141本。Amalgamを処置できずに死んだのが 86本、処置後にQUEENを殺しきれずに死んだのが141本。死のターン中央値 7（勝ったrunは 11）。QUEENは Amalgam死亡後のループ（OFF→EXECUTION→ENRAGE）で Strength を毎回+2ずつ積み、プレイヤーには Vulnerable 99（恒久）が乗るので、ターンが伸びるほど burst が単調に強くなる（`Queen.cs:195-234`、`YOU_ARE_MINE` の debuff 恒久付与 `Queen.cs:171-179`）。
5. ラボで忠実に再現できるQUEEN入場は、enchantment 復元と residual power 注入を実装した現在の lab 契約で **80 spec / 180 spec**（win 記録を含む usable 4 件）。一番大きな除外理由は「入室時の挙動が run 側の状態に依存するレリック」で 72 spec を塞いでいる（`RELIC.EMBER_TEA`・`GIRYA`・`TEA_OF_DISCOURTESY` など 14 種、`.dsh/relic_run_state.json`）。次が relic counter 34 件と preview で説明しきれないカード値 33 件。入場時power は spec 179 件のうち 172 件が deck のレリックの説明対象（`python3 .dsh/act3_entry_powers.py`。注入すると二重になる分を含む）で、注入が要るのは 5 spec 分だけ。TEST_SUBJECT と AEONGLASS は旧trace側にしか無く、デッキ情報が無いため spec を作れない（0件）。

## 1. 件数 (a)

### 1-1. trace全件（panel外の実験runを含む）

| encounter | boss 構成 | 敗北 | 勝利 | 計 |
| --- | --- | --- | --- | --- |
| ENCOUNTER.QUEEN_BOSS | QUEEN 400 + TORCH_HEAD_AMALGAM 199 | 245 | 18 | 263 |
| ENCOUNTER.TEST_SUBJECT_BOSS | TEST_SUBJECT 100/200/300（3形態） | 7 | 3 | 10 |
| ENCOUNTER.AEONGLASS_BOSS | AEONGLASS 512 | 1 | 0 | 1 |

判定は trace の `combat_end`（won / hp）で確定した。内訳: QUEEN敗北245本のうち新形式trace 227本、旧trace 18本。

母集団（新形式trace 1289本 + 旧trace 582本を log と突合）:

| 区分 | run数 |
| --- | --- |
| Act 3ボス室で戦闘した | 274 |
| Act 3に入ったがボス室前で止まった | 99 |
| Act 3未到達 | 1407 |
| log 無しで判定不能 | 87 |
| log と戦闘block が食い違って除外 | 5 |

panel外の実験runを含むので、この内訳を Act 3 踏破率として read しないこと（到達を意図して回した run が混ざっている）。

### 1-2. manifest側（結果が確定した公式runのみ、617件）

| panel / arm | run数 | Act3踏破 | ボスで敗北 | Act3ボス前死亡 | Act3未到達 | 判定不能 |
| --- | --- | --- | --- | --- | --- | --- |
| (panel無し) / - | 10 | 2 | 0 | 0 | 0 | 8 |
| astra_ctrl_v23 / control | 58 | 0 | 14 | 6 | 38 | 0 |
| astra_eval_v1 / candidate | 6 | 1 | 1 | 0 | 4 | 0 |
| astra_eval_v1 / control | 6 | 0 | 1 | 0 | 5 | 0 |
| astra_eval_v10 / candidate | 8 | 1 | 1 | 0 | 6 | 0 |
| astra_eval_v10 / control | 8 | 0 | 1 | 0 | 7 | 0 |
| astra_eval_v11 / candidate | 20 | 0 | 3 | 0 | 17 | 0 |
| astra_eval_v12 / candidate | 30 | 0 | 8 | 1 | 21 | 0 |
| astra_eval_v12 / control | 10 | 0 | 1 | 0 | 9 | 0 |
| astra_eval_v13 / candidate | 12 | 0 | 1 | 1 | 10 | 0 |
| astra_eval_v13 / control | 12 | 0 | 1 | 1 | 10 | 0 |
| astra_eval_v14 / candidate | 12 | 0 | 2 | 1 | 9 | 0 |
| astra_eval_v14 / control | 12 | 1 | 3 | 1 | 6 | 1 |
| astra_eval_v15 / candidate | 12 | 0 | 1 | 1 | 10 | 0 |
| astra_eval_v15 / control | 12 | 0 | 1 | 1 | 10 | 0 |
| astra_eval_v16 / candidate | 20 | 0 | 4 | 2 | 14 | 0 |
| astra_eval_v16 / control | 20 | 0 | 6 | 0 | 14 | 0 |
| astra_eval_v17 / candidate | 8 | 0 | 1 | 1 | 6 | 0 |
| astra_eval_v17 / control | 8 | 0 | 2 | 0 | 6 | 0 |
| astra_eval_v17 / rejected | 8 | 0 | 0 | 2 | 6 | 0 |
| astra_eval_v18 / candidate | 6 | 0 | 4 | 0 | 2 | 0 |
| astra_eval_v19 / candidate | 4 | 0 | 1 | 0 | 3 | 0 |
| astra_eval_v2 / candidate | 12 | 1 | 2 | 1 | 8 | 0 |
| astra_eval_v2 / control | 12 | 1 | 2 | 1 | 8 | 0 |
| astra_eval_v20 / control | 6 | 0 | 1 | 0 | 5 | 0 |
| astra_eval_v21 / candidate | 28 | 0 | 7 | 1 | 20 | 0 |
| astra_eval_v21 / control | 12 | 0 | 4 | 0 | 8 | 0 |
| astra_eval_v22 / candidate | 40 | 0 | 9 | 1 | 30 | 0 |
| astra_eval_v22 / control | 12 | 0 | 2 | 0 | 10 | 0 |
| astra_eval_v3 / candidate | 13 | 0 | 1 | 2 | 10 | 0 |
| astra_eval_v3 / control | 6 | 0 | 0 | 1 | 5 | 0 |
| astra_eval_v4 / candidate | 13 | 0 | 1 | 0 | 12 | 0 |
| astra_eval_v5 / candidate | 13 | 0 | 2 | 1 | 10 | 0 |
| astra_eval_v6 / candidate | 10 | 1 | 1 | 0 | 8 | 0 |
| astra_eval_v6 / control | 10 | 0 | 1 | 1 | 8 | 0 |
| astra_eval_v7 / candidate | 8 | 0 | 0 | 1 | 6 | 1 |
| astra_eval_v7 / control | 8 | 0 | 1 | 0 | 6 | 1 |
| astra_eval_v8 / candidate | 16 | 0 | 2 | 2 | 12 | 0 |
| astra_eval_v8 / control | 16 | 0 | 3 | 0 | 13 | 0 |
| astra_eval_v9 / candidate | 24 | 0 | 4 | 2 | 18 | 0 |
| astra_eval_v9 / control | 8 | 0 | 1 | 1 | 6 | 0 |
| astra_random20 / main | 20 | 0 | 3 | 1 | 16 | 0 |

manifest全体で Act 3ボスまで結果が確定した run は 112本、うち踏破 8本・ボス敗北 104本。`astra_ctrl_v23` の対照は ボス敗北 14本・Act3ボス前死亡 6本。

### 1-3. 勝った戦闘の seed 分解

| seed | 勝ち記録の数 | 記録されたpanel / run名 | ボス |
| --- | --- | --- | --- |
| N8CQ4ZKP2W | 12 | act3_recheck_2675e82; astra_eval_v1; astra_eval_v2; astra_goal_r8_retry1; astra_goal_r9; candidate_rupture2; candidate_v | QUEEN_BOSS |
| D6A1F8C3E5 | 2 | astra_base; astra_seed2 | TEST_SUBJECT_BOSS |
| 495FF454B7 | 1 | astra_ctrl_v23 | QUEEN_BOSS |
| 8D95FF5CE9 | 1 | astra_eval_v14 | QUEEN_BOSS |
| ? | 1 | astra_goal_intangible1 | TEST_SUBJECT_BOSS |
| DD1018C7FF | 1 | astra_eval_v10 | QUEEN_BOSS |
| E8282AC0A7 | 1 | astra_eval_v6 | QUEEN_BOSS |
| FD7A9C8F5F | 1 | smoke_v17 | QUEEN_BOSS |
| H2LV6ZJ4XW | 1 | candidate_last_hp_selfdamage | QUEEN_BOSS |

同じ seed の再実行が勝った回数として数えているので、21本を独立21勝として扱わないこと（EVALUATION.md の seed 単位の重み付けに従うと、勝ち側の独立試行は 9）。

## 2. 戦闘ごとの台帳 (b)

列の意味: 入HP/最大=QUEEN入室時点、deck=枚数(攻=攻撃札 / 防=blockを与える札 / 引=drawする札 / eng=Rupture系自傷エンジン札)、relic/pot=個数、T=プレイヤーのターン数、死T=最後の判断ターン（死はその直後の敵ターンで確定）、Am=Amalgam撃破ターン、Q残=死んだ時点のQUEEN残HP（最後の観測seq時点。EVALUATION.md の注記どおり、その後の反撃で順位が変わりうる）、削%=Q残/400、出Q=QUEENへ入れた火力/ターン、被=敵ターンで失ったHP/ターン、blk=得たblock/ターン、死招=致死攻撃の telegraph、要因=下の分類。

### 2-1. QUEEN戦 敗北（新形式trace、227本・QUEEN残の多い順）

| run | 入HP帯 | 入HP/最大 | deck | relic/pot | T | 死T | Am | Q残 | 削% | 出Q/turn | 被/turn | blk/turn | 死招 | 要因 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| act3_pop2 B4J8Q1R6YK | 60-79 | 78/90 | 21枚/攻2/防1/引2/eng1/強12 | 10/3 | 5 | 5 | 生存 | 400 | 0% | 0 | 15.0 | 5.6 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| act3_pop2 R8V2H6N4ZB | >=80 | 90/94 | 31枚/攻1/防2/引1/eng5/強11 | 13/3 | 9 | 9 | 生存 | 400 | 0% | 0 | 10.0 | 13.2 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| act3_pop2_head B4J8Q1R6YK | 60-79 | 78/90 | 21枚/攻2/防1/引2/eng1/強12 | 10/3 | 5 | 5 | 生存 | 400 | 0% | 0 | 15.0 | 5.6 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| act3_pop2_head R8V2H6N4ZB | >=80 | 90/94 | 31枚/攻1/防2/引1/eng5/強11 | 13/3 | 9 | 9 | 生存 | 400 | 0% | 0 | 10.0 | 14.1 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| act3_probe2_20260930 T5R8K2N9QP | >=80 | 80/88 | 34枚/攻0/防2/引0/eng2/強12 | 12/1 | 6 | 6 | 生存 | 400 | 0% | 0 | 13.3 | 9.3 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| act3_probe_20260930 B3N8V5T1WQ | <60 | 42/101 | 22枚/攻1/防4/引0/eng2/強5 | 11/0 | 5 | 5 | 生存 | 400 | 0% | 0 | 7.8 | 10.0 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| act3_rate_20260930 H4L6P2N8XS | 60-79 | 70/74 | 29枚/攻3/防2/引0/eng2/強15 | 12/3 | 5 | 5 | 生存 | 400 | 0% | 0 | 14.0 | 5.8 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| apotheosis_cand SOS6XYXCNO | <60 | 49/87 | 31枚/攻2/防2/引0/eng1/強16 | 14/3 | 4 | 4 | 生存 | 400 | 0% | 0 | 12.2 | 4.5 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| apotheosis_fire SOS6XYXCNO | <60 | 49/87 | 31枚/攻2/防2/引0/eng1/強16 | 14/3 | 4 | 4 | 生存 | 400 | 0% | 0 | 12.2 | 4.5 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_ctrl_v23 3169EC2E1C | <60 | 53/94 | 18枚/攻4/防2/引0/eng1/強12 | 11/1 | 3 | 3 | 生存 | 400 | 0% | 0 | 17.7 | 4.3 | TORCH_HEAD_AMALGAM:BEAM | Amalgamを殺し切る前に消耗で死亡 |
| astra_ctrl_v23/control 42A34FA0F2 | >=80 | 85/111 | 30枚/攻3/防1/引0/eng1/強4 | 12/2 | 6 | 6 | 生存 | 400 | 0% | 0 | 14.2 | 3.8 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_ctrl_v23/control 4952AC25C0 | >=80 | 85/100 | 28枚/攻1/防0/引0/eng3/強17 | 11/4 | 5 | 5 | 生存 | 400 | 0% | 0 | 17.4 | 1.2 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| astra_ctrl_v23 562858EF63 | <60 | 33/74 | 21枚/攻4/防1/引1/eng0/強8 | 11/0 | 3 | 3 | 生存 | 400 | 0% | 0 | 11.0 | 1.0 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v12/candidate 5F213792B3 | 60-79 | 71/80 | 23枚/攻2/防0/引1/eng2/強2 | 10/2 | 5 | 5 | 生存 | 400 | 0% | 0 | 14.2 | 6.2 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v12/control D4FD317050 | 60-79 | 66/74 | 26枚/攻3/防2/引1/eng3/強10 | 11/2 | 6 | 6 | 生存 | 400 | 0% | 0 | 11.0 | 20.8 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| candidate_sims50 N8CQ4ZKP2W | <60 | 41/79 | 32枚/攻1/防2/引2/eng2/強10 | 17/2 | 5 | 5 | 生存 | 400 | 0% | 0 | 8.2 | 12.6 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| madsci SOS6XYXCNO | 60-79 | 66/87 | 34枚/攻1/防3/引1/eng0/強13 | 14/3 | 6 | 6 | 生存 | 400 | 0% | 0 | 11.0 | 9.5 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| mechonly H2LV6ZJ4XW | >=80 | 112/128 | 28枚/攻2/防2/引0/eng2/強3 | 14/2 | 6 | 6 | 生存 | 400 | 0% | 0 | 18.2 | 3.3 | TORCH_HEAD_AMALGAM:BEAM | Amalgamを殺し切る前に消耗で死亡 |
| mechonly_arm_b3 B4J8Q1R6YK | 60-79 | 79/90 | 31枚/攻1/防3/引3/eng2/強14 | 13/3 | 5 | 5 | 生存 | 400 | 0% | 0 | 15.2 | 6.0 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| mechpanel_arm_clean H2LV6ZJ4XW | >=80 | 112/128 | 28枚/攻2/防2/引0/eng2/強3 | 14/2 | 6 | 6 | 生存 | 400 | 0% | 0 | 18.2 | 3.3 | TORCH_HEAD_AMALGAM:BEAM | Amalgamを殺し切る前に消耗で死亡 |
| priceband AM8C6YXHSG | 60-79 | 72/99 | 29枚/攻1/防2/引2/eng3/強13 | 14/3 | 6 | 6 | 生存 | 400 | 0% | 0 | 11.5 | 11.0 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| sweepF SOS6XYXCNO | <60 | 44/87 | 34枚/攻1/防3/引1/eng0/強13 | 14/3 | 4 | 4 | 生存 | 400 | 0% | 0 | 11.0 | 4.5 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| candidate_rupturequeen H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 6 | 6 | 生存 | 399 | 0% | 0 | 21.3 | 0.0 | TORCH_HEAD_AMALGAM:BEAM | Amalgamを殺し切る前に消耗で死亡 |
| astra_ctrl_v23/control 465F76FB32 | <60 | 53/73 | 29枚/攻3/防2/引0/eng1/強9 | 9/2 | 4 | 4 | 生存 | 397 | 1% | 0 | 13.2 | 5.5 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| candidate_shopcap N8CQ4ZKP2W | >=80 | 81/81 | 31枚/攻1/防4/引1/eng3/強7 | 17/3 | 7 | 7 | 生存 | 395 | 1% | 0 | 11.1 | 11.6 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v15/candidate FD05E30C5B | >=80 | 91/110 | 29枚/攻1/防1/引0/eng2/強11 | 12/2 | 6 | 6 | 生存 | 394 | 2% | 0 | 15.2 | 8.0 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v16/control 4EC1749AAB | <60 | 44/80 | 28枚/攻3/防2/引1/eng2/強7 | 11/1 | 4 | 4 | 生存 | 394 | 2% | 0 | 11.0 | 10.5 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v18/candidate 9E1E0E1D6A | >=80 | 100/100 | 29枚/攻0/防4/引3/eng3/強5 | 10/0 | 7 | 7 | 生存 | 394 | 2% | 0 | 14.3 | 11.6 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v21/candidate 9E1E0E1D6A | >=80 | 100/100 | 29枚/攻0/防4/引3/eng3/強5 | 10/0 | 7 | 7 | 生存 | 394 | 2% | 0 | 14.3 | 11.6 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_ctrl_v23 A37AF69710 | >=80 | 83/87 | 29枚/攻4/防3/引0/eng2/強9 | 12/4 | 6 | 6 | 生存 | 393 | 2% | 0 | 13.8 | 7.8 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| debuff_arm_b1 B3N8V5T1WQ | 60-79 | 76/102 | 30枚/攻3/防2/引0/eng3/強12 | 10/1 | 8 | 8 | 生存 | 393 | 2% | 0 | 9.5 | 11.9 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v13/control 4906EA4DC4 | <60 | 46/78 | 32枚/攻5/防3/引2/eng1/強10 | 12/3 | 3 | 3 | 生存 | 392 | 2% | 0 | 15.3 | 3.7 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v16/control 79DD8E03F6 | 60-79 | 60/100 | 26枚/攻2/防2/引0/eng5/強6 | 9/3 | 5 | 5 | 生存 | 392 | 2% | 0 | 11.4 | 9.8 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v21/candidate BB9869D3D3 | <60 | 52/90 | 30枚/攻3/防2/引0/eng2/強9 | 13/1 | 6 | 6 | 生存 | 392 | 2% | 0 | 13.0 | 4.0 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v21/control BB9869D3D3 | <60 | 52/90 | 30枚/攻3/防2/引0/eng2/強9 | 13/1 | 6 | 6 | 生存 | 392 | 2% | 0 | 13.0 | 4.0 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v5/candidate EB97217329 | <60 | 36/92 | 25枚/攻5/防2/引0/eng3/強10 | 12/2 | 4 | 4 | 生存 | 392 | 2% | 0 | 9.0 | 8.0 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| upgrade_arm_b1 D1W9Y3B7FC | >=80 | 80/80 | 30枚/攻2/防3/引0/eng1/強12 | 9/3 | 7 | 7 | 生存 | 392 | 2% | 0 | 11.0 | 14.9 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| act3_verify_head D6A1F8C3E5 | >=80 | 85/85 | 28枚/攻2/防2/引1/eng1/強16 | 15/2 | 6 | 6 | 生存 | 391 | 2% | 0 | 13.7 | 5.0 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v16/control DC4EF6882C | >=80 | 90/94 | 28枚/攻3/防5/引1/eng2/強10 | 11/3 | 6 | 6 | 生存 | 391 | 2% | 0 | 15.0 | 6.8 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| candidate_new Q6N3V8K2MT | <60 | 43/90 | 30枚/攻3/防3/引1/eng0/強6 | 14/0 | 4 | 4 | 生存 | 389 | 3% | 0 | 10.8 | 3.0 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| codex_smith_candidate_20260919 AM8C6YXHSG | 60-79 | 65/96 | 28枚/攻1/防1/引1/eng2/強13 | 13/0 | 4 | 4 | 生存 | 387 | 3% | 0 | 15.2 | 11.0 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_ctrl_v23 992E1B8DE0 | >=80 | 89/89 | 22枚/攻1/防1/引0/eng1/強13 | 12/3 | 6 | 6 | 生存 | 386 | 4% | 0 | 13.3 | 6.5 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v11/candidate BD0D5921A6 | 60-79 | 77/78 | 24枚/攻5/防0/引1/eng4/強9 | 13/2 | 5 | 5 | 生存 | 386 | 4% | 0 | 14.8 | 5.2 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| candidate_headbutt N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 7 | 7 | 生存 | 385 | 4% | 0 | 11.0 | 11.6 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| act3_verify N8CQ4ZKP2W | <60 | 59/83 | 33枚/攻4/防3/引0/eng3/強8 | 16/2 | 7 | 7 | 生存 | 384 | 4% | 0 | 7.4 | 8.7 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v15/control FD05E30C5B | 60-79 | 68/110 | 28枚/攻1/防1/引1/eng2/強11 | 11/1 | 5 | 5 | 生存 | 384 | 4% | 0 | 13.6 | 7.4 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v16/control DDA4086B1E | 60-79 | 67/70 | 24枚/攻0/防0/引0/eng1/強6 | 16/2 | 4 | 4 | 生存 | 384 | 4% | 0 | 16.8 | 7.2 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| fasten_GY GYIJSAA6W7 | 60-79 | 78/78 | 30枚/攻3/防2/引0/eng3/強5 | 10/1 | 6 | 6 | 5 | 384 | 4% | 16.0 | 12.5 | 9.3 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v7/control 1941B188DE | 60-79 | 76/76 | 29枚/攻1/防3/引1/eng4/強7 | 13/3 | 7 | 7 | ? | 381 | 5% | 1.9 | 10.4 | 10.1 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v17/candidate A8C7F917F3 | 60-79 | 71/76 | 29枚/攻3/防0/引0/eng4/強12 | 11/3 | 4 | 4 | 生存 | 380 | 5% | 0 | 17.2 | 0.0 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| candidate_bound D6A1F8C3E5 | >=80 | 85/85 | 29枚/攻1/防2/引1/eng1/強15 | 16/3 | 8 | 8 | 7 | 380 | 5% | 11.0 | 10.1 | 8.6 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_fysh60 D6A1F8C3E5 | >=80 | 85/85 | 29枚/攻1/防2/引1/eng1/強15 | 16/3 | 8 | 8 | 7 | 380 | 5% | 11.0 | 10.1 | 8.5 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_juggernaut D6A1F8C3E5 | >=80 | 85/85 | 29枚/攻1/防2/引1/eng1/強15 | 16/3 | 8 | 8 | 7 | 380 | 5% | 11.0 | 10.1 | 8.6 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| currentbase D6A1F8C3E5 | >=80 | 85/85 | 29枚/攻1/防2/引1/eng1/強15 | 16/3 | 8 | 8 | 7 | 380 | 5% | 11.0 | 10.1 | 8.6 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| mechonly R8V2H6N4ZB | >=80 | 90/94 | 32枚/攻1/防1/引1/eng4/強11 | 11/3 | 5 | 5 | 生存 | 379 | 5% | 0 | 17.6 | 6.4 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| mechpanel_arm_clean R8V2H6N4ZB | >=80 | 90/94 | 32枚/攻1/防1/引1/eng4/強11 | 11/3 | 5 | 5 | 生存 | 379 | 5% | 0 | 17.6 | 6.4 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| astra_ctrl_v23/control 67A743CCD8 | >=80 | 97/97 | 26枚/攻4/防2/引1/eng4/強9 | 12/3 | 6 | 6 | 生存 | 378 | 6% | 0 | 15.7 | 3.3 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v21/candidate 22FDB96B7C | <60 | 49/103 | 28枚/攻4/防1/引0/eng3/強12 | 14/3 | 3 | 3 | 生存 | 378 | 6% | 0 | 15.3 | 7.3 | TORCH_HEAD_AMALGAM:BEAM | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v9/candidate 5CE6E5E3F8 | <60 | 46/80 | 31枚/攻2/防3/引1/eng3/強9 | 8/2 | 5 | 5 | 生存 | 377 | 6% | 0 | 8.2 | 12.6 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v10/control 2409DE6134 | <60 | 56/90 | 22枚/攻2/防3/引3/eng1/強4 | 13/2 | 6 | 6 | 5 | 376 | 6% | 24.0 | 9.3 | 8.2 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_eval_v22/candidate 04DDDF708F | 60-79 | 71/80 | 24枚/攻6/防0/引1/eng1/強7 | 14/3 | 5 | 5 | 生存 | 375 | 6% | 0 | 14.2 | 0.0 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v22/candidate 5F00D693E5 | 60-79 | 68/76 | 29枚/攻3/防5/引1/eng4/強13 | 9/4 | 4 | 4 | 生存 | 375 | 6% | 0 | 15.5 | 7.0 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v13/candidate 2872AB854A | 60-79 | 77/101 | 27枚/攻2/防0/引1/eng3/強9 | 13/3 | 6 | 6 | 生存 | 374 | 6% | 0 | 12.8 | 2.3 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| candidate_bound N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 8 | 8 | 7 | 374 | 6% | 21.0 | 9.6 | 10.4 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| act3_rate_20260930 D1W9Y3B7FC | 60-79 | 79/80 | 31枚/攻3/防3/引1/eng1/強11 | 8/3 | 4 | 4 | 生存 | 373 | 7% | 0 | 18.5 | 3.0 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v14/control E9617C1035 | 60-79 | 66/95 | 23枚/攻3/防4/引0/eng0/強3 | 16/3 | 7 | 7 | 生存 | 373 | 7% | 0 | 9.4 | 9.7 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| candidate_ruptureplus_rage H2LV6ZJ4XW | >=80 | 143/143 | 30枚/攻4/防1/引0/eng3/強2 | 14/3 | 7 | 7 | 生存 | 373 | 7% | 0 | 18.4 | 7.7 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| drawvalue_M7 M7C4Q9V2RH | >=80 | 80/80 | 30枚/攻5/防1/引0/eng1/強5 | 11/4 | 7 | 7 | 6 | 372 | 7% | 12.0 | 11.7 | 6.0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v14/control AAF7E3EA58 | <60 | 49/92 | 27枚/攻0/防0/引0/eng1/強5 | 17/0 | 4 | 4 | 生存 | 371 | 7% | 0 | 12.2 | 6.8 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v1/control D6A1F8C3E5 | 60-79 | 72/73 | 29枚/攻3/防3/引0/eng1/強17 | 14/3 | 6 | 6 | 生存 | 371 | 7% | 0 | 11.5 | 16.5 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| madsci AM8C6YXHSG | <60 | 40/96 | 28枚/攻1/防3/引0/eng2/強14 | 11/1 | 3 | 3 | 生存 | 371 | 7% | 0 | 13.3 | 16.3 | TORCH_HEAD_AMALGAM:BEAM | Amalgamを殺し切る前に消耗で死亡 |
| axebot_arm_b1 D6A1F8C3E5 | 60-79 | 66/77 | 28枚/攻2/防3/引0/eng1/強18 | 15/3 | 6 | 6 | 生存 | 370 | 7% | 0 | 10.5 | 21.3 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v21/candidate EF715D6190 | 60-79 | 76/76 | 29枚/攻2/防1/引2/eng0/強12 | 17/5 | 4 | 4 | 生存 | 369 | 8% | 0 | 19.0 | 1.5 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v17/control 2E4DDCD0DB | <60 | 58/87 | 28枚/攻2/防0/引3/eng0/強5 | 9/4 | 6 | 6 | 生存 | 367 | 8% | 0 | 9.7 | 13.2 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v18/candidate 22FDB96B7C | 60-79 | 71/100 | 26枚/攻2/防3/引1/eng3/強9 | 14/3 | 6 | 6 | 5 | 366 | 8% | 34.0 | 11.3 | 5.8 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| candidate_fnpengine P3V8N5K2RX | 60-79 | 65/80 | 30枚/攻1/防3/引1/eng1/強6 | 11/2 | 8 | 8 | 7 | 366 | 8% | 12.0 | 8.1 | 12.9 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_mantle L3PN5HBQ8T | >=80 | 122/122 | 25枚/攻1/防4/引2/eng2/強5 | 9/3 | 8 | 8 | 7 | 366 | 8% | 0 | 13.6 | 12.5 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_eval_v16/candidate DFA3BB14AC | <60 | 59/76 | 28枚/攻2/防3/引0/eng2/強7 | 11/4 | 6 | 6 | 生存 | 365 | 9% | 0 | 9.3 | 6.7 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| candidate_ruptureseed H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 7 | 7 | 6 | 365 | 9% | 34.0 | 18.3 | 1.3 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_eval_v8/control 88141BFEC3 | 60-79 | 75/90 | 26枚/攻2/防3/引0/eng1/強8 | 12/3 | 6 | 6 | 生存 | 364 | 9% | 0 | 12.5 | 9.8 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| mechonly AM8C6YXHSG | >=80 | 86/105 | 32枚/攻2/防0/引1/eng3/強15 | 12/2 | 7 | 7 | 6 | 363 | 9% | 37.0 | 11.9 | 10.0 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| stratagem_P3 P3V8N5K2RX | <60 | 57/78 | 30枚/攻2/防1/引2/eng1/強6 | 11/1 | 8 | 8 | 7 | 363 | 9% | 18.0 | 7.1 | 13.5 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| juggling_mapped_panel AM8C6YXHSG | <60 | 45/96 | 28枚/攻1/防2/引1/eng2/強16 | 11/1 | 4 | 4 | 生存 | 362 | 9% | 0 | 11.2 | 12.0 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| model_fixes_panel AM8C6YXHSG | <60 | 45/96 | 28枚/攻1/防2/引1/eng2/強16 | 11/1 | 4 | 4 | 生存 | 362 | 9% | 0 | 11.2 | 12.0 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v8/candidate 901A9ED74B | 60-79 | 72/101 | 30枚/攻2/防2/引1/eng1/強15 | 11/3 | 4 | 4 | 生存 | 361 | 10% | 0 | 17.2 | 1.8 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v9/candidate 901A9ED74B | 60-79 | 72/101 | 30枚/攻2/防2/引1/eng1/強15 | 11/3 | 4 | 4 | 生存 | 361 | 10% | 0 | 17.2 | 1.8 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| candidate_new M7C4Q9V2RH | >=80 | 80/80 | 30枚/攻3/防4/引1/eng1/強7 | 11/4 | 6 | 6 | 生存 | 360 | 10% | 0 | 13.0 | 7.5 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| galvanic_M7 M7C4Q9V2RH | >=80 | 80/80 | 30枚/攻3/防4/引1/eng1/強7 | 11/4 | 6 | 6 | 生存 | 360 | 10% | 0 | 13.0 | 7.5 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v12/candidate E710402B56 | <60 | 41/88 | 23枚/攻2/防2/引0/eng3/強8 | 11/0 | 5 | 5 | 生存 | 359 | 10% | 0 | 7.6 | 9.0 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| astra_ctrl_v23/control D71DA535AD | <60 | 41/84 | 26枚/攻0/防4/引0/eng3/強13 | 13/0 | 6 | 6 | 生存 | 357 | 11% | 0 | 6.3 | 6.5 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| enginefirst_candidate_r108 AM8C6YXHSG | 60-79 | 65/103 | 31枚/攻4/防1/引0/eng3/強15 | 13/2 | 4 | 4 | 生存 | 357 | 11% | 0 | 15.5 | 2.2 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| enginefirst_control_r96 AM8C6YXHSG | 60-79 | 65/103 | 31枚/攻4/防1/引0/eng3/強15 | 13/2 | 4 | 4 | 生存 | 357 | 11% | 0 | 15.5 | 2.2 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| route_hp_heal_r78 AM8C6YXHSG | 60-79 | 65/103 | 31枚/攻4/防1/引0/eng3/強15 | 13/2 | 4 | 4 | 生存 | 357 | 11% | 0 | 15.5 | 2.2 | TORCH_HEAD_AMALGAM:TACKLE_3 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v21/candidate C53467F9A2 | 60-79 | 74/78 | 30枚/攻4/防3/引2/eng2/強8 | 8/5 | 6 | 6 | ? | 356 | 11% | 5.0 | 11.8 | 5.5 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v21/control C53467F9A2 | 60-79 | 74/78 | 30枚/攻4/防3/引2/eng2/強8 | 8/5 | 6 | 6 | ? | 356 | 11% | 5.0 | 11.8 | 5.5 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v22/candidate C53467F9A2 | 60-79 | 74/78 | 30枚/攻4/防3/引2/eng2/強8 | 8/5 | 6 | 6 | ? | 356 | 11% | 5.0 | 11.8 | 5.5 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v6/control 9629CB6A2E | <60 | 44/88 | 31枚/攻2/防2/引0/eng2/強5 | 16/0 | 3 | 3 | 生存 | 355 | 11% | 0 | 13.7 | 11.0 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v22/candidate 1CC360647D | >=80 | 88/92 | 18枚/攻5/防2/引1/eng0/強5 | 11/3 | 6 | 6 | 生存 | 353 | 12% | 0 | 14.7 | 5.7 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| priceband D6A1F8C3E5 | 60-79 | 77/79 | 30枚/攻3/防2/引1/eng1/強18 | 16/3 | 8 | 8 | ? | 353 | 12% | 3.8 | 9.2 | 13.2 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v18/candidate 2D1571760D | >=80 | 83/83 | 27枚/攻3/防1/引1/eng1/強12 | 11/3 | 8 | 8 | 7 | 351 | 12% | 35.0 | 10.4 | 14.8 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| greedydraw_N8 N8CQ4ZKP2W | 60-79 | 79/79 | 32枚/攻2/防4/引1/eng3/強7 | 17/3 | 7 | 7 | 5 | 349 | 13% | 18.5 | 10.7 | 12.1 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| debuff_arm_b1 D6A1F8C3E5 | 60-79 | 75/75 | 29枚/攻3/防3/引1/eng1/強17 | 15/3 | 8 | 8 | 7 | 348 | 13% | 23.0 | 9.4 | 13.8 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_goal_r5 AM8C6YXHSG | 60-79 | 68/99 | 30枚/攻2/防1/引1/eng3/強14 | 13/3 | 7 | 7 | 6 | 346 | 14% | 42.0 | 9.3 | 10.3 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_eval_v21/candidate 2D1571760D | 60-79 | 72/77 | 27枚/攻1/防0/引0/eng1/強12 | 11/3 | 7 | 7 | 6 | 345 | 14% | 41.0 | 10.3 | 5.1 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| goldguard AM8C6YXHSG | 60-79 | 66/103 | 29枚/攻1/防0/引1/eng3/強16 | 13/3 | 6 | 6 | 生存 | 345 | 14% | 0 | 10.5 | 12.8 | TORCH_HEAD_AMALGAM:BEAM | Amalgamを殺し切る前に消耗で死亡 |
| candidate_emergencydraw H2LV6ZJ4XW | >=80 | 129/129 | 29枚/攻1/防4/引0/eng3/強2 | 14/3 | 8 | 8 | 6 | 341 | 15% | 23.0 | 15.9 | 2.1 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| crossseed_vulnlethal H2LV6ZJ4XW | >=80 | 129/129 | 29枚/攻1/防4/引0/eng3/強2 | 14/3 | 8 | 8 | 6 | 341 | 15% | 23.0 | 15.9 | 2.1 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| exhaust_arm AM8C6YXHSG | >=80 | 88/97 | 30枚/攻3/防2/引0/eng3/強14 | 13/3 | 8 | 8 | 6 | 341 | 15% | 29.0 | 10.6 | 12.2 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| candidate_ranked N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 10 | 10 | 6 | 340 | 15% | 13.5 | 7.4 | 9.4 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_rupturefuel H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 8 | 8 | 6 | 336 | 16% | 31.5 | 15.2 | 5.8 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_ctrl_v23 46E15BFA6F | >=80 | 87/87 | 29枚/攻4/防0/引1/eng1/強11 | 14/3 | 7 | 7 | 6 | 335 | 16% | 19.0 | 12.4 | 7.1 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_unmovable H2LV6ZJ4XW | >=80 | 144/144 | 32枚/攻1/防3/引0/eng3/強3 | 14/3 | 10 | 10 | 8 | 334 | 17% | 22.0 | 13.4 | 10.5 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_eval_v20/control FD40F6616D | 60-79 | 72/88 | 27枚/攻4/防0/引1/eng0/強5 | 12/3 | 9 | 9 | ? | 329 | 18% | 3.8 | 8.0 | 10.9 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_eval_v21/control 0C20218D7E | 60-79 | 64/67 | 26枚/攻3/防2/引1/eng1/強9 | 12/1 | 5 | 5 | 3 | 328 | 18% | 36.0 | 12.8 | 2.4 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_eval_v22/candidate 0C20218D7E | 60-79 | 64/67 | 26枚/攻3/防2/引1/eng1/強9 | 12/1 | 5 | 5 | 3 | 328 | 18% | 36.0 | 12.8 | 2.4 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_eval_v22/candidate 5AB4791F7F | 60-79 | 71/85 | 27枚/攻4/防1/引1/eng2/強20 | 13/2 | 7 | 7 | 6 | 328 | 18% | 50.0 | 9.9 | 5.9 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v12/candidate A3D179EEDC | <60 | 56/70 | 23枚/攻4/防1/引0/eng2/強10 | 10/3 | 5 | 5 | 3 | 327 | 18% | 36.5 | 10.6 | 3.8 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_eval_v19/candidate 04DDDF708F | 60-79 | 71/80 | 25枚/攻2/防3/引2/eng1/強8 | 14/3 | 6 | 6 | 4 | 327 | 18% | 35.0 | 12.5 | 0.0 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| tremble_sim100 P3V8N5K2RX | <60 | 40/80 | 29枚/攻2/防3/引1/eng1/強6 | 11/1 | 3 | 3 | 生存 | 327 | 18% | 0 | 13.3 | 2.7 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_ctrl_v23/control F287271E7D | 60-79 | 60/100 | 24枚/攻1/防0/引0/eng3/強5 | 13/2 | 7 | 7 | 6 | 326 | 19% | 43.0 | 7.3 | 7.9 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| candidate_double_rage H2LV6ZJ4XW | >=80 | 139/139 | 32枚/攻2/防1/引1/eng3/強2 | 14/3 | 8 | 8 | 7 | 324 | 19% | 54.0 | 17.4 | 4.5 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_goal_r2 D6A1F8C3E5 | 60-79 | 76/77 | 28枚/攻3/防2/引1/eng2/強16 | 15/2 | 8 | 8 | 6 | 322 | 19% | 24.5 | 9.1 | 10.2 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_ctrl_v23/control 469AAE3BED | >=80 | 87/87 | 24枚/攻2/防1/引1/eng3/強7 | 12/3 | 6 | 6 | 生存 | 320 | 20% | 0 | 14.5 | 6.0 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| candidate_vulnsetup L3PN5HBQ8T | >=80 | 122/122 | 24枚/攻4/防1/引0/eng2/強4 | 9/3 | 8 | 8 | 生存 | 319 | 20% | 0 | 14.4 | 10.6 | TORCH_HEAD_AMALGAM:TACKLE_4 | Amalgamを殺し切る前に消耗で死亡 |
| astra_eval_v18/candidate EF715D6190 | 60-79 | 68/78 | 30枚/攻5/防0/引1/eng0/強12 | 18/5 | 8 | 8 | 6 | 315 | 21% | 22.5 | 8.5 | 10.0 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_eval_v22/candidate EF715D6190 | 60-79 | 68/78 | 30枚/攻5/防0/引1/eng0/強12 | 18/5 | 8 | 8 | 6 | 315 | 21% | 22.5 | 8.5 | 10.0 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_eval_v8/control 221047D541 | 60-79 | 76/110 | 25枚/攻2/防2/引2/eng2/強10 | 15/1 | 5 | 5 | 4 | 312 | 22% | 57.0 | 14.8 | 9.4 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_goal_r6 AM8C6YXHSG | 60-79 | 68/99 | 30枚/攻2/防1/引1/eng3/強14 | 13/3 | 7 | 7 | 6 | 311 | 22% | 62.0 | 9.3 | 11.1 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| candidate_offeringengine P3V8N5K2RX | 60-79 | 78/78 | 30枚/攻3/防1/引2/eng2/強6 | 11/2 | 9 | 9 | 5 | 308 | 23% | 19.2 | 8.7 | 8.7 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| act3_verify_head H2LV6ZJ4XW | >=80 | 118/127 | 28枚/攻3/防2/引0/eng2/強4 | 14/2 | 8 | 8 | 6 | 305 | 24% | 10.5 | 14.2 | 5.6 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| madsci N8CQ4ZKP2W | >=80 | 83/83 | 32枚/攻2/防3/引2/eng3/強7 | 17/3 | 8 | 8 | 6 | 305 | 24% | 39.0 | 9.5 | 6.5 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_ctrl_v23/control 5B5EA36CCE | 60-79 | 75/90 | 30枚/攻1/防3/引2/eng1/強13 | 11/3 | 10 | 10 | ? | 303 | 24% | 9.7 | 7.5 | 13.8 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v22/control 1CC360647D | >=80 | 86/100 | 19枚/攻3/防1/引3/eng0/強5 | 11/5 | 9 | 9 | ? | 303 | 24% | 7.4 | 9.6 | 9.9 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_eval_v2/candidate 7FCFED219F | 60-79 | 72/72 | 21枚/攻4/防1/引1/eng1/強8 | 10/3 | 6 | 6 | 生存 | 303 | 24% | 0 | 12.0 | 11.0 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v2/control 7FCFED219F | 60-79 | 72/72 | 21枚/攻4/防1/引1/eng1/強8 | 10/3 | 6 | 6 | 生存 | 303 | 24% | 0 | 12.0 | 11.0 | TORCH_HEAD_AMALGAM:BEAM | Amalgam生存中に burst で死亡 |
| astra_eval_v16/candidate 137020562C | 60-79 | 72/72 | 36枚/攻1/防4/引1/eng2/強15 | 11/3 | 8 | 8 | 6 | 299 | 25% | 50.5 | 9.0 | 3.2 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| engine_control_r84 D6A1F8C3E5 | >=80 | 85/85 | 29枚/攻2/防2/引0/eng1/強18 | 15/3 | 10 | 10 | 6 | 297 | 26% | 23.5 | 8.2 | 10.2 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| mechonly_arm_b3 D6A1F8C3E5 | >=80 | 85/85 | 29枚/攻2/防2/引0/eng1/強18 | 15/3 | 10 | 10 | 6 | 297 | 26% | 23.5 | 8.2 | 10.2 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| rampart_arm_b1 D6A1F8C3E5 | >=80 | 85/85 | 29枚/攻2/防2/引0/eng1/強18 | 15/3 | 10 | 10 | 6 | 297 | 26% | 23.5 | 8.2 | 10.2 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v8/candidate FBEFCF251B | >=80 | 99/105 | 32枚/攻1/防0/引0/eng2/強4 | 13/2 | 7 | 7 | 6 | 295 | 26% | 74.0 | 14.1 | 2.7 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_eval_v9/candidate FBEFCF251B | >=80 | 99/105 | 32枚/攻1/防0/引0/eng2/強4 | 13/2 | 7 | 7 | 6 | 295 | 26% | 74.0 | 14.1 | 2.7 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_ctrl_v23/control 23A7CEECF7 | <60 | 42/84 | 19枚/攻2/防0/引1/eng2/強7 | 15/3 | 4 | 4 | 3 | 291 | 27% | 69.0 | 9.0 | 13.8 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_ctrl_v23/control 161F480E76 | 60-79 | 67/68 | 24枚/攻1/防2/引0/eng0/強14 | 11/2 | 8 | 8 | 4 | 288 | 28% | 28.0 | 9.9 | 8.4 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_headbutt D6A1F8C3E5 | >=80 | 85/85 | 28枚/攻1/防2/引1/eng1/強15 | 17/3 | 10 | 10 | 6 | 287 | 28% | 25.5 | 8.2 | 11.2 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_ruptureaoe H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 9 | 9 | 5 | 285 | 29% | 25.8 | 13.1 | 5.7 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| counts_arm AM8C6YXHSG | >=80 | 93/95 | 30枚/攻3/防1/引1/eng3/強14 | 13/3 | 9 | 9 | 5 | 284 | 29% | 28.2 | 10.3 | 7.1 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| potion_arm_b1 AM8C6YXHSG | >=80 | 99/99 | 30枚/攻3/防2/引0/eng3/強13 | 13/3 | 10 | 10 | 6 | 284 | 29% | 28.8 | 9.6 | 8.8 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_execution_defense H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 9 | 9 | 5 | 281 | 30% | 29.5 | 13.2 | 6.1 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_eval_v3/candidate 7FCFED219F | 60-79 | 68/68 | 21枚/攻3/防3/引2/eng1/強8 | 10/2 | 7 | 7 | ? | 279 | 30% | 8.4 | 9.7 | 11.4 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_safe_idle_selfdamage H2LV6ZJ4XW | >=80 | 130/130 | 28枚/攻4/防1/引0/eng2/強3 | 14/2 | 9 | 9 | 7 | 278 | 31% | 52.0 | 14.0 | 7.6 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_eval_v22/control A4B7AEE91B | >=80 | 94/98 | 28枚/攻1/防1/引1/eng1/強11 | 13/3 | 10 | 10 | 6 | 273 | 32% | 29.5 | 12.5 | 5.4 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_ctrl_v23 5E58E8A550 | 60-79 | 68/68 | 29枚/攻3/防3/引0/eng2/強11 | 14/3 | 6 | 6 | 5 | 267 | 33% | 111.0 | 11.2 | 6.7 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v17/control 6A8C868A07 | >=80 | 90/107 | 29枚/攻5/防1/引0/eng1/強17 | 13/3 | 9 | 9 | 5 | 267 | 33% | 30.0 | 10.0 | 8.3 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| ruptureself_N8 N8CQ4ZKP2W | 60-79 | 77/77 | 33枚/攻2/防3/引2/eng3/強6 | 16/3 | 9 | 9 | 5 | 263 | 34% | 27.8 | 7.8 | 11.7 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| woundmap N8CQ4ZKP2W | 60-79 | 77/77 | 33枚/攻2/防3/引2/eng3/強6 | 16/3 | 9 | 9 | 5 | 263 | 34% | 27.8 | 7.8 | 11.7 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_rage_nobreakthrough H2LV6ZJ4XW | >=80 | 143/143 | 30枚/攻4/防1/引0/eng4/強3 | 14/3 | 8 | 8 | 7 | 262 | 34% | 99.0 | 16.1 | 7.8 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| woundmap H2LV6ZJ4XW | >=80 | 134/134 | 28枚/攻3/防0/引2/eng2/強2 | 14/2 | 8 | 8 | 7 | 260 | 35% | 106.0 | 16.1 | 4.9 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_eval_v10/candidate 2409DE6134 | >=80 | 83/90 | 22枚/攻2/防3/引0/eng1/強4 | 13/3 | 7 | 7 | ? | 257 | 36% | 20.4 | 11.9 | 8.0 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_eval_v12/candidate BD0D5921A6 | 60-79 | 67/78 | 23枚/攻5/防0/引1/eng4/強8 | 13/2 | 6 | 6 | ? | 256 | 36% | 21.3 | 11.2 | 7.0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v5/candidate DCC93C65AA | 60-79 | 67/76 | 30枚/攻2/防2/引1/eng2/強6 | 11/3 | 8 | 8 | 6 | 253 | 37% | 73.5 | 8.4 | 14.5 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_eval_v9/candidate 76E9F731A3 | 60-79 | 78/80 | 23枚/攻4/防2/引1/eng0/強16 | 17/3 | 8 | 8 | 4 | 253 | 37% | 36.8 | 9.8 | 8.0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v9/control 76E9F731A3 | 60-79 | 78/80 | 23枚/攻4/防2/引1/eng0/強16 | 17/3 | 8 | 8 | 4 | 253 | 37% | 36.8 | 9.8 | 8.0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v12/candidate 09A077CC49 | <60 | 57/90 | 22枚/攻2/防1/引1/eng2/強8 | 12/2 | 9 | 9 | ? | 252 | 37% | 10.8 | 5.9 | 6.8 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_ctrl_v23 81E19F92F4 | >=80 | 107/109 | 27枚/攻5/防2/引1/eng1/強8 | 12/3 | 9 | 9 | 5 | 251 | 37% | 34.8 | 11.9 | 6.6 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v22/candidate 2D1571760D | >=80 | 83/83 | 22枚/攻0/防2/引0/eng1/強6 | 11/3 | 11 | 11 | 7 | 250 | 38% | 36.0 | 7.5 | 10.1 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v11/candidate FD7A9C8F5F | >=80 | 97/114 | 21枚/攻1/防1/引0/eng3/強11 | 11/2 | 7 | 7 | ? | 248 | 38% | 14.7 | 13.4 | 3.0 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| candidate_oneblood N8CQ4ZKP2W | >=80 | 81/81 | 32枚/攻3/防2/引2/eng2/強7 | 16/3 | 9 | 9 | 5 | 248 | 38% | 34.0 | 8.9 | 10.8 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_eval_v21/control 3E69989266 | <60 | 56/80 | 25枚/攻4/防0/引0/eng1/強10 | 8/2 | 5 | 5 | ? | 246 | 38% | 27.2 | 11.2 | 3.6 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_queen_onefuel H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 8 | 8 | 6 | 244 | 39% | 77.5 | 15.2 | 2.6 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| mechpanel_arm_clean AM8C6YXHSG | >=80 | 101/101 | 31枚/攻3/防1/引0/eng3/強12 | 13/3 | 10 | 10 | 6 | 240 | 40% | 30.2 | 9.8 | 10.4 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_queenenergy H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 9 | 9 | 5 | 230 | 43% | 42.2 | 13.2 | 3.1 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| candidate_rage H2LV6ZJ4XW | >=80 | 143/143 | 30枚/攻4/防1/引0/eng3/強2 | 14/3 | 10 | 10 | 5 | 227 | 43% | 27.6 | 13.1 | 10.3 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_ctrl_v23/control C394628E60 | >=80 | 85/87 | 30枚/攻0/防0/引0/eng3/強7 | 17/3 | 12 | 12 | ? | 225 | 44% | 11.3 | 6.6 | 13.3 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v16/control 2E22D77266 | >=80 | 100/100 | 31枚/攻3/防2/引3/eng1/強21 | 14/3 | 12 | 12 | 8 | 221 | 45% | 43.8 | 8.3 | 12.8 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v14/candidate 8D95FF5CE9 | 60-79 | 76/80 | 19枚/攻5/防1/引1/eng1/強11 | 11/3 | 7 | 7 | 3 | 220 | 45% | 38.0 | 10.9 | 5.4 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_ctrl_v23/control 50B404C802 | 60-79 | 76/80 | 31枚/攻4/防1/引3/eng1/強12 | 14/3 | 10 | 10 | 5 | 218 | 45% | 33.0 | 7.6 | 12.7 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_eval_v6/candidate 9629CB6A2E | >=80 | 98/98 | 30枚/攻2/防1/引1/eng2/強6 | 16/2 | 8 | 8 | 6 | 216 | 46% | 87.5 | 11.9 | 8.6 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| candidate_inflame_rage H2LV6ZJ4XW | >=80 | 129/129 | 29枚/攻1/防4/引0/eng3/強2 | 14/3 | 9 | 9 | 5 | 215 | 46% | 43.0 | 13.3 | 8.3 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_eval_v12/candidate FD7A9C8F5F | >=80 | 114/114 | 24枚/攻1/防2/引1/eng3/強10 | 11/3 | 11 | 11 | ? | 212 | 47% | 14.7 | 11.9 | 6.7 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_single_blood_save H2LV6ZJ4XW | >=80 | 130/130 | 28枚/攻2/防3/引2/eng2/強3 | 14/2 | 8 | 8 | 6 | 212 | 47% | 93.5 | 16.0 | 2.8 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| candidate_speed N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防1/引1/eng3/強6 | 16/3 | 10 | 10 | 5 | 208 | 48% | 38.4 | 7.7 | 10.4 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| candidate_queensetup H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 9 | 9 | 5 | 205 | 49% | 48.5 | 13.2 | 6.2 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| candidate_ruptureattack H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 9 | 9 | 5 | 205 | 49% | 48.5 | 13.2 | 6.2 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_goal_r4 D6A1F8C3E5 | 60-79 | 79/83 | 29枚/攻2/防2/引0/eng2/強18 | 15/2 | 9 | 9 | ? | 201 | 50% | 17.1 | 8.4 | 12.9 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_random20/main FD7A9C8F5F | >=80 | 90/114 | 24枚/攻2/防1/引0/eng3/強10 | 11/3 | 10 | 10 | 6 | 200 | 50% | 50.0 | 14.0 | 2.5 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v16/candidate 2E22D77266 | >=80 | 91/98 | 32枚/攻2/防1/引0/eng2/強20 | 13/3 | 12 | 12 | 8 | 197 | 51% | 41.8 | 7.6 | 18.9 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_queen_savefuel H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 9 | 9 | 5 | 190 | 52% | 52.2 | 13.6 | 5.9 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残100-199) |
| astra_eval_v12/candidate FDF8F8EC98 | 60-79 | 66/66 | 29枚/攻5/防3/引1/eng0/強6 | 13/1 | 7 | 7 | 3 | 186 | 53% | 53.5 | 9.4 | 7.1 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_goal_r3 D6A1F8C3E5 | 60-79 | 74/79 | 28枚/攻2/防2/引0/eng2/強17 | 15/2 | 8 | 8 | 4 | 183 | 54% | 43.0 | 8.9 | 7.4 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_multilethal N8CQ4ZKP2W | 60-79 | 78/87 | 33枚/攻3/防1/引2/eng3/強7 | 16/3 | 9 | 9 | 5 | 180 | 55% | 51.0 | 7.9 | 10.1 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_random20/main BD0D5921A6 | 60-79 | 77/78 | 24枚/攻3/防0/引0/eng4/強9 | 13/3 | 8 | 8 | 4 | 176 | 56% | 52.0 | 9.2 | 11.0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| evfix_ctrl AM8C6YXHSG | >=80 | 99/99 | 30枚/攻3/防1/引1/eng3/強14 | 13/3 | 10 | 10 | 6 | 171 | 57% | 55.8 | 9.6 | 4.0 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残100-199) |
| evoptexport AM8C6YXHSG | >=80 | 99/99 | 30枚/攻3/防1/引1/eng3/強14 | 13/3 | 10 | 10 | 6 | 171 | 57% | 55.8 | 9.6 | 4.0 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残100-199) |
| shopexport AM8C6YXHSG | >=80 | 99/99 | 30枚/攻3/防1/引1/eng3/強14 | 13/3 | 10 | 10 | 6 | 171 | 57% | 55.8 | 9.6 | 4.0 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残100-199) |
| sw59 AM8C6YXHSG | >=80 | 99/99 | 30枚/攻3/防1/引1/eng3/強14 | 13/3 | 10 | 10 | 6 | 171 | 57% | 55.8 | 9.6 | 4.0 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残100-199) |
| relic_arm AM8C6YXHSG | >=80 | 94/112 | 32枚/攻2/防3/引0/eng3/強14 | 13/2 | 10 | 10 | 6 | 167 | 58% | 52.8 | 9.1 | 9.5 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_effective N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 12 | 12 | 5 | 160 | 60% | 32.7 | 6.1 | 11.3 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_emergencydraw N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 12 | 12 | 5 | 160 | 60% | 32.7 | 6.1 | 10.8 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_fysh60 N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 12 | 12 | 5 | 160 | 60% | 32.7 | 6.1 | 11.3 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_fysh N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 12 | 12 | 5 | 160 | 60% | 32.7 | 6.1 | 11.3 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_lastchance N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 12 | 12 | 5 | 158 | 60% | 33.0 | 5.8 | 10.8 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_rupturefirst N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 12 | 12 | 5 | 158 | 60% | 31.6 | 6.1 | 9.2 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_ctrl_v23/control 038CDAC87B | >=80 | 80/80 | 27枚/攻3/防2/引1/eng1/強10 | 16/1 | 8 | 8 | 4 | 157 | 61% | 59.5 | 10.0 | 16.6 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_tauntdraw P3V8N5K2RX | >=80 | 80/80 | 30枚/攻2/防3/引0/eng1/強5 | 11/2 | 12 | 12 | 5 | 151 | 62% | 32.9 | 6.7 | 7.0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| control_sim100 P3V8N5K2RX | >=80 | 80/80 | 30枚/攻2/防3/引0/eng1/強5 | 11/2 | 12 | 12 | 5 | 151 | 62% | 32.9 | 6.7 | 7.0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_ctrl_v23/control 41ACBF0DEA | 60-79 | 75/75 | 26枚/攻4/防4/引1/eng1/強14 | 10/2 | 8 | 8 | ? | 148 | 63% | 23.0 | 9.4 | 13.0 | QUEEN:EXECUTION | 火力不足(Queen残100-199) |
| astra_eval_v22/candidate 3E69989266 | 60-79 | 78/90 | 28枚/攻2/防1/引0/eng1/強10 | 8/3 | 7 | 7 | ? | 146 | 64% | 31.9 | 11.1 | 10.3 | QUEEN:EXECUTION | 火力不足(Queen残100-199) |
| candidate_rupture_upgrade H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 9 | 9 | 5 | 142 | 64% | 64.2 | 13.2 | 4.8 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残100-199) |
| third_seed_search H2LV6ZJ4XW | >=80 | 130/130 | 29枚/攻1/防3/引1/eng3/強3 | 14/2 | 9 | 9 | 5 | 142 | 64% | 64.2 | 13.2 | 4.8 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残100-199) |
| enchant_check_b1 H2LV6ZJ4XW | >=80 | 136/136 | 28枚/攻3/防1/引0/eng2/強2 | 14/2 | 9 | 9 | 5 | 138 | 66% | 59.0 | 14.9 | 7.1 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残100-199) |
| burrow_arm_b1 H2LV6ZJ4XW | >=80 | 137/137 | 28枚/攻1/防2/引2/eng2/強3 | 14/3 | 10 | 10 | 6 | 137 | 66% | 59.0 | 13.5 | 8.0 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残100-199) |
| mechonly_arm_b3 T5R8K2N9QP | >=80 | 82/88 | 32枚/攻2/防1/引0/eng4/強9 | 12/3 | 9 | 9 | 5 | 123 | 69% | 69.2 | 8.7 | 5.3 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_ruptureattack N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 12 | 12 | 5 | 108 | 73% | 38.7 | 6.0 | 8.2 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残100-199) |
| astra_eval_v16/candidate DC4EF6882C | >=80 | 80/106 | 29枚/攻2/防3/引0/eng1/強10 | 11/3 | 9 | 9 | 5 | 96 | 76% | 76.0 | 12.1 | 5.3 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_shop_single_blood H2LV6ZJ4XW | >=80 | 130/130 | 28枚/攻2/防3/引2/eng2/強3 | 14/2 | 10 | 10 | 6 | 93 | 77% | 71.5 | 12.3 | 3.2 | QUEEN:OFF_WITH_YOUR_HEAD | 惜敗(Queen残100未満) |
| candidate_clutchlethal N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 12 | 12 | 5 | 75 | 81% | 43.4 | 5.8 | 8.9 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_ruptureenergy N8CQ4ZKP2W | >=80 | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 12 | 12 | 5 | 75 | 81% | 43.4 | 5.8 | 8.9 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v11/candidate 09A077CC49 | >=80 | 80/84 | 26枚/攻4/防1/引2/eng2/強9 | 12/3 | 11 | 11 | ? | 72 | 82% | 23.5 | 7.8 | 4.8 | QUEEN:OFF_WITH_YOUR_HEAD | 惜敗(Queen残100未満) |
| astra_eval_v8/control FBEFCF251B | >=80 | 95/105 | 31枚/攻1/防2/引2/eng2/強6 | 13/3 | 10 | 10 | 6 | 34 | 92% | 82.8 | 10.1 | 6.4 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v21/candidate 3E69989266 | 60-79 | 78/80 | 29枚/攻1/防1/引1/eng1/強12 | 8/3 | 9 | 9 | ? | 29 | 93% | 36.3 | 8.6 | 8.7 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v1/candidate D6A1F8C3E5 | >=80 | 83/85 | 29枚/攻3/防2/引0/eng2/強19 | 18/2 | 11 | 11 | 4 | 28 | 93% | 44.7 | 7.1 | 11.7 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v2/candidate D6A1F8C3E5 | >=80 | 83/85 | 29枚/攻3/防2/引0/eng2/強19 | 18/2 | 11 | 11 | 4 | 28 | 93% | 44.7 | 7.1 | 11.7 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_eval_v2/control D6A1F8C3E5 | >=80 | 83/85 | 29枚/攻3/防2/引0/eng2/強19 | 18/2 | 11 | 11 | 4 | 28 | 93% | 44.7 | 7.1 | 11.7 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| candidate_shop_single_engine_debuff H2LV6ZJ4XW | >=80 | 130/130 | 28枚/攻2/防3/引2/eng2/強3 | 14/2 | 9 | 9 | 5 | 23 | 94% | 85.0 | 13.2 | 4.6 | QUEEN:OFF_WITH_YOUR_HEAD | 惜敗(Queen残100未満) |
| astra_eval_v16/control DFA3BB14AC | >=80 | 87/87 | 26枚/攻2/防3/引2/eng2/強12 | 12/4 | 12 | 12 | 5 | 8 | 98% | 45.4 | 6.9 | 4.2 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_random20/main 09A077CC49 | >=80 | 91/92 | 26枚/攻3/防2/引1/eng2/強11 | 12/3 | 12 | 12 | ? | 8 | 98% | 23.7 | 9.8 | 6.1 | QUEEN:OFF_WITH_YOUR_HEAD | 惜敗(Queen残100未満) |
| smoke2_foul FD7A9C8F5F | >=80 | 111/114 | 27枚/攻1/防1/引0/eng3/強10 | 12/3 | 12 | 12 | 8 | 5 | 99% | 82.5 | 13.2 | 4.5 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |

### 2-2. QUEEN戦 勝利（新形式trace、15本）

| run | 入HP/最大 | deck | relic/pot | T | Am撃破T | Q残(最終観測) | 出Q/turn | 被/turn | blk/turn | 死時のStrength | ポーション使用 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| astra_ctrl_v23 495FF454B7 | 99/113 | 28枚/攻5/防1/引1/eng2/強13 | 10/3 | 7 | 5 | 0 | 158.0 | 5.6 | 8.4 | 27 | potion:CLARITY; potion:WEAK_POTION |
| astra_eval_v14/control 8D95FF5CE9 | 76/80 | 20枚/攻4/防3/引2/eng1/強13 | 11/3 | 7 | 4 | 0 | 97.3 | 10.3 | 9.7 | 3 | potion:SKILL_POTION; potion:FORTIFIER; potion:LIQUID_BRONZE |
| astra_eval_v10/candidate DD1018C7FF | 100/100 | 29枚/攻0/防0/引1/eng2/強14 | 14/3 | 9 | None | 0 | 39.1 | 10.4 | 10.0 | 17 | potion:POTION_OF_BINDING; potion:SNECKO_OIL; potion:POTION_OF_BINDING |
| astra_goal_r8_retry1 N8CQ4ZKP2W | 85/85 | 33枚/攻1/防3/引1/eng3/強8 | 16/3 | 9 | 5 | 0 | 90.0 | 5.8 | 6.1 | 34 | potion:STRENGTH_POTION; potion:FORTIFIER; potion:POTION_OF_BINDING |
| candidate_last_hp_selfdamage H2LV6ZJ4XW | 130/130 | 28枚/攻2/防3/引2/eng2/強3 | 14/2 | 9 | 5 | 0 | 87.0 | 13.0 | 4.0 | 15 | potion:GAMBLERS_BREW; potion:CLARITY |
| smoke_v17 FD7A9C8F5F | 97/114 | 24枚/攻2/防1/引0/eng4/強9 | 11/3 | 9 | 5 | 0 | 73.0 | 9.8 | 2.4 | 12 | potion:POWER_POTION |
| astra_eval_v1/candidate N8CQ4ZKP2W | 85/85 | 33枚/攻3/防3/引2/eng3/強9 | 16/3 | 11 | 7 | 0 | 85.2 | 5.5 | 8.9 | 36 | potion:STRENGTH_POTION; potion:FORTIFIER; potion:POTION_OF_BINDING |
| astra_eval_v2/candidate N8CQ4ZKP2W | 85/85 | 33枚/攻2/防5/引0/eng3/強9 | 16/3 | 11 | 6 | 0 | 76.0 | 5.5 | 9.3 | 30 | potion:FORTIFIER; potion:POTION_OF_BINDING; potion:SWIFT_POTION |
| astra_eval_v2/control N8CQ4ZKP2W | 85/85 | 33枚/攻2/防5/引0/eng3/強9 | 16/3 | 11 | 6 | 0 | 76.0 | 5.5 | 9.3 | 30 | potion:FORTIFIER; potion:POTION_OF_BINDING; potion:SWIFT_POTION |
| astra_goal_r9 N8CQ4ZKP2W | 85/85 | 33枚/攻2/防5/引0/eng3/強9 | 16/3 | 11 | 6 | 0 | 76.0 | 5.5 | 9.3 | 30 | potion:FORTIFIER; potion:POTION_OF_BINDING; potion:SWIFT_POTION |
| act3_recheck_2675e82 N8CQ4ZKP2W | 87/87 | 33枚/攻4/防3/引2/eng3/強10 | 16/3 | 12 | 6 | 0 | 62.3 | 5.2 | 10.0 | 29 | potion:FORTIFIER; potion:POTION_OF_BINDING; potion:SWIFT_POTION |
| astra_eval_v6/candidate E8282AC0A7 | 103/107 | 22枚/攻3/防0/引1/eng1/強10 | 12/3 | 12 | None | 0 | 23.8 | 4.6 | 11.9 | 3 | potion:VULNERABLE_POTION; potion:FORTIFIER |
| candidate_vulnlethal N8CQ4ZKP2W | 81/81 | 33枚/攻2/防3/引1/eng3/強7 | 16/3 | 12 | 5 | 0 | 52.1 | 5.7 | 8.2 | 46 | potion:POTION_OF_BINDING; potion:FYSH_OIL; potion:SWIFT_POTION |
| codex_goal_20260919 N8CQ4ZKP2W | 87/87 | 33枚/攻4/防3/引2/eng3/強10 | 16/3 | 12 | 6 | 0 | 62.3 | 5.2 | 10.0 | 29 | potion:FORTIFIER; potion:POTION_OF_BINDING; potion:SWIFT_POTION |
| current_commit_known_seeds N8CQ4ZKP2W | 87/87 | 33枚/攻4/防3/引2/eng3/強10 | 16/3 | 12 | 6 | 0 | 62.3 | 5.2 | 10.0 | 29 | potion:FORTIFIER; potion:POTION_OF_BINDING; potion:SWIFT_POTION |

Q残(最終観測) は勝っても 0 にならない。勝利は最後の判断の後にトドロメが入ったことを意味する（traceは撃破の1手前で止まる）。EVALUATION.md の進捗比較では勝利=削り100%として扱う。

Am撃破T が None の本数は 2。これらは最後の観測まで Amalgam が生きていて（DD1018C7FF で HP16/199、E8282AC0A7 で HP2/199）、QUEEN への最終一手で戦闘が終わった。Amalgam を殺し切る前に QUEEN を倒した勝ち方なので、§6 候補1の根拠になる。

### 2-3. 旧traceの戦闘（32本・デッキ枚数が取れない）

| trace | encounter | 結果 | 入HP | T | 要求HPの到達点 | 死招 | 要因 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| run_deckfix_d6a1 | AEONGLASS_BOSS | 敗 | 98 | 7 | 形態0/1処理・現形態1残350（要求残350） | NO_ATTACK_TELEGRAPH | 攻撃telegraphに無い伤害で死亡 |
| astra_B_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 8 | Q残250/400・Am残0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_actcost_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 9 | Q残328/400・Am残0 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_aoe_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 9 | Q残328/400・Am残0 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| astra_elite_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 8 | Q残250/400・Am残0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_normality_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 8 | Q残250/400・Am残0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_potion1 | QUEEN_BOSS | 敗 | 85 | 8 | Q残250/400・Am残0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_routecost2_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 8 | Q残347/400・Am残0 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_routecost_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 89 | 7 | Q残265/400・Am残0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_sand_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 8 | Q残231/400・Am残0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_sblock_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 8 | Q残347/400・Am残0 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| astra_sims400_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 10 | Q残241/400・Am残0 | QUEEN:OFF_WITH_YOUR_HEAD | Amalgam処置後、Queenの burst で死亡 |
| astra_turnlethal_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 9 | Q残328/400・Am残0 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| candidate_rupture2_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 9 | Q残328/400・Am残0 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| candidate_rupture2_L3PN5HBQ8T | QUEEN_BOSS | 敗 | 122 | 8 | Q残345/400・Am残0 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| candidate_rupture2_N8CQ4ZKP2W | QUEEN_BOSS | 勝 | 79 | 16 | Q残0/400・Am残0 |  | win |
| run_multi_bbbbz | QUEEN_BOSS | 敗 | 83 | 7 | Q残222/400・Am残118 | NO_ATTACK_TELEGRAPH | 攻撃telegraphに無い伤害で死亡 |
| wide_base_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 9 | Q残328/400・Am残0 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| wide_base_L3PN5HBQ8T | QUEEN_BOSS | 敗 | 122 | 8 | Q残345/400・Am残0 | QUEEN:EXECUTION | 火力不足(Queen残200以上) |
| wide_base_N8CQ4ZKP2W | QUEEN_BOSS | 勝 | 79 | 16 | Q残0/400・Am残0 |  | win |
| wide_sblock_D6A1F8C3E5 | QUEEN_BOSS | 敗 | 85 | 8 | Q残347/400・Am残0 | QUEEN:OFF_WITH_YOUR_HEAD | 火力不足(Queen残200以上) |
| wide_sblock_N8CQ4ZKP2W | QUEEN_BOSS | 勝 | 79 | 16 | Q残0/400・Am残0 |  | win |
| astra_base_D6A1F8C3E5 | TEST_SUBJECT_BOSS | 勝 | 98 | 10 | 形態3/3処理・現形態3残0（要求残0） |  | win |
| astra_goal_endturn1 | TEST_SUBJECT_BOSS | 敗 | 98 | 7 | 形態1/3処理・現形態2残60（要求残360） | TEST_SUBJECT:MULTI_CLAW | Amalgam生存中に burst で死亡 |
| astra_goal_frail1 | TEST_SUBJECT_BOSS | 敗 | 90 | 7 | 形態1/3処理・現形態2残125（要求残425） | TEST_SUBJECT:MULTI_CLAW | Amalgam生存中に burst で死亡 |
| astra_goal_intangible1 | TEST_SUBJECT_BOSS | 勝 | 98 | 10 | 形態3/3処理・現形態3残0（要求残0） |  | win |
| astra_goal_pacts1 | TEST_SUBJECT_BOSS | 敗 | 98 | 8 | 形態2/3処理・現形態3残298（要求残298） | TEST_SUBJECT:PHASE3_LACERATE | Amalgamを殺し切る前に消耗で死亡 |
| astra_goal_scarf1 | TEST_SUBJECT_BOSS | 敗 | 98 | 7 | 形態0/3処理・現形態1残0（要求残500） | NO_ATTACK_TELEGRAPH | Amalgamを殺し切る前に消耗で死亡 |
| astra_goal_suicide1 | TEST_SUBJECT_BOSS | 敗 | 98 | 7 | 形態1/3処理・現形態2残9（要求残309） | TEST_SUBJECT:MULTI_CLAW | Amalgam生存中に burst で死亡 |
| astra_seed2_D6A1F8C3E5 | TEST_SUBJECT_BOSS | 勝 | 98 | 10 | 形態3/3処理・現形態3残0（要求残0） |  | win |
| run_multi_revenge_queen | TEST_SUBJECT_BOSS | 敗 | 83 | 7 | 形態1/3処理・現形態2残53（要求残353） | NO_ATTACK_TELEGRAPH | 攻撃telegraphに無い伤害で死亡 |
| run_potionfix_d6 | TEST_SUBJECT_BOSS | 敗 | 98 | 7 | 形態1/3処理・現形態2残101（要求残401） | NO_ATTACK_TELEGRAPH | 攻撃telegraphに無い伤害で死亡 |

## 3. 敗因の分解 (c) — QUEEN戦

分類の規則（優先順に上から適用。重複計上しない）:

| 規則 | 分類 |
| --- | --- |
| 致死ターンに QUEEN の攻撃 telegraph が無い / telegraph に無い伤害が10以上 | X. 機構漏れの疑い |
| Amalgamを殺し切る前に死亡し、致死ターンに最大HPの40%超の一撃を食らった | A1. Amalgam生存中に burst で死亡 |
| Amalgamを殺し切る前に死亡（それ以外＝だんだん削りられて死亡） | A2. Amalgam処置前に消耗 |
| Amalgam処置後、致死ターンに最大HPの40%超の一撃（OFF_WITH_YOUR_HEAD 3×5 等） | B1. Amalgam処置後にQueen burst |
| Amalgam処置後、Queen残200以上で消耗死 | C1. 火力不足（残200以上） |
| Amalgam処置後、Queen残100-199で消耗死 | C2. 火力不足（残100-199） |
| Amalgam処置後、Queen残100未満 | D. 惜敗 |

| 分類 | 本数 | Queen残中央値 | ターン中央値 | 被/turn中央値 | blk/turn中央値 | Am処置後ターン中央値 |
| --- | --- | --- | --- | --- | --- | --- |
| A1. Amalgam生存中に burst で死亡 | 32 | 382.0 | 6.0 | 13.0 | 7.5 | – |
| A2. Amalgamを殺し切る前に消耗で死亡 | 54 | 385.5 | 5.0 | 14.25 | 6.6 | – |
| B1. Amalgam処置後、Queenの burst で死亡 | 76 | 254.5 | 9.0 | 9.3 | 9.05 | 4.0 |
| C1. 火力不足(Queen残200以上) | 49 | 305 | 8 | 12.8 | 6.8 | 2 |
| C2. 火力不足(Queen残100-199) | 12 | 147.0 | 9.5 | 10.35 | 5.35 | 4.0 |
| D. 惜敗(Queen残100未満) | 4 | 47.5 | 10.5 | 11.05 | 4.7 | 2.0 |

### 3-1. 火力の到達点

| 死んだ時点のQueen残HP | 本数 | Amalgamを殺した後 | QUEENへ入れた合計HP中央値 |
| --- | --- | --- | --- |
| 300-399 | 113 | 49 | 34 |
| 200-299 | 50 | 50 | 146.0 |
| 100-199 | 28 | 28 | 240.0 |
| 400(無傷) | 22 | 0 | 0.0 |
| 1-99 | 14 | 14 | 369.0 |

400のうち何%を削れたかで並べると、上位の集団は「Amalgamに殴りを吸わせている間に自分が死んだ」型で、QUEENへの合計 damage が中央値で100に届かない run が半数近い。これは block不足でも HP不足ではなく、**QUEENへ通す火力の配分**が足りないことを示す。

### 3-1b. Amalgam の生死 × 死んだ時点の Queen 残HP（agent形式QUEEN敗北）

| 死んだ時点の Queen 残HP | 本数 | Amalgam処置後 | Amalgam生存中 | 致死一手がQUEEN burst | 致死一手がAmalgam | telegraphに無い伤害 | ターン中央値 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 400（無傷） | 22 | 0 | 22 | 0 | 22 | 0 | 5.0 |
| 300-399 | 113 | 49 | 64 | 49 | 64 | 0 | 6 |
| 200-299 | 50 | 50 | 0 | 50 | 0 | 0 | 9.0 |
| 100-199 | 28 | 28 | 0 | 28 | 0 | 0 | 10.0 |
| 1-99 | 14 | 14 | 0 | 14 | 0 | 0 | 11.0 |

Queen を 200 以上残して死んだ 185本のうち 86本は Amalgam を殺し切る前、99本は処置後で、どちらも QUEEN に通る火力が足りない形（§3-1 の QUEEN への合計火力中央値 71）で、火力の配分不足が主因です。致死一手が QUEEN の burst だった 141本は全て Amalgam を処置した後で、その 99本は Queen を 200 以上残した位置で折られています。burst を1回受け切っても残り HP が足りない band が大半なので、耐久だけを足しても決まりません（§6 候補2の限界）。Queen 残 100 未満で死んだ 14本は、1ターン分の火力か block があれば flip した可能性のある惜敗 band。

### 3-2. 被ダメージの内訳（どのintentで死んだか）

全敗北227本の被ダメージ合計 18401 の内訳（敵ターン中に失ったHP、telegraph 1件のみに攻撃が有ったターンはその move へ全額、攻撃が複数あるターンは telegraph 割合で按分）:

| 攻撃元 | 割当てHP | 割合 | 致死ターンにそれを食らって死んだ件数 |
| --- | --- | --- | --- |
| TORCH_HEAD_AMALGAM:BEAM | 6710 | 36.5% | 39 |
| QUEEN:OFF_WITH_YOUR_HEAD | 3493 | 19.0% | 112 |
| TORCH_HEAD_AMALGAM:TACKLE_3 | 2352 | 12.8% | 29 |
| TORCH_HEAD_AMALGAM:TACKLE_2 | 1694 | 9.2% | 0 |
| TORCH_HEAD_AMALGAM:TACKLE_4 | 1584 | 8.6% | 18 |
| TORCH_HEAD_AMALGAM:TACKLE | 1378 | 7.5% | 0 |
| QUEEN:EXECUTION | 1145 | 6.2% | 29 |
| UNATTRIBUTED | 45 | 0.2% | 0 |

自分のターン中の自傷（Bloodletting 等）と、その合計で死んだかは別枠:

- 自ターン中のHP減少の合計: 656（敗北227本あたり 2.9）。最終ターンに自傷で death した例: 0本。
- telegraph に attack が無いのにHPを失ったターン: 18本 / 合計 45 HP（1ターンにつき1点ずつ）。内訳は特定済みで、45/45 ターン（18本）で CRIMSON_MANTLE_POWER を乗っていた。Crimson Mantle は自分のターン開始時に自傷する power（`CrimsonMantlePower.cs:23-25` の `AfterPlayerTurnStart`、`SelfDamage` var）で、この集計の「敵ターン中の被ダメ」窓は最後の判断行→次のプレイヤー行の最初までを含むため、ターン開始の自傷がここへ落ちる。機構が抜けているのではなく窓の帰属問題で、`combat.py:2488-2490` と `official_agent.py:425` に同じ自己破壊はモデル済み。

### 3-3. 死の直前: どの一撃で倒れたか

- 最終判断ターン、敵側が telegraph していた攻撃の合計 vs （自分のHP+block）の余白: 中央値 -15（負ならその一撃で死ぬ。-20 以下は「1ターン前の判断で避けられた可能性」の目安）。余白が +10 以上あったのに死んだ本数は 0本（telegraph 与实际伤害の差＝block持続・per-hit 丸め・debuff のタイミング）。

| run | T | Am処置T | Q残 | 死前のHP/block | OFF telegraph | 余白 |
| --- | --- | --- | --- | --- | --- | --- |
| astra_eval_v1/candidate D6A1F8C3E5 | 11 | 4 | 28 | 8/6 | 13x5=65 | -51 |
| astra_eval_v2/candidate D6A1F8C3E5 | 11 | 4 | 28 | 8/6 | 13x5=65 | -51 |
| astra_eval_v2/control D6A1F8C3E5 | 11 | 4 | 28 | 8/6 | 13x5=65 | -51 |
| astra_eval_v16/control 2E22D77266 | 12 | 8 | 221 | 1/0 | 10x5=50 | -49 |
| astra_eval_v8/control 221047D541 | 5 | 4 | 312 | 20/8 | 15x5=75 | -47 |
| potion_arm_b1 AM8C6YXHSG | 10 | 6 | 284 | 3/0 | 10x5=50 | -47 |
| candidate_clutchlethal N8CQ4ZKP2W | 12 | 5 | 75 | 2/19 | 13x5=65 | -44 |
| candidate_ruptureenergy N8CQ4ZKP2W | 12 | 5 | 75 | 2/19 | 13x5=65 | -44 |
| astra_eval_v21/candidate 3E69989266 | 9 | None | 29 | 8/0 | 10x5=50 | -42 |
| relic_arm AM8C6YXHSG | 10 | 6 | 167 | 10/0 | 10x5=50 | -40 |
| astra_eval_v12/candidate FD7A9C8F5F | 11 | None | 212 | 6/5 | 10x5=50 | -39 |
| astra_eval_v9/candidate 76E9F731A3 | 8 | 4 | 253 | 12/0 | 10x5=50 | -38 |

### 3-4. 耐久 vs 火力の切り分け

`boss_hp_required_line` と HP 推移を並べて、**敵の残り要求HPが 0 に届く前に自分の HP が 0 に着いた**のかを見る（QUEEN戦の要求HP=QUEEN 400、Amalgamは任意）。Amalgam を殺し切った141本について、その戦闘の実火力レート（Amalgam処置後の QUEEN へのdamagerate）で残り Queen HP を割った、殺し切るまでの不足ターン数:

| Amalgam処置後に、QUEENを殺すまで自分の火力レートで何ターン必要だったか | 本数 |
| --- | --- |
| 1-2ターン分 | 14 |
| 3-4ターン分 | 26 |
| 5ターン分以上 | 100 |

Amalgam を殺し切れないまま死んだ 86本はこれより手前で、要求HP 599（QUEEN+Amalgam）の半分にも届いていない。ターン不足が1-2の本数が大きければ「少しの火力強化で決まる」型、5以上なら「エンジン自体が必要」型。数字はこのレートの外挿なので、終盤の QUEEN block（BurnBright +20）と ENRAGE で実値はこれより悪化する方向にずれる。

耐久側の指標: 敵ターン中の被ダメに対し block で防いだ割合の中央値は敗北 31%・勝ち 66%。勝ちは被ダメ/ターンを承知でターン 11 まで延ばしてQUEEN を倒している（敗北のターン中央値 7）。

### 3-5. 機構側の所見（デコンパイルの事実）

| 機構 | 実装 | run への効き方 |
| --- | --- | --- |
| Chains of Binding 3（PUPPET_STRINGS） | `Queen.cs:135,164-169` → `ChainsOfBindingPower.cs:36-79`。そのターン引いた札に Bound を最大3枚。Bound札はターンに1枚だけ playable（2枚目以降は `legal_actions` から 外れる）。ターン終了で全部解除。 | 盤面の札を使えず、draw で増やした札も1枚しか使えない。Amalgam を殴り切るターンが伸びる |
| Frail/Weak/Vulnerable 99（YOU_ARE_MINE） | `Queen.cs:136,171-179`。各 stacks 99 で付与、毎ターン 99→98→… と 1 ずつ減るだけで 戦闘中に消えない。 | 攻撃威力 75%（Weak）、被ダメージ 1.5倍（Vulnerable）、block 効率が Frail で下がる。終盤の OFF 3×5 が (3+Str)×1.5×5 で増える |
| Amalgam 生存中のQUEEN行動（BURN_BRIGHT_FOR_ME） | `Queen.cs:145-149,182-193`。分岐は `HasAmalgamDied` のみ。Amalgam 生存中は Amalgam へ Strength +1、Queen 自身に block 20。 | Amalgam の攻撃が毎ターン強くなり、QUEEN には block 20 が乗る。処置が長いほど 火力要求と被ダメが同時に増える |
| Amalgam 死後のQUEEN行動 | `Queen.cs:150-152,195-219,221-234`。OFF_WITH_YOUR_HEAD(3×5) → EXECUTION(15) → ENRAGE(自己Strength+2) のループ。Amalgam が BurnBright の直後に死んだ場合は ENRAGE を即実行。 | 1サイクルで (3+Str)×5×1.5 + (15+Str)×1.5 相当が周期で来る。Str が +2 ずつ伸びるので ターンが進むと burst が単調に強くなる |
| Amalgam の行動列 | `TorchHeadAmalgam.cs:46-64`。分岐なし固定: TACKLE 18 → TACKLE 18 → SOUL_BEAM 8×3 → TACKLE 14 → TACKLE 14 → BEAM に戻る。 | 1ターン目 18、2ターン目 18、3ターン目 8×3（=Vulnerableで24×3相当）と来るので、3ターン目の block 有無が早期生死を決める |

実データで確認した範囲:

- QUEEN を Amalgam 生存中に直接狙った攻撃: 98 回、57 本が 30 以上削った（最大 105）。QUEEN 側が無敵化している事実は無い（`Queen.cs` に damage を1に絞る鉗は無）
- 実トレースで Queen が毎ターン 1 しか減らなかった run は ToastyMittens + ForgottenSoul の  exhaust 由来（`combat.py:2599-2603` に記録済み）
- Amalgam を処置できずに死んだ: 86本 / 221。処置後にQUEを殺しきれずに死んだ: 141本
- 死亡時の QUEEN 残HP 中央値 328、死亡ターン中央値 7

### 3-6. boss 種別の敗因（全敗北、旧traceを含む）

| encounter | 敗北 | 死んだ時点でボス側に残っていた要求HP中央値 | ターン中央値 | 致死一手 top3 | trace形式 |
| --- | --- | --- | --- | --- | --- |
| QUEEN_BOSS | 245 | 334 | 8 | QUEEN:OFF_WITH_YOUR_HEAD 122; TORCH_HEAD_AMALGAM:BEAM 39; QUEEN:EXECUTION 36 | 新形式227・旧18 |
| TEST_SUBJECT_BOSS | 7 | 360 | 7 | TEST_SUBJECT:MULTI_CLAW 3; NO_ATTACK_TELEGRAPH 3; TEST_SUBJECT:PHASE3_LACERATE 1 | 新形式0・旧7 |
| AEONGLASS_BOSS | 1 | 350 | 7 | NO_ATTACK_TELEGRAPH 1 | 新形式0・旧1 |

- QUEEN（敗北239）: 上の §3-1b の内訳どおり、火力が Amalgam に吸われて Queen 残 200 以上で死ぬ群と、Amalgam を処置した後に Queen の burst（OFF_WITH_YOUR_HEAD / EXECUTION）で死ぬ群に分かれる。機構側は §3-5 の Chains・Weak/Frail/Vulnerable 恒久・ENRAGE の Strength 上昇が両群に効いている。
- TEST_SUBJECT（敗北7、すべて旧trace）: 形態 100/200/300 のうち処理できたのが中央値 1-2 で、致死一手は MULTI_CLAW・PHASE3_LACERATE 系と telegraph に無い伤害が混ざる。旧traceは敵の max_hp を記録していないので、形態の要求HPは export 値で補って計算している（§附の生成手順）。このボスの機構（形態切替の条件、Adaptable 系の power）は今回の pass では decompile しておらず、機構説明は未確認。勝った3本（同じ seed の再実行）は 3形態を処理した後に 3形態目の HP を 277/300 残して残りHP22・10ターンで止まっている（trace が撃破の1手前で切れるため実質は撃破）
- AEONGLASS（敗北1、旧trace）: telegraph に attack が無いままHPが減って死亡。512HP の単一形態で、旧trace では被ダメの归属精度が落ちる（手札・pile・敵 max_hp の記録が無い）

## 4. 勝った run との同軸比較 (d)

1回きりの勝ちなので因果は主張しない。EVALUATION.md の軸（入場状態・構築・削り・ターン）で並べる。

| 軸 | 勝ち15本の中央値 | 敗北227本の中央値 | 差 |
| --- | --- | --- | --- |
| 入場HP | 87 | 80 | 7 |
| 入場HP/最大HP | 1.0 | 0.96 | 0.04 |
| deck枚数 | 33 | 29 | 4 |
| 攻撃札 | 2 | 2 | 0 |
| block札 | 3 | 2 | 1 |
| draw札 | 1 | 1 | 0 |
| power札 | 0 | 0 | 0 |
| 強化済 | 9 | 9 | 0 |
| 自傷エンジン札 | 3 | 2 | 1 |
| relic数 | 16 | 13 | 3 |
| 入室時ポーション | 3 | 3 | 0 |
| プレイヤーターン | 11 | 7 | 4 |
| Amalgam処置ターン | 6 | 6 | 0 |
| QUEENへ通した合計HP | 380 | 71 | 309 |
| QUEEN火力/ターン | 76.0 | 19.2 | 56.8 |
| 被ダメ/ターン | 5.5 | 11.2 | -5.7 |
| block取得/ターン | 9.3 | 7.8 | 1.5 |
| blockで防いだ割合 | 0.66 | 0.31 | 0.35 |
| 死亡時Strength | 29 | 4.5 | 24.5 |

勝ち側の特徴（中央値差が大きい順）:

- 自傷エンジン札（Rupture / Bloodletting / Offering / Hemokinesis / Primal Force / Inflame / Burn）を 積んだデッキで、死亡時点の Strength が勝ち側中央値 29・敗北側 4.5。Obsidian『sts2-aiの勝利シード記録』が 記録する2つの勝利デッキ（D6A1F8C3E5=TEST_SUBJECT戦・Strength 32、N8CQ4ZKP2W=QUEEN戦・Strength 30）と同じ形。CODEWIKI 2026-09-08 の「エンジンだけが一致している」という記述を実データで確認した形。
- deck 枚数も勝ち側が大きい（中央値 33 対 29）。
- 被ダメ/ターンは勝ち側のほうが大きく、ターンも長い。QUEEN burst を受け切って殴り切る展開で、「blockで耐えてから削る」より「先に削る」寄り。
- 勝ちは Amalgam をターン 6 前後で処置し、QUEEN 処理まで 11 ターンかけている。敗北側の Amalgam 処置中央値は 6。

### 4-2. 勝った run の deck 構成（seed 単位。同じ seed の再実行は1行にまとめる）

| seed | 勝ち記録 | 入場HP/最大 | deck枚数 | 攻撃札 | block札 | draw札 | engine札 | relic数 | 死亡時Strength | ターン | Am処置ターン | QUEEN火力/ターン | 使用ポーション | 記録された run 名 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N8CQ4ZKP2W | 9 | 85/85 | 33 | 2 | 3 | 1 | 3 | 16 | 30 | 11 | 6 | 76.0 | 3 | act3_recheck_2675e82; astra_eval_v1_candidat; astra_eval_v2_candidat;  |
| 495FF454B7 | 1 | 99/113 | 28 | 5 | 1 | 1 | 2 | 10 | 27 | 7 | 5 | 158.0 | 2 | astra_ctrl_v23 |
| 8D95FF5CE9 | 1 | 76/80 | 20 | 4 | 3 | 2 | 1 | 11 | 3 | 7 | 4 | 97.3 | 3 | astra_eval_v14_control |
| DD1018C7FF | 1 | 100/100 | 29 | 0 | 0 | 1 | 2 | 14 | 17 | 9 | – | 39.1 | 3 | astra_eval_v10_candida |
| E8282AC0A7 | 1 | 103/107 | 22 | 3 | 0 | 1 | 1 | 12 | 3 | 12 | – | 23.8 | 2 | astra_eval_v6_candidat |
| FD7A9C8F5F | 1 | 97/114 | 24 | 2 | 1 | 0 | 4 | 11 | 12 | 9 | 5 | 73.0 | 1 | smoke_v17 |
| H2LV6ZJ4XW | 1 | 130/130 | 28 | 2 | 3 | 2 | 2 | 14 | 15 | 9 | 5 | 87.0 | 2 | candidate_last_hp_self |

勝った 7 seed（agent形式のQUEEN勝ち 15本）のうち、engine 札（Rupture / Bloodletting / Hemokinesis / Offering / Inflame / Burn 系）を積んでいるのが 7 seed。Obsidian『sts2-aiの勝利シード記録』(/Users/mao/Documents/Obsidian/20_作ったもの/sts2-aiの勝利シード記録.md) に書かれた N8CQ4ZKP2W=Rupture+Battle Trance+Bloodletting で Strength 30・31枚、D6A1F8C3E5=Strength 32（TEST_SUBJECT戦）、H2LV6ZJ4XW=23戦23勝で HP 7/130 まで削られた、という記録と、上の表の engine 札数・死亡時 Strength が同じ形をしている。block 札は seed によって 0-5 枚とばらつき、受けずに殴り切る側と受け切って削る側が混じる（§4-1 で被ダメ/ターンが敗北より勝ちのほうが大きいのは、この「受けずに削り切る」勝ち方の重み）。

## 5. ラボで再現できる入場 spec の数 (e)

spec = run_seed・act・floor・入場HP/最大HP・デッキmultiset（強化・enchantment 込み）・relic と counter・potions・敵の初期HP が同一のものを1件（Act 2ラボと同じ流儀）。抽出は `.dsh/extract_act3_specs.py` → `.dsh/act3_boss_specs.jsonl`（main data/ の読み取りのみ）。

### 5-1. 内訳

| encounter | 観測件数 | lab形式で抽出可 | spec数(重複除去) | win記録を含むspec |
| --- | --- | --- | --- | --- |
| ENCOUNTER.QUEEN_BOSS | 263 | 242（新形式traceのみ。旧traceは draw/discard/exhaust pile が無く deck multiset を作れない） | 180 | 10 |
| ENCOUNTER.TEST_SUBJECT_BOSS | 10 | 0（すべて旧trace） | 0 | 0 |
| ENCOUNTER.AEONGLASS_BOSS | 1 | 0（旧trace） | 0 | 0 |

注: 同じ入場状態でも enchantment の有無まで別に数えると別 spec になる。`enchantment` を deck key に入れない重複除去（`.dsh/act3_spec_ladder.py` が使う key）では 179 spec、入れる key（`.dsh/extract_act3_specs.py`）では 180 spec。5-2 以降は抽出ファイル側の 180 件、5-4 の ladder 比較は 179 件ベース。

### 5-2. いまの実装でそのまま使える spec

BossLab が注入できる状態だけで組み合わせた spec（unresolved 無し）は **80 / 180**、そのうちに実走の win 記録が残るのが 4 件。残り 100 件は下記の理由で除外。

| 除外の理由 | spec数 | 意味 |
| --- | --- | --- |
| relic_counters | 34 | trace の relic_counters に数値が出る counter（RELIC.PEN_NIB 22、RELIC.NUNCHAKU 11、RELIC.TUNING_FORK 8 のいずれか）を lab は初期値から始める。counter 注入は未実装 |
| card_value_state | 33 | 印刷値と違うカード vars が、入室時 Strength/Vigor・enchantment でも説明できないもの（Impervious 30→60、Bash 10→20、Taunt 8→16、Strike 6→9 等）。trace のカード `value` は「今の状態でプレイしたら出る値」の preview なので、レリック側の効果（Strike Dummy の初回 Strike、Pen Nib の9回目攻撃倍、Shiv系）なら lab でも自動で再現される。残りは run 横断の props（consumed 系）が本物の再現不能で、実機の最初の観測のカード値を突き合わせればどちらか判くできる |
| relic_run_state | 72 | 入室前後の挙動が自分の `[SavedProperty]` や室数の読み取りに依存するレリックを持つ spec（`RELIC.EMBER_TEA`・`GIRYA`・`TEA_OF_DISCOURTESY`・`VENERABLE_TEA_SET`・`BONE_TEA`・`HAPPY_FLOWER`・`MAW_BANK`・`WINGED_BOOTS` など 14 種。一覧と根拠は `.dsh/relic_run_state.json`（生成: `python3 bosslab/tools/scan_relic_run_state.py` → `bosslab/results/entry_state_relics.json` にも同じ一覧を置く）。lab は レリックをまっさらに作るので、実走が使い切った効果をもう一度発火させる。Act 3 ラボ pass1 で実際に確認したズレ: TEA_OF_DISCOURTESY が `CARD.DAZED` を2枚余計に山札へ、 VENERABLE_TEA_SET の energy 予約が消えて入場 energy が 2 不足。復元は `SerializableRelic.Props`（`SavedProperties`）で可能だが trace に出ない。bridge が props を出力に加えるまで注入では直せない（§7-4） |
| entry_mid_turn | 9 | QUEEN入室の最初の判断行がすでに戦闘中（energy 消費済み・プレイ済み札あり）の spec。HP・札の pile・block・energy は注入で揃うが、「そのターンにプレイ済みの枚数」counterは注入手段が無い（Perfected Strike 等の初手威力が lab では強くなる） |
| relic_overapplies | 2 | akabeko 等を持つのに入室観測に Vigor が出ない 2 件。原因は上記の戦闘途中観測（Vigor は最初の攻撃で消費済み）。注入すると lab だけ 8 余る |

### 5-3. 入場時 power は注入対象としてどう扱うべきか（T12a）

- 入室観測に映る player power の由来をレリック側から特定した結果、**spec 179 件のうち 172 件は deck に入っているレリックが入室時/1ターン目に付けるもの**で、lab はレリックを注入すれば同じ power を勝手に載せる。注入すると二重になる（`Vajra.cs:21-26`、`Gorget.cs:19-26`、`BronzeScales.cs:21-26`、`SwordOfJade.cs:23-25`、`Akabeko.cs:23-28`、`Brimstone.cs:25-36`、`ToastyMittens.cs:46-50`、`OddlySmoothStone.cs:21-26`、`DataDisk.cs:21-26`、`SneckoEye.cs:33-49`）。
- 敵側へ向く grant（`BagOfMarbles`/`RedMask` が `HittableEnemies` へ、`TwistedFunnel` が毒、`PhilosophersStone.cs:41-48` が敵 Strength）や、戦闘中のみ発火（`SparklingRouge` 3ターン目、`Kunai`/`Shuriken`/`RainbowRing` は AfterCardPlayed）、Elite室限定の `SlingOfCourage` は 入室時の power 説明には含めていない（`.dsh/act3_entry_powers.md` に表で残した）。
- 本当に注入が要るのは 5 spec だけ。内訳は FeelNoPain+4/FlameBarrier+6/Hellraiser+1/Plating+6/Strength+1（C394628E60 control）、Rage+5（AAF7E3EA58）、Rupture+2/Strength+1（DDA4086B1E）、NoDraw+1（2D1571760D の 2 spec）。いずれも前の戦闘でカードが乗せて次の戦闘へ持ち越した power で、入室時発火のレリックと衝突しない。lab 側は `EnterRoomDebug` の後、bridge が最初の観測を書く前に `BossLab.ApplyEntryPowers` で residual 分だけ載せる実装にした（commit 02f603c）。

### 5-4. 能力別の ladder（enchantment を deck key に入れない 179 spec 版、`.dsh/act3_spec_ladder.py`・`.dsh/act3_spec_ladder.md`・`.dsh/act3_spec_ladder.json`）

| ラボが追加で復元できるもの | usable spec | win記録を含むspec |
| --- | --- | --- |
| （なし：HP/デッキmultiset/relic/pot のみ） | 28 | 1 |
| +enchantment | 80 | 5 |
| +入場時power注入 | 80 | 5 |
| +relic counter | 90 | 8 |
| +relic の run 状態（EmberTea/Girya 系） | 136 | 11 |
| +入場観測が戦闘途中（プレイ済み札・energy・counter） | 145 | 11 |
| +relic props によるカード値 | 179 | 11 |

1段目からの増分順（上から順に能力を足した場合）: +52、+0、+10、+46、+9、+34。

Act 2 で使った clean 条件（入室時 power を除外要因に数える）は過剰で、同じ trace を今回の由来分類で数え直すと usable は 11 件より増える。enchantment 復元が最大の lever（第一段から第二段で 80 件）で、入室時 power 注入は単独では 0 件しか増やさない（residual が必要な 5 spec は enchantment 復元でも同時に塞がる）。relic counter 復元までで 90 件、run 状態レリックの props 復元までで 136 件、入場観測が戦闘途中の spec と preview で説明しきれないカード値まで含めれば全 179 件が lab の母数になる。Act 2 の clean 69 件も同じ条件で絞った集合なので、BOSSLAB_20261028 の「clean は高HPの勝利状態を減らすバイアス」という注記は strength/vigor 分だけ過大だった（Act 2 側の数値そのものは組み替えていない）。

### 5-5. enchantment の注入方法（lab 側の実装）

`SerializableCard` には `Enchantment`（`SerializableEnchantment{Id, Amount, Props}`）と `Props`、`CurrentUpgradeLevel`、`FloorAddedToDeck` があり、`RunState.LoadCard` は `CardModel.FromSerializable` を通す（`RunState.cs:433-438`）。`FromSerializable` は `EnchantInternal(...)+ModifyCard()+FinalizeUpgradeInternal()` まで行うので （`CardModel.cs:2216-2240`）、lab は札を作るときに enchantment を載せるだけ。ただし amount は trace に出ないので、ゲーム側が使う量を表で持つ（TezcatarasEmber 1 `NutritiousSoup.cs:26-28`、Nimble 2 `FresnelLens.cs:19`、Corrupted 1 `Symbiote.cs:54`、SoulsPower 1 `GraveOfTheForgotten.cs:54`、Goopy 1 `PaelsClaw.cs:37-39`、Vigorous 8 `StoneOfAllTime.cs:44-110`、Swift は既定1）。amount が違えば札の cost/vars が実走とズレるので、実機の最初の観測を突き合わせて 1枚ずつ確認する（Swift・TezcatarasEmber は cost に直接効くため見やすい）。対応済みの spec 抽出表は `.dsh/act3_boss_specs.jsonl`。

### 5-6. QUEEN 以外のボス

TEST_SUBJECT（10戦闘）と AEONGLASS（1戦闘）はすべて旧 `*_trace.jsonl` 側にしか無く、旧形式は pile を記録していないので spec を作れない（0件）。旧traceでも敵HP・ターン・致死一手は復元済みで、TEST_SUBJECT の勝ち 3本（D6A1F8C3E5 の再実行）は 3形態処理後に 277/300 残し HP22・10ターン、敗北は 7-8ターンで 1-2形態処理（致死は MULTI_CLAW / PHASE3_LACERATE 等）。Lab で測るには 新形式traceの入場記録を積む必要がある。boss は 3候補（Aeonglass/Queen/TestSubject）から map seed ごとに決まるが、2026-10 以降の Act3到達 run は全件 QUEEN（235/235）なので、其它を測るには 意図的に選ぶ仕掛けも要る。

## 6. 突破を増やす候補（今回のデータからの判定）

本数の大きい順ではなく、ラボで測れる単位で並べて、本命を1つ決める。Amalgam に殴りを集中させたまま QUEEN が無傷に近い形で死ぬ run が多いので、本命は「殴り先」にする。3案を表にし、続けて各案の根拠と測り方を書く。

| 候補 | 効果の見込み（根拠の本数） | ラボで測れるか | 実装コスト | リスク |
| --- | --- | --- | --- | --- |
| 1（本命）. 殴り先を変える: Amalgam 集中をやめ QUEEN に通す（`official_agent.py:1384-1428` の queen_minion_direct 系） | 大。Amalgam を殺し切れないまま死んだ 86本、QUEEN 残中央値 328/400（削り18%）、Amalgam 生存中に QUEEN を30以上削った run 57本、勝った 2本は Amalgam を処置する前に決着 | 測れる。usable spec 80 件で反復。方針の差は plan の mutation ではなく agent 側の切替（環境変数・設定）で入れ、同一入場状態は保つ | 小。既存の分岐のしきいと順序の変更 | Amalgam の攻撃（BEAM/TACKLE で致死一手 86本）が生きたまま長引く。Chains/Bound で手札が縛られる状態での判断change になり、bound 解除の挙動と絡む。queen_minion_direct は過去の観測で入れた規則なので、過去panelとの比較が壊れる（CODEWIKI を読む） |
| 2. Amalgam 処置後の QUEEN burst を受け切る（block を置くターン、OFF telegraph への応答） | 中。致死一手が QUEEN burst 141本（敗北227本の 62%）。ただし Amalgam 処置後に 1-2ターンで殺し切れていたのは 14本だけで、耐久だけを足しても火力が足りない | 測れる。同一入場で block 札の arm・end_turn/wait の arm を比べる | 小〜中。policy のしきい変更 | 耐久を延ばすと ENRAGE の Strength が積もり burst がさらに強くなる（同じ火力では削り切れず時間切れ）。block を置いたターンに Amalgam の HP が伸びる |
| 3. デッキ構成の対照実験（engine 札・block 札・攻撃札の追加/除去） | 大。死亡時 Strength 勝ち 29 対 敗 4.5、QUEEN火力/ターン 76.0 対 19.2（§4-1、§4-2） | 測れる（`make_bosslab_plan.py` の arm 文法が +CARD.X / -CARD.X に対応済み）。usable 80 件のうち win 記録を含むのは 4 件 | 小（arm 定義のみ）。ただし §7 のように lab の忠実性に欠ける spec が混ざるので、まず pass2 で土台を固める | lab 結果は「その札が戦闘で効くか」の証拠にとどまる（採否は reward policy 側の full run 踏破率で見る、EVALUATION.md の local/global の分離）。pool の大半が loss 記録なので flip 本数より削り割合を主信号にする |

候補に入れないもの: ポーション使用の規則。pass1 の lab では注入したポーションの効果が発火しておらず（§7-3）、実走との比較が壊れていた。修正 DLL で測り直したうえで、使用順序・対象のarm は候補1・2 の従属 arm として扱う（単独の3案目にはしない）。

### 候補1（本命）: 殴り先を変える（Amalgam 集中をやめ、QUEEN に通す）

- 本数: Amalgam を殺し切れないまま死んだ 86本、処置できたのに QUEEN を残して死んだ 141本。敗北側が QUEEN へ通した火力の中央値 71（Amalgam に消えた分が中央値 154）、死んだ時点の Queen 残中央値 328/400。Amalgam 処置のターン中央値 6 に対し死亡ターン中央値 7 なので、処置後に QUEEN を殺すためのターンが実質残っていない。
- 機構: 勝利条件は QUEEN の死亡だけでいい（secondary の Amalgam は primary が死ねば自動死亡、`CombatManager.cs:192`、`Creature.cs:245-268`）。QUEEN は Amalgam 生存中も無敵ではなく、実データで Amalgam 生存中に QUEEN を 30以上削った run が 57本（最大105）、Amalgam 生存中に QUEEN を直接狙った 攻撃が 98回有る。ただし Amalgam 生存中の QUEEN は BurnBright で毎ターン block 20 を得る（`Queen.cs:182-193`）ので、block を超えて通す量が必要になる。
- 勝った run のうち 2本は Amalgam の撃破ターンが記録に残らず、最後の観測で Amalgam が立っていた状態で決着している（astra_eval_v10_candidate DD1018C7FF は Amalgam が HP16/199 の状態でQUEENへの最終一手が決着（QUEEN側は最終観測 HP15、ターン 9）、astra_eval_v6_candidate E8282AC0A7 は Amalgam が HP2/199 の状態でQUEENへの最終一手が決着（QUEEN側は最終観測 HP73、ターン 12））。Amalgam を処置するのを待たずに QUEEN を倒す展開が実データに有るので、殴り先の比較は lab で測る意味がある。残りの 13本は Amalgam をターン 6 前後で処置してから QUEEN を倒す順になっている。
- ラボでの測り方: 同一入場に対して `official_agent.py:1384-1428` の queen_minion_direct を止める arm、QUEEN 優先に変える arm を並べて反復する。主信号は QUEEN 400に対する削り割合（EVALUATION.md の最終戦進捗。Amalgam は撃破/残HPを別記）、副信号に Amalgam 処置ターンと被ダメ。usable spec 80 件が確保できるので、arm 1つの差分が小さくても paired で拾える（BOSSLAB_20261028 §(b)）。

### 候補2: Amalgam 処置後の QUEEN burst を受け切る設計

- 本数: 致死一手が QUEEN 側 OFF_WITH_YOUR_HEAD 112本 + EXECUTION 29本 = 141本（敗北227本の 62%）。Amalgam 処置後の 141本のうち 1-2ターンで殺し切れていたのは 14本だけなので、burst を1回耐えても足りない（5ターン分以上足りないのが 100本）。耐久だけ足す改造は候補1と組で効く。
- 機構: Amalgam 死後の QUEEN は OFF(3×5ヒット)→EXECUTION→ENRAGE（自己Strength+2）のループで、プレイヤーには Weak/Frail/Vulnerable 99 が恒久で乗る（`Queen.cs:135-234`）。OFF の実値は (3+Str)×5×1.5 で周期ごとに伸び、Amalgam が BurnBright の直後に死んだ場合は ENRAGE が即座に入る（`Queen.cs:226`）。機構自体は `combat.py` に入っている（分岐 `combat.py:864-869`、Bound の gate `combat.py:1013-1026,1395-1400`、BurnBright の対象 `combat.py:1809,1838`）ので、直す対象は評価でなく受けの設計（OFF の telegraph が出たターンに何を置くか、block をどのターンに寄せるか）。
- ラボでの測り方: 候補1と同じ入場で、block を1枚足す/引く arm、OFF telegraph ターンに防御を寄せる arm を比べ、flip 本数と削り割合の両方を見る。

### 候補3: 構築側の Strength エンジン（lab では測れない）

- 勝ち deck には Rupture/Bloodletting/Hemokinesis 等の自傷エンジンがあり、死亡時 Strength が 勝ち 29 対 敗 4.5。CODEWIKI と Obsidian『sts2-aiの勝利シード記録』と同じ向きの差を実データで確認した。
- ただしこれは報酬選択（reward policy）側の変化なので、同一入場ラボでは測れない。全体比較（フル run の Act 3 踏破率）で扱う。候補1・2で測る上限（entry 固定での伸び幅）を先に把握してから、構築側の評価に進む。

### 今回の解析で見つかった lab 側の条件

- QUEEN は Amalgam を殺さなくても勝てる（secondary 側の死亡は combat end を起動しない）ので、ラボは「Amalgam 殺し忘れ」と「殴り先」を測る装置として有用。入室は `RoomType.Boss` のまま、agent の potion 判定 `{0:17,1:16,2:15}`（Act 3 = 15）に合わせる。
- spec 母数は実装込みで **80 / 180**（win 記録を含む usable 4 件）。enchantment 復元と residual power 注入は commit 02f603c で実装済み（ビルド確認済み）。power 注入が単独で増やすのは 5 spec 分で、効くのは enchantment 復元。
- 忠実性の判定材料は「lab の最初の観測の card 値・energy・block・power・敵HPを実走の同じ行と突き合わせる」こと。`card_value_state` 指定の 33 spec のズレがレリック由来の preview なら lab でも自動で再現されるし、run 横断の props（consumed 系）が原因なら再現されない。原因を1対1で特定しきるより、この突き合わせで仕分けるのが速い。
- 入場観測がすでに戦闘途中の spec が 9件ある（energy 消費済み・プレイ済み札あり）。「そのターンにプレイ済みの枚数」counter は注入手段が無いので、Perfected Strike 等が参照する初手威力が lab では強くなる。最初の plan では除外するか、arm を絞って使う。
- RELIC.EMBER_TEA / RELIC.GIRYA を持つ spec 72件は、run 側の消費状態が trace に出ないため lab だけ発火が変わる（Act 2 で除外した EMBER_TEA と同型）。注入でなく除外で扱う。
- plan の骨組み（base のみ、arms 未確定）と pass1/pass2 の対応は §7-4 と §附 に置く。pass2 では run 状態レリックを持つ spec を除外したので、pass1 の dev panel の12件のうち10件が pool から落ちている（同じ名前の plan を上書きせず `*_dev2` 系で別管理にする）。

## 7. Act 3 ラボ pass1（dev 12 trial）の実行・忠実性・停止原因

leader が実機で回したもの（dsh はゲームを起動していない）。plan は `bosslab_act3_plan_dev.json`（trial 12・base のみ・offsets [0]・sha256 3f08399838ee3a19…）。agent script sha256 61e780f81fb8a716…、game v0.107.1。pass1 に使った DLL は sha256 c2bd0975772e33cc…（commit 02f603c まで入った版）。`data/bosslab_act3_dev/lab_meta.json` はあとの再実行で上書きされたので、pass1 の sha は実行時 logs から引く。

### 7-1. 12 trial の結果

| trial | seed | spec | lab結果 | ターン | 死時のQUEEN残HP | Amalgam残HP | 経過 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | N8CQ4ZKP2W | 5fc87b6d496b | 敗 | 12 | 30 | 処置済 | 221 |
| 1 | L3PN5HBQ8T | 07963ad93703 | 敗 | 8 | 385 | 62 | 128 |
| 2 | AM8C6YXHSG | 06270e7c70af | 敗 | 3 | 400 | 144 | 39 |
| 3 | H2LV6ZJ4XW | d4c9f1140457 | 敗 | 8 | 321 | 処置済 | 126 |
| 4 | N8CQ4ZKP2W | f19fb10979bf | 敗 | 8 | 343 | 処置済 | 152 |
| 5 | 79DD8E03F6 | b91b92466c0c | 敗 | 4 | 375 | 112 | 59 |
| 6 | 3E69989266 | 69d5563583a3 | 敗 | 4 | 394 | 70 | 55 |
| 7 | D6A1F8C3E5 | f8f7a8c4d489 | 敗 | 9 | 370 | 処置済 | 108 |
| 8 | H2LV6ZJ4XW | b9b8473f7bb2 | 敗 | 9 | 286 | 処置済 | 158 |
| 9 | P3V8N5K2RX | 1ab8aedd3250 | 敗 | 6 | 366 | 67 | 78 |
| 10 | 8D95FF5CE9 | ce97488f1b73 | 敗 | 5 | 364 | 処置済 | 61 |
| 11 | BB9869D3D3 | 4744505c73ad | 敗 | 5 | 400 | 73 | 61 |

lab_results.jsonl の 12 行は全て結果を持ち、その戦闘は全て敗北（`data/bosslab_act3_dev/timeout_attempt1/` に初回の停止 trace が残っている: trial_0000、trial_0011。この2本は 200秒で kill された後、修正 DLL で再実行したもの)。死んだ時点の QUEEN 残HPは 30〜400（中央値 368.0）、Amalgam が最後に生きていた状態で終わったのが 6本。経過は 1 trial 39〜221秒（Act 3 は決定1つが重く、deck 30枚超では1本4〜5分になる）。

pass1 の結果を実走の勝敗パターンと同列には扱えない（7-3 のポーション不具合で、ポーションを使ったターンが「効果なしで消費だけ」になっていた）。trial 0 は 221秒を掛けて QUEEN を 30/400 まで削って敗北しており、終盤まで削る戦闘自体は lab で再現できている。

### 7-2. 忠実性チェック（lab の最初の観測 vs 実走の入場観測）

比較は `bosslab/tools/bosslab_fidelity.py`（比較項目: HP/最大/block/energy/max_energy/player.powers の id+amount、relic id と counter、potions、deck multiset（強化・enchantment id 込み）、pile 別枚数、敵の id/hp/max_hp/初期 move/intents、最初の判断のターン、札の preview 値 cost・Damage・Block）。生成的な詳細表は `python3 bosslab/tools/bosslab_fidelity.py --all --out-dir data/bosslab_act3_dev --plan .dsh/bosslab_act3_plan_dev.json --specs .dsh/act3_boss_specs.jsonl --out .dsh/act3_dev_fidelity/report.md`。

| trial | seed | spec | lab vs 実走（不一致項目） | spec vs 実走 | preview済み札の値 不一致/比較 | 備考 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | N8CQ4ZKP2W | 5fc87b6d | relic_counters | 一致 | 1/1 |  |
| 1 | L3PN5HBQ8T | 07963ad9 | 一致 | 一致 | 0/1 |  |
| 2 | AM8C6YXHSG | 06270e7c | 一致 | 一致 | 0/3 |  |
| 3 | H2LV6ZJ4XW | d4c9f114 | deck.multiset, pile_size.draw_pile | 一致 | 0/1 |  |
| 4 | N8CQ4ZKP2W | f19fb109 | relic_counters | 一致 | 0/4 |  |
| 5 | 79DD8E03F6 | b91b9246 | deck.multiset, pile_size.draw_pile | 一致 | 1/3 |  |
| 6 | 3E69989266 | 69d55635 | 一致 | 一致 | 0/2 |  |
| 7 | D6A1F8C3E5 | f8f7a8c4 | 一致 | 一致 | 比較対象なし |  |
| 8 | H2LV6ZJ4XW | b9b8473f | deck.multiset, enemies.id_hp_maxhp, pile_size.draw_pile | 一致 | 0/1 |  |
| 9 | P3V8N5K2RX | 1ab8aedd | 一致 | 一致 | 0/1 |  |
| 10 | 8D95FF5CE9 | ce97488f | player.energy, player.hp | 一致 | 0/3 |  |
| 11 | BB9869D3D3 | 4744505c | 一致 | 一致 | 0/2 |  |

集計: lab と実走の入場状態が完全一致 6本、不一致 6本（内訳 deck.multiset 3本, pile_size.draw_pile 3本, relic_counters 2本, enemies.id_hp_maxhp 1本, player.hp 1本, player.energy 1本）。spec 抽出は実走に対して 12/12 一致（抽出プロセスは正しい）。札の preview 値は両側が preview した 22 種類のうち 2 種類のみの不一致。入場観測が戦闘途中の spec はこの panel に 0 件（usable 条件で除外済み）。

- 不一致の例（trial 0 N8CQ4ZKP2W）`CARD.POMMEL_STRIKE+0+`: lab=[["1", "11", ""]] / 実走=[["1", "22", ""]]
- 不一致の例（trial 5 79DD8E03F6）`CARD.CONFLAGRATION+0+`: lab=[["1", "2", ""]] / 実走=[["0", "2", ""]]

TezcatarasEmber を適用した Strike が一致側に入っているので、enchantment 復元は cost・Damage とも実走と同じ値を出している（amount 表の既定値 1 で足りた）。Nimble・Corrupted・SoulsPower・Goopy はこの panel では preview されず未検証（amount 表の値が正しいかは pass2 で preview される spec を選んで確認する）。

不一致の内訳の判定: `relic_counters` の差（lab だけ `RELIC.PEN_NIB: 0` が出る）は bridge が counter を常に出すことによる表示差で威力には効かない。deck に余分な札が出る3本 （trial [3, 5, 8]）は 入室時挙動が run 側の状態に依存するレリック（TEA_OF_DISCOURTESY の Dazed 追加、VENERABLE_TEA_SET の energy 予約）で、pass2 の spec 条件では除外した（§5-2）。敵 HP が 1 ずれる本（最初の判断の前に1点入る）と energy 2・HP 4 ずれる本も同じ系統。

### 7-3. 2本の停止と、完走10本に共通するポーション不具合

停止した trial 11 の attempt1 は、trace が turn 3 seq 13 の end_turn まで進んだ所で止まり、attempt2 の trace は同じ seq 13 まで完全一致でその先へ進んでいる（再生順は同じ）✓ エージェントが首を捻っていたのではなく、**敵ターンの実行中に game 側の task が死んで次の観測が来なかった**。mod log のスタック:

```
System.InvalidOperationException: Sequence contains no matching element
  at System.Linq.Enumerable.First[TSource](IEnumerable`1 source, Func`2 predicate)
  at MegaCrit.Sts2.Core.Nodes.Potions.NPotionContainer.RemoveUsed(PotionModel potion)
  at MegaCrit.Sts2.Core.Entities.Players.Player.RemoveUsedPotionInternal(PotionModel potion)
  at MegaCrit.Sts2.Core.Models.PotionModel.RemoveBeforeUse()
  at MegaCrit.Sts2.Core.Models.Potions.FairyInABottle.AfterPreventingDeath(Creature creature)
  at MegaCrit.Sts2.Core.Commands.CreatureCmd.Damage(...)
  at MegaCrit.Sts2.Core.Models.Monsters.TorchHeadAmalgam.SoulBeamMove(...)
  at MegaCrit.Sts2.Core.Entities.Creatures.Creature.TakeTurn()
```

原因: BossLab は `Player.AddPotionInternal(model, slot, silent: true)` でポーションを注入する（`official_mod/BossLab.cs`）が、`silent: true` は `PotionProcured` を上げないので、画面上の holder node が作られない。node は `NPotionContainer.Initialize`（run UI が作られる1回きり、注入より前）と `PotionProcured` でのみ増える（`Nodes/Potions/NPotionContainer.cs:197-207`）。使うと `RemoveUsed` が holder 一覧を `First(...)` で引いて例外（`NPotionContainer.cs:352-357`）で、agent が使っても `FairyInABottle` が自動で使っても同じ所を通る。

pass1 の log には `GameAction UsePotionAction ... completed with exception` が 29 件あり、完走した10本でも例外が出ている。例外は `RemoveBeforeUse`、つまり効果の発動より前なので、**ポーションはスロットから消えるのに効果は適用されない**（trial 2 seq 2 の FIRE_POTION は target を指定しているのに次の行の敵 HP が変わっていない、など trace で確認）。Fairy 経由の致死回避も同じで、trial 11 はそこで止まった。つまり pass1 の 12/12 敗北は「ポーション効果抜きの戦闘」の結果で、実走の敗北分布と比較するならやり直しが必要。

### 7-4. 修正と pass2 への引き継ぎ

- 修正: `BossLab.RefreshPotionUi` を追加（`EnterRoomDebug` の後、bridge を起動する前に `NRun.Instance.GlobalUi.TopBar.PotionContainer.Initialize(runState)` をもう一度読んで holder を作り直す）。`dotnet build` 0 warnings 0 errors、生成 DLL sha256 9a298350ec1d580a171537e90432f70f10796ab699e5181eccffd26703a1a392。
- runtime 確認: 停止した2 trial を leader が修正 DLL で再実行し、どちらも例外なしで完走した（trial 0: 221s・turn 12 まで進行・QUEEN 30/400 まで削って敗北、trial 11: 61s・停止点と同じ seq 13 を越えて turn 5 まで生存）。これで node 問題は解消と判断してよいが、確認できているのは2 trial だけ。
- **完走した10本も修正 DLL で回し直す**（ポーション効果が乗った戦闘にする）。pass1 の `data/bosslab_act3_dev/` は別名で保存してから上書きすると、pass1/pass2 の較べ方が明確になる。
- runner への提案（T13-2 の「散発的な停止」対策）: `-IdleTimeoutSeconds`（既定 90〜120 秒、trace ファイルの最終更新が N 秒動かなければ kill）を足す。今回の2停止はどちらも「最後の観測の後、game が action queue を流さない」型なので、`-TimeoutSeconds` を延ばすより idle 検出の方が早く安全に落とせる。1決定に 40〜221 秒かかる Act 3 では、elapsed だけでは計算中と queue 停止の区別ができない。idle なら trace の更新有無で判別できる。
- pass2 の plan（run 状態レリックを除外して組み直した pool: usable 80 / 180）:
  - `bosslab_act3_plan_fidelity2.json`: trial 3・spec 3・offsets [0]・sha256 6c79192f5b83beb3…
  - `bosslab_act3_plan_dev2.json`: trial 12・spec 12・offsets [0]・sha256 8e58c97a143cc2b1…
  - `bosslab_act3_plan_confirm2.json`: trial 12・spec 12・offsets [2]・sha256 1673df30de074263…
  - `bosslab_act3_plan_confirm3.json`: trial 12・spec 12・offsets [2]・sha256 9b4a0daf26de1c0d…

### 7-5. pass2（base）の実行結果と忠実性

pass1 で確認した不具合を、修正 DLL と run 状態レリックを除外した pool（usable 80 / 180）で確かめ直した panel。実行条件は各 dir の lab_meta.json から読んだ。

#### 忠実性確認 3 trial（`data/bosslab_act3_fidelity2/`）

- 実行条件: plan `bosslab_act3_plan_fidelity2.json` sha256 6c79192f5b83beb3… / DLL 9a298350ec1d580a… / commit 2748bc1 / agent `official_agent.py` / idle kill None / 完走 3・タイムアウト 0・ポーション例外 log 行数 0
- 忠実性: lab の最初の観測 vs 実走の入場観測が完全一致 1/3本（不一致 relic_counters 1本, player.block 1本, player.powers 1本, pile_size.hand 1本, pile_size.draw_pile 1本, pile_size.discard_pile 1本, pile_size.exhaust_pile 1本, enemies.id_hp_maxhp 1本）。lab 側の deck に余分な札: なし。札の preview 値は両側が preview した 3 種類のうち不一致 1 種類。
- 結果: 完走 3本（勝ち 0）· Queen 削り中央値 39% / 平均 39% · Amalgam を処置できないまま死んだのが 0本 · 経過 1 trial 108〜199秒
| trial | seed | spec | 結果 | ターン | 死時Queen残 | Queen削り | Amalgam残 | Queenへの与ダメ概算 | Amalgamへの与ダメ概算 | 失HP | blockで吸収 | 経過秒 | lab vs 実走 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | N8CQ4ZKP2W | 3e7eb281 | 敗 | 11 | 244 | 39% | 処置済 | 135.0 | 173.0 | 75.0 | 95.0 | 199 | relic_counters |
| 1 | DD1018C7FF | 161e7059 | 敗 | 10 | 171 | 57% | 処置済 | 142.0 | 94.0 | 92.0 | 96.0 | 141 | 一致 |
| 2 | 2D1571760D | 9596f14e | 敗 | 8 | 316 | 21% | 処置済 | 55.0 | 152.0 | 64.0 | 123.0 | 108 | enemies.id_hp_maxhp, pile_size.discard_pile, pile_size.draw_pile, pile_size.exhaust_pile, pile_size.hand, player.block, player.powers |
- trial 0（N8CQ4ZKP2W / 3e7eb281）の不一致:
  - `relic_counters`: lab={"RELIC.PEN_NIB": 0} / spec={}
- trial 2（2D1571760D / 9596f14e）の不一致:
  - `player.block`: lab=22 / spec=50
  - `player.powers`: lab=[["POWER.NO_DRAW_POWER", 1]] / spec=[["POWER.NO_DRAW_POWER", 1], ["POWER.VIGOR_POWER", 8]]
  - `pile_size.hand`: lab=0 / spec=1
  - `pile_size.draw_pile`: lab=22 / spec=17
  - `pile_size.discard_pile`: lab=4 / spec=3
  - `pile_size.exhaust_pile`: lab=1 / spec=6
  - `enemies.id_hp_maxhp`: lab=[["MONSTER.TORCH_HEAD_AMALGAM", 180, 199], ["MONSTER.QUEEN", 399, 400]] / spec=[["MONSTER.TORCH_HEAD_AMALGAM", 198, 199], ["MONSTER.QUEEN", 399, 400]]
#### 開発用 12 trial（`data/bosslab_act3_dev2/`）

- 実行条件: plan `bosslab_act3_plan_dev2.json` sha256 8e58c97a143cc2b1… / DLL 9a298350ec1d580a… / commit 2748bc1 / agent `official_agent.py` / idle kill None / 完走 12・タイムアウト 0・ポーション例外 log 行数 0
- 忠実性: lab の最初の観測 vs 実走の入場観測が完全一致 5/12本（不一致 deck.multiset 3本, relic_counters 3本, pile_size.draw_pile 1本, potions 1本）。lab 側の deck に余分な札: CARD.STRIKE_IRONCLAD+1+ x1 2本, CARD.ANGER+1+ x1 1本, CARD.POMMEL_STRIKE+0+ x1 1本, CARD.BYRD_SWOOP+1+ x1 1本。札の preview 値は両側が preview した 24 種類のうち不一致 4 種類。
- 結果: 完走 12本（勝ち 0）· Queen 削り中央値 29% / 平均 27% · Amalgam を処置できないまま死んだのが 3本 · 経過 1 trial 54〜205秒
| trial | seed | spec | 結果 | ターン | 死時Queen残 | Queen削り | Amalgam残 | Queenへの与ダメ概算 | Amalgamへの与ダメ概算 | 失HP | blockで吸収 | 経過秒 | lab vs 実走 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | B4J8Q1R6YK | 8e975fbd | 敗 | 6 | 345 | 14% | 20 | 0.0 | 90.0 | 67.0 | 57.0 | 93 | deck.multiset |
| 1 | FBEFCF251B | 8dbc5b83 | 敗 | 8 | 297 | 26% | 処置済 | 80.0 | 147.0 | 94.0 | 63.0 | 117 | 一致 |
| 2 | 79DD8E03F6 | b91b9246 | 敗 | 4 | 377 | 6% | 64 | 15.0 | 127.0 | 44.0 | 53.0 | 64 | deck.multiset, pile_size.draw_pile |
| 3 | SOS6XYXCNO | f7fe72c3 | 敗 | 4 | 387 | 3% | 26 | 0.0 | 173.0 | 46.0 | 6.0 | 54 | deck.multiset |
| 4 | AM8C6YXHSG | b947d020 | 敗 | 10 | 254 | 36% | 処置済 | 36.0 | 138.0 | 63.0 | 105.0 | 140 | 一致 |
| 5 | N8CQ4ZKP2W | f19fb109 | 敗 | 12 | 175 | 56% | 処置済 | 199.0 | 178.0 | 69.0 | 139.0 | 205 | relic_counters |
| 6 | D6A1F8C3E5 | 65702aa4 | 敗 | 7 | 332 | 17% | 処置済 | 63.0 | 167.0 | 61.0 | 47.0 | 86 | 一致 |
| 7 | D6A1F8C3E5 | 6fb95979 | 敗 | 7 | 369 | 8% | 処置済 | 15.0 | 178.0 | 55.0 | 33.0 | 90 | 一致 |
| 8 | D6A1F8C3E5 | 0b21d5e5 | 敗 | 10 | 220 | 45% | 処置済 | 151.0 | 147.0 | 58.0 | 109.0 | 130 | 一致 |
| 9 | N8CQ4ZKP2W | 9c9b1484 | 敗 | 11 | 227 | 43% | 処置済 | 177.0 | 173.0 | 73.0 | 121.0 | 203 | relic_counters |
| 10 | N8CQ4ZKP2W | 57313213 | 敗 | 11 | 237 | 41% | 処置済 | 172.0 | 173.0 | 68.0 | 125.0 | 201 | relic_counters |
| 11 | C53467F9A2 | fecbbdef | 敗 | 7 | 272 | 32% | 処置済 | 30.0 | 155.0 | 72.0 | 49.0 | 97 | potions |
- trial 0（B4J8Q1R6YK / 8e975fbd）の不一致:
  - `deck.multiset`: lab={"CARD.STRIKE_IRONCLAD+1+": 1, "CARD.ANGER+1+": 1} / spec={"CARD.STRIKE_IRONCLAD+0+": 1, "CARD.ANGER+0+": 1}
- trial 2（79DD8E03F6 / b91b9246）の不一致:
  - `deck.multiset`: lab={"CARD.POMMEL_STRIKE+0+": 1} / spec={}
  - `pile_size.draw_pile`: lab=21 / spec=20
- trial 3（SOS6XYXCNO / f7fe72c3）の不一致:
  - `deck.multiset`: lab={"CARD.BYRD_SWOOP+1+": 1, "CARD.STRIKE_IRONCLAD+1+": 1} / spec={"CARD.BYRD_SWOOP+0+": 1, "CARD.STRIKE_IRONCLAD+0+": 1}
- trial 5（N8CQ4ZKP2W / f19fb109）の不一致:
  - `relic_counters`: lab={"RELIC.PEN_NIB": 0} / spec={}
- trial 9（N8CQ4ZKP2W / 9c9b1484）の不一致:
  - `relic_counters`: lab={"RELIC.PEN_NIB": 0} / spec={}
- trial 10（N8CQ4ZKP2W / 57313213）の不一致:
  - `relic_counters`: lab={"RELIC.PEN_NIB": 0} / spec={}
- trial 11（C53467F9A2 / fecbbdef）の不一致:
  - `potions`: lab=["POTION.OROBIC_ACID", "POTION.POWER_POTION", "POTION.VULNERABLE_POTION"] / spec=["POTION.DEXTERITY_POTION", "POTION.ENERGY_POTION", "POTION.OROBIC_ACID", "POTION.POWER_POTION", "POTION.VULNE
#### 確認用 12 trial（`data/bosslab_act3_confirm2/`）

- 実行条件: plan `bosslab_act3_plan_confirm2.json` sha256 1673df30de074263… / DLL 9a298350ec1d580a… / commit d32a132 / agent `official_agent.py` / idle kill 0 / 完走 12・タイムアウト 0・ポーション例外 log 行数 0
- 忠実性: lab の最初の観測 vs 実走の入場観測が完全一致 8/12本（不一致 relic_counters 2本, player.hp 2本, deck.multiset 1本）。lab 側の deck に余分な札: CARD.BURNING_PACT+1+ x1 1本, CARD.DEFEND_IRONCLAD+1+ x1 1本。札の preview 値は両側が preview した 16 種類のうち不一致 2 種類。
- 結果: 完走 12本（勝ち 1）· Queen 削り中央値 19% / 平均 28% · Amalgam を処置できないまま死んだのが 5本 · 経過 1 trial 49〜194秒
| trial | seed | spec | 結果 | ターン | 死時Queen残 | Queen削り | Amalgam残 | Queenへの与ダメ概算 | Amalgamへの与ダメ概算 | 失HP | blockで吸収 | 経過秒 | lab vs 実走 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | AM8C6YXHSG | b05bd018 | 敗 | 4 | 380 | 5% | 70 | 20.0 | 111.0 | 31.0 | 41.0 | 49 | 一致 |
| 1 | AM8C6YXHSG | 94149577 | 敗 | 7 | 301 | 25% | 処置済 | 22.0 | 37.0 | 59.0 | 70.0 | 116 | 一致 |
| 2 | P3V8N5K2RX | 494896fc | 敗 | 7 | 377 | 6% | 8 | 0.0 | 147.0 | 68.0 | 83.0 | 110 | 一致 |
| 3 | AM8C6YXHSG | 51d0afcd | 敗 | 6 | 368 | 8% | 17 | 0.0 | 91.0 | 58.0 | 54.0 | 84 | 一致 |
| 4 | N8CQ4ZKP2W | 867e4dad | 敗 | 11 | 338 | 16% | 処置済 | 57.0 | 184.0 | 73.0 | 101.0 | 194 | relic_counters |
| 5 | N8CQ4ZKP2W | 3e7eb281 | 敗 | 11 | 232 | 42% | 処置済 | 93.0 | 184.0 | 81.0 | 104.0 | 192 | relic_counters |
| 6 | A4B7AEE91B | a8f49615 | 敗 | 10 | 186 | 54% | 処置済 | 143.0 | 145.0 | 85.0 | 67.0 | 119 | deck.multiset, player.hp |
| 7 | FD7A9C8F5F | 54912dc8 | 勝 | 10 | None | 100% | 処置済 | 132.0 | 70.0 | 106.0 | 33.0 | 172 | player.hp |
| 8 | BB9869D3D3 | 4744505c | 敗 | 6 | 400 | 0% | 33 | 0.0 | 154.0 | 66.0 | 25.0 | 73 | 一致 |
| 9 | AM8C6YXHSG | a3a10386 | 敗 | 8 | 309 | 23% | 処置済 | 25.0 | 92.0 | 86.0 | 75.0 | 114 | 一致 |
| 10 | P3V8N5K2RX | 50fd0da5 | 敗 | 6 | 386 | 4% | 3 | 0.0 | 164.0 | 50.0 | 57.0 | 85 | 一致 |
| 11 | D6A1F8C3E5 | ddb0e68f | 敗 | 9 | 171 | 57% | 処置済 | 173.0 | 173.0 | 81.0 | 109.0 | 103 | 一致 |
- trial 4（N8CQ4ZKP2W / 867e4dad）の不一致:
  - `relic_counters`: lab={"RELIC.PEN_NIB": 0} / spec={}
- trial 5（N8CQ4ZKP2W / 3e7eb281）の不一致:
  - `relic_counters`: lab={"RELIC.PEN_NIB": 0} / spec={}
- trial 6（A4B7AEE91B / a8f49615）の不一致:
  - `player.hp`: lab=90 / spec=94
  - `deck.multiset`: lab={"CARD.DEFEND_IRONCLAD+1+": 1, "CARD.BURNING_PACT+1+": 1} / spec={"CARD.BURNING_PACT+0+": 1, "CARD.DEFEND_IRONCLAD+0+": 1}
- trial 7（FD7A9C8F5F / 54912dc8）の不一致:
  - `player.hp`: lab=114 / spec=97
#### confirm 予備 12 trial（`data/bosslab_act3_confirm3/`）

- 実行条件: plan `bosslab_act3_plan_confirm3.json` sha256 9b4a0daf26de1c0d… / DLL 9a298350ec1d580a… / commit d32a132 / agent `official_agent.py` / idle kill 320 / 完走 1・タイムアウト 1・ポーション例外 log 行数 0
- 忠実性: lab の最初の観測 vs 実走の入場観測が完全一致 2/2本（不一致なし）。lab 側の deck に余分な札: なし。札の preview 値は両側が preview した 2 種類のうち不一致 0 種類。
- 結果: 完走 1本（勝ち 1）· Queen 削り中央値 100% / 平均 100% · Amalgam を処置できないまま死んだのが 0本 · 経過 1 trial 112〜112秒
| trial | seed | spec | 結果 | ターン | 死時Queen残 | Queen削り | Amalgam残 | Queenへの与ダメ概算 | Amalgamへの与ダメ概算 | 失HP | blockで吸収 | 経過秒 | lab vs 実走 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FD7A9C8F5F | bf5c0080 | 勝 | 8 | None | 100% | 処置済 | 111.0 | 62.0 | 73.0 | 7.0 | 112 | 一致 |
| 1 | D6A1F8C3E5 | 897931d3 | – | timeout | – | – | – | 67.0 | 171.0 | 61.0 | 47.0 | kill | 一致 |

### 7-7. pass2 で残った忠実性のズレと、その中身

pass2 の不一致には pass1 に無かった型が3つ出た。どれも plan の値と spec の値は一致している（lab が入力を読み間違えているのではない）ので、game 側の注入経路の問題として切り出せる。

1. **札の upgrade が lab 側で1枚分ずれる**（dev2 trial 0・3、confirm2 trial 6。枚数は同じで、実走 `+0` の札が lab だと `+1` になっている）。該当 trial は Whetstone・Toxic Egg・Pomander・Yummy Cookie・StoneCracker といった「取得時/追加時に札を強化する」系のアティファクトを持っている。lab はレリックを `AddRelicInternal(..., silent: true)`（`Player.cs` の silent 追加）で載せるため `AfterObtained` は飛ぶが、**deck への追加自体**に対する hook（Egg 系）や、turn 開始時の追加（Crossbow 系）は飛ぶので、実走がそのレリックを得る前に加えた札まで lab で強化される方向にずれる。
2. **ポーションが lab では3本までしか乗らない**（dev2 trial 11）。この spec は POTION_BELT を持ち、実走の入場観測には5本載っている。lab の注入は `slot < player.MaxPotionCount` で打切る（`official_mod/BossLab.cs` のポーション注入ループ）が、Potion Belt のスロット増加は `AfterObtained` 側なので silent 追加では増えない。2本が黙って落ちる。
3. **入場 HP が lab だけ大きい**（confirm2 trial 7・114 対 97）。同上、取得時に HP を変えるアティファクト（Pantograph 等）の `AfterObtained` が silent 追加で飛ぶ/遅れる経路の疑い。どの hook なのかは特定できていない（次タスク）。

対処の候補は次の順。まず (a) 走査ルールに `AfterObtained` を入れ、取得時/追加時に札を足す・強化する・スロットを増やすレリックを持つ spec を除外または†にする（現在の `bosslab/tools/scan_relic_run_state.py` の ENTRY_HOOKS に入っていない）。次に (b) BossLab 側で、レリック追加後にスロット数を作り直す（`Player.cs` のスロット追加 API を叩くか、注入前に `MaxPotionCount` を plan のポーション数まで拡張する）と、ポーション落ちを防げる。ただし **いま leader が候補 panel を凍結条件で走らせている最中なので、DLL を変えて base/候補の比較可能性を壊さない**（この節のズレは base・候補で同じ入り方をするので、配对比較では打ち消される。絶対値としての忠実性は上の一致本数より低い、と読む）。

### 7-6. pass2 base の敗因（dev2 + confirm2 の完走分）

完走 24本（win 記録のある spec からの panel なので base 側の勝ち 1本）で、Queen 削り中央値 24%・平均 28%・削り 75% 以上で死んだのが 1本・5% 未満 4本。Amalgam を処置できないまま死んだのが 8本、処置後に Queen を残して死んだのが 16本。

Queen への与ダメ概算の中央値 33・Amalgam への与ダメ概算の中央値 150・失HP 中央値 68・block で防いだ概算中央値 65・死亡ターン中央値 7.5。実走の敗北側（§3-1 の Queen への火力中央値 71・Amalgam に消えた火力中央値 154・敵ターンあたりの被ダメ中央値 11）と同軸で比べるための数字だが、lab の定義はターン窓の差分で、§3-2 の ただし書き（player ターン開始効果や敵の self-block が窓に混じる）をそのまま踏む。Amalgam への火力は Queen の進捗に合算しない（EVALUATION.md の召喚物の扱い）。

死亡ターンに盤面へ居た敵の attack 系 intent（death window の行に映っていたもの、重複込み）: QUEEN:Attack 14、TORCH_HEAD_AMALGAM:Attack 8。

pass1 で出たタイプのズレが pass2 でも出るかの判定は、上の各 panel の不一致項目から読む。run 状態レリック由来の余分な札（`CARD.DAZED`）と入場 energy 差は、pass2 の pool からそれらを持つ spec を落としたので消えているはずで、実際に消えたかは一致本数と不一致項目の列に現れる。`relic_counters` の表示差（lab だけ `RELIC.PEN_NIB: 0` が出る）は bridge 側の表示の問題なので残る（威力には効かない）。

## 8. 候補1の実装状況（副本エージェント、T14-1）

`bosslab/agents/official_agent_queenfirst.py` に official_agent.py の副本を置いた（main の official_agent.py は無変更）。変更は heuristic 内の2か所で、どちらも `queen_present` で守られている所の中だけ。

1. QUEEN が居るとき TORCH_HEAD_AMALGAM を重点対象にしていた短絡（旧 `queen_minion_ids`・`queen_minion_direct`）を QUEEN 本人に向ける。Rupture / Hellraiser / Inflame / Bloodletting の setup、block ゲート、lethal を先に立てる順序はそのまま。decision_source は base の trace と見分けるため `*_queen_direct` 系に改名した。
2. `focused_minions` から TORCH_HEAD_AMALGAM を外す（`{"MONSTER.KIN_FOLLOWER"}` のみに）。Queen 戦で Amalgam 殺しを強制しないため。

差分の確認: `diff -u official_agent.py bosslab/agents/official_agent_queenfirst.py`（生成済みの同じ diff を `.dsh/queenfirst_agent.diff` に置いた）。block・ポーション・end_turn の分岐は main と同一行で、`test_official_agent_queenfirst.py` の7テストが (a) QUEEN 戦で attack の target が実走 base は Amalgam、候補は Queen になること、(b) 殴り先が変わるだけで block が必要なターンでは両者が同じ防御を選ぶこと、(c) QUEEN が居ない戦闘（Decimillipede・Kin Follower）では base と同一の選択になること、を固定している。base 側の既存 Queen テスト（test_official_agent.py の 5件）はそのまま通る。suite は python3 -m unittest discover -p 'test_*.py'。

ラボでの較べ方（実機は leader）: 同じ plan・同じ実行 seed・同じ入場状態で base と候補を別 OutDir で走らせ、`python3 bosslab/tools/analyze_bosslab.py --run data/bosslab_act3_dev2 --run "queenfirst=data/bosslab_act3_queenfirst" --out .dsh/act3_queenfirst_analysis.md --specs .dsh/act3_boss_specs.jsonl` で spec・offset ごとの配对比較を出す。主信号は Queen 削り割合（実走 Act 3 の base 勝率は約7%で床なので、勝敗は補助）。Amalgam 撃破・死亡ターン・失ったHPは 補助列で、EVALUATION.md のとおり召喚物は Queen の進捗に合算しない。

## 附. 再現手順

```bash
cd ~/.sts2/wt-bosslab
python3 .dsh/act3_scan.py            # -> .dsh/act3_fights_census.jsonl（件数の速い census）
python3 .dsh/act3_boss_detail.py     # -> .dsh/act3_boss_fights.jsonl（戦闘1行=1件の台帳）
python3 .dsh/relic_power_map.py      # -> .dsh/relic_powers.json（レリック→power 対応表）
python3 bosslab/tools/scan_relic_run_state.py # -> .dsh/relic_run_state.json（入室時の挙動が run
                                     #    状態に依存するレリックの一覧。lab 用 plan の除外根拠)
python3 .dsh/act3_entry_powers.py    # -> .dsh/act3_entry_powers.md・.jsonl（入場power の由来）
python3 .dsh/extract_act3_specs.py   # -> .dsh/act3_boss_specs.jsonl・.md（lab 用 spec）
python3 .dsh/act3_spec_ladder.py     # -> .dsh/act3_spec_ladder.md・.json（能力別の usable 数）
python3 .dsh/act3_report.py          # -> .dsh/act3_boss_losses.md（このファイル）
```

忠実性チェックと plan 生成（pass2 のコマンド。忠実性用 plan の spec 一覧は `python3 bosslab/tools/make_bosslab_plan.py --specs .dsh/bosslab_act3_fidelity2.specs.jsonl --arm base --max-specs 3 --trials-per-arm 1 --offset-start 0 --order-seed act3-fidelity2 --allow-unresolved --out .dsh/bosslab_act3_plan_fidelity2.json --md .dsh/bosslab_act3_plan_fidelity2.md`。spec 一覧は能力確認用に3件を手で選んだもの）

```bash
python3 bosslab/tools/bosslab_fidelity.py --all --out-dir data/bosslab_act3_dev \
    --plan .dsh/bosslab_act3_plan_dev.json --specs .dsh/act3_boss_specs.jsonl \
    --out .dsh/act3_dev_fidelity/report.md
python3 bosslab/tools/make_bosslab_plan.py --specs .dsh/act3_boss_specs.jsonl --arm base \
    --max-specs 12 --trials-per-arm 1 --offset-start 0 --order-seed act3-dev2 \
    --out .dsh/bosslab_act3_plan_dev2.json --md .dsh/bosslab_act3_plan_dev2.md
python3 bosslab/tools/make_bosslab_plan.py --specs .dsh/act3_boss_specs.jsonl --arm base \
    --max-specs 12 --trials-per-arm 1 --offset-start 2 --order-seed act3-confirm2 \
    --skip-specs .dsh/bosslab_act3_dev2.speclist \
    --out .dsh/bosslab_act3_plan_confirm2.json --md .dsh/bosslab_act3_plan_confirm2.md
```

ゲームは起動していない（実機忠実性は leader 側）。ビルドとラボ実行のコマンド:

```bash
pwsh -File ./build_official_mod.ps1 -GameDir "$HOME/Library/Application Support/Steam/steamapps/common/Slay the Spire 2"
pwsh -File ./run_official_bosslab.ps1 -GameDir "$HOME/Library/Application Support/Steam/steamapps/common/Slay the Spire 2" -Plan .dsh/bosslab_act3_plan_fidelity2.json -OutDir data/bosslab_act3_fidelity2 -AgentScript official_agent.py -AgentSimulations 100 -TimeoutSeconds 700 -IdleTimeoutSeconds 320
pwsh -File ./run_official_bosslab.ps1 -GameDir "$HOME/Library/Application Support/Steam/steamapps/common/Slay the Spire 2" -Plan .dsh/bosslab_act3_plan_dev2.json -OutDir data/bosslab_act3_dev2 -AgentScript official_agent.py -AgentSimulations 100 -TimeoutSeconds 700 -IdleTimeoutSeconds 320
# 候補1（殴り先を Queen 本人へ）を同じ plan・同じ実行 seed で差し替えて測る
pwsh -File ./run_official_bosslab.ps1 -GameDir "$HOME/Library/Application Support/Steam/steamapps/common/Slay the Spire 2" -Plan .dsh/bosslab_act3_plan_dev2.json -OutDir data/bosslab_act3_queenfirst -AgentScript bosslab/agents/official_agent_queenfirst.py -AgentSimulations 100 -TimeoutSeconds 700 -IdleTimeoutSeconds 320
# 配对比較（主信号は Queen 削り割合。Amalgam は別記、勝敗は補助）
python3 bosslab/tools/analyze_bosslab.py --run data/bosslab_act3_dev2 --run "queenfirst=data/bosslab_act3_queenfirst" --out .dsh/act3_queenfirst_analysis.md --specs .dsh/act3_boss_specs.jsonl
```

- 集計時点: 新形式trace 1289本・旧trace 582本・manifest 617件、fights 274行、lab 用 spec 180 件。census 側の除外内訳（log 無し 87・block 突合不一致 5）は `.dsh/act3_fights_census.jsonl` と 1-1 の表参照。
