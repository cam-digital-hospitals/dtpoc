import os

env_get = os.environ.get

# General config
HOST = env_get("HOST", "0.0.0.0")
PORT = int(env_get("PORT", "8000"))

VERSION = env_get("VERSION", "v1")
INPUT_EXCEL_FILE = env_get("INPUT_EXCEL_FILE", "input.xlsx")
OUTPUT_FILE = env_get("OUTPUT_FILE", "output.json")

MONGO_URI = env_get("MONGO_URI", "mongodb://localhost:27017")
MONGO_TIMEOUT_MS = int(env_get("MONGO_TIMEOUT_MS", "5000"))

# Simulation Config
ARR_RATE_INTERVAL_HOURS = int(env_get("ARR_RATE_INTERVAL_HOURS", "1"))
"""Interval duration for which specimen arrival rates are defined in the Excel config template."""

RESOURCE_ALLOCATION_INTERVAL_HOURS = float(
    env_get("RESOURCE_ALLOCATION_INTERVAL_HOURS", "0.5")
)
"""Interval duration for which resource allocations are defined in the Excel config template."""
