import 'server-only';
import {getActiveTenantContext} from './tenant-session';
import {ReferenceApiError} from './reference-api-client';

/** Instrument adapters must never substitute the environment's demo tenant. */
export async function requireReferenceTenantContext() {
  try {return await getActiveTenantContext();}
  catch {throw new ReferenceApiError(401,'Select an active tenant before managing instruments.','ACTIVE_TENANT_REQUIRED');}
}
