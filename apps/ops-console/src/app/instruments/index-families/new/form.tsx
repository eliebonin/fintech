"use client";

import { FormEvent, useRef, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Card,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import {
  OrganisationOption,
  submitIndexFamilyProposalFromBff,
  createIdempotencyKey,
} from "@/lib/browser-api-client";
import { validateIndexFamily } from "./validation";

type Props = {
  organisations: OrganisationOption[];
  error: string | null;
};

export default function NewIndexFamilyForm({ organisations, error }: Props) {
  const [canonicalName, setCanonicalName] = useState("");
  const [internalCode, setInternalCode] = useState("");
  const [providerOrganisationId, setProviderOrganisationId] = useState("");
  const [message, setMessage] = useState<{ severity: "success" | "error"; text: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const idempotencyKey = useRef<string | undefined>(undefined);
  const floatedLabel = { inputLabel: { shrink: true } } as const;
  const nativeSelect = { ...floatedLabel, select: { native: true } } as const;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors = validateIndexFamily(canonicalName, internalCode);
    if (errors.canonicalName) {
      setMessage({ severity: "error", text: errors.canonicalName });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    try {
      const response = await submitIndexFamilyProposalFromBff({
        canonicalName: canonicalName.trim(),
        internalCode: internalCode.trim() || undefined,
        providerOrganisationId: providerOrganisationId || undefined,
        submissionMode: "MANUAL",
      }, idempotencyKey.current ?? (idempotencyKey.current = createIdempotencyKey()));
      setMessage({ severity: "success", text: `${response.data.status} · ${response.data.familyName}. Proposal ${response.data.proposalId} is queued for Operations review.` });
    } catch (submissionError) {
      setMessage({ severity: "error", text: submissionError instanceof Error ? submissionError.message : "Index-family proposal could not be submitted" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Alert severity="info" sx={{ mb: 2.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Manual submission is the default</Typography>
        <Typography variant="body2" sx={{ mt: 0.35 }}>
          A family is a non-tradable conceptual reference node. This proposal does not create a price series or a tradeable instrument; Operations approves it before it can be selected by concrete index variants.
        </Typography>
      </Alert>
      {error && <Alert severity="warning" sx={{ mb: 2 }}>{error} The provider organisation can be enriched later.</Alert>}
      {message && <Alert severity={message.severity} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Card component="form" onSubmit={submit} sx={{ p: { xs: 2, md: 3 } }}>
        <Stack spacing={3}>
          <Box>
            <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>1 · FAMILY IDENTITY</Typography>
            <Typography variant="h6">What lineage does this family represent?</Typography>
            <Typography variant="body2" color="text.secondary">
              Use the provider’s conceptual index name, such as S&amp;P 500 or EURO STOXX 50. Return variants are not separate families.
            </Typography>
          </Box>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField label="Canonical family name" value={canonicalName} onChange={(event) => setCanonicalName(event.target.value)} required fullWidth slotProps={floatedLabel} helperText="Required. Stable descriptive identity for the conceptual index lineage." />
            <TextField label="Internal code (optional)" value={internalCode} onChange={(event) => setInternalCode(event.target.value)} fullWidth slotProps={floatedLabel} helperText="Optional operational code; unique when supplied, but not the UUID identity." />
          </Stack>

          <Box>
            <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>2 · GOVERNANCE</Typography>
            <Typography variant="h6">Who publishes or administers it?</Typography>
            <Typography variant="body2" color="text.secondary">
              Optional provider reference. Choose an existing organisation; creating an organisation is a separate governed workflow.
            </Typography>
          </Box>
          <TextField select label="Provider / administrator organisation (optional)" value={providerOrganisationId} onChange={(event) => setProviderOrganisationId(event.target.value)} fullWidth slotProps={nativeSelect} helperText={organisations.length ? "The organisation responsible for publishing or administering the family." : "No active organisations are available; leave blank or enrich later."}>
            <option value="">— Not specified —</option>
            {organisations.map((item) => <option key={item.organisationId} value={item.organisationId}>{item.displayName}{item.legalName ? ` · ${item.legalName}` : ""}</option>)}
          </TextField>

          <Alert severity="info">
            After approval, return to <Link href="/instruments/indices/new">Add an index</Link> and select this family. A concrete index variant still needs its own return profile and currency semantics.
          </Alert>
          <Stack direction="row" spacing={1.5} sx={{ justifyContent: "space-between", alignItems: "center" }}>
            <Button component={Link} href="/instruments/indices/new" variant="text">Back to add index</Button>
            <Button type="submit" variant="contained" disabled={submitting}>{submitting ? "Submitting…" : "Submit family for review"}</Button>
          </Stack>
        </Stack>
      </Card>
    </>
  );
}
