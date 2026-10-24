export type Counts={status:string;total:number;valid:number;invalid:number;applied:number;replayed:number};
export type ImportRow={row:number;sourceTradeId:string;status:string;values?:Record<string,string>;errors:{field:string;code:string;message:string}[];evidence?:{currency:string;instrumentType:string;instrumentId?:string;listingId?:string}};
export type ImportJob=Counts&{jobId:string;strategyId:string;source:string;filename:string;createdAt:string;reviewHash?:string;rows:ImportRow[];receipt:{row:number;sourceTradeId:string;tradeId:string;outcome:string}[];offset:number;limit:number};
export function importStatus(job:Counts):string{
 if(job.status==='APPLIED')return `${job.applied} booked · ${job.replayed} already booked`;
 if(job.status==='RECEIVED')return 'File received · not validated · 0 booked';
 return `${job.total} checked · ${job.valid} valid · ${job.invalid} ${job.invalid===1?'error':'errors'} · 0 booked`;
}
export function canConfirm(job:Counts):boolean{return job.status==='READY'&&job.total>0&&job.invalid===0;}
export function decodeFile(dataUrl:string):string{
 const marker=';base64,';const i=dataUrl.indexOf(marker);
 if(i<0)throw new Error('The file could not be read. Select it again.');
 return dataUrl.slice(i+marker.length);
}

export function statusLabel(status:string):string{
 return ({RECEIVED:'Awaiting validation',NEEDS_CORRECTION:'Needs correction',READY:'Ready to book',APPLIED:'Booking completed',
  INVALID:'Needs correction',VALID:'Validated',REPLAY:'Already booked'} as Record<string,string>)[status]??'Status unavailable';
}
export function formatImportDate(value:string):string{
 const date=new Date(value.replace(' ','T'));
 if(!Number.isFinite(date.getTime()))return 'Date unavailable';
 return new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'UTC'}).format(date)+' UTC';
}
export function fieldLabel(key:string):string{
 if(key.startsWith('property:')||key.startsWith('properties.'))return 'Custom field';
 return ({sourceTradeId:'Source trade ID',listingId:'Listing',side:'Side',quantity:'Quantity',executionPrice:'Execution price',
  tradeCurrency:'Trade currency',tradeDatetime:'Execution date & time',settlementDate:'Settlement date',tradePurpose:'Purpose',
  marketActivity:'Market activity',valuationEffectiveDate:'Effective valuation date',valuationOverrideReason:'Valuation date override reason',
  counterpartyOrganisationId:'Counterparty',executingBrokerOrganisationId:'Executing broker',traderPersonId:'Trader',
  externalReference:'External reference',clientReference:'Client reference',brokerReference:'Broker reference',referenceSource:'Reference source',
  tagId:'Tag',tagIds:'Tags',comment:'Comment',file:'File',row:'Row'} as Record<string,string>)[key]??key;
}
