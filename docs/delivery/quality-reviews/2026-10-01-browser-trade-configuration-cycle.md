# Browser acceptance: trade configuration → booking → history

Review date: 2026-10-01, Europe/London. Manual browser walkthrough of the current
production frontend build; not an automated end-to-end suite or production sign-off.

## Isolation and fixtures

The live app on port 3000 and its database were not changed. A new database,
`fortem_browser_review_c3b17aa3e76e41159d97e2e9dab8feb2`, was migrated to head
and loaded with deterministic synthetic demo data. A separate API on port 8001
and frontend on port 3001 used that database. Neither test booking sends an order.

Configuration, catalogue lifecycle, party selection and booking were exercised
through browser controls. Setup used the existing demo loader. One tag was
provisioned through the existing provisioning helper because tag-definition
management is not exposed in this UI. For the stronger tenant-isolation check,
the second synthetic tenant was given equivalent administrator/module fixtures
inside this database only; no real account's permissions were changed.

## Observed results

| Check | Browser evidence / result |
| --- | --- |
| Numeric field creation | Optional DECIMAL `TEST_ALLOCATION` published and appeared on the booking ticket. |
| Governed catalogue | Draft `ACCEPTANCE_BUCKETS` created; CORE and HEDGE entries added; catalogue published with a reason and acknowledgement. |
| Dropdown binding | `ACCEPTANCE_BUCKET` published against that catalogue using Use for a trade field; Manage values opened its source directly. |
| Required boolean | Required `ACCEPTANCE_CROSS` published with impact acknowledgement. Unspecified blocked review; error-summary link focused its input. No satisfied validation. |
| Representative booking | BUY 12 HSBC demo shares at GBP 8.125, Demo Income Strategy, counterparty HSBC Demo plc, broker Fortem Demo Management Ltd, trader MVP Operations Booker, Acceptance test tag, allocation 0, cross false, CORE — Core original. Review matched the intended values; saved detail and history showed the booking. |
| Immutable correction | CORE label corrected to Core corrected, record v2. Fresh ticket search showed v2's label; the existing booking retained Core original, v1. |
| Entry retirement | CORE v2 retired with reason/acknowledgement. Fresh search returned Hedge only; old booking retained Core original. |
| Field retirement | Test allocation retired. Fresh ticket no longer requested it; old booking still displayed numeric zero. |
| Sparse booking | SELL 1 at GBP 8.125 with required cross false; optional parties, bucket and tags blank. Review omitted blank properties; saved detail showed false, no tags and signed quantity -1. |
| Audit trail | UI displayed catalogue/field publications, record correction, record retirement and field retirement, with reasons and London timestamps. |
| Tenant isolation | Second tenant first denied access under its operations/module setup; with equivalent test permissions, history still showed zero trades, foreign detail showed no trade values, and its field/catalogue registers remained empty. |

Synthetic trade IDs:

- Representative BUY: `2595da0d-0a11-4a75-a00e-c7fc85f23eb4`.
- Sparse SELL: `4bd37db4-a315-42da-8317-e46a9bb6c089`.

One temporary browser tab was lost before any submission. It was reopened and
the draft re-entered; no duplicate booking was submitted. Final browser log
inspection returned no captured error/warning entries for the surviving tab.
This is not a claim that every earlier tab or server log was error-free.

## Findings and follow-ups

The presentation/validation findings below were subsequently addressed in the
[scoped browser follow-up](2026-10-01-trade-booking-browser-follow-up.md), which
records fresh tests, a reusable UI lifecycle regression and density evidence.
This initial review remains a historical record of the pre-fix observations.

1. Boolean entry uses Yes/No, but review/detail render `false`. Data is correct;
   use consistent human-readable Yes/No presentation in a later UI refinement.
2. An inaccessible/nonexistent foreign trade is labelled API UNAVAILABLE along
   with a not-found message. No information leaked, but the status wording
   misleadingly suggests an outage. Separate expected not-found/denied outcomes
   from service failure in a later change.
3. Required-field errors remained displayed after editing until Review booking
   revalidated the ticket. This is functional but can look stale; consider
   field-level error clearing/revalidation without weakening submit validation.
4. Three properties were manageable, with no collapsed validation targets, but
   the long execution/party/classification form still separates properties from
   review by substantial scrolling. This manual run does not settle the density
   decision: property-heavy tenants, larger catalogues, multiple devices and
   operator feedback remain necessary. No new layout is approved here.
5. Tag selection passed; tenant tag-definition management was not tested because
   it has no corresponding creation UI in this slice.

Large-catalogue paging, formal screen-reader testing, stale-page tenant-switch
write rejection, concurrent lifecycle/booking races and a reusable automated
browser regression suite were not exercised by this manual run. Existing unit
and backend tests are separate evidence; no new full suite was run here and no
application code was changed to address the findings.

## Local evidence and retained environment

Final historical-detail screenshot after both entry and field retirement:
`C:/Users/forte/Documents/ChatGPT/Tech V2/browser-cycle-history-after-retirement-20261001.jpg`.

The isolated database and app instance are retained for review, not deleted.
Local setup/instance metadata and logs live in
`C:/Users/forte/Documents/ChatGPT/Tech V2/` as `browser_walkthrough_setup.py`,
`browser_walkthrough_peer_fixture.py`, `browser-review-instance.json` and
`browser-review-*.log`. These are local artifacts, not deployed product scripts.
Cleanup must target only the exact review database and verified helper processes;
do not reuse broad database or process cleanup commands.

Related delivery notes: [booking property UI](../trade-booking-properties-ui-alpha.md)
and [governed configuration](../governed-trade-configuration-alpha.md).
