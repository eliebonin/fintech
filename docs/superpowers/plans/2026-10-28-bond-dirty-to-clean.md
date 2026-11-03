# Bond DIRTY-to-CLEAN implementation plan

> Execute sequentially, test-first. User selected normalization rather than all-in DIRTY attribution. Preserve the dirty checkout; no subagents, automatic commits or operating financial writes.

**Goal:** Consume an eligible DIRTY quote minus its matching quoted accrued-interest component, then retain the existing separate daily-interest and accrued-stock FX paths.

**Architecture/design:** Store a typed immutable quote-accrual component against the exact source price observation. It inherits that observation's subject, currency, dataset/licence, market date and correction identity. Keep quote settlement date, explicit source reference and recording time. Source price and trades remain unchanged; the derived CLEAN price and component proof are frozen into the result. Quote accrual is not a strategy accrued balance or daily earnings input.

**Tech stack:** Python Decimal, SQLAlchemy/PostgreSQL, current provider-neutral ingestion, economic P&L and React inspector.

**Spec:** This document records the approved second approach from 28 October: DIRTY − matching quoted accrued = CLEAN, with no inference from dirty-price movements and no double-counting of interest/FX. The existing three strategy datasets remain separate. Matching quote evidence is mandatory to determine the CLEAN price; daily interest remains optional unless explicitly required.

## Constraints and review focus

- Pair with the exact observation, including its per-100 convention and source quote settlement date; never borrow another provider/date's accrual or a trade/strategy accrued amount.
- Preserve native RAW price basis, policy/provider ranking, licence/display/valuation rights, actual price date, information cutoff and correction provenance. Missing/late quote evidence is not zero.
- Quoted accrual can be zero or negative for ex-coupon conventions; resulting CLEAN price must satisfy current plain-bond price validation. No floating-point conversion or silent rounding.
- Keep daily earned interest, coupon/payment-only handling and opening accrued-stock FX unchanged after normalization. Dirty execution normalization remains independent and applies once.
- Quote-component corrections create a new price-observation revision even when the DIRTY number is unchanged. Published results remain frozen; stale staged normalized inputs must be reassessed before publication.
- No automatic accrual/coupon calculation, new provider fetch, reference-data overhaul, bond subtype expansion or public market-data file-upload UI.

## Tasks

- [x] **1 — Quote evidence and math:** Typed per-100 contract, exact/signed subtraction, immutable sidecar and migration 103; controlled batched source-bound writer/load and cutoff checks.
- [x] **2 — Ingestion:** Optional bond point fields and source dimensions, atomic pairing, idempotent duplicate detection and same-price/component-only revisions; existing Yahoo/non-bond regression passed.
- [x] **3 — Valuation:** Source DIRTY and derived CLEAN frozen separately; separate daily earnings, bought accrued and stock FX preserved, with coupon-reset and monetary-preview checks. RAW/share adjustment basis stays independent.
- [x] **4 — Review and display:** Readable exact conversion/applied rule, current source-pair/access checks at publication and isolated responsive browser acceptance. Ordinary review/amendment controls retained; no new amendment behavior introduced.
- [x] **5 — Documentation and activation:** Root/capability/methodology references reconciled, focused checks passed; migration 103 applied and API 8001 restarted with user approval. No operating financial writes or rights changes.

## Research / execution ledger

Sources rechecked 28 October: [MSCI methodology, April 2022](https://www.msci.com/eqb/methodology/meth_docs/MSCI_FI_Index_Calculation_Methodology_April2022.pdf) defines dirty = clean + accrued; [S&P methodology, March 2025](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-fixed-income-index-math.pdf?force_download=true) separates price and interest return and accounts for coupon detachment. We use those economic distinctions, not their index-specific weight, reinvestment or missing-price policies.

Ruling: typed observation-linked sidecar instead of a separately ranked accrued series — price and quote component are one source package, sharing licence/provenance and correction. This avoids accidentally selecting a different provider/date's amount. The component's recording time still respects the information cutoff. It is not a generic strategy balance source.

Delivery: [implementation, tests, activation and remaining limits](../../delivery/bond-dirty-to-clean-20261028.md).
46 offline, 25 paired-quote/accrued integration and 54 adjacent regression cases
passed; the final 10 native bond cases were rerun after separating adjustment
basis from CLEAN/DIRTY. 20 frontend cases, TypeScript, OpenAPI parity and one
isolated Edge scenario passed. No full Python suite was run. User approved local
migration 103/restart; revision/table and API health were confirmed. All financial
tests used synthetic data in owned disposable databases.
