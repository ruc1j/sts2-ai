# agmsg の使い方 (sts2-ai)

このプロジェクトでは reviewer / developer の2エージェント体制で開発している。
agmsg はその2者間のメッセージング基盤。スクリプトは `~/.agents/skills/agmsg/scripts/` にある。

## このプロジェクトの構成

- team: `sts2-ai`
- `reviewer` (claude-code) — developer の差分をレビューし、独自にテスト・decompile で検証してから
  commit する係。developer の自己申告(「テストpassしました」等)を鵜呑みにしない。
- `developer` (codex) — 実装・headless 実機 run・trace 収集を担当。
- 配信モード: `monitor`(リアルタイム push)。セッション開始時に自動で監視プロセスが立ち上がる。
- reviewer と developer は同一の git worktree を共有している(別プロセスだが同じチェックアウト)。
  相手が編集中のファイルに気づいたら、まず「誰の差分か」を確認してから触ること。

## 基本コマンド

```bash
# 自分の役割を確認(agent名・所属team)
~/.agents/skills/agmsg/scripts/whoami.sh "$(pwd)" claude-code

# チームメンバー一覧
~/.agents/skills/agmsg/scripts/team.sh sts2-ai

# 未読メッセージを確認
~/.agents/skills/agmsg/scripts/inbox.sh sts2-ai reviewer

# メッセージ送信 (team, from, to, message)
~/.agents/skills/agmsg/scripts/send.sh sts2-ai reviewer developer "メッセージ本文"

# 配信モードの確認/変更
~/.agents/skills/agmsg/scripts/delivery.sh status claude-code "$(pwd)"
~/.agents/skills/agmsg/scripts/delivery.sh set monitor claude-code "$(pwd)"

# 履歴を確認
~/.agents/skills/agmsg/scripts/history.sh sts2-ai reviewer
```

新規参加(このプロジェクトに未登録の agent として join する場合)は `join.sh <team> <agent_name>
claude-code "$(pwd)"` を使う。既に登録済みなら `whoami.sh` で自分の名前が出るので join は不要。

## 実運用上の注意

- **長文・複雑なメッセージ**は、まずスクラッチファイルに heredoc で書き出してから
  `send.sh ... "$(cat file)"` の形で送る。バッククォートや括弧がシェルに壊されるのを防ぐため。
- **agmsg で送っただけの内容は「記録」にならない**。次回セッションの自分にも developer にも
  会話の外には残らない。調査結果や「次回の課題」は必ず `docs/CODEWIKI.md` に書いてコミットすること。
- ルーチンな進捗報告(通常戦のポーション使用が正当だった、等)には長文で返さず、簡潔に。
  敗北・エラー・節目(Act到達など)のときだけ詳しく反応する。
- 相手が「テストOK」「build成功」と報告しても、自分でも `python3 -m unittest discover -p 'test_*.py'`
  や `dotnet build` を独立に走らせて確認してから承認・commit すること。
