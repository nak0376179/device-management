from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import jwt_bearer
from db import commands_table, device_groups_table
from iot_client import IoTClientError, mqtt_publish

router = APIRouter(prefix="/api", tags=["commands"])

_TTL_DAYS = 7


def _assert_device_access(thing_name: str, group_id: str) -> None:
    item = device_groups_table().get_item(Key={"thing_name": thing_name}).get("Item")
    if not item or item.get("group_id") != group_id:
        raise HTTPException(status_code=403, detail="Device not in your group")


class CommandRequest(BaseModel):
    command: str


@router.post("/devices/{thing_name}/commands", status_code=201)
def submit_command(
    thing_name: str, body: CommandRequest, group_id: str = Depends(jwt_bearer)
) -> dict[str, str]:
    _assert_device_access(thing_name, group_id)

    command_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    ttl = int(now.timestamp()) + _TTL_DAYS * 86400

    commands_table().put_item(Item={
        "command_id": command_id,
        "group_id": group_id,
        "thing_name": thing_name,
        "command": body.command,
        "status": "pending",
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "duration_ms": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "ttl": ttl,
    })

    try:
        mqtt_publish(f"cmd/notify/{thing_name}", {"command_id": command_id})
    except IoTClientError:
        pass  # Command is saved; device will see it on reconnect

    return {"command_id": command_id}


@router.get("/commands/{command_id}")
def get_command(command_id: str, group_id: str = Depends(jwt_bearer)) -> dict[str, Any]:
    item = commands_table().get_item(Key={"command_id": command_id}).get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Command not found")
    if item.get("group_id") != group_id:
        raise HTTPException(status_code=403, detail="Not your command")
    return item


@router.get("/devices/{thing_name}/commands")
def list_commands(
    thing_name: str, group_id: str = Depends(jwt_bearer)
) -> dict[str, Any]:
    _assert_device_access(thing_name, group_id)
    resp = commands_table().query(
        IndexName="thing_name-created-index",
        KeyConditionExpression=Key("thing_name").eq(thing_name),
        ScanIndexForward=False,
        Limit=20,
    )
    return {"commands": resp.get("Items", [])}
