from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from boto3.dynamodb.conditions import Attr
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from db import commands_table, device_groups_table

router = APIRouter(prefix="/api/device", tags=["device-agent"])

COMMAND_TIMEOUT_SEC = int(os.environ.get("COMMAND_TIMEOUT_SEC", "30"))


def _thing_name_from_api_key(api_key: str) -> str:
    resp = device_groups_table().scan(FilterExpression=Attr("api_key").eq(api_key))
    items = resp.get("Items", [])
    if not items:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return str(items[0]["thing_name"])


@router.get("/commands/{command_id}")
def fetch_command(
    command_id: str, x_device_api_key: str = Header(...)
) -> dict[str, Any]:
    thing_name = _thing_name_from_api_key(x_device_api_key)
    item = commands_table().get_item(Key={"command_id": command_id}).get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Command not found")
    if item.get("thing_name") != thing_name:
        raise HTTPException(status_code=403, detail="Command not for this device")

    now = datetime.now(timezone.utc).isoformat()
    commands_table().update_item(
        Key={"command_id": command_id},
        UpdateExpression="SET #s = :s, updated_at = :t",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "running", ":t": now},
    )
    return {"command": item["command"], "timeout_sec": COMMAND_TIMEOUT_SEC}


class ResultBody(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


@router.post("/commands/{command_id}/result")
def submit_result(
    command_id: str, body: ResultBody, x_device_api_key: str = Header(...)
) -> dict[str, str]:
    thing_name = _thing_name_from_api_key(x_device_api_key)
    item = commands_table().get_item(Key={"command_id": command_id}).get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Command not found")
    if item.get("thing_name") != thing_name:
        raise HTTPException(status_code=403, detail="Command not for this device")
    if item.get("status") not in ("running", "pending"):
        raise HTTPException(status_code=409, detail="Command already completed")

    status = "completed" if body.exit_code == 0 else "failed"
    now = datetime.now(timezone.utc).isoformat()
    commands_table().update_item(
        Key={"command_id": command_id},
        UpdateExpression=(
            "SET #s = :s, stdout = :out, stderr = :err, "
            "exit_code = :ec, duration_ms = :dur, updated_at = :t"
        ),
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
    return {"status": status}
