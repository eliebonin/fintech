"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import type { InstrumentRecord } from "@/lib/instrument-data";
import { ProductFacts } from '@/app/trades/new/product-ticket';
import type { ProductTerms } from '@/app/trades/new/product-ticket-model';

function Section({ title, eyebrow, action, children }: { title: string; eyebrow?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <Card sx={{ mb: 2 }}>
      <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
        <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "flex-start", gap: 2 }}>
          <Box>
            {eyebrow && <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.12em", fontWeight: 800 }}>{eyebrow}</Typography>}
            <Typography variant="h6" sx={{ mb: 1.75 }}>{title}</Typography>
          </Box>
          {action}
        </Stack>
        {children}
      </CardContent>
    </Card>
  );
}

function KeyValue({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.35 }}>{label}</Typography>
      <Typography variant="body2" sx={{ fontWeight: 650, fontFamily: mono ? "ui-monospace, SFMono-Regular, Consolas, monospace" : undefined, wordBreak: "break-word" }}>{value}</Typography>
    </Box>
  );
}

export function InstrumentDetail({ instrument, standalone = false, futureTerms }: { instrument: InstrumentRecord; standalone?: boolean; futureTerms?: ProductTerms }) {
  const option = instrument.optionTerms;
  const marketDataRows = [
    ...instrument.instrumentMarketData.map((point) => ({ subject: "INSTRUMENT", symbol: "Economic instrument", point })),
    ...instrument.listings.flatMap((listing) => listing.marketData.map((point) => ({ subject: listing.marketVenueMic, symbol: listing.tradingSymbol, point }))),
  ];
  const content = (
    <Box sx={{ maxWidth: 1180, mx: "auto", p: { xs: 2, md: 3.5 } }}>
      {standalone && (
        <Link href="/" style={{ color: "#1f5eff", fontSize: 13, fontWeight: 700 }}>
          ← Back to search
        </Link>
      )}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 2.5, mt: standalone ? 2 : 0, justifyContent: "space-between", alignItems: { sm: "flex-start" } }}>
        <Box>
          <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: "0.14em", fontWeight: 800 }}>{instrument.instrumentType} · CANONICAL INSTRUMENT</Typography>
          <Typography variant="h4" sx={{ mt: 0.5 }}>{instrument.canonicalName}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.8 }}>{instrument.notes}</Typography>
        </Box>
        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
          <Chip label={instrument.status} color="success" size="small" />
          <Chip label={`Definition v${instrument.definitionVersion}`} variant="outlined" size="small" />
        </Stack>
      </Stack>
      {instrument.instrumentType === 'FUTURE' && (futureTerms ? <ProductFacts terms={futureTerms} configuration/> : <Section title="Futures contract facts"><Typography>Approved contract facts unavailable. Inspect conventions to check the underlying, multiplier and dates; no contract multiplier is inferred from the listing conversion.</Typography></Section>)}
      {['STRUCTURED_PRODUCT','FUTURE','BOND'].includes(instrument.instrumentType)?<Section title="Booking conventions" action={<Button component={Link} href={`/instruments/${instrument.instrumentId}/booking-conventions`}>Inspect / configure conventions</Button>}><Typography>Authoritative quantity, quote and contract conventions are approved in Operations. Book trades from the dedicated Trade booking page, not from a listing.</Typography></Section>:null}

      {instrument.instrumentType === 'OPTION' && <Section title="Option terms" eyebrow="CURRENT GOVERNED REFERENCE FACTS">
        {option ? <Box sx={{ display:'grid', gridTemplateColumns:{xs:'1fr',sm:'repeat(3, 1fr)'}, gap:2 }}>
          <KeyValue label="Option type" value={option.optionType}/>
          <KeyValue label="Underlying" value={option.underlyingName ?? 'Not available to this tenant'}/>
          <KeyValue label="Strike" value={option.strike ? `${option.strike} ${option.strikeCurrency ?? ''}`.trim() : 'Not recorded'}/>
          <KeyValue label="Strike basis" value={option.strikeBasis}/>
          <KeyValue label="Expiry" value={option.expiryDate ?? 'Not recorded'}/>
          <KeyValue label="Last trading instant (UTC)" value={option.lastTradingAtUtc ?? 'Not recorded'}/>
          <KeyValue label="Exercise style" value={option.exerciseStyle}/>
          <KeyValue label="Exercise settlement" value={`${option.settlementMethod}${option.settlementCurrency ? ` · ${option.settlementCurrency}` : ''}`}/>
          <KeyValue label="Deliverable units" value={option.deliverableUnits ?? 'Missing or ambiguous'}/>
          <KeyValue label="Premium currency" value={option.premiumCurrency ?? 'Not recorded'}/>
          <KeyValue label="Premium multiplier" value={option.premiumMultiplier ?? 'Not recorded'}/>
          <KeyValue label="Premium style" value={option.premiumStyle ?? 'Not recorded'}/>
        </Box> : <Typography>No unambiguous current option terms are available. Missing conventions are not defaulted.</Typography>}
        <Typography variant="body2" color="text.secondary" sx={{mt:2}}>These are current instrument facts, not a historical trade snapshot. Listing quotation factors appear below. Booking eligibility is checked when selecting the listing in Book trade.</Typography>
      </Section>}

      <Section title="Canonical identity" eyebrow="SOURCE OF TRUTH">
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(4, 1fr)" }, gap: 2 }}>
          <KeyValue label="Instrument UUID" value={instrument.instrumentId} mono />
          <KeyValue label="Asset class" value={instrument.assetClass} />
          <KeyValue label="Issuer" value={instrument.issuer ?? "Not recorded"} />
          <KeyValue label="Base currency" value={instrument.baseCurrency ?? "Not recorded"} />
          <KeyValue label="Effective from" value={instrument.effectiveFrom ?? "Not recorded"} />
          <KeyValue label="Current version" value={`v${instrument.definitionVersion} · APPROVED`} />
          <KeyValue label="Taxonomy" value={instrument.taxonomy.join(" · ")} />
          <KeyValue label="Listing coverage" value={instrument.listings.length ? "Listed / venue-specific" : "No listing attached"} />
        </Box>
      </Section>

      <Section title="Listings" eyebrow={`${instrument.listings.length} VENUE REPRESENTATION${instrument.listings.length === 1 ? "" : "S"}`} action={<Button component={Link} href={`/instruments/${instrument.instrumentId}/listings/new`} size="small" variant="outlined">Add listing</Button>}>
        {instrument.listings.length === 0 ? (
          <Box sx={{ p: 2, bgcolor: "#f7f9fc", borderRadius: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 650 }}>No listing attached</Typography>
            <Typography variant="body2" color="text.secondary">This economic instrument has no attached venue listing. Absence of a listing does not establish that the instrument is OTC.</Typography>
          </Box>
        ) : (
          <Table size="small">
            <TableHead><TableRow><TableCell>Venue</TableCell><TableCell>Symbol</TableCell><TableCell>Trading currency</TableCell><TableCell>Quote factor</TableCell><TableCell>{instrument.instrumentType==='FUTURE'?'Contracts per listed unit':'Unit multiplier'}</TableCell><TableCell>Status</TableCell></TableRow></TableHead>
            <TableBody>
              {instrument.listings.map((listing) => (
                <TableRow key={listing.listingId} hover>
                  <TableCell><Typography variant="body2" sx={{ fontWeight: 700 }}>{listing.marketVenueMic}</Typography><Typography variant="caption" color="text.secondary">{listing.venueName}</Typography></TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>{listing.tradingSymbol}</TableCell>
                  <TableCell>{listing.tradingCurrency}</TableCell>
                  <TableCell>{listing.quoteFactor}</TableCell>
                  <TableCell>{listing.unitMultiplier}</TableCell>
                  <TableCell><Chip label={listing.status} color="success" size="small" variant="outlined" /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Section>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, gap: 2 }}>
        <Section title="Identifiers" eyebrow="FORMAL IDENTIFIERS">
          <Stack divider={<Divider flexItem />}>
            {instrument.identifiers.map((identifier) => (
              <Stack key={`${identifier.scheme}-${identifier.value}`} direction="row" spacing={2} sx={{ py: 1, justifyContent: "space-between" }}>
                <Typography variant="body2" color="text.secondary">{identifier.scheme} <Chip label={identifier.scope} size="small" sx={{ ml: 0.5, height: 20, fontSize: 10 }} /></Typography>
                <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace" }}>{identifier.value}</Typography>
              </Stack>
            ))}
          </Stack>
        </Section>
        <Section title="External mappings" eyebrow="NAMESPACE-BOUND ALIASES">
          <Stack divider={<Divider flexItem />}>
            {instrument.mappings.length === 0 ? <Typography variant="body2" color="text.secondary">No external mappings recorded.</Typography> : instrument.mappings.map((mapping) => (
              <Stack key={`${mapping.namespace}-${mapping.externalId}`} direction="row" spacing={1} sx={{ py: 1, justifyContent: "space-between", alignItems: "center" }}>
                <Box><Typography variant="body2" sx={{ fontWeight: 700 }}>{mapping.externalId}</Typography><Typography variant="caption" color="text.secondary">{mapping.namespace}</Typography></Box>
                <Chip label={mapping.status} size="small" color={mapping.status === "VERIFIED" ? "success" : "warning"} />
              </Stack>
            ))}
          </Stack>
        </Section>
      </Box>

      <Section title="Market-data evidence" eyebrow="EXPLICIT CUT + VINTAGE">
        {marketDataRows.length === 0 ? (
          <Box sx={{ p: 2, bgcolor: "#fff9ed", borderRadius: 2 }}><Typography variant="body2" sx={{ fontWeight: 650 }}>No fixture observation for this instrument</Typography><Typography variant="body2" color="text.secondary">The resolver will use an instrument-level series when one is entitled and available.</Typography></Box>
        ) : (
          <Table size="small">
            <TableHead><TableRow><TableCell>Series</TableCell><TableCell>Value</TableCell><TableCell>Market date</TableCell><TableCell>Cut</TableCell><TableCell>Provider / dataset</TableCell><TableCell>Vintage</TableCell></TableRow></TableHead>
            <TableBody>{marketDataRows.map(({ subject, symbol, point }, index) => (
              <TableRow key={`${point.referenceNodeId ?? subject}-${point.series}-${index}`} hover>
                <TableCell><Typography variant="body2" sx={{ fontWeight: 700 }}>{point.series}</Typography><Typography variant="caption" color="text.secondary">{subject} · {symbol}</Typography></TableCell>
                <TableCell><Typography variant="body2" sx={{ fontWeight: 750 }}>{point.value} {point.currency}</Typography><Typography variant="caption" color="text.secondary">{point.valueBasis}</Typography></TableCell>
                <TableCell>{point.marketDate}</TableCell>
                <TableCell>{point.valuationCut}</TableCell>
                <TableCell><Typography variant="body2">{point.provider}</Typography><Typography variant="caption" color="text.secondary">{point.dataset}</Typography></TableCell>
                <TableCell><Typography variant="caption" sx={{ fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace" }}>{point.vintage}</Typography><Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>received {point.receivedAt.replace("T", " ").replace("Z", " UTC")}</Typography></TableCell>
              </TableRow>
            ))}</TableBody>
          </Table>
        )}
      </Section>
    </Box>
  );

  return standalone ? <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb" }}>{content}</Box> : content;
}
