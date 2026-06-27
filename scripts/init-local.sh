#!/usr/bin/env bash
# Initialize local dev environment: register group/device in Floci and update device/config.json.
# Group: dev-group / devpass, Device: deadbeef0101
# Skips automatically if config.json already has api_key.
set -euo pipefail

ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
BACKEND_URL="${BACKEND_URL:-http://localhost:9001}"
CONFIG="$(dirname "$0")/../device/config.json"
AWS="aws --endpoint-url $ENDPOINT --region ap-northeast-1"

# Skip if already initialized
if [[ -f "$CONFIG" ]]; then
  EXISTING_KEY=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('api_key',''))" 2>/dev/null || true)
  if [[ -n "$EXISTING_KEY" ]]; then
    echo "init-local: already initialized, skipping."
    exit 0
  fi
fi

echo "Initializing local device via $ENDPOINT ..."

# Create group + device via admin API (handles bcrypt hashing server-side)
# Retry until backend is ready (may still be starting)
for i in $(seq 1 20); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/healthz" 2>/dev/null || echo "000")
  [[ "$STATUS" == "200" ]] && break
  echo "  Waiting for backend ($i/20) ..."
  sleep 2
done

curl -sf -X POST "$BACKEND_URL/api/admin/groups" \
  -H "Content-Type: application/json" \
  -d '{"group_id":"dev-group","group_pw":"devpass"}' \
  && echo "Created group: dev-group" \
  || echo "Group already exists (ok)"

DEVICE_RESP=$(curl -s -X POST "$BACKEND_URL/api/admin/groups/dev-group/devices" \
  -H "Content-Type: application/json" \
  -d '{"dev_id":"deadbeef0101"}' 2>/dev/null || echo "{}")
echo "Registered device: $DEVICE_RESP"

API_KEY=$(echo "$DEVICE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_key'])" 2>/dev/null || true)
THING_NAME=$(echo "$DEVICE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['thing_name'])" 2>/dev/null || true)

# Update device config.json if api_key was returned
if [[ -f "$CONFIG" && -n "$API_KEY" ]]; then
  python3 - "$CONFIG" "$API_KEY" "$THING_NAME" "$BACKEND_URL" <<'PY'
import sys, json
path, api_key, thing_name, backend_url = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
cfg = json.loads(open(path).read())
cfg["api_key"] = api_key
cfg["thing_name"] = thing_name
cfg["client_id"] = thing_name.replace(":", "-")  # ':' is invalid in MQTT client ARNs
cfg["backend_url"] = backend_url
open(path, "w").write(json.dumps(cfg, indent=2) + "\n")
print(f"Updated {path}: thing_name={thing_name} client_id={cfg['client_id']} api_key={api_key}")
PY
fi

echo "Init complete."
echo "  Login:  group_id=dev-group  group_pw=devpass"
echo "  Device: dev_id=deadbeef0101  thing_name=dev-group:deadbeef0101"
