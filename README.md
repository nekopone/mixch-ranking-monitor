# MixChannel 勢い監視

[ライブランキングZのMixChannel勢い順](https://live-ranking.com/v/mixch)を24時間・5分おきに確認します。主サイトを取得できない、またはランキングとして正常に解析できない場合は、同系列の[MixChannelリアルタイムランキング](https://ikioi-ranking.com/v/mixch)へ自動で切り替えます。

日本時間の07:00〜21:59は、勢い度が設定値を超えた配信をその都度Discordへ通知します。22:00〜翌06:59は即時通知せず、勢い度が設定値以上になった配信者をユーザーID単位で蓄積します。07時台の最初の監視で公開アーカイブの有無を確認し、1件でも全体公開アーカイブがある配信者だけを一括通知します。

## 通知する内容

- 配信者名
- 配信タイトル
- 勢い度（ページ上の `points`）
- 配信開始からの経過時間
- MixChannelの配信URL

通知上部の配信者名はMixChannelのプロフィールへ、`MixChannelで開く`は現在のライブへ移動します。

夜間分の一括通知は配信者名だけを表示し、名前を押すとMixChannelプロフィールへ移動します。勢い度、配信URL、アーカイブURLは表示しません。同じ配信者を夜間に何度検知しても1人分へまとめます。

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

## 通知しない配信者をユーザーIDで登録する

GitHubの設定画面から、ブロックリストをいつでも変更できます。配信者名は変えられてしまうので使わず、MixChannelのユーザーIDで判定します。

`https://mixch.tv/u/14082684/live` のユーザーID `14082684` は、初期ブロックリストへ登録済みです。以下の設定は、さらに別のIDを追加するときに使います。

1. `Settings` → `Secrets and variables` → `Actions`
2. `Variables` タブ
3. `New repository variable`
4. 名前を `BLOCKED_USER_IDS` にする
5. 値へ通知しないユーザーIDをカンマ区切りで入れる

たとえば配信URLが `https://mixch.tv/u/14082684/live` なら、ユーザーIDは `14082684` です。値には数字だけでなく、この配信URLをそのまま入れても認識します。複数指定はカンマ・空白・改行で区切れます。

```text
14082684, 18844927
https://mixch.tv/u/18856007/live
```

ブロックしたユーザーIDは、勢い度や通知履歴の判定より前に除外されます。設定値に数字でもMixChannel URLでもない文字が混ざっている場合は、黙って無視せず設定エラーとして知らせます。

| 変数名 | 初期値 | 意味 |
| --- | ---: | --- |
| `MOMENTUM_THRESHOLD` | 150 | 昼間はこの値を**超えた**配信を通知。夜間はこの値**以上**を蓄積 |
| `COOLDOWN_HOURS` | 12 | 同じ配信者を再通知しない時間 |
| `ERROR_NOTIFY_COOLDOWN_HOURS` | 6 | 監視エラー通知の最短間隔 |
| `HEARTBEAT_DAYS` | 7 | 定期実行の自動停止を防ぐ生存記録の間隔 |
| `BLOCKED_USER_IDS` | 空欄 | 初期登録の`14082684`へ追加するユーザーIDまたは配信URLの一覧 |
| `FALLBACK_MONITOR_URL` | `https://ikioi-ranking.com/v/mixch` | 主サイトが使えない場合の代替サイト |
| `RELAY_ENABLED` | 未設定 | `false` にすると5分リレーを停止。それ以外は有効 |

## 動作の要点

- GitHubの新規cronが発火しない場合にも止まらないよう、`five-minute-delay` Environmentの5分待機後に本番監視と次回リレーを起動します。
- 日本時間の22:00〜翌06:59もランキング監視を続けますが、Discordへ逐次通知しません。夜間候補は `monitor-state` ブランチへ保存します。
- 07時台の最初の監視でMixChannelの公式アーカイブ取得先を確認し、`全体公開` のアーカイブが1件でもある夜間候補だけを一括通知します。確認に失敗した場合は候補を捨てず、次回の監視で再試行します。
- Environmentの待機時間はGitHub Actionsの請求時間に含まれません。公開リポジトリの標準ランナー利用も無料です。
- リレーの起動や通信状況により、実際の間隔は5分より数十秒ほど長くなる場合があります。
- 通知履歴は `monitor-state` ブランチの `state.json` に保存します。Webhook URLは保存しません。
- 状態ファイルが壊れた場合、未通知扱いにして大量再送せず、処理を失敗させてDiscordへ監視エラーを通知します。
- 通知がない期間も動作確認できるよう、7日に一度だけ状態を更新します。
- まず主サイトへ直接アクセスし、取得失敗・短すぎる応答・解析不能のいずれかなら同系列の代替サイトを直接確認します。両方とも失敗した場合だけ、[Jina Reader](https://jina.ai/reader/)へキャッシュ無効・HTML形式を指定して各サイトを最大2回ずつ再試行します。
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
