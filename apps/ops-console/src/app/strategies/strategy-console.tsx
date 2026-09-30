"use client";

import { FormEvent, useState } from "react";

type Strategy = { strategyId: string; strategyCode: string; displayName: string; strategyType: string; baseCurrencyCode?: string | null; status: string };
const strategyTypes = ["AMC_MANDATE", "FUND", "MANAGED_ACCOUNT", "PROP_SLEEVE", "MODEL_PORTFOLIO", "OTHER"];

export function StrategyConsole({ initialStrategies, canWrite }: { initialStrategies: Strategy[]; canWrite: boolean }) {
  const [strategies, setStrategies] = useState(initialStrategies);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError("");
    const form = event.currentTarget;
    const values = new FormData(form); const payload = Object.fromEntries(values.entries());
    if (payload.strategyType !== "OTHER") delete payload.operatingModelLabel;
    if (!payload.baseCurrencyCode) delete payload.baseCurrencyCode;
    const response = await fetch("/api/strategies", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); const result = await response.json();
    if (!response.ok) { setError(result?.error?.message ?? result?.detail ?? "Strategy could not be created."); setSaving(false); return; }
    setStrategies((current) => [result.data, ...current]); form.reset(); setSaving(false);
  }
  return <main className="mvp-page"><header className="mvp-header"><div><p className="eyebrow">TENANT STRATEGY REGISTER</p><h1>Strategies</h1><p className="muted">Create and classify the funds, mandates, managed accounts, sleeves, and models in this tenant.</p></div><span className="synthetic-badge">TENANT SCOPED</span></header>{canWrite ? <form className="strategy-form" onSubmit={submit}><h2>Create strategy</h2><label>Code<input name="strategyCode" required maxLength={100} placeholder="ALPHA_GBP" /></label><label>Display name<input name="displayName" required maxLength={250} placeholder="Alpha GBP Fund" /></label><label>Type<select name="strategyType" defaultValue="FUND">{strategyTypes.map((type) => <option key={type}>{type}</option>)}</select></label><label>Base currency<input name="baseCurrencyCode" maxLength={3} placeholder="GBP" /></label><label>Other model label<input name="operatingModelLabel" maxLength={250} placeholder="Required only for OTHER" /></label><button type="submit" disabled={saving}>{saving ? "Creating…" : "Create strategy"}</button>{error ? <p className="strategy-error">{error}</p> : null}</form> : <div className="error-panel">Your active tenant membership can view strategies but cannot create or archive them.</div>}<section className="table-wrap"><table><thead><tr><th>Code</th><th>Name</th><th>Operating model</th><th>Base currency</th><th>Status</th></tr></thead><tbody>{strategies.length ? strategies.map((strategy) => <tr key={strategy.strategyId}><td><strong>{strategy.strategyCode}</strong></td><td>{strategy.displayName}</td><td>{strategy.strategyType}</td><td>{strategy.baseCurrencyCode ?? "—"}</td><td><span className="quality quality-accepted">{strategy.status}</span></td></tr>) : <tr><td colSpan={5} className="empty-table">No strategies have been created for this tenant.</td></tr>}</tbody></table></section></main>;
}
