import type {components} from 'api-contracts';
export type CalendarPublish=components['schemas']['CalendarPublish'];
export type CalendarView=components['schemas']['CalendarView'];
export type CalendarOptions=components['schemas']['CalendarOptions'];
export type CalendarDays=components['schemas']['CalendarDaysView'];
export type CalendarAssignment=components['schemas']['CalendarAssignmentCreate'];

/** Explicit dated rows only: omission never creates an open day. */
export function parseCalendarDates(text:string):CalendarPublish['exceptions'] {
 const lines=text.split(/\r?\n/).filter(line=>line.trim());
 if(lines.length>1100)throw new Error('Import at most 1,100 dated entries.');
 const seen=new Set<string>();
 return lines.map((line,index)=>{
  const fields=line.split('|').map(field=>field.trim());
  const [date,status,reason,sourceReference]=fields;
  if(fields.length!==4||!/^\d{4}-\d{2}-\d{2}$/.test(date)||Number.isNaN(Date.parse(date+'T00:00:00Z'))||new Date(date+'T00:00:00Z').toISOString().slice(0,10)!==date)
   throw new Error(`Line ${index+1}: use YYYY-MM-DD | OPEN or CLOSED | reason | source.`);
  if(seen.has(date))throw new Error(`Duplicate date ${date}.`);seen.add(date);
  if(!['OPEN','CLOSED'].includes(status)||!reason||!sourceReference||reason.length>500||sourceReference.length>250)
   throw new Error(`Line ${index+1}: a status, reason and source are required.`);
  return {date,status:status as 'OPEN'|'CLOSED',reason,sourceReference};
 });
}

export function newCalendarDraft():CalendarPublish {
 const year=new Date().getUTCFullYear();
 return {calendarCode:'',displayName:'',purpose:'VALUATION',timezoneName:'Europe/London',decisionTime:'16:00:00',
  coverageFrom:`${year}-01-01`,coverageTo:`${year}-12-31`,mode:'WEEKDAYS',weekdays:[0,1,2,3,4],baseCalendarIds:[],exceptions:[],sourceReference:''};
}
