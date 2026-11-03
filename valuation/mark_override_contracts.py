"""Exact input commands; actors, currencies and permissions come from trusted context."""
from datetime import date
from decimal import Decimal
from uuid import UUID
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator


class MarkOverrideCreate(BaseModel):
    base_batch_id:UUID=Field(alias='baseBatchId')
    input_key:str=Field(alias='inputKey',pattern='^[0-9a-f]{64}$')
    series_id:UUID=Field(alias='seriesId')
    value:Decimal=Field(max_digits=30,decimal_places=12)
    confirm_quote_basis:Literal[True]=Field(alias='confirmQuoteBasis')
    quoted_accrual_per_100:Decimal|None=Field(default=None,alias='quotedAccrualPer100',max_digits=30,decimal_places=12)
    quote_settlement_date:date|None=Field(default=None,alias='quoteSettlementDate')
    reason:str=Field(min_length=1,max_length=2000)
    source_reference:str=Field(alias='sourceReference',min_length=1,max_length=1000)
    model_config=ConfigDict(populate_by_name=True,extra='forbid',str_strip_whitespace=True)

    @field_validator('value','quoted_accrual_per_100',mode='before')
    @classmethod
    def decimals(cls,value):
        if value is not None and not isinstance(value,(str,Decimal)):raise ValueError('Use exact decimal strings')
        return value


class MarkOverrideDecision(BaseModel):
    comment:str=Field(min_length=1,max_length=2000)
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)


class MarkSeriesChoice(BaseModel):
    seriesId:UUID
    label:str
    currency:str|None
    dirtyBond:bool


class MarkGapView(BaseModel):
    inputKey:str
    subjectId:UUID
    valueDate:date
    role:str
    options:list[MarkSeriesChoice]
    notice:str|None


class MarkRequestView(BaseModel):
    requestId:UUID
    inputKey:str
    valueDate:date
    value:str
    currency:str|None
    subjectId:UUID
    reason:str
    sourceReference:str
    requestedBy:UUID
    reviewedBy:UUID|None
    reviewComment:str|None
    status:Literal['PENDING','APPROVED','REJECTED','WITHDRAWN']
    canReview:bool
    canWithdraw:bool


class MarkOverrideReviewView(BaseModel):
    gaps:list[MarkGapView]
    requests:list[MarkRequestView]
    canRequest:bool
    canReview:bool
