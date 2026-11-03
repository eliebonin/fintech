/** Exact server balances. Numbers are never substituted for retained decimal strings. */
export type BalanceHistoryRow={history_id:string;build_id?:string;instrument_id:string;instrument_name:string;currency_code:string;value_date:string;
 opening_balance:string|null;daily_earned:string|null;trade_movements:string|null;coupon_paid:string|null;closing_balance:string|null;basis:string;source_status:string;evidence:unknown};
export type BalanceChartBond={id:string;label:string;currency:string};
export type InterestBond=BalanceChartBond&{currencyId:string};
export type InterestCurrency={id:string;label:string};
export type InterestContext={strategyId:string;strategyLabel:string;from:string;to:string};
export type InterestTab='daily'|'inputs'|'balances';
export type InterestOptions={bonds:InterestBond[];currencies:InterestCurrency[];canWrite:boolean;strategyLabel?:string};
export type DailyInterestInput={input_id:string;instrument_id:string;instrument_name?:string;currency_id:string;currency_code?:string;
 value_date:string;daily_earned_interest:string;revision:number;payload:{sourceReference?:string;eligibleNominal?:string;eligibilityConvention?:string;
 policyId?:string;cutId?:string;reportingCurrencyId?:string;inputs?:{openingBalance:string;closingBalance:string;balanceMovements:string}}};
export type ClosingBalanceInput={input_id:string;instrument_id:string;instrument_name?:string;currency_id:string;currency_code?:string;
 value_date:string;closing_balance:string|null;status:string;revision:number;source_reference:string;reason?:string};
export type InterestIntent={path:'accrual-inputs'|'balance-inputs'|'balance-history-refresh';body:Record<string,unknown>};
export type InterestEditor=({kind:'daily';row?:DailyInterestInput}|{kind:'closing'|'withdraw';row?:ClosingBalanceInput})&{prefill?:{instrumentId:string;currencyId:string;valueDate:string}};
