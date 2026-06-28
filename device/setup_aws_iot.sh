#!/usr/bin/env bash
# Provision an AWS IoT Thing, certificate, and policy for the virtual device.
# Requires: aws cli (configured), jq, curl.
set -euo pipefail

THING_NAME="${1:-dev-group:deadbeef0101}"  # format: group_id:mac_address
REGION="${AWS_REGION:-ap-northeast-1}"
# Policy names and MQTT client IDs must not contain ':'; replace with '-'
SAFE_NAME="${THING_NAME//:/-}"
POLICY_NAME="${SAFE_NAME}-policy"
CLIENT_ID="${SAFE_NAME}"
CERT_DIR="./certs"
TABLE_DEVICES="${TABLE_DEVICES:-Devices}"

# Derive group_id and dev_id from thing_name (format: group_id:dev_id)
GROUP_ID="${THING_NAME%%:*}"
DEV_ID="${THING_NAME#*:}"

mkdir -p "$CERT_DIR"

echo "Region:      $REGION"
echo "Thing name:  $THING_NAME"
echo "Client ID:   $CLIENT_ID"
echo "Policy name: $POLICY_NAME"

ENDPOINT=$(aws iot describe-endpoint \
  --endpoint-type iot:Data-ATS \
  --region "$REGION" \
  --query endpointAddress --output text)
echo "Endpoint:    $ENDPOINT"

if aws iot describe-thing --thing-name "$THING_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "Thing already exists: $THING_NAME"
else
  aws iot create-thing --thing-name "$THING_NAME" --region "$REGION" >/dev/null
  echo "Created thing."
fi

if [[ -f "$CERT_DIR/device.cert.pem" && -f "$CERT_DIR/device.private.key" ]]; then
  echo "Existing certificate found at $CERT_DIR — skipping certificate creation."
  CERT_ARN="$(cat "$CERT_DIR/cert.arn" 2>/dev/null || true)"
  if [[ -z "$CERT_ARN" ]]; then
    echo "ERROR: $CERT_DIR/cert.arn missing. Delete $CERT_DIR and re-run to regenerate."
    exit 1
  fi
else
  CERT_OUTPUT=$(aws iot create-keys-and-certificate --set-as-active --region "$REGION")
  CERT_ARN=$(echo "$CERT_OUTPUT" | jq -r .certificateArn)
  echo "$CERT_OUTPUT" | jq -r .certificatePem > "$CERT_DIR/device.cert.pem"
  echo "$CERT_OUTPUT" | jq -r .keyPair.PrivateKey > "$CERT_DIR/device.private.key"
  echo "$CERT_ARN" > "$CERT_DIR/cert.arn"
  chmod 600 "$CERT_DIR/device.private.key"
  echo "Created certificate: $CERT_ARN"
fi

if [[ ! -f "$CERT_DIR/AmazonRootCA1.pem" ]]; then
  curl -fsSL https://www.amazontrust.com/repository/AmazonRootCA1.pem \
    -o "$CERT_DIR/AmazonRootCA1.pem"
  echo "Downloaded Amazon Root CA."
fi

POLICY_DOC=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["iot:Connect"],
      "Resource": "arn:aws:iot:${REGION}:*:client/${CLIENT_ID}"
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Publish", "iot:Receive"],
      "Resource": "arn:aws:iot:${REGION}:*:topic/\$aws/things/${THING_NAME}/shadow/*"
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Subscribe"],
      "Resource": "arn:aws:iot:${REGION}:*:topicfilter/\$aws/things/${THING_NAME}/shadow/*"
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Subscribe"],
      "Resource": "arn:aws:iot:${REGION}:*:topicfilter/cmd/notify/${THING_NAME}"
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Receive"],
      "Resource": "arn:aws:iot:${REGION}:*:topic/cmd/notify/${THING_NAME}"
    }
  ]
}
EOF
)

if aws iot get-policy --policy-name "$POLICY_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "Updating policy: $POLICY_NAME"
  # Delete non-default versions to stay under the 5-version limit.
  aws iot list-policy-versions --policy-name "$POLICY_NAME" --region "$REGION" \
    --query "policyVersions[?isDefaultVersion==\`false\`].versionId" --output text \
    | tr '\t' '\n' | while read -r vid; do
        [[ -z "$vid" ]] && continue
        aws iot delete-policy-version \
          --policy-name "$POLICY_NAME" --policy-version-id "$vid" \
          --region "$REGION" >/dev/null
      done
  aws iot create-policy-version \
    --policy-name "$POLICY_NAME" \
    --policy-document "$POLICY_DOC" \
    --set-as-default \
    --region "$REGION" >/dev/null
  echo "Policy updated."
else
  aws iot create-policy \
    --policy-name "$POLICY_NAME" \
    --policy-document "$POLICY_DOC" \
    --region "$REGION" >/dev/null
  echo "Created policy: $POLICY_NAME"
fi

aws iot attach-policy \
  --policy-name "$POLICY_NAME" \
  --target "$CERT_ARN" \
  --region "$REGION"

aws iot attach-thing-principal \
  --thing-name "$THING_NAME" \
  --principal "$CERT_ARN" \
  --region "$REGION"

# Register device in DynamoDB and get (or create) api_key.
EXISTING=$(aws dynamodb get-item \
  --table-name "$TABLE_DEVICES" \
  --key "{\"group_id\":{\"S\":\"${GROUP_ID}\"},\"dev_id\":{\"S\":\"${DEV_ID}\"}}" \
  --region "$REGION" \
  --query "Item.api_key.S" --output text 2>/dev/null || true)

if [[ -n "$EXISTING" && "$EXISTING" != "None" ]]; then
  API_KEY="$EXISTING"
  echo "Device already registered: api_key=$API_KEY"
else
  API_KEY=$(python3 -c "import uuid; print(uuid.uuid4())")
  NOW=$(python3 -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())")
  aws dynamodb put-item \
    --table-name "$TABLE_DEVICES" \
    --region "$REGION" \
    --item "{
      \"group_id\":  {\"S\":\"${GROUP_ID}\"},
      \"dev_id\":    {\"S\":\"${DEV_ID}\"},
      \"thing_name\":{\"S\":\"${THING_NAME}\"},
      \"api_key\":   {\"S\":\"${API_KEY}\"},
      \"created_at\":{\"S\":\"${NOW}\"}
    }" >/dev/null
  echo "Registered device in DynamoDB: api_key=$API_KEY"
fi

cat > config.json <<EOF
{
  "endpoint": "${ENDPOINT}",
  "client_id": "${CLIENT_ID}",
  "thing_name": "${THING_NAME}",
  "cert_path": "./certs/device.cert.pem",
  "key_path": "./certs/device.private.key",
  "ca_path": "./certs/AmazonRootCA1.pem",
  "backend_url": "http://localhost:9001",
  "api_key": "${API_KEY}"
}
EOF

echo
echo "Setup complete. config.json written."
echo "  group_id=$GROUP_ID  dev_id=$DEV_ID  api_key=$API_KEY"
