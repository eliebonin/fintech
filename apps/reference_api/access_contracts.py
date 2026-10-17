"""Validated management commands; unknown fields never become authority."""
from typing import Literal
from uuid import UUID
from datetime import datetime,timezone,timedelta
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Command(BaseModel):
    model_config=ConfigDict(extra='forbid')


class ModuleChange(Command):
    enabled: bool

class PublicationPolicyChange(Command):
    enabled: bool
    validUntil: datetime|None=None
    expectedRevision: int=Field(ge=0,strict=True)
    reason: str=Field(min_length=1,max_length=2000)
    confirmChange: Literal[True]

    @field_validator('reason')
    @classmethod
    def reason_required(cls,value):
        if not value.strip():raise ValueError('Reason must not be blank')
        return value.strip()

    @field_validator('validUntil')
    @classmethod
    def utc_expiry(cls,value):
        if value and (value.tzinfo is None or value.utcoffset()!=timedelta(0)):raise ValueError('Timezone-aware UTC expiry required')
        return value


class TenantUpdate(Command):
    name: str=Field(min_length=1,max_length=250)
    contactName: str | None=Field(default=None,max_length=250)
    contactEmail: str | None=Field(default=None,max_length=254,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    status: Literal['ACTIVE','SUSPENDED']
    expectedVersion: int=Field(ge=0,strict=True)
    confirmStatusChange: bool=False

    @field_validator('name','contactName','contactEmail',mode='before')
    @classmethod
    def trim(cls,value,info):
        if not isinstance(value,str):
            return value
        value=value.strip()
        return value if value or info.field_name=='name' else None


class UserCreate(Command):
    name: str=Field(min_length=1,max_length=250)
    role: Literal['MEMBER','TENANT_ADMIN']='MEMBER'

    @field_validator('name',mode='before')
    @classmethod
    def trim(cls,value):
        return value.strip() if isinstance(value,str) else value


class UserChange(Command):
    status: Literal['ACTIVE','SUSPENDED']
    role: Literal['MEMBER','TENANT_ADMIN'] | None=None


class UserGroups(Command):
    groupIds: list[UUID]=Field(max_length=100)


class GroupSave(Command):
    code: str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
    name: str=Field(min_length=1,max_length=250)
    description: str | None=Field(default=None,max_length=2000)
    actions: list[str]=Field(max_length=100)
    status: Literal['ACTIVE','SUSPENDED']='ACTIVE'
    scopeMode: Literal['ALL','SELECTED']
    strategyIds: list[UUID]=Field(default_factory=list,max_length=1000)
    expectedVersion: int | None=Field(default=None,ge=1,strict=True)
    expectedImpactHash: str | None=Field(default=None,pattern=r'^[0-9a-f]{64}$')


class ContextSelect(Command):
    tenantId: UUID | None=None
    userId: UUID | None=None


class GroupPreview(GroupSave):
    groupId: UUID | None=None
