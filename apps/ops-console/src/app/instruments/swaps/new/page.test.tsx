import {beforeEach,expect,it,vi} from 'vitest';
const h=vi.hoisted(()=>({context:vi.fn(),workspace:vi.fn()}));
vi.mock('@/lib/tenant-session',()=>({getActiveTenantContext:h.context,getActiveTenantWorkspace:h.workspace}));
vi.mock('next/navigation',()=>({redirect:(path:string)=>{throw new Error(`redirect:${path}`);}}));
import NewSwapPage from './page';
beforeEach(()=>{h.context.mockReset().mockResolvedValue({tenantId:'selected',userAccountId:'actor'});h.workspace.mockReset().mockResolvedValue({tenantName:'Selected tenant',membershipRole:'TENANT_ADMIN',moduleCodes:['TRADING']});});
it('passes the selected tenant to creation within the existing workspace shell',async()=>{
  const page=await NewSwapPage();expect(page.props.tenantName).toBe('Selected tenant');
  expect(page.props.children.props.children.at(-1).props.tenantId).toBe('selected');
});
it('enforces tenant-admin and trading access and missing-session redirection',async()=>{
  h.workspace.mockResolvedValue({membershipRole:'TRADER',moduleCodes:['TRADING']});await expect(NewSwapPage()).rejects.toThrow('redirect:/instruments');
  h.workspace.mockResolvedValue({membershipRole:'TENANT_ADMIN',moduleCodes:[]});await expect(NewSwapPage()).rejects.toThrow('redirect:/instruments');
  h.context.mockRejectedValue(new Error('No session'));await expect(NewSwapPage()).rejects.toThrow('redirect:/select-tenant');
});
