import {it,expect} from 'vitest';
import {withProposalRetry,type ProposalRetry} from './proposal-retry';
it('retains the key for unchanged retries and replaces it for edited intent',()=>{
  const state:{current:ProposalRetry|null}={current:null};
  const first=withProposalRetry({canonicalName:'A',terms:{strike:'10'}},state);
  expect(withProposalRetry({terms:{strike:'10'},canonicalName:'A'},state).idempotencyKey).toBe(first.idempotencyKey);
  expect(withProposalRetry({canonicalName:'A',terms:{strike:'11'}},state).idempotencyKey).not.toBe(first.idempotencyKey);
});
