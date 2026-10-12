export class SessionRequiredError extends Error {
  readonly code = "ACTIVE_TENANT_REQUIRED";
  readonly status = 401;
  constructor() { super("No active tenant has been selected"); this.name = "SessionRequiredError"; }
}
export class WorkspaceApiError extends Error {
  constructor(public readonly status: number) { super("Tenant workspace could not be loaded"); this.name = "WorkspaceApiError"; }
}
