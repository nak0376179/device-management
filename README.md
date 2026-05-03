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

- [`device/`](./device/) — 仮想ネットワーク機器 (Python, AWS IoT Device SDK v2)
- [`backend/`](./backend/) — FastAPI (ローカル) / Mangum + Lambda + SAM (デプロイ)
- [`frontend/`](./frontend/) — React + Vite + TypeScript ダッシュボード

## 前提ツール

- [uv](https://docs.astral.sh/uv/) (Python 依存管理)
- Node.js 18+ / npm
- AWS CLI (設定済み)、`jq`、`curl` (`make setup-aws` で使用)
- (デプロイ時のみ) AWS SAM CLI、Docker

## 起動

ルート Makefile から `concurrently` 経由でまとめて起動します。Python venv (`device/.venv`, `backend/.venv`)、`frontend/node_modules`、`node_modules` (concurrently)、`device/config.json` (AWS IoT 接続情報) が揃っている必要があります。

```bash
# 初回セットアップ
make install        # 3 つの依存 + ルートの concurrently をインストール
make setup-aws      # AWS IoT Thing/Cert/Policy を作成 (device/config.json を生成)

# 同時起動 (Ctrl+C で全停止)
make dev
```

ブラウザで http://localhost:5173 を開く。

### 単体起動 / その他

```bash
make dev-device     # 仮想デバイスのみ
make dev-backend    # FastAPI のみ
make dev-frontend   # Vite のみ
make help           # 全ターゲット一覧
make clean          # venv / node_modules / ビルド成果物を削除
```

## 制御フロー

UI でトグル → `PATCH /devices/{thing}/shadow` または `POST .../enable|disable`
→ FastAPI が boto3 で `iot-data:UpdateThingShadow` を呼ぶ
→ AWS IoT が delta を仮想デバイスに publish
→ デバイスが state を更新して `reported` を publish
→ UI のポーリングで反映を確認

## デプロイ

```bash
make backend-build    # uv export → sam build (ZIP)
make backend-deploy   # 上記 + sam deploy (初回は backend/ で sam deploy --guided)
```

詳細は `backend/README.md` 参照。
