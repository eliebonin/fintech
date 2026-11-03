import type {BalanceHistoryRow} from './interest-types';
export type BalancePageSize=25|50|100|'all';
export const balanceChartBox={width:1000,height:320,left:100,right:975,top:22,bottom:265};
const DAY=86_400_000;
function instant(value:string){
 const time=Date.parse(`${value}T00:00:00Z`);
 if(!/^\d{4}-\d{2}-\d{2}$/.test(value)||!Number.isFinite(time)||new Date(time).toISOString().slice(0,10)!==value)throw new Error('Invalid balance date');
 return time;
}
export function validateBalanceRange(from:string,to:string):string|null{
 try{if(instant(from)>instant(to))return 'From date must be on or before To date.';}catch{return 'Choose valid From and To dates.';}
 return null;
}
export function balancePage<T>(rows:readonly T[],size:BalancePageSize,offset:number){
 const total=rows.length;
 const start=size==='all'||!total?0:Math.min(Math.floor(Math.max(0,offset)/size)*size,Math.floor((total-1)/size)*size);
 return {items:size==='all'?rows.slice():rows.slice(start,start+size),start,total};
}

/** Approximate SVG coordinates only. Exact amounts and missing states stay in row. */
export function balanceChartGeometry(rows:readonly BalanceHistoryRow[],from:string,to:string){
 const error=validateBalanceRange(from,to);if(error)throw new Error(error);
 if(new Set(rows.map(row=>row.currency_code)).size>1)throw new Error('Choose one currency for the chart');
 const start=instant(from),end=instant(to),box=balanceChartBox;
 const sorted=rows.slice().sort((a,b)=>a.value_date.localeCompare(b.value_date));
 const known=sorted.filter(row=>row.closing_balance!==null);
 const values=known.map(row=>Number(row.closing_balance));
 if(values.some(value=>!Number.isFinite(value)))throw new Error('Some balances cannot be plotted safely');
 let low=0,high=0;for(const value of values){low=Math.min(low,value);high=Math.max(high,value);}
 // Nice monetary ticks include an exact zero, without negative padding for
 // positive-only stocks. Integer tick indices avoid a near-zero float label.
 const span=high-low||1;
 if(!Number.isFinite(span))throw new Error('Balance range cannot be plotted safely');
 const rawStep=span/4,power=10**Math.floor(Math.log10(rawStep));
 const step=([1,2,2.5,5,10].find(unit=>unit>=rawStep/power)??10)*power;
 if(!Number.isFinite(step)||step<=0)throw new Error('Balance range cannot be plotted safely');
 const firstTick=Math.floor(low/step),lastTick=low===0&&high===0?4:Math.ceil(high/step);
 const minimum=firstTick*step,maximum=lastTick*step;
 if(!Number.isFinite(maximum-minimum))throw new Error('Balance range cannot be plotted safely');
 const x=(time:number)=>start===end?(box.left+box.right)/2:box.left+(time-start)/(end-start)*(box.right-box.left);
 const y=(value:number)=>box.bottom-(value-minimum)/(maximum-minimum)*(box.bottom-box.top);
 const points:Array<{row:BalanceHistoryRow;x:number;y:number}>=[],segments:string[]=[];
 let path='',previous:number|null=null,lastDate:string|null=null;
 for(const row of sorted){
  const time=instant(row.value_date);
  if(time<start||time>end)throw new Error('Balance falls outside the selected dates');
  if(lastDate===row.value_date)throw new Error('Duplicate balance date');lastDate=row.value_date;
  if(row.closing_balance===null){if(path)segments.push(path);path='';previous=null;continue;}
  if(previous!==null&&time-previous>DAY){if(path)segments.push(path);path='';}
  const point={row,x:x(time),y:y(Number(row.closing_balance))};points.push(point);
  path+=`${path?' L':'M'} ${point.x} ${point.y}`;previous=time;
 }
 if(path)segments.push(path);
 const ticks=Array.from({length:lastTick-firstTick+1},(_,i)=>{const value=(firstTick+i)*step;return {value,y:y(value)};});
 const dates=Array.from({length:start===end?1:5},(_,i)=>{const time=start+(end-start)*i/4;return {date:new Date(time).toISOString().slice(0,10),x:x(time)};})
  .filter((tick,index,all)=>index===0||tick.date!==all[index-1].date);
 const zeroY=y(0),barWidth=Math.min(32,(box.right-box.left)/((end-start)/DAY+1)*.75);
 const bars=points.map(point=>{
  const left=Math.max(box.left,point.x-barWidth/2),right=Math.min(box.right,point.x+barWidth/2);
  return {row:point.row,x:left,y:Math.min(point.y,zeroY),width:right-left,height:Math.abs(point.y-zeroY)};
 });
 return {points,segments,ticks,dates,minimum,maximum,zeroY,bars};
}
