"""Strict command models for subscription ceilings and scoped assistance."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator

EVENT_TYPES=('BOND_MATURITY','FX_FORWARD_MATURITY')
TIERS={0:'Fully manual',1:'Notifications',2:'Assisted preparation',3:'One-click booking'}
MODULE='LIFECYCLE_MANAGEMENT'
EventType=Literal['BOND_MATURITY','FX_FORWARD_MATURITY']

class Command(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class SubscriptionPreview(Command):
    maximumTier:int=Field(ge=0,le=3,strict=True)
    expectedRevision:int=Field(ge=0,strict=True)

class SubscriptionChange(SubscriptionPreview):
    expectedImpactHash:str=Field(pattern=r'^[0-9a-f]{64}$')
    reason:str=Field(min_length=1,max_length=2000)
    confirmChange:Literal[True]
    confirmBlockedWorkflows:bool=False

class AssistanceChange(Command):
    strategyId:UUID
    eventType:EventType
    selectedTier:int=Field(ge=0,le=3,strict=True)
    expectedRevision:int=Field(ge=0,strict=True)
    expectedSubscriptionRevision:int=Field(ge=0,strict=True)
    reason:str=Field(min_length=1,max_length=2000)

class TransitionPreview(Command):
    proposedMaximumTier:int=Field(ge=0,le=3,strict=True)
    expectedSubscriptionRevision:int=Field(ge=0,strict=True)
    scope:Literal['ABOVE_NEW_CEILING','ALL_CONFIGURED','SELECTED']='ABOVE_NEW_CEILING'
    replacement:Literal['HIGHEST_AVAILABLE','EXPLICIT','KEEP']='HIGHEST_AVAILABLE'
    targetTier:int|None=Field(default=None,ge=0,le=3,strict=True)
    targets:list[tuple[UUID,EventType]]=Field(default_factory=list,max_length=1000)
    @model_validator(mode='after')
    def exact_selection(self):
        if (self.scope=='SELECTED')!=bool(self.targets):raise ValueError('Only SELECTED uses a nonempty explicit target list.')
        if len(set(self.targets))!=len(self.targets):raise ValueError('Duplicate strategy/event targets.')
        if (self.replacement=='EXPLICIT')!=(self.targetTier is not None):raise ValueError('Explicit replacement requires exactly one target tier.')
        return self

class TransitionApply(TransitionPreview):
    inputHash:str=Field(pattern=r'^[0-9a-f]{64}$')
    reason:str=Field(min_length=1,max_length=2000)
    confirmChange:Literal[True]
    confirmReplaceAllowed:bool=False


class SubscriptionView(BaseModel):
    tenantId:UUID
    maximumTier:int
    configuredMaximumTier:int
    revision:int
    source:str|None
    moduleActive:bool
    notificationDiscoveryAvailable:bool
    entitlementFingerprint:str

class SubscriptionChangePreview(BaseModel):
    current:SubscriptionView
    proposedMaximumTier:int
    affectedEventCount:int
    pendingPreparationCount:int
    inputHash:str

class OperationDecision(BaseModel):
    allowed:bool
    reasons:list[str]

class AssistanceView(BaseModel):
    tenantId:UUID
    strategyId:UUID
    eventType:EventType
    maximumTier:int
    selectedTier:int
    subscriptionRevision:int
    assistanceRevision:int
    processingPolicyRevision:int
    processingMode:Literal['DIRECT','REVIEW','MANUAL']
    availableTiers:list[int]
    status:Literal['AVAILABLE','BLOCKED_BY_SUBSCRIPTION']
    canConfigure:bool
    handlerSupported:bool
    notificationDiscoveryAvailable:bool
    operations:dict[str,OperationDecision]

class StrategyOption(BaseModel):
    strategyId:UUID
    label:str
    code:str
    canConfigure:bool=False
    configuredEvents:dict[str,int]=Field(default_factory=dict)

class AssistanceOptions(BaseModel):
    items:list[StrategyOption]
    total:int
    offset:int
    limit:int
    subscription:SubscriptionView
    canConfigureAll:bool=False

class TransitionItem(BaseModel):
    strategyId:UUID
    strategyLabel:str
    eventType:EventType
    beforeTier:int
    afterTier:int
    revision:int
    changed:bool

class AssistanceTransitionPreview(BaseModel):
    items:list[TransitionItem]
    changedCount:int
    unchangedCount:int
    blockedCount:int
    inputHash:str
    subscriptionRevision:int
    proposedMaximumTier:int
    commercialSubscriptionChanged:Literal[False]

class AssistanceTransitionResult(BaseModel):
    updatedCount:int
    unchangedCount:int
    commercialSubscriptionChanged:Literal[False]
    message:str
