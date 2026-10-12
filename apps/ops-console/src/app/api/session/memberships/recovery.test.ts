import {afterEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
vi.mock('next/headers',()=>({cookies:async()=>({get:()=>undefined})}));
import {GET} from './route';
afterEach(()=>vi.unstubAllGlobals());
it('returns recoverable service failure when memberships cannot be reached',async()=>{vi.stubGlobal('fetch',async()=>{throw new TypeError('fetch failed');});const response=await GET();expect(response.status).toBe(503);expect((await response.json()).error.code).toBe('MEMBERSHIPS_UNAVAILABLE');});
