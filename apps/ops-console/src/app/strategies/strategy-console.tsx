"use client";
import {browserFetch as fetch} from '@/lib/browser-fetch';

import { FormEvent, useState } from "react";
import Link from 'next/link';
import {StrategyRegister} from '@/components/strategy-register';
import type {TenantContext} from '@/lib/tenant-types';

export type Strategy = { strategyId: string; strategyCode: string; displayName: string; strategyType: string; baseCurrencyCode?: string | null; status: string };
const strategyTypes = ["AMC_MANDATE", "FUND", "MANAGED_ACCOUNT", "PROP_SLEEVE", "MODEL_PORTFOLIO", "OTHER"];

export function StrategyConsole({ initialStrategies, canWrite,accessGroups=[],createOnly=false,writeContext }: { initialStrategies: Strategy[]; canWrite: boolean;createOnly?:boolean;writeContext?:Pick<TenantContext,'tenantId'|'userAccountId'>;accessGroups?:Array<{groupId:string;name:string;scopeMode:string}> }) {
  const [strategies, setStrategies] = useState(initialStrategies);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [success,setSuccess]=useState('');
  const [blocked,setBlocked]=useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if(blocked||saving)return;
    if(!writeContext){setBlocked(true);setError('Reopen this form to confirm its tenant and user before saving.');return;}
    setSaving(true); setError("");setSuccess('');
    const form = event.currentTarget;
    const values = new FormData(form); const payload:Record<string,unknown> = Object.fromEntries(values.entries());
    payload.initialAccessGroupIds=values.getAll('initialAccessGroupIds');
    if (payload.strategyType !== "OTHER") delete payload.operatingModelLabel;
    if (!payload.baseCurrencyCode) delete payload.baseCurrencyCode;
    try {
    const response = await fetch("/api/strategies", { method: "POST", headers: { "Content-Type": "application/json",
      'X-Expected-Tenant-Id':writeContext.tenantId,'X-Expected-User-Id':writeContext.userAccountId }, body: JSON.stringify(payload) }); const result = await response.json();
    if (!response.ok) {
      if([401,403].includes(response.status)||['TENANT_CONTEXT_CHANGED','WRITE_CONTEXT_REQUIRED'].includes(result?.error?.code))setBlocked(true);
      setError(result?.error?.message ?? result?.detail ?? "Strategy could not be created."); return;
    }
    setStrategies((current) => [result.data, ...current]); form.reset();setSuccess(`${result.data.displayName} was created. Its visibility follows the selected access groups.`);
    }catch{setError('The outcome could not be confirmed. Check the strategy register before submitting again.');}finally{setSaving(false);}
  }
  if(!createOnly)return <StrategyRegister strategies={strategies} canCreate={canWrite}/>;
  return <main className="mvp-page">
    <header className="mvp-header"><div><Link href="/strategies">← Strategies</Link><h1>Create strategy</h1><p className="muted">Classify the strategy and choose its initial access groups.</p></div><span className="synthetic-badge">TENANT SCOPED</span></header>
    {success?<p role="status" className="strategy-notice">{success} <Link href="/strategies">View strategy register</Link></p>:null}
    {canWrite ? <form className="strategy-form" onSubmit={submit}>
      <h2>Create strategy</h2><label>Code<input name="strategyCode" required maxLength={100} placeholder="ALPHA_GBP" /></label><label>Display name<input name="displayName" required maxLength={250} placeholder="Alpha GBP Fund" /></label>
      <label>Type<select name="strategyType" defaultValue="FUND">{strategyTypes.map(type=><option key={type}>{type}</option>)}</select></label><label>Base currency<input name="baseCurrencyCode" maxLength={3} placeholder="GBP" /></label><label>Other model label<input name="operatingModelLabel" maxLength={250} placeholder="Required only for OTHER" /></label>
      <fieldset disabled={saving}><legend>Initial strategy access</legend><p className="access-hint">All-strategy groups already include this new strategy. Choose any additional selected-scope groups below. Creating a strategy does not automatically grant you operational access.</p>
        {accessGroups.filter(group=>group.scopeMode==='SELECTED').map(group=><label className="access-check" key={group.groupId}><input type="checkbox" name="initialAccessGroupIds" value={group.groupId}/>{group.name}</label>)}
        {!accessGroups.some(group=>group.scopeMode==='SELECTED')?<p>No additional selected-scope groups available.</p>:null}
      </fieldset>
      <button type="submit" disabled={saving||blocked||!writeContext}>{saving?'Creating…':'Create strategy'}</button>{error?<p className="strategy-error" role="alert">{error}</p>:null}
      {blocked?<p>This attempt was blocked. Check the strategy register for any earlier uncertain attempt. <a href="/strategies/new">Reload creation page for the selected context</a>. Copy any details you want to keep before reloading.</p>:null}
    </form>:<div className="error-panel">Create-strategy permission is required. Editing or archiving existing strategies is a separate permission.</div>}
  </main>;
}
