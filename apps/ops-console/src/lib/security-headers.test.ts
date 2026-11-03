import {afterEach,expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';
vi.mock('server-only',()=>({}));
import {proxy} from '../proxy';

afterEach(()=>vi.unstubAllEnvs());
it('gives HTML fresh script nonces and baseline protections',()=>{
 vi.stubEnv('NODE_ENV','production');
 const a=proxy(new NextRequest('http://localhost/select-context'));
 const b=proxy(new NextRequest('http://localhost/select-context'));
 const policy=a.headers.get('Content-Security-Policy')??'';
 expect(policy).toContain("'nonce-");expect(policy).not.toContain('unsafe-eval');
 expect(policy.split('script-src')[1]?.split(';')[0]).not.toContain('unsafe-inline');
 expect(policy).not.toBe(b.headers.get('Content-Security-Policy'));
 expect(a.headers.get('X-Content-Type-Options')).toBe('nosniff');
 expect(a.headers.get('X-Frame-Options')).toBe('SAMEORIGIN');
 expect(a.headers.get('Referrer-Policy')).toBe('strict-origin-when-cross-origin');
 expect(policy).not.toContain('upgrade-insecure-requests');
 expect(a.headers.get('Strict-Transport-Security')).toBeNull();
});
it('retains dev compilation and protects rejected stale writes too',()=>{
 vi.stubEnv('NODE_ENV','development');
 const page=proxy(new NextRequest('http://localhost/select-context'));
 expect(page.headers.get('Content-Security-Policy')).toContain('unsafe-eval');
 const rejected=proxy(new NextRequest('http://localhost/api/strategies',{method:'POST'}));
 expect(rejected.status).toBe(409);expect(rejected.headers.get('X-Content-Type-Options')).toBe('nosniff');
});
it('uses HSTS for HTTPS deployments without pinning HTTP localhost',()=>{
 vi.stubEnv('NODE_ENV','production');
 const response=proxy(new NextRequest('https://example.test/valuation'));
 expect(response.headers.get('Strict-Transport-Security')).toBe('max-age=31536000');
 expect(response.headers.get('Content-Security-Policy')).toContain('upgrade-insecure-requests');
});
