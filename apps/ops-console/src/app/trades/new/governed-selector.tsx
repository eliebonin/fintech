"use client";
import { useRef, useState } from "react";
import { configurationRequest, type CatalogueRecord } from "@/lib/trade-configuration-client";

export function GovernedSelector({tenantId, catalogueId, id, label, value, displayValue, required, description, validationError, onSelect}: {tenantId: string; catalogueId: string; id: string; label: string; value: string; displayValue?: string; required: boolean; description?: string; validationError?: string; onSelect: (id: string, label: string) => void}) {
  const [query, setQuery] = useState(""), [options, setOptions] = useState<CatalogueRecord[]>([]), [error, setError] = useState(""), [loading, setLoading] = useState(false), [offset, setOffset] = useState(0), [searched, setSearched] = useState(false), [hasNext, setHasNext] = useState(false);
  const sequence = useRef(0), searchInput = useRef<HTMLInputElement>(null);
  const describedBy = `${id}-help${validationError ? ` ${id}-error` : ""}`;
  async function search(page = 0) {
    const serial = ++sequence.current;
    setLoading(true); setError(""); setSearched(false);
    try {
      const found = await configurationRequest<CatalogueRecord[]>(tenantId, `catalogues/${catalogueId}/records?q=${encodeURIComponent(query)}&offset=${page}&limit=26`);
      if (serial === sequence.current) { setOptions(found.slice(0,25)); setHasNext(found.length > 25); setOffset(page); setSearched(true); }
    } catch (e) { if (serial === sequence.current) { setOptions([]); setError(e instanceof Error ? e.message : "Catalogue search failed."); } }
    finally { if (serial === sequence.current) setLoading(false); }
  }
  return <div className="ticket-governed" id={id} tabIndex={-1} role="group" aria-labelledby={`${id}-label`} aria-describedby={describedBy}>
    <span className="ticket-property-label" id={`${id}-label`}>{label} <span className="ticket-property-rule">{required ? "(required)" : "(optional)"}</span></span>
    <small className="ticket-property-type">Governed dropdown</small>
    <p className="ticket-property-hint" id={`${id}-help`}>{description}</p>
    {validationError ? <p className="ticket-property-message" id={`${id}-error`}>{validationError}</p> : null}
    <div className="ticket-governed-selection" role="status">{value ? <><strong>{displayValue || "Catalogue entry selected"}</strong><button type="button" aria-label={`Clear ${label}`} onClick={() => { onSelect("", ""); searchInput.current?.focus(); }}>Clear value</button></> : <span>No value selected.</span>}</div>
    <label className="ticket-governed-search-label" htmlFor={`${id}-search`}>Search {label}</label>
    <div className="ticket-governed-search"><input ref={searchInput} id={`${id}-search`} type="search" aria-describedby={describedBy} aria-invalid={!!validationError} placeholder="Entry code or label" value={query} maxLength={250} onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); void search(); } }} onChange={e => { sequence.current++; setQuery(e.target.value); setOptions([]); setOffset(0); setLoading(false); setSearched(false); setError(""); }} /><button type="button" disabled={loading} onClick={() => void search()}>{loading ? "Searching…" : "Search values"}</button></div>
    {loading ? <p role="status">Searching the catalogue…</p> : null}
    {searched ? <div className="ticket-governed-results"><p role="status">{options.length ? `Showing ${offset+1}–${offset+options.length}. Select an entry below.` : "No matching published entries. Try another code or label."}</p><ul aria-label={`${label} search results`}>{options.map(option => <li key={option.recordVersionId}><button type="button" aria-pressed={value === option.recordVersionId} onClick={() => { onSelect(option.recordVersionId, `${option.code} — ${option.label}`); setOptions([]); setSearched(false); searchInput.current?.focus(); }}><strong>{option.label}</strong><small>{option.code}{value === option.recordVersionId ? " · Selected" : ""}</small></button></li>)}</ul>{offset > 0 || hasNext ? <div className="ticket-governed-paging"><button type="button" disabled={loading || offset === 0} onClick={() => void search(Math.max(0, offset-25))}>Previous values</button><button type="button" disabled={loading || !hasNext} onClick={() => void search(offset+25)}>Next values</button></div> : null}</div> : null}
    {error ? <p className="ticket-property-message" role="alert">{error}</p> : null}
  </div>;
}
