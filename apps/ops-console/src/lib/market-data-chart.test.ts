import {expect,it} from 'vitest';
import {chartGeometry,resizeWindow,moveWindow,nearestPoint,presetWindow} from './market-data-chart';
it('positions observations by calendar date and supplies labelled numeric ticks',()=>{
 const chart=chartGeometry([{marketDate:'2026-01-01',value:'10'},{marketDate:'2026-01-02',value:'20'},{marketDate:'2026-01-11',value:'15'}]);
 expect(chart.points[1].x-chart.points[0].x).toBeCloseTo((chart.points[2].x-chart.points[0].x)/10);
 expect(chart.priceTicks).toHaveLength(5);expect(chart.dateTicks[0].label).toBe('2026-01-01');
 expect(nearestPoint(chart.points,chart.points[1].x)).toBe(1);
});
it('zooms and pans within the available period and handles single flat points',()=>{
 expect(resizeWindow([0,99],100,.5)).toEqual([25,74]);
 expect(moveWindow([25,74],100,100)).toEqual([50,99]);
 expect(resizeWindow([25,74],100,2)).toEqual([0,99]);
 const chart=chartGeometry([{marketDate:'2026-01-01',value:'0'}]);
 expect(Number.isFinite(chart.points[0].x)).toBe(true);expect(Number.isFinite(chart.points[0].y)).toBe(true);
});

it('keeps short-period date tick labels unique and omits unusable points',()=>{
 const chart=chartGeometry([{marketDate:'2026-01-01',value:'10'},{marketDate:'2026-01-02',value:'12'},{marketDate:null,value:'99'},{marketDate:'2026-01-02',value:'bad'}]);
 expect(chart.points).toHaveLength(2);expect(new Set(chart.dateTicks.map(t=>t.label)).size).toBe(chart.dateTicks.length);
 expect(nearestPoint(chart.points,-100)).toBe(0);expect(nearestPoint(chart.points,10000)).toBe(1);
});

it('quick ranges use calendar months ending at the latest loaded point',()=>{
 const points=[{marketDate:'2025-03-31',value:'1'},{marketDate:'2025-12-31',value:'2'},{marketDate:'2026-02-27',value:'3'},{marketDate:'2026-02-28',value:'4'},{marketDate:'2026-03-31',value:'5'}];
 expect(presetWindow(points,1)).toEqual([3,4]);
 expect(presetWindow(points,3)).toEqual([1,4]);
 expect(presetWindow(points,12)).toEqual([0,4]);
 expect(presetWindow(points,null)).toEqual([0,4]);
});
