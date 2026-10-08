"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Alert, Box, Button, Card, Divider, FormControlLabel, Paper, Stack, Switch, TextField, Typography } from "@mui/material";

import { WorkspaceShell } from "@/components/workspace-shell";
import {
  CurrencyGroup,
  DayCountConvention,
  listCurrenciesFromBff,
  listDayCountConventionsFromBff,
  listOrganisationsFromBff,
  OrganisationOption,
  submitBondProposalFromBff,
  createIdempotencyKey,
} from "@/lib/browser-api-client";
import { validateBondIdentity } from "./validation";

const COUPON_TYPES = [
  { value: "FIXED", label: "Fixed-rate", description: "A stated coupon rate paid on a regular schedule." },
  { value: "ZERO", label: "Zero-coupon", description: "No periodic coupon; value is redeemed at maturity." },
  { value: "FLOATING", label: "Floating-rate", description: "Coupon resets against a reference index plus/minus a spread." },
] as const;

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function NewBondPage() {
  const [canonicalName, setCanonicalName] = useState("");
  const [internalCode, setInternalCode] = useState("");
  const [couponType, setCouponType] = useState("");
  const [issuerOrganisationId, setIssuerOrganisationId] = useState("");
  const [baseCurrencyId, setBaseCurrencyId] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState(today());
  const [issueDate, setIssueDate] = useState("");
  const [maturityDate, setMaturityDate] = useState("");
  const [parAmount, setParAmount] = useState("");
  const [redemptionAmountPerPar, setRedemptionAmountPerPar] = useState("");
  const [isin, setIsin] = useState("");
  const [figi, setFigi] = useState("");
  const [couponRate, setCouponRate] = useState("");
  const [couponFrequency, setCouponFrequency] = useState("");
  const [dayCountConvention, setDayCountConvention] = useState("");
  const [dayCountConventions, setDayCountConventions] = useState<DayCountConvention[]>([]);
  const [dayCountError, setDayCountError] = useState<string | null>(null);
  const [currencyGroups, setCurrencyGroups] = useState<CurrencyGroup[]>([]);
  const [includeCrypto, setIncludeCrypto] = useState(false);
  const [currencyState, setCurrencyState] = useState<"loading" | "ready" | "error">("loading");
  const [organisations, setOrganisations] = useState<OrganisationOption[]>([]);
  const [organisationState, setOrganisationState] = useState<"loading" | "ready" | "error">("loading");
  const [floatingReferenceIndex, setFloatingReferenceIndex] = useState("");
  const [message, setMessage] = useState<{ severity: "success" | "error" | "info"; text: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const idempotencyKey = useRef<string | undefined>(undefined);
  const floatedLabel = { inputLabel: { shrink: true } } as const;
  // Native selects are deliberately used for onboarding catalogues. They keep
   // the options in the browser's form control and avoid a portal-dependent
   // menu that is unreliable in constrained/embedded browser surfaces.
   const nativeSelect = { ...floatedLabel, select: { native: true } } as const;
   const identityColumn = { flex: 1, minWidth: 0 } as const;

  useEffect(() => {
    let mounted = true;
    Promise.allSettled([
      listDayCountConventionsFromBff(),
      listOrganisationsFromBff(),
    ]).then(([dayCountResult, organisationResult]) => {
      if (!mounted) return;

      if (dayCountResult.status === "fulfilled") {
        setDayCountConventions(dayCountResult.value.data);
      } else {
        setDayCountError(dayCountResult.reason instanceof Error ? dayCountResult.reason.message : "Could not load day-count conventions");
      }

      if (organisationResult.status === "fulfilled") {
        setOrganisations(organisationResult.value.data);
        setOrganisationState("ready");
      } else {
        setOrganisationState("error");
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    setCurrencyState("loading");
    const groups = includeCrypto ? ["REGULAR", "CRYPTO"] as const : ["REGULAR"] as const;
    listCurrenciesFromBff(fetch, [...groups]).then((result) => {
      if (!mounted) return;
      setCurrencyGroups(result.data);
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
    const errors = validateBondIdentity(canonicalName, couponType);
    if (errors.canonicalName || errors.couponType) {
      setMessage({ severity: "error", text: errors.canonicalName ?? errors.couponType ?? "Complete the required fields." });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    try {
      const payload: Record<string, unknown> = {
        canonicalName,
        internalCode: internalCode || undefined,
        issuerOrganisationId: issuerOrganisationId || undefined,
        baseCurrencyId: baseCurrencyId || undefined,
        effectiveFrom,
        issueDate: issueDate || undefined,
        maturityDate: maturityDate || undefined,
        parAmount: parAmount || undefined,
        redemptionAmountPerPar: redemptionAmountPerPar || undefined,
        isin: isin || undefined,
        figi: figi || undefined,
        couponType,
        couponRate: couponRate || undefined,
        couponFrequencyPerYear: couponFrequency || undefined,
        dayCountConvention: dayCountConvention || undefined,
        floatingReferenceIndex: floatingReferenceIndex || undefined,
        submissionMode: "MANUAL",
      };
      const response = await submitBondProposalFromBff(payload, idempotencyKey.current ?? (idempotencyKey.current = createIdempotencyKey()));
      setMessage({ severity: "info", text: `${response.data.status} · ${response.data.enrichmentStatus}. Proposal ${response.data.proposalId} is queued for Operations review.` });
    } catch (error) {
      setMessage({ severity: "error", text: error instanceof Error ? error.message : "Bond proposal could not be submitted" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <WorkspaceShell><Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
      <Box sx={{ maxWidth: 980, mx: "auto" }}>
        <Typography variant="caption" color="text.secondary"><Link href="/">WORKSPACE / INSTRUMENTS</Link></Typography>
        <Typography variant="h4" sx={{ mt: 1 }}>Add a bond</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2.5 }}>Capture the economic bond first. Detailed terms can be enriched from a provider before approval.</Typography>
        <Alert severity="info" sx={{ mb: 2.5 }}><Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Only two decisions are required here</Typography><Typography variant="body2" sx={{ mt: 0.35 }}>Enter a canonical name and choose fixed-rate, zero-coupon, or floating-rate. Issue dates, coupon details, identifiers, and issuer facts are optional at submission.</Typography></Alert>
        {message && <Alert severity={message.severity} sx={{ mb: 2 }}>{message.text}</Alert>}

        <Card component="form" onSubmit={submit} sx={{ p: { xs: 2, md: 3 } }}>
          <Stack spacing={3}>
            <Box><Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>1 · ECONOMIC IDENTITY</Typography><Typography variant="h6">What is the bond?</Typography><Typography variant="body2" color="text.secondary">These fields identify the economic debt security, not a venue listing.</Typography></Box>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField label="Canonical name" value={canonicalName} onChange={(event) => setCanonicalName(event.target.value)} required fullWidth helperText="Official security name from the prospectus or provider." />
              <TextField label="Internal code (optional)" value={internalCode} onChange={(event) => setInternalCode(event.target.value)} fullWidth helperText="Stable internal display code; the UUID remains the identity." />
             </Stack>
             <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <Box sx={identityColumn}>
                <TextField
                  select
                  label="Issuer organisation (optional)"
                  value={issuerOrganisationId}
                  onChange={(event) => setIssuerOrganisationId(event.target.value)}
                  fullWidth
                  slotProps={nativeSelect}
                  disabled={organisationState === "loading"}
                  helperText={organisationState === "loading"
                    ? "Loading active organisations…"
                    : organisationState === "error"
                      ? "Organisation catalogue unavailable; leave blank and enrich before approval."
                      : "Select the legal issuer organisation; leave blank when provider enrichment will resolve it."}
                >
                  <option value="">— Not specified —</option>
                  {organisations.map((item) => (
                    <option key={item.organisationId} value={item.organisationId}>
                      {item.displayName}{item.legalName ? ` · ${item.legalName}` : ""}
                    </option>
                  ))}
                </TextField>
              </Box>
              <Box sx={identityColumn}>
                <TextField
                  select
                  label="Base / denomination currency (optional)"
                  value={baseCurrencyId}
                  onChange={(event) => setBaseCurrencyId(event.target.value)}
                  fullWidth
                  slotProps={nativeSelect}
                  disabled={currencyState === "loading"}
                  helperText={currencyState === "loading"
                    ? "Loading active currencies…"
                    : currencyState === "error"
                      ? "Currency catalogue unavailable; leave blank and enrich before approval."
                      : "Currency of principal and coupon payments, if known."}
                >
                  <option value="">— Not specified —</option>
                  {currencyGroups.map((group) => (
                    <optgroup key={group.groupCode} label={group.label}>
                      {group.items.map((item) => (
                        <option key={item.currencyId} value={item.currencyId}>
                          {item.currencyCode} · {item.displayName}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </TextField>
                <FormControlLabel
                  sx={{ ml: 0, mt: 0.25 }}
                  control={<Switch size="small" checked={includeCrypto} onChange={(event) => {
                    const next = event.target.checked;
                    setIncludeCrypto(next);
                    if (!next && currencyGroups.find((group) => group.groupCode === "CRYPTO")?.items.some((item) => item.currencyId === baseCurrencyId)) {
                      setBaseCurrencyId("");
                    }
                  }} />}
                  label={<Typography variant="caption">Include cryptoassets</Typography>}
                />
              </Box>
              <Box sx={identityColumn}>
                <TextField label="Effective from" type="date" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} required fullWidth slotProps={{ inputLabel: { shrink: true } }} />
              </Box>
            </Stack>
            <Divider />
            <Box><Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>2 · COUPON STRUCTURE</Typography><Typography variant="h6">What kind of bond is it?</Typography><Typography variant="body2" color="text.secondary">This is the one required bond-specific choice. It guides provider enrichment and validation.</Typography></Box>
            <TextField select label="Coupon structure" value={couponType} onChange={(event) => setCouponType(event.target.value)} required fullWidth slotProps={nativeSelect} helperText={COUPON_TYPES.find((item) => item.value === couponType)?.description ?? "Choose the closest contractual coupon structure."}>
              <option value="">— Choose a coupon structure —</option>
              {COUPON_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </TextField>
            <Divider />
            <Box><Typography variant="overline" color="text.secondary" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>3 · OPTIONAL KNOWN FACTS</Typography><Typography variant="h6">Add what you know</Typography><Typography variant="body2" color="text.secondary">Every field below may be left blank. A provider or Operations steward can complete the record later.</Typography></Box>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField label="ISIN (optional)" value={isin} onChange={(event) => setIsin(event.target.value)} fullWidth />
              <TextField label="FIGI (optional)" value={figi} onChange={(event) => setFigi(event.target.value)} fullWidth />
              <TextField label="Issue date (optional)" type="date" value={issueDate} onChange={(event) => setIssueDate(event.target.value)} fullWidth slotProps={{ inputLabel: { shrink: true } }} />
              <TextField label="Maturity date (optional)" type="date" value={maturityDate} onChange={(event) => setMaturityDate(event.target.value)} fullWidth slotProps={{ inputLabel: { shrink: true } }} />
            </Stack>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField label="Coupon rate (optional)" value={couponRate} onChange={(event) => setCouponRate(event.target.value)} type="number" fullWidth helperText="Decimal form, e.g. 0.04 means 4%." />
              <TextField label="Payments per year (optional)" value={couponFrequency} onChange={(event) => setCouponFrequency(event.target.value)} type="number" fullWidth />
              <TextField
                select
                label="Day-count convention (optional)"
                value={dayCountConvention}
                onChange={(event) => setDayCountConvention(event.target.value)}
                fullWidth
                slotProps={nativeSelect}
                helperText={dayCountError ? `Catalogue unavailable: ${dayCountError}` : "Select a governed accrual convention, or leave unspecified for provider enrichment."}
              >
                <option value="">— Not specified —</option>
                {dayCountConventions.map((item) => <option key={item.code} value={item.code}>{item.displayName} ({item.code})</option>)}
              </TextField>
              {couponType === "FLOATING" ? <TextField label="Floating reference index (optional)" value={floatingReferenceIndex} onChange={(event) => setFloatingReferenceIndex(event.target.value)} fullWidth placeholder="SONIA, SOFR, EURIBOR…" /> : <Box sx={{ flex: 1 }} />}
            </Stack>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField label="Par amount (optional)" value={parAmount} onChange={(event) => setParAmount(event.target.value)} type="number" fullWidth slotProps={{ htmlInput: { min: "0.00000001", step: "any" } }} helperText="Sourced face amount of one bond. Required for plain-bond booking; leave blank for provider enrichment." />
              <TextField label="Redemption per 100 par (optional)" value={redemptionAmountPerPar} onChange={(event) => setRedemptionAmountPerPar(event.target.value)} type="number" fullWidth slotProps={{ htmlInput: { min: "0.00000001", step: "any" } }} helperText="Enter the contractual redemption quote: 100 means repayment at par. Plain-bond booking supports unadjusted redemption at par only; do not infer this value." />
            </Stack>
            <Stack direction="row" spacing={1.5} sx={{ justifyContent: "space-between", alignItems: "center" }}>
              <Button component={Link} href="/" variant="text">Cancel</Button>
              <Button type="submit" variant="contained" disabled={submitting}>{submitting ? "Submitting…" : "Submit bond for review"}</Button>
            </Stack>
          </Stack>
        </Card>
      </Box>
    </Box></WorkspaceShell>
  );
}
