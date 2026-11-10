"""Pure profile metadata contracts; product economic minimums stay native."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator

STANDARD_FIELDS={
    'COUNTERPARTY':dict(label='Counterparty',source='standard:COUNTERPARTY',attribute='counterparty_organisation_id'),
    'EXECUTING_BROKER':dict(label='Executing broker',source='standard:EXECUTING_BROKER',attribute='executing_broker_organisation_id'),
    'TRADER':dict(label='Trader',source='standard:TRADER',attribute='trader_person_id'),
    'COMMENT':dict(label='Comment',source=None,attribute='comment'),
}

class FieldRule(BaseModel):
    standard_field_key:Literal['COUNTERPARTY','EXECUTING_BROKER','TRADER','COMMENT']|None=Field(default=None,alias='standardFieldKey')
    property_code:str|None=Field(default=None,alias='propertyCode',pattern=r'^[A-Za-z][A-Za-z0-9_]{0,99}$')
    property_version:int|None=Field(default=None,alias='propertyVersion',ge=1,strict=True)
    requirement:Literal['REQUIRED','OPTIONAL','NOT_USED']='OPTIONAL'
    lifecycle_behavior:Literal['ALLOCATION','INHERIT','INPUT']=Field(default='INPUT',alias='lifecycleBehavior')
    model_config=ConfigDict(extra='forbid',populate_by_name=True,frozen=True,str_strip_whitespace=True)

    @model_validator(mode='after')
    def source_binding(self):
        if (self.standard_field_key is None)==(self.property_code is None):raise ValueError('Select exactly one standard or custom field.')
        if (self.property_code is None)!=(self.property_version is None):raise ValueError('Custom fields require an exact definition version.')
        if self.requirement=='NOT_USED' and self.lifecycle_behavior!='INPUT':raise ValueError('A hidden field cannot be inherited or divide allocations.')
        if self.standard_field_key=='COMMENT' and self.lifecycle_behavior=='ALLOCATION':raise ValueError('Free-form comments cannot divide positions.')
        return self

    @property
    def field_key(self):
        return ('STANDARD:'+self.standard_field_key) if self.standard_field_key else ('CUSTOM:'+self.property_code)

class ProfileVersionInput(BaseModel):
    label:str=Field(min_length=1,max_length=250)
    description:str|None=Field(default=None,max_length=2000)
    reason:str=Field(min_length=1,max_length=2000)
    expected_version:int=Field(alias='expectedVersion',ge=0,strict=True)
    fields:list[FieldRule]=Field(max_length=1000+len(STANDARD_FIELDS))
    model_config=ConfigDict(extra='forbid',populate_by_name=True,str_strip_whitespace=True)

    @model_validator(mode='after')
    def unique_fields(self):
        keys=[f.field_key for f in self.fields]
        if len(set(keys))!=len(keys):raise ValueError('Each field family can appear only once in a profile.')
        return self


def standard_input_id(key):
    """Transport key only; canonical standard values keep their real native IDs."""
    from uuid import uuid5,NAMESPACE_URL
    if key not in STANDARD_FIELDS:raise ValueError('Unknown standard field.')
    return uuid5(NAMESPACE_URL,'platform:trade-standard-field:'+key)


class ResolvedField(FieldRule):
    fieldKey:str
    label:str
    sourceKey:str|None
    definitionId:UUID|None
    valueType:str|None=None
    catalogueId:UUID|None=None
    definitionStatus:str|None=None

class ConfigurationView(BaseModel):
    canAssign:bool=False
    tenantId:UUID
    strategyId:UUID
    profileVersionId:UUID
    profileId:UUID
    profileLabel:str
    versionNo:int
    assignmentRevision:int
    configurationHash:str
    fields:list[ResolvedField]
