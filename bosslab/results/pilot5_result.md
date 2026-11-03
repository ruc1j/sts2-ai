# PILOT-5: 休憩の HEAL を SMITH に置き換える反事実

ゲーム起動なし、main の方針コードは変更していない（候補は別ブランチ）。値はすべてモデル内。

## 1. 先に読んだ経緯（過去に悪化した記録）

- `CODEWIKI.md:144`（2026-09-08）: 休憩の回復をHP上限との距離で足切りする案は**不採用**。固定4seedの休憩22回中21回がHEALで、欠損が上限の15%未満ならSMITHへ回すと、K7M2QX9BTRが15戦→13戦と悪化、R9TB3LKD6Mが11戦→12戦と改善。有効3seedで上下に割れた。恒久強化はその周回内に現れるとは限らないがHPは即座に効く、という非対称が理由の候補。
- `CODEWIKI.md:584-593`: ボス直前の休憩をHEALかSMITHか、114局面×6回・探索30回で局所検証。入場HP60未満ではHP+24が+11.7pt、1枚強化は+2.8pt。HP80以上では回復が上限で切られるため1枚強化が+4.4pt。結論は「休憩の規則は変えない」。現在の `heal_waste`（回復の大半が捨てられるときだけSMITH）と同方向。
- `CODEWIKI.md:225`: HATCH を常に選ぶ案は、既存pin 3件（`test_rest_heals_near_boss`、`test_forges_even_next_to_the_boss`、`test_forges_when_the_heal_would_be_mostly_wasted`）を壊すため**閉じた**。

つまり「HPが十分あるときのSMITH優先」は、方向としては既に2回試されて、どちらも採用されていない。

## 2. SMITHの強化先は誰が選ぶか

`official_mod/RestBridge.cs:69` で、SMITHを選ぶと `SmithCardSelector` を積む。ゲームのランダムではなく**エージェントが選んでいる**。点数は `RestBridge.cs:119` の規則（RUPTURE最優先1200、ボス近傍の強ブロック1000+、PS/HELLRAISER 700、RUPTURE系680、CORRUPTION系660、INFLAME/PRIMAL_FORCE/DOMINATE 640、…STRIKE 100）。反事実ではこの点数を写して、未強化札のうち最高点のものを強化した。

## 3. 反事実アーム（PILOT-4と同じ89入場、1乱数）

各runの記録から、条件に合うHEALをSMITHに置き換え、置き換えた回数だけ未強化札を強化し、そのHEALの回復量を入場HPから引いた（下限 max_hp の10%）。

| アーム | 条件 | 置換回数 | 置換したrun | 入場HPの減（中央/最大） | 途中で死んだ可能性 |
| --- | --- | ---: | ---: | ---: | ---: |
| R50 | HP50%以上のHEALすべて（near_bossも） | 296 | 86/89 | 63 / 153 | 25/89 |
| R50B | 同上だが near_boss は残す | 246 | 85/89 | 54 / 136 | 20/89 |
| R35 | HP35%以上 | 333 | 88/89 | 72 / 165 | 38/89 |

モデル内の結果（main との配対、同じ入場・同じ乱数）:

| アーム | Queen勝ち | Queen削り | 改善/悪化 | 生存 | Insatiable勝ち | Ins削り |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| main | 1/59 | 0.246 | — | 7.1 | 12/30 | 0.782 |
| R50 | 0/59 | 0.185 | 14/35 | 4.0 | 4/30 | 0.515 |
| R50B | 0/59 | 0.187 | 12/35 | 4.4 | 8/30 | 0.592 |
| R35 | 0/59 | 0.180 | 14/38 | 3.9 | 4/30 | 0.488 |

3アームとも main より悪い。最良は R50B（Insatiable 12→8勝）だが、Queen勝ちは 1→0、削りは 0.246→0.187。置き換えるほど入場HPが落ち、生存ターンが 7.1→4.4 に縮む。これは「途中で死んだ可能性」を数えていない分だけ甘い見積もりである（R50Bで20/89）。

## 4. 候補の実装（指示どおり最良アームを実装）

- ブランチ `cand/smith-first`、worktree `~/.sts2/wt-clear5b`、commit `614fb41`。base は main `43f0e09`。
- 変更は `official_agent.py` の `choose_rest` のみ。`near_boss` でなく、かつ `hp*2 >= max_hp` なら SMITH を返す分岐を、`heal_waste` の後・HEAL判定の前に追加。閾値はアームの値のまま調整していない。
- `official_agent.py` sha256 先頭 `9bb052490b6c4365`。DLLはビルドせず main からコピーし、`592dc5411a6efda5` で一致を確認。
- テスト: 860件中856成功・4失敗（テストは書き換えていない）。

| 落ちたテスト | 分類 |
| --- | --- |
| `test_rest_heals_before_boss` | **過去の障害の再発**。このfixtureは `run.floor` を持たないため `near_boss` が偽になり、HP64/80でもSMITHを選ぶ。実runではfloorが入るので起きにくいが、「ボス前は回復」のpinそのものと衝突する |
| `test_rest_hatches_egg_when_healthy` | この戦略変更そのものの帰結（HP81%でHATCHよりSMITHが先に出る） |
| `test_rest_hatches_mid_act_when_healthy` | 同上 |
| `test_still_heals_when_the_deficit_is_worth_it` | この戦略変更そのものの帰結（HP62.5%・欠損37.5%でもSMITH） |

## 5. 判断材料

モデル内では、休憩のHEALをSMITHに置き換える方向は**主信号（Queen勝率・Insatiable勝率）を下げる**。過去2回の不採用記録と同じ向き。候補 `614fb41` は指示に従って作ったが、開発用の枠を使う前に、この結果を見て判断してほしい。強化そのものの効果（PILOT-4のD2でQueen 8.5%）は、入場HPを犠牲にせずに得る必要がある。

留保: 反事実は入場HPだけを下げ、道中の死亡は数えていない（別欄の推定のみ）。支配率の高い置き換え（1run中央3回）を含む。
