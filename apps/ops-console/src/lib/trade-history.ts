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
