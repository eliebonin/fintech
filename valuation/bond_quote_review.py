"""Revalidate only the paired DIRTY inputs introduced by bond normalization."""
from datetime import datetime,timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID
from .economics import evidence_hash


def assert_current_normalized_bond_quotes(c,tenant,header,items):
    retained=[]
    for item in items:
        for selection in (item.get('evidence') or {}).get('selections',[]):
            if (selection.get('pricing_evidence') or {}).get('bondPriceNormalization'):retained.append(selection)
    if not retained:return
    from .service import _selection
    from .bond_prices import normalize_bond_selection
    request=header['summary']['request'];now=datetime.now(timezone.utc)
    current=SimpleNamespace(tenant_id=tenant,strategy_id=header['strategy_id'],policy_id=UUID(request['policy_id']),
        cut_id=UUID(request['cut_id']),information_cutoff=now)
    seen=set()
    for old in retained:
        key=(old['market_data_observation_id'] or (old.get('pricing_evidence') or {}).get('manualOverride',{}).get('requestId'),old['valuation_date'])
        if key in seen:continue
        seen.add(key)
        try:
            cutoff=datetime.fromisoformat(old['valuation_cutoff_utc'])
            _,fresh=_selection(c,current,UUID(old['subject_reference_node_id']),cutoff,'BOND')
            fresh=normalize_bond_selection(c,fresh,now)
            identifiers=('market_data_observation_id','market_data_series_id','policy_rule_id','market_data_vintage_id','dataset_id','acquisition_licence_id','currency_id')
            if (any(str(old.get(name))!=str(getattr(fresh,name)) for name in identifiers)
                or str(fresh.pricing_date_used)!=old['pricing_date_used']
                or Decimal(old['selected_value'])!=fresh.selected_value or Decimal(old['valuation_value'])!=fresh.valuation_value
                or evidence_hash(old['pricing_evidence']['bondPriceNormalization'])!=evidence_hash((fresh.pricing_evidence or {}).get('bondPriceNormalization'))):
                raise ValueError('Paired source quotation differs')
        except (ValueError,LookupError,PermissionError,TypeError) as exc:
            raise ValueError('Bond quotation inputs changed or are no longer eligible; recalculate before publication') from exc
