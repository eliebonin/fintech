"use client";

import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  Divider,
  Stack,
  Typography,
} from "@mui/material";

import { calculateCutoffPnl, CUTOFF_PNL_SCENARIOS, type CutoffPnlResult } from "@/lib/cutoff-pnl";

type ScenarioKey = keyof typeof CUTOFF_PNL_SCENARIOS;

function money(value: number, currency: string) {
  const sign = value < 0 ? "-" : "";
  return `${sign}${currency} ${Math.abs(value).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function number(value: number) {
  return value.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function PnlEffect({ label, value, currency, scale }: { label: string; value: number; currency: string; scale: number }) {
  const positive = value >= 0;
  const width = value === 0 ? 3 : Math.max(6, Math.min(100, (Math.abs(value) / scale) * 100));
  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <Typography variant="body2" sx={{ fontWeight: 700 }}>{label}</Typography>
        <Typography variant="body2" sx={{ fontWeight: 800, color: positive ? "#14753c" : "#b42318" }}>{money(value, currency)}</Typography>
      </Stack>
      <Box sx={{ height: 8, mt: 0.65, bgcolor: "#edf1f7", borderRadius: 8, overflow: "hidden" }} aria-hidden="true">
        <Box sx={{ width: `${width}%`, height: "100%", bgcolor: positive ? "#42a86b" : "#e27c73", borderRadius: 8 }} />
      </Box>
    </Box>
  );
}

function ValuePair({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.25 }}>{label}</Typography>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>{value}</Typography>
    </Box>
  );
}

export function CutoffPnlLab() {
  const [selectedKey, setSelectedKey] = useState<ScenarioKey>("US");
  const scenario = CUTOFF_PNL_SCENARIOS[selectedKey];
  const result = useMemo(() => calculateCutoffPnl(scenario), [scenario]);
  const scale = Math.max(Math.abs(result.pricePnl) + Math.abs(result.fxPnl), 1);

  return (
    <Card sx={{ mb: 2.5, p: 2, borderColor: "#d7e3ff" }}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ justifyContent: "space-between", alignItems: { md: "center" } }}>
        <Box>
          <Typography variant="subtitle2">Cutoff P&amp;L lab</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>Switch the valuation context to see how the same cutoff-aware data produces a different reporting-currency P&amp;L.</Typography>
        </Box>
        <Chip label="ILLUSTRATIVE · NOT A BOOKED RUN" size="small" sx={{ alignSelf: { xs: "flex-start", md: "center" }, bgcolor: "#fff4dc", color: "#9a6200", fontWeight: 800, fontSize: 10 }} />
      </Stack>

      <Stack direction="row" spacing={1} sx={{ mt: 1.75 }} role="group" aria-label="Choose valuation cutoff scenario">
        {(["UK", "US"] as ScenarioKey[]).map((key) => {
          const candidate = CUTOFF_PNL_SCENARIOS[key];
          return (
            <Button
              key={key}
              size="small"
              variant={selectedKey === key ? "contained" : "outlined"}
              onClick={() => setSelectedKey(key)}
              aria-pressed={selectedKey === key}
            >
              {candidate.label} · {candidate.reportingCurrency}
            </Button>
          );
        })}
      </Stack>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1.2fr" }, gap: 2, mt: 2 }}>
        <Box sx={{ p: 1.75, bgcolor: "#f7f9fc", borderRadius: 2 }}>
          <Typography variant="caption" color="primary.main" sx={{ fontWeight: 800, letterSpacing: "0.1em" }}>INPUTS SELECTED</Typography>
          <Typography variant="subtitle2" sx={{ mt: 0.5 }}>{scenario.holdingLabel}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>{scenario.quantity.toLocaleString("en-GB")} {scenario.localCurrency} units · {scenario.fxQuote}</Typography>
          <Divider sx={{ my: 1.5 }} />
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1.5 }}>
            <ValuePair label="Previous local value" value={`${scenario.localCurrency} ${number(result.openingLocalValue)}`} />
            <ValuePair label="Selected local value" value={`${scenario.localCurrency} ${number(result.closingLocalValue)}`} />
            <ValuePair label="Quote factor" value={number(scenario.quoteFactor)} />
            <ValuePair label="Unit multiplier" value={number(scenario.unitMultiplier)} />
            <ValuePair label="Previous FX" value={number(scenario.priorFxRate)} />
            <ValuePair label="Selected FX" value={number(scenario.selectedFxRate)} />
            <ValuePair label="P&L period" value={`${scenario.priorMarketDate} → ${scenario.selectedMarketDate}`} />
          </Box>
          <Box sx={{ mt: 1.5, px: 1.2, py: 1, bgcolor: "white", borderRadius: 1.5 }}>
            <Typography variant="caption" color="text.secondary">Frozen information cut</Typography>
            <Typography variant="body2" sx={{ fontWeight: 750 }}>{scenario.utcCut} · {scenario.timezone}</Typography>
          </Box>
        </Box>

        <Box>
          <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "flex-start" }}>
            <Box>
              <Typography variant="caption" color="primary.main" sx={{ fontWeight: 800, letterSpacing: "0.1em" }}>REPORTING-CURRENCY RESULT</Typography>
              <Typography variant="h5" sx={{ mt: 0.45, color: result.totalPnl >= 0 ? "#14753c" : "#b42318" }}>{money(result.totalPnl, scenario.reportingCurrency)}</Typography>
            </Box>
            <Chip label={`${scenario.fxPair} · ${scenario.utcCut}`} size="small" variant="outlined" sx={{ fontSize: 10, fontWeight: 750 }} />
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Opening {money(result.openingReportingValue, scenario.reportingCurrency)} → closing {money(result.closingReportingValue, scenario.reportingCurrency)}</Typography>
          <Divider sx={{ my: 1.5 }} />
          <Stack spacing={1.35}>
            <PnlEffect label="Price / local-market effect" value={result.pricePnl} currency={scenario.reportingCurrency} scale={scale} />
            <PnlEffect label="FX translation effect" value={result.fxPnl} currency={scenario.reportingCurrency} scale={scale} />
          </Stack>
          <Alert severity="info" icon={false} sx={{ mt: 1.7, py: 0.15, bgcolor: "#eef5ff", color: "#31517d" }}>
            {scenario.laterValue} arrives at {scenario.laterReceivedUtc}; it is retained but excluded from this frozen cutoff.
          </Alert>
        </Box>
      </Box>

      <Alert severity="warning" icon={false} sx={{ mt: 1.75, py: 0.15, bgcolor: "#fff9ed", color: "#79541a" }}>
        Model check: this lab makes the UTC cutoff explicit, but the MVP does not yet link the illustrative position to a persisted trade/position snapshot or derive the local-time cutoff from a governed holiday calendar.
      </Alert>
    </Card>
  );
}
