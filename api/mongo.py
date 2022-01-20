from motor.motor_asyncio import AsyncIOMotorClient

from api.config import settings


client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.mongo_db_name]
