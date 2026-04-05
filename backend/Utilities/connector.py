import os
import pymongo
from dotenv import load_dotenv

load_dotenv()

class Connector:
    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        db_name = os.getenv("DATABASE_NAME", "WatchWise")
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[db_name]