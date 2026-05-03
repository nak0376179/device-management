"""Thin wrapper over boto3 iot-data and iot for shadow operations."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

REGION = (
    os.environ.get("AWS_REGION")
    or os.environ.get("AWS_DEFAULT_REGION")
    or "ap-northeast-1"
)


class IoTClientError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _iot_data():
    return boto3.client("iot-data", region_name=REGION)


@lru_cache(maxsize=1)
def _iot():
    return boto3.client("iot", region_name=REGION)


def get_shadow(thing_name: str) -> dict[str, Any]:
    try:
        resp = _iot_data().get_thing_shadow(thingName=thing_name)
    except (BotoCoreError, ClientError) as exc:
        raise IoTClientError(f"get_thing_shadow failed: {exc}") from exc
    return json.loads(resp["payload"].read().decode("utf-8"))


def update_desired(thing_name: str, desired: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"state": {"desired": desired}}).encode("utf-8")
    try:
        resp = _iot_data().update_thing_shadow(thingName=thing_name, payload=payload)
    except (BotoCoreError, ClientError) as exc:
        raise IoTClientError(f"update_thing_shadow failed: {exc}") from exc
    return json.loads(resp["payload"].read().decode("utf-8"))


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
