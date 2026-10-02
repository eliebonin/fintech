"""Closed, typed contracts for funded securities, index futures and plain bonds."""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, Field, StrictBool, field_validator, model_validator
from .contracts import TradeBookingRequest, ApiMeta


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


class StructuredConvention(ConventionBase):
    kind: Literal['STRUCTURED_PRODUCT']
    funding: Literal['FULLY_FUNDED']
    quantity_unit: Literal['UNITS', 'NOMINAL'] = Field(alias='quantityUnit')
    price_basis: Literal['UNIT_PRICE', 'PCT_OF_PAR'] = Field(alias='priceBasis')
    denomination: Decimal | None = Field(default=None, gt=0, max_digits=30, decimal_places=12)
    quantity_minimum: Decimal = Field(alias='quantityMinimum', gt=0, max_digits=30, decimal_places=12)
    quantity_increment: Decimal = Field(alias='quantityIncrement', gt=0, max_digits=30, decimal_places=12)
    accrual: Literal['NONE', 'DIRTY']
    otc_allowed: StrictBool = Field(alias='otcAllowed')

    @model_validator(mode='after')
    def conventions(self):
        if self.price_basis == 'UNIT_PRICE' and self.quantity_unit != 'UNITS':
            raise ValueError('Monetary unit prices require unit quantities.')
        if self.price_basis == 'PCT_OF_PAR':
            if self.quote_factor != 100: raise ValueError('Percentage quotes use divisor 100.')
            if self.quantity_unit == 'UNITS' and self.denomination is None:
                raise ValueError('A denomination is required for unit percentage quotes.')
        return self


class FutureFamilySpecification(BaseModel):
    underlying_kind: Literal['INDEX', 'CRYPTOASSET'] = Field(alias='underlyingKind')
    symbol_root: str = Field(alias='symbolRoot', min_length=1, max_length=30, pattern='^[A-Z0-9]+$')
    year_digits: Literal[1, 2] = Field(alias='yearDigits')
    delivery_months: list[int] = Field(alias='deliveryMonths', min_length=1, max_length=12)
    settlement_method: Literal['CASH', 'PHYSICAL'] = Field(alias='settlementMethod')
    price_basis: Literal['INDEX_POINTS', 'UNDERLYING_UNIT'] = Field(alias='priceBasis')
    contract_size: Decimal | None = Field(default=None, alias='contractSize', gt=0, max_digits=30, decimal_places=12)
    contract_size_currency_id: UUID | None = Field(default=None, alias='contractSizeCurrencyId')
    monetary_multiplier: Decimal = Field(alias='monetaryMultiplier', gt=0, max_digits=30, decimal_places=12)
    quote_factor: Decimal = Field(alias='quoteFactor', gt=0, max_digits=20, decimal_places=8)
    tick_size: Decimal = Field(alias='tickSize', gt=0, max_digits=20, decimal_places=8)
    allow_negative_price: StrictBool = Field(alias='allowNegativePrice')
    model_config = dict(populate_by_name=True, extra='forbid')

    @model_validator(mode='after')
    def coherent(self):
        if len(set(self.delivery_months)) != len(self.delivery_months) or any(not 1 <= n <= 12 for n in self.delivery_months):
            raise ValueError('Delivery months must be distinct calendar months 1 to 12.')
        if self.underlying_kind == 'INDEX':
            if self.price_basis != 'INDEX_POINTS' or self.settlement_method != 'CASH' or self.contract_size is not None or self.contract_size_currency_id is not None:
                raise ValueError('Index families use cash settlement and currency per index point, not physical units.')
        elif self.price_basis != 'UNDERLYING_UNIT' or self.contract_size is None or self.contract_size_currency_id is None or self.contract_size != self.monetary_multiplier:
            raise ValueError('Linear crypto families require asset units per contract and an equal price multiplier.')
        self.delivery_months = sorted(self.delivery_months)
        return self


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


class BondConvention(ConventionBase):
    kind: Literal['BOND']
    quantity_unit: Literal['NOMINAL'] = Field(alias='quantityUnit')
    price_basis: Literal['PCT_OF_PAR'] = Field(alias='priceBasis')
    principal_basis: Literal['UNADJUSTED_NOMINAL'] = Field(alias='principalBasis')
    quantity_minimum: Decimal = Field(alias='quantityMinimum', gt=0, max_digits=30, decimal_places=12)
    quantity_increment: Decimal = Field(alias='quantityIncrement', gt=0, max_digits=30, decimal_places=12)
    accrual: Literal['MANUAL_CONFIRMATION']
    otc_allowed: StrictBool = Field(alias='otcAllowed')

    @model_validator(mode='after')
    def percentage(self):
        if self.quote_factor != 100: raise ValueError('Bond percentage quotes use divisor 100.')
        return self


BookingConvention = Annotated[StructuredConvention | FutureConvention | BondConvention, Field(discriminator='kind')]


class ConventionProposalRequest(BaseModel):
    instrument_id: UUID = Field(alias='instrumentId')
    convention: BookingConvention
    model_config = dict(populate_by_name=True, extra='forbid')


class FutureFamilyProposalRequest(BaseModel):
    canonical_name: str = Field(alias='canonicalName', min_length=1, max_length=250)
    family_code: str = Field(alias='familyCode', min_length=1, max_length=80, pattern='^[A-Z0-9_]+$')
    underlying_id: UUID = Field(alias='underlyingId')
    contract_currency_id: UUID = Field(alias='contractCurrencyId')
    source_reference: str = Field(alias='sourceReference', min_length=1, max_length=1000)
    specification: FutureFamilySpecification | None = None
    model_config = dict(populate_by_name=True, extra='forbid')

    @field_validator('canonical_name', 'source_reference')
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError('A nonblank value is required.')
        return value.strip()


