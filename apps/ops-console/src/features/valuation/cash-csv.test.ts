import {expect,it} from 'vitest';
import {parseCashCsv} from './cash-csv';

const accounts=[{cash_account_id:'account-one',display_label:'Custody'}];
const currencies=[{id:'eur',label:'EUR'}];
it('keeps decimal text and quoted notes intact',()=>{
 const rows=parseCashCsv('account,currency,valueDate,amount,sourceReference,note\r\nCustody,EUR,2026-10-10,-100.123456789012,Statement,"Restricted, pending"',accounts,currencies);
 expect(rows[0]).toEqual({accountId:'account-one',currencyId:'eur',valueDate:'2026-10-10',amount:'-100.123456789012',sourceReference:'Statement',note:'Restricted, pending',expectedRevision:0,correctionReason:null});
});
it('rejects unknown accounts, ambiguous labels and malformed quotes',()=>{
 const text='account,currency,valueDate,amount,sourceReference\nOther,EUR,2026-10-10,1,Statement';
 expect(()=>parseCashCsv(text,accounts,currencies)).toThrow();
 expect(()=>parseCashCsv(text.replace('Other','Custody'),[...accounts,...accounts],currencies)).toThrow();
 expect(()=>parseCashCsv(text+'"',accounts,currencies)).toThrow();
});
