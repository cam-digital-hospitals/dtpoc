import os

env_get = os.environ.get

PROJECT_GROUP = env_get("PROJECT_GROUP", "eng.cam.ac.uk")
VERSION = "v1alpha1"


MONGO_HOST = env_get("MONGO_HOST", "localhost")
MONGO_PORT = int(env_get("MONGO_PORT", "27017"))
MONGO_USER = env_get("MONGO_USER", "root")
MONGO_PASSWORD = env_get("MONGO_PASSWORD", "example")
MONGO_TIMEOUT_MS = int(env_get("MONGO_TIMEOUT_MS", "5000"))



WATCH_CLIENT_TIMEOUT = int(env_get("WATCH_CLIENT_TIMEOUT", "660"))
WATCH_SERVER_TIMEOUT = int(env_get("WATCH_SERVER_TIMEOUT", "600"))
