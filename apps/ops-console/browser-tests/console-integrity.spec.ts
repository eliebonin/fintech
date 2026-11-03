import {test,expect} from './console-check';

test('group codes validate hyphens and underscores without browser regex errors',async({page})=>{
 const writes:string[]=[];
 await page.route('**/api/**',route=>{
  if(route.request().method()!=='GET')writes.push(route.request().url());
  return route.fulfill({json:{tenantId:'synthetic',userId:'admin',tenantModuleCodes:['TRADING'],users:[],groups:[],strategies:[],actions:[{code:'TRADE_READ',moduleCodes:['TRADING']}]}});
 });
 await page.goto('/?mode=tenant-access');
 await page.getByRole('tab',{name:/^Groups/}).click();
 await page.getByRole('button',{name:'Create group',exact:true}).click();
 const code=page.getByRole('textbox',{name:/^Code/});
 for(const value of ['OPS','OPS-UK','OPS_UK','Ops1']){
  await code.fill(value);expect(await code.evaluate(element=>(element as HTMLInputElement).checkValidity())).toBe(true);
 }
 for(const value of ['OPS UK','OPS/UK','OPS[UK]']){
  await code.fill(value);expect(await code.evaluate(element=>(element as HTMLInputElement).validity.patternMismatch)).toBe(true);
 }
 expect(writes).toEqual([]);
});

test('trade import source validation accepts its documented characters and rejects invalid names',async({page})=>{
 await page.route('**/api/trade-imports/options',route=>route.fulfill({json:{strategies:[{id:'s',label:'Synthetic strategy'}],maxRows:500,maxBytes:524288,products:['EQUITY']}}));
 await page.route('**/api/trade-imports/history?**',route=>route.fulfill({json:{items:[],total:0}}));
 await page.goto('/?mode=imports');
 await page.getByRole('combobox',{name:'Strategy',exact:true}).selectOption('s');
 const source=page.getByRole('textbox',{name:'File source',exact:true});
 for(const value of ['custodian-a','custodian_a','custodian.a','1source']){
  await source.fill(value);expect(await source.evaluate(element=>(element as HTMLInputElement).checkValidity())).toBe(true);
 }
 for(const value of ['.source','_source','-source','source/desk','source desk','source!']){
  await source.fill(value);expect(await source.evaluate(element=>(element as HTMLInputElement).validity.patternMismatch)).toBe(true);
 }
});
