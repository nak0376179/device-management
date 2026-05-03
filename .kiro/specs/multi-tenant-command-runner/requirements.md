# Requirements Document

## Introduction

現状の device-management デモは単一テナント前提・Shadow ベースの制御のみ。本仕様では以下の 3 点を追加する:
- **マルチテナント**: グループ ID / PW でテナントを識別し、グループの装置だけを操作できる
- **任意コマンド実行**: フロントから装置に任意コマンドを投入し、大きなレスポンス (数 MB 想定) を取得できる
- **MQTT の役割限定**: 装置の常時接続維持とコマンド着信通知のみ MQTT を使い、データ転送は装置側からも HTTPS REST で行う

ローカル検証はすべて Floci (LocalStack 互換 OSS エミュレータ) 上で動かせること。

## Boundary Context

- **In scope**: グループ CRUD、グループ認証 (JWT)、装置とグループの紐付け、コマンド投入・結果取得 API、装置側コマンド実行エージェント、Floci によるローカル開発環境
- **Out of scope**: グループ間の装置移動 UI、コマンド結果の長期アーカイブ、fine-grained RBAC (グループ内ロール)、既存の Shadow ベース制御 (interface enable/disable) の廃止
- **Adjacent expectations**: 既存の Shadow 制御フロー (Requirement 1–3 以前の動作) はそのまま残す。新機能はその上に追加レイヤとして乗る。

## Requirements

### Requirement 1: グループ管理

**Objective:** As a システム管理者, I want グループ (テナント) を作成して装置を割り当てる手段が欲しい, so that テナントごとに装置を分離して管理できる

#### Acceptance Criteria

1. グループは `group_id` (一意の文字列) と `group_pw` を持ち、`group_pw` はハッシュ化して DynamoDB に保存されること
2. 管理 API `POST /api/admin/groups` でグループを作成できること (重複 group_id はエラー)
3. 管理 API `POST /api/admin/groups/{group_id}/devices` で装置 (thing_name) をグループに紐付けられること
4. 装置は必ず 1 つのグループに所属し、グループなし装置には認証済みテナントからアクセスできないこと
5. ローカル環境では `make seed-local` コマンドで初期グループ・装置データを Floci 上に投入できること

### Requirement 2: テナント認証

**Objective:** As a テナントユーザー, I want group_id と group_pw でログインしてトークンを取得したい, so that 自テナントの装置だけを安全に操作できる

#### Acceptance Criteria

1. `POST /api/auth/login { group_id, group_pw }` でハッシュ検証し、成功時に署名付き JWT (payload: `group_id`, `exp`) を返すこと
2. 無効な認証情報の場合、HTTP 401 を返すこと
3. 以降のすべての `/api/devices/*` および `/api/commands/*` エンドポイントは `Authorization: Bearer <token>` を必須とし、トークン不正・期限切れは HTTP 401 を返すこと
4. JWT の有効期限はデフォルト 8 時間とし、環境変数 `JWT_TTL_HOURS` で上書きできること
5. フロントエンドはログイン画面を持ち、取得した JWT を以降のリクエストに自動付与すること

### Requirement 3: テナント別装置一覧

**Objective:** As a テナントユーザー, I want 自分のグループに属する装置だけを一覧・操作したい, so that 他テナントの装置が見えない

#### Acceptance Criteria

1. `GET /api/devices` は JWT の `group_id` でフィルタし、そのグループに所属する Thing のみ返すこと
2. 他グループの装置 thing_name を直接指定した API 呼び出しは HTTP 403 を返すこと
3. 装置の一覧には「オンライン / オフライン」状態を含むこと (MQTT の接続イベント・LWT を DynamoDB に反映)

### Requirement 4: コマンド実行 — フロントエンド/バックエンド側

**Objective:** As a テナントユーザー, I want 装置に任意のシェルコマンドを投入し、結果を UI で確認したい, so that 装置の状態把握や操作を柔軟に行える

#### Acceptance Criteria

1. `POST /api/devices/{thing_name}/commands { "command": "<shell>" }` でコマンドを登録できること
   - バックエンドは `command_id` (UUID) を生成し、DynamoDB に `{ command_id, group_id, thing_name, command, status: "pending", created_at }` で保存する
   - 登録成功時は HTTP 201 `{ command_id }` を返す
2. 登録後、バックエンドは対象装置の MQTT トピック (`cmd/notify/{thing_name}`) に `{ "command_id": "<uuid>" }` を publish して装置に通知すること
3. `GET /api/commands/{command_id}` でステータスと結果を取得できること (pending / dispatched / running / completed / failed)
4. コマンド結果のサイズは最大 10 MB まで格納できること
5. コマンドの結果が揃うまでフロントエンドが自動ポーリング (3 秒間隔) し、完了後に stdout / stderr / exit_code を表示すること
6. 自テナントのコマンド以外は `GET /api/commands/{command_id}` でも HTTP 403 を返すこと

### Requirement 5: コマンド実行 — 装置側エージェント

**Objective:** As a 仮想装置, I want クラウドからのコマンド通知を受けて REST 経由でコマンドを取得・実行し、結果をアップロードしたい, so that MQTT のサイズ制限に縛られず大きな実行結果を返せる

#### Acceptance Criteria

1. 装置は `cmd/notify/{thing_name}` を MQTT で購読し、`command_id` を受け取ること
2. 通知受信後、装置は `GET <BACKEND_URL>/api/device/commands/{command_id}` (HTTPS REST) でコマンド本体を取得すること
3. 装置はコマンドを `subprocess` で実行し、stdout / stderr / exit_code を収集すること
4. 実行完了後、`POST <BACKEND_URL>/api/device/commands/{command_id}/result { stdout, stderr, exit_code, duration_ms }` で結果をアップロードすること
5. 装置から装置向け REST への認証は、`DEVICE_API_KEY` 環境変数または config.json の `api_key` フィールドで行うこと (ヘッダ: `X-Device-Api-Key`)
6. コマンド実行は装置プロセスのサンドボックス内で行い、実行タイムアウトは `COMMAND_TIMEOUT_SEC` (デフォルト 30 秒) で制御すること

### Requirement 6: Floci ローカル開発環境

**Objective:** As a 開発者, I want AWS 本番環境なしでフル機能をローカル検証したい, so that 開発サイクルを高速化できる

#### Acceptance Criteria

1. `make dev-local` で Floci (Docker コンテナ, `http://localhost:4566`) を起動し、必要な AWS リソース (DynamoDB テーブル等) を自動作成してから全プロセスを起動すること
2. `LOCALSTACK_ENDPOINT=http://localhost:4566` 環境変数が設定された場合、boto3 クライアントがすべてその endpoint_url を使うこと
3. 装置側の MQTT は実 AWS IoT Core を使うこと (Floci は IoT Core MQTT を擬似できないため)。DynamoDB 等の REST/DB 系リソースのみ Floci で代替する
4. `make seed-local` でテスト用グループ (`dev-group` / pw: `devpass`) と装置 (`virtual-device-01`) の紐付けデータを投入できること
5. Floci の停止・データ破棄は `make stop-local` で行えること
