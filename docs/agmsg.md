# agmsg の使い方 (sts2-ai)

このプロジェクトでは leader / coder / researcher / reviewer の4エージェント体制で開発している。
agmsg はエージェント間のメッセージング基盤。スクリプトは `~/.agents/skills/agmsg/scripts/` にある。

## このプロジェクトの構成(2026-08-23時点)

- team: `sts2-ai`
- `leader` (claude-code) — 司令塔。自分ではコードを書かず、調査・優先順位付け・タスク分解・
  他エージェントへの指示・結果統合を行う。
- `coder` (codex) — 実装・regression test追加・headless実機run担当。
- `researcher` (codex) — trace/results/logsの分析、敗因のFACT/HYPOTHESIS分離担当。
- `reviewer` (codex) — coderの差分・既存コードの独立レビュー。coderの自己申告(「テストpassしました」等)
  を鵜呑みにしない。
- 配信モード: `monitor`に設定されているが、**codexのmonitorブリッジは別途シェル関数のセットアップが
  必要で、このプロジェクトでは有効化されていない**(下記「codexピアへのメッセージ配信」参照)。
- 全員が同一の git worktree を共有している(別プロセスだが同じチェックアウト)。他人が編集中の
  ファイルに気づいたら、まず「誰の差分か」を確認してから触ること。

## 基本コマンド

```bash
# 自分の役割を確認(agent名・所属team)
~/.agents/skills/agmsg/scripts/whoami.sh "$(pwd)" claude-code

# チームメンバー一覧
~/.agents/skills/agmsg/scripts/team.sh sts2-ai

# 未読メッセージを確認
~/.agents/skills/agmsg/scripts/inbox.sh sts2-ai leader

# メッセージ送信 (team, from, to, message)
~/.agents/skills/agmsg/scripts/send.sh sts2-ai leader coder "メッセージ本文"

# 配信モードの確認/変更 (claude-code側。codexの配信モードは別、後述)
~/.agents/skills/agmsg/scripts/delivery.sh status claude-code "$(pwd)"
~/.agents/skills/agmsg/scripts/delivery.sh set monitor claude-code "$(pwd)"

# 履歴を確認
~/.agents/skills/agmsg/scripts/history.sh sts2-ai leader
```

新規参加(このプロジェクトに未登録の agent として join する場合)は `join.sh <team> <agent_name>
claude-code "$(pwd)"` を使う。既に登録済みなら `whoami.sh` で自分の名前が出るので join は不要。

## エージェントのspawn(claude-codeから)

leaderがcoder/researcher/reviewerを起動するには `spawn.sh`。tmux配下でなければ新規Terminal.appウィンドウが
開く。

```bash
~/.agents/skills/agmsg/scripts/spawn.sh codex coder \
  --project "$(pwd)" --team sts2-ai \
  --boot-prompt "<役割定義+最初のタスクを1メッセージにまとめて>" \
  --no-wait   # codexにはMonitorが無いのでspawnの待機は無意味、常に付ける
```

- `--boot-prompt` には役割定義とタスクを **1メッセージにまとめて** 渡す。codexは起動直後の1ターンで
  それを一気にこなすので、後から`send.sh`で細切れに情報を追加しても届かない(下記参照)。
- 生存確認は `ps aux | grep "codex resume"` で見る。エージェント名は表示されないので、
  `ps -o pid,tty,command -p <pid>` のcommand先頭にある `codex resume <session-id> ... actas <name>` の
  `<name>` で判別する。

## codexピアへのメッセージ配信(実運用の注意、2026-08-23に判明)

**codexにはclaude-codeのようなリアルタイムMonitorが無い。** `delivery.sh status codex "$(pwd)"` は
`mode: monitor` と出るが、これはcodex起動方法自体を変える別機構(app-serverブリッジ)であり、シェル
プロファイルに専用関数を追加していないと動かない。このプロジェクトでは未セットアップで、spawn直後の
codexエージェントは全員 `Codex bridge: sts2-ai/<name> not running` になる。

