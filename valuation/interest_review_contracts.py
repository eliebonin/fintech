"""Exact, full-population Ops review commands. Identity comes from the server."""
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator


class ReviewReconciliation(BaseModel):
    opening_balance:Decimal=Field(alias='openingBalance',max_digits=30,decimal_places=12,allow_inf_nan=False)
    closing_balance:Decimal=Field(alias='closingBalance',max_digits=30,decimal_places=12,allow_inf_nan=False)
    balance_movements:Decimal=Field(alias='balanceMovements',max_digits=30,decimal_places=12,allow_inf_nan=False)
    model_config=ConfigDict(extra='forbid',populate_by_name=True)

    @field_validator('opening_balance','closing_balance','balance_movements',mode='before')
    @classmethod
    def exact(cls,value):
        if not isinstance(value,str):raise ValueError('Send exact decimal strings')
        return value

    @field_validator('opening_balance','closing_balance','balance_movements')
    @classmethod
    def capacity(cls,value):
        if abs(value)>=Decimal('1e18'):raise ValueError('Amount exceeds the existing 18 whole-digit storage capacity')
        return value


class ReviewRow(BaseModel):
    instrument_id:UUID=Field(alias='instrumentId')
    currency_id:UUID=Field(alias='currencyId')
    amount:Decimal|None=Field(default=None,max_digits=30,decimal_places=12,allow_inf_nan=False)
    decision:Literal['ASSESSED','NOT_SUPPLIED']='ASSESSED'
    covered_days:int=Field(default=1,alias='coveredDays',ge=1,le=31)
    reason:str=Field(default='',max_length=2000)
    source_reference:str=Field(default='',alias='sourceReference',max_length=2000)
    reconciliation:ReviewReconciliation|None=None
    model_config=ConfigDict(extra='forbid',populate_by_name=True,str_strip_whitespace=True)

    @field_validator('amount',mode='before')
    @classmethod
    def exact(cls,value):
        if value is not None and not isinstance(value,str):raise ValueError('Send exact decimal strings')
        return value

    @field_validator('amount')
    @classmethod
    def capacity(cls,value):
        if value is not None and abs(value)>=Decimal('1e18'):raise ValueError('Amount exceeds the existing 18 whole-digit storage capacity')
        return value


class ReviewCommand(BaseModel):
    strategy_id:UUID=Field(alias='strategyId')
    value_date:date=Field(alias='valueDate')
    stage:Literal['DAILY','BALANCE']
    state:Literal['DRAFT','VALIDATED']
    source_hash:str=Field(alias='sourceHash',min_length=64,max_length=64)
    supersedes_review_id:UUID|None=Field(default=None,alias='supersedesReviewId')
    rows:list[ReviewRow]
    model_config=ConfigDict(extra='forbid',populate_by_name=True)

    @model_validator(mode='after')
    def unique(self):
        keys=[(r.instrument_id,r.currency_id) for r in self.rows]
        if len(keys)!=len(set(keys)):raise ValueError('Duplicate review rows')
        if self.stage=='DAILY' and any(len(row.source_reference)>500 for row in self.rows):raise ValueError('Daily source references must be at most 500 characters')
        return self
