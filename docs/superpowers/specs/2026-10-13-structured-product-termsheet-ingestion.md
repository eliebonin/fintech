# Structured-product termsheet ingestion

**Status:** Approved design; not implemented  
**Content type:** Specification  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-13

## Outcome and agreed scope

F54 will ingest termsheets into the structured-product creation inputs, generate
the schedule through the same builder used by manual creation, and support two
modes. ASSISTED loads an editable form before proposal submission. UNATTENDED
submits a complete, validated draft directly into checking without a user pressing
Create. Both retain the existing PENDING proposal and APPROVED/REJECTED decisions;
only approval materializes the instrument. This is instrument creation, not trade
booking. Unattended submission does not grant approval authority.

The user authorized building the foundation before testing real termsheets on
13 October 2026 and approved this written design, explicitly confirming that
ingestion covers all instrument terms: underlying instruments, issuer and other
parties, dates, currency, amount and payoff economics as well as the schedule.
Real-document extraction accuracy and production acceptance remain
unverified. Initial supported ingestion is the existing AUTOCALL,
AUTOCALL_CONSOLATION, PHOENIX and ATHENA templates with SINGLE, BEST_OF and WORST_OF
scope. Existing manual composed-option, range-accrual and supertracker creation
remain available; ingesting those templates and generic OTC swaps is deferred.
An out-of-scope document is retained for review, never coerced into an autocall.

## Existing boundaries and defects

- [Browser builder](../../../apps/ops-console/src/app/instruments/autocalls/new/form.tsx)
  selects template generators, displays editable rows and calls
  `buildAutocallDraftPayload`.
- [Schedule generation](../../../apps/ops-console/src/app/instruments/autocalls/new/schedule.ts)
  uses JavaScript numbers and weekend-only payment lags. The selected calendar's
  holidays are not consumed. Sharing this unchanged is insufficient.
- [Payload conversion](../../../apps/ops-console/src/app/instruments/autocalls/new/payload.ts)
  defaults invalid numeric inputs to zero and emits MANUAL submission metadata.
- [Python contract](../../../apps/reference_api/structured_product_contracts.py)
  validates the graph but ignores unexpected fields and supplies economic defaults.
  An offline probe accepted headline coupon 1.25 with row coupon 6.5.
- [Proposal workflow](../../../apps/reference_api/repository.py) validates active
  catalogue references and tenant-visible underlyings, supports retries, stages
  PENDING and materializes on approval. Source payload ownership must also be
  explicitly checked for this workflow; source IDs alone are insufficient.

See [root review findings](../../../FIX.md). These are current implementation
facts, not behavior to preserve for AI ingestion.

## Architecture choice

Use a server-authoritative Python builder with typed form inputs. The manual page
and ingestion orchestration call its preview operation, so they use one schedule
algorithm. Migrate the initial supported templates with parity fixtures before
switching the browser; keep presentation grouping and draft edit state in
TypeScript. Edited rows remain explicit contractual inputs and are revalidated.
Do not create a second Python generator alongside an authoritative browser one.

Alternatives considered: a shared TypeScript package would preserve more code but
require a Node execution boundary for unattended API clients; independent Python
and TypeScript generators would be easier initially but risk date/payoff drift.
The server builder fits the existing Python ownership of reference and calendar
data and allows direct machine submission without browser automation.

Implement a provider-neutral extraction adapter. A configured adapter may call a
structured-output provider; a fixture adapter supplies deterministic outputs for
tests. Provider/model configuration and credentials stay server-side. Missing
configuration returns a clear unavailable outcome, never simulated successful AI
extraction. No real-document uploads to an external provider occur during build
verification. Choosing and activating a live provider is a separate configuration
step, not a reason to postpone the adapter, inputs or workflow.

## Contracts and evidence

The versioned `structured-product-extraction.v1` envelope contains document ID and
SHA-256 digest, parser/prompt/schema version, completion status, field evidence,
economic inputs, schedule specification and unsupported clauses. Tenant/actor,
source-system ownership, approval state and internal reference IDs are supplied
or resolved by trusted orchestration, never accepted as model authority.

