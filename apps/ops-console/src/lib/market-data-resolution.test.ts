import { describe, expect, it } from "vitest";

import { activePolicyCutId, activePolicyCutLabel, activePolicyLabel, buildOneSubjectResolutionRequest, formatResolutionTimestamp, resolutionStatusLabel } from "./market-data-resolution";

describe("market-data resolution evidence formatting", () => {
  it("labels frozen outcomes without evaluating live data", () => {
    expect(resolutionStatusLabel("DENIED")).toBe("Denied");
    expect(resolutionStatusLabel("SELECTED")).toBe("Selected");
  });

  it("formats frozen UTC timestamps and null evidence safely", () => {
    expect(formatResolutionTimestamp(null)).toBe("—");
    expect(formatResolutionTimestamp("2026-08-28T16:00:00Z")).toBe("2026-08-28 16:00:00Z");
  });

  it("builds a resolution command for exactly the selected subject", () => {
    const request = buildOneSubjectResolutionRequest("node-1", { valuationPolicyId: "policy-1", valuationDate: "2026-08-28", valuationCutId: "cut-1", marketDataAsOfUtc: "2026-08-28T16:00:00Z", usePurpose: "VALUATION" });
    expect(request.subjectReferenceNodeIds).toEqual(["node-1"]);
  });

  it("derives the only permitted valuation cut from the selected active policy", () => {
    expect(activePolicyCutId([
      { valuationPolicyId: "policy-1", valuationCutId: "cut-1", policyCode: "POLICY_1", displayName: "Policy one", valuationCutCode: "CUT_1", valuationCutDisplayName: "Cut one", timezoneName: "Europe/London", localTime: "16:00:00" },
      { valuationPolicyId: "policy-2", valuationCutId: "cut-2", policyCode: "POLICY_2", displayName: "Policy two", valuationCutCode: "CUT_2", valuationCutDisplayName: "Cut two", timezoneName: "Europe/London", localTime: "16:00:00" },
    ], "policy-2")).toBe("cut-2");
    expect(activePolicyCutId([{ valuationPolicyId: "policy-1", valuationCutId: "cut-1", policyCode: "POLICY_1", displayName: "Policy one", valuationCutCode: "CUT_1", valuationCutDisplayName: "Cut one", timezoneName: "Europe/London", localTime: "16:00:00" }], "unknown-policy")).toBeUndefined();
  });

  it("presents the policy code and display name rather than its opaque identifier", () => {
    expect(activePolicyLabel({ valuationPolicyId: "opaque-id", valuationCutId: "cut-1", policyCode: "DEMO_EOD", displayName: "Demo EOD valuation", valuationCutCode: "CUT", valuationCutDisplayName: "Cut", timezoneName: "Europe/London", localTime: "16:00:00" }))
      .toBe("DEMO_EOD — Demo EOD valuation");
  });

  it("presents the policy cut details rather than its opaque identifier", () => {
    expect(activePolicyCutLabel({ valuationPolicyId: "policy-1", valuationCutId: "opaque-cut", policyCode: "DEMO_EOD", displayName: "Demo EOD valuation", valuationCutCode: "LONDON_CLOSE_DEMO", valuationCutDisplayName: "London close (synthetic)", timezoneName: "Europe/London", localTime: "16:30:00" }))
      .toBe("LONDON_CLOSE_DEMO — London close (synthetic) · Europe/London 16:30");
  });
});
