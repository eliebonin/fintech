import type {components} from "api-contracts";
export type EquityCreationOption=components["schemas"]["EquityCreationOption"];



/** Only an explicit catalogue choice may attach source provenance to a proposal. */

export function equityCreationPayload(draft:Record<string,unknown>,mode:string,option?:EquityCreationOption,source:Record<string,unknown>={}) {

  const payload:Record<string,unknown>={...draft,listings:[],submissionMode:mode};

  if(mode==='AUTOMATED'){

    if(!option)throw new Error('Select a configured automation source and policy.');

    if(typeof source.sourceExternalId!=='string'||!source.sourceExternalId.trim())throw new Error('Enter the source instrument identifier.');

    Object.assign(payload,source,{sourceSystemId:option.sourceSystemId,sourceNamespace:option.sourceNamespace,

      automationPolicyCode:option.policyCode,sourceObjectType:'INSTRUMENT'});

  }

  return payload;

}



/** Nullable directory fields must never become visible placeholder text. */

export function equityIssuerLabel(issuer:{displayName:string;legalName?:string|null}):string {

  return issuer.legalName && issuer.legalName!==issuer.displayName

    ?`${issuer.displayName} · ${issuer.legalName}`:issuer.displayName;

}
