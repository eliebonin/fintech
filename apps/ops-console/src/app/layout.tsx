import type { Metadata } from "next";
import type { ReactNode } from "react";
import {cookies} from 'next/headers';
import {contextFingerprint} from '@/lib/server/context-fingerprint';
import {workspaceCssVariables} from '@/lib/workspace-presentation';

import { Providers } from "./providers";
import "./globals.css";
import "./native-workspace.css";
import './access-administration.css';
import './valuation-workspace.css';
import './strategy-workspace.css';

export const metadata: Metadata = {
  title: "Operations Console",
  description: "Reference data and market-data operations workspace",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const store=await cookies();
  const stamp=contextFingerprint(store.get('local_access_session')?.value,store.get('active_tenant')?.value);
  return (
    <html lang="en" style={workspaceCssVariables}>
      <head><meta name="platform-page-context" content={stamp??''}/></head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
