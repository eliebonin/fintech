import 'server-only';
import {createReferenceApiClient} from 'api-contracts';
import {getActiveTenantContext} from './tenant-session';
import {referenceFetch} from './reference-fetch';

export async function pricingPolicyClient() {
 const context=await getActiveTenantContext();
 return createReferenceApiClient({baseUrl:process.env.REFERENCE_API_URL??'http://localhost:8000',
   fetch:referenceFetch((input,init)=>{
     const headers=new Headers(init?.headers??(input instanceof Request?input.headers:undefined));
     headers.set('X-Tenant-Id',context.tenantId);headers.set('X-User-Account-Id',context.userAccountId);
     return fetch(input,{...init,headers});
   })});
}
