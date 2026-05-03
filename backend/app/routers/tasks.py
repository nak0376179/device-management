from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import jwt_bearer
from db import tasks_table
from device import assert_device_access
from iot_client import IoTClientError, mqtt_publish

router = APIRouter(prefix="/api", tags=["tasks"])

_TTL_DAYS = 7


class TaskRequest(BaseModel):
    command: str


@router.post("/devices/{thing_name}/tasks", status_code=201)
def submit_task(
    thing_name: str, body: TaskRequest, group_id: str = Depends(jwt_bearer)
) -> dict[str, str]:
    device_pk = assert_device_access(thing_name, group_id)

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    ttl = int(now.timestamp()) + _TTL_DAYS * 86400

    tasks_table().put_item(Item={
        "device_pk": device_pk,
        "task_id": now_iso,
        "group_id": group_id,
        "command": body.command,
        "status": "pending",
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "duration_ms": None,
        "updated_at": now_iso,
        "ttl": ttl,
    })

    try:
        mqtt_publish(f"cmd/notify/{thing_name}", {"task_id": now_iso})
    except IoTClientError:
        pass

    return {"task_id": now_iso}


@router.get("/devices/{thing_name}/tasks/{task_id:path}")
def get_task(
    thing_name: str, task_id: str, group_id: str = Depends(jwt_bearer)
) -> dict[str, Any]:
    device_pk = assert_device_access(thing_name, group_id)
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
    device_pk = assert_device_access(thing_name, group_id)
    resp = tasks_table().query(
        KeyConditionExpression=Key("device_pk").eq(device_pk),
        ScanIndexForward=False,
        Limit=20,
    )
    return {"tasks": resp.get("Items", [])}
