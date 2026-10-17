# Reviewed Citi Class 1562 seed — 14 October 2026

The user authorized loading XS3446382098 after reviewing the PDF and directing
note early payments to use preference-share redemption dates.

- Note XS3446382098: `01a1399e-e6ff-7e96-a87d-69e19ee03921`.
- Share LU3210286756 (Class 1562): `01a1399e-e6db-72c3-9b3f-3dba85cfcdd4`.
- Proposal `01a1399e-e6be-7e1a-8e1c-5fc2aaa01fc2`: APPROVED.

Both instruments are ACTIVE in the existing personal/demo tenant and visible
through this checkout's instrument repository lookup. No trades were booked.
The note retains GBP 1 denomination, GBP 3,213,470 aggregate issue amount and
2032-10-05 maturity. Its linked share retains GBP 100 denomination/initial value
and 2032-10-07 redemption. Four early note payments follow share redemption dates
as an explicit user modeling assumption. Source fixings use public FTSE 100 and
S&P 500 price-return nodes. Original legal clauses remain retained source evidence;
the modeled scope is the reviewed ordinary contractual base case.

Migration 20261014_88 follows this checkout's self-publication revision 20261014_87
and adds four immutable wrapper tables. Additive declarations are registered in
security_master_schema/models.py. This uses the original ancestry, not the other
checkout's colliding ingestion migrations. The migration was tested on an owned
fresh database using original migrations/demo bootstrap before operating apply.
16 focused disposable tests plus an original-ancestry creation/replay test passed.
Operating rollback preview, apply, replay and original repository readback passed.

The explicit reusable seed and immutable reviewed snapshot remain in
C:/Users/forte/Documents/CTO/fintech-termsheet-ingestion. Execute
scripts/seed_reviewed_citi_wrapper.py there (rollback by default; --apply commits).
The full evidence is that checkout's docs/delivery/termsheet-product-seed-2026-10-14.md.
Neither the general demo loader nor the app invokes this explicit operator seed.
No service restart or provider activation occurred; integrated AI ingestion in
this checkout remains unimplemented. The three other supplied wrapper notes
remain unloaded. No commits or merge were made.


Later update: [all four reviewed notes are now loaded](all-reviewed-autocalls-loaded-2026-10-14.md).
That record supersedes the earlier statement that three remain unloaded.
