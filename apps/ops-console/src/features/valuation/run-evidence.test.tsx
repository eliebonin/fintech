import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {RunEvidence} from './run-evidence';
import type {Detail} from './types';
it('retains readable operational events and discloses technical JSON without inventing results',()=>{
 const detail:Detail={attempt:{attempt_id:'run',request_key:'key',status:'FAILED',started_at:'2026-10-20T12:00:00Z',error_code:'VALUATION_BLOCKED',correlation_id:'correlation'},batch:null,
  events:[{event_id:'event',stage:'CALCULATION',event_code:'FAILED',recorded_at:'2026-10-20T12:00:01Z',details:{reason:'Required FX missing',errorCode:'VALUATION_BLOCKED'}}]};
 const html=renderToStaticMarkup(<RunEvidence detail={detail} status="Failed · No result"/>);
 expect(html).toContain('Operational log');expect(html).toContain('CALCULATION');
 expect(html).toContain('Required FX missing');expect(html).toContain('Technical details (JSON)');
 expect(html).toContain('Correlation ID');expect(html).not.toContain('0.00');
});
