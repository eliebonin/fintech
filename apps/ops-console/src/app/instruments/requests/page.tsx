import { resolveWorkspaceAccess } from "@/lib/server/workspace-access";
import { WorkspaceUnavailable } from "@/components/workspace-unavailable";
export const dynamic = "force-dynamic";

import { redirect } from "next/navigation";
import { Alert, Box, Button, Card, Chip, Stack, Typography } from "@mui/material";

import { WorkspaceShell } from "@/components/workspace-shell";
import { filterInstrumentCreationRequests } from "@/lib/instrument-requests";
import { getWorkQueue, type WorkQueuePayload } from "@/lib/work-queue";
import {QueuePagination,queueOffset} from '@/components/queue-pagination';
import {canManageInstruments} from '@/lib/instrument-authority';

export default async function InstrumentRequestsPage({searchParams}:{searchParams?:Promise<{offset?:string}>}={}) {
  let tenantContext;
  let workspace;
  const access = await resolveWorkspaceAccess();
  if (access.kind === "session-required") redirect("/select-tenant");
  if (access.kind !== "ready") return <WorkspaceUnavailable forbidden={access.kind === "forbidden"} />;
  tenantContext = access.context; workspace = access.workspace;
  let queue: WorkQueuePayload | undefined;
  try { queue = await getWorkQueue({...tenantContext,offset:queueOffset((await searchParams)?.offset)}); } catch { /* The page explains the unavailable queue without substituting unrelated work. */ }
  const requests = filterInstrumentCreationRequests(queue?.items ?? []);
  return <WorkspaceShell sourceLabel={queue?.meta.source === "live-reference-api" ? "LIVE API" : "LOCAL FIXTURES"} tenantName={workspace.tenantName} membershipRole={workspace.membershipRole} moduleCodes={workspace.moduleCodes}><Box sx={{ px: { xs: 2, md: 3.5 }, py: 3, maxWidth: 1180 }}>
    <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { sm: "flex-end" }, mb: 3 }}><Box><Typography variant="overline" color="text.secondary">INSTRUMENTS / REQUESTS</Typography><Typography variant="h5">Pending instrument requests</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Only pending economic-instrument creations appear here. Market data, NAV, mappings, listings, and index-family setup are deliberately excluded.</Typography></Box>{canManageInstruments(workspace)?<Button href="/instruments/create" variant="contained">Create instrument</Button>:null}</Stack>
    {!queue && <Alert severity="warning">Instrument requests are temporarily unavailable. No cross-module work has been substituted into this page.</Alert>}
    {queue && requests.length === 0 && <Card sx={{ p: 3 }}><Typography variant="subtitle1" sx={{ fontWeight: 800 }}>No instrument requests on this queue page</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>This page shows economic-instrument requests from the current queue page. Use Next to inspect further queue records.</Typography></Card>}
    <Stack spacing={1.25}>{requests.map((request) => <Card key={request.itemId} sx={{ p: 2 }}><Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ justifyContent: "space-between", alignItems: { md: "center" } }}><Box><Typography variant="subtitle2" sx={{ fontWeight: 800 }}>{request.title}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>{request.detail}</Typography><Stack direction={{ xs: "column", sm: "row" }} spacing={{ xs: 0.25, sm: 2 }} sx={{ mt: 0.75 }}><Typography variant="caption" color="text.secondary">Type: {request.proposalType?.replace("CREATE_", "").replaceAll("_", " ") ?? "Instrument"}</Typography><Typography variant="caption" color="text.secondary">Submitted: {request.proposedAt ? new Date(request.proposedAt).toLocaleString() : "—"}</Typography><Typography variant="caption" color="text.secondary">Requester: {request.submittedByUserAccountId ?? "Recorded in proposal evidence"}</Typography></Stack></Box><Stack direction="row" spacing={1} sx={{ alignItems: "center", flexShrink: 0 }}><Chip label={request.status} color="warning" size="small" />{request.reviewPath && <Button href={request.reviewPath} variant="outlined" size="small">Review</Button>}</Stack></Stack></Card>)}</Stack>
    {queue && <QueuePagination meta={queue.meta} path="/instruments/requests" />}
  </Box></WorkspaceShell>;
}
