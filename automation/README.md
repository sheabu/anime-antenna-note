# automation — 朝のルーティン & SNS 運用 自動化スイート

`anime-antenna/` の既存スクリプトをラップし、朝のブリーフィングとまとめサイト／X 運用を
自動化する。launchd で毎朝バックグラウンド実行する。

## ディレクトリ構成

```
automation/
├── config.py           共通設定・パス解決・.env 読み込み
├── daily_briefing.py    朝: Notion タスク整理 + 競合巡回要約 + Discord 通知
├── auto_pilot.py        note 抽出→マージ→git push→X 文生成→Make/Discord 連携
├── lib/
│   ├── notion.py        Notion API（タスク DB 取得・期日仕分け）
│   ├── discord.py       Discord Webhook 通知（2000字分割対応）
│   ├── competitors.py   競合サイト巡回（見出し抽出）
│   └── summarize.py     OpenAI 要約（キー無しは抜粋フォールバック）
├── competitors.json     巡回対象サイト設定（要編集）
├── run.sh               launchd / 手動実行の共通ランナー
├── install_launchd.sh   launchd ジョブの登録 / 解除 / 状態確認
├── com.abesho.anime-automation.daily-briefing.plist
├── com.abesho.anime-automation.auto-pilot.plist
├── .env                 実シークレット（git 管理外・要編集）
├── .env.example         .env のテンプレート
└── .venv/               専用 Python 環境（git 管理外）
```

## ラップしている既存スクリプト

| 既存スクリプト | auto_pilot での役割 |
|---|---|
| `scripts/fetch_note_articles_500.py` | note から最新記事を抽出 → `results.json` |
| `scripts/merge_results_to_notes.py`  | `results.json` を `notes_data.json` へマージ |
| `detail_scraper.py`                  | サムネイル等の詳細を補完 |
| `generate_x_ranking.py`              | X ハッシュタグランキング更新 |
| `scripts/send_x_draft_notification.py` | X 投稿テキスト生成（関数を import 再利用） |

既存スクリプトは改変していない。auto_pilot は subprocess 実行と関数 import で連携する。

## セットアップ

### 1. シークレットの設定（必須）

`automation/.env` を編集して以下を埋める（`.env.example` 参照）。
**現状この3つが未設定なので動作には設定が必要。**

- `NOTION_TOKEN` … https://www.notion.so/my-integrations で発行
- `NOTION_DATABASE_ID` … タスク管理 DB の URL に含まれる 32 桁の ID
- `DISCORD_WEBHOOK_URL` … 通知先チャンネルの Webhook URL

任意:
- `MAKE_WEBHOOK_URL` … 設定すると X 投稿文を Make.com 経由で連携（未設定なら Discord 直送）
- `OPENAI_API_KEY` … 競合更新の要約に使用。`anime-antenna-tools/.env` の値を自動利用するため通常は空でよい

> Notion 側で、対象データベースを作成したインテグレーションに「コネクト」共有しておくこと。

### 2. 競合巡回サイトの設定

`competitors.json` の `sites` を実際の巡回対象に書き換える。
`selector` は省略可（省略時は h1〜h3 / 記事リンクから見出しを推定）。

### 3. 動作確認（送信せず確認）

```bash
cd automation
./.venv/bin/python daily_briefing.py --dry-run
./.venv/bin/python auto_pilot.py --dry-run      # push・外部送信なし
```

### 4. launchd へ登録（毎朝自動実行）

```bash
cd automation
./install_launchd.sh install     # daily-briefing 7:00 / auto-pilot 8:30
./install_launchd.sh status      # 状態確認
./install_launchd.sh uninstall   # 解除
```

スリープ中に実行時刻を過ぎた場合、launchd は次回のマシン起動時にジョブを実行する
（＝「PC 起動時実行」も実質カバー）。実行ログは `logs/` に日付別で出力される。

## 注意・前提

- **git push**: `auto_pilot.py` は `notes_data.json` 等に変更があると
  `git add → commit → pull --rebase → push origin main` を自動実行する
  （cron 設定で「push まで完全自動」を選択）。
  非対話 push のため、macOS キーチェーンに GitHub の認証情報
  （PAT 等）がキャッシュされている必要がある。一度手動で push して認証を通しておくこと。
  テスト中は `.env` の `AUTO_PILOT_NO_PUSH=true` で push を止められる。
- 実 X 投稿（tweepy）は本スイートでは行わない。要件どおり「投稿テキスト生成 + 連携」のみ。
- `.env` / `.venv/` / `logs/` は `.gitignore` 済み。シークレットは push されない。
