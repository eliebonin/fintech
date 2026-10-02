export type InstrumentIdentifier = {
  scheme: string;
  value: string;
  scope: string;
};

export type ExternalMapping = {
  namespace: string;
  externalId: string;
  status: string;
  mappingRole: string;
};

export type MarketDataPoint = {
  series: string;
  value: string;
  currency: string | null;
  marketDate: string | null;
  valuationCut: string | null;
  provider: string;
  dataset: string;
  vintage: string;
  receivedAt: string;
  valueBasis: string;
  referenceNodeId?: string | null;
};

export type InstrumentListing = {
  listingId: string;
  marketVenueMic: string;
  venueName: string;
  tradingSymbol: string | null;
  tradingCurrency: string | null;
  status: string;
  quoteFactor: string;
  unitMultiplier: string;
  identifiers?: InstrumentIdentifier[];
  marketData: MarketDataPoint[];
};

export type OptionInstrumentTerms = {
  optionType: string; underlyingId: string | null; underlyingName: string | null;
  strike: string | null; strikeBasis: string; strikeCurrency: string | null;
  expiryDate: string | null; lastTradingAtUtc: string | null; exerciseStyle: string;
  settlementMethod: string; settlementCurrency: string | null; deliverableUnits: string | null;
  premiumCurrency: string | null; premiumMultiplier: string | null; premiumStyle: string | null;
};

export type InstrumentRecord = {
  instrumentId: string;
  canonicalName: string;
  instrumentType: string;
  assetClass: string;
  /** API status is intentionally open-ended so new lifecycle states remain displayable. */
  status: string;
  issuer: string | null;
  baseCurrency: string | null;
  definitionVersion: number;
  effectiveFrom: string | null;
  identifiers: InstrumentIdentifier[];
  mappings: ExternalMapping[];
  listings: InstrumentListing[];
  instrumentMarketData: MarketDataPoint[];
  taxonomy: string[];
  notes: string;
  optionTerms?: OptionInstrumentTerms | null;
};

