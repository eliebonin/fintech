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
      { label: "Option", description: "Listed fixed-strike vanilla options with explicit premium conventions.", href: "/instruments/options/new" },
      { label: "Future", description: "An exact cash-settled index expiry with sourced contract conventions.", href: "/instruments/futures/new" },
      { label: "Structured product", description: "Structured-security definitions for listed or OTC execution; booking conventions follow approval.", href: "/instruments/autocalls/new" },
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
      { label: "Swap", description: "A sourced performance swap with optional rate funding, submitted for approval.", href: "/instruments/swaps/new" },
      { label: "Cryptoasset", description: "Native cryptoassets and their economic identity.", href: "/instruments/crypto/new" },
    ],
  },
  {
    label: "Families and benchmarks",
    description: "Create a concrete index variant. Its family is governed as supporting reference structure.",
    options: [
      { label: "Futures family", description: "A governed non-tradable family; create its contract expiries after approval.", href: "/instruments/future-families" },
      { label: "Index", description: "A benchmark or index variant used by instruments and strategies.", href: "/instruments/indices/new" },
    ],
  },
];
