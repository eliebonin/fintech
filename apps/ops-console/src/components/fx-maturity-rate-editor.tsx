'use client';
export type FxRateOverride={rate:string;sourceReference:string;reason:string};

export function FxMaturityRateEditor({price,suggestedPrice,busy,onPreview,onDirty}:{price:string|null;suggestedPrice:string|null;busy:boolean;onPreview:(value:FxRateOverride)=>void;onDirty?:()=>void}){
 return <details><summary>Prefilled booking — enter or override closing rate</summary>
  <p role="note">{suggestedPrice?`Suggested from maturity-date spot FX (${suggestedPrice}), not a counterparty-confirmed closing rate.`:'No eligible maturity-date spot rate. Enter the confirmed rate with its source and reason; one-click spot booking is unavailable.'}</p>
  <form onChange={onDirty} onSubmit={event=>{event.preventDefault();const data=new FormData(event.currentTarget);onPreview({rate:String(data.get('rate')),sourceReference:String(data.get('sourceReference')),reason:String(data.get('reason'))});}}>
   <label>Closing rate — quote currency per base currency<input name="rate" inputMode="decimal" required maxLength={64} defaultValue={price??''} placeholder="Enter the confirmed rate"/></label>
   <label>Source / confirmation reference<input name="sourceReference" required maxLength={2000}/></label>
   <label>Reason for using this rate<textarea name="reason" required maxLength={2000}/></label>
   <button disabled={busy}>Check entered rate</button>
  </form><p>This checks inputs only. Submit for approval or book afterward according to this strategy’s processing mode. No cash balance changes.</p>
 </details>;
}
