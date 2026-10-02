import {expect,it} from "vitest";
import {formatTradeExactDecimal} from "./trades";
it("preserves the full stored decimal rather than floating-point rounding",()=>{expect(formatTradeExactDecimal("123456789012345678.123456789012")).toBe("123,456,789,012,345,678.123456789012");expect(formatTradeExactDecimal("0.000001")).toBe("0.000001");});
