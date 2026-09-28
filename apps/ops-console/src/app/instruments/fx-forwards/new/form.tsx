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
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import {
  CurrencyGroup,
  createIdempotencyKey,
  listCurrenciesFromBff,
  submitFxForwardProposalFromBff,
} from "@/lib/browser-api-client";
import { validateFxForwardIdentity } from "./validation";

type Props = {
  currencies: CurrencyGroup[];
  error: string | null;
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function optional(value: string): string | undefined {
  return value.trim() || undefined;
}

const floatedLabel = { inputLabel: { shrink: true } } as const;
const nativeSelect = { ...floatedLabel, select: { native: true } } as const;

export default function NewFxForwardForm({ currencies, error }: Props) {
  const [canonicalName, setCanonicalName] = useState("");
  const [internalCode, setInternalCode] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [baseCurrencyId, setBaseCurrencyId] = useState("");
  const [quoteCurrencyId, setQuoteCurrencyId] = useState("");
  const [quoteConvention, setQuoteConvention] = useState("");
  const [agreedForwardRate, setAgreedForwardRate] = useState("");
  const [settlementType, setSettlementType] = useState("DELIVERABLE");
  const [fixingCurrencyId, setFixingCurrencyId] = useState("");
  const [maturityDate, setMaturityDate] = useState("");
  const [settlementDate, setSettlementDate] = useState("");
  const [includeCrypto, setIncludeCrypto] = useState(false);
  const [currencyGroups, setCurrencyGroups] = useState<CurrencyGroup[]>(currencies);
  const [currencyState, setCurrencyState] = useState<"ready" | "loading" | "error">(currencies.length ? "ready" : "error");
  const [message, setMessage] = useState<{ severity: "success" | "error" | "info"; text: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const idempotencyKey = useRef<string | undefined>(undefined);

  useEffect(() => {
    setEffectiveFrom((current) => current || today());
  }, []);

  useEffect(() => {
    if (!includeCrypto) {
      setCurrencyGroups(currencies);
      setCurrencyState(currencies.length ? "ready" : "error");
      return;
    }
    let mounted = true;
    setCurrencyState("loading");
    listCurrenciesFromBff(fetch, ["REGULAR", "CRYPTO"])
      .then((result) => {
        if (!mounted) return;
        setCurrencyGroups(result.data);
        setCurrencyState("ready");
      })
      .catch(() => {
        if (mounted) setCurrencyState("error");
      });
    return () => {
      mounted = false;
    };
  }, [currencies, includeCrypto]);

  function clearCryptoSelection(nextIncludeCrypto: boolean) {
    setIncludeCrypto(nextIncludeCrypto);
    if (nextIncludeCrypto) return;
    const cryptoIds = new Set((currencyGroups.find((group) => group.groupCode === "CRYPTO")?.items ?? []).map((item) => item.currencyId));
    if (cryptoIds.has(baseCurrencyId)) setBaseCurrencyId("");
    if (cryptoIds.has(quoteCurrencyId)) setQuoteCurrencyId("");
    if (cryptoIds.has(fixingCurrencyId)) setFixingCurrencyId("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors = validateFxForwardIdentity(canonicalName, baseCurrencyId, quoteCurrencyId, quoteConvention, agreedForwardRate, maturityDate);
    const firstError = errors.canonicalName ?? errors.baseCurrencyId ?? errors.quoteCurrencyId ?? errors.quoteConvention ?? errors.agreedForwardRate ?? errors.maturityDate;
    if (firstError) {
      setMessage({ severity: "error", text: firstError });
      return;
    }
    if (settlementDate && settlementDate < maturityDate) {
      setMessage({ severity: "error", text: "Settlement date cannot precede maturity date." });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    try {
      const response = await submitFxForwardProposalFromBff({
        canonicalName: canonicalName.trim(),
        internalCode: optional(internalCode),
        effectiveFrom,
        baseCurrencyId,
        quoteCurrencyId,
        quoteConvention: quoteConvention.trim().toUpperCase(),
        agreedForwardRate,
        settlementType,
        fixingCurrencyId: optional(fixingCurrencyId),
        maturityDate,
        settlementDate: optional(settlementDate),
        submissionMode: "MANUAL",
      }, idempotencyKey.current ?? (idempotencyKey.current = createIdempotencyKey()));
      setMessage({ severity: "success", text: `${response.data.status} · ${response.data.quoteConvention}. Proposal ${response.data.proposalId} is queued for Operations review.` });
    } catch (submissionError) {
      setMessage({ severity: "error", text: submissionError instanceof Error ? submissionError.message : "FX-forward proposal could not be submitted" });
    } finally {
      setSubmitting(false);
    }
  }

  const currencyOptions = (currencyGroups.find((group) => group.groupCode === "REGULAR")?.items ?? []);
  const cryptoOptions = (currencyGroups.find((group) => group.groupCode === "CRYPTO")?.items ?? []);
  const options = includeCrypto ? [...currencyOptions, ...cryptoOptions] : currencyOptions;
  const currencyHelper = currencyState === "loading"
    ? "Loading active currencies…"
    : currencyState === "error"
      ? "Currency catalogue unavailable; refresh after restarting the reference API."
      : "For example, GBP in USD_PER_GBP. Currency roles come from the canonical DB catalogue.";

  return (
    <>
      <Alert severity="info" sx={{ mb: 2.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Manual submission is the default</Typography>
        <Typography variant="body2" sx={{ mt: 0.35 }}>This page creates a pending proposal. Operations approves the economic contract. Counterparty, strategy, notional, trade date, and trade-specific MTM belong to the trade/valuation workflows.</Typography>
      </Alert>
      {error && <Alert severity="warning" sx={{ mb: 2 }}>{error} Currency terms may need to be completed during review.</Alert>}
      {message && <Alert severity={message.severity} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Card component="form" noValidate onSubmit={submit} sx={{ p: { xs: 2, md: 3 } }}>
        <Stack spacing={3}>
          <Box>
            <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>1 · ECONOMIC IDENTITY</Typography>
            <Typography variant="h6">What contract is this?</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>One actual OTC forward receives one economic instrument UUID. It is not a rolling FX quote series and it does not need a venue listing.</Typography>
          </Box>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField label="Canonical name" value={canonicalName} onChange={(event) => setCanonicalName(event.target.value)} required fullWidth slotProps={floatedLabel} helperText="Official confirmation or operations name, e.g. GBP/USD 3M OTC forward. It can be amended through a versioned approval workflow; it is not the external identity." />
            <TextField label="Internal code (optional)" value={internalCode} onChange={(event) => setInternalCode(event.target.value)} fullWidth slotProps={floatedLabel} helperText="Stable platform-owned code, unique when supplied. Never use the counterparty's trade reference as the economic UUID." />
          </Stack>
          <TextField label="Effective from" type="date" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} required fullWidth slotProps={floatedLabel} helperText="First date this canonical contract definition is effective." />

          <Divider />
          <Box>
            <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>2 · CONTRACTUAL RATE</Typography>
            <Typography variant="h6">Which currency is delivered and how is the rate quoted?</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>Base and quote are directional. In USD_PER_GBP, the rate is USD for one GBP. Do not add a generic quantity-currency field: the base currency is the contract's economic currency.</Typography>
          </Box>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField select label="Base currency" value={baseCurrencyId} onChange={(event) => setBaseCurrencyId(event.target.value)} required fullWidth disabled={currencyState !== "ready"} slotProps={nativeSelect} helperText={currencyHelper}>
              <option value="">— Choose base currency —</option>
              {options.map((item) => <option key={`base-${item.currencyId}`} value={item.currencyId}>{item.currencyCode} · {item.displayName}</option>)}
            </TextField>
            <TextField select label="Quote currency" value={quoteCurrencyId} onChange={(event) => setQuoteCurrencyId(event.target.value)} required fullWidth disabled={currencyState !== "ready"} slotProps={nativeSelect} helperText={currencyHelper}>
              <option value="">— Choose quote currency —</option>
              {options.map((item) => <option key={`quote-${item.currencyId}`} value={item.currencyId}>{item.currencyCode} · {item.displayName}</option>)}
            </TextField>
          </Stack>
          <FormControlLabel sx={{ ml: 0, mt: -1 }} control={<Switch size="small" checked={includeCrypto} onChange={(event) => clearCryptoSelection(event.target.checked)} />} label={<Typography variant="caption">Include cryptoasset currencies for this pair</Typography>} />
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField label="Quote convention" value={quoteConvention} onChange={(event) => setQuoteConvention(event.target.value.toUpperCase())} required fullWidth slotProps={floatedLabel} placeholder="USD_PER_GBP" helperText="Uppercase convention, normally QUOTE_PER_BASE, e.g. USD_PER_GBP or EUR_PER_GBP." />
            <TextField label="Agreed forward rate" value={agreedForwardRate} onChange={(event) => setAgreedForwardRate(event.target.value)} required type="number" fullWidth slotProps={{ ...floatedLabel, htmlInput: { min: 0, step: "any" } }} helperText="Contractual rate in the quote convention. It is not a monetary MTM." />
            <TextField select label="Settlement type" value={settlementType} onChange={(event) => setSettlementType(event.target.value)} required fullWidth slotProps={nativeSelect} helperText="DELIVERABLE exchanges the two currencies; NDF/CASH settle a calculated amount.">
              <option value="DELIVERABLE">DELIVERABLE</option>
              <option value="NDF">NDF</option>
              <option value="CASH">CASH</option>
            </TextField>
          </Stack>
          <TextField select label="Fixing / settlement currency (optional)" value={fixingCurrencyId} onChange={(event) => setFixingCurrencyId(event.target.value)} fullWidth disabled={currencyState !== "ready"} slotProps={nativeSelect} helperText="Use for NDF or cash settlement when the calculation currency is known; otherwise leave blank.">
            <option value="">— Not specified —</option>
            {options.map((item) => <option key={`fixing-${item.currencyId}`} value={item.currencyId}>{item.currencyCode} · {item.displayName}</option>)}
          </TextField>

          <Divider />
          <Box>
            <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>3 · CONTRACT DATES</Typography>
            <Typography variant="h6">When does it mature and settle?</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>These dates are stored in the shared `instrument_dates` record so downstream services use one date vocabulary across instrument types.</Typography>
          </Box>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField label="Maturity date" type="date" value={maturityDate} onChange={(event) => setMaturityDate(event.target.value)} required fullWidth slotProps={floatedLabel} helperText="Contractual forward maturity / value date." />
            <TextField label="Settlement date (optional)" type="date" value={settlementDate} onChange={(event) => setSettlementDate(event.target.value)} fullWidth slotProps={floatedLabel} helperText="Leave blank when not yet known; use it when settlement is distinct from maturity." />
          </Stack>

          <Alert severity="info">Listings are not needed for an OTC forward. Add any counterparty trade, strategy allocation, notional, trade price, or monetary MTM later through the trade and valuation services.</Alert>
          <Stack direction="row" spacing={1.5} sx={{ justifyContent: "space-between", alignItems: "center" }}>
            <Button component={Link} href="/" variant="text">Cancel</Button>
            <Button type="submit" variant="contained" disabled={submitting || currencyState === "loading"}>{submitting ? "Submitting…" : "Submit FX forward for review"}</Button>
          </Stack>
        </Stack>
      </Card>
    </>
  );
}
