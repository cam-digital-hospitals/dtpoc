import os

import pytz

env_get = os.environ.get

PORT = env_get("PORT", 8000)
TIMEZONE = pytz.timezone(env_get("TIMEZONE", "Europe/London"))
