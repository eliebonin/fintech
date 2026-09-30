"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Box, Button, Card, Chip, Divider, Stack, TextField, Typography } from "@mui/material";

import type { WorkQueueItem, WorkQueuePayload } from "@/lib/work-queue";

const categoryLabels: Record<WorkQueueItem["category"], string> = {
  REFERENCE_DATA_REVIEW: "Reference-data reviews",
  MAPPING_REVIEW: "Mapping reviews",
  NAV_REVIEW: "NAV reviews",
  MARKET_DATA_EXCEPTION: "Market-data exceptions",
};

function submittedAt(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : "Submission time not recorded";
}

export function OperationsWorkQueue({ queue }: { queue: WorkQueuePayload }) {
  const [filter, setFilter] = useState("");
  const items = useMemo(() => {
    const query = filter.trim().toLowerCase();
    if (!query) return queue.items;
    return queue.items.filter((item) => [item.title, item.detail, item.category, item.proposalType, item.referenceId].filter(Boolean).join(" ").toLowerCase().includes(query));
  }, [filter, queue.items]);

  return <>
    <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }}>
      {(Object.entries(categoryLabels) as Array<[WorkQueueItem["category"], string]>).map(([category, label]) => <Card key={category} variant="outlined" sx={{ flex: 1, p: 1.5, bgcolor: "#f8faff" }}><Typography variant="caption" color="text.secondary">{label}</Typography><Typography variant="h6" sx={{ mt: 0.25 }}>{queue.counts[category]}</Typography></Card>)}
    </Stack>
    <TextField label="Filter operations queue" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Search title, workflow, reference, or detail" fullWidth size="small" sx={{ mb: 1.5, bgcolor: "white" }} />
    <Card variant="outlined">
      <Box sx={{ px: 2, py: 1.4, borderBottom: "1px solid #e7ecf4" }}><Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Awaiting review</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>Cross-module items requiring an operations or steward decision.</Typography></Box>
      {items.length === 0 ? <Box sx={{ p: 3 }}><Typography variant="body2" sx={{ fontWeight: 700 }}>No matching review items</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Clear the filter or return when a workflow needs a decision.</Typography></Box> : <Stack divider={<Divider flexItem />}>{items.map((item) => <Stack key={item.itemId} direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ p: 2, justifyContent: "space-between", alignItems: { md: "center" } }}><Box sx={{ minWidth: 0 }}><Typography variant="body2" sx={{ fontWeight: 800 }}>{item.title}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.4 }}>{item.detail}</Typography><Stack direction={{ xs: "column", sm: "row" }} spacing={{ xs: 0.25, sm: 2 }} sx={{ mt: 0.8 }}><Typography variant="caption" color="text.secondary">Workflow: {item.proposalType?.replace("CREATE_", "").replaceAll("_", " ") ?? item.category.replaceAll("_", " ")}</Typography><Typography variant="caption" color="text.secondary">Submitted: {submittedAt(item.proposedAt)}</Typography><Typography variant="caption" color="text.secondary">Reference: {item.referenceId ?? "—"}</Typography></Stack></Box><Stack direction="row" spacing={1} sx={{ flexShrink: 0, alignItems: "center" }}><Chip label={categoryLabels[item.category]} size="small" variant="outlined" /><Chip label={item.status} color="warning" size="small" />{item.reviewPath ? <Button component={Link} href={item.reviewPath} variant="outlined" size="small">Review</Button> : null}</Stack></Stack>)}</Stack>}
    </Card>
  </>;
}
