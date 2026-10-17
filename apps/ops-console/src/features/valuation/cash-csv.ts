/** CSV preserves decimal text. Backend revalidates ownership and economics. */
type Account={cash_account_id:string;display_label:string|null};
type Currency={id:string;label:string};
export type CashRow={accountId:string;currencyId:string;valueDate:string;amount:string;sourceReference:string;note:string|null;expectedRevision:number;correctionReason:string|null};
export function parseCashCsv(text:string,accounts:Account[],currencies:Currency[]):CashRow[]{
 if(text.length>1_000_000)throw new Error('CSV is limited to 1 MB of text.');
 const records:string[][]=[];let cells:string[]=[],cell='',quoted=false,closed=false;
 for(let i=0;i<text.length;i++){
  const char=text[i];
  if(quoted){if(char==='"'){if(text[i+1]==='"'){cell+='"';i++;}else{quoted=false;closed=true;}}else cell+=char;continue;}
  if(char==='"'){if(cell||closed)throw new Error('Malformed CSV quote.');quoted=true;continue;}
  if(char===','||char==='\n'||char==='\r'){
   cells.push(cell.trim());cell='';closed=false;
   if(char!==','){if(char==='\r'&&text[i+1]==='\n')i++;if(cells.some(Boolean))records.push(cells);cells=[];}
  }else{if(closed&&char.trim())throw new Error('Unexpected text after a CSV quote.');cell+=char;}
 }
 if(quoted)throw new Error('Unclosed CSV quote.');
 cells.push(cell.trim());if(cells.some(Boolean))records.push(cells);
 const header=records.shift()?.map(h=>h.replace(/^\uFEFF/,''))??[];
 const allowed=['account','currency','valueDate','amount','sourceReference','note','expectedRevision','correctionReason'];
 if(new Set(header).size!==header.length||header.some(h=>!allowed.includes(h))||allowed.slice(0,5).some(h=>!header.includes(h)))throw new Error('Use the supplied CSV headings.');
 if(!records.length||records.length>500)throw new Error('Upload between 1 and 500 rows.');
 return records.map((record,index)=>{
  if(record.length!==header.length)throw new Error(`CSV row ${index+2} has the wrong number of fields.`);
  const v=Object.fromEntries(header.map((h,i)=>[h,record[i]]));
  const a=accounts.filter(a=>a.display_label===v.account);const c=currencies.filter(c=>c.label===v.currency);
  if(a.length!==1||c.length!==1)throw new Error(`CSV row ${index+2}: account or currency is unknown or ambiguous.`);
  const revision=v.expectedRevision||'0';
  if(!/^\d+$/.test(revision)||!Number.isSafeInteger(Number(revision)))throw new Error('Revision must be a nonnegative integer.');
  return {accountId:a[0].cash_account_id,currencyId:c[0].id,valueDate:v.valueDate,amount:v.amount,sourceReference:v.sourceReference,
   note:v.note||null,expectedRevision:Number(revision),correctionReason:v.correctionReason||null};
 });
}