Each economic field has a nullable value, explicit unit, state and evidence.
States are EXTRACTED, DERIVED, MISSING, CONFLICTING, UNSUPPORTED and NOT_APPLICABLE.
EXTRACTED requires a source page and supporting text; DERIVED records the rule and
source inputs. Conflicts preserve alternatives. A schema-valid missing value
remains missing. Unknown properties are rejected at every ingestion object level.
All monetary/rate/level values use decimal strings; dates use validated ISO dates.
Units distinguish percentage points, decimal fractions, annual and per-period
coupons, absolute levels, percent of initial and percent of par. Never implicitly
equate an annual coupon with a period coupon. Conversion requires its stated rule.

The normalized form contract includes name/code, product subtype, currency,
issuer/guarantor/counterparty, notional where stated, effective/start/maturity
dates, underlying identifiers/fixings/participation, aggregation scope, coupon
and memory terms, final payment treatment, autocall levels/step/floor, KIP terms,
and schedule specification. Economic fields are required only where applicable
to the template, but missing required fields never receive UI demo defaults.
Internal technical row IDs/group codes are generated deterministically.

Keep initial fixing date/rule when the level is pending. Pending fixings are
editable review data and block submission in this slice because the current
creation contract requires a positive fixing. No synthetic fixing is inserted.

Reference resolution uses tenant-visible canonical identifiers and effective
mapping evidence. One eligible exact match can resolve; multiple or absent
matches return candidates/issues for review. A label-only fuzzy match cannot
authorize unattended submission. The server rechecks visibility at submission
and approval. Source-document/payload IDs must belong to the tenant and the
configured source system. Cross-tenant IDs must not disclose document contents.

## Schedule rules

Support EXPLICIT, RULE_BASED and RULE_WITH_EXCEPTIONS schedules. Coupon and autocall
streams can have separate dates and cadences. Explicit periods retain observation
and payment dates, coupon/barrier values and their evidence; do not collapse them
to one regular frequency. Exceptions address a stable stream/period, not an array
offset that changes when a row is added.

Generate only from an evidenced rule specifying anchors, frequency, end-of-month
behavior, stub handling, first eligible autocall date, calendar, business-day
convention and payment lag where relevant. Use governed dated holiday evidence.
Missing calendar coverage or an unsupported convention produces an issue rather
than weekend fallback. Explicit dates do not require guessing a calendar rule,
although their currency/calendar references must still resolve for creation.

Apply evidenced exceptions after generation. Compare explicit dates and rules
when both are present; a disagreement remains a blocking conflict. Regeneration
must not silently overwrite imported exceptions or human-edited rows. Ask the
user to choose preservation or replacement through the editing flow and record
the decision. Preserve legitimate variable coupon/barrier periods; reconcile
headline terms against the declared schedule model, not a blanket equal-rates
test that rejects step-up products.

## Preview, storage and submission

Proposed API boundaries:

- `POST /v1/structured-product-drafts/preview`: typed form inputs and optional
  explicit edited schedule; returns rows, canonical proposal payload, structured
  issues and readiness. Performs no instrument/proposal writes.
- `POST /v1/structured-product-ingestions`: tenant-scoped source intake and mode;
  stores a draft and runs the configured extractor and normalizer. Accept text
  with page boundaries and a bounded PDF intake adapter. Unsupported/scanned
  documents lacking a configured OCR/vision adapter return NEEDS_REVIEW.
- `GET /v1/structured-product-ingestions/{id}`: tenant-scoped draft, evidence,
  editable inputs, revisions, issues and any submitted proposal ID.
- `PATCH /v1/structured-product-ingestions/{id}`: validated user corrections with
  expected revision; retain original extraction, correction actor and evidence.
- `POST /v1/structured-product-ingestions/{id}/submit`: revalidate the latest
  revision and call the existing proposal service. UNATTENDED orchestration calls
  the same function automatically only when READY. Do not call approval.

