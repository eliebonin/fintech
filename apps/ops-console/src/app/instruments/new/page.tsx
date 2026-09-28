"use client";

import { FormEvent, ReactNode, useEffect, useState } from "react";
import Link from "next/link";
import { validateEquityIdentity } from "./validation";
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  Divider,
  FormControlLabel,
  Paper,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { WorkspaceShell } from "@/components/workspace-shell";
import { createIdempotencyKey, flattenCurrencyGroups, listCurrenciesFromBff, submitEquityProposalFromBff } from "@/lib/browser-api-client";
import type { CurrencyGroup } from "@/lib/browser-api-client";

const IDS = {
  sourceSystem: "00000000-0000-7000-8000-000000000021",
  issuer: "00000000-0000-7000-8000-000000000004",
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function SectionIntro({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <Box>
      <Typography variant="overline" sx={{ color: "#1f5eff", letterSpacing: "0.1em", fontWeight: 800 }}>{eyebrow}</Typography>
      <Typography variant="h6" sx={{ mt: 0.1 }}>{title}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.4, maxWidth: 740 }}>{description}</Typography>
    </Box>
  );
}

function FieldHint({ text }: { text: string }) {
  return <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: -1.25 }}>{text}</Typography>;
}

function HelpLabel({ label, tooltip }: { label: string; tooltip: ReactNode }) {
  return (
    <span>
      {label}{" "}
      <Tooltip title={tooltip} arrow>
        <span aria-label={`${label} help`} role="img" style={{ cursor: "help", color: "#1f5eff", fontWeight: 700 }}>ⓘ</span>
      </Tooltip>
    </span>
  );
}

function ScopeBadge({ label, tone }: { label: string; tone: "instrument" | "listing" }) {
  return (
    <Chip
      size="small"
      label={label}
      sx={{
        fontSize: "0.68rem",
        fontWeight: 800,
        letterSpacing: "0.04em",
        color: tone === "instrument" ? "#1647b8" : "#8a4b08",
        bgcolor: tone === "instrument" ? "#e6efff" : "#fff0d9",
        border: "1px solid",
        borderColor: tone === "instrument" ? "#b9d0ff" : "#f0c98a",
      }}
    />
  );
}

