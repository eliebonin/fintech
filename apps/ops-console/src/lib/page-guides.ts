/** Static user guidance. Never an authority, validation or financial engine. */
export type PageGuide={title:string;purpose:string;steps:readonly string[];terms:readonly {term:string;meaning:string}[];impact:readonly string[]};

export const pageGuides={
 context:{title:'Choose your workspace',purpose:'Choose whose tenant permissions you are testing before opening a workflow.',
  steps:['Choose a tenant, then an existing user, and enter the workspace.','Use Platform administration for service-provider controls outside tenants.','Check the testing banner before making changes.'],
  terms:[{term:'Tenant',meaning:'An isolated company workspace with its own users, strategies and configuration.'},{term:'Testing as',meaning:'The selected user’s permissions apply; the real operator remains in audit evidence.'}],
  impact:['This is a development-only context switch, not production sign-in. Subsequent changes are real local-database writes.','Switching users does not make the same operator an independent valuation reviewer.']},
 platform:{title:'Tenant administration',purpose:'Manage company workspaces and module subscriptions from the service-provider context.',
  steps:['Find the tenant and inspect its status and subscriptions.','Use Edit tenant for descriptive information, or the explicit status action to suspend/reactivate.','Check the intended tenant before changing subscriptions.'],
  terms:[{term:'Subscription',meaning:'Makes a module available; user/group actions still control individual access.'},{term:'Suspension',meaning:'Blocks tenant access without deleting retained data.'}],
  impact:['Subscription/status changes affect access. Contact details do not create user accounts.','Module access does not grant provider-data licensing rights.']},
 access:{title:'Users, groups and strategy access',purpose:'Control which people can perform which actions within this tenant.',
  steps:['Review the user’s active group memberships.','Configure actions and strategy scope together within a group.','Review the impact before saving; use the strategy matrix to inspect effective access.'],
  terms:[{term:'Module vs action',meaning:'The tenant needs the subscription; the user also needs the action grant.'},{term:'ALL / SELECTED strategies',meaning:'ALL includes future strategies. SELECTED covers only chosen strategies; an empty selection grants none.'},{term:'Tenant administrator',meaning:'Can manage access, but still needs operational group grants to book or calculate.'}],
  impact:['Saving changes affects access. An action in one group does not combine with strategy scope from another.','Removing access does not delete historical transactions or audit evidence.']},
 effectiveAccess:{title:'Effective access',purpose:'Understand why the current user can or cannot perform an action.',
  steps:['Inspect subscription and membership state.','Expand the action and its source groups.','Ask an authorised administrator to change missing grants.'],
  terms:[{term:'Effective access',meaning:'Current subscriptions, membership, active group actions and applicable scope together.'},{term:'Explanation',meaning:'Permission facts, not a way to grant yourself access.'}],
  impact:['Inspection is read-only. The backend checks authority again when an action is attempted.']},
 organisations:{title:'Tenant organisations',purpose:'Select existing legal entities for counterparties and executing brokers, with private tenant labels and notes.',
  steps:['Use My organisations for the tenant register, or Add organisation to search platform records.','Open Manage to edit private settings and select supported trading roles.','Review and explicitly activate a curated role list only when ready.'],
  terms:[{term:'Shared identity / private settings',meaning:'Legal identity is shared; tenant labels, internal codes and notes are private.'},{term:'Counterparty / executing broker',meaning:'Independent roles: selecting one does not select the other.'},{term:'Curated list',meaning:'Restricts future selections. An explicitly empty list permits no organisations for that role.'}],
  impact:['Adding notes does not activate a restricted list. Missing tenant lists retain existing shared eligibility.','Selection is not KYC or credit approval and does not rewrite historical trade labels.']},
 tradeFields:{title:'Trade configuration',purpose:'Maintain traders, typed custom fields and governed choices used by booking tickets.',
  steps:['Inspect existing definitions before adding another.','Define a field’s meaning/type; maintain the choice catalogue for dropdown fields.','Review the change reason and save. Manage counterparties and brokers under Organisations.'],
  terms:[{term:'Definition vs value',meaning:'Configuration defines the field and permitted choices; each trade records its own value.'},{term:'Choice catalogue',meaning:'A controlled list, not free text. Retired choices should not be reused for a different meaning.'}],
  impact:['Configuration changes future selections/validation, not historical booked evidence.','Create a new definition rather than repurposing an unrelated field’s meaning.']},
 strategies:{title:'Strategies',purpose:'Find tenant strategies you can read, or create one if authorised.',
  steps:['Open a strategy for positions, monetary measures and calendars.','Use the separate creation page and choose the correct operating model.','Grant group actions and strategy scope through access management.'],
  terms:[{term:'Strategy type',meaning:'Classifies a fund, mandate, managed account, prop sleeve or model; it is not a permission grant.'},{term:'Base currency',meaning:'The strategy reporting currency, distinct from instrument/trade currencies.'}],
  impact:['Creating a strategy does not automatically grant everyone access or create holdings.','The register is not a published NAV or accounting ledger.']},
 strategy:{title:'Strategy workspace',purpose:'Inspect dated holdings, contributing movements, monetary measures and associated calendars.',
  steps:['Choose the view and inspection date/basis.','Open a position to inspect its signed movements and running quantity.','For Measures, choose an eligible policy and inspect amounts/evidence. Use Calendars to inspect applicable coverage.'],
  terms:[{term:'Running quantity',meaning:'Buys/sells and supported adjustments accumulate; a partial sale leaves the remaining position open.'},{term:'Listing position',meaning:'Different listings remain separate operational positions.'},{term:'Monetary measures',meaning:'Instrument-specific notional/exposure measures are not automatically NAV assets or contract MTM.'}],
  impact:['Inspection/measure previews do not book trades, perform FIFO/tax accounting or publish P&L.','Missing marks remain unavailable, not assumed zero. Dated cash snapshots are separate.']},
 booking:{title:'Book a trade',purpose:'Record an actual execution against an eligible strategy and instrument/listing.',
  steps:['Choose the strategy, find the reference and check booking readiness.','Enter dates, direction, quantity basis and the product-specific price/rate.','Add parties, tags/properties and submit once after review. Retain the original retry if the outcome is unknown.'],
  terms:[{term:'Units / contracts / notional',meaning:'Use the quantity basis shown for this product; these are not interchangeable.'},{term:'Clean / dirty bond price',meaning:'Dirty already includes accrued interest; do not add it a second time.'},{term:'Effective valuation date',meaning:'Optional standard recognition date, distinct from execution, settlement and information availability.'}],
  impact:['Submission writes attributed execution evidence. It does not imply settlement or create counterparty cash balances.','Correction-prefilled tickets use the supported replacement workflow, not an unrelated duplicate execution.']},
 tradeHistory:{title:'Trade history and corrections',purpose:'Inspect recorded executions, original economics and later correction/lifecycle evidence.',
  steps:['Apply date/search filters and page through the filtered history.','Open a trade for frozen terms, parties, properties and events.','Use available cancel/correct actions with a reason only for record corrections.'],
  terms:[{term:'Recent history',meaning:'The default two-week window is a filter, not deletion of older trades.'},{term:'Cancel / replace',meaning:'Original records remain. An actual opposite market execution is a new trade.'}],
  impact:['Inspection changes nothing. Corrections can require valuations to be reassessed.','Some legacy records have cancel-only recovery rather than supported replacement.']},
 lifecycle:{title:'Maturity processing',purpose:'Close supported matured exposure through an Ops-controlled workflow, separately from cash/payment accounting.',
  steps:['Select Bonds or FX forwards and inspect eligible exposure and terms.','Check the configured preparation/posting path and closure economics.','Post when Ops is ready, or review the prepared entry before approval; inspect the linked audit afterwards.'],
  terms:[{term:'Closure',meaning:'Brings compatible open exposure to zero. Passing maturity alone is not a booking.'},{term:'FX spot suggestion',meaning:'A sourced maturity-day suggestion with warnings, not a guaranteed contract settlement rate.'},{term:'Payment',meaning:'Cash delivery and confirmation are separate from exposure closure.'}],
  impact:['Posting creates a retained lifecycle booking; preview/preparation is not posting.','Current handling is bounded to plain-bond redemption and deliverable FX-forward maturity, not every derivative lifecycle.']},
 valuation:{title:'Valuation and P&L',purpose:'Calculate a reproducible strategy result, review it in staging and explicitly publish an accepted version.',
  steps:['In Input form choose strategy, dates, currency and policy version; supply required daily inputs.','Calculate and inspect Results, component amounts, actual price dates, FX and applied-rule evidence.','Resolve failures or amend supported staged attributions with reasons; complete review and publish explicitly. History contains run logs.'],
  terms:[{term:'Completed + staged',meaning:'Calculation succeeded; the result is not yet published/final.'},{term:'Information cutoff',meaning:'Limits what received data/ledger evidence the run knows; not the market date a price describes.'},{term:'Daily interest vs coupon payment',meaning:'Daily earned accrual contributes to daily P&L. Confirming a coupon does not recognise accumulated income again.'}],
  impact:['Calculation retains frozen inputs. Publication is a separate authorised action; self-publication needs the configured exception.','Changed source trades may require reassessment and block stale staged publication. Published evidence is retained, not silently repriced.','Supported economic P&L is not a complete fund NAV, settlement or accounting service; inspect stated limitations.']},
 cash:{title:'Cash balances',purpose:'Record end-of-day cash snapshots by strategy, currency and holding company.',
  steps:['Choose the strategy/value date, currency and company holding the cash.','Enter the actual balance with useful notes/source context and save the revision.','Inspect retained versions and use the appropriate dated snapshot for valuation.'],
  terms:[{term:'Balance snapshot',meaning:'A stock for its value date, not a new cash flow accumulated daily.'},{term:'Holding company',meaning:'The custodian, broker or exchange holding the cash.'}],
  impact:['Saving does not book a security trade or unwind yesterday’s balance.','Deposits/withdrawals and snapshot changes must not be mistaken for investment profit.']},
 policies:{title:'Pricing policies',purpose:'Specify which observations are eligible for reproducible valuation.',
  steps:['Select a saved version; use Configuration to prepare a new immutable version.','Set explicit/default rules and check compatibility before saving.','Preview the saved version with dates/references and inspect chosen values/evidence. Reference explains source definitions.'],
  terms:[{term:'Strict / flexible',meaning:'Strict requires explicit rules. Flexible uses configured defaults only when no explicit rule matches; missing data for a matching rule does not fall through.'},{term:'As-traded price',meaning:'Compatible with booked units; split-adjusted data requires verified conversion when permitted.'},{term:'Freshness',meaning:'Prior-session data requires a finite allowance; flexible does not mean any old price.'}],
  impact:['Save creates a version, not an edit of frozen runs. Preview uses saved configuration, not unsaved edits.','Matching definitions still require source permissions/context. Saving does not grant data rights.']},
 sources:{title:'Market-data sources and priorities',purpose:'Inspect provider datasets, licensed scopes and priorities among eligible observations.',
  steps:['Inspect the provider/dataset and recorded scope.','Review priorities for the relevant instrument type/scope; change only authorised controls.','Check policy compatibility/coverage for the actual instrument/date.'],
  terms:[{term:'Provider / dataset / scope',meaning:'A provider can supply separate feeds/licensed universes. Access to one is not access to all.'},{term:'Priority',meaning:'Ranks only observations already meeting policy, definition and licensing requirements.'},{term:'Tenant data',meaning:'Private uploads still need valid definitions, dates and eligible source configuration.'}],
  impact:['Reordering cannot bypass rights, missing prices or policy restrictions.','Display, reporting and automated valuation uses are distinct; this page is not legal licensing clearance.']},
 calendars:{title:'Calendars',purpose:'Inspect governed open/closed sessions and holiday coverage used by data and strategy workflows.',
  steps:['Choose the calendar/version and inspect source and coverage.','Check holidays/early closes rather than assuming weekdays.','Inspect fund/strategy-specific composition and overrides in their owning workflow.'],
  terms:[{term:'Published calendar',meaning:'A retained version with source/coverage evidence, not a guess about an uncovered date.'},{term:'Exchange vs fund calendar',meaning:'Funds/strategies can use different closure rules, including combined calendars.'}],
  impact:['Missing/inapplicable coverage can block input selection or schedule generation.','Inspection does not change instrument terms, settle a trade or publish valuation.']},
 explorer:{title:'Market-data explorer',purpose:'Inspect stored time series and provenance, rather than a live trading feed.',
  steps:['Search a reference and choose the actual series definition/source.','Apply the date window to refresh history.','Inspect observation/receipt dates, currency and price basis before use.'],
  terms:[{term:'RAW / split-adjusted / provider-adjusted',meaning:'Different quantity/income bases, not interchangeable closes.'},{term:'Observation vs receipt date',meaning:'The market date described by a value differs from when it was received.'}],
  impact:['Inspection does not ingest data or make it valuation-eligible. Coverage/entitlement checks remain separate.']},
 coverage:{title:'Market-data coverage and evidence',purpose:'Explain whether references have eligible inputs for the requested policy/date.',
  steps:['Choose the policy/context, date and references.','Inspect selected inputs and exceptions.','Resolve missing rules, dates, rights or conventions in the owning workflow.'],
  terms:[{term:'Available vs eligible',meaning:'A stored observation may fail policy, freshness, quantity-basis or licensing checks.'},{term:'Frozen evidence',meaning:'Retained inputs/decisions, not permission to replace them silently with newer marks.'}],
  impact:['A selection/coverage check is not a staged/published financial result. Do not relabel provider data without evidence to bypass a failure.']},
 instruments:{title:'Instruments and listings',purpose:'Find economic references and venue listings, or submit definitions for review.',
  steps:['Search and open the required economic instrument/listing.','Inspect terms, currencies, identifiers and parent/listing relationships.','Use Create instrument for definitions, and Requests/Operations for review.'],
  terms:[{term:'Canonical instrument',meaning:'The economic/security definition; listings describe venue-specific representations.'},{term:'Request vs approved reference',meaning:'Submission is a proposal; approval/materialisation is separate.'}],
  impact:['Reference creation does not book trades, load prices or establish valuation support.','Record executions through the dedicated Book trade page.']},
 review:{title:'Reference review and operations',purpose:'Review proposed reference changes and evidence before an authorised decision.',
  steps:['Open the relevant request; not every queue item is a new instrument.','Review terms, dependencies and evidence.','Approve/reject only with available authority; resolve conflicts rather than rewriting history.'],
  terms:[{term:'Proposal',meaning:'Prepared reference information, not yet an approved economic definition.'},{term:'Listing request',meaning:'A venue-specific definition linked to a parent; it can appear in Operations.'}],
  impact:['Approval can create references and dependent terms. It is not execution, price validation or valuation publication.']},
 listing:{title:'Create a listing',purpose:'Describe how an existing economic instrument is identified/traded on a venue.',
  steps:['Check the selected parent; instrument context should prefill it.','Enter venue, symbol, quote currency and applicable factors.','Submit the proposal and follow review in Operations.'],
  terms:[{term:'Parent',meaning:'The economic contract/security, not another copy for each exchange.'},{term:'Listing factors',meaning:'Quote/unit conventions must agree with booking basis; do not duplicate a futures contract multiplier.'}],
  impact:['Submission does not immediately create an approved listing or position.','Different listings remain separate operational positions.']},
 conventions:{title:'Booking conventions and schedules',purpose:'Inspect approved economics and conventions used to interpret executions.',
  steps:['Check instrument, terms version and applicable dates.','Inspect quantity basis, price/rate interpretation, currency and factors or contractual events.','Use supported authorised configuration/proposal actions with retained reasons/evidence.'],
  terms:[{term:'Frozen convention',meaning:'Existing executions retain their saved evidence, not today’s replacement settings.'},{term:'Schedule',meaning:'Expected contractual dates/actions, not actual payment or settlement evidence.'}],
  impact:['Missing/unsupported conventions can block booking/valuation. Never invent default economics to pass readiness.']},
} satisfies Record<string,PageGuide>;

