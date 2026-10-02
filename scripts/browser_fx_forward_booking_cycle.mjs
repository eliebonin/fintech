/** Browser-control acceptance runner. Never targets the operator's app/database. */
export async function bookForwardCycle(tab,{baseUrl,syntheticOnly,contractName,strategyLabel,counterparty,side="BUY",quantity="1000000",tradeTime="2026-10-01T10:00:00Z",completeProperties}) {
  if(baseUrl!=="http://127.0.0.1:3001"||syntheticOnly!==true)throw new Error("Isolated synthetic review instance required");
  const button=name=>tab.playwright.getByRole("button",{name,exact:true});
  await tab.goto(`${baseUrl}/trades/new?product=FX_FORWARD`);
  await tab.playwright.getByLabel("Search FX-forward contracts",{exact:true}).fill(contractName);
  await button("Search contracts").click();await button("Select contract").click();
  await tab.playwright.getByRole("combobox",{name:"Strategy",exact:true}).selectOption({label:strategyLabel});
  await tab.playwright.getByRole("combobox",{name:"Side",exact:true}).selectOption(side);
  await tab.playwright.getByRole("textbox",{name:"Base-currency amount",exact:true}).fill(quantity);
  await tab.playwright.getByRole("textbox",{name:"Trade time",exact:true}).fill(tradeTime);
  await tab.playwright.getByRole("textbox",{name:"Search counterparty",exact:true}).fill(counterparty);
  await button("Search counterparty").click();await button(counterparty).click();
  if(completeProperties)await completeProperties(tab);
  await button("Review booking").click();
  await tab.playwright.getByRole("heading",{name:"Review FX-forward trade",exact:true}).waitFor({state:"visible"});
  await button("Back to edit").click();
  await button("Review booking").click();await button("Confirm booking").click();
  await tab.playwright.getByRole("heading",{name:"FX-forward obligations · booking snapshot",exact:true}).waitFor({state:"visible"});
  return {side,quantity,tradeUrl:await tab.url()};
}
