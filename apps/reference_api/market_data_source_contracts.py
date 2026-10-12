"""Safe catalogue metadata and bounded source preference commands."""
from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourcePriorityInput(BaseModel):
    instrument_type_id: UUID = Field(alias='instrumentTypeId')
    scope: Literal['TENANT','PLATFORM'] = 'TENANT'
    mode: Literal['CUSTOM','INHERIT'] = 'CUSTOM'
    dataset_ids: list[UUID] = Field(default_factory=list, alias='datasetIds', max_length=200)
    expected_version_id: UUID | None = Field(default=None, alias='expectedVersionId')
    model_config = ConfigDict(populate_by_name=True, extra='forbid')

    @model_validator(mode='after')
    def ordered_sources(self):
        if len(set(self.dataset_ids)) != len(self.dataset_ids):
            raise ValueError('A dataset can occur only once in the priority order')
        if self.mode == 'INHERIT' and (self.dataset_ids or self.scope == 'PLATFORM'):
            raise ValueError('Inheritance is tenant-only and cannot contain an explicit source order')
        return self


class PriorityView(BaseModel):
    versionId: UUID
    instrumentTypeId: UUID
    scope: Literal['TENANT','PLATFORM']
    mode: Literal['CUSTOM','INHERIT']
    versionNo: int
    datasetIds: list[UUID]
    createdAt: datetime


class CoveragePackageView(BaseModel):
    code: str
    label: str
    contentOwner: str
    market: str | None
    timing: str
    validFrom: date
    validTo: date | None


class EntitlementScopeView(BaseModel):
    purpose: str
    coverageMode: str
    packageCodes: list[str]
    validFrom: date
    validTo: date | None


class SourceView(BaseModel):
    datasetId: UUID
    provider: str
    product: str
    code: str
    label: str
    tenantOwned: bool
    coverageDescription: str | None
    coverageMode: str
    packages: list[CoveragePackageView]
    purposes: list[str]
    entitlementScopes: list[EntitlementScopeView]
    nonDisplayAllowed: bool
    validFrom: date
    validTo: date | None


class InstrumentTypeOption(BaseModel):
    id: UUID
    label: str


class SourceCatalogueView(BaseModel):
    canManage: bool
    canManagePlatform: bool
    sources: list[SourceView]
    instrumentTypes: list[InstrumentTypeOption]
    priorities: list[PriorityView]
