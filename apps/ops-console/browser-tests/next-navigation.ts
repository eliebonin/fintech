/** Test-only router adapter for mounted product components in the Vite harness. */
export function useRouter(){return {push:(href:string)=>window.dispatchEvent(new CustomEvent('fixture-navigation',{detail:href})),refresh:()=>{},replace:(href:string)=>window.history.replaceState(null,'',href),back:()=>window.history.back()};}
export function usePathname(){return window.location.pathname;}
export function useSearchParams(){return new URLSearchParams(window.location.search);}
