"use client";

import { FormEvent, useRef, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Card,
  Divider,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import {
  OrganisationOption,
  submitCryptoAssetProposalFromBff,
  createIdempotencyKey,
} from "@/lib/browser-api-client";
import { validateCryptoAssetIdentity } from "./validation";

const SUBTYPES = [
  { value: "NATIVE", label: "Native network asset", description: "The native asset of a blockchain, such as BTC or ETH." },
  { value: "TOKEN", label: "Token", description: "A token issued by a protocol or contract." },
  { value: "STABLECOIN", label: "Stablecoin", description: "A token designed to track a reference currency or value." },
  { value: "WRAPPED", label: "Wrapped asset", description: "A representation of another asset on a different network." },
  { value: "BRIDGED", label: "Bridged asset", description: "An asset representation moved through a cross-chain bridge." },
  { value: "OTHER", label: "Other digital asset", description: "Use when the asset does not fit the governed categories above." },
] as const;

type Props = {
  organisations: OrganisationOption[];
  error: string | null;
};

export default function NewCryptoAssetForm({ organisations, error }: Props) {
  const [canonicalName, setCanonicalName] = useState("");
  const [internalCode, setInternalCode] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState(() => new Date().toISOString().slice(0, 10));
  const [assetSubtype, setAssetSubtype] = useState("");
  const [nativeSymbol, setNativeSymbol] = useState("");
  const [protocolName, setProtocolName] = useState("");
  const [issuerOrganisationId, setIssuerOrganisationId] = useState("");
  const [decimals, setDecimals] = useState("");
  const [message, setMessage] = useState<{ severity: "success" | "error" | "info"; text: string } | null>(null);
  const [reviewProposalId, setReviewProposalId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const idempotencyKey = useRef<string | undefined>(undefined);
  const [identityErrors, setIdentityErrors] = useState<{ canonicalName?: string; assetSubtype?: string; nativeSymbol?: string }>({});
  const floatedLabel = { inputLabel: { shrink: true } } as const;
  // Native selects keep catalogue options reliable in embedded browser surfaces.
  const nativeSelect = { ...floatedLabel, select: { native: true } } as const;
  const floatedNumber = { ...floatedLabel, htmlInput: { min: 0, max: 36, step: 1 } } as const;
  const selectedSubtype = SUBTYPES.find((item) => item.value === assetSubtype);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationErrors = validateCryptoAssetIdentity(canonicalName, assetSubtype, nativeSymbol);
    setIdentityErrors(validationErrors);
    if (validationErrors.canonicalName || validationErrors.assetSubtype || validationErrors.nativeSymbol) {
      setMessage({ severity: "error", text: validationErrors.canonicalName ?? validationErrors.assetSubtype ?? validationErrors.nativeSymbol ?? "Complete the required fields." });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    setReviewProposalId(null);
    try {
      const response = await submitCryptoAssetProposalFromBff({
        canonicalName: canonicalName.trim(),
        internalCode: internalCode.trim() || undefined,
        effectiveFrom,
        assetSubtype,
        nativeSymbol: nativeSymbol.trim().toUpperCase(),
        protocolName: protocolName.trim() || undefined,
        issuerOrganisationId: issuerOrganisationId || undefined,
        decimals: decimals === "" ? undefined : Number(decimals),
        submissionMode: "MANUAL",
      }, idempotencyKey.current ?? (idempotencyKey.current = createIdempotencyKey()));
      setReviewProposalId(response.data.proposalId);
      setMessage({ severity: "info", text: `${response.data.status} · ${response.data.nativeSymbol}. Proposal ${response.data.proposalId} is queued for Operations review.` });
    } catch (submissionError) {
      setMessage({ severity: "error", text: submissionError instanceof Error ? submissionError.message : "Cryptoasset proposal could not be submitted" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Alert severity="info" sx={{ mb: 2.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Manual submission is the default</Typography>
        <Typography variant="body2" sx={{ mt: 0.35 }}>
          This creates a pending economic DIGITAL_ASSET proposal. Approval creates the stable instrument UUID, crypto terms, and a matching currency role. Network deployments and exchange listings are added afterwards.
        </Typography>
      </Alert>
      {error && <Alert severity="warning" sx={{ mb: 2 }}>{error} Issuer can be enriched later.</Alert>}
      {message && <Alert severity={message.severity} sx={{ mb: 2 }}>{message.text}{reviewProposalId && <Typography variant="body2" sx={{ mt: 0.75 }}><Link href={`/reference-data/review/${reviewProposalId}`}>Open proposal review</Link></Typography>}</Alert>}

      <Card component="form" noValidate onSubmit={submit} sx={{ p: { xs: 2, md: 3 } }}>
        <Stack spacing={3}>
          <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 }, bgcolor: "#f7faff", borderColor: "#bfd3ff", borderLeft: "5px solid #1f5eff" }}>
            <Stack spacing={2.25}>
              <Box>
                <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>1 · ECONOMIC ASSET IDENTITY</Typography>
                <Typography variant="h6">What asset is this?</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>These fields describe the cryptoasset itself. BTC-USD on Coinbase or BTC-USDC on Binance are listings created later, not separate economic assets.</Typography>
              </Box>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField label="Canonical name" value={canonicalName} onChange={(event) => { setCanonicalName(event.target.value); setIdentityErrors((current) => ({ ...current, canonicalName: undefined })); }} required fullWidth slotProps={floatedLabel} error={Boolean(identityErrors.canonicalName)} helperText={identityErrors.canonicalName ?? "Official asset or protocol name, e.g. Bitcoin or USD Coin."} />
                <TextField label="Internal code (optional)" value={internalCode} onChange={(event) => setInternalCode(event.target.value)} fullWidth slotProps={floatedLabel} helperText="Stable platform-owned code, unique when supplied; the UUID remains identity." />
              </Stack>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField select label="Asset subtype" value={assetSubtype} onChange={(event) => { setAssetSubtype(event.target.value); setIdentityErrors((current) => ({ ...current, assetSubtype: undefined })); }} required fullWidth error={Boolean(identityErrors.assetSubtype)} slotProps={nativeSelect} helperText={identityErrors.assetSubtype ?? (selectedSubtype?.description ?? "Choose the closest governed cryptoasset category.")}>
                  <option value="">— Choose an asset subtype —</option>
                  {SUBTYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </TextField>
                <TextField label="Canonical / native symbol" value={nativeSymbol} onChange={(event) => { setNativeSymbol(event.target.value.toUpperCase()); setIdentityErrors((current) => ({ ...current, nativeSymbol: undefined })); }} required fullWidth slotProps={floatedLabel} error={Boolean(identityErrors.nativeSymbol)} helperText={identityErrors.nativeSymbol ?? "Canonical symbol, e.g. BTC or USDC. Venue symbols belong to listings."} />
                <TextField label="Effective from" type="date" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} required fullWidth slotProps={floatedLabel} helperText="Business date from which this definition is valid." />
              </Stack>
            </Stack>
          </Paper>

          <Divider />
          <Box>
            <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>2 · PROTOCOL AND CURRENCY ROLE</Typography>
            <Typography variant="h6">What supports the asset?</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>The asset is also registered as a currency role so balances, quotes, and crypto-to-crypto listings can reference the same canonical UUID. Chain-specific deployments remain separate.</Typography>
          </Box>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField label="Protocol / programme name (optional)" value={protocolName} onChange={(event) => setProtocolName(event.target.value)} fullWidth slotProps={floatedLabel} placeholder="Bitcoin, Ethereum, Circle USDC…" helperText="Protocol or issuer programme; leave blank for a genuinely decentralised asset." />
            <TextField label="Smallest-unit decimals (optional)" value={decimals} onChange={(event) => setDecimals(event.target.value)} type="number" fullWidth slotProps={floatedNumber} helperText="Used for the currency role and later deployments, e.g. BTC 8 or USDC 6." />
          </Stack>
          <TextField select label="Issuer / controlling organisation (optional)" value={issuerOrganisationId} onChange={(event) => setIssuerOrganisationId(event.target.value)} fullWidth slotProps={nativeSelect} helperText={organisations.length ? "Select an existing legal issuer where one exists. Leave blank for a decentralised native asset." : "No active organisations are available; leave blank and enrich later."}>
            <option value="">— No issuer / decentralised —</option>
            {organisations.map((item) => <option key={item.organisationId} value={item.organisationId}>{item.displayName}{item.legalName ? ` · ${item.legalName}` : ""}</option>)}
          </TextField>

          <Alert severity="info">
            After approval, use <Link href="/instruments/listings/new">Add a venue listing</Link> to add BTC-USD, BTC-USDC, or another market representation. A future deployment workflow will capture chain/network and contract-address details.
          </Alert>
          <Stack direction="row" spacing={1.5} sx={{ justifyContent: "space-between", alignItems: "center" }}>
            <Button component={Link} href="/" variant="text">Cancel</Button>
            <Button type="submit" variant="contained" disabled={submitting}>{submitting ? "Submitting…" : "Submit cryptoasset for review"}</Button>
          </Stack>
        </Stack>
      </Card>
    </>
  );
}
