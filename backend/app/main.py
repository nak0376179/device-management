"""Device Management API.

Local dev:  uvicorn --app-dir app main:app --reload
On Lambda:  Mangum adapter exposed as `handler`.

All data routes are under /api prefix so the Vite dev proxy can forward
/api/* → backend without path rewriting, and production builds point
VITE_API_URL to the API Gateway origin (routes stay at /api/*).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel

from iot_client import IoTClientError, get_shadow, list_things, update_desired

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Device Management API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api")


class DesiredUpdate(BaseModel):
    desired: dict[str, Any]


class DescriptionBody(BaseModel):
    description: str


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@router.get("/devices")
def list_devices() -> dict[str, Any]:
    return {"devices": _wrap(list_things)}


@router.get("/devices/{thing_name}/shadow")
def read_shadow(thing_name: str) -> dict[str, Any]:
    return _wrap(get_shadow, thing_name)


@router.patch("/devices/{thing_name}/shadow")
def patch_shadow(thing_name: str, body: DesiredUpdate) -> dict[str, Any]:
    return _wrap(update_desired, thing_name, body.desired)


@router.post("/devices/{thing_name}/interfaces/{iface}/enable")
def enable_interface(thing_name: str, iface: str) -> dict[str, Any]:
    return _wrap(update_desired, thing_name, {"interfaces": {iface: {"enabled": True}}})


@router.post("/devices/{thing_name}/interfaces/{iface}/disable")
def disable_interface(thing_name: str, iface: str) -> dict[str, Any]:
    return _wrap(update_desired, thing_name, {"interfaces": {iface: {"enabled": False}}})


@router.put("/devices/{thing_name}/interfaces/{iface}/description")
def set_description(thing_name: str, iface: str, body: DescriptionBody) -> dict[str, Any]:
    return _wrap(
        update_desired, thing_name, {"interfaces": {iface: {"description": body.description}}}
    )


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except IoTClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


app.include_router(router)

handler = Mangum(app, lifespan="off")
