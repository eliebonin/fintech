import type {Item,Presentation} from './types';
import {formatTradeExactDecimal} from '@/lib/trades';
type Bucket={opening_quantity?:string;closing_quantity?:string;key?:{currency_id?:string;quantity_unit?:string;unit_multiplier?:string;quote_factor?:string;product_basis?:string}};
export function PositionFacts({item,metadata}:{item:Item;metadata:Presentation}){
 const data=item.evidence as {identity?:{bucket?:Bucket;lot?:{quantity?:string}};executionInputs?:{effective_at:string;booking:{trade_id:string;price:string;quantity:string;quantity_unit?:string}}[]}|null;
 const bucket=data?.identity?.bucket;
 return <section aria-label="Recorded position quantities"><h4>Position and movements</h4>{bucket?<dl className="pnl-fact-grid">
  <div><dt>Opening quantity</dt><dd>{formatTradeExactDecimal(bucket.opening_quantity??'Not recorded')}</dd></div><div><dt>Closing quantity</dt><dd>{formatTradeExactDecimal(bucket.closing_quantity??'Not recorded')}</dd></div>
  <div><dt>Quantity unit</dt><dd>{bucket.key?.quantity_unit??'Not recorded'}</dd></div><div><dt>Valuation currency</dt><dd>{metadata.currencies[bucket.key?.currency_id??'']??'Not recorded / name unavailable'}</dd></div>
  <div><dt>Unit multiplier</dt><dd>{bucket.key?.unit_multiplier??'Not recorded'}</dd></div><div><dt>Quote factor</dt><dd>{bucket.key?.quote_factor??'Not recorded'}</dd></div>
 </dl>:<p>Boundary quantities are not recorded in this historical result format.</p>}
 {data?.executionInputs?.length?<div className="pnl-table-scroll"><table className="pnl-table"><caption>Period executions — booked facts, not allocated trade P&amp;L</caption><thead><tr><th>Date / trade</th><th>Signed quantity</th><th>Booked price / rate</th></tr></thead><tbody>{data.executionInputs.map((execution,index)=><tr key={index}><th scope="row"><a href={`/trades/${encodeURIComponent(execution.booking.trade_id)}`}>{execution.effective_at.slice(0,10)} · {execution.booking.quantity.startsWith('-')?'Sell / decrease':'Buy / increase'}</a></th><td>{formatTradeExactDecimal(execution.booking.quantity)}</td><td>{execution.booking.price}</td></tr>)}</tbody></table></div>:<p>No period executions recorded on this result version.</p>}
 </section>;
}
