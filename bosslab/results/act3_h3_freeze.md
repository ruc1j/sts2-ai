# H3a / H3c 凍結記録（confirm5 を見る前）

開発用 dev5_swap（12組）の結果を見たうえで、候補を調整せず既定値のまま凍結する。

- H3a: 序盤 N=2 ターンだけ Amalgam（既定）。dev5 では 11/12 組で発火。Queen削り 候補優5/base優5/同値2、総火力/ターン 42.6→37.6、勝ち 2→1。
- H3c: 期待ダメージが生存の 0.5 を超える間だけ Amalgam（既定）。dev5 では 12/12 組で発火。Queen削り 候補優6/base優5/同値1（p=1.0）、総火力/ターン 42.6→42.3、生存ターン 7.3→6.2、勝ち 2→1。
- 調整しない理由: 候補が Amalgam を倒し切る前に Queen へ切り替えると、残った Amalgam の攻撃で体力を失う（act3_dev5_h3a_analysis.md）。dev5 の範囲では、パラメータの変更でこの向きが変わる根拠がない。調整は 0 組合せ（上限 3 組合せの範囲内）。
- 規則: 4693f2e の規則 1〜6 に、前提G（全ターン発火 firing_C ≥ 4）を加える。前提G の追加案は先生の個別承認を得ていない。前提G は候補を落とす方向（測定不能＝保留）にだけ働き、今回は両候補とも dev5 で満たすため、結果は変わらない。
- 確認用: bosslab_act3_plan_confirm5_swap.json（12組）で base、H3a、H3c の順に流す。
- 凍結したファイルのハッシュ（sha256）:

```
2ab4832dc1c84d8e12b683a2038b649019ccd840acf26a0cdaefe88319210095  bosslab/agents/official_agent_H3a.py
cc52649ec11a0ba9a1162e9ae2973b0b7d44f1f7799dfff5db7d4d6dabc761b7  bosslab/agents/official_agent_H3c.py
61e780f81fb8a7168e2a013031b601e5f0c4169bb8b5fce902fd6b70bfeaf65c  official_agent.py
```
