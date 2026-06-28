"""Thin wrapper over boto3 iot/iot-data for shadow + MQTT operations.

Against real AWS IoT Core everything goes through boto3. Against Floci's local
IoT emulator (when ``AWS_ENDPOINT_URL`` is set) two paths are special-cased
because Floci 1.5.28 does not bridge its REST and MQTT planes the way real IoT
Core does:

* MQTT publish — boto3 ``iot-data publish`` does not reach MQTT subscribers, so
  we publish straight to Floci's MQTT broker (port 1883) instead.
* Shadow read/write — boto3 ``get_thing_shadow`` reads a different store than the
  one the device's MQTT shadow updates land in, so we use Floci's raw
  ``/things/{thing}/shadow`` REST endpoint, which does reflect MQTT state.

The control plane (``list_things``) works through boto3 in both modes.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any
from urllib.parse import urlsplit

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# httpx and paho-mqtt are local-dev-only (the Floci IoT bridge below) and are
# imported lazily inside the IS_LOCAL branches so the production Lambda — which
# never sets AWS_ENDPOINT_URL — does not need them bundled.

REGION = (
    os.environ.get("AWS_REGION")
    or os.environ.get("AWS_DEFAULT_REGION")
    or "ap-northeast-1"
)

# Set locally to point boto3 at Floci's IoT Core emulator (http://localhost:4566);
# unset in the cloud so boto3 talks to real AWS IoT Core.
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")

# Floci's MQTT broker host/port (only used in local mode). Defaults derive from
# the Floci endpoint host; override with FLOCI_MQTT_HOST / FLOCI_MQTT_PORT.
_FLOCI_HOST = (
    urlsplit(AWS_ENDPOINT_URL).hostname if AWS_ENDPOINT_URL else None
) or "localhost"
FLOCI_MQTT_HOST = os.environ.get("FLOCI_MQTT_HOST", _FLOCI_HOST)
FLOCI_MQTT_PORT = int(os.environ.get("FLOCI_MQTT_PORT", "1883"))

IS_LOCAL = bool(AWS_ENDPOINT_URL)


class IoTClientError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _iot_data():
    return boto3.client("iot-data", region_name=REGION, endpoint_url=AWS_ENDPOINT_URL)


@lru_cache(maxsize=1)
def _iot():
    return boto3.client("iot", region_name=REGION, endpoint_url=AWS_ENDPOINT_URL)


def _shadow_url(thing_name: str) -> str:
    return f"{AWS_ENDPOINT_URL.rstrip('/')}/things/{thing_name}/shadow"


def get_shadow(thing_name: str) -> dict[str, Any]:
    if IS_LOCAL:
        import httpx

        try:
            resp = httpx.get(_shadow_url(thing_name), timeout=5.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            raise IoTClientError(f"get_thing_shadow failed: {exc}") from exc
    try:
        resp = _iot_data().get_thing_shadow(thingName=thing_name)
    except (BotoCoreError, ClientError) as exc:
        raise IoTClientError(f"get_thing_shadow failed: {exc}") from exc
    return json.loads(resp["payload"].read().decode("utf-8"))


def update_desired(thing_name: str, desired: dict[str, Any]) -> dict[str, Any]:
    body = {"state": {"desired": desired}}
    if IS_LOCAL:
        import httpx

        try:
            resp = httpx.post(_shadow_url(thing_name), json=body, timeout=5.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            raise IoTClientError(f"update_thing_shadow failed: {exc}") from exc
    payload = json.dumps(body).encode("utf-8")
    try:
        resp = _iot_data().update_thing_shadow(thingName=thing_name, payload=payload)
    except (BotoCoreError, ClientError) as exc:
        raise IoTClientError(f"update_thing_shadow failed: {exc}") from exc
    return json.loads(resp["payload"].read().decode("utf-8"))


def mqtt_publish(topic: str, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode()
    if IS_LOCAL:
        # Publish straight to Floci's MQTT broker — its REST publish does not
        # reach MQTT subscribers (the device).
        import paho.mqtt.publish as paho_publish

        try:
            paho_publish.single(
                topic,
                payload=data,
                qos=1,
                hostname=FLOCI_MQTT_HOST,
                port=FLOCI_MQTT_PORT,
            )
        except Exception as exc:  # noqa: BLE001 — paho raises bare socket errors
            raise IoTClientError(f"mqtt publish failed: {exc}") from exc
        return
    try:
        _iot_data().publish(topic=topic, qos=1, payload=data)
    except (BotoCoreError, ClientError) as exc:
        raise IoTClientError(f"mqtt publish failed: {exc}") from exc


def list_things(max_results: int = 250) -> list[dict[str, Any]]:
    try:
        resp = _iot().list_things(maxResults=max_results)
    except (BotoCoreError, ClientError) as exc:
        raise IoTClientError(f"list_things failed: {exc}") from exc
    return [
        {
            "thingName": t["thingName"],
            "thingTypeName": t.get("thingTypeName"),
        }
        for t in resp.get("things", [])
    ]
