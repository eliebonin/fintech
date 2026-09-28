"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Card,
  Divider,
  FormControlLabel,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import { WorkspaceShell } from "@/components/workspace-shell";
import {
  CurrencyGroup,
  InstrumentSearchPayload,
  OrganisationOption,
  createIdempotencyKey,
  listCurrenciesFromBff,
  listOrganisationsFromBff,
  searchReferenceInstrumentsFromBff,
  submitEtpProposalFromBff,
} from "@/lib/browser-api-client";
import type { InstrumentRecord } from "@/lib/instrument-data";
import { validateEtpIdentity } from "./validation";

const ETP_KINDS = [
  { value: "ETF", label: "ETF — fund/share-class wrapper", description: "Usually an open-ended fund or share class traded intraday and intended to track an index, basket, or strategy." },
  { value: "ETC", label: "ETC — exchange-traded commodity product", description: "Usually a debt or certificate wrapper providing exposure to a commodity or commodity index." },
  { value: "ETN", label: "ETN — exchange-traded note", description: "A debt obligation whose repayment follows an index, strategy, or other reference and remains exposed to issuer credit." },
  { value: "ETV", label: "ETV — exchange-traded vehicle", description: "An exchange-traded vehicle that is not being represented as a UCITS ETF." },
  { value: "ETI", label: "ETI — other exchange-traded instrument", description: "Use for an exchange-traded product that does not fit the other governed wrappers." },
] as const;
const LEGAL_FORMS = ["UCITS_FUND", "OTHER_FUND", "DEBT_NOTE", "CERTIFICATE", "TRUST", "OTHER"];
const REPLICATION_METHODS = ["PHYSICAL", "SYNTHETIC", "HYBRID", "NOT_APPLICABLE"];
const COLLATERALISATION = ["NOT_APPLICABLE", "PHYSICAL", "SECURED", "CASH", "UNSECURED"];
const REDEMPTION_MODELS = ["OPEN_ENDED", "FIXED_MATURITY", "ISSUER_REDEEMABLE"];
const DISTRIBUTION_POLICIES = ["ACCUMULATING", "DISTRIBUTING", "NONE", "UNKNOWN"];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

const floatedLabel = { inputLabel: { shrink: true } } as const;
const nativeSelect = { ...floatedLabel, select: { native: true } } as const;

