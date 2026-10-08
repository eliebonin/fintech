'use client';

import {useState} from 'react';

export type BookingSearchItem = {
  id: string;
  instrumentId: string;
  label: string;
  description?: string;
  bookingEligible: boolean;
  readinessStatus?: string | null;
  ineligibilityMessage?: string | null;
};

const labels: Record<string,string> = {
  READY:'Ready to book', MISSING_CONFIGURATION:'Missing configuration',
  CREATION_ONLY:'Creation-only', INACTIVE:'Inactive', NOT_READY:'Not ready',
};

export function readinessLabel(item: BookingSearchItem): string {
  if (item.bookingEligible && (!item.readinessStatus || item.readinessStatus === 'READY')) return labels.READY;
  return item.readinessStatus !== 'READY' ? labels[item.readinessStatus ?? 'NOT_READY'] ?? labels.NOT_READY : labels.NOT_READY;
}

type Props = {
  items: BookingSearchItem[];
  loading: boolean;
  searched: boolean;
  total: number;
  hasMore?: boolean;
  onSelect: (id:string)=>void;
  onLoadMore: ()=>void;
  selectLabel?: string;
  loadMoreLabel?: string;
};

export function BookingSearchResults(props: Props) {
  const [showUnavailable,setShowUnavailable] = useState(false);
  return <ReadinessResults {...props} showUnavailable={showUnavailable} onShowUnavailable={setShowUnavailable}/>;
}

/** Controlled view keeps filtering, raw pagination and accessible counts together. */
export function ReadinessResults({items,loading,searched,total,onSelect,onLoadMore,showUnavailable,onShowUnavailable,
  selectLabel='Select instrument',loadMoreLabel='Load more matches',hasMore:rawHasMore}:Props & {
    showUnavailable:boolean; onShowUnavailable:(value:boolean)=>void;
  }) {
  const ready = items.filter(item=>readinessLabel(item) === labels.READY);
  const shown = showUnavailable ? items : ready;
  const hasMore = rawHasMore ?? items.length < total;
  return <section className="booking-readiness" aria-label="Booking readiness">
    <div className="booking-readiness-toolbar"><h2>Readiness</h2><label><input type="checkbox" checked={showUnavailable} onChange={e=>onShowUnavailable(e.target.checked)}/> Show unavailable</label></div>
    <p className="muted">Approval alone does not mean bookable. Readiness is checked again on selection and booking. Only references visible to this tenant are returned.</p>
    <p className="muted">Instrument readiness only: strategy, permissions and execution fields are checked separately.</p>
    <p role="status">{loading?'Checking readiness…':!searched?'Search to check booking readiness.':!items.length?
      (hasMore?'No visible matches in this loaded page. Load more to continue.':'No matching instruments.'):
      !ready.length&&!showUnavailable?'Matches found, but none of the loaded matches are ready to book. Show unavailable to inspect the reasons.':
      `${shown.length} shown · ${ready.length} ready · ${items.length-ready.length} unavailable in ${items.length} loaded matches.`}</p>
    {shown.length?<ul className="ticket-options">{shown.map(item=><li key={item.id}>
      <div><strong>{item.label}</strong>{item.description?<p className="muted">{item.description}</p>:null}
      <span className="quality">{readinessLabel(item)}</span>
      {readinessLabel(item)!==labels.READY?<p>{item.ineligibilityMessage??'Readiness has not been confirmed. Inspect the instrument configuration.'}</p>:null}</div>
      <div className="ticket-actions">{readinessLabel(item)===labels.READY?<button type="button" disabled={loading} onClick={()=>onSelect(item.id)}>{selectLabel}</button>:null}
      <a href={`/instruments/${encodeURIComponent(item.instrumentId)}`}>Inspect instrument</a></div>
    </li>)}</ul>:null}
    {searched&&hasMore?<button type="button" disabled={loading} onClick={onLoadMore}>{loadMoreLabel}</button>:null}
    {searched&&hasMore?<p className="muted">More matches have not been checked yet. Load more even if this page has no ready instruments.</p>:null}
  </section>;
}
