"""Transport contracts for bounded market-only valuation and review."""
from datetime import date,datetime,time,timedelta,timezone
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,JsonValue,model_validator

class ValuationCreate(BaseModel):
    strategy_id: UUID=Field(alias='strategyId')
    policy_id: UUID=Field(alias='policyId')
    cut_id: UUID=Field(alias='cutId')
    reporting_currency_id: UUID=Field(alias='reportingCurrencyId')
    opening_cutoff: datetime | None=Field(default=None,alias='openingCutoff')
    closing_cutoff: datetime | None=Field(default=None,alias='closingCutoff')
    opening_date: date | None=Field(default=None,alias='openingDate')
    closing_date: date | None=Field(default=None,alias='closingDate')
    information_cutoff: datetime=Field(default_factory=lambda:datetime.now(timezone.utc),alias='informationCutoff')
    predecessor_batch_id: UUID | None=Field(default=None,alias='predecessorBatchId')
    recalculation_reason: str | None=Field(default=None,alias='recalculationReason',min_length=1,max_length=2000)
    model_config=ConfigDict(populate_by_name=True,extra='forbid')

    @property
    def daily(self):
        return self.opening_date is not None

    def resolved_cutoffs(self):
        if self.daily:
            return (datetime.combine(self.opening_date,time.max,timezone.utc),datetime.combine(self.closing_date,time.max,timezone.utc))
        return self.opening_cutoff,self.closing_cutoff

    @model_validator(mode='after')
    def times(self):
        if (self.predecessor_batch_id is None)!=(self.recalculation_reason is None):
            raise ValueError('Predecessor batch and recalculation reason required together')
        if self.recalculation_reason is not None and not self.recalculation_reason.strip():
            raise ValueError('Recalculation reason must not be blank')
        if self.daily or self.closing_date is not None:
            if self.opening_date is None or self.closing_date is None or self.opening_cutoff is not None or self.closing_cutoff is not None:
                raise ValueError('Supply both valuation dates, without timestamp cutoffs')
        elif self.opening_cutoff is None or self.closing_cutoff is None:
            raise ValueError('Opening and closing valuation dates required')
        opening,closing=self.resolved_cutoffs()
        for value in (opening,closing,self.information_cutoff):
            if value.tzinfo is None or value.utcoffset()!=timedelta(0): raise ValueError('Timezone-aware UTC cutoffs required')
        if not opening<closing<=self.information_cutoff:
            raise ValueError('Opening < closing <= information cutoff required')
        if closing-opening>timedelta(days=31): raise ValueError('Alpha period is limited to 31 days')
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
