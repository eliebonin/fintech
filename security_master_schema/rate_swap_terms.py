"""Explicit two-leg rate exchanges; supplied whole marks, no generated cashflows."""
from datetime import date
from decimal import Decimal,localcontext,Inexact
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,Field,field_validator,model_validator

Frequency=Literal['AT_MATURITY','MONTHLY','QUARTERLY','SEMIANNUAL','ANNUAL','CUSTOM']


class RateSwapLeg(BaseModel):
    direction:Literal['PAY','RECEIVE']
    rate_reference_id:UUID=Field(alias='rateReferenceId')
    currency_id:UUID=Field(alias='currencyId')
    contractual_notional:Decimal=Field(alias='contractualNotional',gt=0,max_digits=30,decimal_places=12)
    spread:Decimal=Field(max_digits=20,decimal_places=8)
    day_count_convention_id:UUID=Field(alias='dayCountConventionId')
    interest_calculation_method:str=Field(alias='interestCalculationMethod',min_length=1,max_length=1000)
    observation_description:str=Field(alias='observationDescription',min_length=1,max_length=2000)
    reset_frequency:Frequency=Field(alias='resetFrequency')
    payment_frequency:Frequency=Field(alias='paymentFrequency')
    reset_schedule_description:str|None=Field(default=None,alias='resetScheduleDescription',max_length=2000)
    payment_schedule_description:str|None=Field(default=None,alias='paymentScheduleDescription',max_length=2000)
    model_config=dict(populate_by_name=True,extra='forbid')

    @field_validator('contractual_notional','spread',mode='before')
    @classmethod
    def exact_decimal(cls,value):
        if not isinstance(value,(str,Decimal)):raise ValueError('Use exact decimal strings, not JSON numbers')
        return value

    @field_validator('interest_calculation_method','observation_description','reset_schedule_description','payment_schedule_description')
    @classmethod
    def nonblank(cls,value):
        if value is not None:
            value=value.strip()
            if not value:raise ValueError('Nonblank sourced convention required')
        return value

    @model_validator(mode='after')
    def schedules(self):
        for frequency,evidence in ((self.reset_frequency,self.reset_schedule_description),(self.payment_frequency,self.payment_schedule_description)):
            if (frequency=='CUSTOM')!=(evidence is not None):raise ValueError('Custom frequency requires its sourced schedule description')
        return self


class RateSwapTerms(BaseModel):
    schema_version:Literal[1]=Field(default=1,alias='schemaVersion')
    swap_kind:Literal['RATE_EXCHANGE']=Field(alias='swapKind')
    tenant_identifier:str|None=Field(default=None,alias='tenantIdentifier',min_length=1,max_length=100)
    contractual_notional:Decimal=Field(alias='contractualNotional',gt=0,max_digits=30,decimal_places=12)
    notional_currency_id:UUID=Field(alias='notionalCurrencyId')
    quantity_unit:Literal['NOMINAL','UNITS']=Field(default='NOMINAL',alias='quantityUnit')
    contractual_units:Decimal|None=Field(default=None,alias='contractualUnits',gt=0,max_digits=30,decimal_places=12,exclude_if=lambda v:v is None)
    notional_per_unit:Decimal|None=Field(default=None,alias='notionalPerUnit',gt=0,max_digits=30,decimal_places=12,exclude_if=lambda v:v is None)
    quote_currency_id:UUID=Field(alias='quoteCurrencyId')
    quote_factor:Decimal=Field(alias='quoteFactor',gt=0,max_digits=20,decimal_places=8)
    effective_date:date=Field(alias='effectiveDate')
    maturity_date:date=Field(alias='maturityDate')
    source_reference:str=Field(alias='sourceReference',min_length=1,max_length=1000)
    principal_exchange:Literal['NONE','INITIAL_FINAL','FINAL','CUSTOM','UNSPECIFIED']=Field(alias='principalExchange')
    principal_exchange_description:str|None=Field(default=None,alias='principalExchangeDescription',max_length=2000)
    legs:list[RateSwapLeg]=Field(min_length=2,max_length=2)
    model_config=dict(populate_by_name=True,extra='forbid')

    @field_validator('contractual_notional','contractual_units','notional_per_unit','quote_factor',mode='before')
    @classmethod
    def exact_decimal(cls,value):
        if value is not None and not isinstance(value,(str,Decimal)):raise ValueError('Use exact decimal strings, not JSON numbers')
        return value

    @field_validator('source_reference','principal_exchange_description')
    @classmethod
    def nonblank(cls,value):
        if value is not None:
            value=value.strip()
            if not value:raise ValueError('Nonblank source evidence required')
        return value

    @field_validator('tenant_identifier',mode='before')
    @classmethod
    def identifier(cls,value):return value.strip() or None if isinstance(value,str) else value

    @model_validator(mode='after')
    def contract(self):
        if {leg.direction for leg in self.legs}!={'PAY','RECEIVE'}:raise ValueError('Two opposing pay/receive rate legs required')
        if self.maturity_date<=self.effective_date:raise ValueError('Maturity must follow effective date')
        if self.quote_currency_id!=self.notional_currency_id:raise ValueError('Whole-swap quote must use the booked-notional basis currency')
        if self.quantity_unit=='UNITS':
            if self.contractual_units is None or self.notional_per_unit is None:raise ValueError('Unit-based swaps require contractual units and reference notional per unit')
            with localcontext() as ctx:
                ctx.prec=512;ctx.traps[Inexact]=True
                if self.contractual_units*self.notional_per_unit!=self.contractual_notional:raise ValueError('Units and reference notional must reconcile')
        elif self.contractual_units is not None or self.notional_per_unit is not None:raise ValueError('Nominal swaps do not have contractual unit factors')
        if self.principal_exchange in ('CUSTOM','UNSPECIFIED') and self.principal_exchange_description is None:raise ValueError('Custom or unassessed principal exchange requires explicit evidence')
        return self

    def booked_reference_notional(self,quantity:Decimal)->Decimal:
        with localcontext() as ctx:
            ctx.prec=512;ctx.traps[Inexact]=True
            return quantity*self.notional_per_unit if self.quantity_unit=='UNITS' else quantity

    def leg_notional(self,leg:RateSwapLeg,quantity:Decimal)->Decimal:
        with localcontext() as ctx:
            ctx.prec=512;ctx.traps[Inexact]=True
            return leg.contractual_notional*self.booked_reference_notional(quantity)/self.contractual_notional


def assert_materialized(terms,stored,legs):
    category='CROSS_CURRENCY' if len({leg.currency_id for leg in terms.legs})>1 else 'INTEREST_RATE'
    if len(stored)!=1 or stored[0]['swap_type']!=category or len(legs)!=2:raise ValueError('Rate-swap category/legs differ from approved terms')
    by_number={leg['leg_number']:leg for leg in legs}
    for number,expected in enumerate(terms.legs,1):
        actual=by_number.get(number)
        if actual is None or any((actual['leg_role']!='FUNDING',actual['pay_receive']!=expected.direction,
            str(actual['reference_node_id'])!=str(expected.rate_reference_id),str(actual['currency_id'])!=str(expected.currency_id),
            Decimal(str(actual['spread']))!=expected.spread,actual['return_profile_id'] is not None,actual['schedule_id'] is not None)):
            raise ValueError('Canonical floating leg differs from approved rate-exchange terms')
