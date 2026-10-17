import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {PositionHistoryChart,chartGeometry,type PositionChartData} from './position-history-chart';

const chart:PositionChartData={quantityUnit:'SHARES',through:'2026-10-15T23:59:59.999999+00:00',points:[
 {effectiveAt:'2026-09-01T10:00:00+00:00',buyQuantity:'100',sellQuantity:'0',runningQuantity:'100',tradeCount:1,splitQuantity:'0',splitRatios:[]},
 {effectiveAt:'2026-09-15T10:00:00+00:00',buyQuantity:'0',sellQuantity:'-150',runningQuantity:'-50',tradeCount:1,splitQuantity:'0',splitRatios:[]},
 {effectiveAt:'2026-09-20T00:00:00+00:00',buyQuantity:'0',sellQuantity:'0',runningQuantity:'-100',tradeCount:0,splitQuantity:'-50',splitRatios:['2']}
]};
it('renders a step line, signed trade bars and a separate split marker with accessible exact labels',()=>{
 const html=renderToStaticMarkup(<PositionHistoryChart data={chart}/>);
 expect(html).toContain('Position history');expect(html).toContain('role="img"');expect(html).toContain('Holdings (step line)');
 expect(html).toContain('Sell quantity: -150');expect(html).toContain('Split adjustment: -50');expect(html).toContain('SHARES');
 expect(html).not.toContain('NaN');expect(html).not.toContain('Infinity');
});
it('keeps the line flat between movements and extends it to the selected cutoff',()=>{
 const geometry=chartGeometry(chart);
 expect(geometry.path).toContain('H');expect(geometry.path).toContain('V');expect(geometry.path).not.toContain('L');
 expect(geometry.end).toBe(Date.parse(chart.through));
 expect(geometry.minimum).toBeLessThan(0);expect(geometry.maximum).toBeGreaterThan(0);
});
it('does not turn unavailable or empty chart data into a synthetic zero history',()=>{
 expect(renderToStaticMarkup(<PositionHistoryChart/>)).toContain('Chart data unavailable');
 expect(renderToStaticMarkup(<PositionHistoryChart data={{...chart,points:[]}}/>)).toContain('No movements to plot');
});
