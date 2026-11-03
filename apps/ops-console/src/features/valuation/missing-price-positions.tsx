import type {Batch} from './types';
import {formatTradeExactDecimal} from '@/lib/trades';

/** Unpriced positions remain explicit; a missing market contribution is not zero. */
export function MissingPricePositions({batch}:{batch:Batch}){
 const coverage=batch.summary.inputCoverage;
 if(!coverage||!coverage.unpricedPositions.length&&!coverage.unpricedCashAccounts?.length)return null;
 const metadata=batch.presentation;
 return <section className="pnl-surface" aria-label="Positions with missing prices"><h3>Unpriced positions &amp; cash</h3>
  <p className="pnl-muted">These positions are excluded from the calculated subtotal. Supply the missing marks or request reviewed manual marks in Review, then recalculate.</p>
  {coverage.unpricedPositions.length?<div className="pnl-table-scroll"><table className="pnl-table"><caption>Positions with missing required inputs</caption><thead><tr><th scope="col">Instrument</th><th scope="col">Type</th><th scope="col">Opening quantity</th><th scope="col">Closing quantity</th><th scope="col">Missing input dates</th><th scope="col">P&amp;L</th></tr></thead><tbody>
   {coverage.unpricedPositions.map(row=><tr key={row.positionKey}><th scope="row"><a href={`/instruments/${encodeURIComponent(row.subjectId)}`}>{metadata?.references[row.subjectId]??'Instrument name unavailable'}</a></th><td>{metadata?.instrumentTypes?.[row.subjectId]?.label??row.product.replaceAll('_',' ')}</td><td className="pnl-amount">{formatTradeExactDecimal(row.bucket.opening_quantity)}</td><td className="pnl-amount">{formatTradeExactDecimal(row.bucket.closing_quantity)}</td><td>{coverage.gaps.filter(g=>row.inputKeys.includes(g.inputKey)).map(g=><div key={g.inputKey}>{g.selection.pricing_date_requested??g.request.valuation_date} · {g.role==='FX'?'FX rate':'Price / rate'}</div>)}</td><td>P&amp;L unavailable</td></tr>)}
  </tbody></table></div>:null}
  {coverage.unpricedCashAccounts?.length?<div className="pnl-table-scroll"><table className="pnl-table"><caption>Cash accounts with missing required FX</caption><thead><tr><th scope="col">Cash account</th><th scope="col">Currency</th><th scope="col">Missing FX dates</th><th scope="col">P&amp;L</th></tr></thead><tbody>{coverage.unpricedCashAccounts.map(row=><tr key={`${row.accountId}:${row.currencyId}`}><th scope="row">{metadata?.cashAccounts?.[row.accountId]??'Cash account name unavailable'}</th><td>{metadata?.currencies[row.currencyId]??'Currency name unavailable'}</td><td>{coverage.gaps.filter(g=>row.inputKeys.includes(g.inputKey)).map(g=><div key={g.inputKey}>{g.selection.pricing_date_requested??g.request.valuation_date}</div>)}</td><td>FX P&amp;L unavailable</td></tr>)}</tbody></table></div>:null}
 </section>;
}
