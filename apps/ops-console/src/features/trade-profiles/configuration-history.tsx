'use client';
import {useEffect,useState} from 'react';
import {configurationRequest} from '@/lib/trade-configuration-client';
import styles from './profiles.module.css';
type Event={eventId:string;action:string;reason:string;actorId:string;recordedAtUtc:string};
export function ConfigurationHistory({tenantId}:{tenantId:string}){
 const [events,setEvents]=useState<Event[]>([]),[offset,setOffset]=useState(0),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 useEffect(()=>{let active=true;setLoading(true);setError('');configurationRequest<Event[]>(tenantId,`audit?offset=${offset}&limit=25`).then(result=>{if(active)setEvents(result);}).catch(caught=>{if(active)setError(caught.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[tenantId,offset]);
 return <section className={styles.card}><h2>Configuration history</h2><p>Retained field, catalogue, profile and assignment change events for this tenant. Strategy identities remain in their scoped views.</p>{error?<p role="alert">{error}</p>:loading?<p role="status">Loading history…</p>:<div className={styles.table}><table><caption>Tenant configuration audit</caption><thead><tr><th>When (UTC)</th><th>Action</th><th>Reason</th><th>Evidence</th></tr></thead><tbody>{events.map(event=><tr key={event.eventId}><td>{new Date(event.recordedAtUtc).toISOString().replace('T',' ')}</td><td>{event.action.replaceAll('_',' ')}</td><td>{event.reason}</td><td><details><summary>Audit identifiers</summary><p>Actor: {event.actorId}</p><p>Event: {event.eventId}</p></details></td></tr>)}</tbody></table></div>}<nav className={styles.actions} aria-label="Configuration history pagination"><button type="button" disabled={loading||offset===0} onClick={()=>setOffset(Math.max(0,offset-25))}>Previous events</button><span>Page {Math.floor(offset/25)+1}</span><button type="button" disabled={loading||events.length<25} onClick={()=>setOffset(offset+25)}>Next events</button></nav></section>;
}
