# Virtual Network Device

AWS IoT Core に接続して Device Shadow で状態を同期する仮想ネットワーク機器です。バックエンド (Lambda) や React UI から Shadow の `desired` を更新すると、本スクリプトが受信して反映し、`reported` を返します。

## セットアップ

前提: AWS CLI 設定済み、`jq`, `curl`, [uv](https://docs.astral.sh/uv/) (Python 3.10+)。

```bash
# 1. Thing / Cert / Policy を AWS に作成
./setup_aws_iot.sh                    # デフォルト: virtual-device-01
# または
./setup_aws_iot.sh router-01          # 任意の thing 名

# 2. 依存をインストール
uv sync

# 3. 起動
uv run python virtual_device.py              # 通常
uv run python virtual_device.py -v           # デバッグログ
uv run python virtual_device.py --interval 5 # テレメトリ間隔(秒)
```

リージョンを変える場合は `AWS_REGION=us-west-2 ./setup_aws_iot.sh` のように指定。

## State モデル

```jsonc
{
  "hostname": "virtual-device-01",
  "interfaces": {
    "eth0": { "enabled": true,  "description": "WAN",  "rx_bytes": 0, "tx_bytes": 0 },
    "eth1": { "enabled": true,  "description": "LAN1", "rx_bytes": 0, "tx_bytes": 0 },
    "eth2": { "enabled": false, "description": "LAN2", "rx_bytes": 0, "tx_bytes": 0 }
  },
  "system": { "uptime_sec": 0, "cpu_percent": 5.2, "memory_percent": 42.1 }
}
```

- 制御可能: `hostname`, `interfaces.<name>.enabled`, `interfaces.<name>.description`
- 読み取り専用 (デバイスが更新): `rx_bytes`, `tx_bytes`, `system.*`

## 動作確認 (AWS CLI から)

別ターミナルで Shadow の `desired` を更新するとデバイス側に反映されます。

```bash
aws iot-data update-thing-shadow \
  --thing-name virtual-device-01 \
  --payload '{"state":{"desired":{"interfaces":{"eth1":{"enabled":false}}}}}' \
  /tmp/shadow.json && cat /tmp/shadow.json
```

数秒後に `reported.interfaces.eth1.enabled` が `false` になります。

## 後片付け

```bash
THING=virtual-device-01
CERT_ARN=$(cat ./certs/cert.arn)
aws iot detach-thing-principal --thing-name "$THING" --principal "$CERT_ARN"
aws iot detach-policy --policy-name "${THING}-policy" --target "$CERT_ARN"
aws iot update-certificate --certificate-id "${CERT_ARN##*/}" --new-status INACTIVE
aws iot delete-certificate --certificate-id "${CERT_ARN##*/}"
aws iot delete-policy --policy-name "${THING}-policy"
aws iot delete-thing --thing-name "$THING"
rm -rf certs config.json
```
