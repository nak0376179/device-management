# Implementation Plan

## Task 1: 永続化基盤

- [x] 1.1 `backend/app/db.py` — DynamoDB クライアントヘルパー
  - `LOCALSTACK_ENDPOINT` 環境変数が設定されている場合のみ `endpoint_url` を渡す
  - `@lru_cache` でクライアントをシングルトン化
  - `groups_table()` / `device_groups_table()` / `commands_table()` の 3 ヘルパーを提供
  - _Requirements: 6_
  - _Boundary: db.py_

- [x] 1.2 `backend/pyproject.toml` に依存追加
  - `pyjwt`, `passlib[bcrypt]` を追加。`uv sync` で lock 更新
  - _Requirements: 2_

## Task 2: 認証基盤

- [x] 2.1 `backend/app/auth.py` — JWT 発行・検証
  - `create_token(group_id) -> str`: HS256 署名、`JWT_SECRET` env、`JWT_TTL_HOURS` (デフォルト 8) で有効期限
  - `class JWTBearer(HTTPBearer)`: `__call__` で token 検証し `group_id` を返す
  - `Depends(JWTBearer())` として各 Router に注入できること
  - _Requirements: 2_
  - _Boundary: auth.py_
  - _Depends: 1.2_

- [x] 2.2 `backend/app/routers/auth.py` — ログインエンドポイント
  - `POST /api/auth/login {group_id, group_pw}` → DynamoDB Groups を参照 → bcrypt 検証 → `{token}` 返却
  - 認証失敗は HTTP 401
  - _Requirements: 2.1, 2.2_
  - _Boundary: routers/auth.py_
  - _Depends: 1.1, 2.1_

## Task 3: Admin / テナント管理

- [x] 3.1 `backend/app/models.py` — 全 Pydantic モデル定義
  - `GroupCreate`, `DeviceRegister`, `CommandRequest`, `CommandResult`, `CommandItem`
  - _Requirements: 1, 4, 5_
  - _Boundary: models.py_

- [x] 3.2 `backend/app/routers/admin.py` — グループ・装置 CRUD
  - `POST /api/admin/groups {group_id, group_pw}` → bcrypt hash → DynamoDB Groups PutItem (重複エラーは 409)
  - `POST /api/admin/groups/{group_id}/devices {thing_name}` → `api_key` (UUID v4) 自動生成 → DynamoDB DeviceGroups PutItem
  - _Requirements: 1.1–1.5_
  - _Boundary: routers/admin.py_
  - _Depends: 1.1, 3.1_

## Task 4: 既存装置ルートのテナントフィルタ

- [x] 4.1 `backend/app/routers/devices.py` — 既存ルートを移動しテナントフィルタ追加
  - `GET /api/devices` は JWT `group_id` → DeviceGroups GSI クエリ → その thing_name だけ返す
  - `GET /api/devices/{name}/shadow` / `PATCH` / `POST enable|disable` / `PUT description` は `group_id` での所属確認を追加 (非所属は 403)
  - Shadow に `connected` フィールドを付与: 装置が `reported.connected` を更新する方式なので shadow から読む
  - _Requirements: 3.1–3.3_
  - _Boundary: routers/devices.py_
  - _Depends: 1.1, 2.1_

## Task 5: コマンド実行バックエンド

- [x] 5.1 `backend/app/routers/commands.py` — ユーザー向けコマンド API
  - `POST /api/devices/{name}/commands` → 所属確認 → Commands PutItem (status: pending) → `iot_client.mqtt_publish()` → 201 `{command_id}`
  - `GET /api/commands/{command_id}` → GetItem → `group_id` 一致確認 → CommandItem 返却
  - `GET /api/devices/{name}/commands` → thing_name-created-index クエリ → 最新 20 件
  - _Requirements: 4.1–4.6_
  - _Boundary: routers/commands.py_
  - _Depends: 1.1, 2.1, 3.1, 6.1_

- [x] 5.2 `backend/app/routers/device_agent.py` — 装置向けコマンド API
  - 認証: `X-Device-Api-Key` ヘッダ → DeviceGroups の `api_key` と照合 → thing_name 取得
  - `GET /api/device/commands/{command_id}` → GetItem → `thing_name` 一致確認 → `{command, timeout_sec}` 返却 + status を `running` に更新
  - `POST /api/device/commands/{command_id}/result` → 409 if status != running → UpdateItem (status: completed|failed, stdout/stderr/exit_code/duration_ms)
  - _Requirements: 5.2–5.4_
  - _Boundary: routers/device_agent.py_
  - _Depends: 1.1, 3.1_

## Task 6: IoT 関連

- [x] 6.1 `backend/app/iot_client.py` — MQTT publish 追加
  - `mqtt_publish(topic: str, payload: dict)` を追加: `iot-data` boto3 の `publish()` でラップ
  - IoT Data エンドポイントは実 AWS のまま (`endpoint_url` を Floci に向けない)
  - _Requirements: 4.2_
  - _Boundary: iot_client.py_