export default function NewEtpPage() {
  const [canonicalName, setCanonicalName] = useState("");
  const [internalCode, setInternalCode] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState(today());
  const [etpKind, setEtpKind] = useState("");
  const [legalForm, setLegalForm] = useState("");
  const [replicationMethod, setReplicationMethod] = useState("NOT_APPLICABLE");
  const [collateralisationType, setCollateralisationType] = useState("NOT_APPLICABLE");
  const [redemptionModel, setRedemptionModel] = useState("");
  const [distributionPolicy, setDistributionPolicy] = useState("");
  const [issuerOrganisationId, setIssuerOrganisationId] = useState("");
  const [baseCurrencyId, setBaseCurrencyId] = useState("");
  const [isin, setIsin] = useState("");
  const [includeCrypto, setIncludeCrypto] = useState(false);
  const [currencyGroups, setCurrencyGroups] = useState<CurrencyGroup[]>([]);
  const [organisations, setOrganisations] = useState<OrganisationOption[]>([]);
  const [catalogueState, setCatalogueState] = useState<"loading" | "ready" | "error">("loading");
  const [referenceQuery, setReferenceQuery] = useState("");
  const [referenceResults, setReferenceResults] = useState<InstrumentRecord[]>([]);
  const [referenceNodeId, setReferenceNodeId] = useState("");
  const [selectedReference, setSelectedReference] = useState<InstrumentRecord | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ severity: "success" | "error" | "info"; text: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const idempotencyKey = useRef<string | undefined>(undefined);

  useEffect(() => {
    let mounted = true;
    setCatalogueState("loading");
    Promise.all([listCurrenciesFromBff(fetch, includeCrypto ? ["REGULAR", "CRYPTO"] : ["REGULAR"]), listOrganisationsFromBff()])
      .then(([currencies, organisationResponse]) => {
        if (!mounted) return;
        setCurrencyGroups(currencies.data);
        setOrganisations(organisationResponse.data);
        setCatalogueState("ready");
      })
      .catch(() => {
        if (mounted) setCatalogueState("error");
      });
    return () => {
      mounted = false;
    };
  }, [includeCrypto]);

  async function searchReference() {
    if (!referenceQuery.trim()) {
      setReferenceResults([]);
      setSearchError(null);
      return;
    }
    setSearching(true);
    setSearchError(null);
    try {
      const response: InstrumentSearchPayload = await searchReferenceInstrumentsFromBff(referenceQuery.trim());
      setReferenceResults(response.data);
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : "Reference search is unavailable");
      setReferenceResults([]);
    } finally {
      setSearching(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors = validateEtpIdentity(canonicalName, etpKind, legalForm, redemptionModel);
    const firstError = errors.canonicalName ?? errors.etpKind ?? errors.legalForm ?? errors.redemptionModel;
    if (firstError) {
      setMessage({ severity: "error", text: firstError });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    try {
      const response = await submitEtpProposalFromBff({
        canonicalName: canonicalName.trim(),
        internalCode: internalCode.trim() || undefined,
        effectiveFrom,
        etpKind,
        legalForm,
        replicationMethod,
        collateralisationType,
        redemptionModel,
        distributionPolicy: distributionPolicy || undefined,
        issuerOrganisationId: issuerOrganisationId || undefined,
        baseCurrencyId: baseCurrencyId || undefined,
        referenceNodeId: referenceNodeId || undefined,
        isin: isin.trim() || undefined,
        submissionMode: "MANUAL",
      }, idempotencyKey.current ?? (idempotencyKey.current = createIdempotencyKey()));
      setMessage({ severity: "info", text: `${response.data.status} · ${response.data.etpKind}. Proposal ${response.data.proposalId} is queued for Operations review.` });
    } catch (error) {
      setMessage({ severity: "error", text: error instanceof Error ? error.message : "ETP proposal could not be submitted" });
    } finally {
      setSubmitting(false);
    }
  }

  const selectedKind = ETP_KINDS.find((item) => item.value === etpKind);
  return (
    <WorkspaceShell>
      <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
        <Box sx={{ maxWidth: 1080, mx: "auto" }}>
          <Typography variant="caption" color="text.secondary"><Link href="/">WORKSPACE / INSTRUMENTS</Link></Typography>
          <Typography variant="h4" sx={{ mt: 1 }}>Add an exchange-traded product</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2.5 }}>Create the economic ETF, ETC, ETN, ETV, or ETI first. Venue listings, share-class detail, and constituent snapshots are separate records.</Typography>
          <Alert severity="info" sx={{ mb: 2.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Manual submission is the default</Typography>
            <Typography variant="body2" sx={{ mt: 0.35 }}>This form creates a pending proposal. Operations approves the canonical record; provider enrichment can complete terms that are not known at submission.</Typography>
          </Alert>
          {message && <Alert severity={message.severity} sx={{ mb: 2 }}>{message.text}</Alert>}

          <Card component="form" noValidate onSubmit={submit} sx={{ p: { xs: 2, md: 3 } }}>
            <Stack spacing={3}>
              <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 }, bgcolor: "#f7faff", borderColor: "#bfd3ff", borderLeft: "5px solid #1f5eff" }}>
                <Stack spacing={2.25}>
                  <Box>
                    <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>1 · ECONOMIC IDENTITY</Typography>
                    <Typography variant="h6">What product is this?</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>These fields identify the economic wrapper. A listing such as ISF on XLON is added later and is not another ETP.</Typography>
                  </Box>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                    <TextField label="Canonical name" value={canonicalName} onChange={(event) => setCanonicalName(event.target.value)} required fullWidth slotProps={floatedLabel} helperText="Official product name from the prospectus, KID, or provider. Include the share-class/currency distinction when it is part of the security name." />
                    <TextField label="Internal code (optional)" value={internalCode} onChange={(event) => setInternalCode(event.target.value)} fullWidth slotProps={floatedLabel} helperText="Stable platform-owned code; unique when supplied. Do not use a venue ticker here." />
                  </Stack>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                    <TextField label="Effective from" type="date" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} required fullWidth slotProps={floatedLabel} helperText="Date from which this economic definition is valid." />
                    <TextField label="ISIN (optional)" value={isin} onChange={(event) => setIsin(event.target.value)} fullWidth slotProps={floatedLabel} helperText="Economic security identifier, when already known. Venue-specific identifiers belong to the later listing." />
                    <TextField select label="ETP kind" value={etpKind} onChange={(event) => setEtpKind(event.target.value)} required fullWidth slotProps={nativeSelect} helperText={selectedKind?.description ?? "Choose the legal/economic wrapper closest to the product."}>
                      <option value="">— Choose a product kind —</option>
                      {ETP_KINDS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                    </TextField>
                  </Stack>
                  {selectedKind && <Box sx={{ p: 1.5, bgcolor: "#eef5ff", borderRadius: 1.5 }}><Typography variant="body2" color="text.secondary">{selectedKind.description}</Typography></Box>}
                </Stack>
              </Paper>

              <Divider />
              <Box>
                <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>2 · WRAPPER TERMS</Typography>
                <Typography variant="h6">How is the product structured?</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>Capture what is known now. Do not guess missing legal terms; Operations or an authorised provider can enrich them before approval.</Typography>
              </Box>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField select label="Legal form" value={legalForm} onChange={(event) => setLegalForm(event.target.value)} required fullWidth slotProps={nativeSelect} helperText="ETF commonly uses UCITS_FUND; ETC/ETN commonly use DEBT_NOTE or CERTIFICATE.">
                  <option value="">— Choose a legal form —</option>{LEGAL_FORMS.map((value) => <option key={value} value={value}>{value}</option>)}
                </TextField>
                <TextField select label="Replication / exposure method" value={replicationMethod} onChange={(event) => setReplicationMethod(event.target.value)} fullWidth slotProps={nativeSelect} helperText="How exposure is obtained; NOT_APPLICABLE is valid when it is not known or not meaningful.">
                  {REPLICATION_METHODS.map((value) => <option key={value} value={value}>{value}</option>)}
                </TextField>
                <TextField select label="Collateralisation / credit basis" value={collateralisationType} onChange={(event) => setCollateralisationType(event.target.value)} fullWidth slotProps={nativeSelect} helperText="Important for debt-style ETPs: secured, physical, cash, or unsecured issuer exposure.">
                  {COLLATERALISATION.map((value) => <option key={value} value={value}>{value}</option>)}
                </TextField>
              </Stack>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField select label="Redemption model" value={redemptionModel} onChange={(event) => setRedemptionModel(event.target.value)} required fullWidth slotProps={nativeSelect} helperText="Whether the wrapper is open-ended, has fixed maturity, or can be redeemed by the issuer.">
                  <option value="">— Choose a redemption model —</option>{REDEMPTION_MODELS.map((value) => <option key={value} value={value}>{value}</option>)}
                </TextField>
                <TextField select label="Distribution policy (optional)" value={distributionPolicy} onChange={(event) => setDistributionPolicy(event.target.value)} fullWidth slotProps={nativeSelect} helperText="For funds/share classes, whether income accumulates or distributes. Use NONE for products without distributions.">
                  <option value="">— Not specified —</option>{DISTRIBUTION_POLICIES.map((value) => <option key={value} value={value}>{value}</option>)}
                </TextField>
              </Stack>

              <Divider />
              <Box>
                <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>3 · ISSUER, CURRENCY AND REFERENCE</Typography>
                <Typography variant="h6">Who issued it and what does it reference?</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>Issuer and denomination are economic facts. The primary reference is optional, but selecting an existing canonical index or commodity makes the relationship explicit and prevents free-text aliases.</Typography>
              </Box>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField select label="Issuer organisation (optional)" value={issuerOrganisationId} onChange={(event) => setIssuerOrganisationId(event.target.value)} fullWidth disabled={catalogueState === "loading"} slotProps={nativeSelect} helperText={catalogueState === "loading" ? "Loading active organisations…" : catalogueState === "error" ? "Organisation catalogue unavailable; enrich during review." : "Select the legal issuer. Leave blank for provider enrichment or a decentralised/open vehicle."}>
                  <option value="">— Not specified —</option>{organisations.map((item) => <option key={item.organisationId} value={item.organisationId}>{item.displayName}{item.legalName ? ` · ${item.legalName}` : ""}</option>)}
                </TextField>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <TextField select label="Base / denomination currency (optional)" value={baseCurrencyId} onChange={(event) => setBaseCurrencyId(event.target.value)} fullWidth disabled={catalogueState === "loading"} slotProps={nativeSelect} helperText={catalogueState === "loading" ? "Loading active currencies…" : catalogueState === "error" ? "Currency catalogue unavailable; enrich during review." : "Currency in which the economic value/NAV is normally expressed; listing currencies are separate."}>
                    <option value="">— Not specified —</option>{currencyGroups.map((group) => <optgroup key={group.groupCode} label={group.label}>{group.items.map((item) => <option key={item.currencyId} value={item.currencyId}>{item.currencyCode} · {item.displayName}</option>)}</optgroup>)}
                  </TextField>
                  <FormControlLabel sx={{ ml: 0, mt: 0.25 }} control={<Switch size="small" checked={includeCrypto} onChange={(event) => { const next = event.target.checked; setIncludeCrypto(next); if (!next && currencyGroups.find((group) => group.groupCode === "CRYPTO")?.items.some((item) => item.currencyId === baseCurrencyId)) setBaseCurrencyId(""); }} />} label={<Typography variant="caption">Include cryptoasset currencies</Typography>} />
                </Box>
              </Stack>
              <Paper variant="outlined" sx={{ p: 2, bgcolor: "#fbfcff" }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Primary reference node (optional)</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>Search the live canonical master for an index, commodity, basket, or strategy. This relationship is stored as authoritative `instrument_relationship`; the ETP terms shortcut is populated too.</Typography>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25} sx={{ mt: 1.5 }}>
                  <TextField label="Search canonical references" value={referenceQuery} onChange={(event) => setReferenceQuery(event.target.value)} fullWidth slotProps={floatedLabel} placeholder="S&P 500, gold, MSCI…" />
                  <Button type="button" variant="outlined" onClick={searchReference} disabled={searching}>{searching ? "Searching…" : "Search"}</Button>
                </Stack>
                {searchError && <Typography variant="caption" color="error" sx={{ display: "block", mt: 1 }}>{searchError}</Typography>}
                {referenceResults.length > 0 && <Stack spacing={0.75} sx={{ mt: 1.25 }}>{referenceResults.slice(0, 8).map((item) => <Button key={item.instrumentId} type="button" variant={referenceNodeId === item.instrumentId ? "contained" : "text"} onClick={() => { setReferenceNodeId(item.instrumentId); setSelectedReference(item); }} sx={{ justifyContent: "flex-start", textAlign: "left", textTransform: "none" }}><span><strong>{item.canonicalName}</strong><br /><Typography component="span" variant="caption">{item.instrumentType} · {item.instrumentId}</Typography></span></Button>)}</Stack>}
                {selectedReference && <Alert severity="success" sx={{ mt: 1.25 }} onClose={() => { setSelectedReference(null); setReferenceNodeId(""); }}>Selected: {selectedReference.canonicalName} ({selectedReference.instrumentType})</Alert>}
              </Paper>

              <Alert severity="info">Listings are intentionally separate. After approval, use <Link href="/instruments/listings/new">Add listing</Link> to add the ticker, venue, trading currency, listing FIGI, quote factor, and unit multiplier.</Alert>
              <Stack direction="row" spacing={1.5} sx={{ justifyContent: "space-between", alignItems: "center" }}><Button component={Link} href="/" variant="text">Cancel</Button><Button type="submit" variant="contained" disabled={submitting}>{submitting ? "Submitting…" : "Submit ETP for review"}</Button></Stack>
            </Stack>
          </Card>
        </Box>
      </Box>
    </WorkspaceShell>
  );
}
