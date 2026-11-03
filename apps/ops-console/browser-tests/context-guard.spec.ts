import {test,expect} from './console-check';
test('actual Next guard rejects an old tab after an HttpOnly actor-cookie switch',async({context,page})=>{
 test.setTimeout(90000); // First Next dev compilation is outside the five-second UI assertions.
 const url='http://127.0.0.1:3119';
 await context.addCookies([{name:'local_access_session',value:'synthetic-actor-a',url,httpOnly:true}]);
 // Unknown routes use the real root layout but never touch a financial API or database.
 const response=await page.goto(url+'/__synthetic_context_probe__',{waitUntil:'domcontentloaded'});
 expect(response?.headers()['x-content-type-options']).toBe('nosniff');
 expect(response?.headers()['content-security-policy']).toContain("'nonce-");
 await expect(page.locator('script[nonce]').first()).toBeAttached();
 const stamp=await page.locator('meta[name="platform-page-context"]').getAttribute('content');expect(stamp).toMatch(/^[a-f0-9]{64}$/);
 const send=()=>page.evaluate(async()=>{const stamp=document.querySelector<HTMLMetaElement>('meta[name="platform-page-context"]')!.content;const response=await fetch('/api/__synthetic_context_probe__',{method:'POST',headers:{'X-Page-Context':stamp}});return {status:response.status,text:await response.text()};});
 expect((await send()).status).toBe(404); // passed the guard; no handler exists
 await context.addCookies([{name:'local_access_session',value:'synthetic-actor-b',url,httpOnly:true}]);
 const result=await send();expect(result.status).toBe(409);expect(JSON.parse(result.text).error.code).toBe('TENANT_CONTEXT_CHANGED');
 expect(await page.locator('meta[name="platform-page-context"]').getAttribute('content')).toBe(stamp);
});
