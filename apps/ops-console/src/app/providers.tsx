"use client";

import { createTheme, CssBaseline, ThemeProvider } from "@mui/material";
import { AppRouterCacheProvider } from "@mui/material-nextjs/v16-appRouter";
import type { ReactNode } from "react";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#1f5eff" },
    secondary: { main: "#e9a23b" },
    background: { default: "#f3f6fb", paper: "#ffffff" },
    text: { primary: "#172238", secondary: "#667085" },
  },
  typography: {
    fontFamily: "var(--font-inter), Arial, sans-serif",
    h4: { fontWeight: 750, letterSpacing: "-0.03em" },
    h5: { fontWeight: 700, letterSpacing: "-0.02em" },
    h6: { fontWeight: 700 },
    button: { textTransform: "none", fontWeight: 650 },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiCard: { styleOverrides: { root: { boxShadow: "0 6px 24px rgba(24, 39, 75, 0.06)", border: "1px solid #e7ecf4" } } },
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiTableCell: { styleOverrides: { root: { borderColor: "#edf0f5" } } },
  },
});

export function Providers({ children }: { children: ReactNode }) {
  return (
    <AppRouterCacheProvider>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </AppRouterCacheProvider>
  );
}
