import {expect,it} from 'vitest';
import {parseApiErrorResponse} from './api-errors';
it('explains a permission denial while retaining code and support correlation',async()=>{
 const error=await parseApiErrorResponse(Response.json({error:{code:'TENANT_ACTION_FORBIDDEN',message:'Forbidden',correlationId:'denial-123',retryable:true}},{status:403}),'Could not create');
 expect(error.status).toBe(403);expect(error.code).toBe('TENANT_ACTION_FORBIDDEN');expect(error.correlationId).toBe('denial-123');
 expect(error.message).toMatch(/tenant.*(role|access)/i);expect(error.message).toMatch(/administrator/i);expect(error.retryable).toBe(false);
});
it('asks for tenant selection when a session is absent',async()=>{
 const error=await parseApiErrorResponse(Response.json({error:{code:'ACTIVE_TENANT_REQUIRED',message:'HTTP401'}},{status:401}),'Could not create');
 expect(error.message).toMatch(/select.*tenant/i);expect(error.retryable).toBe(false);
});
it('retains actionable validation errors rather than replacing all failures with permissions',async()=>{
 const error=await parseApiErrorResponse(Response.json({error:{message:'Par amount must be positive',fieldErrors:{parAmount:['Must be positive']}}},{status:422}),'Could not create');
 expect(error.message).toBe('Par amount must be positive');expect(error.fieldErrors).toEqual({parAmount:['Must be positive']});
});
