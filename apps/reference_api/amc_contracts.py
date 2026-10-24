"""Governed AMC creation envelope; no fund-specific identity or NAV defaults."""
from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from .product_booking_contracts import AmcConvention


class AmcProposalRequest(BaseModel):
    canonical_name: str = Field(alias='canonicalName',min_length=1,max_length=250)
    isin: str | None = Field(default=None,min_length=12,max_length=12,pattern='^[A-Z]{2}[A-Z0-9]{9}[0-9]$')
    issuer_organisation_id: UUID = Field(alias='issuerOrganisationId')
    adviser_organisation_id: UUID | None = Field(default=None,alias='adviserOrganisationId')
    reference_node_id: UUID | None = Field(default=None,alias='referenceNodeId')
    base_currency_id: UUID = Field(alias='baseCurrencyId')
    effective_from: date = Field(alias='effectiveFrom')
    maturity_date: date | None = Field(default=None,alias='maturityDate')
    redemption_model: Literal['OPEN_ENDED','FIXED_MATURITY','ISSUER_REDEEMABLE','UNKNOWN'] = Field(alias='redemptionModel')
    distribution_policy: Literal['ACCUMULATING','DISTRIBUTING','NONE','UNKNOWN'] = Field(alias='distributionPolicy')
    collateralisation_type: Literal['SECURED','UNSECURED','UNKNOWN'] = Field(default='UNKNOWN',alias='collateralisationType')
    strategy_description: str | None = Field(default=None,alias='strategyDescription',max_length=4000)
    fee_description: str | None = Field(default=None,alias='feeDescription',max_length=4000)
    pricing_frequency: Literal['DAILY','WEEKLY','MONTHLY','INTRADAY','AD_HOC'] | None = Field(default=None,alias='pricingFrequency')
    publication_lag_business_days: int | None = Field(default=None,alias='publicationLagBusinessDays',ge=0,le=366)
    source_reference: str = Field(alias='sourceReference',min_length=1,max_length=1000)
    convention: AmcConvention
    idempotency_key: str = Field(alias='idempotencyKey',min_length=1,max_length=255)
    model_config = dict(populate_by_name=True,extra='forbid')

    @field_validator('canonical_name','source_reference','idempotency_key')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('A nonblank value is required')
        return value.strip()

    @model_validator(mode='after')
    def coherent(self):
        if self.convention.price_currency_id!=self.base_currency_id or self.convention.effective_from!=self.effective_from:
            raise ValueError('Convention currency and start must agree with the AMC')
        if self.maturity_date and self.maturity_date<=self.effective_from:
            raise ValueError('Maturity must follow effective date')
        if self.redemption_model=='FIXED_MATURITY' and not self.maturity_date:
            raise ValueError('Fixed maturity requires a maturity date')
        if self.redemption_model=='OPEN_ENDED' and self.maturity_date:
            raise ValueError('Open-ended terms cannot also claim a fixed maturity')
        return self
