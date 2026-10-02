"use client";
import { useRef, type ReactNode } from "react";
import type { ConfiguredProperty } from "@/lib/trade-configuration-client";
import { sections, tabDestination, typeLabel, recordStatusLabel, type Section } from "./configuration-model";

export function SectionTabs({ current, disabled, onChange }: { current: Section; disabled: boolean; onChange: (s: Section) => void }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  return <div role="tablist" aria-label="Trade configuration sections" className="configuration-tabs">{sections.map((section, index) => <button key={section} type="button" role="tab" id={`configuration-tab-${index}`} aria-controls={`configuration-panel-${index}`} aria-selected={current === section} tabIndex={current === section ? 0 : -1} disabled={disabled} ref={element => { refs.current[index] = element; }} onClick={() => onChange(section)} onKeyDown={event => {
    const next = tabDestination(index, event.key); if (next === null) return;
    // Manual activation avoids loading the audit section while arrowing past it.
    event.preventDefault(); refs.current[next]?.focus();
  }}>{section}</button>)}</div>;
}
export function Panel({ section, current, children }: { section: Section; current: Section; children: ReactNode }) {
  const index = sections.indexOf(section);
  return <section role="tabpanel" id={`configuration-panel-${index}`} aria-labelledby={`configuration-tab-${index}`} hidden={current !== section} tabIndex={0} className="configuration-panel">{children}</section>;
}
export function Status({ value, catalogueStatus }: { value: string; catalogueStatus?: string }) {
  const style = value === "ACTIVE" && catalogueStatus && catalogueStatus !== "ACTIVE" ? catalogueStatus : value;
  return <span className={`configuration-status status-${style.toLowerCase()}`}>{catalogueStatus ? recordStatusLabel(value, catalogueStatus) : value === "ACTIVE" ? "Published" : value === "RETIRED" ? "Retired" : "Draft"}</span>;
}
export function Empty({ title, children }: { title: string; children: ReactNode }) { return <div className="configuration-empty"><h3>{title}</h3><p>{children}</p></div>; }
export function Pager({ offset, count, next, busy, label, total, onPage }: { offset: number; count: number; next: boolean; busy: boolean; label: string; total?: number; onPage: (n: number) => void }) {
  return <nav aria-label={`${label} pagination`} className="configuration-pagination"><span>{count ? `${offset + 1}–${offset + count}${total === undefined ? "" : ` of ${total}`}` : "0 results"} · Page {Math.floor(offset / 25) + 1}</span><div><button type="button" disabled={busy || offset === 0} onClick={() => onPage(Math.max(0, offset - 25))}>Previous {label}</button><button type="button" disabled={busy || !next} onClick={() => onPage(offset + 25)}>Next {label}</button></div></nav>;
}
export function TextFields({ initial, fixedCode = false, prefix }: { initial?: { code?: string; label?: string; description?: string | null }; fixedCode?: boolean; prefix: string }) {
  return <div className="configuration-form-grid"><label htmlFor={`${prefix}-label`}>Display label<input id={`${prefix}-label`} name="label" required maxLength={250} defaultValue={initial?.label} autoFocus /></label><label htmlFor={`${prefix}-code`}>Stable code<input id={`${prefix}-code`} name="code" required maxLength={100} pattern="[A-Za-z][A-Za-z0-9_]*" defaultValue={initial?.code} readOnly={fixedCode} aria-describedby={`${prefix}-code-help`} /><small id={`${prefix}-code-help`}>{fixedCode ? "This code identifies the same business meaning across versions." : "Start with a letter. Use letters, numbers and underscores."}</small></label><label htmlFor={`${prefix}-description`} className="configuration-wide">Business definition<textarea id={`${prefix}-description`} name="description" required maxLength={2000} defaultValue={initial?.description ?? ""} /><small>Explain what this means and when it should be used.</small></label></div>;
}
export function Reason({ id }: { id: string }) { return <label htmlFor={id}>Change reason<textarea id={id} name="reason" required maxLength={2000} /><small>This reason is recorded in the configuration audit.</small></label>; }
export function FieldRegister({ fields, busy, onEdit, onValues }: { fields: ConfiguredProperty[]; busy: boolean; onEdit: (f: ConfiguredProperty) => void; onValues: (f: ConfiguredProperty) => void }) {
  if (!fields.length) return <Empty title="No fields match">Clear the filters, include retired definitions, or add your first field.</Empty>;
  return <div className="configuration-table-scroll"><table><caption className="configuration-sr-only">Trade field definitions</caption><thead><tr><th scope="col">Field</th><th scope="col">Value type</th><th scope="col">Booking rule</th><th scope="col">Version</th><th scope="col">Actions</th></tr></thead><tbody>{fields.map(f => <tr key={f.definitionId}><th scope="row"><span>{f.label}</span><code>{f.code}</code>{f.description ? <details><summary>Definition</summary><p>{f.description}</p></details> : null}</th><td>{typeLabel(f.valueType)}{f.catalogueId ? <button type="button" className="configuration-link" disabled={busy} onClick={() => onValues(f)} aria-label={`Manage values for ${f.label}`}>Manage values →</button> : null}</td><td>{f.required ? "Required" : "Optional"}</td><td><Status value={f.status} /><small>Version {f.versionNo}</small></td><td>{f.status === "ACTIVE" && f.valueType !== "CHOICE" ? <button type="button" disabled={busy} onClick={() => onEdit(f)} aria-label={`Edit definition for ${f.label}`}>Edit definition</button> : <span className="muted">History only</span>}</td></tr>)}</tbody></table></div>;
}
