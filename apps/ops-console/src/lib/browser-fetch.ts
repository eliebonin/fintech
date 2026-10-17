/** Same-origin browser transport. The fingerprint is not a credential or permission grant. */
export const browserFetch:typeof globalThis.fetch=async(input,init)=>{
 if(typeof document==='undefined'||typeof window==='undefined')return globalThis.fetch(input,init);
 const url=new URL(input instanceof Request?input.url:String(input),window.location.href);
 const method=(init?.method??(input instanceof Request?input.method:'GET')).toUpperCase();
 if(url.origin!==window.location.origin||!url.pathname.startsWith('/api/')||['GET','HEAD','OPTIONS'].includes(method))return globalThis.fetch(input,init);
 const headers=new Headers(init?.headers??(input instanceof Request?input.headers:undefined));
 const stamp=document.querySelector<HTMLMetaElement>('meta[name="platform-page-context"]')?.content;
 if(stamp)headers.set('X-Page-Context',stamp);
 return globalThis.fetch(input,{...init,headers});
};
