"use client";
import {useMemo,useState,useRef} from 'react';
import {chartBox,chartGeometry,datedPoints,moveWindow,nearestPoint,resizeWindow,presetWindow,type ChartPoint} from '@/lib/market-data-chart';
import {formatMarketDataValue} from '@/lib/market-data-series';
import styles from './market-data-history-chart.module.css';

export function MarketDataHistoryChart({points,currency,valueType,seriesType}:{points:ChartPoint[];currency:string|null;valueType:string;seriesType:string}) {
 const ordered=useMemo(()=>datedPoints(points),[points]);
 const [window,setWindow]=useState<[number,number]>([0,Math.max(0,ordered.length-1)]);
 const [hover,setHover]=useState<number|null>(null);
 const [preset,setPreset]=useState<string|null>('All');
 const navigator=useRef<HTMLDivElement>(null);
 const drag=useRef<{kind:'start'|'end'|'move';anchor:number;window:[number,number]}|null>(null);
 const overview=useMemo(()=>chartGeometry(ordered),[ordered]);
 const start=Math.min(window[0],Math.max(0,ordered.length-1)),end=Math.min(window[1],Math.max(0,ordered.length-1));
 const chart=useMemo(()=>chartGeometry(ordered.slice(start,end+1)),[ordered,start,end]);
 const box=chartBox,active=hover===null?null:chart.points[Math.max(0,Math.min(hover,chart.points.length-1))];
 const full=start===0 && end===ordered.length-1;
 function change(next:[number,number]){setWindow(next);setHover(null);setPreset(null);}
 function pointerIndex(clientX:number){
  const rect=navigator.current?.getBoundingClientRect();
  if(!rect?.width)return 0;
  return nearestPoint(overview.points,box.left+(clientX-rect.left)/rect.width*(box.right-box.left));
 }
 function beginDrag(event:React.PointerEvent<HTMLElement>,kind:'start'|'end'|'move'){
  if(ordered.length<2)return;
  event.preventDefault();
  drag.current={kind,anchor:pointerIndex(event.clientX),window:[start,end]};
  navigator.current?.setPointerCapture(event.pointerId);
 }
 function keyboard(event:React.KeyboardEvent<HTMLElement>,kind:'start'|'end'|'move'){
  if(!['ArrowLeft','ArrowRight'].includes(event.key))return;
  event.preventDefault();
  const delta=(event.key==='ArrowLeft'?-1:1)*(event.shiftKey?10:1);
  if(kind==='move')change(moveWindow([start,end],ordered.length,delta));
  else if(kind==='start')change([Math.max(0,Math.min(end,start+delta)),end]);
  else change([start,Math.min(ordered.length-1,Math.max(start,end+delta))]);
 }
 function percent(index:number){return (overview.points[index].x-box.left)/(box.right-box.left)*100;}
 if(!ordered.length)return <p className="muted">No dated numeric observations to chart.</p>;
 const axis=`${valueType==='RATE'?'Rate':'Price'}${currency?` (${currency})`:''}`;
 return <div className={styles.chart}>
  <div className={`${styles.toolbar} ${styles.presets}`} aria-label="Quick chart ranges">
   {([['1M',1],['3M',3],['6M',6],['1Y',12],['All',null]] as const).map(([label,months])=><button type="button" key={label} aria-pressed={preset===label} onClick={()=>{change(presetWindow(ordered,months));setPreset(label);}}>{label}</button>)}
  </div>
  <div className={styles.toolbar} aria-label="Chart zoom controls">
   <button type="button" disabled={end-start<2} onClick={()=>change(resizeWindow([start,end],ordered.length,.5))}>Zoom in</button>
   <button type="button" disabled={full} onClick={()=>change(resizeWindow([start,end],ordered.length,2))}>Zoom out</button>
   <button type="button" disabled={start===0} onClick={()=>change(moveWindow([start,end],ordered.length,-Math.max(1,Math.round((end-start+1)/2))))}>Earlier</button>
   <button type="button" disabled={end===ordered.length-1} onClick={()=>change(moveWindow([start,end],ordered.length,Math.max(1,Math.round((end-start+1)/2))))}>Later</button>
   <button type="button" disabled={full} onClick={()=>{change([0,ordered.length-1]);setPreset('All');}}>Reset zoom</button>
  </div>
  <output className={styles.readout}>{active?`${active.marketDate} | ${formatMarketDataValue(active.value,valueType)}${currency?` ${currency}`:''}`:`${ordered[start].marketDate} to ${ordered[end].marketDate} | ${chart.points.length} observations`}</output>
  <svg className={styles.svg} viewBox={`0 0 ${box.width} ${box.height}`} role="img" tabIndex={0} aria-label={`${seriesType} history chart. ${axis} by market date. Use left and right arrows to inspect observations.`}
   onPointerMove={event=>{const rect=event.currentTarget.getBoundingClientRect();if(rect.width)setHover(nearestPoint(chart.points,(event.clientX-rect.left)/rect.width*box.width));}}
   onPointerLeave={()=>setHover(null)}
   onKeyDown={event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();setHover(Math.max(0,Math.min(chart.points.length-1,(hover??(event.key==='ArrowLeft'?chart.points.length: -1))+(event.key==='ArrowLeft'?-1:1))));}else if(event.key==='Escape'){setHover(null);}}}>
   <text x={box.left} y={17} fill="#52627a" fontSize="13">{axis}</text>
   {chart.priceTicks.map(tick=><g key={tick.value}><line x1={box.left} x2={box.right} y1={tick.y} y2={tick.y} stroke="#e7edf5"/><text x={box.left-10} y={tick.y+4} textAnchor="end" fill="#52627a" fontSize="12">{formatMarketDataValue(String(tick.value),valueType)}</text></g>)}
   <line x1={box.left} x2={box.left} y1={box.top} y2={box.bottom} stroke="#94a3b8"/><line x1={box.left} x2={box.right} y1={box.bottom} y2={box.bottom} stroke="#94a3b8"/>
   {chart.dateTicks.map(tick=><g key={tick.label}><line x1={tick.x} x2={tick.x} y1={box.bottom} y2={box.bottom+5} stroke="#94a3b8"/><text x={tick.x} y={box.bottom+22} textAnchor="middle" fill="#52627a" fontSize="12">{tick.label}</text></g>)}
   <text x={(box.left+box.right)/2} y={box.height-8} textAnchor="middle" fill="#52627a" fontSize="13">Market date</text>
   <polyline fill="none" stroke="#2563eb" strokeWidth="2" points={chart.points.map(p=>`${p.x},${p.y}`).join(' ')}/>
   {chart.points.length===1?<circle cx={chart.points[0].x} cy={chart.points[0].y} r={4} fill="#2563eb"/>:null}
   {active?<g><line x1={active.x} x2={active.x} y1={box.top} y2={box.bottom} stroke="#64748b" strokeDasharray="4 4"/><circle cx={active.x} cy={active.y} r={5} fill="#2563eb" stroke="white" strokeWidth={2}/></g>:null}
  </svg>
  <div className={styles.navigatorLabels}><span>Visible period start: {ordered[start].marketDate}</span><span>Visible period end: {ordered[end].marketDate}</span></div>
  <div className={styles.navigator} ref={navigator} role="group" aria-label="Period navigator"
   onPointerMove={event=>{
    const current=drag.current;if(!current)return;
    const index=pointerIndex(event.clientX);
    if(current.kind==='move')change(moveWindow(current.window,ordered.length,index-current.anchor));
    else if(current.kind==='start')change([Math.max(0,Math.min(index,current.window[1])),current.window[1]]);
    else change([current.window[0],Math.min(ordered.length-1,Math.max(index,current.window[0]))]);
   }}
   onPointerUp={()=>{drag.current=null;}} onPointerCancel={()=>{drag.current=null;}} onLostPointerCapture={()=>{drag.current=null;}}>
   <svg viewBox="0 0 900 72" preserveAspectRatio="none" aria-hidden="true">
    <polyline fill="none" stroke="#94a3b8" strokeWidth="1.5" points={overview.points.map(p=>`${(p.x-box.left)/(box.right-box.left)*900},${8+(p.y-box.top)/(box.bottom-box.top)*56}`).join(' ')}/>
   </svg>
   <div className={styles.shade} style={{left:0,width:`${percent(start)}%`}}/>
   <div className={styles.shade} style={{left:`${percent(end)}%`,right:0}}/>
   <button type="button" className={styles.selection} style={{left:`${percent(start)}%`,width:`${Math.max(.2,percent(end)-percent(start))}%`}} aria-label="Move selected period" onPointerDown={e=>beginDrag(e,'move')} onKeyDown={e=>keyboard(e,'move')}/>
   <button type="button" className={styles.handle} style={{left:`${percent(start)}%`}} role="slider" aria-label="Visible period start" aria-valuemin={0} aria-valuemax={end} aria-valuenow={start} aria-valuetext={ordered[start].marketDate!} onPointerDown={e=>beginDrag(e,'start')} onKeyDown={e=>keyboard(e,'start')}>||</button>
   <button type="button" className={styles.handle} style={{left:`${percent(end)}%`}} role="slider" aria-label="Visible period end" aria-valuemin={start} aria-valuemax={ordered.length-1} aria-valuenow={end} aria-valuetext={ordered[end].marketDate!} onPointerDown={e=>beginDrag(e,'end')} onKeyDown={e=>keyboard(e,'end')}>||</button>
  </div>
  <p className={styles.help}>Drag either edge to resize the period, or drag the selected window to move it. Focus an edge or window and use arrow keys; Shift moves ten observations. Quick ranges end at the latest loaded date.</p>
  {ordered.length < points.length ? <p className={styles.help}>{points.length-ordered.length} observations have no usable date or numeric value and cannot be plotted.</p> : null}
  <p className={styles.help}>Hover or touch the chart for the exact date and value. Use arrow keys when the chart is focused. Zoom changes only this chart; the price table keeps its own page.</p>
 </div>;
}
