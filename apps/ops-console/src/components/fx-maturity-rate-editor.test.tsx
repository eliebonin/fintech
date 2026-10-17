import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {FxMaturityRateEditor} from './fx-maturity-rate-editor';

it('warns that a spot suggestion is not counterparty-confirmed and requires provenance',()=>{
 const html=renderToStaticMarkup(<FxMaturityRateEditor price="1.12" suggestedPrice="1.12" busy={false} onPreview={()=>{}}/>);
 expect(html).toContain('not a counterparty-confirmed closing rate');
 expect(html).toContain('Source / confirmation reference');
 expect(html).toContain('Reason for using this rate');
 expect(html).toContain('value="1.12"');
 expect(html).not.toContain('Book now');
});

it('permits sourced manual input when no eligible spot observation exists',()=>{
 const html=renderToStaticMarkup(<FxMaturityRateEditor price={null} suggestedPrice={null} busy={false} onPreview={()=>{}}/>);
 expect(html).toContain('No eligible maturity-date spot rate');
 expect(html).toContain('Enter the confirmed rate');
 expect(html).toContain('Check entered rate');
});
