import {it,expect} from 'vitest';
import {withProposalRetry,confirmProposalRetry,rejectProposalRetry,type ProposalRetry} from './proposal-retry';
import {BffApiError} from './api-errors';
it('retains uncertain intent across equivalent key ordering and blocks edited intent until confirmed',()=>{
  const state:{current:ProposalRetry|null}={current:null};
  const first=withProposalRetry({canonicalName:'A',terms:{strike:'10'}},state);
  expect(withProposalRetry({terms:{strike:'10'},canonicalName:'A'},state).idempotencyKey).toBe(first.idempotencyKey);
  expect(()=>withProposalRetry({canonicalName:'A',terms:{strike:'11'}},state)).toThrow('unchanged');
  expect(confirmProposalRetry(state,{data:{proposalId:'confirmed'}})).toBe('confirmed');
  expect(withProposalRetry({canonicalName:'A',terms:{strike:'11'}},state).idempotencyKey).not.toBe(first.idempotencyKey);
});
it('retains malformed success and uncertain errors, but releases a definite validation rejection',()=>{
 const state:{current:ProposalRetry|null}={current:null};withProposalRetry({name:'A'},state);
 expect(()=>confirmProposalRetry(state,{})).toThrow();expect(state.current).not.toBeNull();
 rejectProposalRetry(state,new Error('Network'));expect(state.current).not.toBeNull();
 rejectProposalRetry(state,new BffApiError(422,'Invalid'));expect(state.current).toBeNull();
});
