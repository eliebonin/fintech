import {describe,it,expect} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import {TradeConfigurationConsole} from "./trade-configuration-console";
import {FieldRegister,Panel,Pager,SectionTabs,TextFields} from "./configuration-ui";
describe("trade configuration navigation",()=>{
  it("separates fixed fields, custom fields, catalogues and audit",()=>{
    const html=renderToStaticMarkup(<TradeConfigurationConsole tenantId="tenant"/>);
    for(const label of ["Standard fields","Custom fields","Reference catalogues","Audit history","does not grant login access"]){expect(html).toContain(label);}
    expect(html).toContain("/tenant-profile");
  });
  it("starts with browsing, not four permanently open creation forms",()=>{
    const html=renderToStaticMarkup(<TradeConfigurationConsole tenantId="tenant"/>);
    expect(html).toContain("Add field");
    expect(html).not.toContain('name="code"');
    expect(html).not.toContain('name="description"');
    expect(html).not.toContain("Confirm catalogue action");
    expect(html).toContain("Search fields");
  });
  it("links keyboard tabs to persistent labelled panels",()=>{
    const html=renderToStaticMarkup(<SectionTabs current="Custom fields" disabled={false} onChange={()=>{}}/>);
    expect(html).toContain('role="tablist"');
    expect(html).toContain('aria-controls="configuration-panel-1" aria-selected="true" tabindex="0"');
    const panel=renderToStaticMarkup(<Panel current="Custom fields" section="Reference catalogues">Draft stays mounted</Panel>);
    expect(panel).toContain('hidden=""');
    expect(panel).toContain('aria-labelledby="configuration-tab-2"');
    expect(panel).toContain("Draft stays mounted");
  });
  it("makes governed values discoverable without exposing raw source UUIDs",()=>{
    const html=renderToStaticMarkup(<FieldRegister fields={[{definitionId:"id",code:"BUCKET",label:"Booking bucket",description:"Trade purpose",valueType:"REFERENCE",catalogueId:"source-uuid",required:false,versionNo:2,status:"ACTIVE"}]} busy={false} onEdit={()=>{}} onValues={()=>{}}/>);
    expect(html).toContain("Manage values for Booking bucket");
    expect(html).toContain("Edit definition for Booking bucket");
    expect(html).toContain("Dropdown");
    expect(html).not.toContain("source-uuid");
    expect(html).toContain('scope="row"');
  });
  it("keeps retired fields read-only and names their historical status",()=>{
    const html=renderToStaticMarkup(<FieldRegister fields={[{definitionId:"old",code:"BUCKET",label:"Booking bucket",description:null,valueType:"CHOICE",catalogueId:null,required:false,versionNo:1,status:"RETIRED"}]} busy={false} onEdit={()=>{}} onValues={()=>{}}/>);
    expect(html).toContain("Legacy dropdown · history only");
    expect(html).not.toContain("Edit definition");
    expect(html).toContain("Retired");
  });
  it("uses a plain empty state and bounded pagination",()=>{
    expect(renderToStaticMarkup(<FieldRegister fields={[]} busy={false} onEdit={()=>{}} onValues={()=>{}}/>)).toContain("No fields match");
    const html=renderToStaticMarkup(<Pager offset={25} count={6} total={31} next={false} busy={false} label="fields" onPage={()=>{}}/>);
    expect(html).toContain("26–31 of 31");
    expect(html).toContain('disabled="">Next fields');
  });
  it("explains stable codes and ties labels and hints to form inputs",()=>{
    const html=renderToStaticMarkup(<TextFields prefix="field" fixedCode initial={{code:"BUCKET",label:"Booking bucket"}}/>);
    expect(html).toMatch(/readonly=""/i);
    expect(html).toContain('for="field-label"');
    expect(html).toContain('aria-describedby="field-code-help"');
    expect(html).toContain("same business meaning across versions");
  });
});