- [x] 6.2 `device/setup_aws_iot.sh` — IoT Policy に `cmd/notify` トピック追加
  - `iot:Subscribe` / `iot:Receive` に `topic/cmd/notify/${THING_NAME}` を追加
  - 既存 Policy は `create-policy-version` で更新。既存 Thing がある場合は再実行で上書き
  - _Requirements: 5.1_

## Task 7: `main.py` Router 統合

- [x] 7.1 `backend/app/main.py` に全 Router を登録
  - `routers/auth`, `routers/devices`, `routers/commands`, `routers/device_agent`, `routers/admin` を `include_router`
  - 既存のインラインルート (`/api/devices*`) を削除し `routers/devices` に委譲
  - `/healthz` は認証不要のままにする
  - _Requirements: 2–5_
  - _Boundary: main.py_
  - _Depends: 2.2, 3.2, 4.1, 5.1, 5.2_

## Task 8: 装置側コマンドエージェント

- [x] 8.1 `device/command_runner.py` — subprocess 実行
  - `run_command(command, timeout_sec) -> dict`: stdout / stderr / exit_code / duration_ms を返す
  - タイムアウト時は exit_code=-1, stderr にメッセージ
  - _Requirements: 5.3_
  - _Boundary: command_runner.py_

- [x] 8.2 `device/virtual_device.py` — コマンド通知購読追加
  - `_subscribe_shadow()` 内で `cmd/notify/{thing_name}` を追加購読
  - コールバック `_on_command_notify`: `command_id` を受け取り threading で `command_runner.fetch_and_execute()` を呼ぶ
  - `threading.Lock` で同時実行 1 件に制限
  - 接続時に `reported.connected = true` を Shadow に publish、LWT で `false` を設定
  - _Requirements: 5.1, 5.2, 3.3_
  - _Boundary: virtual_device.py_
  - _Depends: 8.1_

- [x] 8.3 `device/config.json` スキーマ拡張
  - `backend_url` (例: `http://localhost:9001`) と `api_key` フィールドを追加
  - `setup_aws_iot.sh` 実行後に手動または seed スクリプトで更新する手順を README に記載
  - _Requirements: 5.5_

## Task 9: フロントエンド

- [x] 9.1 `frontend/src/types.ts` 拡張
  - `Command`, `CommandStatus` 型追加
  - _Requirements: 4_

- [x] 9.2 `frontend/src/api.ts` 拡張 (P)
  - `login(group_id, group_pw)` → JWT を `localStorage` に保存
  - `http()` ヘルパーに `Authorization: Bearer <token>` ヘッダを自動付与
  - `submitCommand(thingName, command)`, `getCommand(commandId)`, `listCommands(thingName)` を追加
  - _Requirements: 2.5, 4.5_
  - _Depends: 9.1_

- [x] 9.3 `frontend/src/components/LoginForm.tsx` (P)
  - group_id / group_pw フォーム → `api.login()` → 成功で親コンポーネントに通知
  - エラー時はメッセージ表示
  - _Requirements: 2.5_

- [x] 9.4 `frontend/src/App.tsx` — 認証状態管理
  - JWT が `localStorage` になければ `LoginForm` を表示
  - JWT 有効期限切れ (401 レスポンス) でログイン画面に戻す
  - _Requirements: 2.5, 3_
  - _Depends: 9.2, 9.3_

- [x] 9.5 `frontend/src/components/CommandPanel.tsx` + `CommandResult.tsx`
  - `CommandPanel`: コマンド入力 → `submitCommand()` → `CommandResult` に command_id を渡す
  - `CommandResult`: 3 秒ポーリング → status が completed/failed になったら停止し stdout/stderr/exit_code を表示
  - _Requirements: 4.5_
  - _Depends: 9.2_

## Task 10: Floci ローカル環境

- [x] 10.1 `scripts/setup-floci.sh` — DynamoDB テーブル作成
  - `Groups`, `DeviceGroups` (GSI: group_id-index), `Commands` (GSI: thing_name-created-index, TTL: ttl 属性) を aws cli で作成
  - `LOCALSTACK_ENDPOINT` が未設定の場合はエラー終了
  - _Requirements: 6.1, 6.2_

- [x] 10.2 `scripts/seed-local.sh` — テストデータ投入
  - `dev-group` / bcrypt(`devpass`) を Groups に PutItem
  - `virtual-device-01` を DeviceGroups に PutItem (api_key 自動生成)
  - `device/config.json` の `api_key` と `backend_url` を更新
  - _Requirements: 6.4_
  - _Depends: 10.1_

- [x] 10.3 `Makefile` — ローカル環境ターゲット追加
  - `dev-local`: Floci (docker compose) 起動 → `setup-floci.sh` → `seed-local.sh` → `make dev`
  - `seed-local`: `seed-local.sh` 単体実行
  - `stop-local`: `docker compose down` で Floci 停止
  - `docker-compose.yml` を追加 (Floci サービス定義)
  - _Requirements: 6.1, 6.3, 6.5_
  - _Depends: 10.2_
