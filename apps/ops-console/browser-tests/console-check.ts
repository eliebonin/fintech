import {test as base,expect} from '@playwright/test';

/** Fail real browser journeys on UI diagnostics, not deliberately rejected HTTP probes. */
export const test=base.extend<{consoleCheck:void}>({
 consoleCheck:[async({page},use,testInfo)=>{
  const issues:string[]=[];
  const onConsole=(message:import('@playwright/test').ConsoleMessage)=>{
   if(!['error','warning'].includes(message.type()))return;
   // Negative-path tests intentionally exercise 4xx/5xx responses and display their errors.
   if(/^Failed to load resource: the server responded with a status of \d{3}/.test(message.text()))return;
   issues.push(`${message.type()}: ${message.text()}`);
  };
  const onError=(error:Error)=>issues.push(`pageerror: ${error.message}`);
  page.on('console',onConsole);page.on('pageerror',onError);
  await use();
  page.off('console',onConsole);page.off('pageerror',onError);
  if(issues.length)await testInfo.attach('browser-console',{body:issues.join('\n\n'),contentType:'text/plain'});
  expect(issues,'Browser HTML, hydration and runtime diagnostics').toEqual([]);
 },{auto:true}],
});

export {expect,type Page} from '@playwright/test';
