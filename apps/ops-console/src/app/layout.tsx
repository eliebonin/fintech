import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Providers } from "./providers";
import "./globals.css";
import "./native-workspace.css";
import './access-administration.css';

export const metadata: Metadata = {
  title: "Operations Console",
  description: "Reference data and market-data operations workspace",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
