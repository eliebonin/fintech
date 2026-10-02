"use client";
import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { configurationRequest as request, type Catalogue, type CatalogueRecord, type ConfiguredProperty, type Selection } from "@/lib/trade-configuration-client";
import { fieldPage, fieldTypes, selectionDelta, type Section } from "./configuration-model";
import { Empty, FieldRegister, Pager, Panel, Reason, SectionTabs, Status, TextFields } from "./configuration-ui";

type Event = { eventId: string; action: string; reason: string; actorId: string; recordedAtUtc: string };
type Confirmation = { title: string; impact: string; reason: boolean; returnId: string; run: (reason: string) => Promise<void> };
const roles = { COUNTERPARTY: "Counterparties", EXECUTING_BROKER: "Executing brokers", TRADER: "Traders" };
type Role = keyof typeof roles;
function data(form: HTMLFormElement) { return Object.fromEntries(new FormData(form).entries()) as Record<string, string>; }

export function TradeConfigurationConsole({ tenantId }: { tenantId: string }) {
  const [tab, setTab] = useState<Section>("Custom fields");
  const [error, setError] = useState(""), [notice, setNotice] = useState(""), [busy, setBusy] = useState(false);
  const working = useRef(false), errorRef = useRef<HTMLDivElement>(null), confirmRef = useRef<HTMLHeadingElement>(null), returnFocus = useRef<string | null>(null);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [loading, setLoading] = useState(true), [loadFailed, setLoadFailed] = useState(false);
  const [fields, setFields] = useState<ConfiguredProperty[]>([]), [fieldQuery, setFieldQuery] = useState(""), [fieldType, setFieldType] = useState(""), [fieldHistory, setFieldHistory] = useState(false), [fieldOffset, setFieldOffset] = useState(0);
  const [fieldEditor, setFieldEditor] = useState(false), [replacement, setReplacement] = useState<ConfiguredProperty | null>(null), [kind, setKind] = useState("TEXT"), [required, setRequired] = useState(false), [chosenSource, setChosenSource] = useState("");
  const [catalogues, setCatalogues] = useState<Catalogue[]>([]), [sources, setSources] = useState<Record<string, Catalogue>>({}), [catalogueOffset, setCatalogueOffset] = useState(0), [catalogueQuery, setCatalogueQuery] = useState(""), [catalogueSearch, setCatalogueSearch] = useState("");
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null), [catalogueEditor, setCatalogueEditor] = useState(false);
  const [records, setRecords] = useState<CatalogueRecord[]>([]), [recordOffset, setRecordOffset] = useState(0), [recordQuery, setRecordQuery] = useState(""), [recordSearch, setRecordSearch] = useState(""), [history, setHistory] = useState(false);
  const [recordEditor, setRecordEditor] = useState(false), [correction, setCorrection] = useState<CatalogueRecord | null>(null);
  const [role, setRole] = useState<Role>("COUNTERPARTY"), [selection, setSelection] = useState<Selection | null>(null), [eligibilityEditor, setEligibilityEditor] = useState(false);
  const [selected, setSelected] = useState<{ id: string; label: string }[]>([]), [candidates, setCandidates] = useState<{ id: string; label: string }[]>([]), [query, setQuery] = useState(""), [selectedQuery, setSelectedQuery] = useState(""), [searched, setSearched] = useState(false);
  const [events, setEvents] = useState<Event[]>([]), [eventOffset, setEventOffset] = useState(0), [auditLoading, setAuditLoading] = useState(false);
  const blocked = busy || !!confirmation;
  const page = fieldPage(fields, fieldQuery, fieldType, fieldHistory, fieldOffset);
  const delta = selectionDelta(selection?.records ?? [], selected);

  useEffect(() => { if (error) errorRef.current?.focus(); }, [error]);
  useEffect(() => { if (confirmation) confirmRef.current?.focus(); else if (returnFocus.current) { document.getElementById(returnFocus.current)?.focus(); returnFocus.current = null; } }, [confirmation]);
  function changeTab(next: Section) { setTab(next); setNotice(""); setError(""); }
  async function perform(action: () => Promise<void>, success?: string) {
    if (working.current) return false;
    working.current = true; setBusy(true); setError(""); setNotice("");
    try { await action(); if (success) setNotice(success); return true; }
    catch (e) { setError(e instanceof Error ? e.message : "Request failed. Your changes have not been confirmed."); return false; }
    finally { working.current = false; setBusy(false); }
  }
  async function refreshFields() { setFields(await request<ConfiguredProperty[]>(tenantId, "properties")); }
  function remember(items: Catalogue[]) { setSources(current => ({ ...current, ...Object.fromEntries(items.map(c => [c.catalogueId, c])) })); }
  async function refreshCatalogues(offset = catalogueOffset, q = catalogueSearch) {
    const items = await request<Catalogue[]>(tenantId, `catalogues?limit=26&offset=${offset}&q=${encodeURIComponent(q)}`);
    setCatalogues(items); remember(items); setCatalogueOffset(offset); setCatalogueSearch(q);
  }
  async function refreshRecords(current = catalogue, offset = recordOffset, q = recordSearch, all = history) {
    if (!current) return;
    setRecords(await request<CatalogueRecord[]>(tenantId, `catalogues/${current.catalogueId}/records?limit=26&offset=${offset}&q=${encodeURIComponent(q)}&history=${all}`));
    setRecordOffset(offset); setRecordSearch(q); setHistory(all);
  }
  async function openCatalogue(current: Catalogue) {
    await refreshRecords(current, 0, "", current.status !== "ACTIVE");
    setCatalogue(current); remember([current]); setRecordQuery(""); setCorrection(null); setRecordEditor(false); setCatalogueEditor(false); setTab("Reference catalogues");
  }
  async function openFieldCatalogue(f: ConfiguredProperty) {
    if (f.catalogueId) await perform(async () => openCatalogue(await request<Catalogue>(tenantId, `catalogues/${f.catalogueId}`)));
  }
  async function editField(f: ConfiguredProperty) {
    await perform(async () => {
      if (f.catalogueId) remember([await request<Catalogue>(tenantId, `catalogues/${f.catalogueId}`)]);
      setReplacement(f); setKind(f.valueType); setRequired(f.required); setChosenSource(f.catalogueId ?? ""); setFieldEditor(true);
    });
  }
  function newField() { setReplacement(null); setKind("TEXT"); setRequired(false); setChosenSource(""); setFieldEditor(true); setError(""); setNotice(""); }
  function cancelConfirmation() { returnFocus.current = confirmation?.returnId ?? null; setConfirmation(null); }
  async function loadWorkspace() {
    setLoading(true); setLoadFailed(false);
    try { const [f, c] = await Promise.all([request<ConfiguredProperty[]>(tenantId, "properties"), request<Catalogue[]>(tenantId, "catalogues?limit=26")]); setFields(f); setCatalogues(c); remember(c); }
    catch (e) { setLoadFailed(true); throw e; }
    finally { setLoading(false); }
  }
  useEffect(() => {
    let active = true;
    Promise.all([request<ConfiguredProperty[]>(tenantId, "properties"), request<Catalogue[]>(tenantId, "catalogues?limit=26")]).then(([f, c]) => {
      if (active) { setFields(f); setCatalogues(c); remember(c); }
    }).catch(e => { if (active) { setError(e.message); setLoadFailed(true); } }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [tenantId]);
  useEffect(() => {
    let active = true;
    request<Selection>(tenantId, `selections/${role}`).then(s => { if (active) { setSelection(s); setSelected(s.records); } }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [tenantId, role]);
  useEffect(() => {
    if (tab !== "Audit history") return;
    let active = true; setAuditLoading(true);
    request<Event[]>(tenantId, `audit?offset=${eventOffset}`).then(e => { if (active) setEvents(e); }).catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setAuditLoading(false); });
    return () => { active = false; };
  }, [tenantId, tab, eventOffset]);
  async function createField(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const v = data(event.currentTarget);
    await perform(async () => {
      await request(tenantId, replacement ? `properties/${replacement.definitionId}/replace` : "properties", { code: v.code, label: v.label, description: v.description, valueType: kind, catalogueId: kind === "REFERENCE" ? chosenSource : null, required, acknowledgeRequiredImpact: v.acknowledge === "on" });
      await refreshFields(); setFieldEditor(false); setReplacement(null);
    }, "Field published. Existing trade history is unchanged.");
  }
  async function createCatalogue(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const v = data(event.currentTarget);
    await perform(async () => { const created = await request<Catalogue>(tenantId, "catalogues", v); await refreshCatalogues(); await openCatalogue(created); }, "Draft catalogue created. Add entries, then publish it for booking.");
  }
  async function saveRecord(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!catalogue) return; const v = data(event.currentTarget);
    await perform(async () => {
      await request(tenantId, correction ? `catalogues/${catalogue.catalogueId}/records/${correction.recordVersionId}/correct` : `catalogues/${catalogue.catalogueId}/records`, correction ? { label: v.label, description: v.description, reason: v.reason } : v);
      await refreshRecords(); setRecordEditor(false); setCorrection(null);
    }, catalogue.status === "DRAFT" ? "Entry saved. It becomes selectable when the catalogue is published." : "Entry published. Existing trades retain their original record version.");
  }
  function catalogueAction(action: "publish" | "retire") {
    if (!catalogue) return;
    setConfirmation({ title: action === "publish" ? `Publish ${catalogue.label}?` : `Retire ${catalogue.label}?`, impact: action === "publish" ? "Published entries become available to fields using this catalogue." : "Retirement blocks future selection. First retire or replace every active field using this catalogue. Historical trades stay unchanged.", reason: true, returnId: `catalogue-${action}`, run: async reason => {
      const saved = await request<Catalogue>(tenantId, `catalogues/${catalogue.catalogueId}/${action}`, { reason });
      setCatalogue(saved); remember([saved]); await refreshCatalogues(); await refreshRecords(saved, 0, "", saved.status !== "ACTIVE");
    } });
  }

  return <main className="mvp-page configuration-page"><div className="configuration-workspace">
    <header className="mvp-header"><div><Link href="/tenant-profile" className="configuration-back">← Tenant profile</Link><p className="eyebrow">TENANT GOVERNANCE</p><h1>Trade configuration</h1><p className="muted">Define the information your team can attach to a trade.</p></div><span className="synthetic-badge">TENANT SCOPED</span></header>
    <div className="configuration-overview"><div><strong>{loading || loadFailed ? "—" : fields.filter(f => f.status === "ACTIVE").length}</strong><span>Active custom fields</span></div><div><strong>{loading || loadFailed ? "—" : fields.filter(f => f.status === "ACTIVE" && f.required).length}</strong><span>Required at booking</span></div><p>Changes apply to future bookings.<br />Historical trade values are preserved.</p></div>
    <SectionTabs current={tab} disabled={blocked} onChange={changeTab} />
    {error ? <div ref={errorRef} tabIndex={-1} role="alert" className="configuration-error"><h2>There is a problem</h2><p>{error}</p><p>Review your inputs before retrying. A completed publication may need a refresh.</p><button type="button" disabled={busy} onClick={() => void perform(loadWorkspace)}>Reload configuration</button></div> : null}
    {notice ? <p role="status" className="configuration-notice">{notice}</p> : null}
    {confirmation ? <section className="configuration-confirm" aria-labelledby="configuration-confirm-title"><h2 id="configuration-confirm-title" ref={confirmRef} tabIndex={-1}>{confirmation.title}</h2><p>{confirmation.impact}</p><form onSubmit={event => { event.preventDefault(); const reason = data(event.currentTarget).reason ?? ""; void perform(async () => { await confirmation.run(reason); setConfirmation(null); }, "Change confirmed. Historical trade values are unchanged."); }}><fieldset disabled={busy}>{confirmation.reason ? <Reason id="confirmation-reason" /> : null}<label className="configuration-check"><input type="checkbox" required />I understand the impact on future bookings.</label><div className="configuration-form-actions"><button className="configuration-primary">{busy ? "Confirming…" : "Confirm change"}</button><button type="button" onClick={cancelConfirmation}>Cancel</button></div></fieldset></form></section> : null}

    <Panel section="Custom fields" current={tab}><fieldset className="configuration-controls" disabled={blocked}>
      <div className="configuration-section-heading"><div><h2>Custom trade fields</h2><p className="muted">Add typed fields or dropdowns backed by a governed catalogue.</p></div>{!fieldEditor ? <button className="configuration-primary" type="button" disabled={loading || loadFailed} onClick={newField}>Add field</button> : null}</div>
      {fieldEditor ? <div className="configuration-editor"><header><p className="eyebrow">{replacement ? `NEW VERSION · ${replacement.code}` : "NEW CUSTOM FIELD"}</p><h3>{replacement ? `Edit ${replacement.label}` : "Add a trade field"}</h3><p>{replacement ? "Publishing a replacement preserves the previous definition for existing trades. A different business meaning needs a new code." : "Use a stable code and a business-friendly label. There are no preallocated field slots."}</p></header>
        <form key={replacement?.definitionId ?? "new-field"} onSubmit={createField}><TextFields initial={replacement ?? undefined} fixedCode={!!replacement} prefix="field" />
          <label htmlFor="field-type">Value type<select id="field-type" value={kind} onChange={e => setKind(e.target.value)}>{Object.entries(fieldTypes).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          {kind === "REFERENCE" ? <div className="configuration-source"><label htmlFor="field-source">Published catalogue<select id="field-source" required value={chosenSource} onChange={e => setChosenSource(e.target.value)}><option value="">Choose a catalogue</option>{Object.values(sources).filter(c => c.status === "ACTIVE").map(c => <option key={c.catalogueId} value={c.catalogueId}>{c.label} · {c.code}</option>)}</select></label><p>Values are maintained in the catalogue, not on each trade.</p><button type="button" onClick={() => { setCatalogue(null); setTab("Reference catalogues"); }}>Find or create a catalogue</button><small>Your field draft stays here while you manage catalogues.</small></div> : null}
          <label className="configuration-check"><input type="checkbox" checked={required} onChange={e => setRequired(e.target.checked)} />Required for every new trade</label>
          {required ? <div className="configuration-impact"><p>Every new booking must provide this value. Existing trades are unaffected.</p><label className="configuration-check"><input name="acknowledge" type="checkbox" required />I acknowledge this booking requirement.</label></div> : null}
          <div className="configuration-form-actions"><button className="configuration-primary">{busy ? "Publishing…" : replacement ? "Publish new version" : "Publish field"}</button><button type="button" onClick={() => { setFieldEditor(false); setReplacement(null); }}>Cancel</button></div>
        </form>
        {replacement ? <div className="configuration-danger-zone"><h4>Stop using this field</h4><p>Retire it for future bookings; keep all historical definitions and values.</p><button id="field-retire" type="button" className="configuration-danger" onClick={() => setConfirmation({ title: `Retire ${replacement.label}?`, impact: "New trades will no longer request this field. Existing values remain readable and unchanged.", reason: false, returnId: "field-retire", run: async () => { await request(tenantId, `properties/${replacement.definitionId}/retire`, {}); await refreshFields(); setFieldEditor(false); setReplacement(null); } })}>Retire field</button></div> : null}
      </div> : null}
      {!fieldEditor ? <><div className="configuration-toolbar"><label htmlFor="field-search">Search fields<input id="field-search" type="search" value={fieldQuery} placeholder="Label, code or definition" onChange={e => { setFieldQuery(e.target.value); setFieldOffset(0); }} /></label><label htmlFor="field-filter">Value type<select id="field-filter" value={fieldType} onChange={e => { setFieldType(e.target.value); setFieldOffset(0); }}><option value="">All types</option>{Object.entries(fieldTypes).map(([value, label]) => <option key={value} value={value}>{label}</option>)}{fieldHistory ? <option value="CHOICE">Legacy dropdown</option> : null}</select></label><label className="configuration-check"><input type="checkbox" checked={fieldHistory} onChange={e => { setFieldHistory(e.target.checked); if (!e.target.checked && fieldType === "CHOICE") setFieldType(""); setFieldOffset(0); }} />Include retired definitions</label></div>
      {loading ? <p role="status">Loading trade fields…</p> : loadFailed ? <Empty title="Fields could not be loaded">Use Reload configuration above to try again.</Empty> : <><FieldRegister fields={page.items} busy={blocked} onEdit={f => void editField(f)} onValues={f => void openFieldCatalogue(f)} /><Pager offset={page.offset} count={page.items.length} total={page.total} next={page.offset + 25 < page.total} busy={blocked} label="fields" onPage={setFieldOffset} /></>}</> : null}
    </fieldset></Panel>

    <Panel section="Standard fields" current={tab}><fieldset className="configuration-controls" disabled={blocked}>
      <div className="configuration-section-heading"><div><h2>Standard trade fields</h2><p className="muted">Choose which canonical records this tenant may select.</p></div></div>
      <p className="configuration-hint">Curating an eligible list does not grant login access or constitute credit approval.</p>
      <div className="configuration-role-cards">{Object.entries(roles).map(([value, label]) => <button key={value} type="button" disabled={eligibilityEditor && role !== value} aria-pressed={role === value} onClick={() => { if (role === value) return; setRole(value as Role); setSelection(null); setSelected([]); setCandidates([]); setEligibilityEditor(false); setQuery(""); setSelectedQuery(""); setSearched(false); }}><strong>{label}</strong><small>{value === "TRADER" ? "Eligible tenant members" : "Canonical organisations"}</small></button>)}</div>
      {eligibilityEditor ? <p className="muted">Publish or discard this draft before switching standard fields.</p> : null}
      {selection ? <><div className="configuration-section-heading"><div><h3>{roles[role]}</h3><p>{selection.mode === "LEGACY" ? "Shared eligibility · no tenant-curated list published" : `Tenant-curated list · version ${selection.versionNo} · ${selection.records.length} records`}</p></div>{!eligibilityEditor ? <button className="configuration-primary" type="button" onClick={() => { setSelected(selection.records); setEligibilityEditor(true); }}>{selection.mode === "LEGACY" ? "Set up eligible list" : "Edit eligible list"}</button> : null}</div>
        {selection.mode === "LEGACY" ? <p className="configuration-impact">New bookings currently use active shared organisations or eligible tenant members. Publishing a curated list restricts future selection to that list.</p> : null}
        {!eligibilityEditor && selection.mode === "CURATED" && selection.records.length ? <details className="configuration-eligible-preview"><summary>View {selection.records.length} eligible records</summary><label htmlFor="eligible-preview-search">Filter eligible records<input id="eligible-preview-search" value={selectedQuery} onChange={e => setSelectedQuery(e.target.value)} /></label><ul className="configuration-record-list">{selection.records.filter(c => c.label.toLocaleLowerCase().includes(selectedQuery.trim().toLocaleLowerCase())).map(c => <li key={c.id}>{c.label}</li>)}</ul></details> : null}
        {eligibilityEditor ? <div className="configuration-editor"><h3>Edit eligible {roles[role].toLowerCase()}</h3><p>Draft changes are not applied until you publish. {delta.added} added · {delta.removed} removed.</p>
          <div className="configuration-selection-grid"><div><h4>Find canonical records</h4><form className="configuration-toolbar" onSubmit={e => { e.preventDefault(); void perform(async () => { setCandidates(await request(tenantId, `candidates/${role}?curated=false&q=${encodeURIComponent(query)}`)); setSearched(true); }); }}><label htmlFor="candidate-search">Search records<input id="candidate-search" value={query} maxLength={250} onChange={e => setQuery(e.target.value)} /></label><button>Search</button></form>
            <ul className="configuration-record-list">{candidates.map(c => <li key={c.id}><span>{c.label}</span><button type="button" disabled={selected.some(s => s.id === c.id)} onClick={() => setSelected(current => [...current, c])} aria-label={`Add ${c.label}`}>{selected.some(s => s.id === c.id) ? "Added" : "Add"}</button></li>)}</ul>{searched && !candidates.length ? <p>No canonical records match. Try a different search.</p> : null}{candidates.length >= 100 ? <p>Showing up to 100 matches. Refine your search to find more.</p> : null}</div>
          <div><h4>Draft list · {selected.length} selected</h4><label htmlFor="selected-search">Filter selected records<input id="selected-search" value={selectedQuery} onChange={e => setSelectedQuery(e.target.value)} /></label><ul className="configuration-record-list">{selected.filter(c => c.label.toLocaleLowerCase().includes(selectedQuery.trim().toLocaleLowerCase())).map(c => <li key={c.id}><span>{c.label}</span><button type="button" onClick={() => setSelected(current => current.filter(s => s.id !== c.id))} aria-label={`Remove ${c.label}`}>Remove</button></li>)}</ul>{!selected.length ? <p>No records selected.</p> : null}</div></div>
          <form onSubmit={e => { e.preventDefault(); const v = data(e.currentTarget); void perform(async () => { const saved = await request<Selection>(tenantId, `selections/${role}`, { ids: selected.map(s => s.id), expectedVersion: selection.versionNo, reason: v.reason }); setSelection(saved); setSelected(saved.records); setEligibilityEditor(false); }, "Eligible list published for future bookings."); }}>
            {!selected.length ? <p className="configuration-impact">Publishing an empty list disables selection for this optional field.</p> : null}<Reason id="eligibility-reason" /><label className="configuration-check"><input type="checkbox" required />I acknowledge the effect on new bookings.</label><div className="configuration-form-actions"><button className="configuration-primary" disabled={selection.mode !== "LEGACY" && !delta.changed}>Publish eligible list</button><button type="button" onClick={() => { setSelected(selection.records); setEligibilityEditor(false); }}>Discard draft</button></div></form>
        </div> : selection.mode === "CURATED" && !selection.records.length ? <Empty title="Selection disabled">This tenant has published an empty eligible list.</Empty> : null}
      </> : <div><p role="status">Loading eligibility…</p><button type="button" onClick={() => void perform(async () => { const s = await request<Selection>(tenantId, `selections/${role}`); setSelection(s); setSelected(s.records); })}>Retry eligibility</button></div>}
    </fieldset></Panel>

    <Panel section="Reference catalogues" current={tab}><fieldset className="configuration-controls" disabled={blocked}>
      {!catalogue ? <><div className="configuration-section-heading"><div><h2>Reference catalogues</h2><p className="muted">Curate reusable dropdown values for your custom fields.</p></div>{!catalogueEditor ? <button className="configuration-primary" type="button" disabled={loading || loadFailed} onClick={() => setCatalogueEditor(true)}>Add catalogue</button> : null}</div>
        {catalogueEditor ? <div className="configuration-editor"><h3>Add a catalogue</h3><p>Create a draft, add its values, then publish it for booking.</p><form onSubmit={createCatalogue}><TextFields prefix="catalogue" /><Reason id="catalogue-reason" /><div className="configuration-form-actions"><button className="configuration-primary">Create draft catalogue</button><button type="button" onClick={() => setCatalogueEditor(false)}>Cancel</button></div></form></div> : null}
        <form className="configuration-toolbar" onSubmit={e => { e.preventDefault(); void perform(() => refreshCatalogues(0, catalogueQuery)); }}><label htmlFor="catalogue-search">Search catalogues<input id="catalogue-search" value={catalogueQuery} placeholder="Label or code" maxLength={250} onChange={e => setCatalogueQuery(e.target.value)} /></label><button>Search</button></form>
        {loading ? <p role="status">Loading catalogues…</p> : loadFailed ? <Empty title="Catalogues could not be loaded">Reload configuration to try again.</Empty> : catalogues.length ? <div className="configuration-table-scroll"><table><caption className="configuration-sr-only">Tenant reference catalogues</caption><thead><tr><th scope="col">Catalogue</th><th scope="col">Status</th><th scope="col">Actions</th></tr></thead><tbody>{catalogues.slice(0, 25).map(c => <tr key={c.catalogueId}><th scope="row">{c.label}<code>{c.code}</code></th><td><Status value={c.status} /></td><td><button type="button" onClick={() => void perform(() => openCatalogue(c))} aria-label={`Manage ${c.label}`}>Manage values</button></td></tr>)}</tbody></table></div> : <Empty title="No catalogues found">Try another search or add a catalogue for your first dropdown.</Empty>}
        <Pager offset={catalogueOffset} count={Math.min(catalogues.length, 25)} next={catalogues.length > 25} busy={blocked || loading} label="catalogues" onPage={offset => void perform(() => refreshCatalogues(offset))} />
      </> : <><button type="button" className="configuration-back" onClick={() => { setCatalogue(null); setRecordEditor(false); }}>← All catalogues</button><div className="configuration-section-heading"><div><p className="eyebrow">{catalogue.code}</p><h2>{catalogue.label}</h2><p className="muted">{catalogue.description}</p></div><Status value={catalogue.status} /></div>
        <div className="configuration-catalogue-actions">{catalogue.status === "DRAFT" ? <button id="catalogue-publish" className="configuration-primary" type="button" onClick={() => catalogueAction("publish")}>Publish catalogue</button> : null}{catalogue.status === "ACTIVE" ? <button type="button" onClick={() => { setChosenSource(catalogue.catalogueId); setKind("REFERENCE"); if (!fieldEditor) { setReplacement(null); setRequired(false); } setFieldEditor(true); setTab("Custom fields"); }}>Use for a trade field</button> : null}{catalogue.status !== "RETIRED" ? <button id="catalogue-retire" type="button" className="configuration-danger" onClick={() => catalogueAction("retire")}>Retire catalogue</button> : null}</div>
        <p className="configuration-hint">{catalogue.status === "DRAFT" ? "Draft values are not selectable on trades. Add entries below, then publish the catalogue." : catalogue.status === "RETIRED" ? "Read-only history. Retired catalogues cannot be republished." : "Correct labels without changing meaning. For a new meaning, retire the entry and add a new code."}</p>
        <div className="configuration-section-heading"><h3>Catalogue entries</h3>{catalogue.status !== "RETIRED" && !recordEditor ? <button className="configuration-primary" type="button" onClick={() => { setCorrection(null); setRecordEditor(true); }}>Add entry</button> : null}</div>
        {recordEditor ? <div className="configuration-editor"><h3>{correction ? `Correct ${correction.label}` : "Add a catalogue entry"}</h3>{correction ? <p>This creates a new version of the same meaning. Booked trades retain the previous label.</p> : null}<form key={correction?.recordVersionId ?? "new-record"} onSubmit={saveRecord}><TextFields initial={correction ?? undefined} fixedCode={!!correction} prefix="entry" /><Reason id="entry-reason" /><label className="configuration-check"><input type="checkbox" required />{correction ? "The business meaning is unchanged." : "This entry is ready for selection when the catalogue is published."}</label><div className="configuration-form-actions"><button className="configuration-primary">{correction ? "Publish corrected version" : catalogue.status === "DRAFT" ? "Save draft catalogue entry" : "Publish entry"}</button><button type="button" onClick={() => { setRecordEditor(false); setCorrection(null); }}>Cancel</button></div></form></div> : null}
        <form className="configuration-toolbar" onSubmit={e => { e.preventDefault(); void perform(() => refreshRecords(catalogue, 0, recordQuery)); }}><label htmlFor="entry-search">Search entries<input id="entry-search" value={recordQuery} maxLength={250} placeholder="Label or code" onChange={e => setRecordQuery(e.target.value)} /></label><label className="configuration-check"><input type="checkbox" checked={history} onChange={e => { const checked = e.target.checked; void perform(() => refreshRecords(catalogue, 0, recordSearch, checked)); }} />Include retired entry versions</label><button>Search</button></form>
        {records.length ? <div className="configuration-table-scroll"><table><caption className="configuration-sr-only">Catalogue entry versions</caption><thead><tr><th scope="col">Entry</th><th scope="col">Version</th><th scope="col">Actions</th></tr></thead><tbody>{records.slice(0, 25).map(r => <tr key={r.recordVersionId}><th scope="row">{r.label}<code>{r.code}</code></th><td><Status value={r.status} catalogueStatus={catalogue.status} /><small>Version {r.versionNo}</small></td><td>{r.status === "ACTIVE" && catalogue.status !== "RETIRED" ? <div className="configuration-row-actions"><button type="button" disabled={recordEditor} onClick={() => { setCorrection(r); setRecordEditor(true); }} aria-label={`Correct label for ${r.label}`}>Correct label</button><button id={`retire-${r.recordVersionId}`} disabled={recordEditor} className="configuration-danger" type="button" aria-label={`Retire entry ${r.label}`} onClick={() => setConfirmation({ title: `Retire ${r.label}?`, impact: "New trades can no longer select this entry. Booked trades retain its original value and version.", reason: true, returnId: `retire-${r.recordVersionId}`, run: async reason => { await request(tenantId, `catalogues/${catalogue.catalogueId}/records/${r.recordVersionId}/retire`, { reason }); await refreshRecords(); } })}>Retire</button></div> : <span className="muted">History only</span>}</td></tr>)}</tbody></table></div> : <Empty title="No entries found">Try a different search, include historical versions, or add an entry.</Empty>}
        <Pager offset={recordOffset} count={Math.min(records.length, 25)} next={records.length > 25} busy={blocked} label="entries" onPage={offset => void perform(() => refreshRecords(catalogue, offset))} />
      </>}
    </fieldset></Panel>

    <Panel section="Audit history" current={tab}><fieldset className="configuration-controls" disabled={blocked || auditLoading}><div className="configuration-section-heading"><div><h2>Configuration audit history</h2><p className="muted">Publication, correction and retirement events for this tenant.</p></div><button type="button" onClick={() => void perform(async () => setEvents(await request(tenantId, `audit?offset=${eventOffset}`)))}>Refresh audit</button></div>
      {auditLoading ? <p role="status">Loading audit history…</p> : events.length ? <ol className="configuration-audit">{events.map(e => <li key={e.eventId}><div><h3>{e.action.toLowerCase().replaceAll("_", " ")}</h3><time dateTime={e.recordedAtUtc}>{new Date(e.recordedAtUtc).toLocaleString("en-GB", { timeZone: "Europe/London" })} · London</time></div><p>{e.reason}</p><details><summary>Actor and event identifiers</summary><p>Actor: <code>{e.actorId}</code></p><p>Event: <code>{e.eventId}</code></p></details></li>)}</ol> : <Empty title="No audit events on this page">Configuration changes will appear here after publication.</Empty>}
      <Pager offset={eventOffset} count={events.length} next={events.length === 25} busy={blocked || auditLoading} label="events" onPage={setEventOffset} />
    </fieldset></Panel>
  </div></main>;
}
