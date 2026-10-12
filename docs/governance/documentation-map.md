# Documentation map and precedence

**Status:** Accepted maintained reference  
**Content type:** Documentation reference  
**Owner:** Product and engineering  
**Last reviewed:** 2026-10-12

## Read the smallest relevant set

1. [Feature register](../product/feature-register.md): locate the stable ID/status.
2. Its linked capability section: desired scope, backend/frontend, cuts/trade-offs, weaknesses, remaining work and evidence.
3. Follow only the relevant delivery/source/test; do not read every chronological plan to find current support.
4. [System overview](../architecture/system-overview.md), domain indexes and [glossary](glossary.md) explain boundaries/terms.

## Collections and authority

| Collection | Purpose | Not proof of |
| --- | --- | --- |
| `docs/product/feature-register.md`, `features/` | Maintained desired-versus-delivered scope and gaps | Production certification or new scope approval |
| `docs/architecture/` current domain references | Implementation boundaries/design explanation | Deployment of every target architecture |
| `docs/platform/`, app/package READMEs | Engineering reference/run entry points | Complete business acceptance |
| `docs/delivery/` | Dated implementation/tests/activation; [catalogue](../delivery/catalogue.md) | Latest state when later work supersedes it |
| Specification index → `docs/superpowers/specs/` | Design intent/constraints | Implemented features |
| Plan index → `docs/superpowers/plans/` | Intended execution/checkpoints | Completion from a checked or unchecked plan alone |
| `docs/delivery/quality-reviews/` | Dated findings/verification | Permanent defects after remediation or all-code audit |
| `docs/research/`, `fintech-moduls/` | Evidence/commercial directions | Approved requirements or delivered modules |
| `security-master-notes/`, `ui/` | Foundations, detailed legacy specs/workflows | Current runtime support by themselves |
| `docs/archive/` | Immutable pre-reorganisation snapshots | Current policy; never edit as maintained pages |

Dated reviews under `docs/architecture/` remain dated reviews, not current architecture merely because of their folder. Code/migrations/tests are implementation evidence; when they contradict a current page, correct that page/register rather than maintain competing descriptions.

## Maintenance

- Latest explicit user scope/deferral governs direction; researched/discussed ideas are not automatic implementation authorization.
- Register/records state reviewed support at a code baseline, linking sources instead of duplicating specs.
- Later delivery can supersede earlier scope/activation notes; preserve old test evidence and add a pointer.
- Accepted ADRs retain rationale/consequences; replace via supersession, not hidden history edits.
- Live state, tests, browser and financial comparison are independent claims; docs review does not perform them implicitly.
- Add the next stable feature ID; update status/record/evidence together and mark unverified gaps honestly.

No mass migration was needed: September's domains/archive remain useful. This review adds capability-led retrieval, repairs entry points and classifies history without breaking old paths.

## Research basis

[Diátaxis](https://diataxis.fr/start-here/) separates reference/explanation from task guides/tutorials; applied here to capability facts versus run instructions and evidence. [arc42 risks/debt](https://docs.arc42.org/section-11/) motivates explicit weaknesses/mitigations; [arc42 decisions](https://docs.arc42.org/section-9/) supports retained rationale/consequences. Stable IDs/layout/statuses are project choices, not mandated standards. Opened 2026-10-12; these living guides impose no financial/regulatory obligations.
