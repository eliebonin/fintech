import { afterEach,expect,it,vi } from 'vitest';
const harness=vi.hoisted(()=>({slots:[] as any[],cursor:0,effects:[] as (()=>any)[],path:'/instruments/create'}));
vi.mock('next/navigation',()=>({usePathname:()=>harness.path}));
vi.mock('react',async original=>({...await original<typeof import('react')>(),useState:(initial:any)=>{const i=harness.cursor++;if(!(i in harness.slots))harness.slots[i]=initial;return [harness.slots[i],(value:any)=>{harness.slots[i]=value;}];},useEffect:(effect:()=>any)=>harness.effects.push(effect)}));
import { WorkspaceShell } from './workspace-shell';
function render(props:any={}) {harness.cursor=0;harness.effects=[];return WorkspaceShell({children:'content',...props});}
function sidebar(node:any):any {if(!node||typeof node!=='object')return;if(node.type?.name==='Sidebar')return node.props;for(const child of [node.props?.children].flat(Infinity)){const found=sidebar(child);if(found)return found;}}
const workspace={tenantId:'tenant',tenantName:'Selected tenant',tenantCode:'SELECTED',membershipRole:'TENANT_ADMIN',moduleCodes:['TRADING']};
afterEach(()=>{harness.slots=[];harness.path='/instruments/create';vi.unstubAllGlobals();});
it('does not show mock identity or module grants before workspace verification',()=>{const props=sidebar(render());expect(props.tenantName).toBeUndefined();expect(props.moduleCodes).toEqual([]);});
it('loads the selected workspace for legacy pages',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>workspace}));render();harness.effects[0]();await new Promise(resolve=>setTimeout(resolve,0));expect(sidebar(render()).tenantName).toBe('Selected tenant');expect(sidebar(render()).moduleCodes).toEqual(['TRADING']);});
it('rejects stale workspace results after navigation',async()=>{let finish:(value:any)=>void=()=>{};vi.stubGlobal('fetch',vi.fn(()=>new Promise(resolve=>{finish=resolve;})));render();const cleanup=harness.effects[0]();cleanup();harness.path='/reference-data/review/proposal';finish({ok:true,json:async()=>workspace});await new Promise(resolve=>setTimeout(resolve,0));expect(sidebar(render()).tenantName).toBeUndefined();});
it('uses explicit server-verified context without another request',()=>{const fetch=vi.fn();vi.stubGlobal('fetch',fetch);const props=sidebar(render({tenantName:workspace.tenantName,moduleCodes:workspace.moduleCodes,membershipRole:workspace.membershipRole}));harness.effects[0]();expect(fetch).not.toHaveBeenCalled();expect(props.tenantName).toBe(workspace.tenantName);});
it('keeps permissions empty when workspace lookup fails',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false}));render();harness.effects[0]();await new Promise(resolve=>setTimeout(resolve,0));expect(sidebar(render()).moduleCodes).toEqual([]);});
