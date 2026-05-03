"""Fetch a command from the backend, execute it, and post the result."""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Any

import requests

logger = logging.getLogger("command_runner")


def run_command(command: str, timeout_sec: int = 30) -> dict[str, Any]:
    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "duration_ms": int((time.monotonic() - start) * 1000),
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Command timed out after {timeout_sec}s",
            "exit_code": -1,
            "duration_ms": int((time.monotonic() - start) * 1000),
        }


def fetch_and_execute(command_id: str, backend_url: str, api_key: str) -> None:
    headers = {"X-Device-Api-Key": api_key}

    try:
        resp = requests.get(
            f"{backend_url}/api/device/commands/{command_id}",
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("Failed to fetch command %s: HTTP %s", command_id, resp.status_code)
            return
        data = resp.json()
    except Exception as exc:
        logger.error("Error fetching command %s: %s", command_id, exc)
        return

    logger.info("Executing command %s: %r", command_id, data["command"])
    result = run_command(data["command"], data.get("timeout_sec", 30))
    logger.info("Command %s done: exit_code=%s duration=%dms",
                command_id, result["exit_code"], result["duration_ms"])

    try:
        resp = requests.post(
            f"{backend_url}/api/device/commands/{command_id}/result",
            headers=headers,
            json=result,
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("Failed to post result for %s: HTTP %s", command_id, resp.status_code)
    except Exception as exc:
        logger.error("Error posting result for %s: %s", command_id, exc)
