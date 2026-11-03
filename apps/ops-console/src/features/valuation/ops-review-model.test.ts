import {expect,it} from 'vitest';
import {positionLabel,positionContext,selectPositionRows} from './ops-review-model';
import type {Item,Presentation} from './types';
const rows:Item[]=Array.from({length:27},(_,i)=>({attribution_id:`a${i}`,subject_id:`s${i}`,trade_id:null,version:1,market_pnl:String(i),components:{PRICE:String(i)},evidence:{},display:{interest:null,other:null,attention:i===26?['Interest not supplied']:[]}}));
const presentation:Presentation={references:Object.fromEntries(rows.map((r,i)=>[r.subject_id!,`Instrument ${i}`])),currencies:{},datasets:{},rules:{},users:{},context:{},totals:{interest:null,other:null},pendingAmendments:0};
it('searches and filters across the entire result before pagination',()=>{
 expect(selectPositionRows(rows,presentation,{query:'Instrument 26',attentionOnly:true,sort:'name'}).map(r=>r.attribution_id)).toEqual(['a26']);
});
it('orders signed exact monetary strings without floating point loss',()=>{
 const values=['999999999999999999.000000000001','999999999999999999.000000000002','-0.000000000001'];
 const items=values.map((v,i)=>({...rows[i],net_pnl:v}));
 expect(selectPositionRows(items,presentation,{query:'',attentionOnly:false,sort:'pnl-desc'}).map(r=>r.net_pnl)).toEqual([values[1],values[0],values[2]]);
});
it('does not turn an unavailable label into a visible UUID',()=>{
 expect(positionLabel(rows[0],undefined)).toBe('Instrument name unavailable');
});
it('searches business identifiers and technical aliases without displaying internal codes',()=>{
 const metadata={...presentation,instrumentDisplays:{s26:{primaryName:'Treasury bill',identifier:{scheme:'ISIN',value:'GB00BSGRV302'},context:['GBP denomination'],searchText:'Treasury bill GB00BSGRV302 RECON_20828',basis:'CURRENT_ACCESSIBLE_METADATA' as const}}};
 for(const query of ['GB00BSGRV302','RECON_20828'])expect(selectPositionRows(rows,metadata,{query,attentionOnly:false,sort:'name'}).map(r=>r.attribution_id)).toEqual(['a26']);
 expect(positionLabel(rows[26],metadata)).toBe('Treasury bill');
 expect(positionLabel(rows[0],{...metadata,instrumentDisplays:{}})).toBe('Instrument name unavailable');
});
it('distinguishes same-name positions using frozen currency and unit conventions',()=>{
 const item={...rows[0],evidence:{identity:{bucket:{key:{currency_id:'usd',quantity_unit:'CONTRACTS',unit_multiplier:'100',quote_factor:'1'}}}}};
 expect(positionContext(item,{...presentation,currencies:{usd:'USD'}})).toBe('USD · CONTRACTS · multiplier 100 · quote factor 1');
});

it('filters contributing components across the full result and includes explicitly recorded zero',()=>{
 const items=rows.map((row,i):Item=>({...row,components:i===26?{PRICE:'0',RESET:'0'}:{PRICE:'1'}}));
 expect(selectPositionRows(items,presentation,{query:'',attentionOnly:false,sort:'name',componentCodes:['RESET']}).map(r=>r.attribution_id)).toEqual(['a26']);
 expect(selectPositionRows(items,presentation,{query:'',attentionOnly:false,sort:'name',componentCodes:['CARRY','RESET']}).map(r=>r.attribution_id)).toEqual(['a26']);
});

it('combines instrument type with search, attention and source filters across off-page positions',()=>{
 const metadata={...presentation,instrumentTypes:Object.fromEntries(rows.map((r,i)=>[r.subject_id!,
  i===26?{code:'BOND',label:'Bond'}:{code:'EQUITY',label:'Equity'}]))};
 const filters={query:'Instrument',attentionOnly:false,sort:'name',instrumentType:'BOND'};
 expect(selectPositionRows(rows,metadata,filters).map(r=>r.attribution_id)).toEqual(['a26']);
 expect(selectPositionRows(rows,metadata,{...filters,attentionOnly:true,componentCodes:['PRICE']}).map(r=>r.attribution_id)).toEqual(['a26']);
 expect(selectPositionRows(rows,metadata,{...filters,query:'Instrument 0'})).toEqual([]);
 expect(selectPositionRows(rows,metadata,{...filters,instrumentType:'EQUITY',attentionOnly:true})).toEqual([]);
 expect(selectPositionRows(rows,metadata,{...filters,instrumentType:''})).toHaveLength(27);
});

it('keeps unavailable classifications filterable without guessing a type from the instrument name',()=>{
 const metadata={...presentation,references:{s0:'Bond named equity'},instrumentTypes:{s1:{code:'BOND',label:'Bond'}}};
 expect(selectPositionRows(rows.slice(0,2),metadata,{query:'',attentionOnly:false,sort:'name',instrumentType:'UNKNOWN'}).map(r=>r.attribution_id)).toEqual(['a0']);
 expect(selectPositionRows(rows.slice(0,2),metadata,{query:'',attentionOnly:false,sort:'name',instrumentType:'BOND'}).map(r=>r.attribution_id)).toEqual(['a1']);
});
