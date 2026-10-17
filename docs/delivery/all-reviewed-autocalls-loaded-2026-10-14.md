# All four reviewed autocalls loaded — 14 October 2026

The user authorized loading all four and resolving contentious points using best
guesses. Three remaining note/share bundles were tested and committed in one
transaction; existing Citi Class 1562 was reused. All four notes and linked share
layers are ACTIVE in the existing personal/demo app database. Note proposals are
APPROVED. Original app instrument lookup includes each note and both earlier
Phoenix notes, so all six supplied PDF products are loaded. No trades were booked.

| Note ISIN | Note instrument ID | Share instrument ID |
| --- | --- | --- |
| FR001401AGT4 | `01a139b2-0bc2-7b59-a40b-1c031b638992` | `01a139b2-0ba1-7f81-bb35-52eabe49f1cf` |
| XS3487050836 | `01a139b2-0c28-7af6-9683-0927e54db37b` | `01a139b2-0c13-7f32-ba17-85c77d41ebea` |
| XS3446382098 | `01a1399e-e6ff-7e96-a87d-69e19ee03921` | `01a1399e-e6db-72c3-9b3f-3dba85cfcdd4` |
| XS3446168687 | `01a139b2-0cc6-7032-ab23-99ab24281629` | `01a139b2-0cac-7baa-aef1-61019e9d15f7` |

## Assumptions and retained distinctions

- HSBC: GBP 1 initial share value as directed; explicit London dates, with regular
  August-holiday projections for 2029-2031. Share issuer uses verified company
  registration; no missing LEI/share ISIN was invented.
- BNP: GBP 1 initial value as directed; external share identity stays UNCONFIRMED.
  Its nontradable internal dependency is bound to the note. GBP 0.01 denomination
  remains distinct from the GBP 1 issue-price payout base. Early note payments
  follow source share redemption dates, as stated in the certificate terms.
- Citi Class 1571: note early payments use share redemption dates, consistent with
  the approved Class 1562 approach. Keep GBP 100 initial value, all three source
  fixings and separate final dates. Catalogue validity starts on documented trade
  date 2026-10-01; legal note/share issue dates remain 2026-10-19 / 2026-10-15.
  No existing approved definition was mutated.
- Exceptional/discretionary events are outside the agreed ordinary modeled scope.
  Original source facts/hashes remain intact; assumptions and user authority are
  retained separately. This is not full legal, lifecycle or pricing certification.

## Reusable seed

[Operator command](C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion/scripts/seed_reviewed_wrappers.py) rolls back by default;
`--apply` commits all selected bundles atomically and `--isin` selects one.

```powershell
python -B scripts/seed_reviewed_wrappers.py
python -B scripts/seed_reviewed_wrappers.py --apply
```

The [shared loader](C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion/security_master_schema/reviewed_citi_wrapper_seed.py)
retains compatibility with the original single-Citi command. Its original source
snapshot/digest is unchanged. New immutable snapshots:

- [HSBC](C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion/security_master_schema/data/reviewed_wrapper_fr001401agt4_2026_10_14.json).
- [BNP](C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion/security_master_schema/data/reviewed_wrapper_xs3487050836_2026_10_14.json).
- [Citi Class 1571](C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion/security_master_schema/data/reviewed_wrapper_xs3446168687_2026_10_14.json).

Wrapper `effectiveFrom` separates catalogue/terms validity from legal issue date.
Materialization uses it for definitions, terms, identifiers, parties, taxonomy and
composition validity. Absent this field, existing issue-date behavior remains.
Legacy JSON normalizes for replay; the pre-issue Citi catalogue date comes from
its documented trade date, not a fabricated issue date.

## Verification and limits

40 focused tests passed in owned disposable PostgreSQL: all four graphs,
legacy/new replay, separate units, explicit dates, pre-issue visibility and source
regressions. The [all-four regression](C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion/tests/test_all_reviewed_wrapper_seeds.py)
checks eight separate instruments, retained future issue dates, public index
references and durable unconfirmed BNP identity.

Operating preview passed; apply created three/reused one; replay created zero and
reused all four IDs. Original app repository readback verified active states,
approvals, lookup, share links, calls, legal issue dates and earlier Phoenix notes.
Migration remains 20261014_88. No new migration, restart, provider call or frontend
change occurred. Browser acceptance was not exercised. Logs: `.implementation/all-wrappers-*`.

The [initial delivery](C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion/docs/delivery/termsheet-product-seed-2026-10-14.md) retains chronology;
earlier REVIEW_ONLY/source-guard statements describe pre-review evidence, not
current app inventory. The immutable extraction manifest still records original
omissions. Approved guesses are separate operator decisions. General AI-ingestion
and provider activation remain outstanding.

Execute the explicit operator command from the isolated checkout named above;
the seed code is not integrated into this checkout or its general demo loader.


Later update: [approved booking conventions now make all six parent notes READY](termsheet-note-booking-readiness-2026-10-14.md)
on the structured-security OTC ticket. No actual trade was booked.
