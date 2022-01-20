from pydantic import BaseModel, Field, AnyUrl, validator
from bson import ObjectId

from typing import Optional, List


class PyObjectId(ObjectId):
    # implementing pydantic's validator protocol
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError(f'{v} is invalid ObjectId')
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
        json_encoders = {ObjectId: str}


class Resource(MongoDocument):
    url: AnyUrl = Field(...)


class ResourceUrl(BaseModel):
    url: AnyUrl = Field(...)


class ResourceQuery(BaseModel):
    id: Optional[str] = Field(alias='_id')
    url: Optional[AnyUrl]


class ProxyIn(BaseModel):
    url: AnyUrl = Field(...)
    # TODO: `country` value probably must be an enum
    country: str
    resources_ids: List[PyObjectId] = Field(...)

    @validator('country')
    def lower(cls, v):
        return v.lower()

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ProxyUpdate(BaseModel):
    url: Optional[AnyUrl]
    country: Optional[str]
    resources_ids: Optional[List[PyObjectId]]

    @validator('country')
    def lower(cls, v):
        if v:
            return v.lower()

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ProxyRequest(BaseModel):
    country: Optional[str]
    rpw: Optional[int]
    resources_ids: List[PyObjectId]
    ttl: int

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            'properties': {
                'country': {
                    'type': 'string',
                    'description': 'Proxy contry.'
                },
                'rpw': {
                    'type': 'number',
                    'description': 'Request served per week. Specified value is considered to mean "less than or equal to".'
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


class Proxy(MongoDocument, ProxyIn):
    pass
