from __future__ import annotations

from typing import Any

from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import jwt_bearer
from db import devices_table
from iot_client import IoTClientError, get_shadow, list_things, update_desired

router = APIRouter(prefix="/api", tags=["devices"])


def _assert_device_access(thing_name: str, group_id: str) -> None:
    # thing_name format: "group_id:dev_id"
    parts = thing_name.split(":", 1)
    if len(parts) != 2 or parts[0] != group_id:
        raise HTTPException(status_code=403, detail="Device not in your group")
    dev_id = parts[1]
    item = devices_table().get_item(
        Key={"group_id": group_id, "dev_id": dev_id}
    ).get("Item")
    if not item:
        raise HTTPException(status_code=403, detail="Device not in your group")


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except IoTClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/devices")
def list_devices(group_id: str = Depends(jwt_bearer)) -> dict[str, Any]:
    resp = devices_table().query(
        KeyConditionExpression=Key("group_id").eq(group_id),
    )
    thing_names = {item["thing_name"] for item in resp.get("Items", [])}
    all_things = _wrap(list_things)
    devices = []
    for t in all_things:
        if t["thingName"] not in thing_names:
            continue
        connected = False
        try:
            shadow = get_shadow(t["thingName"])
            connected = bool(shadow.get("state", {}).get("reported", {}).get("connected", False))
        except IoTClientError:
            pass
        devices.append({**t, "connected": connected})
    return {"devices": devices}


class DesiredUpdate(BaseModel):
    desired: dict[str, Any]


class DescriptionBody(BaseModel):
    description: str


@router.get("/devices/{thing_name}/shadow")
def read_shadow(thing_name: str, group_id: str = Depends(jwt_bearer)) -> dict[str, Any]:
    _assert_device_access(thing_name, group_id)
    return _wrap(get_shadow, thing_name)


@router.patch("/devices/{thing_name}/shadow")
def patch_shadow(
    thing_name: str, body: DesiredUpdate, group_id: str = Depends(jwt_bearer)
) -> dict[str, Any]:
    _assert_device_access(thing_name, group_id)
    return _wrap(update_desired, thing_name, body.desired)


@router.post("/devices/{thing_name}/interfaces/{iface}/enable")
def enable_interface(
    thing_name: str, iface: str, group_id: str = Depends(jwt_bearer)
) -> dict[str, Any]:
    _assert_device_access(thing_name, group_id)
    return _wrap(update_desired, thing_name, {"interfaces": {iface: {"enabled": True}}})


@router.post("/devices/{thing_name}/interfaces/{iface}/disable")
def disable_interface(
    thing_name: str, iface: str, group_id: str = Depends(jwt_bearer)
) -> dict[str, Any]:
    _assert_device_access(thing_name, group_id)
    return _wrap(update_desired, thing_name, {"interfaces": {iface: {"enabled": False}}})


@router.put("/devices/{thing_name}/interfaces/{iface}/description")
def set_description(
    thing_name: str, iface: str, body: DescriptionBody, group_id: str = Depends(jwt_bearer)
) -> dict[str, Any]:
    _assert_device_access(thing_name, group_id)
    return _wrap(update_desired, thing_name, {"interfaces": {iface: {"description": body.description}}})
