import {describe,it,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {TradeConfigurationConsole} from './trade-configuration-console';
import {ProfileEditor} from '@/features/trade-profiles/profile-editor';
import {FieldLibrary} from '@/features/trade-profiles/field-library';
import {StrategyTradeProfile} from '@/features/trade-profiles/strategy-trade-profile';
describe('profile-first configuration navigation',()=>{
 it('separates profiles, definitions, reference data and history',()=>{
  const html=renderToStaticMarkup(<TradeConfigurationConsole tenantId="tenant"/>);
  for(const text of ['Profiles','Field library','History','Reference data','Create profile'])expect(html).toContain(text);
  expect(html).not.toContain('Required for every new trade');expect(html).not.toContain('name="code"');
 });
 it('keeps native standard fields and lifecycle meaning explicit',()=>{
  const html=renderToStaticMarkup(<ProfileEditor tenantId="tenant" onSaved={()=>{}} onCancel={()=>{}}/>);
  for(const text of ['Counterparty','Executing broker','Trader','Comment','Lifecycle rules','Review publication'])expect(html).toContain(text);
  expect(html).not.toContain('Publish version');
 });
 it('describes shared meaning without global required switches',()=>{
  const html=renderToStaticMarkup(<FieldLibrary tenantId="tenant"/>);
  expect(html).toContain('type and source once');expect(html).toContain('Required/optional rules');expect(html).not.toContain('Required for every');
 });
 it('does not offer assignment controls until scoped authority is known',()=>{
  const html=renderToStaticMarkup(<StrategyTradeProfile tenantId="tenant" strategyId="strategy"/>);
  expect(html).toContain('Loading assigned profile');expect(html).not.toContain('Change assigned profile');
 });
});
