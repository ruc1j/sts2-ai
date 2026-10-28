# BossLab trial plan

- specs: `act3_boss_specs.jsonl` 全 180 件のうち選択条件を通ったもの 50 件から 12 件（order-seed `act3-confirm4` の hash 順、上位 12 件）
- v1 の状態注入で扱えない spec（enchantment・カードの vars・relic counter・入場時 power） を除いた残りは全 spec 中 80 件
- arms: base（単一 arm なので rotation なし）
- require-card: なし（deck にその札を含む spec だけを選ぶ。除去 arm が実際に除去できるようにする）
- trials: 12（arm 別 {'base': 12}）、offset 2..2で乱数を振る（再測定計画は別の offset 範囲を使い、実効 seed を独立させる）
- 入室 hook の扱い（bosslab/tools/relic_entry_effects.py）: 入室後に付与する deferred が 1 trial（RELIC.STONE_CRACKER）、開手札がlab で再現できない flag が 0 trial（なし）。入場 HP とポーション枠は BossLab.cs 側で記録値に寄せるため trial 単位の指定はない
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_confirm4.json`

## 除外条件（dev2 結果を見る前に確定）

対象プールは `act3_boss_specs.jsonl` の QUEEN_BOSS 180 件（全員 Queen 戦闘）。まず v1 の注入で扱えない
spec（unresolved）を落とし、次に `.dsh/bosslab_act3_used.speclist`（dev2/confirm 系で使った 26 件）と
重複する spec を落とし、次に下の除外レリックを持つ spec を落とす。残った eligible 50 件から
order-seed `act3-confirm4` の sha256(seed|spec_id) 順で上位 12 件を選ぶ。除外・選定はすべて実走の前に
固定した。

除外レリックと理由:
- 開手札にランダム札を混ぜる系（`relic_entry_effects.py` の `flag_unfixed` 族すべて）: CROSSBOW /
  TOOLBOX / BIG_HAT / ORANGE_DOUGH / POWER_CELL / BLESSED_ANTLER / FUNERARY_MASK / JEWELED_MASK /
  RADIANT_PEARL。入室 hook または最初のターンの開始・ドローでゲーム側の RNG が札を生むため、lab が
  同じ札を同じ位置に出せる保証がなく、入場状態が再現できない。leader が CROSSBOW を除いた理由（ターン
  単位のランダム付与）を、同じ性質の全レリックに広げた。除外した結果 flag_relics は 0 件。
- RELIC.GOOPY: 入室時に決まる Defend のブロック量が lab で特定できず防御値がずれる。

対処して保持（除外しない）:
- RELIC.STONE_CRACKER: `defer_relics` を付け入室後に付与するので、入室 hook の 2 ランダム札アップグレード
  が二重発火しない（confirm3_fixed で deck 一致を確認済み）。この panel では 1 trial（1563989f9e55）。
- RELIC.ROYAL_POISON: 除外しない。ターン 1 の自己被ダメージ 4 は HP 修正（コミット 927f26f、初手判断の
  直前に記録値へ寄せる）で解消する前提。この panel の 2 件（c589d7860c35・59ed603b4b73）が修正の実機検証
  になる。

この計画は計画のみで実走していない。HP 修正は未ビルド（dev2 3 腕が現行 DLL で走行中のため）で、ビルドと
実機反映は leader の合図 later。

注: `used.speclist` に confirm3_fixed の spec が反映されていない。59ed603b4b73 は confirm3_fixed の
trial 0010 と同一 spec で、used.speclist に入ってないため選定された。完全に独立した新規 panel にするには
confirm3_fixed の各 spec を used.speclist へ追記してから再生成する必要がある（leader の指示待ち）。

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| 8340d5737b02 | 72 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 29 | 負 | base |
| c589d7860c35 | 53 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 18 | 負 | base |
| c79980be865c | 65 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 28 | 負 | base |
| 56accb541102 | 59 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| 624ae0d1306b | 90 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 24 | 負 | base |
| 98ab6c77b59b | 72 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 27 | 負 | base |
| 703d7333c072 | 77 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 30 | 負 | base |
| 1563989f9e55 | 44 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 34 | 負 | base |
| f737cab6f8b6 | 94 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 32 | 負 | base |
| 5f6a1726cfea | 81 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| c247ea1ceac4 | 90 | TORCH_HEAD_AMALGAM:196/QUEEN:397 | 29 | 負 | base |
| 59ed603b4b73 | 90 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 31 | 負 | base |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。
