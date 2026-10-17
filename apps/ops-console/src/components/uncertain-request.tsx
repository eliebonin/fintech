'use client';
/** Recovery is explicit: never automatically replay a write or release unknown intent. */
export function UncertainRequest({busy,onRetry}:{busy:boolean;onRetry:()=>void}){
 return <aside className="error-panel" role="status"><p>An earlier request has an unknown outcome. Retry its original payload unchanged, or inspect the relevant history in another tab before leaving. Editing the draft does not change the retained request.</p><button type="button" disabled={busy} onClick={onRetry}>Retry original request</button></aside>;
}
