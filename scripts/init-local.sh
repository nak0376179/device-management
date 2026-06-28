#!/usr/bin/env bash
# Initialize a fully-local dev environment on Floci (no real AWS needed):
#   - register group + device via the backend admin API (DynamoDB on Floci)
#   - create the matching IoT Thing in Floci's IoT registry (so it shows up in
#     the device list, which intersects DynamoDB with iot:ListThings)
#   - (re)generate device/config.json pointing the virtual device at Floci's
#     plain-MQTT IoT broker (localhost:1883, no TLS / certificates)
#
# Idempotent: safe to run on every `make dev-local`. Floci defaults to in-memory
# storage, so this re-provisions group/device/thing/config on each fresh start.
#
#   Group:  dev-group / devpass
#   Device: deadbeef0101  ->  thing_name dev-group:deadbeef0101
set -euo pipefail

ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
BACKEND_URL="${BACKEND_URL:-http://localhost:9001}"
MQTT_HOST="${FLOCI_MQTT_HOST:-localhost}"
MQTT_PORT="${FLOCI_MQTT_PORT:-1883}"
CONFIG="$(dirname "$0")/../device/config.json"

# Floci accepts any credentials; default to dummies so this works without a
# configured (or expired) real AWS profile.
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AWS_REGION="${AWS_REGION:-ap-northeast-1}"
AWS="aws --endpoint-url $ENDPOINT --region $AWS_REGION"

echo "Initializing local device via $ENDPOINT ..."

# Wait for the backend (it may still be starting under concurrently).
for i in $(seq 1 20); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/healthz" 2>/dev/null || echo "000")
  [[ "$STATUS" == "200" ]] && break
  echo "  Waiting for backend ($i/20) ..."
  sleep 2
done

# Create group + device via admin API (handles bcrypt hashing server-side).
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

if [[ -z "$API_KEY" || -z "$THING_NAME" ]]; then
  echo "ERROR: device registration did not return api_key/thing_name." >&2
  exit 1
fi

# Create the IoT Thing in Floci so list_devices (DynamoDB ∩ iot:ListThings)
# surfaces it. Also triggers Floci's IoT MQTT broker to start.
$AWS iot create-thing --thing-name "$THING_NAME" >/dev/null 2>&1 \
  && echo "Created IoT thing: $THING_NAME" \
  || echo "IoT thing exists: $THING_NAME (ok)"

# (Re)write device/config.json for plain-MQTT local mode (no certs/CA needed).
python3 - "$CONFIG" "$API_KEY" "$THING_NAME" "$BACKEND_URL" "$MQTT_HOST" "$MQTT_PORT" <<'PY'
import sys, json
path, api_key, thing_name, backend_url, mqtt_host, mqtt_port = sys.argv[1:7]
cfg = {
    "local": True,
    "endpoint": mqtt_host,
    "mqtt_port": int(mqtt_port),
    "thing_name": thing_name,
    "client_id": thing_name.replace(":", "-"),  # ':' is invalid in MQTT client ids
    "api_key": api_key,
    "backend_url": backend_url,
}
open(path, "w").write(json.dumps(cfg, indent=2) + "\n")
print(f"Wrote {path}: thing_name={thing_name} mqtt={mqtt_host}:{mqtt_port}")
PY

echo "Init complete."
echo "  Login:  group_id=dev-group  group_pw=devpass"
echo "  Device: dev_id=deadbeef0101  thing_name=$THING_NAME"
