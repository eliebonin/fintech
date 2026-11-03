type Row=Record<string,unknown>;
const row=(value:unknown):Row=>value&&typeof value==='object'&&!Array.isArray(value)?value as Row:{};
const text=(value:unknown)=>typeof value==='string'?value:'Not recorded';

/** Present the frozen quotation bridge. Never derive interest or recalculate prices here. */
export function BondPriceNormalization({selections}:{selections:Row[]}){
 const quotes=selections.map(selection=>({selection,quote:row(row(selection.pricing_evidence).bondPriceNormalization)}))
  .filter(({quote})=>quote.method==='DIRTY_MINUS_QUOTED_ACCRUAL_PER_100');
 if(!quotes.length)return null;
 return <section aria-label="Bond quote normalization">
  <h5>DIRTY to CLEAN · quoted prices per 100 nominal</h5>
  <div className="pnl-check-scroll"><table className="pnl-table pnl-check-table">
   <caption>Source quotation and exact normalization used</caption>
   <thead><tr><th scope="col">Valuation date</th><th scope="col">Actual market date</th><th scope="col">Quote settlement date</th><th scope="col">DIRTY source</th><th scope="col">Quoted accrued</th><th scope="col">CLEAN used</th></tr></thead>
   <tbody>{quotes.map(({selection,quote},index)=><tr key={index}>
    <th scope="row">{text(selection.valuation_date)}</th><td>{text(quote.marketDate)}</td><td>{text(quote.quoteSettlementDate)}</td>
    <td className="pnl-check-exact">{text(quote.dirtyPrice)}</td><td className="pnl-check-exact">{text(quote.accruedPer100)}</td><td className="pnl-check-exact">{text(quote.cleanPrice)}</td>
   </tr>)}</tbody>
  </table></div>
  <p>DIRTY minus its matching quoted accrued gives CLEAN. Daily interest and accrued-balance FX use separate strategy inputs; neither is inferred from this quotation.</p>
 </section>;
}
