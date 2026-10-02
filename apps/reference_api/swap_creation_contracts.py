"""Versioned, sourced performance-swap economics; no cashflow generation."""
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, StrictBool, field_validator, model_validator

Frequency = Literal['AT_MATURITY', 'MONTHLY', 'QUARTERLY', 'SEMIANNUAL', 'ANNUAL', 'CUSTOM']


def spread_from_basis_points(value: str | Decimal) -> Decimal:
    """Convert displayed basis points to the persisted decimal rate."""
    if not isinstance(value, (str, Decimal)):
        raise ValueError('Basis points must be a decimal string or Decimal.')
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('Invalid basis points.') from exc
    if not number.is_finite():
        raise ValueError('Basis points must be finite.')
    return number / Decimal('10000')


class GenericSwapTerms(BaseModel):
    schema_version: Literal[1] = Field(default=1, alias='schemaVersion')
    performance_reference_id: UUID = Field(alias='performanceReferenceId')
    contractual_notional: Decimal = Field(alias='contractualNotional', gt=0, max_digits=30, decimal_places=12)
    notional_currency_id: UUID = Field(alias='notionalCurrencyId')
    effective_date: date = Field(alias='effectiveDate')
    maturity_date: date = Field(alias='maturityDate')
    performance_direction: Literal['PAY', 'RECEIVE'] = Field(alias='performanceDirection')
    return_basis: Literal['TOTAL', 'EXCESS'] = Field(alias='returnBasis')
    return_profile_id: UUID = Field(alias='returnProfileId')
    leverage: Decimal = Field(default=Decimal('1'), gt=0, max_digits=30, decimal_places=12)
    quote_currency_id: UUID = Field(alias='quoteCurrencyId')
    quote_factor: Decimal = Field(alias='quoteFactor', gt=0, max_digits=20, decimal_places=8)
    source_reference: str = Field(alias='sourceReference', min_length=1, max_length=1000)
    financing_treatment: Literal['NONE', 'EMBEDDED', 'SEPARATE', 'EMBEDDED_AND_SEPARATE'] = Field(alias='financingTreatment')
    funding_reference_id: UUID | None = Field(default=None, alias='fundingReferenceId')
    funding_spread: Decimal | None = Field(default=None, alias='fundingSpread', max_digits=20, decimal_places=8)
    funding_notional_basis: Literal['BOOKED_NOMINAL', 'LEVERAGED_NOMINAL'] | None = Field(default=None, alias='fundingNotionalBasis')
    day_count_convention_id: UUID | None = Field(default=None, alias='dayCountConventionId')
    interest_calculation_method: str | None = Field(default=None, alias='interestCalculationMethod', min_length=1, max_length=1000)
    funding_observation_description: str | None = Field(default=None, alias='fundingObservationDescription', min_length=1, max_length=2000)
    funding_reset_frequency: Frequency | None = Field(default=None, alias='fundingResetFrequency')
    funding_payment_frequency: Frequency | None = Field(default=None, alias='fundingPaymentFrequency')
    funding_reset_schedule_description: str | None = Field(default=None, alias='fundingResetScheduleDescription', min_length=1, max_length=2000)
    funding_payment_schedule_description: str | None = Field(default=None, alias='fundingPaymentScheduleDescription', min_length=1, max_length=2000)
    additional_funding_acknowledged: StrictBool = Field(default=False, alias='additionalFundingAcknowledged')
    additional_funding_evidence: str | None = Field(default=None, alias='additionalFundingEvidence', min_length=1, max_length=2000)
    performance_reset_frequency: Frequency = Field(alias='performanceResetFrequency')
    performance_schedule_description: str | None = Field(default=None, alias='performanceScheduleDescription', min_length=1, max_length=2000)
    redemption_rule: Literal['TERMINATE', 'CONTINUE'] = Field(alias='redemptionRule')
    continuation_description: str | None = Field(default=None, alias='continuationDescription', min_length=1, max_length=2000)
    model_config = dict(populate_by_name=True, extra='forbid')

    @field_validator('contractual_notional', 'leverage', 'quote_factor', 'funding_spread', mode='before')
    @classmethod
    def decimal_input(cls, value):
        if value is not None and not isinstance(value, (str, Decimal)):
            raise ValueError('Use decimal strings, not JSON numbers.')
        return value

    @field_validator('source_reference', 'interest_calculation_method', 'funding_observation_description',
        'funding_reset_schedule_description', 'funding_payment_schedule_description', 'additional_funding_evidence',
        'performance_schedule_description', 'continuation_description')
    @classmethod
    def nonblank(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError('Nonblank source-backed text is required.')
        return value

    @model_validator(mode='after')
    def coherent(self):
        if self.effective_date >= self.maturity_date:
            raise ValueError('Effective date must precede maturity.')
        if self.quote_currency_id != self.notional_currency_id:
            raise ValueError('Quote and notional currencies must match.')
        required = ('funding_spread', 'funding_notional_basis', 'day_count_convention_id',
            'interest_calculation_method', 'funding_reset_frequency', 'funding_payment_frequency')
        dependent = required + ('funding_observation_description', 'funding_reset_schedule_description', 'funding_payment_schedule_description')
        if self.funding_reference_id is None:
            if any(getattr(self, name) is not None for name in dependent):
                raise ValueError('Funding terms require a funding reference.')
            expected = 'EMBEDDED' if self.return_basis == 'EXCESS' else 'NONE'
        else:
            if any(getattr(self, name) is None for name in required):
                raise ValueError('Funding reference requires complete funding conventions.')
            expected = 'EMBEDDED_AND_SEPARATE' if self.return_basis == 'EXCESS' else 'SEPARATE'
        if self.financing_treatment != expected:
            raise ValueError('Financing treatment must agree with return basis and funding reference.')
        if expected == 'EMBEDDED_AND_SEPARATE':
            if not self.additional_funding_acknowledged or not self.additional_funding_evidence:
                raise ValueError('Additional funding requires acknowledgement and confirmation evidence.')
        elif self.additional_funding_acknowledged or self.additional_funding_evidence is not None:
            raise ValueError('Additional funding acknowledgement is only for excess return with separate funding.')
        for frequency, description in ((self.performance_reset_frequency, self.performance_schedule_description),
            (self.funding_reset_frequency, self.funding_reset_schedule_description),
            (self.funding_payment_frequency, self.funding_payment_schedule_description)):
            if frequency == 'CUSTOM' and not description:
                raise ValueError('Custom frequencies require a source-backed schedule description.')
            if frequency != 'CUSTOM' and description is not None:
                raise ValueError('Custom schedule descriptions require custom frequency.')
        if self.redemption_rule == 'CONTINUE' and not self.continuation_description:
            raise ValueError('Continuation requires a source-backed replacement or proceeds rule.')
        if self.redemption_rule == 'TERMINATE' and self.continuation_description is not None:
            raise ValueError('Termination cannot include a continuation rule.')
        return self


class SwapProposalRequest(BaseModel):
    canonical_name: str = Field(alias='canonicalName', min_length=1, max_length=250)
    tenant_identifier: str | None = Field(default=None, alias='tenantIdentifier', min_length=1, max_length=100)
    terms: GenericSwapTerms
    model_config = dict(populate_by_name=True, extra='forbid')

    @field_validator('canonical_name', 'tenant_identifier')
    @classmethod
    def nonblank(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError('A nonblank value is required.')
        return value
