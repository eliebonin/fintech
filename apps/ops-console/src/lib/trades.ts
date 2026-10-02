export type BookedTrade = {
  productEconomics?: {bondDetails?:Record<string,string>|null;terms:import('api-contracts').components['schemas']['ProductBookingContextView'];amount:string;amountKind:'CONSIDERATION'|'REFERENCE_CONTRACT_VALUE'|'ENTRY_REFERENCE_VALUE';direction?:'PAY'|'RECEIVE'|null}|null;
  positionEffect?: 'OPEN'|'CLOSE'|null;
  optionEconomics?: import('api-contracts').components['schemas']['OptionTradeEconomicsView']|null;
  fxForwardEconomics?: import("api-contracts").components["schemas"]["FxForwardTradeEconomicsView"] | null;
  tradeId: string;
  subjectReferenceNodeId: string;
  subjectName: string;
  instrumentId: string | null;
  instrumentName: string | null;
  instrumentType: string | null;
  listingId: string | null;
  listingSymbol: string | null;
  venueMic: string | null;
  venueName: string | null;
  strategyId: string;
  strategyCode: string;
  strategyName: string;
  tradeType: string;
  tradePurpose: string | null;
  marketActivity: string | null;
  executionPrice: string | null;
  lockedYtm: string | null;
  priceBasis: string | null;
  priceCurrency: string | null;
  quantity: string;
  quantityUnit: string;
  tradeDatetimeUtc: string;
  instructionDate: string | null;
  settlementDate: string | null;
  traderPersonId: string | null;
  bookedByUserAccountId: string;
  executionChannel: string;
  sourceSystemId: string | null;
  sourceReceivedAtUtc: string | null;
  executionVenueId: string | null;
  dealingCapacity: string | null;
  lifecycleStatus: string;
  referenceInstrumentId: string | null;
  comment: string | null;
};

export type TradePayload = {
  data: BookedTrade[];
  meta: { source: string; apiVersion: string; correlationId: string; total?: number };
};

export type TradeParty = {
  tradePartyRoleId: string;
  role: string;
  organisationId: string | null;
  organisationName: string | null;
  personId: string | null;
  personName: string | null;
  partyName: string;
};

export type TradeFee = {
  tradeFeeId: string;
  feeType: string;
  payerOrganisationId: string | null;
  payerOrganisationName: string | null;
  recipientOrganisationId: string | null;
  recipientOrganisationName: string | null;
  feeAmount: string;
  feeCurrency: string | null;
  feeRate: string | null;
  feeRateUnit: string | null;
  feeBasis: string;
  accrualDate: string | null;
  settlementDate: string | null;
  status: string;
  externalReference: string | null;
};

export type TradeExternalReference = {
  tradeExternalReferenceId: string;
  sourceSystemId: string | null;
  tradePartyRoleId: string | null;
  referenceType: string;
  referenceValue: string;
  sourceReceivedAtUtc: string | null;
};

export type TradeLifecycleEvent = {
  tradeLifecycleEventId: string;
  sequenceNo: number;
  eventType: string;
  eventDatetimeUtc: string;
  sourceSystemId: string | null;
  sourceEventId: string | null;
  eventPayload: string | null;
  recordedByUserAccountId: string;
  recordedAtUtc: string;
};

export type TradeDetailPayload = {
  data: {
    trade: BookedTrade;
    parties: TradeParty[];
    fees: TradeFee[];
    externalReferences: TradeExternalReference[];
    lifecycleEvents: TradeLifecycleEvent[];
    properties?: import("api-contracts").components["schemas"]["TradePropertyValueView"][];
    tags?: import("api-contracts").components["schemas"]["TradeTagView"][];
    traderName?: string | null;
  };
  meta: { source: string; apiVersion: string; correlationId: string };
};

export function formatTradeNumber(value: string | null, maximumFractionDigits = 4): string {
  if (value === null) return "—";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toLocaleString("en-GB", { maximumFractionDigits }) : value;
}

/** Group decimal text without losing any digits to JavaScript numbers. */
export function formatTradeExactDecimal(value:string|null):string {
  if(value===null)return "—";
  if(!/^-?\d+(?:\.\d+)?$/.test(value))return value;
  const [integer,fraction]=value.split(".");
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g,",")+(fraction===undefined?"":`.${fraction}`);
}

export function tradeDirection(quantity: string): "BUY" | "SELL" {
  return Number(quantity) < 0 ? "SELL" : "BUY";
}

export function formatTradeDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString().replace("T", " ").replace(".000Z", "Z");
}
