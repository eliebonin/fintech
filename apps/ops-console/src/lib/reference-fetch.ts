import { apiRead } from "./server/api-read";
/** A timeout is an uncertain write outcome, never permission to auto-retry. */
export function referenceFetch(fetchImpl:typeof fetch=fetch):typeof fetch {
  return async (input,init)=>{
    const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
    if (method === "GET" || method === "HEAD") return apiRead(input, init, fetchImpl);
    const { forwardLocalSession } = await import('./server/local-session-forward');
    init = await forwardLocalSession(input,init);
    const callerSignal=init?.signal??(input instanceof Request?input.signal:undefined);
    return fetchImpl(input,{...init,signal:callerSignal
      ?AbortSignal.any([callerSignal,AbortSignal.timeout(35000)])
      :AbortSignal.timeout(35000)});
  };
}
