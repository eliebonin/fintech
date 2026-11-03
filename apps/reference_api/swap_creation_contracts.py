# HTTP proposal envelope and compatibility exports for domain-owned swap terms.
from pydantic import BaseModel, Field, field_validator, model_validator
from security_master_schema.swap_terms import Frequency, GenericSwapTerms, RateSwapTerms, SwapTerms, spread_from_basis_points
from uuid import UUID


class SwapProposalRequest(BaseModel):
    idempotency_key: str | None = Field(default=None,alias='idempotencyKey',min_length=1,max_length=255)
    canonical_name: str = Field(alias='canonicalName', min_length=1, max_length=250)
    tenant_identifier: str | None = Field(default=None, alias='tenantIdentifier', min_length=1, max_length=100)
    terms: SwapTerms
    existing_reference_id:UUID|None=Field(default=None,alias='existingReferenceId',exclude_if=lambda v:v is None)
    expected_reference_definition_id:UUID|None=Field(default=None,alias='expectedReferenceDefinitionId',exclude_if=lambda v:v is None)
    model_config = dict(populate_by_name=True, extra='forbid')

    @field_validator('canonical_name')
    @classmethod
    def nonblank(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError('A nonblank value is required.')
        return value

    @field_validator('tenant_identifier', mode='before')
    @classmethod
    def optional_identifier(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @model_validator(mode='after')
    def preserve_identifier(self):
        if (self.existing_reference_id is None)!=(self.expected_reference_definition_id is None):
            raise ValueError('Reference completion requires its expected current definition')
        if self.existing_reference_id is not None and not isinstance(self.terms,RateSwapTerms):
            raise ValueError('Only first-time rate-exchange reference completion is supported')
        if (self.tenant_identifier is not None and self.terms.tenant_identifier is not None
                and self.tenant_identifier != self.terms.tenant_identifier):
            raise ValueError('Proposal and terms tenant identifiers must agree.')
        self.tenant_identifier = self.tenant_identifier or self.terms.tenant_identifier
        self.terms = self.terms.model_copy(update={'tenant_identifier': self.tenant_identifier})
        return self
