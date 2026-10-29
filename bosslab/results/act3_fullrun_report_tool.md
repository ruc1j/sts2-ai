# act3_fullrun_report.py — Act 3 フルrunパネルの集計ツール（T46、2026-10-29）

## 結論

`astra_ctrl_v23`（136 run、commit 775f366・arm=control）を入力に、leader の棚卸し
（`docs/ACT3_FULLRUN_PANEL_20261029.md`）と **6 項目すべて一致**。乖離は無し。走行中の `astra_ctrl_v24` は
runmeta/manifest の揃った完走分だけを読み込んで動作確認した（第2段階は途中）。

| 指標 | leader 棚卸し | このツール | 一致 |
| --- | --- | --- | --- |
| Act 3 進入 | 45 | 45 | ○ |
| Queen と戦った | 33 | 33 | ○ |
| 踏破 | 1 | 1 | ○ |
| Queen 削り割合 中央値 | 16% | 16%（0.1625） | ○ |
| Amalgam 撃破（Queen戦のうち） | 19/33 | 19/33 | ○ |
| Queen 入場HP 中央値 | 80 | 80 | ○ |
| 死亡ターン 中央値 | 7 | 7 | ○ |
| 入場デッキ 攻撃/Skill/Power/枚数/強化/ポーション | 13/10/2/28/10/3 | 13/10/2/28/10/3 | ○ |

Wilson 95% も一致（進入 25.7〜41.4%、Queen到達 59〜84%、踏破/進入 0.4〜11.6%、踏破/全 0.1〜4.0%、
Amalgam 40.8〜72.8%）。

## 使い方

リポジトリの worktree から、trace が置いてある `data/` を指して実行する（v24 の trace は main リポジトリの
`data/` に走行中に増える。書き換えず読むだけ）。

```bash
python3 bosslab/tools/act3_fullrun_report.py \
  --data-dir /Users/mao/workspace/sts2-ai/data \
  --prefix astra_ctrl_v23 --prefix astra_ctrl_v24 \
  --out bosslab/results/act3_fullrun_report.md
```

`--prefix` を複数渡すと tag ごとに集計し、末尾に 2 tag の分布比較表（合算してよいかの確認）を出す。
`--out` 無しなら標準出力。manifest が無くても trace だけで動く（v24 は完走後に manifest が作られる）。

## 集計の中身

run ごとは trace から直接出す（manifest 不要）。`_agent.jsonl` を読んで、(a) `run.act==2` で Act 3 進入、
(b) QUEEN を含む戦闘があれば Queen 戦、(c) その戦闘を挟む `combat_end.won` で踏破、(d) 最初の Queen 観測の
手札・山札・捨て札・除外札の合計で入場デッキ（攻撃/Skill/Power/強化/ポーション、HP/最大HP）、
(e) Queen 削り割合、(f) Amalgam 撃破の有無、(g) 死亡ターンを集める。完走判定は `_runmeta.json` か
`_manifest.json` の存在（無い走行中 trace は除外）。

集計は段階別の率に Wilson 95% 区間（母集団は標本数）、Queen 削りと死亡ターンの中央値と四分位、
Skill 枚数・強化数・入場HP を中央値で 2 群に分けた層別（各群の標本数つき）。群間の差は記述のみで、
有意性や因果は主張しない。

## 設計で気をつけた点（v23 照合で確定した挙動）

- Queen 戦闘の途中に `combat` 以外の行（戦闘中のイベント・相互作用）が入ることがある。ツールは最初の
  Queen 観測から、その戦闘を閉じる `combat_end` まで走り、途中の非戦闘行を飛ばして戦闘行だけを拾う。
  これを戦闘行だけで打ち切ると、後で Amalgam を倒した組を撃破と数え損ねる（C394628E60 等 2 組）。
- Amalgam 撃破は「Queen 戦闘の最後の観測で Amalgam が不在」で判定する。Amalgam は入場時にすでに損傷して
  いることがある（150/199 など）ので、削り HP が最大に達したかで倒したかを見ると素通りする（removed が
  最大未満で終わる）。最後の行に居るかどうかで数えると leader の 19/33 と一致した。
- 入場デッキの型は、panel 内の全 run が手札に一度でも出した card id→型の表で補う（山札側の札は
  `type: null`）。この表を run ごとに狭くとると型不明が 18 枚残って攻撃 6 枚などになり leader とズレる。
- 死亡ターンは Queen 戦闘の最後の戦闘行の `turn`。踏破 run は死亡ターンなし（中央値から除外）。
- 層別は「以上」を中央値以上で切る。入場HP はこれで leader と一致（以上19/未満14）するが、Skill 枚数は
  中央値 10 ちょうどが 10 run 居るため、この区切りだと 以上24/未満9 になる（leader の 23/10 と 1 run 差、
  tie をどちらに置くかの差で、記述の数なので結論には影響しない）。

## 実際の出力（astra_ctrl_v23、136 run）

- 段階別: Act 3 進入 45/136（33%、25.7〜41.4%）、Queen 到達 33/45（73%、59〜84%）、踏破 1/45（2.2%、
  0.4〜11.6%）＝全run 1/136（0.7%、0.1〜4.0%）、Amalgam 撃破 19/33（58%、40.8〜72.8%）。
- Queen 削り割合: 中央値 16%（四分位 2〜33%、最大 84%）。死亡ターン: 中央値 7（四分位 6〜9）。
- 層別（記述のみ）: Skill 以上 24 run（削り中央 17%、Amalgam 撃破 16、死亡中央 8）/ 未満 9 run（2%、3、4）。
  強化 以上 19（16%、13、8）/ 未満 14（12%、6、6）。入場HP 以上19（16%、10、7.5）/ 未満14（16%、9、6.5）。
  Skill・強化で削りと撃破が多い向き（`act3_amalgam_kill_speed.md` と同じ向き）だが入場HP で差は小さい。
  標本が小さく、デッキの強さと到達順序と交絡している。

テストは `test_act3_fullrun_report.py`（3 件: 戦闘中の非戦闘行を跨ぐ Queen 戦闘と panel 全体の型表で入場
デッキを補う挙動、完走判定で走行中 trace を除外、Wilson 区間の値）。suite 996 OK。
