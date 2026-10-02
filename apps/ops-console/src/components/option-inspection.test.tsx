import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { InstrumentDetail } from './instrument-detail';
import { searchInstruments } from '@/lib/instrument-data';

describe('governed option inspection', () => {
  it('renders current instrument terms even before a listing exists', () => {
    const instrument = {...searchInstruments('')[0], instrumentType:'OPTION', listings:[], optionTerms:{optionType:'PUT',underlyingId:null,underlyingName:null,strike:'10.123456789012',strikeBasis:'ABSOLUTE',strikeCurrency:'GBP',expiryDate:'2027-09-17',lastTradingAtUtc:'2027-09-17T16:30:00+00:00',exerciseStyle:'EUROPEAN',settlementMethod:'CASH',settlementCurrency:'GBP',deliverableUnits:'100',premiumCurrency:'GBP',premiumMultiplier:'100',premiumStyle:'UPFRONT'}};
    const html = renderToStaticMarkup(<InstrumentDetail instrument={instrument} />);
    expect(html).toContain('Option terms');
    expect(html).toContain('10.123456789012');
    expect(html).toContain('Not available to this tenant');
    expect(html).toContain('No listing attached');
    expect(html).not.toContain('as expected for an OTC security');
    expect(html).toContain('Booking eligibility is checked');
  });
  it('does not invent missing option conventions', () => {
    const html = renderToStaticMarkup(<InstrumentDetail instrument={{...searchInstruments('')[0],instrumentType:'OPTION',optionTerms:null}} />);
    expect(html).toContain('No unambiguous current option terms');
  });
});
