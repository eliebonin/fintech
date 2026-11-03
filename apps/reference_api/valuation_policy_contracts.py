"""Bounded composite policy configuration and preview contracts."""
from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel
from .contracts import MarketDataResolutionSnapshotItemView
# Preserve API imports and OpenAPI model identities without duplicate validators.
from market_data.pricing_policy_contracts import PolicyCreate, PolicyRuleInput


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
    selectionMode: Literal['STRICT','FLEXIBLE']
    rules: list[PolicyRuleInput]
    defaultRules: list[PolicyRuleInput]


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


class PriceProfile(BaseModel):
    seriesType: str
    closingMethod: str = 'UNKNOWN'
    valueBasis: str
    seriesCount: int
    valuationSeriesCount: int


class PolicyDataSource(BaseModel):
    datasetId: UUID
    label: str
    provider: str
    purposes: list[str]
    nonDisplayAllowed: bool
    priceProfiles: list[PriceProfile]


class PolicyDataOptions(BaseModel):
    sources: list[PolicyDataSource]


class CompatibilityIssue(BaseModel):
    code: str
    message: str
    action: str


class RuleCompatibility(BaseModel):
    ruleSequence: int
    origin: str
    matchingSeriesCount: int
    eligibleSeriesCount: int
    sourceLabels: list[str]
    issues: list[CompatibilityIssue]


class PolicyCompatibility(BaseModel):
    status: Literal['COMPATIBLE_CONFIGURATION','ACTION_REQUIRED']
    scope: str
    rules: list[RuleCompatibility]
