import 'server-only';
import {WorkspaceApiError} from './workspace-errors';

/** APP_ENV describes deployment trust; NODE_ENV only describes the JS build. */
export function requireLocalMode(): void {
 if(!['local','test','development'].includes(process.env.APP_ENV??''))throw new WorkspaceApiError(503);
}

export function localOperatorKey(): string {
 requireLocalMode();
 const key=process.env.LOCAL_ACCESS_OPERATOR_KEY??'';
 if(key.length<32||/\s/u.test(key))throw new Error('LOCAL_ACCESS_OPERATOR_KEY must be configured by scripts/configure_local_access.py');
 return key;
}
