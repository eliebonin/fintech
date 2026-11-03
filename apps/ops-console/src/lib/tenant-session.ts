import "server-only";
import { apiRead } from "./server/api-read";
import { SessionRequiredError, WorkspaceApiError } from "./server/workspace-errors";

import { cookies } from "next/headers";
import {requireLocalMode} from './server/local-identity';

import type { TenantContext } from "./tenant-types";

export type ActiveTenantWorkspace = {
  tenantId: string;
  tenantCode: string;
  tenantName: string;
  membershipRole: string;
  moduleCodes: string[];
  platformRole?: string | null;
  permissionCodes?: string[];
  tenantModuleCodes?: string[];
  userName?: string;
  actorId?: string;
};

async function selectedSession():Promise<ActiveTenantWorkspace&{userId:string}> {
  requireLocalMode();
  const token = (await cookies()).get('local_access_session')?.value;
  if (!token) throw new SessionRequiredError();
  const response = await apiRead(new URL('/v1/local-session',process.env.REFERENCE_API_URL ?? 'http://localhost:8000'),{
    headers:{'X-Local-Access-Token':token},cache:'no-store',redirect:'error',
  });
  if (!response.ok) throw new WorkspaceApiError(response.status);
  const selected = await response.json() as ActiveTenantWorkspace&{userId:string};
  if (!selected.tenantId||!selected.userId) throw new SessionRequiredError();
  return selected;
}

/** Only an API-verified opaque session establishes the current user/tenant. */
export async function getActiveTenantContext(): Promise<TenantContext> {
  const selected=await selectedSession();
  return {tenantId:selected.tenantId,userAccountId:selected.userId,source:'local-session'};
}

export async function getActiveTenantWorkspace(selectedContext?: TenantContext): Promise<ActiveTenantWorkspace> {
  const selected=await selectedSession();
  if(selectedContext&&(selectedContext.tenantId!==selected.tenantId||selectedContext.userAccountId!==selected.userId))throw new WorkspaceApiError(403);
  return selected;
}
