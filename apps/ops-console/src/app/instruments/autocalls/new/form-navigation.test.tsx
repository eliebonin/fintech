import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import AutocallForm from './form';

it('offers real section targets without hiding contractual inputs or essential warnings',()=>{
 const html=renderToStaticMarkup(<AutocallForm/>);
 expect(html).toContain('aria-label="On this page"');
 for(const id of ['product-identity','product-references','product-terms']){
  expect(html).toContain(`href="#${id}"`);
  expect(html).toContain(`id="${id}"`);
 }
 expect(html).not.toContain('href="#product-events"');
 expect(html).toContain('Submit it for steward review');
 expect(html).toContain('Generate schedule');
 expect(html).toContain('<h1');
});
