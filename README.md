# device-management

AWS IoT Core を使ったネットワーク機器リモート制御のデモ。AWS IoT 以外（仮想デバイス・API・UI）はローカル PC で完結します。

```
┌─────────────┐  MQTT/TLS  ┌──────────────┐  HTTPS  ┌──────────┐  HTTP  ┌──────────┐
│  Virtual    │ ─────────▶ │ AWS IoT Core │ ◀─────  │ FastAPI  │ ◀───── │  React   │
│  Device     │ ◀───────── │ (Shadow)     │ ─────▶  │ (boto3)  │ ─────▶ │  (Vite)  │
│  (Python)   │   Shadow   │              │         │ uvicorn  │  REST  │  :5173   │
└─────────────┘   delta    └──────────────┘         │  :9001   │        └──────────┘
                                                    └──────────┘
                                                       │ sam build && sam deploy
                                                       ▼
                                               Lambda(ZIP) + HTTP API
```

## ディレクトリ

| パス | 概要 |
|------|------|
| `device/` | 仮想ネットワーク機器 (Python, AWS IoT Device SDK v2) |
| `backend/` | FastAPI (ローカル) / Mangum + Lambda + SAM (デプロイ) |
| `frontend/` | React + Vite + TypeScript ダッシュボード |
| `scripts/` | ローカル開発補助スクリプト |
| `docs/` | 開発ガイド・利用ガイド |

## ドキュメント

- [開発ガイド](docs/dev-guide.md) — セットアップ・アーキテクチャ・API リファレンス
- [利用ガイド](docs/user-guide.md) — UI の使い方

## クイックスタート

### ローカル開発（推奨）

AWS IoT は本物を使いつつ、DynamoDB は Floci（LocalStack 互換）でローカルエミュレーションします。

```bash
# 前提ツールのインストール確認: uv, Node.js 18+, AWS CLI (設定済み), jq, curl, Docker

# 1. 依存インストール
make install

# 2. AWS IoT Thing/証明書を作成（初回のみ）
make setup-aws

# 3. ローカル DynamoDB + 全プロセスを起動
#    初回は自動でデバイス初期化(init-local)が実行されます
make dev-local
```

ブラウザで http://localhost:5173 を開く。ログイン: `group_id=dev-group` / `group_pw=devpass`

### AWS 環境（実 DynamoDB）

```bash
make install
make setup-aws
make dev            # 全プロセスを同時起動
```

## よく使うコマンド

```bash
make dev-local      # Floci + 全プロセス起動（ローカル開発）
make dev            # 全プロセス起動（AWS DynamoDB 使用）
make init-local     # ローカルデバイス初期化（手動再実行用）
make stop-local     # Floci を停止してデータを破棄
make dev-device     # 仮想デバイスのみ起動
make dev-backend    # FastAPI のみ起動
make dev-frontend   # Vite のみ起動
make help           # 全ターゲット一覧
make clean          # venv / node_modules / ビルド成果物を削除
```

## デプロイ

```bash
make backend-build    # uv export → sam build (ZIP)
make backend-deploy   # 上記 + sam deploy
```

詳細は [開発ガイド](docs/dev-guide.md) の「デプロイ」セクションを参照。

## ポート

| 用途 | ポート |
|------|--------|
| React (Vite) | 5173 |
| FastAPI (uvicorn) | 9001 |
| Floci (DynamoDB) | 4566 |
