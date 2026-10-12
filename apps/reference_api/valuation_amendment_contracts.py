"""Typed signed component deltas; source corrections are a separate calculation."""
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,field_validator


class ComponentChange(BaseModel):
    attribution_id: UUID=Field(alias='attributionId')
    component: Literal['ADJUSTMENT','DIVIDEND','RESET','CASHFLOW','BROKER_FEE','CUSTODY_FEE','MANAGEMENT_FEE','PERFORMANCE_FEE','TAX','OTHER_COST']
    amount: Decimal=Field(max_digits=30,decimal_places=12,allow_inf_nan=False)
    reason: str=Field(min_length=1,max_length=2000)
    source_reference: str=Field(alias='sourceReference',min_length=1,max_length=500)
    model_config=ConfigDict(extra='forbid',populate_by_name=True,str_strip_whitespace=True)

    @field_validator('amount',mode='before')
    @classmethod
    def exact_amount(cls,value):
        if not isinstance(value,str): raise ValueError('Send an exact decimal string')
        return value
