import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { parseHistoryQuery, historyHref, safeHistoryReturn } from "./trade-history";

describe("trade history navigation", () => {
  beforeEach(() => { vi.useFakeTimers(); vi.setSystemTime(new Date("2026-09-30T23:30:00Z")); });
  afterEach(() => vi.useRealTimers());
  it("defaults to fourteen inclusive UTC calendar days", () => {
    expect(parseHistoryQuery({})).toMatchObject({ range: "14d", fromDate: "2026-09-17", toDate: "2026-09-30" });
  });
  it("supports thirty days and explicit unbounded history", () => {
    expect(parseHistoryQuery({ range: "30d" })).toMatchObject({ fromDate: "2026-09-01", toDate: "2026-09-30" });
    expect(parseHistoryQuery({ range: "all" })).toMatchObject({ range: "all", fromDate: "", toDate: "" });
  });
  it("preserves explicit custom and open-ended dates", () => {
    expect(parseHistoryQuery({ fromDate: "2024-01-01" })).toMatchObject({ range: "custom", fromDate: "2024-01-01", toDate: "" });
    expect(parseHistoryQuery({ range: "custom", fromDate: "", toDate: "" })).toMatchObject({ range: "all", fromDate: "", toDate: "" });
  });
  it("handles month/year and leap-year boundaries without local timezone drift", () => {
    vi.setSystemTime(new Date("2024-03-01T00:00:00Z"));
    expect(parseHistoryQuery({})).toMatchObject({ fromDate: "2024-02-17", toDate: "2024-03-01" });
    vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));
    expect(parseHistoryQuery({})).toMatchObject({ fromDate: "2025-12-19", toDate: "2026-01-01" });
  });
  it("retains the displayed preset dates when paging after midnight", () => {
    const href = historyHref(parseHistoryQuery({}), 2);
    vi.setSystemTime(new Date("2026-10-01T01:00:00Z"));
    const restored = parseHistoryQuery(Object.fromEntries(new URL(href, "http://local").searchParams));
    expect(restored).toMatchObject({ range: "14d", fromDate: "2026-09-17", toDate: "2026-09-30", page: 2 });
  });
  it("normalizes malformed and repeated pagination parameters", () => {
    expect(parseHistoryQuery({ page: "-4", pageSize: "200", q: ["ETP", "ignored"] })).toMatchObject({ page: 1, pageSize: 25, q: "ETP" });
    expect(parseHistoryQuery({ page: "3", pageSize: "50" })).toMatchObject({ page: 3, pageSize: 50 });
  });
  it("preserves filters when navigating between pages", () => {
    expect(historyHref(parseHistoryQuery({ q: "ETP", side: "SELL", portfolioCode: "CUSTOM" }), 2))
      .toBe("/trades?q=ETP&portfolioCode=CUSTOM&fromDate=2026-09-17&toDate=2026-09-30&side=SELL&range=14d&pageSize=25&page=2");
  });
  it("never accepts an external return destination", () => {
    expect(safeHistoryReturn("https://evil.test")).toBe("/trades");
    expect(safeHistoryReturn("//evil.test/trades")).toBe("/trades");
    expect(safeHistoryReturn("/trades/new")).toBe("/trades");
    expect(safeHistoryReturn("/trades?q=ETP&page=2")).toContain("q=ETP");
  });
});
