"""Read-only legacy export preparation. No market-data or booking shortcuts.

Source CSV bytes remain immutable evidence. Normalized buckets are preparation,
not booked trades, income, account balances or approved instrument definitions.
"""
import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re

KINDS=('strategy_info','currencies','trades','all_instruments','bonds','swaps',
       'prices','fx_rates','cash_balances','accrued_interests')
OPTIONAL_KINDS=('funds','options','futures','structured','structured_composition',
                'barriers','indices','instrument_types','instruments','bond_schedules')


def source_id(value):
    """CSV integer identifiers may have .0; never pass through binary floats."""
    if not value:return ''
    try:
        parsed=Decimal(value)
        if not parsed.is_finite() or parsed!=parsed.to_integral_value() or parsed<0:
            raise ValueError('Invalid source identifier')
        return format(parsed.quantize(Decimal('1')),'f')
    except InvalidOperation as exc:raise ValueError('Invalid source identifier') from exc


def document(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')


def source_trade_active(row):
    """Older export variants omit activity; explicit flags must be unambiguous."""
    if 'active' not in row:return True
    flag=str(row['active']).strip().casefold()
    if flag not in ('true','false'):raise ValueError('Invalid source trade activity flag')
    return flag=='true'


@dataclass(frozen=True)
class Bundle:
    name:str
    as_of:date
    files:dict
    tables:dict
    positions:list
    flows:list
    bonds:list
    manifest:dict
    digest:str


def load_bundle(directory,name,as_of,*,excluded_trade_ids=(),amc_ids=(),include_details=False):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',name):raise ValueError('Invalid bundle name')
    files={};tables={};variants={};excluded=set(excluded_trade_ids);amcs=set(amc_ids)
    kinds=list(KINDS)+[k for k in OPTIONAL_KINDS if include_details and (Path(directory)/f'{name}-{as_of}-{k}.csv').exists()]
    for kind in kinds:
        path=Path(directory)/f'{name}-{as_of}-{kind}.csv'
        if kind=='fx_rates' and not path.exists():
            path=Path(directory)/f'{name}-{as_of}-fx.csv'
            variants[kind]='CURRENCY_IDS_FX_FILE'
        raw=path.read_bytes()
        if len(raw)>4*1024*1024:raise ValueError('Source file exceeds bounded seed size')
        reader=csv.DictReader(StringIO(raw.decode('utf-8-sig'),newline=''))
        if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)):
            raise ValueError('Duplicate or missing CSV headers')
        rows=list(reader)
        if len(rows)>100000:raise ValueError('Source file exceeds bounded seed rows')
        if any(None in r or any(v is None for v in r.values()) for r in rows):raise ValueError('Malformed CSV row')
        files[kind]=raw;tables[kind]=rows
    strategies=tables['strategy_info']
    if len(strategies)!=1 or strategies[0]['strategy_name']!=name or strategies[0]['active']!='True':
        raise ValueError('Expected one active source strategy')
    strategy=strategies[0];sid=source_id(strategy['strategy_id'])
    currencies={source_id(r['currency_id']):r['currency'] for r in tables['currencies']}
    if len(currencies)!=len(tables['currencies']):raise ValueError('Duplicate source currency IDs')
    if variants.get('fx_rates'):
        for row in tables['fx_rates']:
            for side in ('base','quote'):
                code=currencies.get(source_id(row.get(side+'_currency_id')))
                if not code:raise ValueError('Unknown FX currency identifier')
                if row.get(side+'_currency') and row[side+'_currency']!=code:
                    raise ValueError('FX currency code conflicts with source identifier')
                row[side+'_currency']=code
    base=currencies.get(source_id(strategy['strategy_currency_id']))
    if not base:raise ValueError('Unknown strategy currency')
    instruments={source_id(r['instrument_id']):r for r in tables['all_instruments']}
    if len(instruments)!=len(tables['all_instruments']):raise ValueError('Duplicate source instrument IDs')
    trades=tables['trades']
    if len({r['trade_id'] for r in trades})!=len(trades):raise ValueError('Duplicate trade IDs')
    positions=[];flows=[];removed=[];inactive=[];dates=[]
    for row in trades:
        if source_id(row['strategy_id'])!=sid:raise ValueError('Trade belongs to a different strategy')
        day=datetime.fromisoformat(row['trade_datetime_utc']).date()
        if day>as_of:raise ValueError('Trade after bundle cutoff')
        active=source_trade_active(row)
        if row['trade_id'] in excluded:removed.append(row['trade_id']);continue
        if not active:inactive.append(row['trade_id']);continue
        iid=source_id(row['instrument_id'])
        if iid not in instruments:raise ValueError('Missing instrument for source trade')
        for field in ('quantity','price'):
            try:valid=Decimal(row[field]).is_finite()
            except InvalidOperation:valid=False
            if not valid:raise ValueError('Nonfinite or missing trade economics')
        if row['trade_type']=='RESET':
            if instruments[iid]['instrument_type']!='CURRENCY':raise ValueError('RESET is not a currency flow')
            flows.append(dict(row))
        else:positions.append(dict(row))
        dates.append(day)
    if not dates:raise ValueError('No retained source trades')
    for kind,field in [('prices','date'),('fx_rates','date'),('accrued_interests','value_date'),('cash_balances','trade_datetime_utc')]:
        for row in tables[kind]:
            if datetime.fromisoformat(row[field]).date()>as_of:raise ValueError(f'{kind} after bundle cutoff')
    retained_ids={r['trade_id'] for r in positions}
    known_accrual_ids=retained_ids|set(inactive)
    if any(r['trade_id'] not in known_accrual_ids for r in tables['accrued_interests']):raise ValueError('Accrual refers to an unavailable position trade')
    for row in tables['swaps']:
        for field in ('instrument_id','funded_instrument_id','funding_instrument_id'):
            if row.get(field) and source_id(row[field]) not in instruments:raise ValueError('Missing swap dependency')
    required={base}
    required.update(r['trade_currency'] for r in positions+flows if r.get('trade_currency'))
    required.update(r['trade_currency'] for r in tables['cash_balances'] if r.get('trade_currency'))
    required.update(r['currency'] for r in instruments.values() if r.get('currency'))
    if required-set(currencies.values()):raise ValueError('Required currency missing from source catalogue')
    organisations=sorted({source_id(r['counterparty_id']) for r in trades+tables['cash_balances'] if r.get('counterparty_id')})
    bonds=[dict(r) for r in tables['bonds'] if source_id(r['instrument_id']) not in amcs]
    manifest=dict(schemaVersion=1,sourceStrategyId=sid,sourceName=name,asOf=str(as_of),baseCurrency=base,
        earliestTradeDate=str(min(dates)),files={k:dict(sha256=sha256(v).hexdigest(),rows=len(tables[k])) for k,v in files.items()},
        positionTradeCount=len(positions),datedResetFlowCount=len(flows),resetValueDateField='trade_datetime_utc (source UTC date)',
        excludedTradeIds=sorted(excluded),removedTradeIds=sorted(removed),amcSourceIds=sorted(amcs),ignoredAmcBondRows=len(tables['bonds'])-len(bonds),
        requiredCurrencies=sorted(required),unmappedOrganisationIds=organisations,
        financialPostingStatus='NOT_POSTED',marketDataRights='NOT_INFERRED_FROM_FILE_POSSESSION',
        limitations=['FINAL_OPEN_INSTRUMENT_UNIVERSE_ONLY','NO_CORPORATE_ACTION_EXPORT','NO_EXPECTED_PNL_EXPORT',
            'INSTRUMENT_TERMS_AND_QUOTE_SEMANTICS_REQUIRE_MAPPING','SOURCE_DATE_NOT_PUBLICATION_TIME'])
    if variants:manifest['sourceSchemaVariants']=variants
    if inactive:manifest['inactiveTradeIds']=sorted(inactive)
    digest=sha256(document(manifest)).hexdigest()
    return Bundle(name,as_of,files,tables,positions,flows,bonds,manifest,digest)


def retain_files(bundle,directory):
    """Content-addressed private operator evidence, outside versioned fixtures."""
    root=Path(directory)/bundle.digest;root.mkdir(parents=True,exist_ok=True)
    retained={}
    for kind,content in dict(bundle.files,manifest=document(bundle.manifest)).items():
        path=root/(kind+('.json' if kind=='manifest' else '.csv'))
        if path.exists():
            if path.read_bytes()!=content:raise ValueError('Retained file differs from its content identity')
        else:
            with path.open('xb') as handle:handle.write(content)
        retained[kind]=path.resolve()
    return retained
