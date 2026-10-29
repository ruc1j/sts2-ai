# dev5 で最初に追加する調整候補（T36.3）

## 結論

追加で試す候補は **H3c の danger 閾値 0.3**（構成 C）。既定の H3a（N=2）と H3c（閾値 0.5）を測り終わってから、
dev5_swap に対して 3 番目の候補 arm として 1 構成だけ足す。confirm5 には出さず、dev5 だけで比べる。

## なぜ C を追加するのか

T34 の調整範囲（`act3_h3_dev_tuning_range.md`）は 3 構成までに絞ってある。

| 構成 | 内容 | dev5 での測定 |
| --- | --- | --- |
| A | H3a、open turns N=2（序盤2ターン Queen へ） | 既定 |
| B | H3c、danger 閾値 0.5（次ターン受けるダメージが最大HPの5割超で Queen へ） | 既定 |
| C | H3c、danger 閾値 0.3（同じ Queen 切りを脅威が3割超に緩めた時点で発火） | 追加候補 |

A と B は既に流す既定なので、追加で測るのはグリッド上の残点 C だけ。B（0.5）はほぼ致死のときしか Queen を
狙わない。C（0.3）は脅威が中程度でも Queen に切り始める、という一段攻撃的な設定で、Queen を早く狙うと
Queen削り割合が伸びるか、その分 総火力/ターン と勝敗が落ちないかをみる。H3c は同じエージェントで、閾値だけ
環境変数 `QUEENFIRST_H3_DANGER_FRAC` を 0.3 に変える（エージェントのコード変更なし・leader が env を差し替える）。

## いつ・どの条件で試すか

- いつ: dev5_swap の base・H3a・H3c（0.5）が走り終わった時点で、同じ dev5_swap plan に 3 本目の run dir
  （H3c 0.3）を足して流す。評価は 1 コマンドの `bosslab/tools/dev5_report.py` を `--cand H3c03=<run dir>` で
  追加し、A/B と並べて読む（firing_C、Queen削りの配対差、火力/ターン、ゲート）。
- 誰と比べるか: base に対して H3c03 単独の Δ。H3a・H3c0.5・H3c0.3 を dev 間で比べるが、multiple comparison（同時に
  多くを比べることによる見かけの改善）は dev5 側に閉じ込め、確認用には dev5 で選ばれた 1 arm だけを進める。
- confirm5 へ進める条件: 4693f2e の選定で `firing_C ≥ 4` かつ `Δshave>0・Δfp≥0・Δwin≥0` を dev5 で満たす arm が
  あれば、その 1 arm だけ confirm5_swap へ進める。満たす arm が無ければ hybrid は保留のまま、C は confirm へ
  進めない（発火しない arm の Δshave は機構を検定しないため）。
- C を採用候補に上げる条件: B（0.5）が dev5 でゲートを通過したとき、閾値を一段緩めた C が同じ Queen 削りを
  より多くの戦闘で得るか（Δshave が B 以上、Δfp/Δwin を落とさない）を確かめる。B がそもそもゲートを
  通らないなら C も上げず、まず H3a（N=2）側の結果で機構の有無を見る。

## dev5 用の評価手順（leader 向け）

dev5 の run dir 3〜4 本（base / H3a / H3c0.5 / 追加で H3c0.3）が揃ったら:

```bash
python3 bosslab/tools/dev5_report.py \
  --base data/bosslab_act3_dev5_swap_base \
  --cand H3a=data/bosslab_act3_dev5_swap_H3a \
  --cand H3c05=data/bosslab_act3_dev5_swap_H3c \
  --cand H3c03=data/bosslab_act3_dev5_swap_H3c03 \
  --out bosslab/results/act3_dev5_tuning_report.md
```

各 arm について (a) 全ターン発火と発火ターン、(b) Queen削りの配対差と符号検定 p、(c) 総火力/ターン と生存ターン、
(d) 4693f2e のゲート（Δshave>0・Δfp≥0・Δwin≥0 と前提 G）が出る。run dir が途中で止まっていても、欠けた arm は
「実行データ無し」として扱い、落ちない。

## dev5 実測後の見直し（2026-10-29、H3a 結果）

H3a（N=2）が走った。発火 11/12、Queen 削り 候補優5/base優5/同値2（Δshave = 0）、総火力/ターン 42.6→37.6、
勝ち 2→1。戦闘別のターン照合は `bosslab/results/act3_dev5_h3a_analysis.md`。

- H3a の敗因は「Queen を早く狙いすぎ、Amalgam を倒し切る前に手を引いた」こと。base が強いのは Amalgam を
  殴り切って倒してから Queen へ移る点で、base は Amalgam を倒した戦闘でその攻撃を止めて体力を保っている。
- 配対 12 組で、cand（H3a）が Amalgam を倒せたのは 1 組だけ（両者が勝った 4c69c357dcda）。base は 8 組で倒した。
  base の勝ち 2 組は、base が Amalgam を倒してから Queen を削った組。H3a が削ったのに倒せなかった 11 組で、
  残った Amalgam が毎ターン 22〜63 を刻み cand の体力を削った（詳細は上の doc）。
- N=1 の是非: 妥当でない。N=1 は Amalgam をより早く放置するので、上の敗因を強める方向。実測で N=2 でも
  cand の Amalgam 撃破は 1/12 なので、N=1 では 0 に近づく。H3a 形を残すなら N を上げる（N=3、Amalgam を
  長く殴る）側のほうがマシ。
- 妥当な方向は Amalgam 撃破の可否で Queen へ切る側（H3c 系）。追加候補 C（H3c danger 閾値 0.3）も、実質
  「Queen へ早く切る」側なので今回の実測と逆方向。C の見直し:
  - B（H3c 0.5）が dev5 で Amalgam を倒せる見込みのあるターン以降に Queen へ移り、`Δshave > 0` を満たして
    Δfp/Δwin を落とすなら、その arm を confirm5_swap へ進める。
  - B が Amalgam を倒す前に Queen へ切って Δwin を落とすなら、閾値を緩める（0.3、C）ではなく逆に厳しくする
    （Queen へ切る条件を「Amalgam を倒せる/倒した」に寄せる）方向で試す。C（0.3）は上げない。
  - いずれも dev5 側の測定で、H3c の実測（走行中）を待ってから決める。次の測定は `dev5_report.py` で H3c を
    base と並べて (a)〜(d) を読む（run dir 名は dev5_swap ではなく dev5）。
