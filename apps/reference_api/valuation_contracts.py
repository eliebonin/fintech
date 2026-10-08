"""Transport contracts for bounded market-only valuation and review."""
from datetime import datetime,timedelta,timezone
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,JsonValue,model_validator

class ValuationCreate(BaseModel):
    strategy_id: UUID=Field(alias='strategyId')
    policy_id: UUID=Field(alias='policyId')
    cut_id: UUID=Field(alias='cutId')
    reporting_currency_id: UUID=Field(alias='reportingCurrencyId')
    opening_cutoff: datetime=Field(alias='openingCutoff')
    closing_cutoff: datetime=Field(alias='closingCutoff')
    information_cutoff: datetime=Field(alias='informationCutoff')
    model_config=ConfigDict(populate_by_name=True,extra='forbid')

    @model_validator(mode='after')
    def times(self):
        for value in (self.opening_cutoff,self.closing_cutoff,self.information_cutoff):
            if value.tzinfo is None or value.utcoffset()!=timedelta(0): raise ValueError('Timezone-aware UTC cutoffs required')
        if not self.opening_cutoff<self.closing_cutoff<=self.information_cutoff:
            raise ValueError('Opening < closing <= information cutoff required')
        if self.closing_cutoff-self.opening_cutoff>timedelta(days=31): raise ValueError('Alpha period is limited to 31 days')
        if self.information_cutoff>datetime.now(timezone.utc)+timedelta(minutes=1): raise ValueError('Information cutoff cannot be in the future')
        return self

class ReviewComment(BaseModel):
    comment: str=Field(min_length=1,max_length=2000)
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class ValuationAttemptList(BaseModel):
    items: list[dict[str,JsonValue]]
    scope: str='MARKET_ONLY'
    total: int
    canManage: bool
    actorId: UUID

class ValuationAttemptDetail(BaseModel):
    attempt: dict[str,JsonValue]
    events: list[dict[str,JsonValue]]
    batch: dict[str,JsonValue] | None

class ValuationOptions(BaseModel):
    strategies: list[dict[str,JsonValue]]
    policies: list[dict[str,JsonValue]]
    currencies: list[dict[str,JsonValue]]
