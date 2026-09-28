import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const source = readFileSync(fileURLToPath(new URL("./operations-console.tsx", import.meta.url)), "utf8");

describe("work queue interaction", () => {
  it("lets an operator select a queue record and inspect its details", () => {
    expect(source).toContain("selectedQueueItem");
    expect(source).toContain("setSelectedQueueItem");
    expect(source).toContain('id="work-queue-detail"');
    expect(source).toContain("onClick={() => inspectQueueItem(item)}");
    expect(source).toContain('aria-label={`Inspect ${item.title}`}');
  });

  it("keeps every review record discoverable with a queue filter", () => {
    expect(source).toContain("const [queueFilter, setQueueFilter] = useState(\"\");");
    expect(source).toContain("const visibleQueueItems =");
    expect(source).toContain("visibleQueueItems.map");
    expect(source).not.toContain("queue.items.slice(0, 3)");
    expect(source).toContain('placeholder="e.g. ETH, Ethereum, bond, mapping ID…"');
  });

  it("keeps cutoff demonstrations out of the operations queue page", () => {
    expect(source).not.toContain("Valuation cutoff evidence");
    expect(source).not.toContain("Cutoff P&L lab");
    expect(source).not.toContain("<CutoffPnlLab />");
  });
});
