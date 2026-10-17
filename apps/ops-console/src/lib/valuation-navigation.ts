/** Cross-tab navigation must reveal the disclosure before moving DOM focus. */
export function openValuationInputs(activate:()=>void){
 activate();requestAnimationFrame(()=>{
  const target=document.getElementById('valuation-input-register');
  const disclosure=target?.closest('details');if(disclosure)disclosure.open=true;
  target?.setAttribute('tabindex','-1');target?.focus();target?.scrollIntoView({block:'start',behavior:'smooth'});
 });
}
