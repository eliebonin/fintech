export type ChartPoint = {marketDate: string | null; value: string};
export const chartBox = {width: 900, height: 330, left: 88, right: 872, top: 30, bottom: 266};
export function resizeWindow(window: [number,number], total: number, factor: number): [number,number] {
 const length=Math.min(total,Math.max(Math.min(2,total),Math.round((window[1]-window[0]+1)*factor)));
 const start=Math.max(0,Math.min(total-length,Math.round((window[0]+window[1]+1-length)/2)));
 return [start,start+length-1];
}
export function moveWindow(window: [number,number],total:number,delta:number): [number,number] {
 const length=window[1]-window[0]+1;
 const start=Math.max(0,Math.min(total-length,window[0]+delta));
 return [start,start+length-1];
}
export function datedPoints(points: ChartPoint[]) {
 return points.filter(p=>p.marketDate && Number.isFinite(Date.parse(p.marketDate)) && Number.isFinite(Number(p.value)))
  .sort((a,b)=>a.marketDate!.localeCompare(b.marketDate!));
}
export function chartGeometry(input: ChartPoint[]) {
 const sorted=datedPoints(input), box=chartBox;
 if(!sorted.length)return {points:[],priceTicks:[],dateTicks:[]};
 const times=sorted.map(p=>Date.parse(p.marketDate!));
 const first=times[0],last=times[times.length-1];
 let low=Infinity,high=-Infinity;
 for(const point of sorted){low=Math.min(low,Number(point.value));high=Math.max(high,Number(point.value));}
 const padding=(high-low)*.08 || Math.abs(low)*.02 || 1;
 low-=padding;high+=padding;
 const x=(time:number)=>first===last?(box.left+box.right)/2:box.left+(time-first)/(last-first)*(box.right-box.left);
 const y=(value:number)=>box.bottom-(value-low)/(high-low)*(box.bottom-box.top);
 return {
  points:sorted.map((p,i)=>({...p,x:x(times[i]),y:y(Number(p.value))})),
  priceTicks:Array.from({length:5},(_,i)=>{const value=low+(high-low)*i/4;return {value,y:y(value)};}),
  dateTicks:Array.from({length:first===last?1:5},(_,i)=>{const time=first+(last-first)*i/4;return {label:new Date(time).toISOString().slice(0,10),x:x(time)};}).filter((tick,index,ticks)=>index===0 || tick.label!==ticks[index-1].label)
 };
}
export function nearestPoint(points: Array<{x:number}>,x:number) {
 if(!points.length)return -1;
 let low=0,high=points.length-1;
 while(low<high){const mid=Math.floor((low+high)/2);if(points[mid].x<x)low=mid+1;else high=mid;}
 return low>0 && Math.abs(points[low-1].x-x)<Math.abs(points[low].x-x)?low-1:low;
}

// Inputs are already dated and chronological. Presets end at the latest loaded date.
export function presetWindow(points: ChartPoint[],months:number|null): [number,number] {
 if(!points.length)return [0,0];
 if(months===null)return [0,points.length-1];
 const latest=new Date(points[points.length-1].marketDate!);
 const monthStart=new Date(Date.UTC(latest.getUTCFullYear(),latest.getUTCMonth()-months,1));
 const lastDay=new Date(Date.UTC(monthStart.getUTCFullYear(),monthStart.getUTCMonth()+1,0)).getUTCDate();
 monthStart.setUTCDate(Math.min(latest.getUTCDate(),lastDay));
 const cutoff=monthStart.toISOString().slice(0,10);
 const first=points.findIndex(p=>p.marketDate!>=cutoff);
 return [first<0?points.length-1:first,points.length-1];
}
