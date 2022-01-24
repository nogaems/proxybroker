from fastapi import HTTPException
from pydantic import BaseModel, Field, AnyUrl
from bson import ObjectId

from typing import Optional, List

from api import mongo
from api.config import settings


class PyObjectId(ObjectId):
    # implementing pydantic's validator protocol
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError(f'"{v}" is invalid ObjectId')
        return ObjectId(v)

    # in order to avoid troubles during docs generation
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type='string')


class MongoDocument(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias='_id')

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        anystr_lower = True
        json_encoders = {ObjectId: str}


class Resource(MongoDocument):
    url: AnyUrl


class ResourceUrl(BaseModel):
    url: AnyUrl


class ResourceQuery(BaseModel):
    id: Optional[str] = Field(alias='_id')
    url: Optional[AnyUrl]


class ResourcesIdsVerificator:
    # pydantic does not support coroutines in `validator` decorator yet,
    # hence I have to come up with some boilerplate code
    async def verify_resources_ids(self):
        if self.resources_ids is None:
            return
        if not len(self.resources_ids):
            raise HTTPException(status_code=422, detail=[{
                'loc': ['body', 'resources_ids'],
                'type': 'value_error',
                'msg': 'resources_ids list must be non-empty'
            }])
        invalid_ids = []
        existing_resources_ids = [resource['_id'] for resource in
                                  await mongo.db.resources.find({},
                                                                {'_id': 1})
                                  .to_list(settings.max_resources_num)]
        for i, _id in enumerate(self.resources_ids):
            if _id not in existing_resources_ids:
                invalid_ids.append((i, _id))
        if invalid_ids:
            raise HTTPException(status_code=422, detail=[
                {
                    'loc': ['body', 'resources_ids', i],
                    'type': 'value_error',
                    'msg': f'resource with ObjectId {_id} does not exist'
                } for i, _id in invalid_ids
            ])


class ProxyIn(BaseModel, ResourcesIdsVerificator):
    url: AnyUrl
    # TODO: `country` value probably must be an enum
    country: str
    resources_ids: List[PyObjectId]

    class Config:
        anystr_lower = True


class ProxyUpdate(BaseModel, ResourcesIdsVerificator):
    url: Optional[AnyUrl]
    country: Optional[str]
    resources_ids: Optional[List[PyObjectId]]

    class Config:
        anystr_lower = True


class ProxyRequest(BaseModel):
    country: Optional[str]
    rpw: Optional[int]
    # in this particular case I don't reuse `ResourcesIdsVerificator` class inheritance
    # simply because unlike the other, this model faces end-user input and these request
    # are idempotent database-wise, so there's actually no point of doing extra job here
    resources_ids: List[PyObjectId]
    ttl: int

    class Config:
        anystr_lower = True
        schema_extra = {
            'properties': {
                'country': {
                    'type': 'string',
                    'description': 'Proxy contry.'
                },
                'rpw': {
                    'type': 'number',
                    'description': 'Request served per week. Specified value is considered to mean "less than or equal to".'  # noqa
                },
                'ttl': {
                    'type': 'number',
                    'description': 'Time-to-live, period of time a proxy will be taken.'
                },
                'resources_ids': {
                    'type': 'array',
                    'description': 'The list of resources\' IDs required proxy should be capable to parse.',
                    'items': {
                        'type': 'string'
                    },
                },
            }
        }


class Proxy(MongoDocument):
    url: AnyUrl
    country: str
    resources_ids: List[PyObjectId]
