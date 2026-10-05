/** Reviewed payloads are isolated from mutable drafts and retained across uncertain outcomes. */
export type FrozenBookingSubmission<T>={payload:T;key:string;expectedTenantId:string};

function freezeTree(value:unknown):void {
  if(value&&typeof value==='object'&&!Object.isFrozen(value)){
    Object.freeze(value);
    for(const child of Object.values(value))freezeTree(child);
  }
}

export function freezeBookingSubmission<T>(payload:T,key:string,expectedTenantId:string):FrozenBookingSubmission<T> {
  const snapshot=structuredClone(payload);
  freezeTree(snapshot);
  return Object.freeze({payload:snapshot,key,expectedTenantId});
}

export function bookingSubmissionOptions<T>(envelope:FrozenBookingSubmission<T>):RequestInit {
  return {method:'POST',cache:'no-store',headers:{Accept:'application/json','Content-Type':'application/json',
    'Idempotency-Key':envelope.key,'X-Expected-Tenant-Id':envelope.expectedTenantId},body:JSON.stringify(envelope.payload)};
}