const instruments: InstrumentRecord[] = [
  {
    instrumentId: "0198f4de-2fb5-7b8b-8c0d-000000000101",
    canonicalName: "HSBC Holdings plc ordinary shares",
    instrumentType: "EQUITY",
    assetClass: "EQUITY",
    status: "ACTIVE",
    issuer: "HSBC Holdings plc",
    baseCurrency: "GBP",
    definitionVersion: 3,
    effectiveFrom: "2025-01-01",
    identifiers: [
      { scheme: "ISIN", value: "GB0005405286", scope: "INSTRUMENT" },
      { scheme: "FIGI", value: "BBG000C05BD1", scope: "INSTRUMENT" },
      { scheme: "INTERNAL", value: "EQ-HSBC-ORD", scope: "INSTRUMENT" },
    ],
    mappings: [
      { namespace: "BANK_A_STATIC_PROD", externalId: "ABC", status: "VERIFIED", mappingRole: "PRIMARY" },
      { namespace: "CUSTODIAN_B_ASSET_PROD", externalId: "FOO", status: "VERIFIED", mappingRole: "ALIAS" },
      { namespace: "CLIENT_C_SECURITY_MASTER", externalId: "XYZ", status: "PROPOSED", mappingRole: "ALIAS" },
    ],
    listings: [
      {
        listingId: "0198f4de-2fb5-7b8b-8c0d-000000000201",
        marketVenueMic: "XLON",
        venueName: "London Stock Exchange",
        tradingSymbol: "HSBA",
        tradingCurrency: "GBX",
        status: "ACTIVE",
        quoteFactor: "100",
        unitMultiplier: "1",
        marketData: [
          {
            series: "OFFICIAL_CLOSE",
            value: "1032.50",
            currency: "GBX",
            marketDate: "2026-08-31",
            valuationCut: "LONDON_CLOSE",
            provider: "Exchange feed",
            dataset: "LSE_EQUITIES_EOD",
            vintage: "LSE-20260901-001",
            receivedAt: "2026-09-01T17:12:00Z",
            valueBasis: "RAW",
          },
          {
            series: "BID",
            value: "1031.50",
            currency: "GBX",
            marketDate: "2026-08-31",
            valuationCut: "LONDON_CLOSE",
            provider: "Exchange feed",
            dataset: "LSE_EQUITIES_EOD",
            vintage: "LSE-20260901-001",
            receivedAt: "2026-09-01T17:12:00Z",
            valueBasis: "RAW",
          },
        ],
      },
      {
        listingId: "0198f4de-2fb5-7b8b-8c0d-000000000202",
        marketVenueMic: "XPAR",
        venueName: "Euronext Paris",
        tradingSymbol: "HSB",
        tradingCurrency: "EUR",
        status: "ACTIVE",
        quoteFactor: "1",
        unitMultiplier: "1",
        marketData: [
          {
            series: "OFFICIAL_CLOSE",
            value: "12.08",
            currency: "EUR",
            marketDate: "2026-08-31",
            valuationCut: "PARIS_CLOSE",
            provider: "Venue composite",
            dataset: "EURONEXT_EQUITIES_EOD",
            vintage: "XPAR-20260901-004",
            receivedAt: "2026-09-01T17:20:00Z",
            valueBasis: "RAW",
          },
        ],
      },
    ],
    instrumentMarketData: [],
    taxonomy: ["LISTED_EQUITY", "CROSS_LISTED"],
    notes: "Synthetic fixture demonstrating one economic instrument with two venue listings.",
  },
  {
    instrumentId: "0198f4de-2fb5-7b8b-8c0d-000000000102",
    canonicalName: "Northstar Infrastructure 2031 senior bond",
    instrumentType: "BOND",
    assetClass: "FIXED_INCOME",
    status: "ACTIVE",
    issuer: "Northstar Infrastructure plc",
    baseCurrency: "GBP",
    definitionVersion: 2,
    effectiveFrom: "2026-01-01",
    identifiers: [
      { scheme: "ISIN", value: "XS0000002031", scope: "INSTRUMENT" },
      { scheme: "INTERNAL", value: "BOND-NSTAR-2031", scope: "INSTRUMENT" },
    ],
    mappings: [
      { namespace: "CUSTODIAN_B_ASSET_PROD", externalId: "BOND-NS-31", status: "VERIFIED", mappingRole: "PRIMARY" },
    ],
    listings: [],
    instrumentMarketData: [],
    taxonomy: ["OTC_BOND", "STERLING_CREDIT"],
    notes: "Synthetic OTC bond fixture; its evaluated price is held at the economic-instrument level.",
  },
  {
    instrumentId: "0198f4de-2fb5-7b8b-8c0d-000000000103",
    canonicalName: "GBP/EUR 1M forward quote series",
    instrumentType: "FX_FORWARD",
    assetClass: "FX",
    status: "ACTIVE",
    issuer: "Internal reference market",
    baseCurrency: "GBP",
    definitionVersion: 1,
    effectiveFrom: "2026-01-01",
    identifiers: [
      { scheme: "INTERNAL", value: "FX-GBPEUR-1M-SERIES", scope: "INSTRUMENT" },
    ],
    mappings: [],
    listings: [],
    instrumentMarketData: [],
    taxonomy: ["ROLLING_FX_FORWARD_SERIES"],
    notes: "Synthetic market-data reference object; an actual negotiated forward would be a separate economic instrument.",
  },
];

export function searchInstruments(query: string): InstrumentRecord[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return instruments;
  }

  return instruments.filter((instrument) => {
    const searchable = [
      instrument.canonicalName,
      instrument.instrumentId,
      instrument.instrumentType,
      instrument.issuer,
      ...instrument.identifiers.map((identifier) => identifier.value),
      ...instrument.mappings.map((mapping) => mapping.externalId),
      ...instrument.listings.flatMap((listing) => [listing.tradingSymbol, listing.marketVenueMic]),
    ];
    return searchable.some((value) => (value ?? "").toLowerCase().includes(normalized));
  });
}

export function getInstrument(instrumentId: string): InstrumentRecord | undefined {
  return instruments.find((instrument) => instrument.instrumentId === instrumentId);
}