const creationTerms:Record<string,{title:string;terms:PageGuide['terms']}>= {
 autocalls:{title:'Structured-product creation',terms:[{term:'Parent and underlyings',meaning:'This issued product owns the payoff; references and product-specific fixings drive its components.'},{term:'Schedule, barriers and memory',meaning:'Contractual observation/payout rules, not simulated performance or prices.'}]},
 swaps:{title:'Swap creation',terms:[{term:'Funded / funding reference',meaning:'The return-bearing instrument and optional financing reference; spread belongs to funding terms.'},{term:'Units, notional, leverage',meaning:'Contract basis and leverage must be explicit; trade quantity and contract nominal are not interchangeable.'},{term:'Reset / maturity',meaning:'Terms describe timing; they do not automatically book resets, closure or cash.'}]},
 futures:{title:'Futures contract creation',terms:[{term:'Family / contract / listing',meaning:'Shared conventions, a dated canonical maturity, then venue-specific symbols.'},{term:'Multiplier / month code',meaning:'Verify contract size, price-to-money convention, delivery month and year format.'},{term:'Physical / crypto delivery',meaning:'Creation support does not enable every delivery or booking workflow.'}]},
 'future-families':{title:'Futures families',terms:[{term:'Family',meaning:'Common underlying, currency, multiplier and delivery conventions for dated contracts.'},{term:'Delivery cycle',meaning:'Listed months, month codes and year-digit format identify contracts; a symbol alone is not proof of terms.'}]},
 bonds:{title:'Bond creation',terms:[{term:'Currency / nominal',meaning:'Contractual currency and redemption/quote basis, not a particular trade amount.'},{term:'Coupon / maturity',meaning:'Interest and redemption terms; an expected schedule is not payment confirmation.'}]},
 'fx-forwards':{title:'FX-forward creation',terms:[{term:'Base / quote',meaning:'The orientation of the agreed exchange rate.'},{term:'Agreed rate / maturity',meaning:'Contract exchange economics/end date; daily marks and cash delivery are separate facts.'}]},
 options:{title:'Option creation',terms:[{term:'Call/put, strike and expiry',meaning:'Contractual rights/exercise terms, not the premium paid on a particular trade.'},{term:'Underlying / multiplier',meaning:'Reference asset and contract size needed to interpret quantities/prices.'}]},
 funds:{title:'Fund creation',terms:[{term:'Fund / share class',meaning:'The vehicle and, where applicable, a currency/fee share class.'},{term:'NAV date',meaning:'The date a NAV describes, distinct from later publication/sign-off.'}]},
 etps:{title:'Exchange-traded product creation',terms:[{term:'Product / listing',meaning:'Define the economic product; add venue-specific listings after approval.'},{term:'Issuer / wrapper',meaning:'Legal party and structure, not a trade counterparty or settlement confirmation.'}]},
 indices:{title:'Index creation',terms:[{term:'Index',meaning:'An economic reference level, not automatically a directly tradable security.'},{term:'Currency / family',meaning:'Measurement currency and applicable reference classification.'}]},
 'index-families':{title:'Index-family creation',terms:[{term:'Family',meaning:'Classification shared by related index references, not a traded position.'}]},
 crypto:{title:'Digital-asset creation',terms:[{term:'Asset / currency / venue listing',meaning:'Asset identity differs from the quote currency and exchange-specific trading pair.'}]},
};

