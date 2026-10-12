"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Alert, Box, Button, Card, Chip, CircularProgress, InputAdornment, MenuItem, Pagination, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";

import type { InstrumentCatalogueItem } from "api-contracts";
import { getCataloguePage } from "@/lib/instrument-catalogue-pagination";
import { INSTRUMENT_CATALOGUE_COLUMNS } from "@/lib/instrument-catalogue-view";

import { CATALOGUE_INSTRUMENT_TYPES } from "@/features/instruments/catalogue-types";
import { parseApiErrorResponse } from "@/lib/api-errors";

const PAGE_SIZES = [25, 50, 100];

export function InstrumentCatalogue({ initialResults, initialTotal = initialResults.length,canManage=false, initialError = "", onSourceChange }: { initialResults: InstrumentCatalogueItem[]; initialTotal?: number;canManage?:boolean; initialError?: string; onSourceChange?: (source: string) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(initialResults);
  const [instrumentType, setInstrumentType] = useState("ALL");
  const [status, setStatus] = useState("ACTIVE");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(initialTotal);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(initialError);
  const [revision, setRevision] = useState(0);
  const types = [...new Set([...CATALOGUE_INSTRUMENT_TYPES, ...initialResults.map(item => item.instrumentType), ...results.map(item => item.instrumentType)])].sort();
  const visibleResults = results;
  const { offset, pageCount, firstResult, lastResult } = getCataloguePage({ page, pageSize, total });

  useEffect(() => {
    if (revision === 0) return;
    const controller = new AbortController();
    let current = true;
    const timeout = window.setTimeout(() => {
      setLoading(true);
      setError("");
      const params = new URLSearchParams({ q: query, limit: String(pageSize), offset: String(offset) });
      if (instrumentType !== "ALL") params.set("instrument_type", instrumentType);
      if (status !== "ALL") params.set("status", status);
      fetch(`/api/instruments/catalogue?${params}`, { signal: controller.signal, cache: "no-store" })
        .then(async response => {
          if (!response.ok) throw await parseApiErrorResponse(response, "Search is temporarily unavailable. Try again.");
          return await response.json() as { data: InstrumentCatalogueItem[]; meta: { total?: number | null; source?: string } };
        })
        .then(payload => {
          if (!current) return;
          setResults(payload.data);
          setTotal(payload.meta.total ?? payload.data.length);
          onSourceChange?.(payload.meta.source?.includes("fixture") ? "LOCAL FIXTURES" : "LIVE API");
        })
        .catch((reason: unknown) => {
          if (!current || controller.signal.aborted) return;
          setError(reason instanceof Error ? reason.message : "Search could not be loaded. Try again.");
          setResults([]);
          setTotal(0);
          onSourceChange?.("SEARCH UNAVAILABLE");
        })
        .finally(() => { if (current) setLoading(false); });
    }, 300);
    return () => { current = false; window.clearTimeout(timeout); controller.abort(); };
  }, [instrumentType, offset, pageSize, query, status, revision, onSourceChange]);

  function changeQuery(value: string) { setRevision(value => value + 1); setQuery(value); setPage(1); }
  function changeType(value: string) { setRevision(value => value + 1); setInstrumentType(value); setPage(1); }
  function changeStatus(value: string) { setRevision(value => value + 1); setStatus(value); setPage(1); }
  function changePageSize(value: number) { setRevision(value => value + 1); setPageSize(value); setPage(1); }

  return <Box sx={{ px: { xs: 2, md: 3.5 }, py: 3 }}>
    <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ mb: 2.5, justifyContent: "space-between", alignItems: { lg: "flex-end" } }}>
      <Box><Typography variant="overline" color="text.secondary">INSTRUMENTS / CATALOGUE</Typography><Typography variant="h5">Instrument catalogue</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Explore canonical instruments available to this tenant.</Typography></Box>
      <Stack direction="row" spacing={1}><Button component={Link} href="/instruments/requests" variant="outlined">Requests</Button>{canManage?<Button component={Link} href="/instruments/create" variant="contained">Create instrument</Button>:null}</Stack>
    </Stack>
    <Card sx={{ overflow: "hidden" }}>
      <Box sx={{ p: 2, borderBottom: "1px solid #edf0f5" }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.25} sx={{ alignItems: { md: "center" } }}>
          <TextField value={query} onChange={(event) => changeQuery(event.target.value)} placeholder="Search name, ISIN, FIGI, ticker, venue, or external code…" fullWidth size="small" slotProps={{ input: { startAdornment: <InputAdornment position="start"><Typography sx={{ color: "#1f5eff", fontWeight: 900 }}>⌕</Typography></InputAdornment>, endAdornment: loading ? <InputAdornment position="end"><CircularProgress size={18} /></InputAdornment> : undefined } }} />
          <TextField select label="Type" value={instrumentType} onChange={(event) => changeType(event.target.value)} size="small" sx={{ minWidth: 160 }}><MenuItem value="ALL">All types</MenuItem>{types.map((type) => <MenuItem key={type} value={type}>{type}</MenuItem>)}</TextField>
          <TextField select label="Status" value={status} onChange={(event) => changeStatus(event.target.value)} size="small" sx={{ minWidth: 130 }}><MenuItem value="ACTIVE">Active</MenuItem><MenuItem value="ALL">All statuses</MenuItem></TextField>
        </Stack>
        {error && <Alert severity="error" sx={{ mt: 1.5 }}>{error} <Button onClick={() => setRevision(value => value + 1)}>Try again</Button></Alert>}
      </Box>
      <Box sx={{ px: 2, py: 1.25, borderBottom: "1px solid #edf0f5", display: "flex", justifyContent: "space-between", alignItems: "center" }}><Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}><Typography variant="subtitle2">Instruments</Typography><Chip label="CANONICAL" size="small" sx={{ height: 20, fontSize: 10, bgcolor: "#edf3ff", color: "#2854a7", fontWeight: 800 }} /></Stack><Typography variant="caption" color="text.secondary">{firstResult}–{lastResult} of {total}</Typography></Box>
      {!error && visibleResults.length === 0 ? <Box sx={{ p: 3 }}><Typography variant="body2" sx={{ fontWeight: 700 }}>No matching instrument</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Try a different search term or broaden the filters.</Typography></Box> : <Box sx={{ overflowX: "auto" }}><Table size="small" aria-label="Instrument catalogue"><TableHead><TableRow>{INSTRUMENT_CATALOGUE_COLUMNS.map((column) => <TableCell key={column.key} sx={{ fontWeight: 800, whiteSpace: "nowrap" }}>{column.label}</TableCell>)}<TableCell /></TableRow></TableHead><TableBody>{visibleResults.map((instrument) => <TableRow key={instrument.instrumentId} hover><TableCell sx={{ fontWeight: 700, minWidth: 260 }}>{instrument.canonicalName}</TableCell><TableCell>{instrument.instrumentType}</TableCell><TableCell>{instrument.baseCurrency ?? "—"}</TableCell><TableCell><Chip label={instrument.status} size="small" color={instrument.status === "ACTIVE" ? "success" : "default"} variant="outlined" /></TableCell><TableCell>{instrument.listingCount || "—"}</TableCell><TableCell align="right"><Button component={Link} href={`/instruments/${instrument.instrumentId}`} size="small">View</Button></TableCell></TableRow>)}</TableBody></Table></Box>}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ px: 2, py: 1.5, justifyContent: "space-between", alignItems: { sm: "center" } }}>
        <TextField select label="Rows per page" value={String(pageSize)} onChange={(event) => changePageSize(Number(event.target.value))} size="small" sx={{ minWidth: 160 }}>{PAGE_SIZES.map((size) => <MenuItem key={size} value={String(size)}>{size}</MenuItem>)}</TextField>
        <Pagination count={pageCount} page={page} onChange={(_, nextPage) => { setPage(nextPage); setRevision(value => value + 1); }} siblingCount={0} boundaryCount={1} color="primary" showFirstButton showLastButton aria-label="Instrument catalogue pages" />
      </Stack>
    </Card>
  </Box>;
}
