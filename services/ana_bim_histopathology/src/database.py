from conf import MONGO_URI
from pymongo import MongoClient


def get_database():
    try:
        client = MongoClient(MONGO_URI)
        yield client
    finally:
        if client:
            client.close()
