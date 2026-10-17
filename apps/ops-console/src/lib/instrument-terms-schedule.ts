export type Fact = Record<string, unknown>;
export type TermsLayer = {
  instrumentId: string; canonicalName: string; instrumentType: string; relation: string;
  version: number; issuer: string | null; currency: string | null;
  dates: Fact; economics: Fact; facts: Record<string, Fact[]>;
};
export type TermsSchedule = {
  instrumentId: string; basis: string; layers: TermsLayer[]; referenceLabels: Record<string, string>;
};
