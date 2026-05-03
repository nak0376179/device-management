#!/usr/bin/env bash
# Create DynamoDB tables in Floci (LocalStack-compatible endpoint).
set -euo pipefail

ENDPOINT="${LOCALSTACK_ENDPOINT:-http://localhost:4566}"
AWS="aws --endpoint-url $ENDPOINT --region ap-northeast-1"

echo "Using endpoint: $ENDPOINT"

# Groups
$AWS dynamodb create-table \
  --table-name Groups \
  --attribute-definitions AttributeName=group_id,AttributeType=S \
  --key-schema AttributeName=group_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  2>/dev/null && echo "Created: Groups" || echo "Exists:  Groups"

# DeviceGroups  (GSI: group_id-index)
$AWS dynamodb create-table \
  --table-name DeviceGroups \
  --attribute-definitions \
    AttributeName=thing_name,AttributeType=S \
    AttributeName=group_id,AttributeType=S \
  --key-schema AttributeName=thing_name,KeyType=HASH \
  --global-secondary-indexes '[
    {
      "IndexName": "group_id-index",
      "KeySchema": [{"AttributeName":"group_id","KeyType":"HASH"}],
      "Projection": {"ProjectionType":"ALL"}
    }
  ]' \
  --billing-mode PAY_PER_REQUEST \
  2>/dev/null && echo "Created: DeviceGroups" || echo "Exists:  DeviceGroups"

# Commands  (GSI: thing_name-created-index, TTL on ttl attribute)
$AWS dynamodb create-table \
  --table-name Commands \
  --attribute-definitions \
    AttributeName=command_id,AttributeType=S \
    AttributeName=thing_name,AttributeType=S \
    AttributeName=created_at,AttributeType=S \
  --key-schema AttributeName=command_id,KeyType=HASH \
  --global-secondary-indexes '[
    {
      "IndexName": "thing_name-created-index",
      "KeySchema": [
        {"AttributeName":"thing_name","KeyType":"HASH"},
        {"AttributeName":"created_at","KeyType":"RANGE"}
      ],
      "Projection": {"ProjectionType":"ALL"}
    }
  ]' \
  --billing-mode PAY_PER_REQUEST \
  2>/dev/null && echo "Created: Commands" || echo "Exists:  Commands"

$AWS dynamodb update-time-to-live \
  --table-name Commands \
  --time-to-live-specification "Enabled=true,AttributeName=ttl" \
  2>/dev/null || true

echo "Tables ready."
