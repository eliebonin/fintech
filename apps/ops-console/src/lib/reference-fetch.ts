/** A timeout is an uncertain write outcome, never permission to auto-retry. */
export function referenceFetch(fetchImpl:typeof fetch=fetch):typeof fetch {
  return (input,init)=>{
    const callerSignal=init?.signal??(input instanceof Request?input.signal:undefined);
    return fetchImpl(input,{...init,signal:callerSignal
      ?AbortSignal.any([callerSignal,AbortSignal.timeout(35000)])
      :AbortSignal.timeout(35000)});
  };
}
