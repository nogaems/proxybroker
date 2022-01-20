from fastapi import APIRouter, Request, Body, HTTPException, status
from pydantic import AnyUrl

from typing import List, Optional
from time import time
from uuid import uuid4

from api import models
from api import mongo
from api.config import settings

resources = APIRouter()

# Even though there's totally no need for a thorough CRUD interface implementation,
# I'll have it here just for demonstration purposes since this a job application project.
# Also there's plenty of repetitions in this code and I'm intentionally not putting it
# in a separate modules and functions in order to improve readability and to save up some time.
# TODO: restructure parts like ensiring that an entity exists within a certain collection, etc
# in a way that it could be reused.


@resources.get('/resources', response_model=List[models.Resource])
async def get_all_resources():
    '''
    Get full list of supported resources
    '''
    return await mongo.db.resources.find({}).to_list(settings.max_resources_num)


@resources.post('/resources/searches', response_model=models.Resource)
async def find_resource(_id: Optional[models.PyObjectId] = Body(None), url: AnyUrl = Body(None)):
    '''
    Find a resource by ID or URL
    '''
    query = {}
    if _id:
        query['_id'] = _id
    if url:
        query['url'] = url
    if not query:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Search terms must be either "_id" or "url"')
    resource = await mongo.db.resources.find_one(query)
    if resource:
        return resource
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f'There is no resource matching query {query}')


@resources.post('/resources', response_model=models.Resource, status_code=201)
async def add_resource(resource: models.ResourceUrl):
    '''
    Add a new resource
    '''
    existing = await mongo.db.resources.find_one({'url': resource.url})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f'Resource with URL {resource.url} already exists with ID {existing["_id"]}')
    result = await mongo.db.resources.insert_one(resource.dict())
    if result:
        return {
            '_id': result.inserted_id,
            'url': resource.url
        }
    else:
        HTTPException(
            detail=f'Failed to add a resource with URL {resource.url}', status_code=500)


@resources.put('/resources/{resource_id}', response_model=models.Resource)
async def update_resource(resource_id: models.PyObjectId, resource: models.ResourceUrl):
    '''
    Update resource URL
    '''
    existing = await mongo.db.resources.find_one({'_id': resource_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Resource with ID {resource_id} does not exist')
    if existing['url'] == resource.url:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Specified URL is the same as the former one')
    result = await mongo.db.resources.update_one({'_id': resource_id},
                                                 {'$set': {'url': resource.url}})
    if result and result.modified_count:
        return {
            '_id': resource_id,
            'url': resource.url
        }
    else:
        raise HTTPException(
            detail=f'Failed to update a resource with ID {resource_id}', status_code=500)


@resources.delete('/resources/{resource_id}', response_model=models.Resource)
async def delete_resource(resource_id: models.PyObjectId):
    '''
    Delete a resource
    '''
    existing = await mongo.db.resources.find_one({'_id': resource_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Resource with ID {resource_id} does not exist')
    result = await mongo.db.resources.delete_one({'_id': resource_id})
    print(dir(result))
    if result and result.deleted_count:
        return existing
    else:
        HTTPException(
            detail=f'Failed to delete a resource with ID {resource_id}', status_code=500)


proxies = APIRouter()

# Since there's no clear explanation of `rpw` usage in the context of a search criteria whatsoever,
# I just loosely assume here that it means "less than this amount of rpw".
# TODO: add simple syntax for query capabilities for `rpw` field in a way that this value could be used
# arbitrarily, i.e. introduce `>`, `>=` etc operators.


@proxies.post('/proxies', response_model=models.Proxy)
async def add_proxy(proxy: models.ProxyIn):
    '''
    Add a proxy
    '''
    existing = await mongo.db.proxies.find_one({'url': proxy.url})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f'Proxy with specified URL {proxy.url} already exists with ID {existing["_id"]}')
    result = await mongo.db.proxies.insert_one(proxy.dict())
    if result and result.inserted_id:
        return await mongo.db.proxies.find_one({'_id': result.inserted_id})
    else:
        HTTPException(detail=f'Failed to add a proxy {proxy}', status_code=500)


@proxies.get('/proxies', response_model=List[models.Proxy])
async def get_all_proxies():
    '''
    Get full list of existing proxies

    '''
    return await mongo.db.proxies.find({}).to_list(None)


# Probably it would be more idiomatic to use GET method here but
# having a body payload within a GET request is beyond specification
# and might cause undefined behavior and implementation issues on client side.
@proxies.post('/proxies/obtain', response_model=models.Proxy)
async def obtain_proxy(request: Request, query: models.ProxyRequest):
    '''
    Since there's no clear explanation of `rpw` usage in the context of a search criteria whatsoever,
    I just loosely assume here that it means "less than this amount of rpw".
    On success, returned proxy gets marked as being used and is not available for anyone else until
    specified `ttl` wears off.
    '''
    # TODO: add simple syntax for query capabilities for `rpw` field in a way that this value could be used
    # arbitrarily, i.e. introduce `>`, `>=` etc operators.
    db_query = query.dict(exclude_none=True)
    for to_exclude in ['ttl', 'rpw']:
        if to_exclude in db_query:
            db_query.pop(to_exclude)
    db_query['resources_ids'] = {"$all": db_query["resources_ids"]}
    found = await mongo.db.proxies.find(db_query).to_list(None)
    print(found)
    if found:
        redis = request.app.state.redis  # shortcut
        awailable = []
        for proxy in found:
            if await redis.get(f'{proxy["_id"]}') is None:
                # proxy is currently not taken
                awailable.append(f'{proxy["_id"]}')
        if awailable:
            hist = [(proxy, len(await redis.keys(f'{proxy}_*'))) for proxy in awailable]
            print(hist)
            if query.rpw is not None:
                # some additional filtering must be done
                hist = list(filter(lambda x: x[1] <= query.rpw, hist))
            print(hist)
            if hist:
                # we finally got ourselves good candidates,
                # now for load balancing's sake we just use
                # the one that's been used least often
                hist.sort(key=lambda x: x[1])
                proxy_id = models.PyObjectId(hist[0][0])
                filler = str(uuid4())
                await redis.set(f'{proxy_id}_{time()}', filler, ex=settings.redis_proxy_history)
                await redis.set(f'{proxy_id}', filler, ex=query.ttl)
                return await mongo.db.proxies.find_one({'_id': proxy_id})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@proxies.put('/proxies/{proxy_id}', response_model=models.Proxy)
async def update_proxy(proxy_id: models.PyObjectId, proxy: models.ProxyUpdate):
    '''
    Update specified proxy
    '''
    existing = await mongo.db.proxies.find_one({'_id': proxy_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Proxy with ID {proxy_id} does not exist')
    existing.update(proxy.dict(exclude_none=True))
    result = await mongo.db.proxies.update_one({'_id': proxy_id},
                                               {'$set': existing})
    if result:
        return await mongo.db.proxies.find_one({'_id': proxy_id})
    else:
        raise HTTPException(
            detail=f'Failed to update a proxy with ID {proxy_id}', status_code=500)


@proxies.delete('/proxies/{proxy_id}', response_model=models.Proxy)
async def delete_proxy(proxy_id: models.PyObjectId):
    '''
    Delete specified proxy
    '''
    existing = await mongo.db.proxies.find_one({'_id': proxy_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Proxy with ID {proxy_id} does not exist')
    result = await mongo.db.proxies.delete_one({'_id': proxy_id})
    if result and result.deleted_count:
        return existing
    else:
        raise HTTPException(
            detail=f'Failed to delete a proxy with ID {proxy_id}', status_code=500)
