"""Read-only discovery contracts; a displayed action is never posting authority."""
from datetime import date,datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .assistance_contracts import SubscriptionView

EventStatus=Literal['UPCOMING','DUE','OVERDUE','PREPARED','BOOKED','REASSESSMENT','BLOCKED','REVIEW_DUE','CONFIRMATION_RECORDED','SCHEDULED_TODAY','DATE_PASSED','SOURCE_UNAVAILABLE']
Attention=Literal['ACTIONABLE','INFORMATION']
class WorklistQuery(BaseModel):
    model_config=ConfigDict(extra='forbid')
    fromDate:date
    toDate:date
    strategyId:UUID|None=None
    instrumentId:UUID|None=None
    q:str=Field(default='',max_length=250)
    eventType:Literal['ALL','BOND_MATURITY','FX_FORWARD_MATURITY','BOND_COUPON','FUTURE_EXPIRY','OPTION_EXPIRY','STRUCTURED_OBSERVATION']='ALL'
    attention:Literal['ALL','ACTIONABLE','INFORMATION']='ALL'
    status:Literal['ALL','UPCOMING','DUE','OVERDUE','PREPARED','BOOKED','REASSESSMENT','BLOCKED','REVIEW_DUE','CONFIRMATION_RECORDED','SCHEDULED_TODAY','DATE_PASSED','SOURCE_UNAVAILABLE']='ALL'
    includeEarlierOverdue:bool=True
    offset:int=Field(default=0,ge=0)
    limit:int=Field(default=25,ge=1,le=100,json_schema_extra={"enum":[25,50,100]})
    @model_validator(mode='after')
    def dates(self):
        if self.fromDate>self.toDate:raise ValueError('From date must not follow To date.')
        if self.limit not in (25,50,100):raise ValueError('Rows per page must be 25, 50 or 100.')
        return self
class WorklistQuantity(BaseModel):
    currency:str
    unit:str
    netQuantity:str
    grossQuantity:str
    entries:int
class DateTiming(BaseModel):
    tone:Literal['TODAY','SOON','WEEK','LATER','OVERDUE','NEUTRAL']
    label:str
    businessDays:int|None=None
    basis:Literal['CALENDAR','WEEKDAYS','UNKNOWN']
    calendarName:str|None=None
    timezoneName:str
    evaluatedOn:date
    explanation:str

class WorklistEvent(BaseModel):
    eventKey:str
    eventType:Literal['BOND_MATURITY','FX_FORWARD_MATURITY','BOND_COUPON','FUTURE_EXPIRY','OPTION_EXPIRY','STRUCTURED_OBSERVATION']='BOND_MATURITY'
    instrumentType:Literal['BOND','FX_FORWARD','FUTURE','OPTION','STRUCTURED_PRODUCT','SWAP']='BOND'
    strategyId:UUID
    strategyName:str
    instrumentId:UUID
    instrumentName:str
    identifier:str|None=None
    eventDate:date|None=None
    milestoneKind:str|None=None
    eventAtUtc:datetime|None=None
    sourceFingerprint:str|None=None
    relatedInstrumentId:UUID|None=None
    relatedInstrumentName:str|None=None
    couponPeriodId:UUID|None=None
    positionDate:date|None=None
    maturityDate:date|None
    status:EventStatus
    attention:Attention
    quantities:list[WorklistQuantity]
    remainingEntries:int|None
    selectedTier:int
    maximumTier:int
    processingMode:Literal['DIRECT','REVIEW','MANUAL']
    reasons:list[str]
    actionLabel:str
    actionHref:str
    proposalId:UUID|None=None
    postingId:UUID|None=None
    positionAssessed:bool
    dateTiming:DateTiming|None=None
class WorklistResponse(BaseModel):
    items:list[WorklistEvent]
    total:int
    offset:int
    limit:int
    evaluatedAt:datetime
    fromDate:date
    toDate:date
    statusCounts:dict[str,int]
    subscription:SubscriptionView
    discoveryEventTypes:list[str]
    unavailableReason:str|None=None
class WorklistStrategy(BaseModel):
    strategyId:UUID
    label:str
class WorklistOptions(BaseModel):
    items:list[WorklistStrategy]
    total:int
    offset:int
    limit:int


class CouponConfirmation(BaseModel):
    paymentId:UUID
    status:Literal['CONFIRMED','REVERSED']
    paymentDate:date
    amount:str
    currency:str
    sourceReference:str
    note:str
    recordedAt:datetime
    scheduleRevision:int
    currentSchedule:bool

