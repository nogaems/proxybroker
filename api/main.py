from fastapi import FastAPI

from api.routers import resources, proxies
from api.redis import init_redis_pool

app = FastAPI(title='Proxy Broker', version='0.1.0')

app.include_router(resources, tags=['Resources'])
app.include_router(proxies, tags=['Proxies'])


@app.on_event("startup")
async def startup_event():
    app.state.redis = await init_redis_pool()


@app.on_event("shutdown")
async def shutdown_event():
    await app.state.redis.close()
