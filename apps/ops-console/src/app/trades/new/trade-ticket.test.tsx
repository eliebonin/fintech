import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";

import { buildTicketPayload, createTicketDraft, defaultSettlementDate, TradeTicket, updateTicketDraft, validateTicketDraft } from "./trade-ticket";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => {} }) }));

describe("T+2 weekday settlement default", () => {
  it.each([
    ["2026-09-30T10:00:00Z", "2026-10-02"],
    ["2026-10-01T10:00:00Z", "2026-10-05"],
    ["2026-10-02T10:00:00Z", "2026-10-06"],
    ["2026-10-03T10:00:00Z", "2026-10-06"],
    ["2026-12-31T10:00:00Z", "2027-01-04"],
    ["2028-02-28T10:00:00Z", "2028-03-01"],
    ["2026-10-02T00:30:00+14:00", "2026-10-06"],
  ])("defaults %s to %s, excluding the trade date and weekends", (tradeTime, expected) => {
    expect(defaultSettlementDate(tradeTime)).toBe(expected);
  });

  it.each(["", "2026-10", "2026-02-30T10:00:00Z", "2026-10-02T10:00:00"])("does not derive dates from invalid or incomplete timestamps: %s", (value) => {
    expect(defaultSettlementDate(value)).toBe("");
  });

  it("initializes the ticket with a settlement default", () => {
    expect(createTicketDraft(new Date("2026-10-02T10:00:00Z"))).toMatchObject({ tradeDatetime: "2026-10-02T10:00:00Z", settlementDate: "2026-10-06" });
  });

  it("recalculates when trade time changes before a manual override", () => {
    const draft = createTicketDraft(new Date("2026-09-30T10:00:00Z"));
    expect(updateTicketDraft(draft, "tradeDatetime", "2026-10-02T10:00:00Z", false).settlementDate).toBe("2026-10-06");
    expect(updateTicketDraft(draft, "tradeDatetime", "incomplete", false).settlementDate).toBe("2026-10-02");
  });

  it("preserves manually entered settlement dates even when equal to the old default", () => {
    const draft = createTicketDraft(new Date("2026-09-30T10:00:00Z"));
    expect(updateTicketDraft(draft, "tradeDatetime", "2026-10-02T10:00:00Z", true).settlementDate).toBe("2026-10-02");
    expect(updateTicketDraft(draft, "settlementDate", "2026-10-08", true).settlementDate).toBe("2026-10-08");
  });
});

describe("listing-first trade ticket", () => {
  const listing = { referenceNodeId: "listing-1", canonicalName: "Example ETP", marketVenueMic: "XNAS", venueName: "Nasdaq", tradingSymbol: "ETP-TEST", tradingCurrency: "USD", status: "ACTIVE", isTradable: true };

  it("renders the editable settlement field with the default and calendar limitation", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-02T10:00:00Z"));
    try {
      const html = renderToStaticMarkup(<TradeTicket listing={listing} strategies={[]} />);
      expect(html).toContain('aria-label="Settlement date" type="date"');
      expect(html).toContain('value="2026-10-06"');
      expect(html).toContain("Holidays are not applied");
    } finally { vi.useRealTimers(); }
  });

  it("shows parties, classifications and typed properties before booking", () => {
    const context = {tenantId:"tenant",bookedByUserAccountId:"actor",properties:[{definitionId:"flag",code:"FLAG",label:"Client instructed",valueType:"BOOLEAN" as const,required:false,choices:[],description:null}],tags:[{tagId:"tag",code:"CORE",label:"Core"}]};
    const html = renderToStaticMarkup(<TradeTicket listing={listing} strategies={[]} context={context} />);
    expect(html).toContain("Counterparty");
    expect(html).toContain("Executing broker");
    expect(html).toContain("Trader");
    expect(html).toContain("Client instructed");
    expect(html).toContain("Review booking");
  });

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
