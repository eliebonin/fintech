"""Read-only discovery contracts; a displayed action is never posting authority."""
from datetime import date,datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .assistance_contracts import SubscriptionView

EventStatus=Literal['UPCOMING','DUE','OVERDUE','PREPARED','BOOKED','REASSESSMENT','BLOCKED']
Attention=Literal['ACTIONABLE','INFORMATION']
class WorklistQuery(BaseModel):
    model_config=ConfigDict(extra='forbid')
    fromDate:date
    toDate:date
    strategyId:UUID|None=None
    instrumentId:UUID|None=None
    q:str=Field(default='',max_length=250)
    eventType:Literal['BOND_MATURITY']='BOND_MATURITY'
    attention:Literal['ALL','ACTIONABLE','INFORMATION']='ALL'
    status:Literal['ALL','UPCOMING','DUE','OVERDUE','PREPARED','BOOKED','REASSESSMENT','BLOCKED']='ALL'
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
class WorklistEvent(BaseModel):
    eventKey:str
    eventType:Literal['BOND_MATURITY']='BOND_MATURITY'
    instrumentType:Literal['BOND']='BOND'
    strategyId:UUID
    strategyName:str
    instrumentId:UUID
    instrumentName:str
    identifier:str|None=None
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
