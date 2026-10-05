import type {components} from 'api-contracts';
import type {BookedTrade} from './trades';

/** Resolve names from the approved context or booked snapshot, never current master data. */
export function swapContextLabels(context:components['schemas']['ProductBookingContextView']):Record<string,string> {
  const swap=context.swapDetails,terms=swap?.genericTerms;
  if(!swap||!terms)return {};
  const labels:Record<string,string>={[terms.performanceReferenceId]:swap.performanceReferenceName};
  if(context.currency){labels[terms.notionalCurrencyId]=context.currency;labels[terms.quoteCurrencyId]=context.currency;}
  if(terms.fundingReferenceId&&swap.fundingReferenceName)labels[terms.fundingReferenceId]=swap.fundingReferenceName;
  for(const [key,idField] of [['returnProfile','return_profile_id'],['dayCountConvention','day_count_convention_id']]){
    const row=swap.sourceFacts[key];
    if(!row||typeof row!=='object'||Array.isArray(row))continue;
    const record=row as Record<string,unknown>;
    if(typeof record[idField]==='string'&&typeof record.display_name==='string')labels[record[idField]]=record.display_name;
  }
  return labels;
}

export function bookedSwapFacts(trade:BookedTrade) {
  const economics=trade.productEconomics,terms=economics?.terms.swapDetails?.genericTerms;
  if(economics?.terms.kind!=='SWAP'||!terms)return undefined;
  return {terms,bookedNotional:economics.bookedNotional??trade.quantity.replace(/^-/,''),labels:swapContextLabels(economics.terms)};
}

export type HistorySearchParams = Record<string, string | string[] | undefined>;
export type HistoryQuery = {
  q: string; portfolioCode: string; fromDate: string; toDate: string;
  side: string; lifecycleStatus: string; page: number; pageSize: number;
  range: "14d" | "30d" | "all" | "custom";
};

export function parseHistoryQuery(raw: HistorySearchParams): HistoryQuery {
  const value = (name: string) => (Array.isArray(raw[name]) ? raw[name][0] : raw[name]) ?? "";
  const page = Number(value("page"));
  const pageSize = Number(value("pageSize"));
  const requestedRange = value("range");
  let fromDate = value("fromDate");
  let toDate = value("toDate");
  let range: HistoryQuery["range"] = requestedRange === "all" ? "all"
    : requestedRange === "custom" || (!requestedRange && (fromDate || toDate)) ? "custom"
    : requestedRange === "30d" ? "30d" : "14d";
  if (range === "all" || (range === "custom" && !fromDate && !toDate)) {
    range = "all"; fromDate = ""; toDate = "";
  } else if ((range === "14d" || range === "30d") && !(fromDate && toDate)) {
    const today = new Date();
    toDate = today.toISOString().slice(0, 10);
    const start = new Date(`${toDate}T00:00:00Z`);
    start.setUTCDate(start.getUTCDate() - (range === "30d" ? 29 : 13));
    fromDate = start.toISOString().slice(0, 10);
  }
  return {
    q: value("q").trim().slice(0, 200), portfolioCode: value("portfolioCode").slice(0, 100),
    fromDate, toDate, range,
    side: ["BUY", "SELL"].includes(value("side")) ? value("side") : "",
    lifecycleStatus: value("lifecycleStatus").slice(0, 30),
    page: Number.isSafeInteger(page) && page > 0 && page <= 1000000 ? page : 1,
    pageSize: [25, 50, 100].includes(pageSize) ? pageSize : 25,
  };
}

export function historyHref(query: HistoryQuery, page = query.page): string {
  const params = new URLSearchParams();
  for (const key of ["q", "portfolioCode", "fromDate", "toDate", "side", "lifecycleStatus"] as const) {
    if (query[key]) params.set(key, query[key]);
  }
  params.set("range", query.range);
  params.set("pageSize", String(query.pageSize));
  params.set("page", String(page));
  return `/trades?${params.toString()}`;
}

export function safeHistoryReturn(value: string | string[] | undefined): string {
  if (typeof value !== "string" || !(value === "/trades" || value.startsWith("/trades?"))) return "/trades";
  const params = Object.fromEntries(new URL(value, "http://local").searchParams);
  return historyHref(parseHistoryQuery(params));
}
