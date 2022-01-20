from pydantic import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    mongo_url: str
    mongo_db_name: str
    redis_url: str
    redis_db_name: str
    max_resources_num: int
    redis_proxy_history: int

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


settings = Settings()
