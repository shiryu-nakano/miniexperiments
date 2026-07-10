# atcoder-daily-problem

AtCoder Problems の公開API（kenkoooo氏提供）を使い、指定したレベル（問題番号）のうち
自分がまだAC(正解)していない問題を毎日1問ランダムに選んで通知するためのスクリプトです。

## 構成

```
config.json                     # ユーザーIDと検索対象レベルの設定ファイル
data/ac_cache.json              # AC済み問題IDのキャッシュ（自動更新されるので基本触らなくてOK）
scripts/pick_problem.py         # 未AC問題を1問選んで標準出力に出すメインスクリプト
.github/workflows/daily.yml     # 毎日自動実行するGitHub Actionsワークフロー
```

## 設定方法

### 1. config.json を編集

```json
{
  "atcoder_user_id": "your_atcoder_id",
  "levels": ["A"],
  "exclude_contest_prefixes": []
}
```

- `atcoder_user_id`: AtCoder Problems 上のユーザーID（AtCoderのログインIDと同じ）
- `levels`: 検索対象にしたい問題番号のリスト。`["A"]` なら各コンテストのA問題のみ、
  `["A", "B"]` のように複数指定も可能
- `exclude_contest_prefixes`: 除外したいコンテストIDの接頭辞（例: `["APG4b"]` で
  演習用コンテストを除外、など）。不要なら空配列のままでOK

ユーザーIDをリポジトリに直接書きたくない場合は、`config.json` の `atcoder_user_id` は
空のままにしておき、GitHub Actions の Secrets に `ATCODER_USER_ID` を登録してください
（`daily.yml` 側で自動的に上書きされます）。

### 2. GitHub Secrets の設定（リポジトリの Settings > Secrets and variables > Actions）

- `DISCORD_WEBHOOK_URL`: 通知先のDiscord Webhook URL
- `ATCODER_USER_ID`: （任意）config.json に書きたくない場合のみ設定

### 3. Discord通知部分の差し替え

`.github/workflows/daily.yml` の `Notify to Discord` ステップは、Webhookに直接投げる
最小実装のサンプルです。すでにお持ちの「文字列をDiscordに通知する仕組み」がある場合は、
このステップを丸ごとそちらの呼び出しに差し替えてください。
前段の `Pick an unsolved problem` ステップの出力 `steps.pick.outputs.message` に
通知したい文字列が入っています。

## 動作の仕組み

1. `https://kenkoooo.com/atcoder/resources/problems.json` から全問題一覧を取得
2. `https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions` から提出履歴を取得し、
   `result == "AC"` の問題IDを集計（`data/ac_cache.json` に取得済み範囲をキャッシュし、
   2回目以降は差分だけ取得することでAPI負荷を抑えています）
3. `levels` に一致し、かつAC済みでない問題からランダムに1問選んで出力

## ローカルでのテスト実行

```bash
cd atcoder-daily-problem
python3 scripts/pick_problem.py
```

標準出力に通知メッセージが表示されます。

## 注意事項

- AtCoder Problems は非公式に提供されているAPIです。連続アクセス時は1秒以上間隔をあける
  よう配慮しています（スクリプト内で対応済み）
- cron のスケジュールはデフォルトで JST 7:00（UTC 22:00）に設定しています。
  変更したい場合は `.github/workflows/daily.yml` の `cron` の値を編集してください
