import {afterEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({workspace:vi.fn()}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantWorkspace:h.workspace}));
import {WorkspaceApiError} from '@/lib/server/workspace-errors';
import {POST,GET} from './route';
afterEach(()=>vi.resetAllMocks());
it('retired selection never creates an identity cookie',async()=>{const response=await POST();expect(response.status).toBe(410);expect(response.cookies.get('active_tenant')).toBeUndefined();});
it.each([403,503])('retains workspace failure status %s',async status=>{h.workspace.mockRejectedValue(new WorkspaceApiError(status));expect((await GET()).status).toBe(status);});
