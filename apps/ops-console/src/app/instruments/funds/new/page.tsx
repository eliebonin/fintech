"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { Alert, Box, Button, Card, Chip, Divider, Paper, Stack, TextField, Typography } from "@mui/material";

import { WorkspaceShell } from "@/components/workspace-shell";
import { fundOnboardingStages, validateFundDraft } from "./onboarding-model";

const FUND_KINDS = ["STANDALONE", "UMBRELLA", "SUB_FUND"];
const DOMICILES = ["IE — Ireland", "LU — Luxembourg", "GB — United Kingdom", "US — United States", "OTHER"];
const floatedLabel = { inputLabel: { shrink: true } } as const;
const nativeSelect = { ...floatedLabel, select: { native: true } } as const;

export default function NewFundPage() {
  const [canonicalName, setCanonicalName] = useState("");
  const [internalCode, setInternalCode] = useState("");
  const [fundKind, setFundKind] = useState("STANDALONE");
  const [domicileCountry, setDomicileCountry] = useState("");
  const [legalForm, setLegalForm] = useState("");
  const [manager, setManager] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  function continueDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors = validateFundDraft({ canonicalName, domicileCountry });
    if (errors.canonicalName || errors.domicileCountry) {
      setMessage(errors.canonicalName ?? errors.domicileCountry ?? null);
      return;
    }
    setMessage("Fund vehicle draft is complete. The next implementation slice will persist it through the dedicated fund-proposal API before share-class creation is enabled.");
  }

  return (
    <WorkspaceShell sourceLabel="UI DRAFT">
      <Box sx={{ minHeight: "100vh", bgcolor: "#f3f6fb", p: { xs: 2, md: 5 } }}>
        <Box sx={{ maxWidth: 1080, mx: "auto" }}>
          <Typography variant="caption" color="text.secondary"><Link href="/">WORKSPACE / INSTRUMENTS / FUNDS</Link></Typography>
          <Typography variant="h4" sx={{ mt: 1 }}>Add a fund</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2.5 }}>Start with the legal fund vehicle. A share class is then created as the tradable economic instrument; venue listings belong to that share class.</Typography>

          <Alert severity="info" sx={{ mb: 2.5 }}>
            This first draft establishes the correct workflow and field boundaries. It does not yet submit a fund proposal to the API, so it cannot create a canonical record or a listing.
          </Alert>
          {message && <Alert severity={message.startsWith("Fund vehicle") ? "success" : "error"} sx={{ mb: 2.5 }}>{message}</Alert>}

          <Stack direction={{ xs: "column", md: "row" }} spacing={1.25} sx={{ mb: 3 }}>
            {fundOnboardingStages.map((stage, index) => <Paper key={stage.key} variant="outlined" sx={{ flex: 1, p: 1.6, borderColor: index === 0 ? "#1f5eff" : "#d9e2f0", bgcolor: index === 0 ? "#f4f8ff" : "white" }}>
              <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}><Chip label={index + 1} size="small" color={index === 0 ? "primary" : "default"} /><Box><Typography variant="subtitle2" sx={{ fontWeight: 800 }}>{stage.title}</Typography><Typography variant="caption" color="text.secondary">{stage.tradable ? "Economic/tradable identity" : "Legal portfolio identity"}</Typography></Box></Stack>
            </Paper>)}
          </Stack>

          <Card component="form" onSubmit={continueDraft} sx={{ p: { xs: 2, md: 3 } }}>
            <Stack spacing={3}>
              <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 }, bgcolor: "#f7faff", borderColor: "#bfd3ff", borderLeft: "5px solid #1f5eff" }}>
                <Typography variant="overline" color="primary.main" sx={{ fontWeight: 800, letterSpacing: "0.1em" }}>1 · FUND VEHICLE</Typography>
                <Typography variant="h6">What legal portfolio are the share classes in?</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35, mb: 2.25 }}>Do not enter a ticker, NAV currency, ISIN, or listing here. Those belong to a later share-class record.</Typography>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <TextField label="Fund / sub-fund canonical name" value={canonicalName} onChange={(event) => setCanonicalName(event.target.value)} required fullWidth slotProps={floatedLabel} helperText="Official legal or prospectus name of the vehicle or sub-fund. It may have several investor share classes." />
                  <TextField label="Internal code (optional)" value={internalCode} onChange={(event) => setInternalCode(event.target.value)} fullWidth slotProps={floatedLabel} helperText="Stable internal display code. It is not the UUID, ISIN, or venue ticker." />
                </Stack>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mt: 2 }}>
                  <TextField select label="Fund kind" value={fundKind} onChange={(event) => setFundKind(event.target.value)} fullWidth slotProps={nativeSelect} helperText="Use SUB_FUND where the legal structure has an umbrella parent; standalone includes a single independent vehicle.">
                    {FUND_KINDS.map((value) => <option key={value} value={value}>{value}</option>)}
                  </TextField>
                  <TextField select label="Domicile" value={domicileCountry} onChange={(event) => setDomicileCountry(event.target.value)} required fullWidth slotProps={nativeSelect} helperText="Jurisdiction of the legal fund vehicle; this is distinct from the share-class dealing or listing currency.">
                    <option value="">— Choose domicile —</option>{DOMICILES.map((value) => <option key={value} value={value}>{value}</option>)}
                  </TextField>
                  <TextField label="Legal form (optional)" value={legalForm} onChange={(event) => setLegalForm(event.target.value)} fullWidth slotProps={floatedLabel} helperText="For example ICAV, SICAV, OEIC, unit trust, or limited partnership. Leave blank when source enrichment will provide it." />
                </Stack>
                <TextField label="Fund manager / AIFM (optional)" value={manager} onChange={(event) => setManager(event.target.value)} fullWidth slotProps={floatedLabel} sx={{ mt: 2 }} helperText="First-draft text field. The persisted workflow will use the canonical organisation selector and effective-dated fund-manager relationship." />
              </Paper>

              <Divider />
              <Paper variant="outlined" sx={{ p: 2.25, bgcolor: "#fbfcff" }}>
                <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 800, letterSpacing: "0.1em" }}>NEXT · SHARE CLASS</Typography>
                <Typography variant="h6">Create the security investors actually hold</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>The next screen will capture class code, currency, accumulating/distributing treatment, NAV/dealing frequency, ISIN, global FIGI, and class-specific fee rules. It becomes the `FUND_SHARE_CLASS` economic instrument.</Typography>
                <Alert severity="warning" sx={{ mt: 1.5 }}>A share class cannot be created until this fund vehicle has been approved and has its canonical internal UUID.</Alert>
              </Paper>

              <Paper variant="outlined" sx={{ p: 2.25, bgcolor: "#fffdf8" }}>
                <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 800, letterSpacing: "0.1em" }}>THEN · LISTINGS</Typography>
                <Typography variant="h6">Add only where that share class trades</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>Most mutual-fund classes have no venue listing and deal directly at NAV. A listed ETF share class may have one or several listings, each with its own ticker, trading currency, venue FIGI, quote factor, and unit multiplier.</Typography>
              </Paper>

              <Stack direction="row" sx={{ justifyContent: "space-between" }}><Button component={Link} href="/" variant="text">Cancel</Button><Button type="submit" variant="contained">Validate fund vehicle draft</Button></Stack>
            </Stack>
          </Card>
        </Box>
      </Box>
    </WorkspaceShell>
  );
}
