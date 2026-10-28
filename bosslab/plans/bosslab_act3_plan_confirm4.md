# BossLab trial plan

- specs: `act3_boss_specs.jsonl` 全 180 件のうち選択条件を通ったもの 40 件から 12 件（order-seed `act3-confirm4` の hash 順、上位 12 件）
- v1 の状態注入で扱えない spec（enchantment・カードの vars・relic counter・入場時 power） を除いた残りは全 spec 中 80 件
- arms: base（単一 arm なので rotation なし）
- require-card: なし（deck にその札を含む spec だけを選ぶ。除去 arm が実際に除去できるようにする）
- trials: 12（arm 別 {'base': 12}）、offset 2..2で乱数を振る（再測定計画は別の offset 範囲を使い、実効 seed を独立させる）
- 入室 hook の扱い（bosslab/tools/relic_entry_effects.py）: 入室後に付与する deferred が 1 trial（RELIC.STONE_CRACKER）、開手札がlab で再現できない flag が 0 trial（なし）。入場 HP とポーション枠は BossLab.cs 側で記録値に寄せるため trial 単位の指定はない
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_confirm4.json`

## 除外条件（dev2 結果を見る前に確定）

対象プールは `act3_boss_specs.jsonl` の QUEEN_BOSS 180 件（全員 Queen 戦闘）。まず v1 の注入で扱えない
spec（unresolved）を落とし、次に `.dsh/bosslab_act3_used.speclist`（dev2/confirm 系で使った 26 件）と
重複する spec を落とし、次に下の除外レリックを持つ spec を落とす。残った eligible 40 件から
order-seed `act3-confirm4` の sha256(seed|spec_id) 順で上位 12 件を選ぶ。除外・選定はすべて実走の前に
固定した。

除外レリックと理由（すべて「入室 hook が最初の判断で消費する RNG/状態が lab で再現不能」の系統）:
- 開手札にランダム札を混ぜる系（`relic_entry_effects.py` の `flag_unfixed` 族すべて）: CROSSBOW / TOOLBOX /
  BIG_HAT / ORANGE_DOUGH / POWER_CELL / BLESSED_ANTLER / FUNERARY_MASK / JEWELED_MASK / RADIANT_PEARL。入室
  hook か最初のターンの開始・ドローでゲーム側の RNG が札を生むため、lab が同じ札を同じ位置に出せる保証が
  ない。leader が CROSSBOW を除いた理由を同じ性質の全レリックへ拡張。flag_relics は 0 件。
- RELIC.PAELS_CLAW（ENCHANTMENT.GOOPY の供給元）: Goopy を付与された Defend の block = 基礎 +
  (Amount - 1)、Amount はその札のプレイ回数で増る per-card の run 状態（Goopy.cs:28-42 /
  PaelsClaw.cs:30-46）。trace は Amount を出さず hand の block としてしか見えないため lab で特定不能
  （block 5 vs 7、T21.2）。
- RELIC.PENDULUM: `[SavedProperty] TurnsSeen` が 3 ターン毎に 0 へ wrap した最初のターン開始で 1 枚引く
  （Pendulum.cs:75-90）。実走は boss 入室時にカウンタが 2 で最初のターン開始に引き→入室手札 6、lab は
  新規レリック（TurnsSeen=0）で引かず手札 5。カウンタは trace に出ない per-relic の run 状態。
  scan_relic_run_state.py は元来 AfterPlayerTurnStart を見ず「初手判断に影響なし」と誤分類していたため
  自動除外されず panel に残った。走査に AfterPlayerTurnStart を追加（コミット c6a4ac7）＋ここで明示除外。

対処して保持（除外しない）:
- RELIC.STONE_CRACKER: `defer_relics` を付け入室後に付与するので、入室 hook の 2 ランダム札アップグレードが
  二重発火しない（confirm3_fixed で deck multiset と札の cost/値が一致、T21.3）。ただし defer により
  StoneCracker の `StableShuffle(CombatCardSelection)`（StoneCracker.cs:20-28）が入室 hook で開戦手札の
  RNG stream を消費しなくなり、開戦手札の中身が実走と異なる（deck 総枚数と各札の値は同じ、引かれる札だけ
  違う）。この panel では 1 trial（1563989f9e55）。その trial の初手開戦手札の構成差は戦略の差でなく注入の
  帰結なので、判定では開戦手札の構成・枚数の差は無視し、deck multiset と中盤以降の状態で比較する（下記）。
- RELIC.ROYAL_POISON: 除外しない。ターン 1 の自己被ダメージ 4 は HP 修正（コミット 927f26f）で解消する前提。
  この panel の 2 件（c589d7860c35・59ed603b4b73）が修正の実機検証になる。

### 入室 hook 起因の開戦手札の差について（T21.3、confirm3_fixed 0002 = spec 83e6a3465fde で検証）

その trial の lab 初手 hand 5 / draw 26 に対し記録（= 元trace と一致）は hand 6 / draw 25。これは元trace の
入場観測のアーチファクトではない（fidelity: spec=元trace 一致、不一致は pile_size の hand/draw の 2 項目
だけ、deck 31 枚 multiset と各札の cost/Block・Damage は全一致）。差は 2 つの別系統:
- 枚数 5 vs 6: RELIC.PENDULUM が実走の最初のターン開始（カウンタ wrap）で 1 枚引いた分。lab はカウンタ
  復元不能（per-relic run 状態、trace に出ない）で引かない。
- 中身の差（lab=STRIKE/TAUNT 系、記録=DARK_EMBRACE/FEED/EVIL_EYE 系）: RELIC.STONE_CRACKER を defer した
  ことで開戦手札を配る RNG stream が実走とずれ、別の 5 枚が配られる。
どちらの開戦手札の差も札の「値・deck 内容」の誤りではなく、入室 hook の RNG / 状態を lab が再現できない
帰結。よって STONE_CRACKER / PENDULUM を含む spec では初手の hand/draw 枚数と構成の差を採否判定で無視し
（候補の戦略の差と扱わない）、同じ entry の base 候補間配対では両腕に同じ制約がかかるので比較の向きは
保たれる。ただし初手そのものは異なる開戦手札からの判断になる点は弱みとして明記する。confirm4 は PENDULUM を
除外したので、残る STONE_CRACKER 1 trial についてのみこの開戦手札構成の caveat があたる。

注1: プール全体で PAELS_CLAW 2 件（bbbfd4fc2927・2d1d3d3b4f4e、いずれも CROSSBOW 併せ持ち）、PENDULUM 41 件。
PENDULUM 除外後も eligible 40 件で 12 件は埋まる。PENDULUM 除外で選定は変わり、c79980be865c・98ab6c77b59b・
703d7333c072 の PENDULUM 3 件が落ち、75157844a09c・2f944dc24562・8aa46daede55 が入った。

注2: `used.speclist` に confirm3_fixed の spec が反映されていない。59ed603b4b73 は confirm3_fixed の
trial 0010 と同一 spec で、used.speclist に入ってないため選定された。完全に独立した新規 panel にするには
confirm3_fixed の各 spec を used.speclist へ追記してから再生成する必要がある（leader の指示待ち）。

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| 8340d5737b02 | 72 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 29 | 負 | base |
| c589d7860c35 | 53 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 18 | 負 | base |
| 56accb541102 | 59 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| 624ae0d1306b | 90 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 24 | 負 | base |
| 1563989f9e55 | 44 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 34 | 負 | base |
| f737cab6f8b6 | 94 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 32 | 負 | base |
| 5f6a1726cfea | 81 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| c247ea1ceac4 | 90 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 29 | 負 | base |
| 59ed603b4b73 | 90 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 31 | 負 | base |
| 75157844a09c | 114 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 24 | 負 | base |
| 2f944dc24562 | 78 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 30 | 負 | base |
| 8aa46daede55 | 111 | TORCH_HEAD_AMALGAM:199/QUEEN:399 | 27 | 負 | base |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
