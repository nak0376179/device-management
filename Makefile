.PHONY: help install install-device install-backend install-frontend install-root \
        setup-aws dev dev-device dev-backend dev-frontend \
        dev-local init-local stop-local \
        backend-docs-export backend-export backend-build backend-deploy clean

CONCURRENTLY := ./node_modules/.bin/concurrently

help: ## このヘルプを表示
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: install-device install-backend install-frontend install-root ## 全依存をインストール

install-device: ## device/ の依存を uv で同期
	cd device && uv sync

install-backend: ## backend/ の依存 (dev 含む) を uv で同期
	cd backend && uv sync

install-frontend: ## frontend/ の依存をインストール
	cd frontend && npm install

install-root: ## ルートの依存 (concurrently) をインストール
	npm install

setup-aws: ## AWS IoT の Thing/Cert/Policy を作成 (初回のみ)
	cd device && ./setup_aws_iot.sh

dev: ## device, backend, frontend を同時起動 (Ctrl+C で全停止)
	@test -x $(CONCURRENTLY) || { echo "First run: make install-root"; exit 1; }
	@test -d device/.venv || { echo "First run: make install-device"; exit 1; }
	@test -d backend/.venv || { echo "First run: make install-backend"; exit 1; }
	@test -d frontend/node_modules || { echo "First run: make install-frontend"; exit 1; }
	@test -f device/config.json || { echo "First run: make setup-aws"; exit 1; }
	$(CONCURRENTLY) \
	  --names device,backend,frontend \
	  --prefix-colors blue,green,magenta \
	  --kill-others \
	  "cd device && PYTHONUNBUFFERED=1 exec uv run python -u virtual_device.py" \
	  "cd backend && PYTHONUNBUFFERED=1 exec uv run uvicorn --app-dir app main:app --reload --port 9001 --log-config log_config.json" \
	  "cd frontend && exec npm run dev"

dev-device: ## device 単体起動
	cd device && uv run python virtual_device.py

dev-backend: ## backend 単体起動
	cd backend && uv run uvicorn --app-dir app main:app --reload --port 9001 --log-config log_config.json

dev-frontend: ## frontend 単体起動
	cd frontend && npm run dev

# Floci accepts any credentials; dummies keep local dev independent of a real
# (or expired) AWS profile. DynamoDB + IoT Core both run inside Floci.
LOCAL_ENV := AWS_ENDPOINT_URL=http://localhost:4566 AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=ap-northeast-1

dev-local: ## Floci(DynamoDB+IoT) 起動 → 自動プロビジョニング → 全プロセス起動 (実 AWS 不要)
	@test -x $(CONCURRENTLY) || { echo "First run: make install-root"; exit 1; }
	@test -d device/.venv || { echo "First run: make install-device"; exit 1; }
	@test -d backend/.venv || { echo "First run: make install-backend"; exit 1; }
	@test -d frontend/node_modules || { echo "First run: make install-frontend"; exit 1; }
	docker compose up -d
	@until $(LOCAL_ENV) aws --endpoint-url http://localhost:4566 --region ap-northeast-1 dynamodb list-tables >/dev/null 2>&1; do \
	  echo "  Waiting for Floci..."; sleep 0.5; done
	$(LOCAL_ENV) bash scripts/setup-floci.sh
	$(CONCURRENTLY) \
	  --names device,backend,frontend,init \
	  --prefix-colors blue,green,magenta,yellow \
	  --kill-others-on-fail \
	  "cd device && PYTHONUNBUFFERED=1 exec uv run python -u virtual_device.py" \
	  "cd backend && $(LOCAL_ENV) PYTHONUNBUFFERED=1 exec uv run uvicorn --app-dir app main:app --reload --port 9001 --log-config log_config.json" \
	  "cd frontend && exec npm run dev" \
	  "$(LOCAL_ENV) BACKEND_URL=http://localhost:9001 bash scripts/init-local.sh"

init-local: ## ローカル開発用グループ・デバイス・IoT Thing を初期化 (dev-local が自動実行)
	$(LOCAL_ENV) BACKEND_URL=http://localhost:9001 bash scripts/init-local.sh

stop-local: ## Floci を停止してデータを破棄
	docker compose down -v

backend-docs-export: ## OpenAPI spec を backend/openapi.json に出力 (ReDoc 等で活用)
	cd backend && uv run python -c \
	  "import json, sys; sys.path.insert(0, 'app'); from main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))" \
	  > openapi.json
	@echo "→ backend/openapi.json に出力しました"

backend-export: ## backend/app/requirements.txt を pyproject から再生成 (SAM ビルド用)
	cd backend && uv export --no-hashes --no-dev --no-emit-project --format requirements-txt -o app/requirements.txt

backend-build: backend-export ## SAM build (ZIP)
	cd backend && sam build --use-container

backend-deploy: backend-build ## SAM deploy
	cd backend && sam deploy

clean: ## venv, node_modules, ビルド成果物を削除
	rm -rf device/.venv backend/.venv
	rm -rf frontend/node_modules node_modules
	rm -rf frontend/dist backend/.aws-sam
