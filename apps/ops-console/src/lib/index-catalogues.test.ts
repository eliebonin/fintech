import { describe, expect, it } from "vitest";

import { flattenCurrencyGroups, listCurrenciesFromBff, listIndexFamiliesFromBff, listIndexKindsFromBff, listOrganisationsFromBff, listReturnProfilesFromBff, submitIndexFamilyProposalFromBff } from "./browser-api-client";

describe("index onboarding catalogues", () => {
  it("loads currencies through the BFF route", async () => {
    let requestedUrl = "";
    const fetchImpl: typeof fetch = async (input) => {
      requestedUrl = String(input);
      return new Response(JSON.stringify({ data: [{ groupCode: "REGULAR", label: "Regular currencies", items: [{ currencyId: "usd", currencyCode: "USD", displayName: "US dollar", currencyKind: "FIAT" }] }], meta: {} }), { status: 200 });
    };

    const result = await listCurrenciesFromBff(fetchImpl);

    expect(requestedUrl).toBe("/api/currencies");
    expect(result.data[0].items[0].currencyCode).toBe("USD");
  });

  it("requests both currency groups when the selector opts into crypto", async () => {
    let requestedUrl = "";
    const fetchImpl: typeof fetch = async (input) => {
      requestedUrl = String(input);
      return new Response(JSON.stringify({ data: [], meta: {} }), { status: 200 });
    };

    await listCurrenciesFromBff(fetchImpl, ["REGULAR", "CRYPTO"]);

    expect(new URL(requestedUrl, "http://ops-console.test").searchParams.get("groups")).toBe("REGULAR,CRYPTO");
  });

  it("flattens grouped currencies without losing their canonical rows", () => {
    const currencies = flattenCurrencyGroups([
      { groupCode: "REGULAR", label: "Regular currencies", items: [{ currencyId: "usd", currencyCode: "USD", displayName: "US dollar", currencyKind: "FIAT" }] },
      { groupCode: "CRYPTO", label: "Cryptoassets", items: [{ currencyId: "btc", currencyCode: "BTC", displayName: "Bitcoin", currencyKind: "CRYPTOASSET" }] },
    ]);

    expect(currencies.map((currency) => currency.currencyCode)).toEqual(["USD", "BTC"]);
  });

  it("loads return profiles and organisations through their BFF routes", async () => {
    const requestedUrls: string[] = [];
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input);
      requestedUrls.push(url);
      if (url === "/api/return-profiles") {
        return new Response(JSON.stringify({ data: [{ returnProfileId: "price", profileCode: "PRICE_RETURN", displayName: "Price return", description: "Price only", baseReturnBasis: "PRICE", incomeTreatment: "NONE" }], meta: {} }), { status: 200 });
      }
      return new Response(JSON.stringify({ data: [{ organisationId: "org", displayName: "Index administrator", legalName: null, status: "ACTIVE" }], meta: {} }), { status: 200 });
    };

    const profiles = await listReturnProfilesFromBff(fetchImpl);
    const organisations = await listOrganisationsFromBff(fetchImpl);

    expect(requestedUrls).toEqual(["/api/return-profiles", "/api/organisations"]);
    expect(profiles.data[0].profileCode).toBe("PRICE_RETURN");
    expect(organisations.data[0].displayName).toBe("Index administrator");
  });

  it("loads index families through the DB-backed BFF catalogue", async () => {
    let requestedUrl = "";
    const fetchImpl: typeof fetch = async (input) => {
      requestedUrl = String(input);
      return new Response(JSON.stringify({ data: [{ indexFamilyId: "family", familyNodeId: "node", familyName: "S&P 500", providerOrganisationId: null, providerOrganisationName: null }], meta: {} }), { status: 200 });
    };

    const result = await listIndexFamiliesFromBff(fetchImpl);

    expect(requestedUrl).toBe("/api/index-families");
    expect(result.data[0].familyName).toBe("S&P 500");
  });

  it("loads index-kind definitions through the DB-backed BFF catalogue", async () => {
    let requestedUrl = "";
    const fetchImpl: typeof fetch = async (input) => {
      requestedUrl = String(input);
      return new Response(JSON.stringify({ data: [{ indexKindCode: "PUBLIC", displayName: "Public benchmark", description: "Publicly disseminated; methodology may still be provider-owned.", disseminationClass: "PUBLIC", methodologyOwnership: "PROVIDER_OWNED", exampleText: "S&P 500", status: "ACTIVE" }], meta: {} }), { status: 200 });
    };

    const result = await listIndexKindsFromBff(fetchImpl);

    expect(requestedUrl).toBe("/api/index-kind-catalogue");
    expect(result.data[0].methodologyOwnership).toBe("PROVIDER_OWNED");
  });

  it("submits an index-family proposal through the BFF route", async () => {
    let requestedUrl = "";
    let requestedBody = "";
    const fetchImpl: typeof fetch = async (input, init) => {
      requestedUrl = String(input);
      requestedBody = String(init?.body);
      return new Response(JSON.stringify({ data: { proposalId: "proposal", status: "PENDING", proposalType: "CREATE_INDEX_FAMILY", submissionMode: "MANUAL", familyName: "S&P 500", familyId: null, familyNodeId: null, proposedAt: "2026-09-07T00:00:00Z" }, meta: {} }), { status: 201 });
    };

    const result = await submitIndexFamilyProposalFromBff({ canonicalName: "S&P 500", submissionMode: "MANUAL" }, "idem-family", fetchImpl);

    expect(requestedUrl).toBe("/api/instruments/index-families");
    expect(JSON.parse(requestedBody)).toEqual({ canonicalName: "S&P 500", submissionMode: "MANUAL" });
    expect(result.data.status).toBe("PENDING");
  });
});
