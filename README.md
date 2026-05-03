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

## ローカル開発の注意点

### ポート

| 用途 | ポート | 競合しがちな相手 |
| --- | --- | --- |
| Vite (frontend) | 5173 | — |
| FastAPI (backend) | **9001** | 8000 は他プロジェクトの Docker と衝突しがち、8021 は macOS の launchd が予約 (FreeSWITCH ESL 等) |

ポートが既に使われていると次のような症状になります：

- `HTTP 404: {"detail":"Not Found"}` — 別の FastAPI/HTTP サーバが先に LISTEN している (中身が違う)
- `[Errno 48] address already in use` — uvicorn 起動失敗
- `Connection reset by peer` — launchd 予約ポートに接続したが対応サービスが起動していない

調査コマンド:

```bash
lsof -iTCP:9001 -sTCP:LISTEN -n -P    # IPv4/IPv6 両方の LISTEN を表示
netstat -anv -p tcp | grep 9001        # launchd 予約は lsof に出ないことがあるので併用
docker ps --format 'table {{.Names}}\t{{.Ports}}' | grep 9001
```

ポートを変える場合は **3 箇所**を揃える必要があります:

- `Makefile` の `dev` / `dev-backend` ターゲット (`--port`)
- `frontend/vite.config.ts` の proxy `target` のデフォルト
- (任意) `backend/README.md` のサンプル curl

### Ctrl+C で確実にプロセスを終わらせる

`make dev` は `concurrently` で 3 プロセスを束ねていますが、各コマンドは内部的に `sh -c "..."` 経由で起動されます。素朴に書くと sh が SIGTERM を子に伝播せず、Ctrl+C 後に `virtual_device.py` 等が**孤児**として残ります。同じ `client_id` で再接続すると AWS IoT が duplicate を検出して接続を切るため、`AWS_ERROR_MQTT_UNEXPECTED_HANGUP` の再接続ループが発生します。

対策として Makefile の各コマンドは `cd <dir> && exec <cmd>` の形で書き、sh をプロセス置換しています。これにより concurrently → uv/npm → 子プロセスの親子関係が直結し、SIGTERM が確実に届きます。

それでも前回の取り残しが残っていた場合の確認・後始末:

```bash
ps aux | grep -E 'virtual_device|uvicorn|vite' | grep -v grep
pkill -f virtual_device.py        # 必要なら -9 で強制
```

`AWS_ERROR_MQTT_UNEXPECTED_HANGUP` がトグル操作と無関係に断続的に出るときは、まず `virtual_device.py` が二重起動していないか確認してください。

## デプロイ

```bash
make backend-build    # uv export → sam build (ZIP)
make backend-deploy   # 上記 + sam deploy (初回は backend/ で sam deploy --guided)
```

詳細は `backend/README.md` 参照。
