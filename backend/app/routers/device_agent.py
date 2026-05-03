from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from db import devices_table, tasks_table
from device import make_device_pk

router = APIRouter(prefix="/api/device", tags=["device-agent"])

COMMAND_TIMEOUT_SEC = int(os.environ.get("COMMAND_TIMEOUT_SEC", "30"))


def _device_pk_from_api_key(api_key: str) -> str:
    resp = devices_table().query(
        IndexName="api_key-index",
        KeyConditionExpression=Key("api_key").eq(api_key),
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        raise HTTPException(status_code=401, detail="Invalid API key")
    item = items[0]
    return make_device_pk(item["group_id"], item["dev_id"])


@router.get("/tasks/{task_id:path}")
def fetch_task(
    task_id: str, x_device_api_key: str = Header(...)
) -> dict[str, Any]:
    device_pk = _device_pk_from_api_key(x_device_api_key)
    now = datetime.now(timezone.utc).isoformat()
    try:
        resp = tasks_table().update_item(
            Key={"device_pk": device_pk, "task_id": task_id},
            UpdateExpression="SET #s = :running, updated_at = :t",
            ConditionExpression=Attr("status").eq("pending"),
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":running": "running", ":t": now},
            ReturnValues="ALL_OLD",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HTTPException(status_code=404, detail="Task not found or not pending")
        raise
    return {"command": resp["Attributes"]["command"], "timeout_sec": COMMAND_TIMEOUT_SEC}


class ResultBody(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


@router.post("/tasks/{task_id:path}/result")
def submit_result(
    task_id: str, body: ResultBody, x_device_api_key: str = Header(...)
) -> dict[str, str]:
    device_pk = _device_pk_from_api_key(x_device_api_key)
    status = "completed" if body.exit_code == 0 else "failed"
    now = datetime.now(timezone.utc).isoformat()
    try:
        tasks_table().update_item(
            Key={"device_pk": device_pk, "task_id": task_id},
            UpdateExpression=(
                "SET #s = :s, stdout = :out, stderr = :err, "
                "exit_code = :ec, duration_ms = :dur, updated_at = :t"
            ),
            ConditionExpression=Attr("status").is_in(["running", "pending"]),
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": status,
                ":out": body.stdout,
                ":err": body.stderr,
                ":ec": body.exit_code,
                ":dur": body.duration_ms,
                ":t": now,
            },
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HTTPException(status_code=409, detail="Task already completed")
        raise
    return {"status": status}
