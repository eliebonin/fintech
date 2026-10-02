export type QueueCandidate = {
  itemId: string;
  category: string;
  status: string;
  proposalType?: string | null;
};

const INSTRUMENT_CREATION_PROPOSAL_TYPES = new Set([
  "CREATE",
  "CREATE_BOND",
  "CREATE_CRYPTO_ASSET",
  "CREATE_ETP",
  "CREATE_FX_FORWARD",
  "CREATE_OPTION",
  "CREATE_FUTURE",
  "CREATE_SWAP",
  "CREATE_INDEX",
  "CREATE_STRUCTURED_PRODUCT",
]);

export function filterInstrumentCreationRequests<T extends QueueCandidate>(items: T[]): T[] {
  return items.filter((item) => (
    item.category === "REFERENCE_DATA_REVIEW"
    && item.status === "PENDING"
    && item.proposalType != null
    && INSTRUMENT_CREATION_PROPOSAL_TYPES.has(item.proposalType)
  ));
}
