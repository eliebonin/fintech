import {expect,it} from 'vitest';
import {balanceChartGeometry,balanceChartBox,balancePage,validateBalanceRange} from './balance-chart-model';
import type {BalanceHistoryRow} from './interest-types';
const row=(day:string,value:string|null):BalanceHistoryRow=>({history_id:day,instrument_id:'bond',instrument_name:'Example bond',currency_code:'USD',value_date:day,
 opening_balance:null,daily_earned:null,trade_movements:null,coupon_paid:null,closing_balance:value,basis:'DERIVED',source_status:'CURRENT',evidence:{}});

it('breaks the plotted line at unassessed or absent days without turning them into zero',()=>{
 const input=[row('2026-10-01','1000.123456789012'),row('2026-10-02',null),row('2026-10-03','0'),row('2026-10-05','-20')];
 const chart=balanceChartGeometry(input,'2026-10-01','2026-10-05');
 expect(chart.segments).toHaveLength(3);expect(chart.points).toHaveLength(3);
 expect(chart.points[0].row.closing_balance).toBe('1000.123456789012');
 expect(chart.points[1].row.closing_balance).toBe('0');expect(chart.minimum).toBeLessThan(-20);
 expect(chart.points.every(point=>Number.isFinite(point.x)&&Number.isFinite(point.y))).toBe(true);
});
it('supports flat, single-date and entirely unknown histories',()=>{
 expect(balanceChartGeometry([row('2026-10-01','0')],'2026-10-01','2026-10-01').points[0].y).toBeTypeOf('number');
 expect(balanceChartGeometry([row('2026-10-01',null)],'2026-10-01','2026-10-01').points).toHaveLength(0);
});
it('uses zero as the positive-only floor and an explicit tick for every signed range',()=>{
 for(const values of [['10','100'],['-100','-10'],['-20','100'],['0']] as const){
  const input=values.map((value,i)=>row(`2026-10-0${i+1}`,value));
  const chart=balanceChartGeometry(input,'2026-10-01',`2026-10-0${values.length}`);
  expect(chart.ticks.filter(tick=>tick.value===0)).toHaveLength(1);
  expect(chart.ticks.find(tick=>tick.value===0)?.y).toBe(chart.zeroY);
  expect(chart.points.every(point=>point.y>=balanceChartBox.top&&point.y<=balanceChartBox.bottom)).toBe(true);
  expect(chart.maximum).toBeGreaterThan(chart.minimum);
 }
 const positive=balanceChartGeometry([row('2026-10-01','123456')],'2026-10-01','2026-10-01');
 expect(positive.minimum).toBe(0);expect(positive.zeroY).toBe(balanceChartBox.bottom);
 expect(positive.ticks.map(tick=>tick.value)).toEqual([0,50000,100000,150000]);
 const negative=balanceChartGeometry([row('2026-10-01','-100')],'2026-10-01','2026-10-01');
 expect(negative.maximum).toBe(0);expect(negative.zeroY).toBe(balanceChartBox.top);
});
it('rejects invalid geometry and mixed monetary currencies',()=>{
 expect(()=>balanceChartGeometry([row('2026-10-01','Infinity')],'2026-10-01','2026-10-02')).toThrow();
 expect(()=>balanceChartGeometry([row('2026-10-01','1'),{...row('2026-10-02','2'),currency_code:'GBP'}],'2026-10-01','2026-10-02')).toThrow();
 expect(validateBalanceRange('2026-10-02','2026-10-01')).toBeTruthy();
 expect(validateBalanceRange('2024-01-01','2026-10-20')).toBeNull();
});
it('paginates the full dataset at 25/50/100/all and clamps obsolete page offsets',()=>{
 const rows=Array.from({length:131},(_,i)=>row(`point-${i}`,String(i)));
 for(const size of [25,50,100] as const)expect(balancePage(rows,size,0).items).toHaveLength(size);
 expect(balancePage(rows,'all',100).items).toHaveLength(131);
 expect(balancePage(rows,25,130).start).toBe(125);
 expect(balancePage(rows,25,130).items).toHaveLength(6);
 expect(balancePage([],25,100)).toMatchObject({start:0,total:0,items:[]});
});
it('anchors positive and negative bars at zero, keeps zero known and omits missing balances',()=>{
 const chart=balanceChartGeometry([row('2026-10-01','10'),row('2026-10-02','-5'),row('2026-10-03','0'),row('2026-10-04',null)],'2026-10-01','2026-10-04');
 expect(chart.bars).toHaveLength(3);
 expect(chart.bars[0].y+chart.bars[0].height).toBeCloseTo(chart.zeroY);
 expect(chart.bars[1].y).toBeCloseTo(chart.zeroY);
 expect(chart.bars[1].height).toBeGreaterThan(0);expect(chart.bars[2].height).toBe(0);
 for(const bar of chart.bars){expect(bar.width).toBeGreaterThan(0);expect(bar.x).toBeGreaterThanOrEqual(balanceChartBox.left);expect(bar.x+bar.width).toBeLessThanOrEqual(balanceChartBox.right);}
 const single=balanceChartGeometry([row('2026-10-01','10')],'2026-10-01','2026-10-01');
 expect(single.bars[0].width).toBeLessThanOrEqual(32);
 const daily=balanceChartGeometry(Array.from({length:20},(_,i)=>row(`2026-10-${String(i+1).padStart(2,'0')}`,'10')),'2026-10-01','2026-10-20');
 for(let i=1;i<daily.bars.length;i++)expect(daily.bars[i-1].x+daily.bars[i-1].width).toBeLessThan(daily.bars[i].x);
});
