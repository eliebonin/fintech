import type { ReactNode } from "react";
import Link from "next/link";

/** Common heading for native forms that share the console's visual language. */
export function WorkspacePageHeader({ title, eyebrow, children, backHref, backLabel }: {
  title: string;
  eyebrow: string;
  children?: ReactNode;
  backHref: string;
  backLabel: string;
}) {
  return <header className="mvp-header workspace-page-header">
    <div>
      <Link className="workspace-back-link" href={backHref}>{backLabel}</Link>
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      {children}
    </div>
  </header>;
}
