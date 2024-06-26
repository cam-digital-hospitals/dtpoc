import os

PROJECT_GROUP = os.environ.get("WATCH_CLIENT_TIMEOUT", "eng.cam.ac.uk")
WATCH_CLIENT_TIMEOUT = int(os.environ.get("WATCH_CLIENT_TIMEOUT", "660"))
WATCH_SERVER_TIMEOUT = int(os.environ.get("WATCH_SERVER_TIMEOUT", "600"))
