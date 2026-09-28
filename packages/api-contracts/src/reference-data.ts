import type { components } from "./generated";

/**
 * Compatibility names for the Reference Data BFF.  Each API-shaped alias is
 * intentionally derived from the generated OpenAPI schema rather than copied
 * into the console application.
 */
export type ReferenceApiMeta = components["schemas"]["ApiMeta"];
export type ReferenceDataProposalPayload = components["schemas"]["ReferenceDataProposalResponse"];
export type InstrumentSearchPayload = components["schemas"]["InstrumentSearchResponse"];
export type ReferenceNodeOption = components["schemas"]["ReferenceNodeOptionView"];
export type ReferenceNodeSearchPayload = components["schemas"]["ReferenceNodeSearchResponse"];
export type EquityProposalPayload = components["schemas"]["EquityProposalResponse"];
export type CryptoAssetProposalPayload = components["schemas"]["CryptoAssetProposalResponse"];
export type BondProposalPayload = components["schemas"]["BondProposalResponse"];
export type FxForwardProposalPayload = components["schemas"]["FxForwardProposalResponse"];
export type EtpProposalPayload = components["schemas"]["EtpProposalResponse"];
export type IndexProposalPayload = components["schemas"]["IndexProposalResponse"];
export type MarketVenue = components["schemas"]["MarketVenueView"];
export type MarketVenuePayload = components["schemas"]["MarketVenueResponse"];
export type DayCountConvention = components["schemas"]["DayCountConventionView"];
export type DayCountConventionPayload = components["schemas"]["DayCountConventionResponse"];
export type Currency = components["schemas"]["CurrencyView"];
export type CurrencyGroup = components["schemas"]["CurrencyGroupView"];
export type CurrencyPayload = components["schemas"]["CurrencyResponse"];
export type ReturnProfile = components["schemas"]["ReturnProfileView"];
export type ReturnProfilePayload = components["schemas"]["ReturnProfileResponse"];
export type IndexKind = components["schemas"]["IndexKindView"];
export type IndexKindPayload = components["schemas"]["IndexKindResponse"];
export type OrganisationOption = components["schemas"]["OrganisationOptionView"];
export type OrganisationOptionPayload = components["schemas"]["OrganisationOptionResponse"];
export type IndexFamilyOption = components["schemas"]["IndexFamilyOptionView"];
export type IndexFamilyPayload = components["schemas"]["IndexFamilyOptionResponse"];
export type IndexFamilyProposalPayload = components["schemas"]["IndexFamilyProposalResponse"];
export type StructuredProductProposalPayload = components["schemas"]["StructuredProductProposalResponse"];

/** Console grouping, not an API wire value. */
export type CurrencyGroupCode = "REGULAR" | "CRYPTO";
