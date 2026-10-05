import {describe,it,expect} from 'vitest';
import {freezeBookingSubmission,bookingSubmissionOptions} from './booking-submission';

describe('reviewed booking envelope',()=>{
  it('retains nested values and exact request bytes after the editable draft changes',()=>{
    const draft={quantity:'100.00',properties:[{definitionId:'field',value:false}],tags:['one']};
    const frozen=freezeBookingSubmission(draft,'retry-1','tenant-1');
    draft.quantity='200';draft.properties[0].value=true;draft.tags.push('two');
    const first=bookingSubmissionOptions(frozen),retry=bookingSubmissionOptions(frozen);
    expect(first.body).toBe('{"quantity":"100.00","properties":[{"definitionId":"field","value":false}],"tags":["one"]}');
    expect(retry).toEqual(first);
    expect(first.headers).toMatchObject({'Idempotency-Key':'retry-1','X-Expected-Tenant-Id':'tenant-1'});
    expect(()=>frozen.payload.properties.push({definitionId:'other',value:true})).toThrow();
  });
});
