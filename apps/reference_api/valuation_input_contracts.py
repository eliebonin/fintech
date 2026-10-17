"""Source-neutral assessed daily interest, not a generic bond pricing model."""
from datetime import date
from decimal import Decimal
from uuid import UUID
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator


class AccrualCreate(BaseModel):
    strategy_id: UUID=Field(alias='strategyId')
    instrument_id: UUID=Field(alias='instrumentId')
    value_date: date=Field(alias='valueDate')
    currency_id: UUID | None=Field(default=None,alias='currencyId')
    policy_id: UUID | None=Field(default=None,alias='policyId')
    cut_id: UUID | None=Field(default=None,alias='cutId')
    reporting_currency_id: UUID | None=Field(default=None,alias='reportingCurrencyId')
    opening_balance: Decimal | None=Field(default=None,alias='openingBalance',max_digits=30,decimal_places=12,allow_inf_nan=False)
    daily_earned: Decimal=Field(alias='dailyEarned',max_digits=30,decimal_places=12,allow_inf_nan=False)
    closing_balance: Decimal | None=Field(default=None,alias='closingBalance',max_digits=30,decimal_places=12,allow_inf_nan=False)
    balance_movements: Decimal | None=Field(default=None,alias='balanceMovements',max_digits=30,decimal_places=12,allow_inf_nan=False)
    eligible_nominal: Decimal | None=Field(default=None,alias='eligibleNominal',max_digits=30,decimal_places=12,allow_inf_nan=False)
    source_reference: str | None=Field(default=None,alias='sourceReference',min_length=1,max_length=500)
    eligibility_convention: str | None=Field(default=None,alias='eligibilityConvention',min_length=1,max_length=250)
    supersedes_input_id: UUID | None=Field(default=None,alias='supersedesInputId')
    model_config=ConfigDict(extra='forbid',populate_by_name=True,str_strip_whitespace=True)

    @field_validator('opening_balance','daily_earned','closing_balance','balance_movements','eligible_nominal',mode='before')
    @classmethod
    def decimal_strings(cls,value):
        if value is None: return value
        if not isinstance(value,str): raise ValueError('Send exact decimal strings, not binary floating-point amounts')
        return value

    @model_validator(mode='after')
    def complete_optional_balance(self):
        balances=(self.opening_balance,self.closing_balance,self.balance_movements)
        if any(v is not None for v in balances):
            if any(v is None for v in balances) or not all((self.policy_id,self.cut_id,self.reporting_currency_id)):
                raise ValueError('Balance reconciliation requires all balances/movements and pricing context')
        elif self.currency_id is None:
            raise ValueError('Daily-only interest requires an explicit currencyId')
        return self


class EconomicFlowCreate(BaseModel):
    strategy_id: UUID=Field(alias='strategyId')
    instrument_id: UUID=Field(alias='instrumentId')
    currency_id: UUID=Field(alias='currencyId')
    economic_date: date=Field(alias='economicDate')
    payment_date: date | None=Field(default=None,alias='paymentDate')
    amount: Decimal=Field(max_digits=30,decimal_places=12,allow_inf_nan=False)
    component: Literal['DIVIDEND','RESET','COUPON','CASHFLOW','BROKER_FEE','CUSTODY_FEE','MANAGEMENT_FEE','PERFORMANCE_FEE','TAX','OTHER_COST']
    recognition_role: Literal['INCOME','PAYMENT_ONLY']=Field(alias='recognitionRole')
    source_reference: str=Field(alias='sourceReference',min_length=1,max_length=500)
    model_config=ConfigDict(extra='forbid',populate_by_name=True,str_strip_whitespace=True)

    @field_validator('amount',mode='before')
    @classmethod
    def decimal_strings(cls,value):
        if not isinstance(value,str): raise ValueError('Send an exact decimal string')
        return value


class EconomicFlowCancel(BaseModel):
    reason: str=Field(min_length=1,max_length=2000)
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
