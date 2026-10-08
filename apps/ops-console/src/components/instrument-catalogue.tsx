"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Alert, Box, Button, Card, Chip, CircularProgress, InputAdornment, MenuItem, Pagination, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";

import type { InstrumentRecord } from "@/lib/instrument-data";
import { getCataloguePage } from "@/lib/instrument-catalogue-pagination";
import { INSTRUMENT_CATALOGUE_COLUMNS } from "@/lib/instrument-catalogue-view";

const PAGE_SIZES = [25, 50, 100];

export function InstrumentCatalogue({ initialResults, initialTotal = initialResults.length,canManage=false }: { initialResults: InstrumentRecord[]; initialTotal?: number;canManage?:boolean }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(initialResults);
  const [instrumentType, setInstrumentType] = useState("ALL");
  const [status, setStatus] = useState("ACTIVE");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(initialTotal);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const hasLoadedInitialPage = useRef(false);
  const searchController = useRef<AbortController | null>(null);
  const types = [...new Set([...initialResults, ...results].map((instrument) => instrument.instrumentType))].sort();
  const visibleResults = results;
  const { offset, pageCount, firstResult, lastResult } = getCataloguePage({ page, pageSize, total });

  useEffect(() => {
    if (!hasLoadedInitialPage.current) {
      hasLoadedInitialPage.current = true;
      return;
    }
    const timeout = window.setTimeout(() => {
      const controller = new AbortController();
      searchController.current?.abort();
      searchController.current = controller;
      setLoading(true);
      setError("");
      const params = new URLSearchParams({ q: query, limit: String(pageSize), offset: String(offset) });
      if (instrumentType !== "ALL") params.set("instrument_type", instrumentType);
      if (status !== "ALL") params.set("status", status);
      fetch(`/api/instruments/search?${params}`, { signal: controller.signal })
        .then(async (response) => {
          if (!response.ok) throw new Error("Search service returned an error");
          return (await response.json()) as { data: InstrumentRecord[]; meta: { total?: number | null } };
        })
        .then((payload) => {
          setResults(payload.data);
          setTotal(payload.meta.total ?? payload.data.length);
        })
        .catch((reason: unknown) => {
          if (!(reason instanceof DOMException && reason.name === "AbortError")) {
            setError("Search is temporarily unavailable. Try again or clear the query.");
            setResults([]);
            setTotal(0);
          }
        })
        .finally(() => {
          if (searchController.current === controller) {
            searchController.current = null;
            setLoading(false);
          }
        });
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [instrumentType, offset, pageSize, query, status]);

  function changeQuery(value: string) { setQuery(value); setPage(1); }
  function changeType(value: string) { setInstrumentType(value); setPage(1); }
  function changeStatus(value: string) { setStatus(value); setPage(1); }
  function changePageSize(value: number) { setPageSize(value); setPage(1); }

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
        {error && <Alert severity="error" sx={{ mt: 1.5 }}>{error}</Alert>}
      </Box>
      <Box sx={{ px: 2, py: 1.25, borderBottom: "1px solid #edf0f5", display: "flex", justifyContent: "space-between", alignItems: "center" }}><Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}><Typography variant="subtitle2">Instruments</Typography><Chip label="CANONICAL" size="small" sx={{ height: 20, fontSize: 10, bgcolor: "#edf3ff", color: "#2854a7", fontWeight: 800 }} /></Stack><Typography variant="caption" color="text.secondary">{firstResult}–{lastResult} of {total}</Typography></Box>
      {visibleResults.length === 0 ? <Box sx={{ p: 3 }}><Typography variant="body2" sx={{ fontWeight: 700 }}>No matching instrument</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Try a different search term or broaden the filters.</Typography></Box> : <Box sx={{ overflowX: "auto" }}><Table size="small" aria-label="Instrument catalogue"><TableHead><TableRow>{INSTRUMENT_CATALOGUE_COLUMNS.map((column) => <TableCell key={column.key} sx={{ fontWeight: 800, whiteSpace: "nowrap" }}>{column.label}</TableCell>)}<TableCell /></TableRow></TableHead><TableBody>{visibleResults.map((instrument) => <TableRow key={instrument.instrumentId} hover><TableCell sx={{ fontWeight: 700, minWidth: 260 }}>{instrument.canonicalName}</TableCell><TableCell>{instrument.instrumentType}</TableCell><TableCell>{instrument.baseCurrency ?? "—"}</TableCell><TableCell><Chip label={instrument.status} size="small" color={instrument.status === "ACTIVE" ? "success" : "default"} variant="outlined" /></TableCell><TableCell>{instrument.listings.length || "—"}</TableCell><TableCell align="right"><Button component={Link} href={`/instruments/${instrument.instrumentId}`} size="small">View</Button></TableCell></TableRow>)}</TableBody></Table></Box>}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ px: 2, py: 1.5, justifyContent: "space-between", alignItems: { sm: "center" } }}>
        <TextField select label="Rows per page" value={String(pageSize)} onChange={(event) => changePageSize(Number(event.target.value))} size="small" sx={{ minWidth: 160 }}>{PAGE_SIZES.map((size) => <MenuItem key={size} value={String(size)}>{size}</MenuItem>)}</TextField>
        <Pagination count={pageCount} page={page} onChange={(_, nextPage) => setPage(nextPage)} siblingCount={0} boundaryCount={1} color="primary" showFirstButton showLastButton aria-label="Instrument catalogue pages" />
      </Stack>
    </Card>
  </Box>;
}