export default function NewEquityPage() {
  const [mode, setMode] = useState("MANUAL");
  const [name, setName] = useState("");
  const [internalCode, setInternalCode] = useState("");
  const [issuer, setIssuer] = useState(IDS.issuer);
  const [baseCurrency, setBaseCurrency] = useState("");
  const [currencyGroups, setCurrencyGroups] = useState<CurrencyGroup[]>([]);
  const [includeCrypto, setIncludeCrypto] = useState(false);
  const [currencyState, setCurrencyState] = useState<"loading" | "ready" | "error">("loading");
  const [effectiveFrom, setEffectiveFrom] = useState(today());
  const [isin, setIsin] = useState("");
  const [figi, setFigi] = useState("");
  const [sedol, setSedol] = useState("");
  const [cusip, setCusip] = useState("");
  const [sourceExternalId, setSourceExternalId] = useState("");
  const [sourcePayloadId, setSourcePayloadId] = useState("");
  const sourceObjectType = "INSTRUMENT";
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [confidence, setConfidence] = useState("0.99");
  const [message, setMessage] = useState<{ severity: "success" | "error" | "info"; text: string } | null>(null);
  const [identityErrors, setIdentityErrors] = useState<{ canonicalName?: string }>({});
  const [submitting, setSubmitting] = useState(false);
  const floatedLabel = { inputLabel: { shrink: true } } as const;
  // Keep catalogue options in a native browser select so onboarding remains
  // usable in embedded browser surfaces where portal menus may not open.
  const nativeSelect = { ...floatedLabel, select: { native: true } } as const;

  useEffect(() => {
    let mounted = true;
    setCurrencyState("loading");
    const groups = includeCrypto ? ["REGULAR", "CRYPTO"] as const : ["REGULAR"] as const;
    listCurrenciesFromBff(fetch, [...groups]).then((result) => {
      if (!mounted) return;
      setCurrencyGroups(result.data);
      const items = flattenCurrencyGroups(result.data);
      setBaseCurrency((current) => current || items.find((item) => item.currencyCode === "USD")?.currencyId || items[0]?.currencyId || "");
      setCurrencyState("ready");
    }).catch(() => {
      if (mounted) setCurrencyState("error");
    });
    return () => {
      mounted = false;
    };
  }, [includeCrypto]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationErrors = validateEquityIdentity(name, internalCode);
    setIdentityErrors(validationErrors);
    if (validationErrors.canonicalName) {
      setMessage({ severity: "error", text: validationErrors.canonicalName });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    const payload: Record<string, unknown> = {
      canonicalName: name,
      internalCode: internalCode || undefined,
      issuerOrganisationId: issuer || undefined,
      baseCurrencyId: baseCurrency,
      effectiveFrom,
      isin: isin || undefined,
      figi: figi || undefined,
      sedol: sedol || undefined,
      cusip: cusip || undefined,
      listings: [],
      submissionMode: mode,
    };
    if (mode === "AUTOMATED") {
      Object.assign(payload, {
        sourceSystemId: IDS.sourceSystem,
        sourceNamespace: "BANK_A_STATIC_PROD",
        sourceExternalId,
        sourcePayloadId: sourcePayloadId || undefined,
        sourceObjectType,
        automationPolicyCode: "BANK_A_EQUITY_CREATE",
        idempotencyKey,
        confidenceScore: confidence,
      });
    }
    try {
      const mutationKey = idempotencyKey || createIdempotencyKey();
      if (!idempotencyKey) setIdempotencyKey(mutationKey);
      const response = await submitEquityProposalFromBff(payload, mutationKey);
      setMessage({ severity: response.data?.status === "APPROVED" ? "success" : "info", text: `${response.data?.status ?? "PENDING"} · proposal ${response.data?.proposalId}${response.data?.instrumentId ? ` · instrument ${response.data.instrumentId}` : ""}` });
    } catch (error) {
      setMessage({ severity: "error", text: error instanceof Error ? error.message : "Equity proposal could not be submitted" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <WorkspaceShell><Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
      <Box sx={{ maxWidth: 980, mx: "auto" }}>
        <Typography variant="caption" color="text.secondary"><Link href="/">WORKSPACE / INSTRUMENTS</Link></Typography>
        <Typography variant="h4" sx={{ mt: 1 }}>Add an equity</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2.5 }}>Create a reviewable reference-data proposal for one economic equity. Listings are added separately after the instrument is approved.</Typography>

        <Alert severity="info" sx={{ mb: 2.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Instrument identity versus listing</Typography>
          <Typography variant="body2" sx={{ mt: 0.35 }}><strong>Economic instrument:</strong> the company security itself, identified by its canonical name, issuer, ISIN, FIGI, and denomination currency. It can be OTC or have several listings. <strong>Listing:</strong> a separate venue representation added only after this instrument is approved.</Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mt: 1.25 }}>
            <ScopeBadge label="BLUE · INSTRUMENT DATA" tone="instrument" />
          </Stack>
        </Alert>
        <Stack direction="row" sx={{ justifyContent: "flex-end", mb: 2 }}>
          <Button component={Link} href="/instruments/listings/new" variant="outlined" size="small">Add listing to an approved instrument</Button>
        </Stack>

        <Card component="form" noValidate onSubmit={submit} sx={{ p: { xs: 2, md: 3 } }}>
          <Stack spacing={3}>
            {message && <Alert severity={message.severity}>{message.text}</Alert>}

            <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 }, bgcolor: "#f7faff", borderColor: "#bfd3ff", borderLeft: "5px solid #1f5eff" }}>
              <Stack spacing={2.25}>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25} sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}>
                  <SectionIntro eyebrow="1 · ECONOMIC INSTRUMENT" title="What security is this?" description="These fields describe the underlying equity contract. They are shared by every venue listing of that security." />
                  <ScopeBadge label="INSTRUMENT-LEVEL" tone="instrument" />
                </Stack>
                <Stack spacing={2}>
                  <TextField
                    label={<HelpLabel label="Canonical name" tooltip={<span>
                      <strong>What to enter:</strong> the official name of the economic security, for example “Acme plc Ordinary Shares”. Do not enter ACME (ticker) or a provider code.<br />
                      <strong>Where:</strong> instrument-level; the same security name can have several listings.<br />
                      <strong>Unique?</strong> No. Use ISIN or FIGI for identity and duplicate matching.<br />
                      <strong>Can it change?</strong> Yes, through an approved amendment. The instrument UUID and linked trades stay unchanged.
                    </span>} />}
                    value={name}
                    onChange={(event) => {
                      setName(event.target.value);
                      setIdentityErrors((current) => current.canonicalName ? {} : current);
                    }}
                    required
                    fullWidth
                    error={Boolean(identityErrors.canonicalName)}
                    helperText={identityErrors.canonicalName ?? "Enter the official security name. Do not enter ACME (ticker), XLON (venue), or a bank/provider code here."}
                  />
                  <TextField
                    label={<HelpLabel label="Internal code" tooltip={<span>
                      <strong>What to enter:</strong> an optional short code owned by this platform, for example ACME_EQUITY. It is not an ISIN, FIGI, ticker, Bloomberg code, or exchange symbol.<br />
                      <strong>Where:</strong> instrument-level. Put XLON/ACME or NYSE/ACME in the listing fields.<br />
                      <strong>Unique?</strong> Yes, when supplied, across this master. Do not reuse a retired code.<br />
                      <strong>Can it change?</strong> Yes, through an approved amendment; the instrument UUID remains the same.
                    </span>} />}
                    value={internalCode}
                    onChange={(event) => setInternalCode(event.target.value)}
                    fullWidth
                    helperText="Optional platform-owned code. Keep it short and stable; venue tickers belong in the listing section."
                  />
                  <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                    <TextField select label="Issuer organisation" value={issuer} onChange={(event) => setIssuer(event.target.value)} fullWidth slotProps={nativeSelect} helperText="Select the legal organisation that issued the security—not its parent group, exchange, or data provider. Search existing records first. If there is no confident match, leave this blank and submit for review; one issuer record can be reused for many instruments.">
                      <option value="">Issuer not yet resolved — review required</option>
                      <option value={IDS.issuer}>HSBC Demo plc · issuer organisation</option>
                    </TextField>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <TextField select label="Base / denomination currency" value={baseCurrency} onChange={(event) => setBaseCurrency(event.target.value)} required fullWidth disabled={currencyState !== "ready"} slotProps={nativeSelect} helperText={currencyState === "loading" ? "Loading active currencies…" : currencyState === "error" ? "Currency catalogue unavailable; leave blank and enrich before approval." : "Currency used to express the instrument’s economic denomination. Example: USD."}>
                        <option value="">— Choose a currency —</option>
                        {currencyGroups.map((group) => <optgroup key={group.groupCode} label={group.label}>{group.items.map((item) => <option key={item.currencyId} value={item.currencyId}>{item.currencyCode} · {item.displayName}</option>)}</optgroup>)}
                      </TextField>
                      <FormControlLabel
                        sx={{ ml: 0, mt: 0.25 }}
                        control={<Switch size="small" checked={includeCrypto} onChange={(event) => {
                          const next = event.target.checked;
                          setIncludeCrypto(next);
                          if (!next && currencyGroups.find((group) => group.groupCode === "CRYPTO")?.items.some((item) => item.currencyId === baseCurrency)) setBaseCurrency("");
                        }} />}
                        label={<Typography variant="caption">Include cryptoassets</Typography>}
                      />
                    </Box>
                    <TextField label="Instrument effective from" type="date" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} required fullWidth slotProps={{ inputLabel: { shrink: true } }} helperText="Business date from which this instrument definition is valid." />
                  </Stack>
                </Stack>
                <Divider />
                <Stack spacing={1.5}>
                  <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25} sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}>
                    <SectionIntro eyebrow="2 · INSTRUMENT IDENTIFIERS" title="How do we identify this instrument?" description="These identifiers match the economic security across providers and venues. They do not identify a particular exchange listing." />
                    <ScopeBadge label="INSTRUMENT-LEVEL" tone="instrument" />
                  </Stack>
                  <Stack spacing={2}>
                    <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                      <TextField label="ISIN" value={isin} onChange={(event) => setIsin(event.target.value)} required fullWidth helperText="12-character ISO 6166 identifier for this security. Example: GB00B03MLX29." />
                      <TextField label="Global / share-class FIGI" value={figi} onChange={(event) => setFigi(event.target.value)} fullWidth helperText="FIGI for the security or share class. A venue-level FIGI belongs with the listing." />
                    </Stack>
                    <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                      <TextField label="SEDOL" value={sedol} onChange={(event) => setSedol(event.target.value)} fullWidth helperText="Optional seven-character UK/Ireland security identifier. Example: 0263494." />
                      <TextField label="CUSIP" value={cusip} onChange={(event) => setCusip(event.target.value)} fullWidth helperText="Optional nine-character North American security identifier. Example: 037833100." />
                    </Stack>
                    <TextField label="CFI classification code" value="" disabled fullWidth helperText="Classification only—not an identity key. It will be captured by a later classification workflow." />
                    <FieldHint text="If an instrument identifier is unknown, leave it blank. Never put a ticker in ISIN, FIGI, SEDOL, or CUSIP." />
                  </Stack>
                </Stack>
              </Stack>
            </Paper>

            <Divider />
            <SectionIntro eyebrow="3 · APPROVAL ROUTE" title="How should this proposal enter the workflow?" description="Both routes create an auditable proposal. Neither route allows the browser to write an approved instrument directly." />
            <TextField select label="Submission path" value={mode} onChange={(event) => setMode(event.target.value)} slotProps={nativeSelect} helperText={mode === "AUTOMATED" ? "The source policy checks identifiers, issuer, listing, confidence, and duplicate conflicts. Passing every rule may auto-approve; any uncertainty sends the proposal to manual review." : "Manual is the default. The proposal is stored as PENDING, and an authorised operator must approve it before canonical rows are created."}>
              <option value="MANUAL">Manual operations review (default)</option>
              <option value="AUTOMATED">Automated source — policy evaluated</option>
            </TextField>

            {mode === "AUTOMATED" ? <Paper variant="outlined" sx={{ p: 2, bgcolor: "#f8fbff" }}>
              <Stack spacing={2}>
                <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Source and idempotency facts</Typography>
                <Typography variant="body2" color="text.secondary">These fields explain who supplied the record and let a retry return the same proposal instead of creating a duplicate.</Typography>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <TextField label="Source system" value="Bank A static data production" disabled fullWidth helperText="Configured source system: BANK_A_STATIC_PROD." />
                  <TextField label="Source namespace" value="BANK_A_STATIC_PROD" disabled fullWidth helperText="Namespace in which the external code is meaningful." />
                  <TextField label="Source object type" value="INSTRUMENT" disabled fullWidth helperText="This screen creates an economic instrument. Venue-specific mappings belong to the separate listing workflow." />
                </Stack>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <TextField label="Source external ID" value={sourceExternalId} onChange={(event) => setSourceExternalId(event.target.value)} required placeholder="Example: BANK-ACME-XLON" fullWidth helperText="The bank/provider code to map to the new internal UUID." />
                  <TextField label="Source payload ID" value={sourcePayloadId} onChange={(event) => setSourcePayloadId(event.target.value)} fullWidth helperText="Optional UUID of the retained inbound payload/message." />
                </Stack>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <TextField label="Automation policy" value="BANK_A_EQUITY_CREATE" disabled fullWidth helperText="Policy requires ISIN + FIGI, an issuer, and confidence ≥ 0.95. Venue listings are proposed separately." />
                  <TextField label="Confidence score" value={confidence} onChange={(event) => setConfidence(event.target.value)} type="number" required slotProps={{ htmlInput: { min: 0, max: 1, step: 0.01 } }} fullWidth helperText="Normalized source confidence from 0 to 1. Example: 0.99." />
                  <TextField label="Idempotency key" value={idempotencyKey} onChange={(event) => setIdempotencyKey(event.target.value)} required placeholder="Example: bank-a-file-2026-09-02-row-17" fullWidth helperText="Stable source event key. Retrying the same key returns the original proposal." />
                </Stack>
              </Stack>
            </Paper> : <Paper variant="outlined" sx={{ p: 2, bgcolor: "#fffdf8" }}><Typography variant="subtitle2" sx={{ fontWeight: 800 }}>What happens next?</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.45 }}>The system stores your submitted facts as a pending proposal. Operations can inspect the identifiers, source evidence, and duplicate checks before approving or rejecting it. Until approval, there is no tradable instrument or listing in the canonical master.</Typography></Paper>}

            <Stack direction="row" spacing={1.5} sx={{ justifyContent: "space-between", alignItems: "center" }}>
              <Button component={Link} href="/" variant="text">Cancel</Button>
              <Button type="submit" variant="contained" disabled={submitting}>{submitting ? "Submitting…" : mode === "MANUAL" ? "Submit instrument for review" : "Evaluate source proposal"}</Button>
            </Stack>
          </Stack>
        </Card>
      </Box>
    </Box></WorkspaceShell>
  );
}
