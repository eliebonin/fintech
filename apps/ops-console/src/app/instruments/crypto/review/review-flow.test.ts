import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const reviewPage = fileURLToPath(new URL("./[proposalId]/page.tsx", import.meta.url));
const reviewForm = fileURLToPath(new URL("./[proposalId]/form.tsx", import.meta.url));

describe("cryptoasset proposal review flow", () => {
  it("provides a review page with approval and rejection actions", () => {
    expect(existsSync(reviewPage)).toBe(true);
    expect(existsSync(reviewForm)).toBe(true);
    const source = `${readFileSync(reviewPage, "utf8")}\n${readFileSync(reviewForm, "utf8")}`;
    expect(source).toContain("decideCryptoAssetProposalFromBff");
    expect(source).toContain("APPROVED");
    expect(source).toContain("REJECTED");
    expect(source).toContain("currencyId");
  });
});
