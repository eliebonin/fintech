import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {LifecycleAllocationFields} from './lifecycle-allocation-fields';
it('shows inherited classifications read-only and before/after quantities',()=>{
 const html=renderToStaticMarkup(<LifecycleAllocationFields tenantId="tenant" disabled={false} inputs={{}} onChange={()=>{}} movements={[{
 movementKey:'a'.repeat(64),subjectId:'sample',quantity:'-800000',cleanAmount:'800000',annotationIssues:[],
 annotationFields:[{definitionId:'field',label:'Mandate',valueType:'TEXT',required:true,behavior:'ALLOCATION',locked:true,value:'Core',displayValue:'Core'}]}]}/>);
 expect(html).toContain('Mandate');expect(html).toContain('Core');expect(html).toContain('Inherited');expect(html).toContain('800,000');expect(html).toContain('After booking');
 expect(html).not.toContain('<input');
});
it('shows missing required new metadata without replacing it with zero',()=>{
 const html=renderToStaticMarkup(<LifecycleAllocationFields tenantId="tenant" disabled={false} inputs={{}} onChange={()=>{}} movements={[{
 movementKey:'b'.repeat(64),subjectId:'sample',quantity:'-10',cleanAmount:'10',annotationIssues:['Required value missing'],
 annotationFields:[{definitionId:'field',label:'Processing reason',valueType:'DECIMAL',required:true,behavior:'INPUT',locked:false,value:null}]}]}/>);
 expect(html).toContain('Processing reason');expect(html).toContain('Required value missing');expect(html).toContain('required');expect(html).toContain('value=""');
});
