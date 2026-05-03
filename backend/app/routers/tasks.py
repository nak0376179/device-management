from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import jwt_bearer
from db import devices_table, tasks_table
from iot_client import IoTClientError, mqtt_publish

router = APIRouter(prefix="/api", tags=["tasks"])

_TTL_DAYS = 7


def _assert_device_access(thing_name: str, group_id: str) -> tuple[str, str]:
    """Verify device belongs to group. Returns (dev_id, device_pk)."""
    parts = thing_name.split(":", 1)
    if len(parts) != 2 or parts[0] != group_id:
        raise HTTPException(status_code=403, detail="Device not in your group")
    dev_id = parts[1]
    item = devices_table().get_item(
        Key={"group_id": group_id, "dev_id": dev_id}
    ).get("Item")
    if not item:
        raise HTTPException(status_code=403, detail="Device not in your group")
    return dev_id, f"{group_id}#{dev_id}"


class TaskRequest(BaseModel):
    command: str


@router.post("/devices/{thing_name}/tasks", status_code=201)
def submit_task(
    thing_name: str, body: TaskRequest, group_id: str = Depends(jwt_bearer)
) -> dict[str, str]:
    _dev_id, device_pk = _assert_device_access(thing_name, group_id)

    now = datetime.now(timezone.utc)
    task_id = now.isoformat()
    ttl = int(now.timestamp()) + _TTL_DAYS * 86400

    tasks_table().put_item(Item={
        "device_pk": device_pk,
        "task_id": task_id,
        "group_id": group_id,
        "command": body.command,
        "status": "pending",
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "duration_ms": None,
        "updated_at": now.isoformat(),
        "ttl": ttl,
    })

    try:
        mqtt_publish(f"cmd/notify/{thing_name}", {"task_id": task_id})
    except IoTClientError:
        pass

    return {"task_id": task_id}


@router.get("/devices/{thing_name}/tasks/{task_id:path}")
def get_task(
    thing_name: str, task_id: str, group_id: str = Depends(jwt_bearer)
) -> dict[str, Any]:
    _dev_id, device_pk = _assert_device_access(thing_name, group_id)
    item = tasks_table().get_item(
        Key={"device_pk": device_pk, "task_id": task_id}
    ).get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    return item


@router.get("/devices/{thing_name}/tasks")
def list_tasks(
    thing_name: str, group_id: str = Depends(jwt_bearer)
) -> dict[str, Any]:
    _dev_id, device_pk = _assert_device_access(thing_name, group_id)
    resp = tasks_table().query(
        KeyConditionExpression=Key("device_pk").eq(device_pk),
        ScanIndexForward=False,
        Limit=20,
    )
    return {"tasks": resp.get("Items", [])}
