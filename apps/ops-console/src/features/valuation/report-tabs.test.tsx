import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it,vi} from 'vitest';
import {ReportTabs,ReportPanel} from './report-tabs';

it('labels four controlled report views without hiding pending review counts from the visible tab',()=>{
 const html=renderToStaticMarkup(<ReportTabs active="breakdown" onNavigate={()=>{}} pendingAmendments={2}/>);
 expect(html).toContain('aria-label="Selected valuation report"');
 for(const id of ['breakdown','positions','review','logs']){
  expect(html).toContain(`id="pnl-report-${id}-tab"`);
  expect(html).toContain(`aria-controls="pnl-report-${id}-panel"`);
 }
 expect(html).toContain('Positions &amp; cash');expect(html).toContain('2 pending amendments');
 const panel=renderToStaticMarkup(<ReportPanel view="positions" active="breakdown"><input defaultValue="retained draft"/></ReportPanel>);
 expect(panel).toContain('hidden=""');expect(panel).toContain('retained draft');
});
it('activates a requested section through the real tab handler',()=>{
 const navigate=vi.fn();const element=ReportTabs({active:'breakdown',onNavigate:navigate});
 const buttons=element.props.children;
 buttons[1].props.onClick();expect(navigate).toHaveBeenCalledWith('positions');
});
