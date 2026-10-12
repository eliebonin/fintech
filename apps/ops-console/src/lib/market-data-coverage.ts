import type {PricingPreview} from './pricing-policy';
export type CoverageRow={id:string;state:'selected'|'exception'|'unknown';item:PricingPreview['items'][number]|null};
/** The required input set is the denominator, even when no observation exists. */
export function coverageRows(required:string[],items:PricingPreview['items']):CoverageRow[]{
 return required.map(id=>{
  const matches=items.filter(item=>item.subjectReferenceNodeId===id);
  const item=matches.length===1?matches[0]:null;
  const selected=item?.status==='SELECTED'&&item.selectedValue!==null&&item.selectedValue!==undefined&&item.entitlementDecision==='ALLOWED'&&!item.exceptionCode&&item.stalenessStatus!=='STALE';
  const unknown=!item||Boolean(item.exceptionCode?.includes('UNKNOWN'))||item.status==='NOT_EVALUATED';
  return {id,item,state:selected?'selected':unknown?'unknown':'exception'};
 });
}
export function coverageTotals(rows:CoverageRow[]){return {required:rows.length,selected:rows.filter(r=>r.state==='selected').length,exceptions:rows.filter(r=>r.state==='exception').length,unknown:rows.filter(r=>r.state==='unknown').length};}
