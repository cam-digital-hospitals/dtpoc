from pymongo import MongoClient

from .conf import MONGO_TIMEOUT_MS, MONGO_URI


def get_database():
    try:
        client = MongoClient(MONGO_URI, timeoutMS=MONGO_TIMEOUT_MS)
        yield client
    finally:
        if client:
            client.close()
