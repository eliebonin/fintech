import {expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {InstrumentCatalogue} from './instrument-catalogue';
import {InstrumentDetail} from './instrument-detail';
import {searchInstruments} from '@/lib/instrument-data';

it('keeps the catalogue inspectable but removes creation for viewers',()=>{
 const html=renderToStaticMarkup(<InstrumentCatalogue initialResults={[]}/>);
 expect(html).toContain('Instrument catalogue');
 expect(html).toContain('/instruments/requests');
 expect(html).not.toContain('href="/instruments/create"');
});
it('retains creation for an explicitly authorized instrument manager',()=>{
 const props={initialResults:[],canManage:true};
 expect(renderToStaticMarkup(<InstrumentCatalogue {...props}/>)).toContain('href="/instruments/create"');
});
it('retains instrument facts but hides listing and convention writes from viewers',()=>{
 const instrument={...searchInstruments('')[0],instrumentType:'BOND'};
 const html=renderToStaticMarkup(<InstrumentDetail instrument={instrument}/>);
 expect(html).toContain('Canonical identity');
 expect(html).not.toContain(`/instruments/${instrument.instrumentId}/listings/new`);
 expect(html).not.toContain(`/instruments/${instrument.instrumentId}/booking-conventions`);
});
it('shows contextual listing and convention actions to an authorized manager',()=>{
 const instrument={...searchInstruments('')[0],instrumentType:'BOND'};
 const props={instrument,canManage:true};
 const html=renderToStaticMarkup(<InstrumentDetail {...props}/>);
 expect(html).toContain(`/instruments/${instrument.instrumentId}/listings/new`);
 expect(html).toContain(`/instruments/${instrument.instrumentId}/booking-conventions`);
});
