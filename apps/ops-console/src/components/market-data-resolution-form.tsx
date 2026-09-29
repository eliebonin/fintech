"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { buildOneSubjectResolutionRequest } from "@/lib/market-data-resolution";

export function MarketDataResolutionForm({ subjectReferenceNodeId }: { subjectReferenceNodeId: string }) {
  const router = useRouter();
  const [error, setError] = useState("");
  async function submit(formData: FormData) {
    setError("");
    const localCut = String(formData.get("marketDataAsOfUtc"));
    const response = await fetch("/api/market-data/resolution-snapshots", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(buildOneSubjectResolutionRequest(subjectReferenceNodeId, { valuationPolicyId: String(formData.get("valuationPolicyId")), valuationDate: String(formData.get("valuationDate")), valuationCutId: String(formData.get("valuationCutId")), marketDataAsOfUtc: `${localCut}:00Z`, usePurpose: "VALUATION" })) });
    if (!response.ok) { setError("Resolution could not be created."); return; }
    const snapshot = await response.json() as { marketDataResolutionSnapshotId: string };
    router.push(`/market-data/resolution-snapshots/${snapshot.marketDataResolutionSnapshotId}`);
  }
  return <form className="date-form" action={submit}><label>Policy ID <input required name="valuationPolicyId" /></label><label>Cut ID <input required name="valuationCutId" /></label><label>Valuation date <input required type="date" name="valuationDate" defaultValue="2026-08-28" /></label><label>Information cut (UTC) <input required type="datetime-local" name="marketDataAsOfUtc" defaultValue="2026-08-28T16:00" /></label><button type="submit">Freeze resolution evidence</button>{error ? <span className="error-panel">{error}</span> : null}</form>;
}
