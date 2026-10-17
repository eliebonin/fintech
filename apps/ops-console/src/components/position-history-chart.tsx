'use client';
import {useId,useState} from 'react';

export type PositionChartPoint={effectiveAt:string;buyQuantity:string;sellQuantity:string;runningQuantity:string;tradeCount:number;splitQuantity:string;splitRatios:string[]};
export type PositionChartData={quantityUnit:string;through:string;points:PositionChartPoint[]};
const WIDTH=1000,HEIGHT=340,LEFT=88,RIGHT=25,TOP=24,BOTTOM=57;
const dateLabel=(value:number)=>new Date(value).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'});

/** Numbers are used only for SVG coordinates; labels retain server decimal strings. */
export function chartGeometry(data:PositionChartData){
 const times=data.points.map(p=>Date.parse(p.effectiveAt)),end=Date.parse(data.through);
 const values=data.points.flatMap(p=>[Number(p.buyQuantity),Number(p.sellQuantity),Number(p.runningQuantity)]);
 if(!times.length||!Number.isFinite(end)||[...times,...values].some(v=>!Number.isFinite(v))||end<times[times.length-1]||times.some((v,i)=>i>0&&v<times[i-1]))throw new Error('Invalid chart history');
 const first=times[0],span=Math.max(end-first,86400000),start=first-span*.02;
 // Always include zero: shorts and signed bars must use the same baseline.
 let low=0,high=0;for(const value of values){low=Math.min(low,value);high=Math.max(high,value);}
 const padding=(high-low||1)*.1,minimum=low-padding,maximum=high+padding;
 const x=(instant:number)=>LEFT+(instant-start)/(end-start)*(WIDTH-LEFT-RIGHT);
 const y=(quantity:number)=>TOP+(maximum-quantity)/(maximum-minimum)*(HEIGHT-TOP-BOTTOM);
 let path=`M ${LEFT} ${y(0)}`;
 const points=data.points.map((point,index)=>{
  const px=x(times[index]),py=y(Number(point.runningQuantity));path+=` H ${px} V ${py}`;
  return {...point,x:px,y:py};
 });
 path+=` H ${x(end)}`;
 return {path,points,x,y,start,end,minimum,maximum};
}

export function PositionHistoryChart({data}:{data?:PositionChartData}){
 const id=useId(),[selected,setSelected]=useState<number|null>(null);
 if(!data)return <p className="muted">Chart data unavailable. The movement table remains the source of detail.</p>;
 if(!data.points.length)return <p className="muted">No movements to plot.</p>;
 let geometry;try{geometry=chartGeometry(data);}catch{return <p role="alert">Chart data could not be displayed safely. Inspect the movement table.</p>;}
 const {points,path,x,y,start,end,minimum,maximum}=geometry,baseline=y(0);
 const ticks=Array.from({length:5},(_,i)=>minimum+(maximum-minimum)*i/4);
 const tickLabel=(value:number)=>new Intl.NumberFormat('en-GB',{maximumSignificantDigits:5,notation:Math.abs(value)>=1e9||(value!==0&&Math.abs(value)<.001)?'scientific':'standard'}).format(value);
 const active=selected===null?undefined:points[selected];
 const label=(p:PositionChartPoint)=>`${p.effectiveAt} · Buy quantity: ${p.buyQuantity} · Sell quantity: ${p.sellQuantity} · Holdings: ${p.runningQuantity} ${data.quantityUnit}${p.splitRatios.length?` · Split adjustment: ${p.splitQuantity} (ratio ${p.splitRatios.join(', ')})`:''}`;
 return <figure className="position-history-chart">
  <figcaption><h3>Position history</h3><p>Full history through {dateLabel(end)} · {data.quantityUnit.replaceAll('_',' ')} · same cutoffs as the movement table</p></figcaption>
  <ul className="position-chart-legend" aria-label="Chart legend"><li><span className="chart-key chart-key-line"/>Holdings (step line)</li><li><span className="chart-key chart-key-buy"/>Buys / positive bookings</li><li><span className="chart-key chart-key-sell"/>Sells / negative bookings</li><li><span className="chart-key chart-key-split"/>Split adjustment</li></ul>
  <div className="position-chart-scroll"><svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-labelledby={`${id}-title ${id}-description`}>
   <title id={`${id}-title`}>Holdings and trade quantities over time</title><desc id={`${id}-description`}>A step line shows cumulative holdings. Positive and negative trade bars share a zero baseline. Diamonds identify reviewed stock splits, not trades. Exact quantities remain in the movement table. Focus or hover over a movement for details.</desc>
   {ticks.map((tick,i)=><g key={i}><line className="chart-grid" x1={LEFT} x2={WIDTH-RIGHT} y1={y(tick)} y2={y(tick)}/><text className="chart-label" x={LEFT-10} y={y(tick)+4} textAnchor="end">{tickLabel(tick)}</text></g>)}
   <line className="chart-zero" x1={LEFT} x2={WIDTH-RIGHT} y1={baseline} y2={baseline}/>
   {points.map((p,index)=><g key={p.effectiveAt} tabIndex={0} role="img" aria-label={label(p)} onMouseEnter={()=>setSelected(index)} onFocus={()=>setSelected(index)} onClick={()=>setSelected(index)}>
    <title>{label(p)}</title>
    {Number(p.buyQuantity)>0?<rect className="chart-buy" x={p.x-7} width={6} y={y(Number(p.buyQuantity))} height={Math.max(.8,baseline-y(Number(p.buyQuantity)))}/>:null}
    {Number(p.sellQuantity)<0?<rect className="chart-sell" x={p.x+1} width={6} y={baseline} height={Math.max(.8,y(Number(p.sellQuantity))-baseline)}/>:null}
    <circle className="chart-hit" cx={p.x} cy={p.y} r={9}/>
   </g>)}
   <path className="chart-holdings" d={path}/>
   {points.map((p,index)=><g key={p.effectiveAt+'mark'} onMouseEnter={()=>setSelected(index)} onClick={()=>setSelected(index)}><title>{label(p)}</title>{p.splitRatios.length?<path className="chart-split" d={`M ${p.x} ${p.y-6} l 6 6 l -6 6 l -6 -6 Z`}/>:<circle className="chart-point" cx={p.x} cy={p.y} r={3}/>}</g>)}
   {[0,1,2,3,4].map(i=>{const instant=start+(end-start)*i/4;return <text className="chart-label" key={i} x={x(instant)} y={HEIGHT-25} textAnchor={i===0?'start':i===4?'end':'middle'}>{dateLabel(instant)}</text>;})}
   <text className="chart-label" x={WIDTH-RIGHT} y={HEIGHT-5} textAnchor="end">UTC dates</text>
  </svg></div>
  <p className="position-chart-readout" aria-live="polite">{active?label(active):'Hover, tap or keyboard-focus a movement to inspect exact quantities.'}</p>
  <p className="muted">Holdings stay flat between events. Same-time buys and sells are shown separately; the line shows their combined result. Chart coordinates are illustrative; exact quantities are retained in the table and details.</p>
 </figure>;
}
