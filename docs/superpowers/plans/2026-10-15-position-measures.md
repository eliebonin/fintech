# Position monetary measures implementation plan

Execution: sequential in the existing checkout, preserving unrelated work; no
subagents, commits, operating seeds or P&L publication changes.

Goal: independent, read-only monetary measures, not NAV weights or P&L.
The approved design is the conversation: equal cash-security measures; bond dirty
price first, otherwise clean plus assessed accrued balance; bounded delta-one swap
reference notional, underlying-equivalent exposure and whole-swap MTM separately.

Architecture: exact Decimal kernel in valuation/position_measures.py; governed
input adapter in valuation/measure_inputs.py; scoped strategy preview endpoint
and a separate Measures strategy tab. Reuse holdings reconstruction, policy date,
calendar, rights and FX resolution. Source observations and booking versions stay
retained in existing storage; response includes input evidence and hash. Preview
is not a published result and has no aggregate NAV/weights.

1. Write failing numerical tests for signs, quote factors, leverage once, dirty
   preference, clean/accrual fallback, incomplete inputs, zero and negative MTM.
   Implement the pure kernel; prove the tests pass.
2. Add dimension-constrained resolution to the existing resolver so bond CLEAN
   and DIRTY candidates cannot be mixed. Existing callers remain unchanged.
   Adapter checks frozen units/terms, currencies, compatible as-traded price
   basis, sealed calendars, current display and valuation rights and scoped actions.
   Missing inputs block individual measures, never become zero. Cross-listing
   bond accrual without safe position assessment is explicitly unsupported.
3. Add a read-only strategy measures endpoint and separate server-rendered tab,
   selected policy/date, native and strategy-currency amounts and expandable
   evidence. All input selection stays on the backend; no browser financial math.
4. Run focused unit/API/component regressions, TypeScript and contract freshness;
   activate local API, verify normal reads, update methodology/capability references.

Constraints: no pricing models, weights, interim reset engine, autocall swap
valuation, option/future/FX-forward measures, arbitrary price fallback or general
regulatory risk claim. A valid zero is distinct from unavailable. Swap marks are
whole-swap values, not underlying prices. NOMINAL swap exposure stays unavailable
without explicit equivalent units/reset basis. Sealed historical pricing coverage
is not inferred. No changes to operating policies/rights to make previews pass.

Review focus: permissions before reconstruction; denied source values never leak;
unknown currency and quote basis cannot acquire an assumed factor; accrued stocks
must not use daily earnings/trade accrual; multiple incompatible swap booking
versions cannot merge; historical dates remain independent of current wall clock.

## Execution ledger

- Implemented the exact kernel, governed adapter, scoped read-only endpoint and
  separate Strategy Measures tab. No migration or operating financial write.
- Final focused backend run: 49 passed; frontend/read-deadline checks: 15 passed.
  TypeScript and API contract freshness passed. Full suite deliberately not run.
- Swap exposure is bounded to frozen canonical index units; native INDEX_LEVEL
  selection remains distinct from PRICE/CLOSE. Unsupported interim resets and
  shared bond accrued-balance allocation remain explicitly unavailable.
- Activated the API. Live read-only preview returns all three measures for nine
  Strat Testing equities with reporting FX. Mock swap reference notionals are
  available locally; swap/index/FX policy gaps remain visible, not auto-configured.
- Preview evidence is returned, not persisted as a staged/published valuation.
  See the delivery record for formulas, checks and outstanding limitations.
- Authenticated live-page rendering passed; temporary test session revoked.
  Diff whitespace check passed. No manual visual acceptance or full-suite claim.
- Subsequent authorized remediation fixed native split-mark safety and frozen
  fund-share-class recognition; their expected failures became ordinary passing
  regressions. Added owned synthetic index input setup and a separate mock policy,
  valid from existing USD/GBP coverage on October 8. Final affected run: 111 pass;
  live API returns all three native/GBP measures for all 11 positions. See the
  delivery record's remediation section for rights/date boundaries and evidence.
