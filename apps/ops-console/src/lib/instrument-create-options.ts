export type InstrumentCreateOption = {
  label: string;
  description: string;
  href: string;
};

export type InstrumentCreateGroup = {
  label: string;
  description: string;
  options: InstrumentCreateOption[];
};

export const INSTRUMENT_CREATE_GROUPS: InstrumentCreateGroup[] = [
  {
    label: "Listed and fund instruments",
    description: "Create the economic instrument first. Add a venue listing after approval.",
    options: [
      { label: "Equity", description: "Shares and other equity securities.", href: "/instruments/new" },
      { label: "Bond", description: "Fixed-income and debt securities.", href: "/instruments/bonds/new" },
      { label: "Fund", description: "Funds and share classes.", href: "/instruments/funds/new" },
      { label: "ETP", description: "ETFs, ETNs, ETCs, and related products.", href: "/instruments/etps/new" },
    ],
  },
  {
    label: "OTC and digital instruments",
    description: "Describe the economic contract, rather than a trade booked against it.",
    options: [
      { label: "FX forward", description: "An OTC FX-forward contract definition.", href: "/instruments/fx-forwards/new" },
      { label: "Structured product", description: "Autocallable and other structured-product definitions.", href: "/instruments/autocalls/new" },
      { label: "Cryptoasset", description: "Native cryptoassets and their economic identity.", href: "/instruments/crypto/new" },
    ],
  },
  {
    label: "Indices and benchmarks",
    description: "Create a concrete index variant. Its family is governed as supporting reference structure.",
    options: [
      { label: "Index", description: "A benchmark or index variant used by instruments and strategies.", href: "/instruments/indices/new" },
    ],
  },
];
