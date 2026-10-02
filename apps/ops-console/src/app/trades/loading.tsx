export default function TradeLoading() {
  return <main className="mvp-page" aria-busy="true"><h1>Loading trades</h1><p role="status">Loading tenant trade records…</p><div aria-hidden="true">{[1, 2, 3, 4, 5].map((row) => <div key={row} className="trade-loading-row" />)}</div></main>;
}
