import {LifecycleWorklist} from '../src/features/lifecycle-worklist/worklist-console';
import {BondRedemptionConsole} from '../src/components/bond-redemption-console';
import {PlatformLifecycleSubscription} from '../src/features/lifecycle-assistance/platform-subscription';
import {StrategyLifecycleAssistance} from '../src/features/lifecycle-assistance/strategy-assistance';
import {LifecycleDowngradeWorkspace} from '../src/features/lifecycle-assistance/downgrade-workspace';
import {TradeTicket} from '../src/app/trades/new/trade-ticket';
import {FxForwardTicket} from '../src/app/trades/new/fx-forward-ticket';
import {StrategyTradeProfile} from '../src/features/trade-profiles/strategy-trade-profile';
// Test-only entry. No production route, database, credentials or live provider.
import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {CashRegister} from '../src/features/valuation/cash-register';
import {ReportingWorkspace} from '../src/features/regulatory-reporting/workspace';
import '../src/app/regulatory-reporting/reporting.css';
import {BondCouponConsole} from '../src/components/bond-coupon-console';
import {useAccessData} from '../src/components/access-loader';
import {browserFetch} from '../src/lib/browser-fetch';
import {submitRetained,type RetainedIntent} from '../src/lib/retained-mutation';
import {useRetainedNavigation} from '../src/lib/use-retained-navigation';
import {openValuationInputs} from '../src/lib/valuation-navigation';
import {MeasureCurrencyDisplay,MeasureAmount} from '../src/components/measure-currency-display';
import {ResultWorkspace} from '../src/features/valuation/result-workspace';
import {MarkOverrideReview} from '../src/features/valuation/mark-override-review';
import type {Batch} from '../src/features/valuation/types';
import {ValuationConsole} from '../src/components/valuation-console';
import {PagedValuationChoice} from '../src/features/valuation/paged-choice';
import {OrganisationConsole} from '../src/features/organisations/organisation-console';
import {ReferenceWorkspace} from '../src/features/tenant-reference/reference-workspace';
import {ReferenceCatalogue} from '../src/features/tenant-reference/reference-catalogue';
import {TradeConfigurationConsole} from '../src/app/tenant-profile/trade-configuration/trade-configuration-console';
import '../src/app/globals.css';
import '../src/app/access-administration.css';
import '../src/app/native-workspace.css';
import '../src/app/valuation-workspace.css';
import '../src/app/tenant-profile/organisations/organisations.css';
import {Button,ThemeProvider,CssBaseline} from '@mui/material';
import {workspaceTheme} from '../src/lib/workspace-theme';
import {workspaceCssVariables} from '../src/lib/workspace-presentation';
import AutocallForm from '../src/app/instruments/autocalls/new/form';
import {PageHelp} from '../src/components/page-help';
import {WorkspaceOutline,WorkspaceSkipLink} from '../src/components/workspace-navigation';
import {PricingPolicyConsole} from '../src/components/pricing-policy-console';
import {ImportConsole} from '../src/features/imports/import-console';
import {TenantAccessConsole} from '../src/components/tenant-access-console';
import {ProductConventionForm} from '../src/components/product-convention-form';

function StyleWorkspace(){return <ThemeProvider theme={workspaceTheme}><CssBaseline/><WorkspaceSkipLink/><main id="workspace-content" tabIndex={-1} className="mvp-page organisation-page"><h1>Style acceptance</h1><button>Unclassified action</button><Button>Material action</Button><Button size="small">Compact action</Button><WorkspaceOutline items={[{id:'section-two',label:'Second section'}]}/><h2 id="section-two" tabIndex={-1}>Section two</h2><div className="organisation-table"><table><thead><tr><th>Name</th><th>Role</th><th>Actions</th></tr></thead><tbody><tr><td>Synthetic bank</td><td>Counterparty</td><td><button>Manage</button></td></tr></tbody></table></div></main></ThemeProvider>;}

