"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  CircularProgress,
  Divider,
  InputAdornment,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { InstrumentDetail } from "./instrument-detail";
import type { InstrumentRecord } from "@/lib/instrument-data";
import type { WorkQueueItem, WorkQueuePayload } from "@/lib/work-queue";
import { WorkspaceShell } from "./workspace-shell";

export function OperationsConsole({ initialResults, initialSource = "synthetic-fixture", initialQueue, tenantName, tenantCode, membershipRole, moduleCodes }: { initialResults: InstrumentRecord[]; initialSource?: string; initialQueue?: WorkQueuePayload; tenantName: string; tenantCode: string; membershipRole: string; moduleCodes: string[] }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(initialResults);
  const [selectedId, setSelectedId] = useState(initialResults[0]?.instrumentId ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const searchController = useRef<AbortController | null>(null);
  const [queue, setQueue] = useState<WorkQueuePayload | undefined>(initialQueue);
  const [queueLoading, setQueueLoading] = useState(!initialQueue);
  const [queueError, setQueueError] = useState("");
  const [selectedQueueItem, setSelectedQueueItem] = useState<WorkQueueItem | null>(initialQueue?.items[0] ?? null);
  const [queueFilter, setQueueFilter] = useState("");

  useEffect(() => {
    if (initialQueue) return;
    let active = true;
    fetch("/api/work-queue")
      .then(async (response) => {
        if (!response.ok) throw new Error("Work queue service returned an error");
        return (await response.json()) as WorkQueuePayload;
      })
      .then((payload) => {
        if (active) {
          setQueue(payload);
          setSelectedQueueItem(payload.items[0] ?? null);
        }
      })
      .catch(() => {
        if (active) setQueueError("Work queue is temporarily unavailable.");
      })
      .finally(() => {
        if (active) setQueueLoading(false);
      });
    return () => {
      active = false;
    };
  }, [initialQueue]);

  const selected = results.find((instrument) => instrument.instrumentId === selectedId) ?? results[0];
  const normalizedQueueFilter = queueFilter.trim().toLowerCase();
  const visibleQueueItems = queue?.items.filter((item) => {
    if (!normalizedQueueFilter) return true;
    return [item.title, item.detail, item.status, item.category, item.referenceId ?? ""]
      .join(" ")
      .toLowerCase()
      .includes(normalizedQueueFilter);
  }) ?? [];

  async function updateSearch(value: string) {
    setQuery(value);
    setError("");
    searchController.current?.abort();
    if (!value.trim()) {
      setResults(initialResults);
      setSelectedId(initialResults[0]?.instrumentId ?? "");
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    searchController.current = controller;
    setLoading(true);
    try {
      const response = await fetch(`/api/instruments/search?q=${encodeURIComponent(value)}`, { signal: controller.signal });
      if (!response.ok) throw new Error("Search service returned an error");
      const payload = (await response.json()) as { data: InstrumentRecord[] };
      setResults(payload.data);
      setSelectedId(payload.data[0]?.instrumentId ?? "");
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError("Search is temporarily unavailable. Try again or clear the query.");
      setResults([]);
      setSelectedId("");
    } finally {
      if (searchController.current === controller) {
        searchController.current = null;
        setLoading(false);
      }
    }
  }

  function inspectQueueItem(item: WorkQueueItem) {
    setSelectedQueueItem(item);
  }

  function handleQueueItemKeyDown(event: React.KeyboardEvent<HTMLDivElement>, item: WorkQueueItem) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      inspectQueueItem(item);
    }
  }

  return (
    <WorkspaceShell sourceLabel={initialSource === "live-reference-api" ? "LIVE API" : "LOCAL FIXTURES"} tenantName={tenantName} membershipRole={membershipRole} moduleCodes={moduleCodes}>
        <Box sx={{ px: { xs: 2, md: 3.5 }, py: 3 }}>
          <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ mb: 2.5, justifyContent: "space-between", alignItems: { lg: "flex-end" } }}>
            <Box><Typography variant="overline" color="text.secondary">ACTIVE TENANT · {tenantName} · {tenantCode}</Typography><Typography variant="h5">Global instrument catalogue</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Canonical instruments, venue listings, and external aliases available to this tenant. Tenant-owned instruments will appear as a separate category.</Typography></Box>
            <Button variant="outlined" size="small">Export view</Button>
          </Stack>
          <TextField value={query} onChange={(event) => void updateSearch(event.target.value)} placeholder="Search by name, ISIN, FIGI, ticker, venue, or external code…" fullWidth size="small" sx={{ bgcolor: "white", mb: 2.5 }} slotProps={{ input: { startAdornment: <InputAdornment position="start"><Typography sx={{ color: "#1f5eff", fontWeight: 900 }}>⌕</Typography></InputAdornment>, endAdornment: loading ? <InputAdornment position="end"><CircularProgress size={18} /></InputAdornment> : undefined } }} />
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <Card id="work-queue" sx={{ mb: 2.5, p: 2 }}>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { md: "center" } }}>
              <Box><Typography variant="subtitle2">Work queue</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>Items requiring an operations or steward decision.</Typography></Box>
              {queueLoading ? <CircularProgress size={20} /> : <Chip label={`${queue ? queue.items.length : 0} open`} size="small" color={queue && queue.items.length ? "warning" : "success"} />}
            </Stack>
            {queueError && <Alert severity="error" sx={{ mt: 1.5 }}>{queueError}</Alert>}
            {queue && <>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mt: 1.75 }}>
                {[["Reference-data reviews", queue.counts.REFERENCE_DATA_REVIEW], ["Mapping reviews", queue.counts.MAPPING_REVIEW], ["NAV reviews", queue.counts.NAV_REVIEW], ["Market-data exceptions", queue.counts.MARKET_DATA_EXCEPTION]].map(([label, count]) => <Box key={String(label)} sx={{ flex: 1, px: 1.4, py: 1.1, bgcolor: "#f7f9fc", borderRadius: 1.5 }}><Typography variant="caption" color="text.secondary">{label}</Typography><Typography variant="h6" sx={{ mt: 0.25 }}>{count}</Typography></Box>)}
              </Stack>
              <TextField
                label="Filter work queue"
                value={queueFilter}
                onChange={(event) => setQueueFilter(event.target.value)}
                placeholder="e.g. ETH, Ethereum, bond, mapping ID…"
                size="small"
                fullWidth
                sx={{ mt: 1.5 }}
              />
              {queue.items.length > 0 && <Stack divider={<Divider flexItem />} sx={{ mt: 1.25, maxHeight: 420, overflowY: "auto", pr: 0.5 }}>
                {visibleQueueItems.map((item) => {
                  const isSelected = selectedQueueItem?.itemId === item.itemId;
                  return (
                    <Stack
                      key={item.itemId}
                      direction="row"
                      spacing={1.5}
                      role="button"
                      tabIndex={0}
                      aria-label={`Inspect ${item.title}`}
                      onClick={() => inspectQueueItem(item)}
                      onKeyDown={(event) => handleQueueItemKeyDown(event, item)}
                      sx={{ py: 1, px: 0.75, justifyContent: "space-between", alignItems: "center", cursor: "pointer", borderRadius: 1.5, bgcolor: isSelected ? "#eef3ff" : "transparent", "&:hover": { bgcolor: "#f7f9fc" } }}
                    >
                      <Box sx={{ minWidth: 0 }}><Typography variant="body2" sx={{ fontWeight: 700 }}>{item.title}</Typography><Typography variant="caption" color="text.secondary">{item.detail}</Typography></Box>
                      <Stack direction="row" spacing={0.75} sx={{ flexShrink: 0, alignItems: "center" }}><Chip label={item.category.replaceAll("_", " ")} size="small" variant="outlined" sx={{ fontSize: 10 }} />{item.reviewPath && <Button component={Link} href={item.reviewPath} size="small" variant="outlined" onClick={(event) => event.stopPropagation()} sx={{ minWidth: 0, px: 1.1 }}>Review</Button>}</Stack>
                    </Stack>
                  );
                })}
                {visibleQueueItems.length === 0 && <Typography variant="body2" color="text.secondary" sx={{ py: 2, px: 0.75 }}>No queue records match this filter.</Typography>}
              </Stack>}
              {selectedQueueItem && <Box id="work-queue-detail" sx={{ mt: 1.5, p: 1.5, border: "1px solid #d7e3ff", borderRadius: 1.5, bgcolor: "#f8faff" }}>
                <Typography variant="overline" color="primary.main" sx={{ letterSpacing: "0.08em", fontWeight: 800 }}>Selected queue record</Typography>
                <Typography variant="subtitle2" sx={{ mt: 0.25 }}>{selectedQueueItem.title}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>{selectedQueueItem.detail}</Typography>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={{ xs: 0.25, sm: 2 }} sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">Status: <strong>{selectedQueueItem.status}</strong></Typography>
                  <Typography variant="caption" color="text.secondary">Category: <strong>{selectedQueueItem.category.replaceAll("_", " ")}</strong></Typography>
                  <Typography variant="caption" color="text.secondary">Reference: <strong>{selectedQueueItem.referenceId ?? "—"}</strong></Typography>
                </Stack>
                {selectedQueueItem.reviewPath && <Button component={Link} href={selectedQueueItem.reviewPath} size="small" variant="contained" sx={{ mt: 1.25 }}>Open review</Button>}
              </Box>}
            </>}
          </Card>

          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", xl: "360px minmax(0, 1fr)" }, gap: 2.5, alignItems: "start" }}>
            <Card sx={{ overflow: "hidden" }}>
              <Box sx={{ px: 2, py: 1.6, borderBottom: "1px solid #edf0f5", display: "flex", justifyContent: "space-between", alignItems: "center" }}><Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}><Typography variant="subtitle2">Results</Typography><Chip label="GLOBAL" size="small" sx={{ height: 20, fontSize: 10, bgcolor: "#edf3ff", color: "#2854a7", fontWeight: 800 }} /></Stack><Chip label={`${results.length} records`} size="small" variant="outlined" /></Box>
              {results.length === 0 ? <Box sx={{ p: 3 }}><Typography variant="body2" sx={{ fontWeight: 700 }}>No matching instrument</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Try an ISIN, venue MIC, or external mapping code.</Typography></Box> : results.map((instrument) => <Box key={instrument.instrumentId} role="button" tabIndex={0} aria-label={`Select ${instrument.canonicalName}`} onClick={() => setSelectedId(instrument.instrumentId)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelectedId(instrument.instrumentId); } }} sx={{ px: 2, py: 1.7, cursor: "pointer", borderBottom: "1px solid #edf0f5", bgcolor: selected?.instrumentId === instrument.instrumentId ? "#eef3ff" : "white", borderLeft: selected?.instrumentId === instrument.instrumentId ? "3px solid #1f5eff" : "3px solid transparent", "&:hover": { bgcolor: "#f7f9fc" }, "&:focus-visible": { outline: "2px solid #1f5eff", outlineOffset: -2 } }}><Stack direction="row" spacing={1} sx={{ justifyContent: "space-between" }}><Box sx={{ minWidth: 0 }}><Typography variant="body2" sx={{ fontWeight: 750, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{instrument.canonicalName}</Typography><Typography variant="caption" color="text.secondary">{instrument.instrumentType} · {instrument.baseCurrency}</Typography></Box><Chip label={instrument.status} size="small" color="success" variant="outlined" sx={{ height: 21, fontSize: 10 }} /></Stack><Stack direction="row" spacing={0.6} useFlexGap sx={{ mt: 1, flexWrap: "wrap" }}>{instrument.listings.slice(0, 3).map((listing) => <Chip key={listing.listingId} label={`${listing.marketVenueMic} ${listing.tradingSymbol}`} size="small" sx={{ height: 21, fontSize: 10, bgcolor: "#f4f6fa" }} />)}{instrument.listings.length === 0 && <Chip label="OTC / instrument-level" size="small" sx={{ height: 21, fontSize: 10, bgcolor: "#f4f6fa" }} />}</Stack></Box>)}
            </Card>
            {selected ? <InstrumentDetail instrument={selected} /> : <Card sx={{ p: 4 }}><Typography variant="h6">Select an instrument</Typography></Card>}
          </Box>
        </Box>
    </WorkspaceShell>
  );
}
