import {it,expect} from 'vitest';
import {ruleLabel,updateRule,defaultRules} from './model';
it('keeps a field once and resets hidden lifecycle behavior',()=>{
 let rules=defaultRules();rules=updateRule(rules,{standardFieldKey:'COUNTERPARTY',requirement:'REQUIRED',lifecycleBehavior:'ALLOCATION'});
 expect(rules.filter(r=>r.standardFieldKey==='COUNTERPARTY')).toHaveLength(1);
 rules=updateRule(rules,{standardFieldKey:'COUNTERPARTY',requirement:'NOT_USED',lifecycleBehavior:'ALLOCATION'});
 expect(rules.find(r=>r.standardFieldKey==='COUNTERPARTY')?.lifecycleBehavior).toBe('INPUT');
 expect(ruleLabel('ALLOCATION')).toContain('separate');
});
