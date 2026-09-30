import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const reviewForm = fileURLToPath(new URL("./[proposalId]/form.tsx", import.meta.url));

describe("reference-data proposal lifecycle handoff", () => {
  it("makes the terminal outcome and its next action explicit", () => {
    const source = readFileSync(reviewForm, "utf8");

    expect(source).toContain('"Submitted"');
    expect(source).toContain('"Pending review"');
    expect(source).toContain('"Approved"');
    expect(source).toContain('"Rejected"');
    expect(source).toContain("View approved instrument");
    expect(source).toContain("/instruments/${current.referenceNodeId}");
    expect(source).toContain("Back to pending instrument requests");
    expect(source).toContain("Reason: {current.decisionReason}");
  });
});
