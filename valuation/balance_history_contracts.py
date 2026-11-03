"""Exact local stock curation and explicit history maintenance commands."""
from datetime import date,datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator


class BalanceInputCreate(BaseModel):
    strategy_id:UUID=Field(alias='strategyId')
    instrument_id:UUID=Field(alias='instrumentId')
    currency_id:UUID=Field(alias='currencyId')
    value_date:date=Field(alias='valueDate')
    closing_balance:Decimal|None=Field(default=None,alias='closingBalance',max_digits=30,decimal_places=12,allow_inf_nan=False)
    status:Literal['ACTIVE','WITHDRAWN']='ACTIVE'
    source_reference:str=Field(alias='sourceReference',min_length=1,max_length=2000)
    reason:str=Field(min_length=1,max_length=2000)
    supersedes_input_id:UUID|None=Field(default=None,alias='supersedesInputId')
    model_config=ConfigDict(populate_by_name=True,extra='forbid',str_strip_whitespace=True)

    @field_validator('closing_balance',mode='before')
    @classmethod
    def exact(cls,value):
        if value is not None and not isinstance(value,str):raise ValueError('Send an exact decimal string')
        return value

    @model_validator(mode='after')
    def valid_stock(self):
        if self.status=='ACTIVE' and self.closing_balance is None:raise ValueError('An assessed closing balance is required')
        if self.status=='WITHDRAWN' and (self.closing_balance is not None or not self.supersedes_input_id):raise ValueError('Withdraw the current revision without a replacement amount')
        return self


class BalanceHistoryRefresh(BaseModel):
    strategy_id:UUID=Field(alias='strategyId')
    from_date:date=Field(alias='fromDate')
    to_date:date=Field(alias='toDate')
    information_cutoff:datetime|None=Field(default=None,alias='informationCutoff')
    model_config=ConfigDict(populate_by_name=True,extra='forbid')

    @model_validator(mode='after')
    def ordered(self):
        if self.from_date==date.min:raise ValueError('The update requires a preceding opening-balance date')
        if self.to_date<self.from_date or (self.to_date-self.from_date).days>366:raise ValueError('Choose an ordered update interval of at most 366 days; all contributing history is still read')
        if self.information_cutoff is not None and self.information_cutoff.utcoffset() is None:raise ValueError('Information cutoff must include its UTC offset')
        return self
