# BossLab trial plan

- specs: `--spec-ids` による手動選択 12 件（band/outcome/card 条件は無視、列挙順で trial_index 0.. を割り当てる）
- このうち 12 件は v1 の注入で扱えない状態を含み、lab の合成状態は実走から次の分だけずれる（方向は既知: enchantment・カードの成長値・入場時 power・relic counter が消える）:
  - b4a2aa806372: relic_counters_unobserved
  - 5f6a1726cfea: relic_counters_unobserved
  - b3a5b3a3434c: relic_counters_unobserved, relic_run_state:RELIC.HAPPY_FLOWER
  - 3e7eb2812625: relic_counters_unobserved
  - 56accb541102: relic_counters_unobserved
  - ff496290bef2: relic_counters_unobserved, relic_run_state:RELIC.HAPPY_FLOWER
  - 64bf5887f985: relic_counters_unobserved, relic_run_state:RELIC.HAPPY_FLOWER
  - 9c9b148472cd: relic_counters_unobserved
  - 5fc87b6d496b: relic_counters_unobserved, relic_run_state:RELIC.HAPPY_FLOWER
  - f19fb10979bf: relic_counters_unobserved
  - 867e4dad6aa9: relic_counters_unobserved
  - 5731321317b5: relic_counters_unobserved
- arms: base（単一 arm なので rotation なし）
- 選定条件: --spec-ids ファイル列挙時点の裁量（生成器は条件適用なし）
- trials: 12（arm 別 {'base': 12}）、offset 0..0で乱数を振る
- 入室 hook の扱い（bosslab/tools/relic_entry_effects.py）: 入室後に付与する deferred が 0 trial（なし）、開手札がlab で再現できない flag が 0 trial（なし）。入場 HP とポーション枠は BossLab.cs 側で記録値に寄せるため trial 単位の指定はない
- 実行: `pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' -Plan bosslab_act3_plan_fid6.json`

## 選択された base spec

| spec | 入場HP | 敵HP | デッキ枚数 | 記録された実走 | mutation |
| --- | --- | --- | --- | --- | --- |
| b4a2aa806372 | 81 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 32 | 負 | base |
| 5f6a1726cfea | 81 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| b3a5b3a3434c | 83 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 32 | 負 | base |
| 3e7eb2812625 | 87 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 勝 | base |
| 56accb541102 | 59 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| ff496290bef2 | 41 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 32 | 負 | base |
| 64bf5887f985 | 81 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 31 | 負 | base |
| 9c9b148472cd | 81 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| 5fc87b6d496b | 79 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 32 | 負 | base |
| f19fb10979bf | 78 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| 867e4dad6aa9 | 77 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |
| 5731321317b5 | 81 | TORCH_HEAD_AMALGAM:199/QUEEN:400 | 33 | 負 | base |

注: `deck` は pile 順を捨てた全集合（ソート順）で、戦闘開始のシャッフルはゲーム側の乱数（run seed と walked floors から決まる stream）が行う。同じ seed・同じ floor でも引く順は元の run と完全には一致しない（一致させたい場合は `.dsh/bosslab_notes.md` の「入場順を固定する」案）。

## 実行（実機は leader）

fid6 は忠実性の入場再照合専用 plan（判定には使わない）。旧ブリッジ（relic_counters_observed が偽）で
除外されたカウンターレリック RELIC.PEN_NIB 所持 spec 14 件のうち、hash 順で 12 件（order seed `fid6`、
除外 2 件 `b90f21b465f8` / `2f944dc24562`）。NUNCHAKU / TUNING_FORK は observed 偽の spec がこの集合に無かった。
入場時に BossLab が最初のターンで PEN_NIB のカウンタを書き戻すので、旧 trace spec を新 build の
relic_counters 列付き観測で流し、入場が一致するか確かめる。

- 起動（base agent、run dir `data/bosslab_act3_fid6_base`）:
```bash
pwsh -File ./run_official_bosslab.ps1 -GameDir '<game dir>' \
  -Plan bosslab/plans/bosslab_act3_plan_fid6.json -OutDir data/bosslab_act3_fid6_base -AgentScript official_agent.py
```
- 忠実性照合（完走後 1 行）:
```bash
python3 bosslab/tools/confirm_fidelity_report.py --out-dir data/bosslab_act3_fid6_base \
  --plan bosslab/plans/bosslab_act3_plan_fid6.json --specs .dsh/act3_boss_specs.jsonl \
  --flag RELIC.PEN_NIB --out bosslab/results/act3_fid6_fidelity.md
```
