"""Controlled preparation inputs; economic execution facts stay read-only."""
from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator

class Contract(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class ProfileCreate(Contract):
    name:str=Field(min_length=1,max_length=250)
    lei:str=Field(pattern=r'^[A-Z0-9]{18}[0-9]{2}$')
    firmCategory:Literal['MIFID_FIRM','CREDIT_INSTITUTION','THIRD_COUNTRY_BRANCH','SMALL_AIFM_MIFID','COLLECTIVE_MANAGER','OTHER']
    firmScope:Literal['IN_SCOPE','OUT_OF_SCOPE','UNASSESSED']='UNASSESSED'
    reason:str=Field(min_length=3,max_length=2000)
    expectedRevision:int|None=Field(default=None,ge=1)

    @field_validator('lei')
    @classmethod
    def lei_checksum(cls,value):
        expanded=''.join(str(ord(c)-55) if c.isalpha() else c for c in value)
        if int(expanded)%97!=1:raise ValueError('LEI checksum is invalid')
        return value

class Prepare(Contract):
    profileId:UUID
    strategyId:UUID
    fromDate:date
    toDate:date

    @model_validator(mode='after')
    def ordered(self):
        if self.fromDate>self.toDate:raise ValueError('Opening date must not follow closing date')
        return self

class Mapping(Contract):
    instrumentIsin:str|None=Field(default=None,pattern=r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')
    instrumentDescription:str|None=Field(default=None,min_length=1,max_length=250)
    buyerId:str|None=Field(default=None,min_length=1,max_length=100)
    sellerId:str|None=Field(default=None,min_length=1,max_length=100)
    capacity:Literal['DEAL','MTCH','AOTC']|None=None
    venueMic:str|None=Field(default=None,pattern=r'^[A-Z0-9]{4}$')
    investmentDecisionId:str|None=Field(default=None,min_length=1,max_length=100)
    executionDecisionId:str|None=Field(default=None,min_length=1,max_length=100)

class Review(Contract):
    expectedRevision:int=Field(ge=1)
    action:Literal['REPORTABLE','NOT_REPORTABLE','HOLD','AUTOMATIC','UPDATE_MAPPING']
    reason:str=Field(min_length=3,max_length=2000)
    mapping:Mapping|None=None

class Export(Prepare):
    expectedRevisions:dict[UUID,int]=Field(min_length=1)

    @field_validator('expectedRevisions')
    @classmethod
    def positive_revisions(cls,value):
        if any(v<1 for v in value.values()):raise ValueError('Revisions must be positive')
        return value
