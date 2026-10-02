/**
 * Real UI regression for the documented synthetic review instance.
 * Run exports in order via Codex cua_repl, passing its documented Tab API.
 * No hidden HTTP calls, browser mocks, order execution, or production targets.
 */
export function createCycle({baseUrl, syntheticOnly, runCode}) {
  if(baseUrl!=="http://127.0.0.1:3001" || syntheticOnly!==true)throw new Error("Use the isolated synthetic review instance only");
  if(!/^UI_[A-Z0-9_]+$/.test(runCode))throw new Error("Supply a fresh UI_ run code");
  return {baseUrl,runCode,checks:[],numeric:`${runCode} allocation`,flag:`${runCode} cross`,bucket:`${runCode} bucket`,catalogue:`${runCode} buckets`,original:`${runCode} Core original`,corrected:`${runCode} Core corrected`,hedge:`${runCode} Hedge`,tradeUrl:null};
}
const button=(tab,name)=>tab.playwright.getByRole("button",{name,exact:true});
const label=(tab,name)=>tab.playwright.getByLabel(name,{exact:true});
const panel=(tab,name)=>tab.playwright.getByRole("tabpanel",{name,exact:true});
function assert(condition,message){if(!condition)throw new Error(message);}
async function contains(tab,text){await tab.playwright.getByRole("main").filter({hasText:text}).waitFor({state:"visible"});}
async function status(tab,text){await tab.playwright.getByRole("status").filter({hasText:text}).waitFor({state:"visible"});}
async function configuration(tab,cycle){await tab.goto(`${cycle.baseUrl}/tenant-profile/trade-configuration`);await button(tab,"Add field").waitFor({state:"visible"});await button(tab,"Add field").click();await button(tab,"Cancel").click();}
async function textFields(tab,scope,code,text){
  await scope.getByRole("textbox",{name:"Display label",exact:true}).fill(text);
  await scope.getByRole("textbox",{name:/^Stable code/}).fill(code);
  await scope.getByRole("textbox",{name:/^Business definition/}).fill("Synthetic UI regression fixture; do not use for real bookings.");
}
async function newField(tab,cycle,code,text,type,required=false){
  await button(tab,"Add field").click(); const scope=panel(tab,"Custom fields");
  await textFields(tab,scope,code,text);await scope.getByRole("combobox",{name:"Value type",exact:true}).selectOption(type);
  if(required){await label(tab,"Required for every new trade").check();await label(tab,"I acknowledge this booking requirement.").check();}
  await button(tab,"Publish field").click();await status(tab,"Field published.");
}
async function confirm(tab,reason){
  const scope=tab.playwright.getByRole("region").filter({has:tab.playwright.getByRole("button",{name:"Confirm change",exact:true})});
  if(reason)await scope.getByRole("textbox",{name:/^Change reason/}).fill(reason);
  await scope.getByRole("checkbox",{name:"I understand the impact on future bookings.",exact:true}).check();
  await scope.getByRole("button",{name:"Confirm change",exact:true}).click();await status(tab,"Change confirmed.");
}
export async function configureCycle(tab,cycle){
  await configuration(tab,cycle);
  await newField(tab,cycle,`${cycle.runCode}_ZERO`,cycle.numeric,"DECIMAL");
  await newField(tab,cycle,`${cycle.runCode}_FLAG`,cycle.flag,"BOOLEAN",true);
  await tab.playwright.getByRole("tab",{name:"Reference catalogues",exact:true}).click();await button(tab,"Add catalogue").click();
  await textFields(tab,panel(tab,"Reference catalogues"),`${cycle.runCode}_LIST`,cycle.catalogue);
  await panel(tab,"Reference catalogues").getByRole("textbox",{name:/^Change reason/}).fill("Create synthetic regression catalogue");
  await button(tab,"Create draft catalogue").click();await status(tab,"Draft catalogue created.");
  for(const [code,text] of [["CORE",cycle.original],["HEDGE",cycle.hedge]]){
    await button(tab,"Add entry").click();await textFields(tab,panel(tab,"Reference catalogues"),code,text);
    await panel(tab,"Reference catalogues").getByRole("textbox",{name:/^Change reason/}).fill("Add synthetic catalogue fixture");
    await label(tab,"This entry is ready for selection when the catalogue is published.").check();
    await button(tab,"Save draft catalogue entry").click();await status(tab,"Entry saved.");
  }
  await button(tab,"Publish catalogue").click();await confirm(tab,"Publish synthetic regression values");
  await button(tab,"Use for a trade field").click();await textFields(tab,panel(tab,"Custom fields"),`${cycle.runCode}_BUCKET`,cycle.bucket);
  await button(tab,"Publish field").click();await status(tab,"Field published.");
  cycle.checks.push("UI-created decimal, required Boolean and governed dropdown/catalogue");
  return cycle.checks;
}
async function booking(tab,cycle){await tab.goto(`${cycle.baseUrl}/trades/new?listingId=00000000-0000-7000-8000-000000000016`);await tab.playwright.waitForLoadState({state:"networkidle"});await label(tab,"Quantity").fill("12");await label(tab,"Execution price").fill("8.125");await label(tab,"Strategy").selectOption({label:"DEMO_INCOME · Demo Income Strategy"});}
export async function bookCycle(tab,cycle){
  await booking(tab,cycle);await label(tab,"Quantity").fill("0");await button(tab,"Review booking").press("Space");
  await tab.playwright.getByRole("heading",{name:"Check the following fields",exact:true}).waitFor({state:"visible"});
  const flag=label(tab,`${cycle.flag} (required)`);await flag.press("ArrowDown");await flag.selectOption("false");
  assert(await flag.getAttribute("aria-invalid")==="false","Edited required Boolean retained a stale error");
  assert(await tab.playwright.evaluate(()=>document.activeElement?.id)===await flag.getAttribute("id"),"Editing stole keyboard focus");
  assert(await label(tab,"Quantity").getAttribute("aria-invalid")==="true","Editing a property hid an unrelated quantity error");
  await label(tab,"Quantity").fill("12");assert(await label(tab,"Quantity").getAttribute("aria-invalid")==="false","Correcting quantity retained a stale error");
  // The earlier fixture also has a required Boolean. Complete every Boolean, preserving No.
  for(const select of await tab.playwright.getByRole("combobox").all()){
    const options=await select.evaluate(el=>Array.from(el.options).map(o=>o.value));
    if(options.includes("true")&&options.includes("false"))await select.selectOption("false");
  }
  await label(tab,`${cycle.numeric} (optional)`).fill("0");
  await tab.playwright.getByRole("searchbox",{name:`Search ${cycle.bucket}`,exact:true}).fill("CORE");
  await tab.playwright.getByRole("searchbox",{name:`Search ${cycle.bucket}`,exact:true}).press("Enter");
  await button(tab,`${cycle.original} CORE`).click();
  for(const [name,query,result] of [["counterparty","HSBC","HSBC Demo plc"],["executing broker","Fortem","Fortem Demo Management Ltd"],["trader","","MVP Operations Booker"]]){
    await label(tab,`Search ${name}`).fill(query);await button(tab,`Search ${name}`).press("Enter");await button(tab,result).click();
  }
  await label(tab,"Acceptance test").check();
  await button(tab,"Add reference").click();await label(tab,"Reference value").fill(cycle.runCode);
  await label(tab,"Comment").fill(cycle.runCode);
  await button(tab,"Review booking").press("Space");await contains(tab,"Review listed cash trade");
  const values=await tab.playwright.evaluate(()=>Array.from(document.querySelectorAll(".ticket-review>div")).map(el=>[el.querySelector("dt")?.textContent,el.querySelector("dd")?.textContent]));
  assert(values.some(([name,value])=>name===cycle.flag&&value==="No"),"Review did not display No");
  assert(values.some(([name,value])=>name===cycle.numeric&&value==="0"),"Review lost zero");
  await button(tab,"Back to edit").click();assert(await label(tab,`${cycle.numeric} (optional)`).getAttribute("value")==="0","Back to edit lost zero");
  await button(tab,"Review booking").press("Space");await button(tab,"Confirm booking").click();
  await tab.playwright.getByRole("heading",{name:"Trade properties and tags",exact:true}).waitFor({state:"visible"});
  cycle.tradeUrl=await tab.url();await contains(tab,cycle.original);await contains(tab,"No");
  for(const name of ["HSBC Demo plc","Fortem Demo Management Ltd","MVP Operations Booker","Acceptance test",cycle.runCode])await contains(tab,name);
  await tab.goto(`${cycle.baseUrl}/trades?range=all`);await tab.playwright.locator(`a[href^="${new URL(cycle.tradeUrl).pathname}?"]`).waitFor({state:"visible"});
  cycle.checks.push("Required validation clears on edit without focus theft; zero/No survive review-back-booking-history");return cycle.checks;
}
export async function lifecycleCycle(tab,cycle){
  await configuration(tab,cycle);await label(tab,"Search fields").fill(cycle.bucket);await button(tab,`Manage values for ${cycle.bucket}`).click();
  await button(tab,`Correct label for ${cycle.original}`).click();
  await panel(tab,"Reference catalogues").getByRole("textbox",{name:"Display label",exact:true}).fill(cycle.corrected);
  await panel(tab,"Reference catalogues").getByRole("textbox",{name:/^Change reason/}).fill("Correct label only, same business meaning");
  await label(tab,"The business meaning is unchanged.").check();await button(tab,"Publish corrected version").click();await status(tab,"Entry published.");
  await tab.goto(`${cycle.baseUrl}/trades/new?listingId=00000000-0000-7000-8000-000000000016`);await tab.playwright.getByRole("searchbox",{name:`Search ${cycle.bucket}`,exact:true}).fill("CORE");await tab.playwright.getByRole("searchbox",{name:`Search ${cycle.bucket}`,exact:true}).press("Enter");await button(tab,`${cycle.corrected} CORE`).waitFor({state:"visible"});
  await configuration(tab,cycle);await label(tab,"Search fields").fill(cycle.bucket);await button(tab,`Manage values for ${cycle.bucket}`).click();
  await button(tab,`Retire entry ${cycle.corrected}`).click();await confirm(tab,"Retire synthetic regression value");
  await tab.playwright.getByRole("tab",{name:"Custom fields",exact:true}).click();await label(tab,"Search fields").fill(cycle.numeric);await button(tab,`Edit definition for ${cycle.numeric}`).click();await button(tab,"Retire field").click();await confirm(tab);
  await tab.goto(`${cycle.baseUrl}/trades/new?listingId=00000000-0000-7000-8000-000000000016`);await tab.playwright.waitForLoadState({state:"networkidle"});
  assert(await label(tab,`${cycle.numeric} (optional)`).count()===0,"Retired field remains on a fresh ticket");
  await tab.playwright.getByRole("searchbox",{name:`Search ${cycle.bucket}`,exact:true}).fill("CORE");await tab.playwright.getByRole("searchbox",{name:`Search ${cycle.bucket}`,exact:true}).press("Enter");await contains(tab,"No matching published entries.");
  await tab.playwright.getByRole("searchbox",{name:`Search ${cycle.bucket}`,exact:true}).fill("HEDGE");await tab.playwright.getByRole("searchbox",{name:`Search ${cycle.bucket}`,exact:true}).press("Enter");await button(tab,`${cycle.hedge} HEDGE`).waitFor({state:"visible"});
  await tab.goto(cycle.tradeUrl);await contains(tab,cycle.original);const text=await tab.playwright.getByRole("main").innerText();assert(!text.includes(cycle.corrected),"Historical label changed after correction");
  const fields=await tab.playwright.evaluate(()=>Array.from(document.querySelectorAll(".detail-field")).map(el=>[el.querySelector("small")?.textContent,el.querySelector("strong")?.textContent]));
  assert(fields.some(([name,value])=>name?.startsWith(cycle.numeric)&&value==="0"),"Retirement lost historical zero");
  cycle.checks.push("Catalogue label correction and entry/field retirement preserve booked version and zero");return cycle.checks;
}
export async function isolationCycle(tab,cycle){
  await tab.goto(`${cycle.baseUrl}/select-tenant`);await button(tab,"Fortem Second Tenant FORTEM_SECOND_TENANT · TENANT_ADMIN Open workspace →").click();
  await tab.goto(cycle.tradeUrl);await contains(tab,"NOT FOUND");const text=await tab.playwright.getByRole("main").innerText();assert(!text.includes(cycle.original)&&!text.includes("API UNAVAILABLE"),"Foreign trade leaked or was mislabelled as an outage");
  await tab.goto(`${cycle.baseUrl}/trades?range=all`);await contains(tab,"No trades have been recorded for this tenant.");
  await configuration(tab,cycle);await contains(tab,"No fields match");
  cycle.checks.push("Equivalent-permission second tenant sees no foreign history, fields or trade values; NOT FOUND not outage");return cycle.checks;
}
export async function densityFields(tab,cycle,start=0,count=5){
  if(start===0){await tab.goto(`${cycle.baseUrl}/select-tenant`);await button(tab,"Fortem Demo Tenant FORTEM_DEMO_TENANT · TENANT_ADMIN Open workspace →").click();await configuration(tab,cycle);}
  for(let i=start;i<start+count;i++)await newField(tab,cycle,`${cycle.runCode}_D${i}`,`${cycle.runCode} optional ${String(i).padStart(2,"0")}`,"TEXT");
  return {createdThrough:start+count};
}
export async function inspectDensity(tab,cycle){
  await booking(tab,cycle);await button(tab,"Review booking").press("Space");
  const flag=label(tab,`${cycle.flag} (required)`);
  assert(await tab.playwright.evaluate(()=>document.activeElement?.id)!==await flag.getAttribute("id"),"Density navigation precondition: error summary should hold focus");
  try{await tab.playwright.getByRole("link",{name:`${cycle.flag} is required.`,exact:true}).press("Enter");}
  catch(error){
    // Native hash navigation can time out the Cua CDP key response after it
    // succeeds. Accept only that transport error AND the real DOM postcondition.
    if(!String(error).includes('Timed out running CDP command "Input.dispatchKeyEvent"') || await tab.playwright.evaluate(()=>document.activeElement?.id)!==await flag.getAttribute("id"))throw error;
    cycle.transportNotes=[...(cycle.transportNotes??[]),"Hash-navigation key response timed out; target focus verified from DOM."];
  }
  assert(await tab.playwright.evaluate(()=>document.activeElement?.id)===await flag.getAttribute("id"),"Heavy ticket error link missed its target");
  const metrics=await tab.playwright.evaluate(()=>({height:document.documentElement.scrollHeight,viewport:window.innerHeight,width:window.innerWidth,scrollWidth:document.documentElement.scrollWidth,properties:document.querySelectorAll(".ticket-property").length,requiredTop:document.querySelector(".ticket-property select[required]")?.getBoundingClientRect().top,optionalTop:Array.from(document.querySelectorAll("fieldset")).find(el=>el.querySelector("legend")?.textContent==="Optional properties")?.getBoundingClientRect().top}));
  assert(metrics.properties>=20,"Density test needs at least 20 properties");
  assert(metrics.requiredTop<metrics.optionalTop,"Required properties must precede optional properties");
  cycle.density=metrics;cycle.checks.push("Property-heavy ticket: required-first ordering and error-target keyboard navigation verified");return metrics;
}
export async function densityReview(tab,cycle){
  for(const select of await tab.playwright.getByRole("combobox").all()){
    const options=await select.evaluate(el=>Array.from(el.options).map(o=>o.value));
    if(options.includes("true")&&options.includes("false"))await select.selectOption("false");
  }
  for(const index of ["00","19"])await label(tab,`${cycle.runCode} optional ${index} (optional)`).fill(`Sample ${index}`);
  await button(tab,"Review booking").press("Space");await contains(tab,"Sample 00");await contains(tab,"Sample 19");
  await button(tab,"Back to edit").click();
  for(const index of ["00","19"])assert(await label(tab,`${cycle.runCode} optional ${index} (optional)`).getAttribute("value")===`Sample ${index}`,"Heavy review-back lost an optional value");
  cycle.checks.push("Property-heavy first/last optional values survive review and back-to-edit; not booked");return cycle.checks;
}
