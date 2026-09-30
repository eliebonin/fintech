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
  createIdempotencyKey,
  decideReferenceDataProposalFromBff,
  ReferenceDataProposalPayload,
} from "@/lib/browser-api-client";

type Proposal = ReferenceDataProposalPayload["data"];

function displayValue(value: unknown): string {
  if (value == null || value === "") return "Not specified";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function Field({ label, value }: { label: string; value: unknown }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.35 }}>{label}</Typography>
      <Typography variant="body2" sx={{ fontWeight: 700, wordBreak: "break-word" }}>{displayValue(value)}</Typography>
    </Box>
  );
}

function proposalTitle(proposal: Proposal): string {
  const payload = proposal.proposedPayload;
  return displayValue(payload.canonicalName ?? payload.familyName ?? payload.nativeSymbol ?? payload.tradingSymbol ?? proposal.proposalType);
}

export default function ReferenceDataProposalReviewForm({ proposal }: { proposal: Proposal }) {
  const [current, setCurrent] = useState(proposal);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState<{ severity: "success" | "error" | "info"; text: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const idempotencyKey = useRef<string | undefined>(undefined);
  const pending = current.status === "PENDING";

  async function decide(decision: "APPROVED" | "REJECTED") {
    if (!reason.trim()) {
      setMessage({ severity: "error", text: "Enter a decision reason before continuing." });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    try {
      const key = idempotencyKey.current ?? (idempotencyKey.current = createIdempotencyKey());
      const response = await decideReferenceDataProposalFromBff(current.proposalId, { decision, reason: reason.trim() }, key);
      setCurrent(response.data);
      setMessage({
        severity: decision === "APPROVED" ? "success" : "info",
        text: decision === "APPROVED"
          ? "Approved. The owning workflow has materialised its canonical rows."
          : "Rejected. No canonical rows were created by this decision.",
      });
    } catch (error) {
      setMessage({ severity: "error", text: error instanceof Error ? error.message : "The proposal decision could not be saved." });
    } finally {
      setSubmitting(false);
    }
  }

  const payloadEntries = Object.entries(current.proposedPayload);
  return (
    <Card sx={{ p: { xs: 2, md: 3 } }}>
      <Stack spacing={3}>
        {message && <Alert severity={message.severity}>{message.text}</Alert>}
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}>
          <Box>
            <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>{current.proposalType}</Typography>
            <Typography variant="h5" sx={{ mt: 0.35 }}>{proposalTitle(current)}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.45 }}>Proposal {current.proposalId}</Typography>
          </Box>
          <Chip label={current.status} color={current.status === "APPROVED" ? "success" : current.status === "PENDING" ? "warning" : "default"} />
        </Stack>

        <Divider />
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ alignItems: { sm: "center" } }}>
          {["Submitted", "Pending review", current.status === "APPROVED" ? "Approved" : current.status === "REJECTED" ? "Rejected" : "Decision"].map((step, index) => <Stack key={step} direction="row" spacing={0.75} sx={{ alignItems: "center" }}><Chip label={`${index + 1} · ${step}`} size="small" color={index < 2 || !pending ? "primary" : "default"} variant={index < 2 || !pending ? "filled" : "outlined"} />{index < 2 && <Typography color="text.secondary" sx={{ display: { xs: "none", sm: "block" } }}>→</Typography>}</Stack>)}
        </Stack>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2 }}>
          <Field label="Proposal type" value={current.proposalType} />
          <Field label="Submission mode" value={current.submissionMode} />
          <Field label="Payload schema" value={current.payloadSchemaVersion} />
          <Field label="Match status" value={current.matchStatus} />
          <Field label="Confidence score" value={current.confidenceScore} />
          <Field label="Reference node" value={current.referenceNodeId} />
          <Field label="Proposed at" value={current.proposedAt} />
          <Field label="Decision" value={current.decision} />
          <Field label="Decided at" value={current.decidedAt} />
        </Box>

        <Box>
          <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.1em", fontWeight: 800 }}>SUBMITTED PAYLOAD</Typography>
          <Typography variant="h6">Proposed facts</Typography>
        </Box>
        <Paper component="pre" variant="outlined" sx={{ m: 0, p: 2, maxHeight: 360, overflow: "auto", bgcolor: "#f7faff", fontFamily: "monospace", fontSize: 12, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
          {JSON.stringify(current.proposedPayload, null, 2)}
        </Paper>
        {payloadEntries.length === 0 && <Typography color="text.secondary">No structured payload fields were supplied.</Typography>}

        {current.decisionEvidence && (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Decision evidence</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, whiteSpace: "pre-wrap" }}>{JSON.stringify(current.decisionEvidence, null, 2)}</Typography>
            {current.decisionReason && <Typography variant="body2" sx={{ mt: 1 }}>Reason: {current.decisionReason}</Typography>}
          </Paper>
        )}

        {pending ? (
          <>
            <TextField
              label="Decision reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              required
              fullWidth
              multiline
              minRows={3}
              slotProps={{ inputLabel: { shrink: true } }}
              helperText="Record the evidence or operational rationale for this decision."
            />
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ justifyContent: "flex-end" }}>
              <Button variant="outlined" color="error" onClick={() => void decide("REJECTED")} disabled={submitting}>{submitting ? "Saving…" : "Reject proposal"}</Button>
              <Button variant="contained" onClick={() => void decide("APPROVED")} disabled={submitting}>{submitting ? "Saving…" : "Approve proposal"}</Button>
            </Stack>
          </>
        ) : <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ alignSelf: "flex-start" }}>
          {current.status === "APPROVED" && current.referenceNodeId && <Button component={Link} href={`/instruments/${current.referenceNodeId}`} variant="contained">View approved instrument</Button>}
          <Button component={Link} href="/instruments/requests" variant={current.status === "APPROVED" && current.referenceNodeId ? "outlined" : "contained"}>Back to pending instrument requests</Button>
        </Stack>}
      </Stack>
    </Card>
  );
}
