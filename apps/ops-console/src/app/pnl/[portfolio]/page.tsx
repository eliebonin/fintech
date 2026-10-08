import { redirect } from "next/navigation";

/** Old bookmarks must not resurrect demo aliases or their local-tenant fallback. */
export default async function RetiredPortfolioPnlPage() {
  redirect("/valuation");
}
