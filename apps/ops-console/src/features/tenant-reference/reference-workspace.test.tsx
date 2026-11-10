import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {ReferenceWorkspace} from './reference-workspace';
it('separates shared reference maintenance from trade requirements',()=>{
 const html=renderToStaticMarkup(<ReferenceWorkspace tenantId="tenant"/>);
 expect(html).toContain('Reference data');expect(html).toContain('Maintain shared values');expect(html).toContain('Loading reference sources');
 expect(html).not.toContain('No sources found');
});
