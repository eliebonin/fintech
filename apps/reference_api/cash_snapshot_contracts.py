"""Exact dated cash snapshots, not trades or cash movements."""
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator


class CashAccountCreate(BaseModel):
    strategy_id: UUID=Field(alias='strategyId')
    company_id: UUID=Field(alias='companyId')
    label: str=Field(min_length=1,max_length=100)
    account_type: Literal['CUSTODY','BANK','BROKER','EXCHANGE','MARGIN']=Field(alias='accountType')
    model_config=ConfigDict(extra='forbid',populate_by_name=True,str_strip_whitespace=True)


class CashSnapshotRow(BaseModel):
    account_id: UUID=Field(alias='accountId')
    currency_id: UUID=Field(alias='currencyId')
    value_date: date=Field(alias='valueDate')
    amount: Decimal=Field(max_digits=30,decimal_places=12,allow_inf_nan=False)
    source_reference: str=Field(alias='sourceReference',min_length=1,max_length=500)
    note: str | None=Field(default=None,max_length=2000)
    expected_revision: int=Field(default=0,alias='expectedRevision',ge=0)
    correction_reason: str | None=Field(default=None,alias='correctionReason',min_length=1,max_length=2000)
    model_config=ConfigDict(extra='forbid',populate_by_name=True,str_strip_whitespace=True)

    @field_validator('amount',mode='before')
    @classmethod
    def exact(cls,value):
        if not isinstance(value,str): raise ValueError('Use exact decimal strings, not floating-point amounts')
        return value

    @model_validator(mode='after')
    def dated(self):
        if self.value_date>date.today(): raise ValueError('Future EoD balances are not supported')
        if self.expected_revision and not self.correction_reason: raise ValueError('Corrections require a separate reason')
        return self


class CashUpload(BaseModel):
    strategy_id: UUID=Field(alias='strategyId')
    rows: list[CashSnapshotRow]=Field(min_length=1,max_length=500)
    model_config=ConfigDict(extra='forbid',populate_by_name=True)

    @model_validator(mode='after')
    def unique_rows(self):
        keys=[(r.account_id,r.currency_id,r.value_date) for r in self.rows]
        if len(keys)!=len(set(keys)): raise ValueError('Duplicate account/currency/date rows in upload')
        return self


class CashPreview(BaseModel):
    strategy_id: UUID=Field(alias='strategyId')
    value_date: date=Field(alias='valueDate')
    policy_id: UUID=Field(alias='policyId')
    cut_id: UUID=Field(alias='cutId')
    reporting_currency_id: UUID=Field(alias='reportingCurrencyId')
    model_config=ConfigDict(extra='forbid',populate_by_name=True)
