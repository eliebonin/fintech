import {afterEach,expect,it,vi} from 'vitest';
import {NextRequest} from 'next/server';
const h=vi.hoisted(()=>({select:vi.fn(),workspace:vi.fn(),sign:vi.fn()}));
vi.mock('@/lib/tenant-session',()=>({selectActiveTenant:h.select,getActiveTenantWorkspace:h.workspace,signActiveTenantId:h.sign}));
import {WorkspaceApiError} from '@/lib/server/workspace-errors';
import {POST,GET} from './route';
afterEach(()=>vi.resetAllMocks());
it('does not report cookie-signing configuration failure as tenant denial',async()=>{h.select.mockResolvedValue({tenantId:'t'});h.sign.mockImplementation(()=>{throw new Error('ACTIVE_TENANT_COOKIE_SECRET missing');});const response=await POST(new NextRequest('http://localhost/api/session/active-tenant',{method:'POST',body:JSON.stringify({tenantId:'t'})}));expect(response.status).toBe(503);expect(response.cookies.get('active_tenant')).toBeUndefined();});
it.each([403,503])('retains workspace failure status %s',async status=>{h.workspace.mockRejectedValue(new WorkspaceApiError(status));expect((await GET()).status).toBe(status);});
