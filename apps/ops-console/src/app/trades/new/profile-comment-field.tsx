import type {TradeBookingContext} from '@/lib/browser-api-client';
import type {TicketError} from './ticket-model';
export function ProfileCommentField({context,comment,purpose,errors=[],onChange}:{context:TradeBookingContext;comment?:string;purpose:string;errors?:TicketError[];onChange:(value:string)=>void}){
 const rule=context.tradeProfile?.fields.find(field=>field.standardFieldKey==='COMMENT');
 const required=purpose==='OTHER'||rule?.requirement==='REQUIRED',used=!!rule&&rule.requirement!=='NOT_USED';
 if(!context.tradeProfile)return null;
 if(!used&&!required)return comment?<div><strong>Retained comment</strong><p>{comment}</p><p className="muted">This profile does not accept a new comment. Only an unchanged original value can be kept on a linked correction.</p><button type="button" onClick={()=>onChange('')}>Clear retained comment</button></div>:null;
 const error=errors.find(issue=>issue.field==='comment');
 return <label>Comment ({required?'required':'optional'})<textarea id="comment" aria-label="Comment" aria-invalid={!!error} aria-describedby={error?'comment-error':undefined} required={required} maxLength={10000} value={comment??''} onChange={event=>onChange(event.target.value)}/>{error?<small id="comment-error">{error.message}</small>:null}</label>;
}
