"""Explicit sourced coupon dates/economics, never inferred earnings or cash."""
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',populate_by_name=True,str_strip_whitespace=True)


class CouponPeriod(Strict):
    coupon_key:str=Field(alias='couponKey',min_length=1,max_length=100)
    accrual_start:date=Field(alias='accrualStart')
    accrual_end:date=Field(alias='accrualEnd')
    payment_date:date=Field(alias='paymentDate')
    record_date:date|None=Field(default=None,alias='recordDate')
    ex_date:date|None=Field(default=None,alias='exDate')
    coupon_rate:Decimal|None=Field(default=None,alias='couponRate',max_digits=20,decimal_places=12,allow_inf_nan=False)
    amount_per_100:Decimal|None=Field(default=None,alias='amountPer100',max_digits=30,decimal_places=12,allow_inf_nan=False)
    rate_formula:str|None=Field(default=None,alias='rateFormula',min_length=1,max_length=2000)

    @field_validator('coupon_rate','amount_per_100',mode='before')
    @classmethod
    def exact(cls,value):
        if value is not None and not isinstance(value,str): raise ValueError('Send exact decimal strings')
        return value

    @model_validator(mode='after')
    def contractual(self):
        if self.accrual_end<=self.accrual_start or self.payment_date<self.accrual_start:
            raise ValueError('Ordered accrual period and explicit payment date required')
        if all(x is None for x in (self.coupon_rate,self.amount_per_100,self.rate_formula)):
            raise ValueError('Provide a sourced rate, amount per 100, or formula; unknown is not zero')
        return self


class ScheduleCreate(Strict):
    instrument_id:UUID=Field(alias='instrumentId')
    expected_revision:int=Field(alias='expectedRevision',ge=0,strict=True)
    source_reference:str=Field(alias='sourceReference',min_length=1,max_length=2000)
    reason:str=Field(min_length=1,max_length=2000)
    calendar_id:UUID|None=Field(default=None,alias='calendarId')
    day_count_convention_id:UUID|None=Field(default=None,alias='dayCountConventionId')
    business_day_convention:Literal['UNADJUSTED','FOLLOWING','MODIFIED_FOLLOWING','PRECEDING','MODIFIED_PRECEDING']|None=Field(default=None,alias='businessDayConvention')
    periods:list[CouponPeriod]=Field(min_length=1,max_length=500)
    confirm_schedule:Literal[True]=Field(alias='confirmSchedule')

    @model_validator(mode='after')
    def coherent(self):
        keys=[r.coupon_key for r in self.periods]
        if len(set(keys))!=len(keys): raise ValueError('Unique coupon keys required')
        if any(a.accrual_end>b.accrual_start for a,b in zip(self.periods,self.periods[1:])):
            raise ValueError('Periods must be ordered and non-overlapping')
        return self


class PaymentCreate(Strict):
    strategy_id:UUID=Field(alias='strategyId')
    period_id:UUID=Field(alias='periodId')
    payment_date:date=Field(alias='paymentDate')
    amount:Decimal=Field(max_digits=30,decimal_places=12,allow_inf_nan=False)
    currency_id:UUID=Field(alias='currencyId')
    cash_account_id:UUID|None=Field(default=None,alias='cashAccountId')
    source_reference:str=Field(alias='sourceReference',min_length=1,max_length=2000)
    note:str=Field(default='',max_length=2000)
    supersedes_payment_id:UUID|None=Field(default=None,alias='supersedesPaymentId')
    confirm_payment:Literal[True]=Field(alias='confirmPayment')

    @field_validator('amount',mode='before')
    @classmethod
    def exact(cls,value):
        if not isinstance(value,str): raise ValueError('Send an exact decimal string')
        return value

    @field_validator('amount')
    @classmethod
    def nonzero(cls,value):
        if not value: raise ValueError('A payment confirmation requires a nonzero amount')
        return value


class PaymentReverse(Strict):
    strategy_id:UUID=Field(alias='strategyId')
    payment_id:UUID=Field(alias='paymentId')
    reason:str=Field(min_length=1,max_length=2000)
    confirm_payment:Literal[True]=Field(alias='confirmPayment')
