import { afterEach, expect, it, vi } from "vitest";
const h = vi.hoisted(() => ({ slots: [] as any[], cursor: 0, send: vi.fn() }));
vi.mock("react", async original => ({ ...await original<typeof import("react")>(), useState: (initial: any) => { const i = h.cursor++; if (!(i in h.slots)) h.slots[i] = typeof initial === "function" ? initial() : initial; return [h.slots[i], (v: any) => h.slots[i] = typeof v === "function" ? v(h.slots[i]) : v]; }, useRef: (initial: any) => { const i = h.cursor++; if (!(i in h.slots)) h.slots[i] = { current: initial }; return h.slots[i]; }, useEffect: () => {} }));
vi.mock("@/lib/browser-api-client", async original => ({ ...await original<typeof import("@/lib/browser-api-client")>(), submitBondProposalFromBff: h.send }));
import NewBondPage from "./page";
function find(node: any, predicate: (n: any) => boolean): any { if (!node || typeof node !== "object") return; if (predicate(node)) return node; for (const child of [node.props?.children].flat(Infinity)) { const found = find(child, predicate); if (found) return found; } }
function render() { h.cursor = 0; return NewBondPage(); }
afterEach(() => { h.slots = []; h.cursor = 0; h.send.mockReset(); });
it("captures sourced par and redemption terms without inventing defaults", async () => {
 let tree = render();
 expect(find(tree, n => n.props?.label === "Par amount (optional)").props.value).toBe("");
 expect(find(tree, n => n.props?.label === "Redemption per 100 par (optional)").props.value).toBe("");
 for (const [label, value] of [["Canonical name", "Sourced bond"], ["Coupon structure", "FIXED"], ["Par amount (optional)", "1000.00"], ["Redemption per 100 par (optional)", "100"]]) find(tree, n => n.props?.label === label).props.onChange({ target: { value } });
 h.send.mockResolvedValueOnce({ data: { status: "PENDING", enrichmentStatus: "READY_FOR_APPROVAL", proposalId: "proposal" } });
 await find(render(), n => n.props?.component === "form").props.onSubmit({ preventDefault() {} });
 expect(h.send.mock.calls[0][0]).toMatchObject({ parAmount: "1000.00", redemptionAmountPerPar: "100" });
});
it("keeps sparse provider-enrichable submissions possible", async () => {
 let tree = render(); for (const [label, value] of [["Canonical name", "Sparse bond"], ["Coupon structure", "ZERO"]]) find(tree, n => n.props?.label === label).props.onChange({ target: { value } });
 h.send.mockResolvedValueOnce({ data: { status: "PENDING", enrichmentStatus: "PENDING_ENRICHMENT", proposalId: "proposal" } });
 await find(render(), n => n.props?.component === "form").props.onSubmit({ preventDefault() {} });
 expect(h.send.mock.calls[0][0]).toMatchObject({ parAmount: undefined, redemptionAmountPerPar: undefined });
});
