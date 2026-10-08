import {it,expect} from 'vitest';
import {parseCalendarDates} from './calendar-input';
it('imports explicit dates without inventing dates between them',()=>{
 expect(parseCalendarDates('2026-08-31 | CLOSED | Fund holiday | Administrator notice\n2026-09-01 | OPEN | NAV day | Schedule')).toEqual([
  {date:'2026-08-31',status:'CLOSED',reason:'Fund holiday',sourceReference:'Administrator notice'},
  {date:'2026-09-01',status:'OPEN',reason:'NAV day',sourceReference:'Schedule'}]);
});
it('rejects impossible dates, duplicates and missing evidence',()=>{
 expect(()=>parseCalendarDates('2026-02-30 | CLOSED | Holiday | Notice')).toThrow();
 expect(()=>parseCalendarDates('2026-08-31 | CLOSED | Holiday | Notice\n2026-08-31 | OPEN | Reopen | Notice')).toThrow();
 expect(()=>parseCalendarDates('2026-08-31 | CLOSED | Holiday |')).toThrow();
});
