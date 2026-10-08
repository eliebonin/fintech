"""Bounded composite policy configuration and preview contracts."""
from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .contracts import MarketDataResolutionSnapshotItemView


class PolicyRuleInput(BaseModel):
    rule_sequence: int = Field(alias='ruleSequence',ge=1,le=10000)
    subject_type: str | None = Field(default=None,alias='subjectType',max_length=50)
    instrument_type_id: UUID | None = Field(default=None,alias='instrumentTypeId')
    subject_reference_node_id: UUID | None = Field(default=None,alias='subjectReferenceNodeId')
    market_data_series_id: UUID | None = Field(default=None,alias='marketDataSeriesId')
    market_venue_id: UUID | None = Field(default=None,alias='marketVenueId')
    series_type: str = Field(alias='seriesType',min_length=1,max_length=50)
    pricing_convention: Literal['LEGACY','SESSION_CLOSE','NAMED_FIXING','EXPLICIT_TIME','NAV_DATE'] = Field(alias='pricingConvention')
    pricing_cut_id: UUID | None = Field(default=None,alias='pricingCutId')
    market_calendar_id: UUID | None = Field(default=None,alias='marketCalendarId')
    fixing_code: str | None = Field(default=None,alias='fixingCode',min_length=1,max_length=100)
    value_basis: str | None = Field(default=None,alias='valueBasis',min_length=1,max_length=50)
    dataset_id: UUID | None = Field(default=None,alias='datasetId')
    selection_method: Literal['OFFICIAL','LAST_BEFORE_CUT','MID','APPROVED','FALLBACK'] = Field(default='OFFICIAL',alias='selectionMethod')
    pricing_date_rule: Literal['SAME_DAY','PRIOR_AVAILABLE','FIXED_LAG'] = Field(default='SAME_DAY',alias='pricingDateRule')
    lag_business_days: int = Field(default=0,alias='lagBusinessDays',ge=0,le=366)
    max_staleness_business_days: int | None = Field(default=0,alias='maxStalenessBusinessDays',ge=0,le=366)
    missing_data_action: Literal['FAIL','WARN','MANUAL_OVERRIDE'] = Field(default='FAIL',alias='missingDataAction')
    model_config=ConfigDict(populate_by_name=True,extra='forbid',str_strip_whitespace=True)

    @model_validator(mode='after')
    def convention_terms(self):
        if self.pricing_convention=='NAV_DATE' and (not self.market_calendar_id or self.series_type not in ('OFFICIAL_NAV','NAV','INDICATIVE_NAV')):
            raise ValueError('NAV_DATE requires a fund valuation calendar and a NAV series type')
        if self.pricing_convention in ('NAMED_FIXING','EXPLICIT_TIME') and not self.pricing_cut_id:
            raise ValueError('A rule-specific pricing cut is required')
        if self.pricing_convention=='NAMED_FIXING' and not self.fixing_code:
            raise ValueError('A fixing code is required')
        if self.pricing_convention!='NAMED_FIXING' and self.fixing_code:
            raise ValueError('Fixing code only applies to named fixing rules')
        if self.pricing_date_rule!='FIXED_LAG' and self.lag_business_days:
            raise ValueError('Lag requires FIXED_LAG')
        return self


class PolicyCreate(BaseModel):
    policy_code: str = Field(alias='policyCode',min_length=1,max_length=100,pattern=r'^[A-Za-z0-9_][A-Za-z0-9_.-]*$')
    display_name: str = Field(alias='displayName',min_length=1,max_length=250)
    valuation_cut_id: UUID = Field(alias='valuationCutId')
    strategy_id: UUID | None = Field(default=None,alias='strategyId')
    valid_from: date = Field(alias='validFrom')
    valid_to: date | None = Field(default=None,alias='validTo')
    rules: list[PolicyRuleInput] = Field(min_length=1,max_length=50)
    model_config=ConfigDict(populate_by_name=True,extra='forbid',str_strip_whitespace=True)

    @model_validator(mode='after')
    def ordered_rules(self):
        if len({r.rule_sequence for r in self.rules})!=len(self.rules):
            raise ValueError('Rule sequences must be unique')
        if self.valid_to and self.valid_to<self.valid_from:
            raise ValueError('Policy validity is reversed')
        return self


class PolicyView(BaseModel):
    valuationPolicyId: UUID
    policyCode: str
    displayName: str
    valuationCutId: UUID
    strategyId: UUID | None
    versionNo: int
    status: str
    validFrom: date
    validTo: date | None
    createdByUserAccountId: UUID | None
    createdAtUtc: datetime | None
    rules: list[PolicyRuleInput]


class PolicyOption(BaseModel):
    id: UUID
    label: str


class PolicyOptions(BaseModel):
    canManage: bool
    cuts: list[PolicyOption]
    venues: list[PolicyOption]
    instrumentTypes: list[PolicyOption]
    calendars: list[PolicyOption]
    strategies: list[PolicyOption]
    datasets: list[PolicyOption]


class ResolutionPreview(BaseModel):
    status: str
    items: list[MarketDataResolutionSnapshotItemView]
