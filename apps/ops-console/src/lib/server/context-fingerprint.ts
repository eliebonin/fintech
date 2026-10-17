import 'server-only';
import {createHash} from 'node:crypto';

/** Correlation of form intent, not authentication. Never expose the opaque cookies. */
export function contextFingerprint(session?:string,legacyTenant?:string):string|null{
 if(!session&&!legacyTenant)return null;
 return createHash('sha256').update(JSON.stringify([session??null,legacyTenant??null])).digest('hex');
}
