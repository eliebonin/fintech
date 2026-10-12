'use client';
import {recognitionDate,type RecognitionDraft} from '@/lib/valuation-recognition';
export function RecognitionSummary({draft}:{draft:RecognitionDraft}){
 return <p>Valuation effective date: <strong>{recognitionDate(draft)||'Invalid execution date'}</strong> · UTC business-date convention.{draft.valuationOverrideReason?` Override reason: ${draft.valuationOverrideReason}`:''}</p>;
}
export function ValuationRecognitionFields({draft,onChange}:{draft:RecognitionDraft;onChange:(patch:Partial<RecognitionDraft>)=>void}){
 return <fieldset className="ticket-section"><legend>Valuation recognition</legend>
  <p>Built-in trade fields shared across tenants. Blank uses the UTC execution date. This is not settlement; changing it moves both daily position inclusion and the execution contribution.</p>
  <label>Valuation effective date (optional)<input id="valuationEffectiveDate" type="date" value={draft.valuationEffectiveDate??''} onChange={event=>onChange({valuationEffectiveDate:event.target.value})}/></label>
  <label>Valuation override reason<input id="valuationOverrideReason" maxLength={1000} value={draft.valuationOverrideReason??''} onChange={event=>onChange({valuationOverrideReason:event.target.value})}/></label>
  <RecognitionSummary draft={draft}/>
 </fieldset>;
}
