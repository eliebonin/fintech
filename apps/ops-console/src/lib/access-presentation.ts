import {accessLabel, type AccessGroup} from './access-administration';

// Presentation only: the API remains authoritative for action and scope decisions.
const actions:Record<string,[string,string]>={
 REPORTING_READ:['View regulatory preparation','Read prepared transaction reports and history within permitted strategies.'],
 REPORTING_PREPARE:['Prepare transaction reports','Retain execution facts for assessment within permitted strategies; no regulator submission.'],
 REPORTING_REVIEW:['Review transaction reports','Amend reporting mappings and reasoned scope/hold decisions within permitted strategies.'],
 REPORTING_EXPORT:['Export reporting preparation','Freeze/download preparation CSV and evidence within permitted strategies; exported is not submitted.'],
 REPORTING_CONFIGURE:['Configure reporting entities','Maintain tenant-wide reporting legal entities and assessed regulatory status.'],
 STRATEGY_CREATE:['Create strategies','Create a strategy and choose its initial group access.'],
 STRATEGY_READ:['View strategies','Read strategy details within this group’s strategy scope.'],
 STRATEGY_WRITE:['Edit strategies','Update existing strategies within this group’s scope.'],
 TRADE_READ:['View trades','Read trade history and trade details.'],
 TRADE_WRITE:['Book trades','Create trades on permitted strategies.'],
 TRADE_CORRECT:['Correct and cancel trades','Submit corrections or cancellations; existing records remain auditable.'],
 LIFECYCLE_READ:['View lifecycle events','View plain-bond and deliverable FX-forward maturity previews, prepared entries and posting evidence on permitted strategies. FX evidence also requires market-data read. Event notifications and other product workflows remain deferred.'],
 LIFECYCLE_PREPARE:['Prepare lifecycle entries','Prepare sourced plain-bond or deliverable FX-forward maturity entries on permitted strategies for independent approval. FX requires market-data read.'],
 LIFECYCLE_BOOK:['Book lifecycle entries','Ops-triggered Book now or source-confirmed maturity booking; also requires trade-write on the same strategy and market-data read for FX. Not unattended automation.'],
 LIFECYCLE_APPROVE:['Approve lifecycle entries','Approve prepared maturity entries with independent reviewer/operator ancestry and trade-write on the same strategy. FX also requires market-data read.'],
 LIFECYCLE_CONFIGURE:['Configure lifecycle handling','Change retained plain-bond maturity or FX-forward maturity processing modes on permitted strategies with a reason and revision check. FX also selects an explicit pricing policy. Admin status alone does not grant it.'],
 TRADE_CONFIGURE:['Manage trade fields','Maintain tenant-wide custom fields and their curated values.'],
 REFERENCE_READ:['Browse instruments','Read the available instruments and listings.'],
 REFERENCE_PROPOSE:['Propose instruments','Submit new instruments or changes for review.'],
 REFERENCE_APPROVE:['Approve instruments','Review and approve instrument requests.'],
 MARKET_DATA_READ:['View market data','Inspect data and evidence; strategy-linked evidence is scoped.'],
 MARKET_DATA_MANAGE:['Manage market data','Maintain market-data setup; strategy-linked settings are scoped.'],
 VALUATION_READ:['View valuations','Read runs and results on permitted strategies.'],
 VALUATION_RUN:['Run valuations','Calculate and stage results on permitted strategies.'],
 VALUATION_REVIEW:['Review valuations','Review or publish permitted results; review safeguards still apply.'],
 VALUATION_SELF_PUBLISH:['Self-publish valuations','Explicit strategy-scoped exception; requires review permission and active tenant opt-in. Never allows self-approval of amendments.'],
 CALENDAR_READ:['View calendars','Inspect shared calendars and permitted strategy calendars.'],
 CALENDAR_MANAGE:['Manage calendars','Maintain calendars; strategy-specific changes are scoped.'],
};
export function actionTitle(code:string){return actions[code]?.[0]??accessLabel(code);}
export function actionDescription(code:string){return actions[code]?.[1]??'Subject to enabled modules and API access checks.';}
export function groupScopeSummary(group:AccessGroup){
 if(group.scopeMode==='ALL')return 'Current and future strategies';
 if(group.scopeMode!=='SELECTED')return 'Scope unavailable';
 const count=group.strategyIds?.length??0;
 return count?`${count} selected ${count===1?'strategy':'strategies'}`:'No strategies selected';
}