**結果として**: coder/researcher/reviewerが起動直後の1ターンを終えて待機状態(Terminalでcodexの入力
プロンプトが表示された状態)になった後、leaderが `send.sh` で新しいタスクを送っても、そのcodexセッション
はinboxを能動的に再チェックしない限り気づかない。inboxにメッセージは正しく溜まるので `inbox.sh` で
後から確認はできるが、**自動では届かない**。

**やってはいけないこと**: 待機中のcodexセッションに新タスクを届けようとして `spawn.sh codex <name>
--boot-prompt "..."` を**再度**呼ぶ(resumeのつもり)。元のセッションがまだ生きていて同じsession IDの
"active writer" を握っているため、新しいTerminalウィンドウ側は起動直後に

```
Error: Failed to resume session ...: thread <id> already has an active writer (code -32600)
```

で即死する。空のTerminalウィンドウが増えるだけで何も届かない。`spawn.sh`のresumeは、対象セッションが
**本当に終了している**場合にのみ有効。

**正しいやり方(生きているcodexセッションに新タスクを届ける)**:

1. まず `send.sh sts2-ai leader <name> "<タスク本文>"` でinboxに積む(記録として残る、これ自体は届かない)。
2. 対象codexプロセスのtty→Terminal window idを突き合わせる:
   ```bash
   ps -o pid,tty,command -p <pid>              # 例: ttys004
   osascript -e 'tell application "Terminal" to get {id, tty} of every window'
   ```
3. AppleScriptでそのwindowへ直接キー入力を送り、inboxを見るよう促す(短い指示で良い、タスク本文自体は
   inboxにあるので再送しなくてよい):
   ```bash
   osascript <<APPLESCRIPT
   set t to do shell script "cat /path/to/short_nudge.txt"
   tell application "Terminal" to do script t in window id <window-id>
   APPLESCRIPT
   ```
   nudge文の例: 「leaderからinboxに新タスクが届いています。`~/.agents/skills/agmsg/scripts/inbox.sh
   sts2-ai <name>` を実行して確認し、実行してください。以降もタスク完了後は毎回同じコマンドで
   inboxを再確認してください(monitorブリッジ未設定のため自動通知が来ません)。」

   **注意**: `do script ... in window` はcodexのTUI入力欄に文字を流し込むだけで、実際のEnter押下として
   認識されないことがある(codex側が忙しくなくアイドル状態だと特に起きやすい)。文字が入力欄に残ったまま
   送信されていない=CPU時間が全く伸びない、という状態になる。念のため直後に明示的なReturnキー押下を
   System Events で送ること:
   ```bash
   osascript <<APPLESCRIPT
   tell application "Terminal"
       activate
       set index of window id <window-id> to 1
   end tell
   delay 0.3
   tell application "System Events" to tell process "Terminal" to keystroke return
   APPLESCRIPT
   ```
   対象windowが既にbusy(処理中)なら不要(そこへ余分なReturnを送ると新しい空ターンを積んでしまう恐れが
   あるので、busyな窓には打たない)。
4. 成功したかは `ps -o pid,time -p <pid>` のCPU時間が伸びているかで確認する(数秒待って再実行、伸びて
   いなければStep3のReturn押下からやり直す)。

**再spawnして良いのは**、対象プロセスが実際に終了している(`ps`にPIDが出ない)場合のみ。その場合は
`--boot-prompt`に次のタスクを直接書いて通常どおりspawnすればresumeで前回の文脈ごと戻ってくる。

## 実運用上の注意

- **長文・複雑なメッセージ**は、まずスクラッチファイルに heredoc で書き出してから
  `send.sh ... "$(cat file)"` の形で送る。バッククォートや括弧がシェルに壊されるのを防ぐため。
- **agmsg で送っただけの内容は「記録」にならない**。次回セッションの自分にも他エージェントにも
  会話の外には残らない。調査結果や「次回の課題」は必ず `docs/CODEWIKI.md` に書いてコミットすること。
- ルーチンな進捗報告(通常戦のポーション使用が正当だった、等)には長文で返さず、簡潔に。
  敗北・エラー・節目(Act到達など)のときだけ詳しく反応する。
- 相手が「テストOK」「build成功」と報告しても、自分でも `python3 -m unittest discover -p 'test_*.py'`
  や `dotnet build` を独立に走らせて確認してから承認・commit すること。