class FutureFamilyView(BaseModel):
    family_id: UUID = Field(alias='familyId')
    family_node_id: UUID = Field(alias='familyNodeId')
    family_code: str = Field(alias='familyCode')
    canonical_name: str = Field(alias='canonicalName')
    underlying_id: UUID = Field(alias='underlyingId')
    underlying_name: str = Field(alias='underlyingName')
    contract_currency_id: UUID = Field(alias='contractCurrencyId')
    currency: str
    specification: FutureFamilySpecification | None = None
    model_config = dict(populate_by_name=True)


class FutureFamilySearchResponse(BaseModel):
    data: list[FutureFamilyView]
    meta: ApiMeta


class FutureProposalRequest(BaseModel):
    canonical_name: str = Field(alias='canonicalName', min_length=1, max_length=250)
    family_code: str = Field(alias='familyCode', min_length=1, max_length=80, pattern='^[A-Z0-9_]+$')
    family_id: UUID | None = Field(default=None, alias='familyId')
    underlying_id: UUID = Field(alias='underlyingId')
    contract_month: date = Field(alias='contractMonth')
    convention: FutureConvention
    model_config = dict(populate_by_name=True, extra='forbid')


class ProductBookingRequest(TradeBookingRequest):
    price_type: Literal['CLEAN', 'DIRTY'] | None = Field(default=None, alias='priceType')
    accrued_interest_amount: Decimal | None = Field(default=None, alias='accruedInterestAmount', max_digits=30, decimal_places=12)
    settlement_evidence: str | None = Field(default=None, alias='settlementEvidence', min_length=1, max_length=1000)
    instrument_id: UUID = Field(alias='instrumentId')
    listing_id: UUID | None = Field(default=None, alias='listingId')
    execution_route: Literal['LISTED', 'OTC'] = Field(alias='executionRoute')
    execution_price: Decimal = Field(alias='executionPrice', max_digits=30, decimal_places=12)
    quantity: Decimal = Field(gt=0, max_digits=30, decimal_places=12)
    settlement_date: date | None = Field(default=None, alias='settlementDate')
    position_effect: Literal['OPEN', 'CLOSE'] | None = Field(default=None, alias='positionEffect')
    expected_terms_fingerprint: str = Field(alias='expectedTermsFingerprint', pattern='^[0-9a-f]{64}$')

    @field_validator('settlement_evidence')
    @classmethod
    def trim_evidence(cls, value):
        return value.strip() if value is not None else None

    @model_validator(mode='after')
    def _validate_dates_and_timezone(self):
        self._validate_annotations()
        original = self.settlement_date
        if self.trade_datetime.tzinfo is None or self.trade_datetime.utcoffset() is None:
            raise ValueError('tradeDatetime must include a timezone offset')
        if original and original < self.trade_datetime.astimezone(timezone.utc).date():
            raise ValueError('Settlement cannot precede execution.')
        if self.execution_route == 'LISTED' and not self.listing_id:
            raise ValueError('Listed execution requires a listing.')
        if self.execution_route == 'OTC' and self.listing_id:
            raise ValueError('This alpha selects OTC conventions on the instrument, without a reference listing.')
        return self


class ProductBookingContextView(BaseModel):
    instrument_id: UUID = Field(alias='instrumentId')
    name: str
    kind: Literal['STRUCTURED_PRODUCT', 'FUTURE', 'BOND']
    coupon_type: str | None = Field(default=None, alias='couponType')
    coupon_rate: Decimal | None = Field(default=None, alias='couponRate')
    coupon_frequency: int | None = Field(default=None, alias='couponFrequency')
    day_count_convention: str | None = Field(default=None, alias='dayCountConvention')
    listing_id: UUID | None = Field(default=None, alias='listingId')
    listing_name: str | None = Field(default=None, alias='listingName')
    execution_route: Literal['LISTED', 'OTC'] = Field(alias='executionRoute')
    currency: str | None = None
    convention: BookingConvention | None = None
    terms_fingerprint: str | None = Field(default=None, alias='termsFingerprint')
    booking_eligible: bool = Field(default=False, alias='bookingEligible')
    ineligibility_message: str | None = Field(default=None, alias='ineligibilityMessage')
    contract_month: date | None = Field(default=None, alias='contractMonth')
    underlying_id: UUID | None = Field(default=None, alias='underlyingId')
    underlying_name: str | None = Field(default=None, alias='underlyingName')
    listing_unit_multiplier: Decimal | None = Field(default=None, alias='listingUnitMultiplier')
    maturity_date: date | None = Field(default=None, alias='maturityDate')
    model_config = dict(populate_by_name=True)


class ProductBookingContextResponse(BaseModel):
    data: ProductBookingContextView
    meta: ApiMeta


class ProductBookingSearchResponse(BaseModel):
    data: list[ProductBookingContextView]
    meta: ApiMeta


class BondTradeDetailsView(BaseModel):
    price_type: Literal['CLEAN', 'DIRTY'] = Field(alias='priceType')
    clean_amount: str = Field(alias='cleanAmount')
    dirty_amount: str = Field(alias='dirtyAmount')
    accrued_interest_amount: str = Field(alias='accruedInterestAmount')
    settlement_evidence: str = Field(alias='settlementEvidence')
    model_config = dict(populate_by_name=True, extra='forbid')


class ProductTradeEconomicsView(BaseModel):
    bond_details: BondTradeDetailsView | None = Field(default=None, alias='bondDetails')
    terms: ProductBookingContextView
    amount: str
    amount_kind: Literal['CONSIDERATION', 'REFERENCE_CONTRACT_VALUE'] = Field(alias='amountKind')
    direction: Literal['PAY', 'RECEIVE'] | None = None
    model_config = dict(populate_by_name=True)
