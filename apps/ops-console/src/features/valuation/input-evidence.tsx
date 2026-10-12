type Input={kind?:string;valueDate?:string;inputId?:string;payload?:{currencyId?:string;reportingCurrencyId?:string;sourceReference?:string;amounts?:Record<string,string>}};
/** Exact server-returned amounts only; no client-side interest calculation. */
export function InputEvidence({evidence}:{evidence:unknown}){
 if(!evidence||typeof evidence!=='object')return null;
 const inputs=(evidence as {economicInputs?:Input[]}).economicInputs??[];
 return <>{inputs.filter(i=>i.kind==='DAILY_ACCRUAL').map((input,index)=><article key={input.inputId??index}><h5>Daily accrued interest · {input.valueDate}</h5>
  <p>{input.payload?.sourceReference} · local {input.payload?.currencyId} / reporting {input.payload?.reportingCurrencyId}</p>
  <dl><dt>Daily earned · local / reporting</dt><dd>{input.payload?.amounts?.dailyLocal} / {input.payload?.amounts?.dailyBase}</dd>
   <dt>Accumulated balance · local / reporting</dt><dd>{input.payload?.amounts?.balanceLocal} / {input.payload?.amounts?.balanceBase}</dd>
   <dt>FX on opening accrued receivable (CARRY)</dt><dd>{input.payload?.amounts?.receivableFx}</dd></dl></article>)}</>;
}
