# Screen specification: crypto venue listing onboarding

## Purpose

Create a venue-specific crypto market representation only after an approved
canonical cryptoasset exists. The workflow supports BTC/USD, BTC/USDC,
USDC/USD, and equivalent pairs without duplicating the underlying asset.

## Existing route

`/instruments/crypto/new` is the canonical parent workflow. It creates a
pending `DIGITAL_ASSET` economic-instrument proposal; approval materialises the
stable UUID, versioned `secm.crypto_asset_terms`, and a matching
`secm.currency.reference_node_id` role. The form is manual-first and lets
Operations leave issuer and precision unknown for later enrichment.

Pending parent proposals are reviewed at
`/instruments/crypto/review/{proposalId}`. The review screen is tenant-scoped,
shows the submitted identity and protocol facts, requires an auditable reason,
and sends an explicit approve/reject decision. Approval creates the instrument
and currency role atomically; a rejected proposal creates neither.

`/instruments/listings/new` is the shared listing workflow. It searches the
canonical instrument catalogue, so it can select a `DIGITAL_ASSET` as well as
an equity. The browser submits a manual proposal through the BFF; Operations
approval materialises the listing.

## Required and optional fields

| Field | Scope | Rule |
|---|---|---|
| Economic instrument | Parent | Must be an approved canonical node. For crypto this is the base asset. |
| Market venue | Listing | Loaded from `secm.market_venue`; CEX/DEX venues are valid without a MIC. |
| Primary venue symbol | Listing | Required; e.g. `BTC-USD` or `BTCUSDC`. |
| Quote/trading currency | Listing | Loaded from `secm.currency`; can be fiat or another cryptoasset role. The selector starts with regular currencies and can request the crypto group with its toggle. |
| Venue product ID | Listing identifier | Optional venue-native API/product key; operational, not merely reporting. |
| FIX security ID | Listing identifier | Optional execution/allocation identifier. |
| Venue FIGI | Listing identifier | Optional where the venue/security has one. |
| Quote factor/unit multiplier | Listing terms | Default to 1 and remain distinct from the parent asset's economics. |

The existing-listings panel shows venue, symbol, quote currency, and operational
identifier rows before submission to make duplicate markets visible.

## Storage contract

- `secm.listing.trading_symbol` stores the primary operational symbol.
- `secm.financial_reference_identifier` stores `TICKER`,
  `VENUE_PRODUCT_ID`, `FIX_SECURITY_ID`, and other venue-context identifiers.
- `ing.external_object_mapping` stores provider, custodian, broker, and client
  aliases.
- The identifier actually used by an execution/import remains a typed
  `trd.trade_external_reference` for audit and reconciliation.

## Deferred

The initial parent workflow intentionally does not create chain deployments.
Add a separate deployment screen/API for `secm.crypto_asset_deployment` once
network and contract-address governance is needed; a parent asset can have
multiple deployments and a native asset has no contract address.

Venue-specific minimum notional, quantity step, price increment, and API route
constraints should be added as generic listing execution terms once an actual
venue adapter requires them; they do not belong in cryptoasset parent terms.
