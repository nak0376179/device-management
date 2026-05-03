from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from auth import pwd_context
from db import device_groups_table, groups_table

router = APIRouter(prefix="/api/admin", tags=["admin"])


class GroupCreate(BaseModel):
    group_id: str
    group_pw: str


class DeviceRegister(BaseModel):
    thing_name: str


@router.post("/groups", status_code=201)
def create_group(body: GroupCreate) -> dict[str, str]:
    now = datetime.now(timezone.utc).isoformat()
    try:
        groups_table().put_item(
            Item={
                "group_id": body.group_id,
                "group_pw_hash": pwd_context.hash(body.group_pw),
                "created_at": now,
            },
            ConditionExpression="attribute_not_exists(group_id)",
        )
    except groups_table().meta.client.exceptions.ConditionalCheckFailedException:
        raise HTTPException(status_code=409, detail="Group already exists")
    return {"group_id": body.group_id}


@router.post("/groups/{group_id}/devices", status_code=201)
def register_device(group_id: str, body: DeviceRegister) -> dict[str, str]:
    if not groups_table().get_item(Key={"group_id": group_id}).get("Item"):
        raise HTTPException(status_code=404, detail="Group not found")
    api_key = str(uuid.uuid4())
    device_groups_table().put_item(Item={
        "thing_name": body.thing_name,
        "group_id": group_id,
        "api_key": api_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"thing_name": body.thing_name, "api_key": api_key}
