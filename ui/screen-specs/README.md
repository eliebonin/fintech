# Screen specifications

Each screen specification should describe:

1. user goal and allowed roles;
2. entry points and required tenant context;
3. data queries and display fields;
4. loading, empty, stale, error, unauthorized, and pending states;
5. mutations and approval/correction behaviour;
6. links to API contracts and backend audit records; and
7. acceptance examples using synthetic data.

Recommended first specifications:

- [`instrument-search.md`](instrument-search.md) (implemented first slice)
- [`market-data-cutoff-pnl.md`](market-data-cutoff-pnl.md)
- [`market-data-series-mvp.md`](market-data-series-mvp.md)
- [`portfolio-pnl-mvp.md`](portfolio-pnl-mvp.md)
- [`index-onboarding.md`](index-onboarding.md)
- `home-work-queue.md`
- `global-search.md`
- `instrument-detail.md`
- `trade-booking-and-detail.md`
- `soft-nav-review.md`

The MVP pages are server-rendered and tenant-context aware. They display only
synthetic fixture data in local development, and every market-data card keeps
the provider, dataset, licence, cut and observation receipt context visible.
