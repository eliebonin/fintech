# Reviewed share-ratio position replay

**Intent:** Value an unchanged pre-action trade using the transformed position and native RAW marks. A 100-share holding with an 11:10 event becomes 110, without altering execution quantity, price or ledger history.

## Boundary

Extend the existing positions foundation, not trade accounting. Supported events are reviewed STOCK_SPLIT and basic BONUS_ISSUE quantity changes on the same canonical equity/ETF. Merger, spin-off, security replacement, loyalty entitlements and cash-in-lieu remain unsupported. Integer-only allocations block if a net holding would create fractions. No rounding or manufactured cash trade.

## Governance

An append-only replay decision freezes a specific source-action version, canonical instrument, exact positive ratio, UTC unit-change boundary, economic date, fraction policy, reviewer, source references and action snapshot. Platform reference administration publishes/revokes decisions; source ANNOUNCED records are not silently promoted. Replay uses the latest decision visible at the information cutoff and requires the selected source version to match its frozen snapshot. New source versions invalidate old decisions until reviewed. Historical decisions and valuation results remain unchanged.

## Reconstruction and attribution

Replay net signed holdings chronologically. Purchases/sales after an event use new units, before it old units. Deferred reporting recognition carries any intervening unit conversion. Daily recognition uses the event's economic date, while exposure/eligibility use actual execution timestamps. Equality at an exact action instant is ambiguous and blocks. Apply each action once per compatible bucket; retain before/after quantity, proof and trade lineage. The existing value bridge uses opening/closing quantities in their respective units and unchanged execution notionals; no RAW mark conversion.

## Evidence and acceptance

Projection and staged-line hashes include reviewed action identity and quantity adjustments. Unsupported or unreviewed relevant actions remain blocked, including flat round trips. Tests cover multiple/reverse splits, partial sales, shorts, flat/reopening histories, deferred recognition, information cutoffs, duplicate/conflicting events, fractions, unchanged trades and zero mechanical split P&L. Use pure tests then owned disposable PostgreSQL integration; no full-suite run or official P&L publication.

Air Liquide's basic 11:10 allocation must distinguish ex-date pricing from delivery date. Its loyalty premium and fractional rights are not inferred from Yahoo's STOCK_SPLIT classification.
