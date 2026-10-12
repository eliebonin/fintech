import "server-only";
import { getActiveTenantContext, getActiveTenantWorkspace, type ActiveTenantWorkspace } from "../tenant-session";
import type { TenantContext } from "../tenant-types";
import { SessionRequiredError, WorkspaceApiError } from "./workspace-errors";
export type WorkspaceAccess =
  | { kind: "ready"; context: TenantContext; workspace: ActiveTenantWorkspace }
  | { kind: "session-required" }
  | { kind: "forbidden" }
  | { kind: "unavailable" };
export async function resolveWorkspaceAccess(): Promise<WorkspaceAccess> {
  let context: TenantContext;
  try { context = await getActiveTenantContext(); }
  catch (error) { if (error instanceof SessionRequiredError) return { kind: "session-required" }; throw error; }
  try { return { kind: "ready", context, workspace: await getActiveTenantWorkspace(context) }; }
  catch (error) {
    if (error instanceof WorkspaceApiError && [401, 403].includes(error.status)) return { kind: "forbidden" };
    return { kind: "unavailable" };
  }
}
