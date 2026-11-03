/** Forward safe admission metadata, never arbitrary upstream response headers. */
export function forwardWorkloadHeaders<T extends Response>(upstream:Response,result:T):T {
 const retry=upstream.headers.get('Retry-After');
 if([429,503].includes(upstream.status)&&retry&&/^\d{1,5}$/.test(retry)){
  result.headers.set('Retry-After',retry);result.headers.set('Cache-Control','no-store');
 }
 const id=upstream.headers.get('X-Request-ID');
 if(id&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id))result.headers.set('X-Request-ID',id);
 return result;
}
