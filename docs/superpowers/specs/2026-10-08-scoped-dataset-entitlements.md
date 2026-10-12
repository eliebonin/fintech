# Scoped dataset entitlements

## Approved intent

Keep one provider/content-owner identity per organisation. Represent licensed coverage (for example CME Group COMEX versus NYMEX EoD settlements) as dataset packages, not duplicate providers. Permit tenant access to only reviewed packages before price selection or disclosure. The user authorised implementation and previously requested sequential work without further plan-approval prompts.

## Design

- Add named dataset coverage packages, with content owner, optional licensing market, timing category and evidence reference.
- Explicitly classify each dataset/series pair into one package. Do not infer licensing markets from delivery channels, provider names or Globex.
- Existing dataset-wide tenant grants remain dataset-wide. A new SCOPED grant permits only its associated packages. Missing classification fails closed for scoped grants.
- Packages remain subordinate to existing conjunctive provider/owner activity rights; this feature creates no legal permission.
- Enforce the same package boundary in resolution, market-data catalogue/detail, and retained valuation/selection evidence disclosure.
- No provider duplication, no operating-data grant changes, no quarterly workflow, no source-priority or strict/flexible policy redesign in this delivery.

## Acceptance

Within one mixed synthetic dataset, a COMEX-only tenant can select and display the COMEX series but cannot select or display NYMEX or unclassified series. Scope grants cannot reference another dataset. Suspended/expired packages deny access. Existing dataset-wide grants continue working. Frozen evidence is rechecked against current coverage permissions. Focused tests use an isolated database, not operating data.

## References

- [CME entitlement systems](https://www.cmegroup.com/market-data/distributor/files/data-licensing-policy-guidelines-entitlement-systems.pdf): designated contract markets, content limitations, timing and usage are separate entitlement dimensions. The linked 2021 educational guidance is not a substitute for the current executed agreement.
- [CME licensing options](https://www.cmegroup.com/market-data/license-data.html): internal display, non-display, distribution and derived-data licensing are distinct.

## Delivery approach

Implement the persisted scope model and shared SQL eligibility boundary first, then integrate all existing consumers and verify with focused regression tests. Licensing administration remains platform-governed; tenant preferences cannot create coverage grants.
