import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import { buildTicketPayload, validateTicketDraft } from "./trade-ticket";

describe("listing-first trade ticket", () => {
  const listing = { referenceNodeId: "listing-1", canonicalName: "Example ETP", marketVenueMic: "XNAS", venueName: "Nasdaq", tradingSymbol: "ETP-TEST", tradingCurrency: "USD", status: "ACTIVE", isTradable: true };

  it("keeps the listing identity outside the editable booking payload", () => {
    const payload = buildTicketPayload(listing, {
      strategyId: "strategy-1", side: "BUY", quantity: "10", executionPrice: "12.5", tradeDatetime: "2026-09-30T10:00:00Z", settlementDate: "2026-10-02",
    });

    expect(payload).toMatchObject({ listingId: "listing-1", strategyId: "strategy-1", side: "BUY", quantity: "10", executionPrice: "12.5" });
    expect(payload).not.toHaveProperty("priceCurrency");
    expect(payload).not.toHaveProperty("executionVenue");
  });

  it("rejects zero quantity locally while allowing a sell with positive ticket quantity", () => {
    expect(validateTicketDraft({ strategyId: "strategy-1", quantity: "0", executionPrice: "12.5", tradeDatetime: "2026-09-30T10:00:00Z", settlementDate: "2026-10-02" })).toContain("Quantity");
    expect(validateTicketDraft({ strategyId: "strategy-1", quantity: "10", executionPrice: "12.5", tradeDatetime: "2026-09-30T10:00:00Z", settlementDate: "2026-10-02" })).toBeNull();
  });
});

describe("trade booking entry point", () => {
  const newTradePage = readFileSync(new URL("./page.tsx", import.meta.url), "utf8");
  const ticket = readFileSync(new URL("./trade-ticket.tsx", import.meta.url), "utf8");

  it("allows the dedicated booking route to start without a preselected listing", () => {
    expect(newTradePage).not.toContain('if (!listingId) redirect("/instruments")');
  });

  it("searches active listings before rendering their locked booking facts", () => {
    expect(ticket).toContain("Search active listings");
    expect(ticket).toContain("searchReferenceNodesFromBff");
    expect(ticket).toContain('referenceLevel: "LISTING"');
  });
});
