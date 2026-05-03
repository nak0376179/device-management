"""Device Management API.

Local dev:  uvicorn --app-dir app main:app --reload --port 9001
On Lambda:  Mangum adapter exposed as `handler`.

Routes:
  /healthz                    — health check (no auth)
  /api/auth/*                 — login
  /api/admin/*                — group/device provisioning
  /api/devices/*              — tenant-scoped device control (JWT required)
  /api/devices/*/tasks/*      — task submission & result poll (JWT required)
  /api/device/*               — device-facing task fetch/result (X-Device-Api-Key)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from routers import admin, auth, device_agent, devices, tasks

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Device Management API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(devices.router)
app.include_router(tasks.router)
app.include_router(device_agent.router)

handler = Mangum(app, lifespan="off")
