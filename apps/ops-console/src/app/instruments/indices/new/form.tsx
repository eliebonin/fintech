"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Card,
  Checkbox,
  Divider,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import {
  CurrencyGroup,
  IndexFamilyOption,
  IndexKind,
  OrganisationOption,
  ReturnProfile,
  listCurrenciesFromBff,
  submitIndexProposalFromBff,
  createIdempotencyKey,
} from "@/lib/browser-api-client";
import { validateIndexIdentity } from "./validation";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function optional(value: string): string | undefined {
  return value.trim() || undefined;
}

type Props = {
  currencies: CurrencyGroup[];
  returnProfiles: ReturnProfile[];
  organisations: OrganisationOption[];
  indexFamilies: IndexFamilyOption[];
  indexKinds: IndexKind[];
  error: string | null;
};

export default function NewIndexForm({ currencies, returnProfiles, organisations, indexFamilies, indexKinds, error }: Props) {
  const [canonicalName, setCanonicalName] = useState("");
  const [internalCode, setInternalCode] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState(today());
  const [indexKind, setIndexKind] = useState("");
  const [indexFamilyId, setIndexFamilyId] = useState("");
  const [returnProfileId, setReturnProfileId] = useState("");
  const [baseCurrencyId, setBaseCurrencyId] = useState("");
  const [currencyGroups, setCurrencyGroups] = useState<CurrencyGroup[]>(currencies);
  const [includeCrypto, setIncludeCrypto] = useState(false);
  const [currencyState, setCurrencyState] = useState<"ready" | "loading" | "error">(currencies.length ? "ready" : "error");
  const [administratorOrganisationId, setAdministratorOrganisationId] = useState("");
  const [calculationAgentOrganisationId, setCalculationAgentOrganisationId] = useState("");
  const [baseDate, setBaseDate] = useState("");
  const [baseLevel, setBaseLevel] = useState("");
  const [weightingMethod, setWeightingMethod] = useState("");
  const [rebalanceFrequency, setRebalanceFrequency] = useState("");
  const [calculationFrequency, setCalculationFrequency] = useState("");
  const [dividendTreatment, setDividendTreatment] = useState("");
  const [launchDate, setLaunchDate] = useState("");
  const [methodologyReference, setMethodologyReference] = useState("");
  const [methodologyDocumentUri, setMethodologyDocumentUri] = useState("");
  const [isBacktestedHistory, setIsBacktestedHistory] = useState(false);
  const [message, setMessage] = useState<{ severity: "success" | "error" | "info"; text: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const idempotencyKey = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!includeCrypto) {
      setCurrencyGroups(currencies);
      setCurrencyState(currencies.length ? "ready" : "error");
      return;
    }
    let mounted = true;
    setCurrencyState("loading");
    listCurrenciesFromBff(fetch, ["REGULAR", "CRYPTO"]).then((result) => {
      if (!mounted) return;
      setCurrencyGroups(result.data);
      setCurrencyState("ready");
    }).catch(() => {
      if (mounted) setCurrencyState("error");
    });
    return () => {
      mounted = false;
    };
  }, [currencies, includeCrypto]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors = validateIndexIdentity(canonicalName, indexKind);
    if (errors.canonicalName || errors.indexKind) {
      setMessage({ severity: "error", text: errors.canonicalName ?? errors.indexKind ?? "Complete the required fields." });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    try {
      const response = await submitIndexProposalFromBff({
        canonicalName: canonicalName.trim(),
        internalCode: optional(internalCode),
        effectiveFrom,
        indexKind,
        indexFamilyId: optional(indexFamilyId),
        returnProfileId: optional(returnProfileId),
        baseCurrencyId: optional(baseCurrencyId),
        administratorOrganisationId: optional(administratorOrganisationId),
        calculationAgentOrganisationId: optional(calculationAgentOrganisationId),
        baseDate: optional(baseDate),
        baseLevel: optional(baseLevel),
        weightingMethod: optional(weightingMethod),
        rebalanceFrequency: optional(rebalanceFrequency),
        calculationFrequency: optional(calculationFrequency),
        dividendTreatment: optional(dividendTreatment),
        launchDate: optional(launchDate),
        methodologyReference: optional(methodologyReference),
        methodologyDocumentUri: optional(methodologyDocumentUri),
        isBacktestedHistory,
        submissionMode: "MANUAL",
      }, idempotencyKey.current ?? (idempotencyKey.current = createIdempotencyKey()));
      setMessage({ severity: "success", text: `${response.data.status} · ${response.data.indexKind}. Proposal ${response.data.proposalId} is queued for Operations review.` });
    } catch (submissionError) {
      setMessage({ severity: "error", text: submissionError instanceof Error ? submissionError.message : "Index proposal could not be submitted" });
    } finally {
      setSubmitting(false);
    }
  }

  const selectedKind = indexKinds.find((item) => item.indexKindCode === indexKind);
  const kindDescription = selectedKind?.description ?? "Choose the closest governed category; dissemination and methodology ownership are separate concepts.";
  const returnDescription = returnProfiles.find((item) => item.returnProfileId === returnProfileId)?.description ?? "Choose price return, total return, net/gross total return, excess return, or dividend points when known.";
  const floatedLabel = { inputLabel: { shrink: true } } as const;
  // Native selects keep the placeholder option visible when no value is chosen.
  // Force the MUI label to its floated position so it cannot render on top of
  // that option text (especially for the optional catalogue fields).
  const nativeSelect = { ...floatedLabel, select: { native: true } } as const;

  return (
    <>
      <Alert severity="info" sx={{ mb: 2.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Manual submission is the default</Typography>
        <Typography variant="body2" sx={{ mt: 0.35 }}>This page creates a pending proposal only. Operations approves the canonical record; provider enrichment and constituent snapshots can be added afterwards.</Typography>
      </Alert>
      {error && <Alert severity="warning" sx={{ mb: 2 }}>{error} Some optional catalogue values may need to be enriched later.</Alert>}
      {message && <Alert severity={message.severity} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Card component="form" onSubmit={submit} sx={{ p: { xs: 2, md: 3 } }}>
        <Stack spacing={3}>
          <Box><Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>1 · ECONOMIC IDENTITY</Typography><Typography variant="h6">What is the index?</Typography><Typography variant="body2" color="text.secondary">These fields describe the economic index node, not a listing or market-data series. Include the return variant in the canonical name when it is known.</Typography></Box>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField label="Canonical name" value={canonicalName} onChange={(event) => setCanonicalName(event.target.value)} required fullWidth slotProps={floatedLabel} helperText="Required. Use the official name of the concrete variant, e.g. S&P 500 Net Total Return USD. This is descriptive identity data and should not be reused for another index." />
            <TextField label="Internal code (optional)" value={internalCode} onChange={(event) => setInternalCode(event.target.value)} fullWidth slotProps={floatedLabel} helperText="Optional stable code for operations and integrations. It is not the UUID identity and must be unique when supplied." />
          </Stack>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField label="Effective from" type="date" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} required fullWidth slotProps={{ inputLabel: { shrink: true } }} helperText="Date from which this canonical definition is effective." />
            <TextField select label="Index kind" value={indexKind} onChange={(event) => setIndexKind(event.target.value)} required fullWidth slotProps={nativeSelect} helperText={kindDescription}>
              <option value="">— Choose an index kind —</option>
              {indexKinds.map((item) => <option key={item.indexKindCode} value={item.indexKindCode}>{item.displayName}</option>)}
            </TextField>
            <TextField select label="Index family (optional)" value={indexFamilyId} onChange={(event) => setIndexFamilyId(event.target.value)} fullWidth slotProps={nativeSelect} helperText={indexFamilies.length ? "Select an existing DB-backed family. Families are separate governed records; ask Operations to create a missing family first." : "No active family is available; leave blank or ask Operations to create one separately."}>
              <option value="">— No family selected —</option>
              {indexFamilies.map((item) => <option key={item.indexFamilyId} value={item.indexFamilyId}>{item.familyName}{item.providerOrganisationName ? ` · ${item.providerOrganisationName}` : ""}</option>)}
            </TextField>
          </Stack>
          <Box sx={{ mt: -2 }}>
            <Button component={Link} href="/instruments/index-families/new" size="small" variant="text">Create a new index family</Button>
          </Box>
          {selectedKind && (
            <Box sx={{ mt: -1, p: 1.75, border: "1px solid", borderColor: "divider", borderRadius: 1.5, bgcolor: "#f8fafc" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>{selectedKind.displayName}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>{selectedKind.description}</Typography>
              <Stack direction={{ xs: "column", md: "row" }} spacing={{ xs: 0.4, md: 2 }} sx={{ mt: 1 }}>
                <Typography variant="caption"><strong>Dissemination:</strong> {selectedKind.disseminationClass}</Typography>
                <Typography variant="caption"><strong>Methodology ownership:</strong> {selectedKind.methodologyOwnership}</Typography>
              </Stack>
              {selectedKind.exampleText && <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.75 }}><strong>Example:</strong> {selectedKind.exampleText}</Typography>}
            </Box>
          )}

          <Divider />
          <Box><Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>2 · RETURN AND CURRENCY SEMANTICS</Typography><Typography variant="h6">What does the index measure?</Typography><Typography variant="body2" color="text.secondary">Return profiles are governed catalogue values, not mutable labels on observations. Leave a field blank only when the source or Operations steward will enrich it later.</Typography></Box>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField select label="Return profile (optional)" value={returnProfileId} onChange={(event) => setReturnProfileId(event.target.value)} fullWidth slotProps={nativeSelect} helperText={returnDescription}>
              <option value="">— Not specified —</option>
              {returnProfiles.map((item) => <option key={item.returnProfileId} value={item.returnProfileId}>{item.displayName} ({item.profileCode})</option>)}
            </TextField>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <TextField select label="Base currency (optional)" value={baseCurrencyId} onChange={(event) => setBaseCurrencyId(event.target.value)} fullWidth disabled={currencyState === "loading"} slotProps={nativeSelect} helperText={currencyState === "loading" ? "Loading active currencies…" : currencyState === "error" ? "Currency catalogue unavailable; leave blank and enrich before approval." : "Currency in which the index level or published index value is expressed."}>
                <option value="">— Not specified —</option>
                {currencyGroups.map((group) => <optgroup key={group.groupCode} label={group.label}>{group.items.map((item) => <option key={item.currencyId} value={item.currencyId}>{item.currencyCode} · {item.displayName}</option>)}</optgroup>)}
              </TextField>
              <FormControlLabel
                sx={{ ml: 0, mt: 0.25 }}
                control={<Switch size="small" checked={includeCrypto} onChange={(event) => {
                  const next = event.target.checked;
                  setIncludeCrypto(next);
                  if (!next && currencyGroups.find((group) => group.groupCode === "CRYPTO")?.items.some((item) => item.currencyId === baseCurrencyId)) setBaseCurrencyId("");
                }} />}
                label={<Typography variant="caption">Include cryptoassets</Typography>}
              />
            </Box>
          </Stack>

          <Divider />
          <Box><Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>3 · ADMINISTRATION</Typography><Typography variant="h6">Who maintains the methodology?</Typography><Typography variant="body2" color="text.secondary">These are organisation references, not issuers of a security. They can be completed from the organisation catalogue or enriched later.</Typography></Box>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField select label="Index administrator (optional)" value={administratorOrganisationId} onChange={(event) => setAdministratorOrganisationId(event.target.value)} fullWidth slotProps={nativeSelect} helperText="Organisation responsible for index administration or publication."><option value="">— Not specified —</option>{organisations.map((item) => <option key={item.organisationId} value={item.organisationId}>{item.displayName}{item.legalName ? ` · ${item.legalName}` : ""}</option>)}</TextField>
            <TextField select label="Calculation agent (optional)" value={calculationAgentOrganisationId} onChange={(event) => setCalculationAgentOrganisationId(event.target.value)} fullWidth slotProps={nativeSelect} helperText="Organisation responsible for calculation, fixing, or publication where different."><option value="">— Not specified —</option>{organisations.map((item) => <option key={item.organisationId} value={item.organisationId}>{item.displayName}{item.legalName ? ` · ${item.legalName}` : ""}</option>)}</TextField>
          </Stack>

          <Divider />
          <Box><Typography variant="overline" color="text.secondary" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>4 · KNOWN METHODOLOGY FACTS</Typography><Typography variant="h6">Add what is already known</Typography><Typography variant="body2" color="text.secondary">All fields are optional. The methodology version is effective-dated so later corrections or changes do not rewrite history.</Typography></Box>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}><TextField label="Base date (optional)" type="date" value={baseDate} onChange={(event) => setBaseDate(event.target.value)} fullWidth slotProps={floatedLabel} /><TextField label="Base level (optional)" value={baseLevel} onChange={(event) => setBaseLevel(event.target.value)} type="number" fullWidth slotProps={{ ...floatedLabel, htmlInput: { step: "any" } }} helperText="Published level at the base date, if the methodology states one." /><TextField label="Launch date (optional)" type="date" value={launchDate} onChange={(event) => setLaunchDate(event.target.value)} fullWidth slotProps={floatedLabel} /></Stack>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}><TextField label="Weighting method (optional)" value={weightingMethod} onChange={(event) => setWeightingMethod(event.target.value)} fullWidth slotProps={floatedLabel} placeholder="Free float market cap, equal weight…" /><TextField label="Rebalance frequency (optional)" value={rebalanceFrequency} onChange={(event) => setRebalanceFrequency(event.target.value)} fullWidth slotProps={floatedLabel} placeholder="Monthly, quarterly…" /><TextField label="Calculation frequency (optional)" value={calculationFrequency} onChange={(event) => setCalculationFrequency(event.target.value)} fullWidth slotProps={floatedLabel} placeholder="Daily, intraday…" /></Stack>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}><TextField label="Dividend treatment (optional)" value={dividendTreatment} onChange={(event) => setDividendTreatment(event.target.value)} fullWidth slotProps={floatedLabel} placeholder="Reinvested, paid out, excess…" /><TextField label="Methodology reference (optional)" value={methodologyReference} onChange={(event) => setMethodologyReference(event.target.value)} fullWidth slotProps={floatedLabel} placeholder="Document or methodology version" /><TextField label="Methodology document URI (optional)" value={methodologyDocumentUri} onChange={(event) => setMethodologyDocumentUri(event.target.value)} fullWidth slotProps={floatedLabel} placeholder="https://… or internal document reference" /></Stack>
          <FormControlLabel control={<Checkbox checked={isBacktestedHistory} onChange={(event) => setIsBacktestedHistory(event.target.checked)} />} label="The supplied history may include backtested or simulated observations" />
          <Stack direction="row" spacing={1.5} sx={{ justifyContent: "space-between", alignItems: "center" }}><Button component={Link} href="/" variant="text">Cancel</Button><Button type="submit" variant="contained" disabled={submitting}>{submitting ? "Submitting…" : "Submit index for review"}</Button></Stack>
        </Stack>
      </Card>
    </>
  );
}
