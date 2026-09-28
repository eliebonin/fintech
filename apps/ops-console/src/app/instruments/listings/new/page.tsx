"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { WorkspaceShell } from "@/components/workspace-shell";

import type { InstrumentRecord } from "@/lib/instrument-data";
import {
  createIdempotencyKey,
  flattenCurrencyGroups,
  listCurrenciesFromBff,
  listMarketVenuesFromBff,
  searchReferenceInstrumentsFromBff,
  submitEquityListingProposalFromBff,
} from "@/lib/browser-api-client";
import type { CurrencyGroup, MarketVenue } from "@/lib/browser-api-client";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function NewEquityListingPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<InstrumentRecord[]>([]);
  const [selected, setSelected] = useState<InstrumentRecord | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [venues, setVenues] = useState<MarketVenue[]>([]);
  const [venueState, setVenueState] = useState<"loading" | "ready" | "error">("loading");
  const [currencyGroups, setCurrencyGroups] = useState<CurrencyGroup[]>([]);
  const [includeCrypto, setIncludeCrypto] = useState(false);
  const [currencyState, setCurrencyState] = useState<"loading" | "ready" | "error">("loading");
  const [venue, setVenue] = useState("");
  const [symbol, setSymbol] = useState("");
  const [figi, setFigi] = useState("");
  const [venueProductId, setVenueProductId] = useState("");
  const [fixSecurityId, setFixSecurityId] = useState("");
  const [currency, setCurrency] = useState("");
  const [quoteFactor, setQuoteFactor] = useState("1");
  const [unitMultiplier, setUnitMultiplier] = useState("1");
  const [effectiveFrom, setEffectiveFrom] = useState(today());
  const [primary, setPrimary] = useState(false);
  const [message, setMessage] = useState<{ severity: "success" | "error" | "info"; text: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const idempotencyKey = useRef<string | undefined>(undefined);
  const floatedLabel = { inputLabel: { shrink: true } } as const;
  // Use native selects for venue/currency catalogues. This keeps the control
  // reliable in embedded browser surfaces and still renders the DB-backed
  // options supplied by the BFF.
  const nativeSelect = { ...floatedLabel, select: { native: true } } as const;
  const listingColumn = { flex: 1, minWidth: 0 } as const;

  useEffect(() => {
    listMarketVenuesFromBff()
      .then((body) => {
        setVenues(body.data);
        setVenueState("ready");
      })
      .catch(() => setVenueState("error"));
  }, []);

  useEffect(() => {
    let mounted = true;
    setCurrencyState("loading");
    const groups = includeCrypto ? ["REGULAR", "CRYPTO"] as const : ["REGULAR"] as const;
    listCurrenciesFromBff(fetch, [...groups])
      .then((result) => {
        if (!mounted) return;
        setCurrencyGroups(result.data);
        const items = flattenCurrencyGroups(result.data);
        setCurrency((current) => current || items.find((item) => item.currencyCode === "USD")?.currencyId || items[0]?.currencyId || "");
        setCurrencyState("ready");
      })
      .catch(() => {
        if (mounted) setCurrencyState("error");
      });
    return () => {
      mounted = false;
    };
  }, [includeCrypto]);

  async function searchInstruments() {
    if (!query.trim()) {
      setResults([]);
      setSelected(null);
      return;
    }
    setSearching(true);
    setSearchError("");
    try {
      const body = await searchReferenceInstrumentsFromBff(query.trim());
      setResults(body.data);
      setSelected(null);
    } catch (error) {
      setResults([]);
      setSearchError(error instanceof Error ? error.message : "Instrument search is unavailable");
    } finally {
      setSearching(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const body = await submitEquityListingProposalFromBff({
        instrumentId: selected.instrumentId,
        listing: {
          marketVenueId: venue,
          tradingSymbol: symbol,
          figi: figi || undefined,
          venueProductId: venueProductId || undefined,
          fixSecurityId: fixSecurityId || undefined,
          tradingCurrencyId: currency,
          quoteFactor,
          unitMultiplier,
          isPrimaryListing: primary,
          effectiveFrom,
        },
        submissionMode: "MANUAL",
      }, idempotencyKey.current ?? (idempotencyKey.current = createIdempotencyKey()));
      setMessage({
        severity: "info",
        text: `${body.data?.status ?? "PENDING"} · listing proposal ${body.data?.proposalId} for ${selected.canonicalName}. It is queued for operations approval; it will appear as a canonical listing only after approval.`,
      });
    } catch (error) {
      setMessage({ severity: "error", text: error instanceof Error ? error.message : "Listing proposal could not be submitted" });
    } finally {
      setSubmitting(false);
    }
  }

  const selectedVenue = venues.find((item) => item.marketVenueId === venue);
  const duplicateListing = selected?.listings.find((listing) =>
    listing.marketVenueMic === selectedVenue?.venueCode
    && listing.tradingSymbol?.trim().toUpperCase() === symbol.trim().toUpperCase()
  );

  return (
    <WorkspaceShell><Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
      <Box sx={{ maxWidth: 980, mx: "auto" }}>
        <Typography variant="caption" color="text.secondary"><Link href="/">WORKSPACE / INSTRUMENTS</Link></Typography>
        <Typography variant="h4" sx={{ mt: 1 }}>Add a venue listing</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2.5 }}>Select an existing approved economic instrument first. Venue and ticker facts are stored as a separate listing proposal.</Typography>

        <Alert severity="info" sx={{ mb: 2.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Parent instrument is mandatory</Typography>
          <Typography variant="body2" sx={{ mt: 0.35 }}>A listing is never created from free text. Search the canonical master, review the issuer and identifiers, then select the exact instrument before entering venue-specific data.</Typography>
        </Alert>

        {message && <Alert severity={message.severity} sx={{ mb: 2 }}>{message.text}</Alert>}

        <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 }, mb: 2.5, bgcolor: "white" }}>
          <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>1 · SELECT ECONOMIC INSTRUMENT</Typography>
          <Typography variant="h6">Which security is this listing for?</Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mt: 1.5 }}>
            <TextField value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void searchInstruments(); }} placeholder="Search name, ISIN, FIGI, ticker, or external code" fullWidth size="small" />
            <Button variant="contained" onClick={() => void searchInstruments()} disabled={searching}>{searching ? "Searching…" : "Search"}</Button>
          </Stack>
          {searchError && <Alert severity="error" sx={{ mt: 1.5 }}>{searchError}</Alert>}
          {results.length > 0 && <Stack spacing={1} sx={{ mt: 1.5 }}>
            {results.map((instrument) => <Button key={instrument.instrumentId} onClick={() => setSelected(instrument)} variant={selected?.instrumentId === instrument.instrumentId ? "contained" : "outlined"} sx={{ justifyContent: "flex-start", textAlign: "left", textTransform: "none" }}>
              <Box><Typography variant="body2" sx={{ fontWeight: 750 }}>{instrument.canonicalName}</Typography><Typography variant="caption" sx={{ display: "block" }}>{instrument.instrumentType} · {instrument.issuer ?? "Issuer unresolved"} · {instrument.instrumentId}</Typography></Box>
            </Button>)}
          </Stack>}
          {selected && <Box sx={{ mt: 1.5, p: 1.5, bgcolor: "#eef3ff", border: "1px solid #b9d0ff", borderRadius: 1.5 }}>
            <Typography variant="caption" sx={{ color: "#1647b8", fontWeight: 800 }}>SELECTED INSTRUMENT</Typography>
            <Typography sx={{ fontWeight: 800 }}>{selected.canonicalName}</Typography>
            <Typography variant="body2" color="text.secondary">{selected.instrumentType} · {selected.issuer ?? "Issuer unresolved"} · {selected.baseCurrency ?? "Currency unresolved"}</Typography>
            <Typography variant="caption" sx={{ display: "block", mt: 0.5, fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace" }}>{selected.instrumentId}</Typography>
          </Box>}
          {selected && <Paper variant="outlined" sx={{ mt: 1.5, overflow: "hidden", borderColor: "#d9e1ef" }}>
            <Box sx={{ px: 1.5, py: 1.1, bgcolor: "#f7f9fc", borderBottom: "1px solid #e4e9f2" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Existing listings</Typography>
              <Typography variant="caption" color="text.secondary">Check the venue + ticker key before proposing another listing.</Typography>
            </Box>
            {selected.listings.length === 0 ? (
              <Box sx={{ p: 1.5 }}><Typography variant="body2" sx={{ fontWeight: 650 }}>No active listings attached</Typography><Typography variant="caption" color="text.secondary">This instrument can still be listed; no duplicate key currently exists.</Typography></Box>
            ) : (
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead><TableRow><TableCell>Venue</TableCell><TableCell>Primary symbol</TableCell><TableCell>Trading identifiers</TableCell><TableCell>Trading currency</TableCell><TableCell>Quote factor</TableCell><TableCell>Unit multiplier</TableCell><TableCell>Status</TableCell></TableRow></TableHead>
                  <TableBody>{selected.listings.map((listing) => <TableRow key={listing.listingId} sx={{ bgcolor: duplicateListing?.listingId === listing.listingId ? "#fff4e3" : undefined }}>
                    <TableCell><Typography variant="body2" sx={{ fontWeight: 750 }}>{listing.marketVenueMic}</Typography><Typography variant="caption" color="text.secondary">{listing.venueName}</Typography></TableCell>
                    <TableCell><Typography variant="body2" sx={{ fontWeight: 800 }}>{listing.tradingSymbol}</Typography><Typography variant="caption" color="text.secondary" sx={{ display: "block", fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace" }}>{listing.listingId.slice(0, 13)}…</Typography></TableCell>
                    <TableCell>{(listing.identifiers ?? []).filter((identifier) => ["VENUE_PRODUCT_ID", "FIX_SECURITY_ID"].includes(identifier.scheme)).map((identifier) => <Typography key={`${identifier.scheme}:${identifier.value}`} variant="caption" sx={{ display: "block", fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace" }}>{identifier.scheme}: {identifier.value}</Typography>)}</TableCell>
                    <TableCell>{listing.tradingCurrency}</TableCell>
                    <TableCell>{listing.quoteFactor}</TableCell>
                    <TableCell>{listing.unitMultiplier}</TableCell>
                    <TableCell><Typography variant="caption" sx={{ color: listing.status === "ACTIVE" ? "#14753c" : "#8a5a00", fontWeight: 800 }}>{listing.status}</Typography></TableCell>
                  </TableRow>)}</TableBody>
                </Table>
              </Box>
            )}
          </Paper>}
        </Paper>

        <Paper component="form" onSubmit={submit} noValidate variant="outlined" sx={{ p: { xs: 2, md: 2.5 }, opacity: selected ? 1 : 0.58 }}>
          <Typography variant="overline" color="warning.dark" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>2 · LISTING DATA</Typography>
          <Typography variant="h6">Where and how does it trade?</Typography>
          {!selected && <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2 }}>Select an approved economic instrument above to unlock listing fields.</Typography>}
          <Stack spacing={2} sx={{ mt: 1.5 }}>
            {duplicateListing && <Alert severity="warning" sx={{ bgcolor: "#fff4e3", color: "#6f3b00", border: "1px solid #f0c98a" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Duplicate listing key</Typography>
              <Typography variant="body2">{selectedVenue?.venueCode} + {duplicateListing.tradingSymbol} already exists for this instrument. Choose another venue or ticker.</Typography>
            </Alert>}
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField select label="Market venue" value={venue} onChange={(event) => setVenue(event.target.value)} required fullWidth disabled={!selected || venueState !== "ready"} slotProps={nativeSelect} helperText={venueState === "loading" ? "Loading active venues from the canonical reference database…" : venueState === "error" ? "Canonical venues could not be loaded. Restart the reference API and refresh." : "Select the canonical venue UUID; do not type a venue name."}>
                <option value="">— Choose a venue —</option>
                {venues.map((marketVenue) => <option key={marketVenue.marketVenueId} value={marketVenue.marketVenueId}>{marketVenue.venueCode} · {marketVenue.displayName} ({marketVenue.venueType})</option>)}
              </TextField>
              <TextField label="Primary venue symbol" value={symbol} onChange={(event) => setSymbol(event.target.value)} required fullWidth disabled={!selected} helperText="Primary symbol used by this venue. Example: BTC-USD or TTE." />
              <TextField label="Venue FIGI (optional)" value={figi} onChange={(event) => setFigi(event.target.value)} fullWidth disabled={!selected} helperText="Optional listing-level FIGI; the economic instrument FIGI is not repeated here." />
            </Stack>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField label="Venue product ID (optional)" value={venueProductId} onChange={(event) => setVenueProductId(event.target.value)} fullWidth disabled={!selected} helperText="Venue-native product/market key used by its API or execution adapter." />
              <TextField label="FIX security ID (optional)" value={fixSecurityId} onChange={(event) => setFixSecurityId(event.target.value)} fullWidth disabled={!selected} helperText="Identifier used in FIX execution/allocation messages when different from the symbol." />
            </Stack>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <Box sx={listingColumn}>
                <TextField select label="Quote / trading currency" value={currency} onChange={(event) => setCurrency(event.target.value)} required fullWidth disabled={!selected || currencyState !== "ready"} slotProps={nativeSelect} helperText={currencyState === "loading" ? "Loading active currencies…" : currencyState === "error" ? "Canonical currencies could not be loaded. Refresh after restarting the reference API." : "For crypto, this is the quote asset: BTC/USD, BTC/USDC, or ETH/BTC."}>
                  <option value="">— Choose a currency —</option>
                  {currencyGroups.map((group) => <optgroup key={group.groupCode} label={group.label}>{group.items.map((item) => <option key={item.currencyId} value={item.currencyId}>{item.currencyCode} · {item.displayName} ({item.currencyKind})</option>)}</optgroup>)}
                </TextField>
                <FormControlLabel
                  sx={{ ml: 0, mt: 0.25 }}
                  control={<Switch size="small" checked={includeCrypto} onChange={(event) => {
                    const next = event.target.checked;
                    setIncludeCrypto(next);
                    if (!next && currencyGroups.find((group) => group.groupCode === "CRYPTO")?.items.some((item) => item.currencyId === currency)) setCurrency("");
                  }} disabled={!selected} />}
                  label={<Typography variant="caption">Include cryptoassets</Typography>}
                />
              </Box>
              <Box sx={listingColumn}>
                <TextField label="Quote factor" value={quoteFactor} onChange={(event) => setQuoteFactor(event.target.value)} type="number" required fullWidth disabled={!selected} helperText="Use 100 when a GBP listing is quoted in GBX pence; otherwise normally 1." />
              </Box>
              <Box sx={listingColumn}>
                <TextField label="Unit multiplier" value={unitMultiplier} onChange={(event) => setUnitMultiplier(event.target.value)} type="number" required fullWidth disabled={!selected} helperText="Economic units represented by one traded unit." />
              </Box>
              <Box sx={listingColumn}>
                <TextField label="Listing effective from" type="date" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} required fullWidth disabled={!selected} slotProps={{ inputLabel: { shrink: true } }} />
              </Box>
            </Stack>
            <FormControlLabel control={<Checkbox checked={primary} onChange={(event) => setPrimary(event.target.checked)} disabled={!selected} />} label="Designate as the primary listing" />
            <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
              <Button component={Link} href="/instruments/crypto/new" variant="text">Create a cryptoasset instead</Button>
              <Button type="submit" variant="contained" disabled={!selected || submitting || venueState !== "ready" || currencyState !== "ready" || !venue || !symbol || !currency || Boolean(duplicateListing)}>{submitting ? "Submitting…" : "Submit listing for review"}</Button>
            </Stack>
          </Stack>
        </Paper>
      </Box>
    </Box></WorkspaceShell>
  );
}
