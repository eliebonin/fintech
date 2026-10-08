import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {it,expect} from 'vitest';
import {CalendarConsole} from './calendar-console';
it('shows read-only calendar inspection without publication controls',()=>{
 const html=renderToStaticMarkup(<CalendarConsole options={{canManage:false,calendars:[],strategies:[],assignments:[]}}/>);
 expect(html).toContain('Read-only');expect(html).toContain('Preview');expect(html).not.toContain('Publish immutable version');
});
it('separates purposes and exposes evidence-backed exception and assignment controls',()=>{
 const html=renderToStaticMarkup(<CalendarConsole options={{canManage:true,calendars:[],strategies:[],assignments:[]}}/>);
 expect(html).toContain('VALUATION');expect(html).toContain('DEALING');expect(html).toContain('SETTLEMENT');
 expect(html).toContain('Publish immutable version');expect(html).toContain('Assign pinned version');expect(html).toContain('UNKNOWN');
});
