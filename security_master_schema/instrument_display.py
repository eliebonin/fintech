"""Read-only identity presentation; no financial calculation or identifier allocation."""


def make_instrument_display(*,name,kind=None,identifiers=(),symbol=None,venue=None,currency=None,
                            currency_role=None,tenant_identifier=None,search_aliases=(),type_label=None):
    def clean(value):return value.strip() if isinstance(value,str) and value.strip() else None
    identifiers=[dict(scheme=str(row['scheme']).upper(),value=clean(row.get('value')))
        for row in identifiers if row.get('scheme') and clean(row.get('value'))]
    def first(schemes):
        return next((row for scheme in schemes for row in identifiers if row['scheme']==scheme),None)
    standard=first(('ISIN','FIGI','CUSIP','SEDOL','RIC'))
    native=first(('OCC_SYMBOL','EXCHANGE_SYMBOL','TICKER'))
    symbol=clean(symbol);tenant_identifier=clean(tenant_identifier)
    if kind=='SWAP' and tenant_identifier:
        identifier=dict(scheme='TENANT_REFERENCE',value=tenant_identifier)
    elif symbol and kind in {'EQUITY','ETF','ETP','FUTURE','OPTION','DIGITAL_ASSET'}:
        scheme='CONTRACT_SYMBOL' if kind in {'FUTURE','OPTION'} else 'TRADING_PAIR' if kind=='DIGITAL_ASSET' else 'TICKER'
        identifier=dict(scheme=scheme,value=symbol)
    elif kind in {'FUTURE','OPTION'}:identifier=native or standard
    else:identifier=standard
    fisn=first(('FISN',))
    primary=clean(name) or (fisn['value'] if fisn else 'Instrument name unavailable')
    context=[value for value in (clean(venue),f'{currency} {currency_role}' if clean(currency) and clean(currency_role) else None) if value]
    aliases=[primary,*(row['value'] for row in identifiers),symbol,tenant_identifier,*context,*search_aliases]
    return dict(primaryName=primary,identifier=identifier,context=list(dict.fromkeys(context)),
        instrumentType=kind,instrumentTypeLabel=type_label,
        searchText=' '.join(dict.fromkeys(clean(value) for value in aliases if clean(value))),
        basis='CURRENT_ACCESSIBLE_METADATA')