const creationGuides:Record<string,PageGuide>=Object.fromEntries(Object.entries(creationTerms).map(([key,value])=>[key,{
 title:value.title,purpose:'Describe the economic reference and contractual terms before trading use.',
 steps:['Check for an existing reference to avoid duplicates.','Complete applicable identity, parties and terms; review dependency/schedule warnings.','Review and submit through the controlled approval workflow.'],terms:value.terms,
 impact:['Submission is not approval and creates no execution, cash, price history or published valuation.','Reference creation support does not establish booking/valuation readiness for every product variant.'],
}]));

type GuideId=keyof typeof pageGuides;
const exactRoutes:Record<string,GuideId>={
 '/select-context':'context','/select-tenant':'context','/platform/tenants':'platform',
 '/tenant-profile/access':'access','/tenant-profile/effective-access':'effectiveAccess','/tenant-profile/organisations':'organisations','/tenant-profile/trade-configuration':'tradeFields',
 '/strategies':'strategies','/strategies/new':'strategies','/trades/new':'booking','/trades/lifecycle':'lifecycle','/trades':'tradeHistory',
 '/valuation':'valuation','/valuation/cash-balances':'cash',
 '/market-data/policies':'policies','/market-data/sources':'sources','/market-data/calendars':'calendars','/market-data/explorer':'explorer','/market-data/coverage':'coverage',
 '/instruments':'instruments','/instruments/create':'instruments','/instruments/new':'instruments','/instruments/requests':'review','/operations':'review','/instruments/listings/new':'listing',
};

