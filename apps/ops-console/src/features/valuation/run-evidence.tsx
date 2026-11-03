import type {Detail} from './types';
import {displayTime} from './presentation';
import {TechnicalReference} from './technical-reference';

/** Already returned operational evidence only; never selects or recalculates inputs. */
export function RunEvidence({detail,status}:{detail:Detail;status:string}){
 return <section className="pnl-surface pnl-audit" aria-label="Run evidence and operational log">
  <h3>Operational log</h3><p>Recorded attempt: {status}</p>
  <TechnicalReference id={detail.attempt.correlation_id} label="Correlation ID"/>
  {detail.events.length?<ol className="pnl-event-list">{detail.events.map(event=><li key={event.event_id}><strong>{event.stage} · {event.event_code}</strong><time>{displayTime(event.recorded_at)}</time><details><summary>Technical details (JSON)</summary><pre>{JSON.stringify(event.details,null,2)}</pre></details></li>)}</ol>:<p>No operational events were returned for this attempt.</p>}
  <details><summary>Calculation scope and limitations</summary><p>Only reviewed basic share-ratio events are replayed. Other corporate transformations are not enabled. Cash FX is always assessed using daily opening balances and EoD movement treatment. Missing cash is disclosed and does not by itself block publication; required nonzero market inputs and all financial/review checks still apply. Provider comparison is NOT_COMPARED unless independently performed.</p></details>
 </section>;
}
