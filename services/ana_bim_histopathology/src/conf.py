import os

from ifcopenshell import geom as ifc_geom

env_get = os.environ.get

settings = ifc_geom.settings()
settings.set(settings.USE_WORLD_COORDS, True)

DEFAULT_GRID_SIZE = 0.5
"""Default grid size in meters for pathfinding algorithm."""

DEFAULT_RUNNER_SPEED = 1.2
"""Default runner speed in m/s."""

BIM_FILE = env_get("BIM_FILE", "Histo.ifc")
OUTPUT_FILE = env_get("OUTPUT_FILE", "output.json")

MONGO_HOST = env_get("MONGO_HOST", "localhost")
MONGO_PORT = int(env_get("MONGO_PORT", "27017"))
MONGO_USER = env_get("MONGO_USER", "root")
MONGO_PASSWORD = env_get("MONGO_PASSWORD", "example")
MONGO_TIMEOUT_MS = int(env_get("MONGO_TIMEOUT_MS", "5000"))