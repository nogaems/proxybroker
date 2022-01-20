from motor.motor_asyncio import AsyncIOMotorClient
import bson

from api import models
from api.config import settings

import os

client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.mongo_db_name]
