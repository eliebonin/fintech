import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {MarketDataHistoryChart} from './market-data-history-chart';
it('renders currency and date axes, accessible zoom controls and full-period points',()=>{
 const html=renderToStaticMarkup(<MarketDataHistoryChart points={[{marketDate:'2026-01-01',value:'10'},{marketDate:'2026-01-11',value:'20'}]} currency="USD" valueType="PRICE" seriesType="CLOSE"/>);
 for(const text of ['Price (USD)','Market date','Zoom in','Zoom out','Reset zoom','Visible period start','Visible period end','2026-01-01','1M','3M','6M','1Y','All','Period navigator'])expect(html).toContain(text);
 expect(html).toContain('tabindex="0"');
 expect(html).not.toContain('type="range"');
 expect(html).toContain('Move selected period');
});
