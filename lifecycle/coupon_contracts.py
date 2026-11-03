"""Explicit bond cashflows and coupon confirmations, never inferred income."""
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',populate_by_name=True,str_strip_whitespace=True)


class BondCashflow(Strict):
    cashflow_key:str=Field(alias='cashflowKey',min_length=1,max_length=100)
    cashflow_type:Literal['COUPON','PRINCIPAL']=Field(alias='cashflowType')
    accrual_start:date|None=Field(default=None,alias='accrualStart')
    accrual_end:date|None=Field(default=None,alias='accrualEnd')
    payment_date:date=Field(alias='paymentDate')
    record_date:date|None=Field(default=None,alias='recordDate')
    ex_date:date|None=Field(default=None,alias='exDate')
    coupon_rate:Decimal|None=Field(default=None,alias='couponRate',max_digits=20,decimal_places=12,allow_inf_nan=False)
    amount_per_100:Decimal|None=Field(default=None,alias='amountPer100',max_digits=30,decimal_places=12,allow_inf_nan=False)
    amount_formula:str|None=Field(default=None,alias='amountFormula',min_length=1,max_length=2000)

    @field_validator('coupon_rate','amount_per_100',mode='before')
    @classmethod
    def exact(cls,value):
        if value is not None and not isinstance(value,str): raise ValueError('Send exact decimal strings')
        return value

    @model_validator(mode='after')
    def contractual(self):
        if self.cashflow_type=='PRINCIPAL':
            if any(x is not None for x in (self.accrual_start,self.accrual_end,self.record_date,self.ex_date,self.coupon_rate)):
                raise ValueError('Principal cashflows must not contain coupon-period metadata')
            if self.amount_per_100 is not None and self.amount_per_100<=0:
                raise ValueError('Principal repayment amount must be positive')
            if self.amount_per_100 is None and self.amount_formula is None:
                raise ValueError('Provide a sourced principal amount per 100 or formula')
            return self
        if (self.accrual_start is None or self.accrual_end is None
                or self.accrual_end<=self.accrual_start or self.payment_date<self.accrual_start):
            raise ValueError('Ordered accrual period and explicit payment date required')
        if all(x is None for x in (self.coupon_rate,self.amount_per_100,self.amount_formula)):
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
    cashflows:list[BondCashflow]=Field(min_length=1,max_length=500)
    confirm_schedule:Literal[True]=Field(alias='confirmSchedule')

    @model_validator(mode='after')
    def coherent(self):
        keys=[r.cashflow_key for r in self.cashflows]
        if len(set(keys))!=len(keys): raise ValueError('Unique cashflow keys required')
        coupons=sorted((r for r in self.cashflows if r.cashflow_type=='COUPON'),key=lambda r:r.accrual_start)
        if any(a.accrual_end>b.accrual_start for a,b in zip(coupons,coupons[1:])):
            raise ValueError('Coupon periods must be non-overlapping')
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
