"""Validated booking commands shared by HTTP, imports and operator calls.

These are the original models/aliases; HTTP response and detail DTOs stay in API.
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator, model_validator


class TradePropertyInput(BaseModel):
    definition_id: UUID = Field(alias="definitionId")
    value: Annotated[StrictStr, Field(max_length=2000)] | StrictBool
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class TradeReferenceInput(BaseModel):
    reference_type: Literal["SOURCE_TRADE_ID", "CLIENT_REFERENCE", "BROKER_REFERENCE"] = Field(alias="referenceType")
    reference_value: str = Field(alias="referenceValue", min_length=1, max_length=500)
    source_system_id: str | None = Field(default=None, alias="sourceSystemId", max_length=100)
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    @field_validator("reference_value")
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError("Reference is required.")
        return value.strip()


class CancelBookingRequest(BaseModel):
    expected_sequence_no: int = Field(alias='expectedSequenceNo', ge=1)
    reason: str = Field(min_length=1, max_length=1000)
    model_config = ConfigDict(populate_by_name=True, extra='forbid')

    @field_validator('reason')
    @classmethod
    def trim_reason(cls, value):
        value=value.strip()
        if not value: raise ValueError('A correction reason is required.')
        return value


class BookingCorrectionRequest(CancelBookingRequest):
    trade_id: UUID = Field(alias='tradeId')


class ValuationRecognitionFields(BaseModel):
    """Platform-wide optional booking fields; never curated tenant properties."""
    valuation_effective_date: date | None = Field(default=None, alias='valuationEffectiveDate')
    valuation_override_reason: str | None = Field(default=None, alias='valuationOverrideReason', max_length=1000)

    @model_validator(mode='after')
    def validate_recognition(self):
        from .recognition import recognition
        recognition(self)
        return self


class TradeBookingRequest(ValuationRecognitionFields):
    correction: BookingCorrectionRequest | None = None
    listing_id: UUID = Field(alias="listingId")
    strategy_id: UUID = Field(alias="strategyId")
    side: Literal["BUY", "SELL"]
    quantity: Decimal = Field(gt=0)
    execution_price: Decimal = Field(alias="executionPrice", gt=0)
    trade_datetime: datetime = Field(alias="tradeDatetime")
    settlement_date: date = Field(alias="settlementDate")
    counterparty_organisation_id: UUID | None = Field(default=None, alias="counterpartyOrganisationId")
    external_reference: str | None = Field(default=None, alias="externalReference", max_length=500)
    comment: str | None = Field(default=None, max_length=10000)
    executing_broker_organisation_id: UUID | None = Field(default=None, alias="executingBrokerOrganisationId")
    trader_person_id: UUID | None = Field(default=None, alias="traderPersonId")
    trade_purpose: Literal["INVESTMENT", "REBALANCING", "HEDGING", "OTHER"] = Field(default="INVESTMENT", alias="tradePurpose")
    market_activity: Literal["PRIMARY", "SECONDARY"] | None = Field(default=None, alias="marketActivity")
    tag_ids: list[UUID] = Field(default_factory=list, alias="tagIds", max_length=100)
    properties: list[TradePropertyInput] = Field(default_factory=list, max_length=1000)
    external_references: list[TradeReferenceInput] = Field(default_factory=list, alias="externalReferences", max_length=20)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("external_reference", "comment")
    @classmethod
    def _trim_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    def _validate_annotations(self) -> None:
        if self.trade_purpose == "OTHER" and not self.comment: raise ValueError("OTHER purpose requires a comment.")
        if self.external_reference and self.external_references: raise ValueError("Use legacy externalReference or structured references, not both.")
        if len(set(self.tag_ids)) != len(self.tag_ids): raise ValueError("Duplicate tag IDs.")
        if len({p.definition_id for p in self.properties}) != len(self.properties): raise ValueError("Duplicate property IDs.")
        if len({(r.reference_type, r.source_system_id, r.reference_value) for r in self.external_references}) != len(self.external_references): raise ValueError("Duplicate external references.")

    @model_validator(mode="after")
    def _validate_dates_and_timezone(self) -> "TradeBookingRequest":
        self._validate_annotations()
        if self.trade_datetime.tzinfo is None or self.trade_datetime.utcoffset() is None:
            raise ValueError("tradeDatetime must include a timezone offset")
        if self.settlement_date < self.trade_datetime.astimezone(timezone.utc).date():
            raise ValueError("settlementDate must not be before tradeDatetime")
        return self


@dataclass(frozen=True)
class BookingResult:
    """Stable execution identity, independent of any presentation envelope."""
    trade_id: UUID
