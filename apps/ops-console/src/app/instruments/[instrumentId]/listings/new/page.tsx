import { notFound, redirect } from "next/navigation";

import NewEquityListingPage from "../../../listings/new/page";
import { getInstrument, MvpApiError } from "@/lib/mvp-api-client";
import { getActiveTenantContext } from "@/lib/tenant-session";

export const dynamic = "force-dynamic";

export default async function ContextualListingPage({ params }: { params: Promise<{ instrumentId: string }> }) {
  const { instrumentId } = await params;
  let context;
  try {
    context = await getActiveTenantContext();
  } catch {
    redirect("/select-tenant");
  }

  try {
    const response = await getInstrument(context, instrumentId);
    return <NewEquityListingPage initialInstrument={response.data} />;
  } catch (error) {
    if (error instanceof MvpApiError && error.status === 404) notFound();
    throw error;
  }
}
