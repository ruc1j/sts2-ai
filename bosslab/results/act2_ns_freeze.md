# Act 2 noshrug の凍結記録（確認用を流す前）

開発用の24 trial（12 spec × base/noshrug）は完走した（失敗0）。結果は `act2_ns_dev_report.md`。事前登録（`act2_ns_prereg.md`）に従い、確認用を見る前に次のとおり凍結する。

## 開発用の結果（調整は行わない）

- 発火（G''）: 6 / 12 組（閾値4）。満たしたため、候補を測定の対象に残し、確認用に進む。
- ボスを削った割合: noshrug優6、base優1、同値5（Δshave +5、p=0.125）。平均はbase 81.2%、noshrug 87.0%。
- 総火力/ターン: base 28.2、noshrug 29.7（Δfp +1.5）。
- 勝ち: base 6、noshrug 7（Δwin +1）。生存ターンは9.17から9.08（noshrug優4、base優3、同値5）。
- 開発用の結果は候補に好意的な向きだった。ただし12組の1乱数で、p=0.125。候補の定義（未強化Shrugを1枚外す）は変更しない（調整は0組合せ）。

## 確認用

- plan: `bosslab_act2_plan_ns_conf.json`（12 spec × base/noshrug = 24 trial。事前登録時点のままで、訂正後のハッシュと同じ）。
- エージェント: `official_agent.py`（無変更）。
