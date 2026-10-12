"""Validated management commands; unknown fields never become authority."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Command(BaseModel):
    model_config=ConfigDict(extra='forbid')


class ModuleChange(Command):
    enabled: bool


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


class ContextSelect(Command):
    tenantId: UUID | None=None
    userId: UUID | None=None
