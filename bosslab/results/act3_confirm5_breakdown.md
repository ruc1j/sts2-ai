# 確認用 confirm5 の内訳と忠実性2件の切り分け（T42、2026-10-29）

解析のみ。実機・ビルド不使用。対象は leader が完走した confirm5_swap（base / H3a / H3c 各 12 組、run dir
`data/bosslab_act3_confirm5_base` / `_H3a` / `_H3c`）。判定は事前登録規則（commit 4693f2e）を
`bosslab/tools/confirm5_report.py` で機械的に 1 回適用したもの（`act3_confirm5_judgment.md`）。因果は主張せず、
内訳と数字、および候補の仮説として書く。

## 1. 忠実性 2 件の切り分け（不一致 `deck.multiset`）

confirm5 base の忠実性は 10/12 一致、不一致 2 件はすべて `deck.multiset`（`act3_confirm5_fidelity.md`）。どの
カードが違ったか（lab 観測 vs boss-spec 記録、key は `カードID+強化値+呪い`）:

| trial | spec | lab 側のカード | 記録側のカード | 違い | spec の入場レリック |
| --- | --- | --- | --- | --- | --- |
| 0000 | 0256297739fc | DEFEND_IRONCLAD +1, METAMORPHOSIS +1 | DEFEND_IRONCLAD +0, METAMORPHOSIS +0 | 強化値（記録は無強化、lab は強化） | PENDULUM 他（原因レリック不是） |
| 0003 | c247ea1ceac4 | DEMON_FORM +1 | DEMON_FORM +0 | 強化値のみ | WHETSTONE / LETTER_OPENER 他（原因レリック不是） |

- 追加・消失カードではなく、同じカードの **強化値（+0 / +1）だけ** が違う。2 件とも FORGOTTEN_SOUL /
  BLESSED_ANTLER（HP 二重発火の原因レリック）ではなく、confirm5 panel は原因レリックを含まない設計。よって
  HP 二重発火とは別系統の不一致。
- 機構の候補（trace から、デコンパイル未実行）: 入場時カード強化をするレリック（c247ea1ceac4 に LETTER_OPENER /
  WHETSTONE、0256297739fc に強化を与えるレリック）が、元 run では特定のカードを強化した状態で記録されたのに、
  BossLab 再走で入場効果の「どのカードを強化したか」が元 run と違うカードに乗り直す。HP 二重発火（入場効果を
  凍結できない）と同じ系統で、出方が「入場カード強化のずれ」になっている。入場効果を記録時点で凍結しないと
  再現できない問題として、codewiki 草案の二重発火と束ねて扱う。原因レリック起因ではないので、忠実性の残りとして
  別枠で追う（次 build で spec を採り直すときにまとめて直す方向）。

## 2. 該当 2 組を除いた感度分析（参考・規則は変えない）

上の 2 組（0256297739fc / c247ea1ceac4）が base 対 候補の向きを動かすか。同じ spec・offset の配対なので、
2 組を除いた 10 組で `apply_hybrid_rule.candidate_delta` を再計算（`confirm5_report.py` と同じ入口）。

| 候補 | 集合 | 配対 | Δshave（候補優/base優/同値） | 精密 p | Δfp（base→cand 総火力/ターン） | Δwin（base→cand） |
| --- | --- | --- | --- | --- | --- | --- |
| H3a | confirm5 全 12 | 12 | −2（5 / 7 / 0） | 0.774 | −7.5（37.9 → 30.4） | −1（1 → 0） |
| H3a | confirm5 10（2除） | 10 | 0（5 / 5 / 0） | 1.000 | −7.2（39.2 → 31.9） | −1（1 → 0） |
| H3c | confirm5 全 12 | 12 | +2（7 / 5 / 0） | 0.774 | −3.1（37.9 → 34.8） | −1（1 → 0） |
| H3c | confirm5 10（2除） | 10 | +2（6 / 4 / 0） | 0.754 | −2.8（39.2 → 36.4） | −1（1 → 0） |

- 2 組を除くと H3a の Δshave は −2 から 0 へ戻る（除いた 2 組で候補が削り負けしていた）。ただし H3a は dev5 の
  Δshave 0 と合わせ 0 以下なので 採用条件（両集合 Δshave>0）には変わらず、判定（不採用）は変わらない。
- H3c は 2 組を除いても Δshave +2 のまま。dev5 と confirm5 で向き一致（条件1 充足）だが、Δfp < 0 と Δwin < 0 が
  両集合で不変、p > 0.05。判定（保留）は変わらない。
- 結論: 忠実性 2 組の除去は 採否を反転させない。Δwin（base 1 勝 → 候補 0 勝）と Δfp（候補が下回る）は 2 組
  除去後も同じ向き。判定入口（4693f2e + 前提 G）の結果は、この 2 件の忠実性漂移に頑健。

## 3. 確認用 結果の内訳（候補ごと）

判定（`act3_confirm5_judgment.md`）: H3a **不採用**、H3c **保留**（dev5 と同じ）。内訳の数字:

- Amalgam 撃破: base 7/12、H3a 1/12、H3c 2/12。base だけ勝てた 1 組は `d48032980ad0`（base 勝利）。候補は
  その組でも Amalgam を倒せず敗北（H3a の cand Amalgam 最終 HP 96、base 削り 199 を倒し切った）。base 勝利は
  その 1 組のみで、候補の勝利は 0（Δwin −1）。
- base が Amalgam を倒せた組のうち、候補が Amalgam を残したまま敗北した組（Amalgam 残害）: H3a 6 組、H3c 5 組。
  候補が Amalgam を残して死んだときの Amalgam 最終 HP は 95〜150 が 6 組、12・41 が 2 組（H3a、0256297739fc=107,
  75157844a09c=104, c247ea1ceac4=95, d48032980ad0=96, e75781521da8=41, ca23400bbcc3=12）。大半は Amalgam が
  ほぼ満タンのまま候補が落ちている。
- dev5 と同じ向きの理由（候補の仮説、因果は主張しない）: base は Amalgam を集中攻撃で先に仕留め、その後は Amalgam の
  攻撃が止まるので体力を保って Queen へ押せる。候補（H3a/H3c は序盤〜中盤で Queen へ殴り先を変える）は Amalgam を
  生かしたまま Queen に火力を移すため、残った Amalgam の毎ターン攻撃で体力を削られ、Queen を倒し切る前に落ちる。
  dev5 の解析（`act3_dev5_h3a_analysis.md`）と同じ構造が confirm5 でも再現し、Amalgam 撃破が base 7/12 に対し候補
  1/12・2/12 へ落ち、勝ちも base 1 → 候補 0 に減った。削り割合（主信号）は H3c で +2（Queen を多く削る）だが、その
  分だけ Amalgam を残して敗北が増えており、採用には進めない。
- 忠実性 2 件（上 1）の除外でも向きは不変（上 2）。Amalgam 残害は強化漂移の 2 組に限定されず候補全体に現れる。
