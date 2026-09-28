"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  Divider,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import {
  CryptoAssetProposalPayload,
  decideCryptoAssetProposalFromBff,
  createIdempotencyKey,
} from "@/lib/browser-api-client";

type Proposal = CryptoAssetProposalPayload["data"];

function Field({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.35 }}>{label}</Typography>
      <Typography variant="body2" sx={{ fontWeight: 700, wordBreak: "break-word" }}>{value || "Not specified"}</Typography>
    </Box>
  );
}

export default function CryptoAssetProposalReviewForm({ proposal }: { proposal: Proposal }) {
  const [current, setCurrent] = useState(proposal);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState<{ severity: "success" | "error" | "info"; text: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const idempotencyKey = useRef<string | undefined>(undefined);
  const floatedLabel = { inputLabel: { shrink: true } } as const;
  const pending = current.status === "PENDING";

  async function decide(decision: "APPROVED" | "REJECTED") {
    if (!reason.trim()) {
      setMessage({ severity: "error", text: "Enter a decision reason before continuing." });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    try {
      const response = await decideCryptoAssetProposalFromBff(current.proposalId, { decision, reason: reason.trim() }, idempotencyKey.current ?? (idempotencyKey.current = createIdempotencyKey()));
      setCurrent(response.data);
      setMessage({
        severity: decision === "APPROVED" ? "success" : "info",
        text: decision === "APPROVED"
          ? "Approved. The canonical DIGITAL_ASSET instrument and currency role have been created."
          : "Rejected. No canonical instrument or currency role was created.",
      });
    } catch (error) {
      setMessage({ severity: "error", text: error instanceof Error ? error.message : "The cryptoasset decision could not be saved." });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Alert severity="info" sx={{ mb: 2.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Approval creates both roles atomically</Typography>
        <Typography variant="body2" sx={{ mt: 0.35 }}>
          Approval creates one economic DIGITAL_ASSET instrument and one linked currency role. Listings and chain deployments remain separate follow-up records.
        </Typography>
      </Alert>
      {message && <Alert severity={message.severity} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Card sx={{ p: { xs: 2, md: 3 } }}>
        <Stack spacing={3}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}>
            <Box>
              <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>{current.proposalType}</Typography>
              <Typography variant="h5" sx={{ mt: 0.35 }}>{current.canonicalName}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.45 }}>Proposal {current.proposalId}</Typography>
            </Box>
            <Chip label={current.status} color={current.status === "APPROVED" ? "success" : current.status === "PENDING" ? "warning" : "default"} />
          </Stack>

          <Divider />
          <Box>
            <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>SUBMITTED ECONOMIC IDENTITY</Typography>
            <Typography variant="h6">What was requested?</Typography>
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2 }}>
            <Field label="Canonical name" value={current.canonicalName} />
            <Field label="Internal code" value={current.internalCode ?? ""} />
            <Field label="Effective from" value={current.effectiveFrom} />
            <Field label="Asset subtype" value={current.assetSubtype} />
            <Field label="Native symbol" value={current.nativeSymbol} />
            <Field label="Protocol / programme" value={current.protocolName ?? ""} />
            <Field label="Decimals" value={current.decimals == null ? "" : String(current.decimals)} />
            <Field label="Issuer organisation ID" value={current.issuerOrganisationId ?? ""} />
            <Field label="Submission mode" value={current.submissionMode} />
            <Field label="Proposed at" value={current.proposedAt} />
          </Box>

          <Paper variant="outlined" sx={{ p: 2, bgcolor: "#f7faff" }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Materialisation status</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.45 }}>
              {current.status === "APPROVED"
                ? `Instrument ${current.instrumentId ?? "created"}; currency role ${current.currencyCode ?? current.currencyId ?? "created"}.`
                : current.status === "REJECTED"
                  ? "The proposal was rejected and did not create canonical rows."
                  : "No canonical rows exist yet. Approval will create the instrument and its currency role in one transaction."}
            </Typography>
          </Paper>

          {pending && (
            <>
              <TextField
                label="Decision reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                required
                fullWidth
                multiline
                minRows={3}
                slotProps={floatedLabel}
                helperText="Record the evidence or operational rationale for this decision."
              />
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ justifyContent: "flex-end" }}>
                <Button variant="outlined" color="error" onClick={() => void decide("REJECTED")} disabled={submitting}>{submitting ? "Saving…" : "Reject proposal"}</Button>
                <Button variant="contained" onClick={() => void decide("APPROVED")} disabled={submitting}>{submitting ? "Saving…" : "Approve and create canonical roles"}</Button>
              </Stack>
            </>
          )}
          {!pending && <Button component={Link} href="/" variant="contained" sx={{ alignSelf: "flex-start" }}>Back to operations console</Button>}
        </Stack>
      </Card>
    </>
  );
}
