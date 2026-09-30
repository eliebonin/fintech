"use client";

import { useRef, useState } from "react";
import { Alert, Box, Button, Card, Chip, CircularProgress, InputAdornment, Stack, TextField, Typography } from "@mui/material";
import Link from "next/link";

import { InstrumentDetail } from "./instrument-detail";
import type { InstrumentRecord } from "@/lib/instrument-data";

export function InstrumentCatalogue({ initialResults }: { initialResults: InstrumentRecord[] }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(initialResults);
  const [selectedId, setSelectedId] = useState(initialResults[0]?.instrumentId ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const searchController = useRef<AbortController | null>(null);
  const selected = results.find((instrument) => instrument.instrumentId === selectedId) ?? results[0];

  async function updateSearch(value: string) {
    setQuery(value);
    setError("");
    searchController.current?.abort();
    if (!value.trim()) {
      setResults(initialResults);
      setSelectedId(initialResults[0]?.instrumentId ?? "");
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
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError("Search is temporarily unavailable. Try again or clear the query.");
        setResults([]);
        setSelectedId("");
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
      <Box><Typography variant="overline" color="text.secondary">INSTRUMENTS / CATALOGUE</Typography><Typography variant="h5">Instrument catalogue</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Explore canonical instruments available to this tenant. Tenant-owned instruments will be shown separately when that model is introduced.</Typography></Box>
      <Stack direction="row" spacing={1}><Button component={Link} href="/instruments/requests" variant="outlined">Requests</Button><Button component={Link} href="/instruments/create" variant="contained">Create instrument</Button></Stack>
    </Stack>
    <TextField value={query} onChange={(event) => void updateSearch(event.target.value)} placeholder="Search by name, ISIN, FIGI, ticker, venue, or external code…" fullWidth size="small" sx={{ bgcolor: "white", mb: 2.5 }} slotProps={{ input: { startAdornment: <InputAdornment position="start"><Typography sx={{ color: "#1f5eff", fontWeight: 900 }}>⌕</Typography></InputAdornment>, endAdornment: loading ? <InputAdornment position="end"><CircularProgress size={18} /></InputAdornment> : undefined } }} />
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", xl: "360px minmax(0, 1fr)" }, gap: 2.5, alignItems: "start" }}>
      <Card sx={{ overflow: "hidden" }}>
        <Box sx={{ px: 2, py: 1.6, borderBottom: "1px solid #edf0f5", display: "flex", justifyContent: "space-between", alignItems: "center" }}><Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}><Typography variant="subtitle2">Results</Typography><Chip label="CANONICAL" size="small" sx={{ height: 20, fontSize: 10, bgcolor: "#edf3ff", color: "#2854a7", fontWeight: 800 }} /></Stack><Chip label={`${results.length} records`} size="small" variant="outlined" /></Box>
        {results.length === 0 ? <Box sx={{ p: 3 }}><Typography variant="body2" sx={{ fontWeight: 700 }}>No matching instrument</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Try an ISIN, venue MIC, or external mapping code.</Typography></Box> : results.map((instrument) => <Box key={instrument.instrumentId} role="button" tabIndex={0} aria-label={`Select ${instrument.canonicalName}`} onClick={() => setSelectedId(instrument.instrumentId)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelectedId(instrument.instrumentId); } }} sx={{ px: 2, py: 1.7, cursor: "pointer", borderBottom: "1px solid #edf0f5", bgcolor: selected?.instrumentId === instrument.instrumentId ? "#eef3ff" : "white", borderLeft: selected?.instrumentId === instrument.instrumentId ? "3px solid #1f5eff" : "3px solid transparent", "&:hover": { bgcolor: "#f7f9fc" }, "&:focus-visible": { outline: "2px solid #1f5eff", outlineOffset: -2 } }}><Stack direction="row" spacing={1} sx={{ justifyContent: "space-between" }}><Box sx={{ minWidth: 0 }}><Typography variant="body2" sx={{ fontWeight: 750, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{instrument.canonicalName}</Typography><Typography variant="caption" color="text.secondary">{instrument.instrumentType} · {instrument.baseCurrency}</Typography></Box><Chip label={instrument.status} size="small" color="success" variant="outlined" sx={{ height: 21, fontSize: 10 }} /></Stack><Stack direction="row" spacing={0.6} useFlexGap sx={{ mt: 1, flexWrap: "wrap" }}>{instrument.listings.slice(0, 3).map((listing) => <Chip key={listing.listingId} label={`${listing.marketVenueMic} ${listing.tradingSymbol}`} size="small" sx={{ height: 21, fontSize: 10, bgcolor: "#f4f6fa" }} />)}{instrument.listings.length === 0 && <Chip label="OTC / instrument-level" size="small" sx={{ height: 21, fontSize: 10, bgcolor: "#f4f6fa" }} />}</Stack></Box>)}
      </Card>
      {selected ? <InstrumentDetail instrument={selected} /> : <Card sx={{ p: 4 }}><Typography variant="h6">Select an instrument</Typography></Card>}
    </Box>
  </Box>;
}