Store tenant-owned intake records, immutable extraction/correction revisions and
source evidence through an explicit migration. Documents have bounded size/page
count, safe generated storage identity, supported content validation and digest.
Avoid storing large document bytes in proposal JSON. Retrieval/deletion follow
tenant ownership; operator errors/logs do not expose source text or secrets.

Readiness is READY, NEEDS_REVIEW or UNSUPPORTED. Each issue has code, field path,
message, severity and evidence references. Parser refusal/truncation/failure,
missing required terms, ambiguous references, pending fixings, economic conflicts,
unrepresented clauses and unsupported date rules prevent unattended submission.
Confidence is review metadata and cannot bypass a gate.

Enforce REFERENCE_PROPOSE for draft mutations and submission and REFERENCE_APPROVE
for decisions. Unattended workers act as an explicitly authorized tenant service
actor through the existing authority boundary. The model has no DB, submission,
approval or network-fetch tools. Termsheet text is data, not instructions.

Use tenant/source-scoped idempotency plus draft revision locking. Retrying an
identical revision returns the existing proposal; a changed payload with the same
key conflicts. After submission, preserve the submitted revision and proposal
link; further corrections start a new revision/replacement workflow rather than
mutating the checking payload. Recheck references and readiness inside the
submission transaction to avoid stale preview decisions.

## Frontend

Add termsheet intake to the existing structured-product creation page. ASSISTED
hydrates all inputs without demo defaults and opens the same editable schedule.
Show evidence and unresolved fields beside the relevant inputs; preserve the
original extraction when the user overrides a value. Display READY or blocking
issues before enabling submission. Successful submission navigates to the
existing proposal checking surface.

UNATTENDED intake shows extraction/review/submission status and the resulting
proposal link. Failed readiness leaves an editable draft instead of creating a
proposal. No separate approval button or automatic decision is added to ingestion.
Changing the mode never weakens validation or changes schedule economics.

## Verification and delivery boundary

Build synthetic page-labelled termsheets and independently authored expected
inputs/schedules. Cover regular and irregular schedules, independent Phoenix
cadences, step-down barriers, memory/final-payment behavior, holiday payment lags,
month-end/stubs, unsupported clauses, source conflicts, missing/pending fixings,
decimal precision and unknown fields. Assert exact builder outputs and manual vs
ingested parity, not just schema validity or successful HTTP status.

Test provider refusal/incomplete/malformed output, document instructions seeking
to change tenant/approval, ambiguous/cross-tenant references and source IDs,
concurrent duplicate submission, stale revision edits, revalidation after a
reference changes, and zero proposal/materialization writes on blocked drafts.
An unattended READY case must create one PENDING proposal with source evidence;
the existing approval path must create the same instrument graph as assisted
submission. Use an owned disposable PostgreSQL database for persistence tests.
Run focused Python, frontend and generated-contract checks; perform no production
DB migrations, restarts or external-provider calls during test verification.

Update F54's register/record/implementation map together with delivered evidence.
Keep real-termsheet accuracy, OCR/vision coverage, live provider activation,
browser acceptance and production acceptance explicitly NOT VERIFIED until tested.
Do not describe the synthetic-fixture suite as validating issuer document coverage.

## Best-practice evidence

Opened 2026-10-13. These are engineering recommendations, not financial rules.

- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
  documents schema-constrained output, refusals/incomplete responses and remaining
  content mistakes. Apply a typed provider adapter and independent semantic gates;
  using this source does not select OpenAI as the required provider.
- [OWASP prompt-injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
  recommends separating untrusted document parsing from privileged actions.
  Apply a tool-free extractor and trusted tenant-aware orchestrator.
- [OWASP improper output handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/)
  recommends validating model output before backend use and encoding display
  output. Apply strict ingestion schemas, economic checks and plain-text evidence.

The server builder, readiness names, initial template boundary and approval
integration are project design choices informed by the inspected implementation.
