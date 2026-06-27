"""DynamoDB client helpers with Floci (local) / real AWS support."""

from __future__ import annotations

import os
from functools import lru_cache

import boto3

# Set locally to point boto3 at Floci (http://localhost:4566); unset in the
# cloud so boto3 talks to real AWS. AWS_ENDPOINT_URL is the standard boto3 var.
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")

TABLE_GROUPS = os.environ.get("TABLE_GROUPS", "Groups")
TABLE_DEVICES = os.environ.get("TABLE_DEVICES", "Devices")
TABLE_TASKS = os.environ.get("TABLE_TASKS", "Tasks")


@lru_cache(maxsize=1)
def _resource():
    return boto3.resource("dynamodb", endpoint_url=AWS_ENDPOINT_URL)


def groups_table():
    return _resource().Table(TABLE_GROUPS)


def devices_table():
    return _resource().Table(TABLE_DEVICES)


def tasks_table():
    return _resource().Table(TABLE_TASKS)
