import { expectTypeOf, test } from "vitest";

import type { components } from "./generated";
import type {
  CurrencyPayload,
  InstrumentSearchPayload,
  ReferenceApiMeta,
  ReferenceNodeSearchPayload,
} from "./reference-data";

test("reference-data compatibility aliases are generated-schema types", () => {
  expectTypeOf<ReferenceApiMeta>().toEqualTypeOf<components["schemas"]["ApiMeta"]>();
  expectTypeOf<InstrumentSearchPayload>().toEqualTypeOf<components["schemas"]["InstrumentSearchResponse"]>();
  expectTypeOf<ReferenceNodeSearchPayload>().toEqualTypeOf<components["schemas"]["ReferenceNodeSearchResponse"]>();
  expectTypeOf<CurrencyPayload>().toEqualTypeOf<components["schemas"]["CurrencyResponse"]>();
});
