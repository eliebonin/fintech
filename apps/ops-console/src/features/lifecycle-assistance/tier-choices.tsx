import {useId} from 'react';
import {tierLabels} from './client';
import styles from './assistance.module.css';
const descriptions=['Ops identifies events and books through the normal authorised workflow.','Bond-maturity worklist and manual handling. Other event discovery is planned.','Prepared entries are completed and reviewed before posting.','Ops clicks to post a ready entry when the strategy permits direct execution.'];
export function TierChoices({label,value,maximum=3,disabled=false,onChange}:{label:string;value:number;maximum?:number;disabled?:boolean;onChange:(value:number)=>void}){
 const name=useId();return <fieldset className={styles.choices} disabled={disabled}><legend>{label}</legend>{tierLabels.map((text,tier)=><label key={tier}><input type="radio" name={name} value={tier} checked={value===tier} disabled={tier>maximum} onChange={()=>onChange(tier)}/><span>Tier {tier} — {text}<small>{descriptions[tier]}{tier>maximum?' Above the current subscription ceiling.':''}</small></span></label>)}</fieldset>;
}
export function AssistanceBoundary(){return <p className={styles.note}>Subscriptions enable assistance, not user permissions. Independent-review rules still apply. Bond-maturity notifications are available in Lifecycle; FX/other event discovery is planned. Existing bond/FX preparation and booking retain their current controls.</p>;}
