# Shared booking convention foundation; no HTTP or repository imports.
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, StrictBool, field_validator, model_validator


class ConventionBase(BaseModel):
    effective_from: date = Field(alias='effectiveFrom')
    price_currency_id: UUID = Field(alias='priceCurrencyId')
    quote_factor: Decimal = Field(alias='quoteFactor', gt=0, max_digits=20, decimal_places=8)
    source_reference: str = Field(alias='sourceReference', min_length=1, max_length=1000)
    model_config = dict(populate_by_name=True, extra='forbid')

    @field_validator('source_reference')
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError('Source evidence is required.')
        return value.strip()


class FutureConvention(ConventionBase):
    kind: Literal['FUTURE']
    quantity_unit: Literal['CONTRACTS'] = Field(alias='quantityUnit')
    price_basis: Literal['INDEX_POINTS', 'UNDERLYING_UNIT'] = Field(alias='priceBasis')
    settlement_method: Literal['CASH', 'PHYSICAL'] = Field(default='CASH', alias='settlementMethod')
    contract_size: Decimal | None = Field(default=None, alias='contractSize', gt=0, max_digits=30, decimal_places=12)
    contract_size_currency_id: UUID | None = Field(default=None, alias='contractSizeCurrencyId')
    delivery_start_date: date | None = Field(default=None, alias='deliveryStartDate')
    delivery_end_date: date | None = Field(default=None, alias='deliveryEndDate')
    monetary_multiplier: Decimal = Field(alias='monetaryMultiplier', gt=0, max_digits=30, decimal_places=12)
    tick_size: Decimal = Field(alias='tickSize', gt=0, max_digits=20, decimal_places=8)
    allow_negative_price: StrictBool = Field(alias='allowNegativePrice')
    last_trading_at_utc: datetime = Field(alias='lastTradingAtUtc')
    final_settlement_date: date = Field(alias='finalSettlementDate')

    @model_validator(mode='after')
    def dates(self):
        if self.price_basis == 'UNDERLYING_UNIT' and (self.contract_size is None or self.contract_size_currency_id is None or self.contract_size != self.monetary_multiplier):
            raise ValueError('Linear underlying-unit quotes require the sourced contract size as price multiplier.')
        if self.price_basis == 'INDEX_POINTS' and (self.settlement_method != 'CASH' or self.contract_size is not None or self.contract_size_currency_id is not None):
            raise ValueError('Index-point futures cannot claim physical asset delivery.')
        if self.last_trading_at_utc.tzinfo is None or self.last_trading_at_utc.utcoffset() is None:
            raise ValueError('Last trading cutoff needs a timezone.')
        if not self.effective_from <= self.last_trading_at_utc.astimezone(timezone.utc).date() <= self.final_settlement_date:
            raise ValueError('Effective date, cutoff and final settlement must be ordered.')
        if self.settlement_method == 'PHYSICAL':
            if not self.delivery_start_date or not self.delivery_end_date or not self.last_trading_at_utc.astimezone(timezone.utc).date() <= self.delivery_start_date <= self.delivery_end_date or self.final_settlement_date != self.delivery_end_date:
                raise ValueError('Physical delivery needs an ordered delivery window ending on final settlement.')
        elif self.delivery_start_date is not None or self.delivery_end_date is not None:
            raise ValueError('Cash settlement has no physical delivery window.')
        return self
