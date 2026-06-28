# device-management

AWS IoT Core を使ったネットワーク機器リモート制御のデモ。ローカル開発では **DynamoDB も IoT Core も Floci でエミュレート**し、実 AWS なしで完結します（本番は実 AWS にデプロイ）。

```
┌─────────────┐  MQTT      ┌──────────────┐  HTTPS  ┌──────────┐  HTTP  ┌──────────┐
│  Virtual    │ ─────────▶ │  IoT Core    │ ◀─────  │ FastAPI  │ ◀───── │  React   │
│  Device     │ ◀───────── │  (Shadow)    │ ─────▶  │ (boto3)  │ ─────▶ │  (Vite)  │
│  (Python)   │   Shadow   │ 実AWS / Floci│         │ uvicorn  │  REST  │  :5173   │
└─────────────┘   delta    └──────────────┘         │  :9001   │        └──────────┘
                                                    └──────────┘
                                                       │ sam build && sam deploy
                                                       ▼
                                               Lambda(ZIP) + HTTP API
```

> **ローカルの IoT 配線について**: Floci 1.5.28 は IoT Core を含みますが、REST 面と
> MQTT 面が分離しており、実 IoT Core が持つ REST↔MQTT ブリッジがありません。そのため
> ローカルモード（`AWS_ENDPOINT_URL` 設定時）に限り、backend はコマンド通知を Floci の
> MQTT ブローカ(:1883)へ直接 publish し、デバイス状態は Floci の生 REST Shadow から読みます。
> 本番（実 AWS）の経路は従来どおり boto3 / mTLS のまま変更ありません。

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

DynamoDB も IoT Core も Floci でエミュレートします。**実 AWS アカウント・認証情報は不要**です。

```bash
# 前提ツールのインストール確認: uv, Node.js 20+, AWS CLI, Docker
#   （AWS CLI は Floci 操作にのみ使用。実 AWS 認証は不要）

# 1. 依存インストール
make install

# 2. Floci(DynamoDB + IoT) 起動 → 自動プロビジョニング → 全プロセス起動
#    グループ/デバイス/IoT Thing/config.json は dev-local が冪等に自動生成します
make dev-local
```

ブラウザで http://localhost:5173 を開く。ログイン: `group_id=dev-group` / `group_pw=devpass`

### AWS 環境（実 DynamoDB + 実 IoT Core）

```bash
make install
make setup-aws      # 実 AWS IoT の Thing/証明書/Policy を作成（AWS 認証情報 + jq, curl が必要）
make dev            # 全プロセスを同時起動（実 AWS へ接続）
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
| Floci (DynamoDB + IoT REST) | 4566 |
| Floci IoT MQTT ブローカ | 1883 |
