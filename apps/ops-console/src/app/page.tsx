export const dynamic = "force-dynamic";

import { searchInstruments } from "@/lib/instrument-data";
import { OperationsConsole } from "@/components/operations-console";
import { resolveLocalTenantContext } from "@/lib/tenant-context";
import { searchReferenceInstruments } from "@/lib/reference-api-client";
import { getWorkQueue, type WorkQueuePayload } from "@/lib/work-queue";

export default async function HomePage() {
  let initialResults = searchInstruments("");
  let initialSource = "synthetic-fixture";
  let initialQueue: WorkQueuePayload | undefined;
  const tenantContext = resolveLocalTenantContext();
  try {
    const response = await searchReferenceInstruments("", tenantContext);
    initialResults = response.data;
    initialSource = response.meta.source;
  } catch {
    // The BFF remains the authoritative interactive path; local fixture mode
    // keeps the shell usable when the API process is not running.
  }
  try {
    initialQueue = await getWorkQueue(tenantContext);
  } catch {
    // The client island will request the BFF queue and show its local fallback.
  }
  return <OperationsConsole initialResults={initialResults} initialSource={initialSource} initialQueue={initialQueue} />;
}
