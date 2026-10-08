import 'server-only';
import {NextRequest,NextResponse} from 'next/server';
import {getActiveTenantContext} from './tenant-session';
import type {TenantContext} from './tenant-types';

type BookingWriteResult={response:NextResponse;context?:never;payload?:never;key?:never}|
  {response?:never;context:TenantContext;payload:Record<string,unknown>;key:string};

export async function readBookingWrite(request:NextRequest,legacyCash=false):Promise<BookingWriteResult> {
  const fail=(status:number,code:string,message?:string):BookingWriteResult=>({response:NextResponse.json({error:{code,...(message?{message}:{})}},{status})});
  const key=request.headers.get('Idempotency-Key')?.trim();
  if(!key)return fail(400,'IDEMPOTENCY_KEY_REQUIRED','Idempotency-Key is required.');
  const expected=request.headers.get('X-Expected-Tenant-Id');
  if(!legacyCash&&!expected)return fail(400,'EXPECTED_TENANT_REQUIRED','Reopen the ticket to confirm its tenant context.');
  let payload:unknown;
  try{payload=await request.json();}catch{return fail(400,'INVALID_JSON','Request body must be valid JSON.');}
  if(!payload||typeof payload!=='object'||Array.isArray(payload))return fail(400,'INVALID_JSON','Request body must be a JSON object.');
  let context:TenantContext;
  try{context=await getActiveTenantContext();}catch{return fail(401,'ACTIVE_TENANT_REQUIRED');}
  if(expected&&expected!==context.tenantId)return fail(409,'TENANT_CONTEXT_CHANGED','The active tenant changed. Restart the ticket before booking.');
  const enriched=['correction','properties','tagIds','traderPersonId','executingBrokerOrganisationId','tradePurpose','marketActivity','externalReferences'].some(field=>field in payload);
  if(legacyCash&&enriched&&!expected)return fail(400,'EXPECTED_TENANT_REQUIRED','Reopen the ticket to confirm its tenant context.');
  return {context,payload:payload as Record<string,unknown>,key};
}
