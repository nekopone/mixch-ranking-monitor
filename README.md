# MixChannel 勢い監視

[ライブランキングZのMixChannel勢い順](https://live-ranking.com/v/mixch)を5分おきに確認し、勢い度が設定値を超えた配信をDiscordへ通知します。

## 通知する内容

- 配信者名
- 配信タイトル
- 勢い度（ページ上の `points`）
- 順位
- 配信開始からの経過時間
- MixChannelの配信URL

初期設定では勢い度が **150を超えた配信（151以上）** が対象です。同じ配信者は名前を変えてもMixChannelユーザーIDで識別し、通知後12時間は再通知しません。

## 最初に必要な設定

### 1. Discord Webhookを登録

既存の監視システムと同じWebhook URLを、次の場所へ登録します。

1. GitHubでこのリポジトリを開く
2. `Settings`
3. `Secrets and variables`
4. `Actions`
5. `New repository secret`
6. 名前を `DISCORD_WEBHOOK_URL` にする
7. 値へDiscord Webhook URLを貼り、保存する

Webhook URLはパスワード同然です。README、プログラム、Actions変数には貼らず、必ず **Secret** に入れてください。

### 2. テスト通知

1. リポジトリ上部の `Actions`
2. 左側の `MixChannel勢い監視`
3. `Run workflow`
4. `Discordへテスト通知を1件送る` をオン
5. `Run workflow`

初期状態では `dry_run` もオンなので、実在する配信の通知履歴は変更しません。

## 勢い度の基準を変える

プログラムを編集せず、GitHubの画面で変更できます。

1. `Settings` → `Secrets and variables` → `Actions`
2. `Variables` タブ
3. `New repository variable`
4. 名前を `MOMENTUM_THRESHOLD`、値を好きな数値にする

たとえば値が `200` なら、201以上で通知します。未設定なら150です。

| 変数名 | 初期値 | 意味 |
| --- | ---: | --- |
| `MOMENTUM_THRESHOLD` | 150 | この値を**超えた**配信を通知 |
| `COOLDOWN_HOURS` | 12 | 同じ配信者を再通知しない時間 |
| `ERROR_NOTIFY_COOLDOWN_HOURS` | 6 | 監視エラー通知の最短間隔 |
| `HEARTBEAT_DAYS` | 7 | 定期実行の自動停止を防ぐ生存記録の間隔 |

## 動作の要点

- GitHub Actionsを毎時3分、8分、13分……58分に動かします。毎時0分付近の混雑を避けつつ、間隔は5分です。
- GitHub側の混雑時には開始が遅れたり、ごくまれに実行自体が落とされたりすることがあります。5分ぴったりを保証する仕組みではありません。
- 通知履歴は `monitor-state` ブランチの `state.json` に保存します。Webhook URLは保存しません。
- 状態ファイルが壊れた場合、未通知扱いにして大量再送せず、処理を失敗させてDiscordへ監視エラーを通知します。
- 公開リポジトリの定期実行が60日無活動で止まらないよう、7日に一度だけ状態を更新します。
- 元サイトがGitHubの実行機へ空の本文を返した場合だけ、[Jina Reader](https://jina.ai/reader/)へキャッシュ無効・HTML形式を指定して公開ページを取得します。通常は元サイトへ直接アクセスします。
- 外部Pythonパッケージは使いません。毎回のインストール時間と通信量を減らしています。

## 手動で通知候補だけ確認する

`Actions` → `MixChannel勢い監視` → `Run workflow` を開きます。

- `dry_run` はオンのまま
- `この手動実行だけ使う勢い度` に、たとえば `20` を入力

実行ログに候補が表示されますが、Discord通知と通知履歴の更新はしません。

## ローカルでテストする

```bash
python3 -m unittest discover -s tests -v
```

実ページを通知なしで確認する場合:

```bash
DRY_RUN=true MOMENTUM_THRESHOLD=0 python3 -m src.mixch_monitor
```