function Access(){const {data,error,stale,busy,command,reload}=useAccessData<{name:string}>('/api/access',{name:'Original'});return <><h1>{data?.name}</h1><p role="alert">{error}</p><button disabled={busy||stale} onClick={()=>void command('/api/access/users',{name:'Changed'})}>Save user</button><button onClick={()=>void reload()}>Refresh current state</button></>;}
function Ticket(){const retained=useRef<RetainedIntent|null>(null),[message,setMessage]=useState('');useRetainedNavigation(retained);return <form onSubmit={async e=>{e.preventDefault();const body=Object.fromEntries(new FormData(e.currentTarget));try{await submitRetained(body,retained,async(body,key)=>{const r=await browserFetch('/api/mock-booking',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':key},body:JSON.stringify(body)});if(!r.ok)throw new Error('Outcome unknown');return r.json();});setMessage('Booked');}catch(e){setMessage((e as Error).message);}}}><label>Quantity<input name="quantity" required/></label><button>Book synthetic trade</button><p role="status">{message}</p></form>;}
function Navigation(){const [tab,setTab]=useState('results');return <><button onClick={()=>openValuationInputs(()=>setTab('input'))}>Correct source inputs</button><section hidden={tab!=='input'}><details><summary>Daily input register</summary><section id="valuation-input-register"><h2>Daily inputs</h2></section></details></section></>;}
function InstrumentReport(){const [report,setReport]=useState<Batch>();const [view,setView]=useState<import('../src/features/valuation/report-navigation').ReportView>(new URLSearchParams(location.search).get('reportView')==='breakdown'?'breakdown':'positions');useEffect(()=>{void fetch('/api/test-instrument-report').then(r=>r.json()).then(setReport);},[]);return <main className="mvp-page pnl-workspace">{report?<ResultWorkspace batch={report} currency="GBP" activeTab={view} onNavigate={setView}/>:<p>Loading synthetic report</p>}</main>;}
function MarkReviewFixture(){const [report,setReport]=useState<Batch>();useEffect(()=>{void fetch('/api/test-instrument-report').then(r=>r.json()).then(setReport);},[]);return <main className="mvp-page pnl-workspace">{report?<MarkOverrideReview batch={report}/>:<p>Loading synthetic review</p>}</main>;}
const mode=new URLSearchParams(location.search).get('mode');
function FutureConfiguration(){const [props,setProps]=useState<React.ComponentProps<typeof ProductConventionForm>>();useEffect(()=>{void fetch('/api/test-future-convention').then(r=>r.json()).then(setProps);},[]);return <main className="mvp-page"><h1>Futures convention acceptance</h1>{props?<ProductConventionForm {...props}/>:<p>Loading synthetic convention</p>}</main>;}
Object.entries(workspaceCssVariables).forEach(([name,value])=>document.documentElement.style.setProperty(name,String(value)));
function render(content:React.ReactNode){const helpPath=mode==='policy'?'/market-data/policies':mode==='structured'?'/instruments/autocalls/new':null;createRoot(document.getElementById('root')!).render(<ThemeProvider theme={workspaceTheme}><CssBaseline/>{helpPath?<PageHelp pathname={helpPath}/>:null}{content}</ThemeProvider>);}
const batch:Batch={batch_id:'synthetic-batch',status:'STAGED',staged_by:'maker',reviews:[],summary:{scope:'MARKET_ONLY',resultFormat:'POSITION_V2',marketPnl:'1',openingValue:'1',closingValue:'2',executionValue:'0',reportingCurrencyId:'gbp',externalComparison:'NOT_COMPARED',limitations:[]},items:Array.from({length:new URLSearchParams(location.search).get('many')==='true'?127:20},(_,i)=>({attribution_id:String(i),trade_id:null,position_key:String(i),subject_id:`00000000-0000-7000-8000-${String(i+1).padStart(12,'0')}`,version:1,market_pnl:'1',components:{PRICE:'1'},evidence:{}}))};
const ticketStrategy={strategyId:'00000000-0000-7000-8000-000000000555',strategyCode:'TEST',displayName:'Synthetic fund',status:'ACTIVE'};
const ticketContext={tenantId:'synthetic-tenant',bookedByUserAccountId:'synthetic-actor',properties:[],tags:[]};
if(mode==='reference-data')render(<ReferenceWorkspace tenantId="synthetic-tenant"/>);else
if(mode==='reference-catalogue')render(<ReferenceCatalogue tenantId="synthetic-tenant" catalogueId="00000000-0000-7000-8000-000000000777"/>);else
if(mode==='profile-cash-ticket')render(<TradeTicket listing={{referenceNodeId:'00000000-0000-7000-8000-000000000556',canonicalName:'Synthetic equity',marketVenueMic:'XLON',venueName:'London',tradingSymbol:'TEST',tradingCurrency:'GBP',status:'ACTIVE',isTradable:true}} strategies={[ticketStrategy]} context={ticketContext}/>);else
if(mode==='profile-forward-ticket')render(<FxForwardTicket initialInstrument={{instrumentId:'00000000-0000-7000-8000-000000000557',name:'Synthetic EUR/USD forward',baseCurrency:'EUR',quoteCurrency:'USD',quoteConvention:'USD_PER_EUR',agreedRate:'1.1',settlementDate:'2026-12-15',maturityDate:'2026-12-15',settlementType:'DELIVERABLE',termsFingerprint:'a'.repeat(64),bookingEligible:true}} strategies={[ticketStrategy]} context={ticketContext}/>);else
if(mode==='strategy-profile')render(<main className="mvp-page configuration-page"><StrategyTradeProfile tenantId="synthetic-tenant" strategyId="00000000-0000-7000-8000-000000000555"/></main>);else
if(mode==='trade-configuration')render(<TradeConfigurationConsole tenantId="synthetic-tenant" view={new URLSearchParams(location.search).get('view')??'profiles'}/>);else
if(mode==='structured')render(<AutocallForm/>);else
if(mode==='reporting')render(<main className="mvp-page reg-page"><PageHelp pathname="/regulatory-reporting"/><h1>Transaction reporting</h1><ReportingWorkspace permissions={new URLSearchParams(location.search).get('reader')==='true'?['REPORTING_READ']:['REPORTING_READ','REPORTING_CONFIGURE','REPORTING_PREPARE','REPORTING_REVIEW','REPORTING_EXPORT']}/></main>);else
if(mode==='future-convention')render(<FutureConfiguration/>);else
if(mode==='lifecycle-worklist-strict')render(<React.StrictMode><main className="mvp-page"><LifecycleWorklist tenantId="synthetic-tenant" actorId="operator" initial={{fromDate:'2026-10-01',toDate:'2026-12-01'}}/></main></React.StrictMode>);else
if(mode==='lifecycle-worklist')render(<main className="mvp-page"><PageHelp pathname="/lifecycle" embedded/><LifecycleWorklist tenantId="synthetic-tenant" actorId="operator" initial={{fromDate:'2026-10-01',toDate:'2026-12-01'}}/></main>);else
if(mode==='lifecycle-context')render(<main className="mvp-page"><BondRedemptionConsole actorId="operator" tenantId="synthetic-tenant" initialStrategyId="00000000-0000-7000-8000-000000000555" initialInstrumentId="00000000-0000-7000-8000-000000000556"/></main>);else
if(mode==='lifecycle-subscription')render(<main className="mvp-page access-admin-page"><PlatformLifecycleSubscription tenantId="synthetic-tenant"/></main>);else
if(mode==='lifecycle-strategy')render(<StrategyLifecycleAssistance tenantId="synthetic-tenant" strategyId="00000000-0000-7000-8000-000000000555"/>);else
if(mode==='lifecycle-downgrade')render(<LifecycleDowngradeWorkspace tenantId="synthetic-tenant"/>);else
if(mode==='styles')render(<StyleWorkspace/>);else
if(mode==='tenant-access')render(<TenantAccessConsole/>);else
if(mode==='policy')render(<main className="mvp-page"><PricingPolicyConsole options={{canManage:new URLSearchParams(location.search).get('reader')!=='true',cuts:[{id:'cut',label:'EoD'}],venues:[],instrumentTypes:[],calendars:[],strategies:[],datasets:[]}} initialPolicies={[{valuationPolicyId:'saved-policy',policyCode:'SAVED',displayName:'Saved version'}]}/></main>);else
if(mode==='imports')render(<ImportConsole tenantId="synthetic-tenant" canWrite={new URLSearchParams(location.search).get('reader')!=='true'}/>);else
if(mode==='organisations')render(<OrganisationConsole tenantId="synthetic-tenant"/>);else
if(mode==='labels')render(<ResultWorkspace batch={batch} currency="GBP" activeTab="positions" onNavigate={()=>{}}/>);else
if(mode==='instrument-report')render(<InstrumentReport/>);else
if(mode==='mark-review')render(<MarkReviewFixture/>);else
if(mode==='valuation')render(<main className="mvp-page"><ValuationConsole canCalculate={new URLSearchParams(location.search).get('reader')!=='true'} canReview={new URLSearchParams(location.search).get('reader')!=='true'} actorId="reviewer"/></main>);else
if(mode==='choice')render(<PagedValuationChoice kind="strategies" label="Strategy" name="strategy_id" value="item-500" initialChoices={[]} onChange={()=>{}}/>);else
render(mode==='display'?<MeasureCurrencyDisplay initial="both"><MeasureAmount measure={{localAmount:'100',currency:'USD',strategyAmount:'80',strategyCurrency:'GBP',status:'AVAILABLE'}}/></MeasureCurrencyDisplay>:mode==='cash'?<CashRegister canWrite/>:mode==='coupon'?<main className="mvp-page"><BondCouponConsole/></main>:mode==='access'?<Access/>:mode==='navigation'?<Navigation/>:<Ticket/>);
