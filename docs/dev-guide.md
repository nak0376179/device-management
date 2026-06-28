# 開発ガイド

## 目次

1. [前提ツール](#前提ツール)
2. [プロジェクト構成](#プロジェクト構成)
3. [ローカル開発環境のセットアップ](#ローカル開発環境のセットアップ)
4. [アーキテクチャ詳細](#アーキテクチャ詳細)
5. [API リファレンス](#api-リファレンス)
6. [DynamoDB スキーマ](#dynamodb-スキーマ)
7. [デプロイ](#デプロイ)
8. [トラブルシューティング](#トラブルシューティング)

---

## 前提ツール

| ツール | 用途 |
|--------|------|
| [uv](https://docs.astral.sh/uv/) | Python 依存管理 (`device/`, `backend/`) |
| Node.js 18+ / npm | フロントエンド依存管理 |
| AWS CLI (設定済み) | IoT Thing 作成・SAM デプロイ |
| `jq`, `curl` | `setup-aws` スクリプト内で使用 |
| Docker | Floci（ローカル DynamoDB）起動 |
| AWS SAM CLI | デプロイ時のみ必要 |

---

## プロジェクト構成

```
device-management/
├── device/                    # 仮想デバイス
│   ├── virtual_device.py      # メインプロセス（MQTT 接続・Shadow 管理）
│   ├── command_runner.py      # コマンド取得・実行・結果返却
│   ├── config.json            # 接続設定（setup-aws で生成、init-local で更新）
│   ├── certs/                 # AWS IoT 証明書（.gitignore 推奨）
│   └── setup_aws_iot.sh       # AWS IoT Thing/Cert/Policy 作成スクリプト
├── backend/
│   └── app/
│       ├── main.py            # FastAPI エントリポイント + Mangum ハンドラ
│       ├── auth.py            # JWT 生成・検証、パスワードハッシュ
│       ├── db.py              # DynamoDB テーブルクライアント
│       ├── iot_client.py      # IoT Core / Shadow / MQTT publish ラッパー
│       └── routers/
│           ├── auth.py        # POST /api/auth/login
│           ├── admin.py       # POST /api/admin/groups, /devices（認証なし）
│           ├── devices.py     # GET/PATCH /api/devices/*（JWT 必須）
│           ├── commands.py    # POST/GET /api/devices/{}/commands（JWT 必須）
│           └── device_agent.py# GET/POST /api/device/commands/*（API キー認証）
├── frontend/src/
│   ├── App.tsx                # ログイン状態管理・デバイス一覧
│   ├── api.ts                 # バックエンド API クライアント
│   ├── types.ts               # 型定義
│   └── components/
│       ├── LoginForm.tsx      # ログインフォーム
│       ├── CommandPanel.tsx   # コマンド入力・実行
│       └── CommandResult.tsx  # コマンド結果表示（ポーリング）
├── scripts/
│   ├── setup-floci.sh         # DynamoDB テーブル作成（Floci 用）
│   └── init-local.sh          # ローカルデバイス初期化（グループ・デバイス登録）
├── docker-compose.yml         # Floci（ローカル DynamoDB エミュレータ）
└── Makefile                   # 開発コマンド集約
```

---

## ローカル開発環境のセットアップ

### 1. 依存インストール

```bash
make install
# 内部で以下を実行:
#   cd device && uv sync
#   cd backend && uv sync
#   cd frontend && npm install
#   npm install  (concurrently)
```

### 2. ローカル起動（実 AWS 不要）

```bash
make dev-local
```

DynamoDB も IoT Core も Floci でエミュレートするため、`make setup-aws` や AWS 認証情報は不要です（実 AWS にデプロイ／接続する場合のみ後述の `setup-aws` を使用）。

内部の処理順序：

1. `docker compose up -d` — Floci（DynamoDB + IoT Core）起動。`:4566`(REST) と `:1883`(MQTT) を公開
2. `scripts/setup-floci.sh` — DynamoDB テーブル作成（冪等）
3. `concurrently` で device / backend / frontend / init を並列起動。`init` = `scripts/init-local.sh`
4. backend には `AWS_ENDPOINT_URL`＋ダミー認証(`test/test`)＋region を渡す（boto3 を Floci に向ける）

`init-local.sh`（冪等・毎回実行）が行うこと：
- `POST /api/admin/groups` — グループ `dev-group` 登録
- `POST /api/admin/groups/dev-group/devices` — デバイス `deadbeef0101` 登録（→ `api_key`）
- `iot create-thing` — Floci IoT レジストリに Thing 作成（デバイス一覧は DynamoDB ∩ `iot:ListThings`）
- `device/config.json` を生成（`local:true`, `endpoint:localhost`, `mqtt_port:1883`, `thing_name`, `client_id`, `api_key`, `backend_url`）

Floci は既定で in-memory のため、`make dev-local` 起動ごとに上記が冪等に再プロビジョニングされます。デバイス（仮想機器）はプロビジョニング完了まで config を待機し、IoT MQTT ブローカ起動まで接続をリトライします。

> **デバイスの MQTT 接続（ローカル）**: Floci の IoT MQTT ブローカは平文 MQTT(:1883) なので、
> デバイスは mTLS ではなく平文 MQTT で接続します（証明書不要）。`config.json` の `local:true`
> で分岐し、実 AWS 向けの mTLS 経路はそのまま残ります。

### 3. AWS IoT 準備（実 AWS にデプロイ／接続する場合のみ）

```bash
make setup-aws      # 要: AWS 認証情報, jq, curl
```

以下が作成されます：
- AWS IoT Thing: `dev-group:deadbeef0101`
- 証明書・秘密鍵: `device/certs/`
- IoT ポリシー: `dev-group-deadbeef0101-policy`
- `device/config.json`（endpoint, cert パスを含む実 AWS 用設定）

> AWS CLI が `ap-northeast-1` で設定されている必要があります。別リージョンを使う場合は `AWS_REGION=us-east-1 make setup-aws` のように指定してください。

または `make init-local` で手動実行（バックエンドが起動済みの状態で）。

### 4. アクセス確認

| URL | 内容 |
|-----|------|
| http://localhost:5173 | React ダッシュボード |
| http://localhost:9001/docs | FastAPI Swagger UI |
| http://localhost:9001/healthz | ヘルスチェック |

---

## アーキテクチャ詳細

### マルチテナント設計

グループ（テナント）がデバイスを所有します。`thing_name` は `{group_id}:{dev_id}` の形式で、テナント間の分離はこのプレフィックスで実現されています。

```
Groups テーブル: group_id → パスワードハッシュ
DeviceGroups テーブル: (group_id, dev_id) → thing_name, api_key
Commands テーブル: command_id → thing_name, コマンド内容, 実行結果
```

### 認証フロー

```
UI → POST /api/auth/login (group_id + group_pw)
   → JWT トークン発行 (payload: group_id)
   → 以降のリクエストに Authorization: Bearer <token>
```

デバイス側は `X-Device-Api-Key` ヘッダで API キー認証を使います。JWT は使いません。

### タスク実行フロー

```
1. UI → POST /api/devices/{thing_name}/tasks
         → DynamoDB に status=pending で記録（PK=group_id#dev_id, SK=task_id）
         → AWS IoT MQTT topic cmd/notify/{thing_name} に task_id をパブリッシュ

2. デバイスが MQTT 通知を受信
         → GET /api/device/tasks/{task_id}  (status → running)
         → シェルでコマンドを実行
         → POST /api/device/tasks/{task_id}/result  (status → completed/failed)

3. UI がポーリング → GET /api/devices/{thing_name}/tasks/{task_id} → 結果を表示
```

MQTT が届かなくても DynamoDB にタスクが残るため、デバイスが再接続後に処理できます（ただし現実装では再接続時の pending 取得は未実装）。

### Device Shadow フロー

```
UI → PATCH /api/devices/{thing_name}/shadow (desired 更新)
   → boto3 が IoT Core UpdateThingShadow を呼ぶ
   → IoT Core が delta を MQTT でデバイスに送信
   → デバイスが state を更新して reported をパブリッシュ
   → UI のポーリングで確認
```

### プロセス管理（exec の重要性）

`make dev-local` の `concurrently` では各コマンドを `cd <dir> && exec <cmd>` の形で起動しています。`exec` によって shell がプロセス置換され、Ctrl+C の SIGTERM が確実に子プロセスに届きます。これを省略すると shell が孤児として残り、仮想デバイスが AWS IoT に再接続しようとしてループします。

---

## API リファレンス

Swagger UI: http://localhost:9001/docs

### 認証不要

| メソッド | パス | 概要 |
|----------|------|------|
| GET | `/healthz` | ヘルスチェック |
| POST | `/api/auth/login` | ログイン（JWT 発行） |
| POST | `/api/admin/groups` | グループ作成 |
| POST | `/api/admin/groups/{group_id}/devices` | デバイス登録 |

### JWT 認証必須（Authorization: Bearer \<token\>）

| メソッド | パス | 概要 |
|----------|------|------|
| GET | `/api/devices` | デバイス一覧（接続状態付き） |
| GET | `/api/devices/{thing_name}/shadow` | Shadow 取得 |
| PATCH | `/api/devices/{thing_name}/shadow` | Shadow desired 更新 |
| POST | `/api/devices/{thing_name}/interfaces/{iface}/enable` | インターフェース有効化 |
| POST | `/api/devices/{thing_name}/interfaces/{iface}/disable` | インターフェース無効化 |
| PUT | `/api/devices/{thing_name}/interfaces/{iface}/description` | 説明文更新 |
| POST | `/api/devices/{thing_name}/tasks` | タスク送信 |
| GET | `/api/devices/{thing_name}/tasks` | タスク履歴（最新 20 件） |
| GET | `/api/devices/{thing_name}/tasks/{task_id}` | タスク結果取得 |

### デバイス API キー認証（X-Device-Api-Key ヘッダ）

| メソッド | パス | 概要 |
|----------|------|------|
| GET | `/api/device/tasks/{task_id}` | タスク取得（status を running に更新） |
| POST | `/api/device/tasks/{task_id}/result` | 実行結果を送信 |

---

## DynamoDB スキーマ

### Groups

| 属性 | 型 | 概要 |
|------|----|------|
| `group_id` (PK) | S | テナント ID |
| `group_pw_hash` | S | bcrypt ハッシュ |
| `created_at` | S | ISO 8601 |

### Devices

| 属性 | 型 | 概要 |
|------|----|------|
| `group_id` (PK) | S | テナント ID |
| `dev_id` (SK) | S | MAC アドレス等 |
| `thing_name` | S | `group_id:dev_id` |
| `api_key` | S | UUID v4 (GSI: `api_key-index`) |
| `created_at` | S | ISO 8601 |

### Tasks

| 属性 | 型 | 概要 |
|------|----|------|
| `device_pk` (PK) | S | `group_id#dev_id` |
| `task_id` (SK) | S | ISO 8601 タイムスタンプ（created_at を兼ねる） |
| `group_id` | S | テナント ID |
| `command` | S | シェルコマンド文字列 |
| `status` | S | `pending` / `running` / `completed` / `failed` |
| `stdout`, `stderr` | S | 実行結果 |
| `exit_code` | N | 終了コード |
| `duration_ms` | N | 実行時間（ミリ秒） |
| `updated_at` | S | ISO 8601 |
| `ttl` | N | TTL（7 日後の UNIX 時刻） |

---

## デプロイ

### バックエンドのみ Lambda にデプロイ

```bash
make backend-build    # uv export → sam build --use-container
make backend-deploy   # sam deploy
```

初回は `backend/` で `sam deploy --guided` を先に実行して `samconfig.toml` を生成してください。

### 環境変数（Lambda / 本番）

| 変数 | 説明 |
|------|------|
| `TABLE_GROUPS` | Groups テーブル名（デフォルト: `Groups`） |
| `TABLE_DEVICES` | Devices テーブル名（デフォルト: `Devices`） |
| `TABLE_TASKS` | Tasks テーブル名（デフォルト: `Tasks`） |
| `AWS_ENDPOINT_URL` | 設定時は Floci ローカルモード（DynamoDB/IoT を Floci に向け、MQTT publish と Shadow 読取をローカルブリッジ経由にする）。本番は未設定 |
| `FLOCI_MQTT_HOST` | ローカルモードで backend が通知を publish する MQTT ブローカのホスト（既定: `AWS_ENDPOINT_URL` のホスト→`localhost`） |
| `FLOCI_MQTT_PORT` | 同ポート（既定: `1883`） |
| `COMMAND_TIMEOUT_SEC` | コマンドタイムアウト秒数（デフォルト: 30） |

---

## トラブルシューティング

### ポートが使用中

```bash
lsof -iTCP:9001 -sTCP:LISTEN -n -P
netstat -anv -p tcp | grep 9001
docker ps --format 'table {{.Names}}\t{{.Ports}}' | grep 9001
```

ポートを変更する場合は **3 箇所**を揃えます：
- `Makefile` の `dev` / `dev-backend` / `dev-local` の `--port`
- `frontend/vite.config.ts` の proxy `target`
- `scripts/init-local.sh` の `BACKEND_URL`

### 仮想デバイスが二重起動している

```bash
ps aux | grep -E 'virtual_device|uvicorn|vite' | grep -v grep
pkill -f virtual_device.py
```

`AWS_ERROR_MQTT_UNEXPECTED_HANGUP` が繰り返し出る場合、前回の `virtual_device.py` が残っています。

### Floci が起動していない

```bash
docker ps | grep floci
docker compose up -d
```

### init-local を再実行したい

```bash
make stop-local        # Floci のデータをリセット（docker compose down -v）
# device/config.json の api_key を "" に戻す
make dev-local         # 自動で init-local が実行される
```

または Floci を再起動せずに手動で実行する場合（デバイスが既存なら api_key が返ってくるだけ）：

```bash
make init-local
```
