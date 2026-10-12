export function PricingPolicyHelp(){
 return <section className="history-panel"><h2>What each choice means</h2><dl>
  <dt>Latest available EoD</dt><dd>A flexible policy starts with each listing’s exchange-session closing price, not an arbitrary last trade. Explicit rules take precedence. Missing expected-session data blocks selection unless a bounded prior-session allowance is configured.</dd>
  <dt>Policy valuation context</dt><dd>The policy-level context must match the calculation request. It is not a universal pricing hour; each rule determines its own pricing target.</dd>
  <dt>When is the price taken?</dt><dd>Exchange session close, a named fixing or another defined time. Exchange close is a timing rule, not a claim that the provider is an official exchange source.</dd>
  <dt>Closing method</dt><dd>There is one closing-price type. Its method is recorded separately: exchange-official, last trade, provider-defined or unknown. Require exchange-official close only when your policy needs that designation; leaving it unchecked does not relax adjustment, freshness or permission checks.</dd>
  <dt>Price adjustments</dt><dd>Unadjusted follows the units traded. Split-adjusted rewrites past prices for stock splits. Provider-adjusted follows the provider’s methodology and may include dividends. These are not interchangeable in valuation.</dd>
  <dt>Provider and source priority</dt><dd>A dataset is a particular feed from a provider. Priority ranks only sources that match the selected price definition and permissions.</dd>
  <dt>Recorded permitted use</dt><dd>Internal reporting access does not automatically allow valuation. Automated calculation permission is a separate check. Configuration displays recorded permissions; it is not legal clearance.</dd>
 </dl><p><a href="/market-data/sources">Inspect Data sources and permissions</a>. Check compatibility before saving, then preview actual instruments and dates. Neither check replaces price validation.</p></section>;
}
