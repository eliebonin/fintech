"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { Alert, Box, Button, Card, Chip, CircularProgress, InputAdornment, MenuItem, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";

import type { InstrumentRecord } from "@/lib/instrument-data";
import { INSTRUMENT_CATALOGUE_COLUMNS } from "@/lib/instrument-catalogue-view";

export function InstrumentCatalogue({ initialResults }: { initialResults: InstrumentRecord[] }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(initialResults);
  const [instrumentType, setInstrumentType] = useState("ALL");
  const [status, setStatus] = useState("ACTIVE");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const searchController = useRef<AbortController | null>(null);
  const types = [...new Set(initialResults.map((instrument) => instrument.instrumentType))].sort();
  const visibleResults = results.filter((instrument) => (
    (instrumentType === "ALL" || instrument.instrumentType === instrumentType)
    && (status === "ALL" || instrument.status === status)
  ));

  async function updateSearch(value: string) {
    setQuery(value);
    setError("");
    searchController.current?.abort();
    if (!value.trim()) {
      setResults(initialResults);
      return;
    }
    const controller = new AbortController();
    searchController.current = controller;
    setLoading(true);
    try {
      const response = await fetch(`/api/instruments/search?q=${encodeURIComponent(value)}`, { signal: controller.signal });
      if (!response.ok) throw new Error("Search service returned an error");
      setResults(((await response.json()) as { data: InstrumentRecord[] }).data);
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError("Search is temporarily unavailable. Try again or clear the query.");
        setResults([]);
      }
    } finally {
      if (searchController.current === controller) {
        searchController.current = null;
        setLoading(false);
      }
    }
  }

  return <Box sx={{ px: { xs: 2, md: 3.5 }, py: 3 }}>
    <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ mb: 2.5, justifyContent: "space-between", alignItems: { lg: "flex-end" } }}>
      <Box><Typography variant="overline" color="text.secondary">INSTRUMENTS / CATALOGUE</Typography><Typography variant="h5">Instrument catalogue</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Explore canonical instruments available to this tenant.</Typography></Box>
      <Stack direction="row" spacing={1}><Button component={Link} href="/instruments/requests" variant="outlined">Requests</Button><Button component={Link} href="/instruments/create" variant="contained">Create instrument</Button></Stack>
    </Stack>
    <Card sx={{ overflow: "hidden" }}>
      <Box sx={{ p: 2, borderBottom: "1px solid #edf0f5" }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.25} sx={{ alignItems: { md: "center" } }}>
          <TextField value={query} onChange={(event) => void updateSearch(event.target.value)} placeholder="Search name, ISIN, FIGI, ticker, venue, or external code…" fullWidth size="small" slotProps={{ input: { startAdornment: <InputAdornment position="start"><Typography sx={{ color: "#1f5eff", fontWeight: 900 }}>⌕</Typography></InputAdornment>, endAdornment: loading ? <InputAdornment position="end"><CircularProgress size={18} /></InputAdornment> : undefined } }} />
          <TextField select label="Type" value={instrumentType} onChange={(event) => setInstrumentType(event.target.value)} size="small" sx={{ minWidth: 160 }}><MenuItem value="ALL">All types</MenuItem>{types.map((type) => <MenuItem key={type} value={type}>{type}</MenuItem>)}</TextField>
          <TextField select label="Status" value={status} onChange={(event) => setStatus(event.target.value)} size="small" sx={{ minWidth: 130 }}><MenuItem value="ACTIVE">Active</MenuItem><MenuItem value="ALL">All statuses</MenuItem></TextField>
        </Stack>
        {error && <Alert severity="error" sx={{ mt: 1.5 }}>{error}</Alert>}
      </Box>
      <Box sx={{ px: 2, py: 1.25, borderBottom: "1px solid #edf0f5", display: "flex", justifyContent: "space-between", alignItems: "center" }}><Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}><Typography variant="subtitle2">Instruments</Typography><Chip label="CANONICAL" size="small" sx={{ height: 20, fontSize: 10, bgcolor: "#edf3ff", color: "#2854a7", fontWeight: 800 }} /></Stack><Chip label={`${visibleResults.length} records`} size="small" variant="outlined" /></Box>
      {visibleResults.length === 0 ? <Box sx={{ p: 3 }}><Typography variant="body2" sx={{ fontWeight: 700 }}>No matching instrument</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Try a different search term or broaden the filters.</Typography></Box> : <Box sx={{ overflowX: "auto" }}><Table size="small" aria-label="Instrument catalogue"><TableHead><TableRow>{INSTRUMENT_CATALOGUE_COLUMNS.map((column) => <TableCell key={column.key} sx={{ fontWeight: 800, whiteSpace: "nowrap" }}>{column.label}</TableCell>)}<TableCell /></TableRow></TableHead><TableBody>{visibleResults.map((instrument) => <TableRow key={instrument.instrumentId} hover><TableCell sx={{ fontWeight: 700, minWidth: 260 }}>{instrument.canonicalName}</TableCell><TableCell>{instrument.instrumentType}</TableCell><TableCell>{instrument.baseCurrency ?? "—"}</TableCell><TableCell><Chip label={instrument.status} size="small" color={instrument.status === "ACTIVE" ? "success" : "default"} variant="outlined" /></TableCell><TableCell>{instrument.listings.length || "—"}</TableCell><TableCell align="right"><Button component={Link} href={`/instruments/${instrument.instrumentId}`} size="small">View</Button></TableCell></TableRow>)}</TableBody></Table></Box>}
    </Card>
  </Box>;
}
