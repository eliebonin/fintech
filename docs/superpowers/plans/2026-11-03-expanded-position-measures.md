# Expanded position-measure coverage

> **For agentic workers:** Use superpowers:executing-plans sequentially. The user requested priority 6; no new plan approval is needed. Preserve the in-progress priority 1–3 changes.

**Goal:** Expose supported native and strategy-currency measures for spot crypto, dated linear crypto futures, listed vanilla options, fully funded notes and supplied-mark swaps, independently of unsupported risk measures.

**Architecture:** Reuse governed selection, current DISPLAY rights, reporting FX, immutable booking validation and maintained bond stocks and the existing note-specific assessed bridge. Add focused product contract adapters below HTTP. No changes to daily P&L, trades, source data, permissions, NAV weights or publication.

**Tech Stack:** Existing Python Decimal, SQLAlchemy/PostgreSQL, FastAPI adapter and Next.js report.

**Spec and evidence:** [Coverage decisions and research](../../delivery/expanded-position-measures-20261103.md). The referenced recommendation explicitly permits incomplete risk-exposure coverage.

## Scope and definitions

- Spot DIGITAL_ASSET: three equal signed quote-currency values, using the selected listing's price and frozen factors. No exchange substitution.
- Dated linear futures: current notional/exposure = signed contracts × exact contract price × frozen monetary multiplier / divisor, for INDEX_POINTS and UNDERLYING_UNIT, cash or physical. No inverse/quanto inference, delivery cash or clearing MTM.
- Listed vanilla options: market value = signed contracts × canonical premium × premium multiplier / divisor. Reference is explicitly labelled contractual strike notional = signed contracts × deliverable units × strike, in strike currency. It is not current underlying value or delta exposure. Economic exposure needs governed sensitivities and stays unavailable in this slice.
- Fully funded notes: percentage-quoted reference = signed nominal (or units × denomination); unit-price reference is a labelled current funded-value proxy. Whole-note market value uses compatible quotation and DIRTY precedence, or CLEAN + an exact-date assessed note closing bridge with matching eligible nominal. No second accrual addition. Underlying risk exposure remains unavailable unless the user explicitly chooses a labelled proxy.
- Performance and rate-exchange swaps: validate original whole-contract units, reference notional and quote factors. Reference = booked nominal or units × reference/unit; market value = booked quantity × whole mark / divisor. Embedded funding, leverage and orientation are not reapplied to the mark. Existing supported unit-index exposure remains; other underlying/reset risk models remain unavailable.
- Each measure can fail independently. Missing mark does not erase a known reference amount; missing FX preserves the native amount. Exact zero remains zero. Do not add an unstated zero after maturity/expiry.

## Tasks

- [x] Add failing focused product-measure and independent-availability regressions.
- [x] Extend spot crypto and dated linear futures using native frozen units and exact contract dimensions.
- [x] Add shared read-only booking validation and option/note adapters; retain original version identities, source restrictions and current accrued stock checks.
- [x] Expand supplied whole-swap reference/market values without inventing risk exposure; isolate risk-only restrictions.
- [x] Add visible basis explanations and product-specific inputs to the existing measure inspection UI, with focused tests.
- [x] Run affected product/measure/access regressions, types/schema parity and read-only local acceptance; update maintained capability, methodology and finding references.

## Review focus

- Premium multipliers and deliverable units are distinct; apply each only to its own measure.
- Native/strike/underlying/reporting currencies must never be relabelled.
- Dirty mark plus separate balance is never added twice; missing stock is not zero.
- Intermediate resets may constrain inferred exposure without invalidating a supplied whole-swap mark.
- Incompatible contracts and stale sources remain explicit; do not weaken booking or rights checks to improve coverage.

Implementation discovery: bond history intentionally excludes conditional notes. Reuse the existing governed CLEAN-note assessed bridge; do not pass note sources through bond coupon reconstruction. The user explicitly agreed to leave unmodelled option/note risk exposure unavailable.

## Completion evidence

174 affected backend regressions passed. Live follow-ups passed 46 missing-price/permission checks and 42 forward/product checks. These suites overlap and are not summed. Frontend: 21 rendering/formatting checks and TypeScript; OpenAPI parity and secret scan passed. No full Python suite was run. API/frontend activated; existing FCPGF read-only pages and option/forward/swap inspection verified. No operating financial writes or schema migration.

Conditional notes use their existing exact-date assessed closing bridge, not bond coupon reconstruction. Risk-only limitations remain explicit by user agreement. Whole-portfolio reconciliation, persisted/published measures and production scaling remain outside this completed slice.