class CouponInspection(BaseModel):
    eventKey:str
    strategyId:UUID
    instrumentId:UUID
    periodId:UUID
    scheduleId:UUID
    scheduleRevision:int
    cashflowKey:str
    paymentDate:date
    accrualStart:date
    accrualEnd:date
    recordDate:date|None
    exDate:date|None
    currency:str
    couponRate:str|None
    amountPer100:str|None
    amountFormula:str|None
    sourceReference:str
    sourceRecordedAt:datetime
    positionDate:date
    positionAssessed:bool
    quantities:list[WorklistQuantity]
    confirmations:list[CouponConfirmation]
    financialTreatment:Literal['NOT_ASSESSED']='NOT_ASSESSED'


class ContractMilestone(BaseModel):
    kind:str
    date:date
    atUtc:datetime|None=None

class FutureInspection(BaseModel):
    eventKey:str
    strategyId:UUID
    instrumentId:UUID
    sourceFingerprint:str
    evaluatedAt:datetime
    milestoneKind:str
    milestones:list[ContractMilestone]
    settlementMethod:Literal['CASH','PHYSICAL']|None=None
    familyName:str|None=None
    contractMonth:date|None=None
    conventionId:UUID|None=None
    conventionVersion:int|None=None
    sourceReference:str|None=None
    sourceApprovedAt:datetime|None=None
    quantityUnit:Literal['CONTRACTS']='CONTRACTS'
    monetaryMultiplier:str|None=None
    quoteFactor:str|None=None
    positionAssessed:bool
    quantities:list[WorklistQuantity]
    reasons:list[str]
    firstNoticeDate:date|None=None
    financialTreatment:Literal['NOT_ASSESSED']='NOT_ASSESSED'


class OptionInspection(BaseModel):
    eventKey:str
    strategyId:UUID
    instrumentId:UUID
    sourceFingerprint:str
    evaluatedAt:datetime
    milestoneKind:str
    milestones:list[ContractMilestone]
    optionTermsId:UUID|None=None
    termsVersion:int|None=None
    definitionId:UUID|None=None
    sourceApprovedAt:datetime|None=None
    underlyingId:UUID|None=None
    underlyingName:str|None=None
    optionType:str|None=None
    strike:str|None=None
    strikeCurrency:str|None=None
    exerciseStyle:str|None=None
    settlementMethod:str|None=None
    settlementCurrency:str|None=None
    premiumCurrency:str|None=None
    premiumMultiplier:str|None=None
    deliverableUnits:str|None=None
    positionAssessed:bool
    quantities:list[WorklistQuantity]
    reasons:list[str]
    financialTreatment:Literal['NOT_ASSESSED']='NOT_ASSESSED'


class StructuredBarrierView(BaseModel):
    underlyingName:str|None=None
    comparison:str
    basis:str
    lowerLevel:str|None=None
    upperLevel:str|None=None
    measure:str|None=None
    lowerInclusive:bool|None=None
    upperInclusive:bool|None=None

class StructuredConditionView(BaseModel):
    groupCode:str
    combination:str
    aggregation:str
    scope:str
    sourceStatus:str
    barriers:list[StructuredBarrierView]
    actions:list[str]

class StructuredInspection(BaseModel):
    eventKey:str
    strategyId:UUID
    instrumentId:UUID
    instrumentType:Literal['STRUCTURED_PRODUCT','SWAP']
    instrumentName:str
    observedInstrumentId:UUID|None=None
    observedInstrumentName:str|None=None
    relation:str|None=None
    sourceFingerprint:str
    sourceBasis:Literal['CURRENT_APPROVED_TERMS']='CURRENT_APPROVED_TERMS'
    evaluatedAt:datetime
    noticeKind:str
    eventDate:date|None=None
    conditionalPaymentDate:date|None=None
    firstAutocallDate:date|None=None
    autocallEligibility:Literal['ELIGIBLE_DATE','BEFORE_FIRST_DATE','NOT_ASSESSED','NOT_APPLICABLE']='NOT_ASSESSED'
    issuer:str|None=None
    currency:str|None=None
    definitionVersion:int|None=None
    termsVersion:int|None=None
    scheduleEventId:UUID|None=None
    sourceEventStatus:str|None=None
    positionDate:date
    positionAssessed:bool
    quantities:list[WorklistQuantity]
    conditions:list[StructuredConditionView]
    reasons:list[str]
    outcomeStatus:Literal['NOT_ASSESSED']='NOT_ASSESSED'
