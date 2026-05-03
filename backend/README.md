# Device Management API

FastAPI ベースのバックエンド。ローカル開発は `uvicorn`、AWS デプロイは SAM (Mangum + Lambda ZIP パッケージ)。AWS IoT Core の Device Shadow を REST で操作します。

## エンドポイント

| Method | Path | 説明 |
| ------ | ---- | ---- |
| GET    | `/healthz` | ヘルスチェック |
| GET    | `/devices` | Thing 一覧 |
| GET    | `/devices/{thing}/shadow` | Shadow 取得 |
| PATCH  | `/devices/{thing}/shadow` | `desired` をマージ更新 |
| POST   | `/devices/{thing}/interfaces/{iface}/enable` | インターフェース有効化 |
| POST   | `/devices/{thing}/interfaces/{iface}/disable` | インターフェース無効化 |
| PUT    | `/devices/{thing}/interfaces/{iface}/description` | description 変更 |

PATCH の例:

```bash
curl -X PATCH http://localhost:9001/devices/virtual-device-01/shadow \
  -H 'Content-Type: application/json' \
  -d '{"desired":{"interfaces":{"eth1":{"enabled":false}}}}'
```

## ローカル開発

前提: [uv](https://docs.astral.sh/uv/) (Python 3.10+)、AWS 認証情報 (`aws configure`)。同 AWS アカウントの IoT Core を直接叩きます。

```bash
cd backend
uv sync

# uvicorn 起動 (app/ 配下を import path に)
uv run uvicorn --app-dir app main:app --reload --port 9001

# 別ターミナル
curl http://localhost:9001/healthz
curl http://localhost:9001/devices
curl http://localhost:9001/devices/virtual-device-01/shadow
```

OpenAPI: http://localhost:9001/docs

## デプロイ (SAM, ZIP パッケージ)

前提: `sam` CLI、Docker (sam build に使用)、AWS 認証情報。

`app/requirements.txt` は `pyproject.toml` の lock から自動生成 (`uv export`) して扱います。ルートの Makefile からまとめて呼べます。

```bash
# 一発: requirements 再生成 → sam build → sam deploy
make backend-deploy

# 個別実行する場合
make backend-export             # uv export で app/requirements.txt を更新
cd backend && sam build --use-container
cd backend && sam deploy --guided   # 初回のみ (stack-name: device-mgmt 等を設定)
cd backend && sam deploy             # 2 回目以降
```

完了後、`Outputs.ApiUrl` がエンドポイントになります。

```bash
API=$(aws cloudformation describe-stacks --stack-name device-mgmt \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)
curl "${API}healthz"
```

## 後片付け

```bash
sam delete --stack-name device-mgmt
```

## 構成メモ

- `app/main.py` の `handler = Mangum(app, lifespan="off")` が Lambda エントリ。
- 依存は `pyproject.toml` で一元管理。dev 専用 (`uvicorn` 等) は `[dependency-groups].dev` に。`app/requirements.txt` は SAM 用の自動生成ファイル (`make backend-export`)。
- IAM は `iot:GetThingShadow` / `iot:UpdateThingShadow` を `thing/*` に、`iot:ListThings` / `iot:DescribeThing` を `*` に許可（List 系は ARN レベル制御不可）。
- HTTP API は CORS を全開放 (デモ前提)。本番では `AllowOrigins` を絞る。