/** Exact routes precede anchored detail routes; unsupported paths get no misleading fallback. */
export function getPageGuide(pathname:string):PageGuide|undefined {
 const path=pathname.split(/[?#]/,1)[0].replace(/\/+$/,'')||'/';
 const exact=Object.hasOwn(exactRoutes,path)?exactRoutes[path]:undefined;if(exact)return pageGuides[exact];
 const creation=path.match(/^\/instruments\/([^/]+)\/new$/);
 if(creation)return Object.hasOwn(creationGuides,creation[1])?creationGuides[creation[1]]:undefined;
 if(path==='/instruments/future-families')return creationGuides['future-families'];
 if(/^\/strategies\/[^/]+$/.test(path))return pageGuides.strategy;
 if(/^\/trades\/[^/]+$/.test(path))return pageGuides.tradeHistory;
 if(/^\/instruments\/[^/]+\/listings\/new$/.test(path))return pageGuides.listing;
 if(/^\/instruments\/[^/]+\/(booking-conventions|terms-schedule)$/.test(path))return pageGuides.conventions;
 if(/^\/instruments\/[^/]+$/.test(path))return pageGuides.instruments;
 if(/^\/(reference-data|instruments\/crypto)\/review\/[^/]+$/.test(path))return pageGuides.review;
 if(/^\/market-data\/resolution-snapshots\/[^/]+$/.test(path))return pageGuides.coverage;
 return undefined;
}
