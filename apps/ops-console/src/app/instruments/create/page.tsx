"use client";

import Link from "next/link";
import { Box, Button, Card, Stack, Typography } from "@mui/material";

import { WorkspaceShell } from "@/components/workspace-shell";
import { INSTRUMENT_CREATE_GROUPS } from "@/lib/instrument-create-options";

export default function InstrumentCreatePage() {
  return <WorkspaceShell><Box sx={{ px: { xs: 2, md: 3.5 }, py: 3, maxWidth: 1180 }}>
    <Typography variant="overline" color="text.secondary">INSTRUMENTS / CREATE</Typography><Typography variant="h5">Create an instrument</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 3 }}>Choose the economic instrument type first. Each route creates a reviewable instrument request; venue listings are added only after an instrument is approved.</Typography>
    <Stack spacing={2.5}>{INSTRUMENT_CREATE_GROUPS.map((group) => <Box key={group.label}><Typography variant="subtitle1" sx={{ fontWeight: 800 }}>{group.label}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.25, mb: 1.25 }}>{group.description}</Typography><Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))", lg: "repeat(3, minmax(0, 1fr))" }, gap: 1.5 }}>{group.options.map((option) => <Card key={option.href} sx={{ p: 2, display: "flex", flexDirection: "column", alignItems: "flex-start" }}><Typography variant="subtitle2" sx={{ fontWeight: 800 }}>{option.label}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 1.5, flex: 1 }}>{option.description}</Typography><Button component={Link} href={option.href} size="small" variant="outlined">Choose {option.label}</Button></Card>)}</Box></Box>)}</Stack>
    <Card variant="outlined" sx={{ p: 2, mt: 3, bgcolor: "#f8faff" }}><Typography variant="subtitle2">Supporting reference structure</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Index families and venue listings are intentionally not types in this picker. They are supporting structures: an index family is governed separately, while a listing belongs to an approved instrument.</Typography></Card>
  </Box></WorkspaceShell>;
}
