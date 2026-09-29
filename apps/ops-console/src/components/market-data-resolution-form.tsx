"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { activePolicyCutId, activePolicyCutLabel, activePolicyLabel, buildOneSubjectResolutionRequest, type ActiveValuationPolicy } from "@/lib/market-data-resolution";

export function MarketDataResolutionForm({ subjectReferenceNodeId }: { subjectReferenceNodeId: string }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [valuationDate, setValuationDate] = useState("2026-08-28");
  const [policies, setPolicies] = useState<ActiveValuationPolicy[]>([]);
  const [valuationPolicyId, setValuationPolicyId] = useState("");
  const selectedPolicy = policies.find((policy) => policy.valuationPolicyId === valuationPolicyId);
  const valuationCutId = activePolicyCutId(policies, valuationPolicyId);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/market-data/valuation-policies?valuationDate=${encodeURIComponent(valuationDate)}`)
      .then(async (response) => response.ok ? await response.json() as ActiveValuationPolicy[] : Promise.reject())
      .then((availablePolicies) => {
        if (cancelled) return;
        setPolicies(availablePolicies);
        setValuationPolicyId((selected) => availablePolicies.some((policy) => policy.valuationPolicyId === selected) ? selected : (availablePolicies[0]?.valuationPolicyId ?? ""));
      })
      .catch(() => { if (!cancelled) { setPolicies([]); setValuationPolicyId(""); setError("Active valuation policies could not be loaded."); } });
    return () => { cancelled = true; };
  }, [valuationDate]);

  async function submit(formData: FormData) {
    setError("");
    const localCut = String(formData.get("marketDataAsOfUtc"));
    if (!valuationCutId) { setError("Select an active valuation policy."); return; }
    const response = await fetch("/api/market-data/resolution-snapshots", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(buildOneSubjectResolutionRequest(subjectReferenceNodeId, { valuationPolicyId, valuationDate, valuationCutId, marketDataAsOfUtc: `${localCut}:00Z`, usePurpose: "VALUATION" })) });
    if (!response.ok) { setError("Resolution could not be created."); return; }
    const snapshot = await response.json() as { marketDataResolutionSnapshotId: string };
    router.push(`/market-data/resolution-snapshots/${snapshot.marketDataResolutionSnapshotId}`);
  }
  return <form className="date-form" action={submit}><label>Valuation date <input required type="date" name="valuationDate" value={valuationDate} onChange={(event) => setValuationDate(event.target.value)} /></label><label>Active valuation policy <select required value={valuationPolicyId} onChange={(event) => setValuationPolicyId(event.target.value)} disabled={!policies.length}><option value="">{policies.length ? "Choose policy" : "No active policies"}</option>{policies.map((policy) => <option key={policy.valuationPolicyId} value={policy.valuationPolicyId}>{activePolicyLabel(policy)}</option>)}</select></label><label>Policy cut <output>{selectedPolicy ? activePolicyCutLabel(selectedPolicy) : "—"}</output></label><label>Information cut (UTC) <input required type="datetime-local" name="marketDataAsOfUtc" defaultValue="2026-08-28T16:00" /></label><button type="submit" disabled={!valuationCutId}>Freeze resolution evidence</button>{error ? <span className="error-panel">{error}</span> : null}</form>;
}
