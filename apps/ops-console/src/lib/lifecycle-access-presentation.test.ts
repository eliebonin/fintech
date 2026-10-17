import {expect,it} from 'vitest';
import {actionTitle,actionDescription} from './access-presentation';
it('distinguishes direct lifecycle booking from approval and configuration',()=>{
 expect(actionTitle('LIFECYCLE_BOOK')).toBe('Book lifecycle entries');
 expect(actionTitle('LIFECYCLE_APPROVE')).toBe('Approve lifecycle entries');
 expect(actionDescription('LIFECYCLE_BOOK')).toContain('Book now');
 expect(actionDescription('LIFECYCLE_BOOK')).toContain('trade-write');
 expect(actionDescription('LIFECYCLE_APPROVE')).toContain('independent');
 expect(actionDescription('LIFECYCLE_CONFIGURE')).toContain('plain-bond maturity');
 expect(actionDescription('LIFECYCLE_CONFIGURE')).toContain('revision check');
 expect(actionDescription('LIFECYCLE_READ')).toContain('remain deferred');
});
