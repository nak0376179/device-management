#!/usr/bin/env bash
# Provision an AWS IoT Thing, certificate, and policy for the virtual device.
# Requires: aws cli (configured), jq, curl.
set -euo pipefail

THING_NAME="${1:-virtual-device-01}"
REGION="${AWS_REGION:-ap-northeast-1}"
POLICY_NAME="${THING_NAME}-policy"
CERT_DIR="./certs"

mkdir -p "$CERT_DIR"

echo "Region:      $REGION"
echo "Thing name:  $THING_NAME"
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
      "Resource": "arn:aws:iot:${REGION}:*:client/${THING_NAME}"
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
    }
  ]
}
EOF
)

if aws iot get-policy --policy-name "$POLICY_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "Policy already exists: $POLICY_NAME"
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

cat > config.json <<EOF
{
  "endpoint": "${ENDPOINT}",
  "client_id": "${THING_NAME}",
  "thing_name": "${THING_NAME}",
  "cert_path": "./certs/device.cert.pem",
  "key_path": "./certs/device.private.key",
  "ca_path": "./certs/AmazonRootCA1.pem"
}
EOF

echo
echo "Setup complete. config.json written."
echo "Next: pip install -r requirements.txt && python virtual_device.py"
