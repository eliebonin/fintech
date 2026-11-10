import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it} from 'vitest';
import {AllocationPolicyFields} from './lifecycle-allocation-policy';
it('uses tenant-defined field labels and defaults to fresh input',()=>{
 const html=renderToStaticMarkup(<AllocationPolicyFields fields={[{definitionId:'id',label:'Custom mandate',code:'CUSTOM',description:null,valueType:'TEXT',catalogueId:null,required:false,versionNo:1,status:'ACTIVE'}]} rules={{}} disabled={false} onChange={()=>{}}/>);
 expect(html).toContain('Custom mandate');expect(html).toContain('value="INPUT" selected=""');expect(html).toContain('Preserve position allocation');expect(html).not.toContain('investment_bucket');
});
it('keeps allocation and non-allocation inheritance as separate behaviors',()=>{
 const html=renderToStaticMarkup(<AllocationPolicyFields fields={[{definitionId:'id',label:'Sleeve',code:'SLEEVE',description:null,valueType:'TEXT',catalogueId:null,required:true,versionNo:1,status:'ACTIVE'}]} rules={{id:'ALLOCATION'}} disabled onChange={()=>{}}/>);
 expect(html).toContain('value="ALLOCATION" selected=""');expect(html).toContain('Inherit when sources agree');expect(html).toContain('<small>Required</small>');expect(html).toContain('disabled');
});
