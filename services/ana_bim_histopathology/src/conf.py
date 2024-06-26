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
MONGO_URI = env_get("MONGO_URI", "mongodb://localhost:27017")
MONGO_TIMEOUT_MS = 5000
