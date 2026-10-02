/** Display only: never coerce or round the stored booking value. */
export function displayTradeProperty(type: string, value: unknown, displayValue?: string | null): string {
  if (value === undefined || value === null || value === "") return "Not specified";
  if (type === "BOOLEAN" && typeof value === "boolean") return value ? "Yes" : "No";
  return displayValue ?? String(value);
}
