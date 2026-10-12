"""Retained financial evidence does not bypass current market-data permissions."""
from uuid import UUID
from market_data.display_access import assert_dataset_display, EvidenceDisplayDenied


def batch_datasets(batch):
    datasets=set()
    try:
        if not batch['items']:
            from .position_storage import valid_empty_summary
            if valid_empty_summary(batch.get('summary',{})): return set()
            raise ValueError('Missing source population')
        for item in batch['items']:
            selections=item['evidence']['selections']
            if not selections:
                from decimal import Decimal
                evidence=item['evidence']; bucket=evidence.get('identity',{}).get('bucket',{})
                if (item.get('position_key') and evidence.get('resultFormat')=='POSITION_V2'
                    and evidence.get('noMarketMarksRequired') is True
                    and Decimal(bucket['opening_quantity'])==Decimal(bucket['closing_quantity'])==0
                    and evidence['identity']['facts']):
                    continue
                raise ValueError('Missing source evidence')
            for selection in selections:
                datasets.add(UUID(str(selection['dataset_id'])))
    except (KeyError,ValueError,TypeError,ArithmeticError) as exc:
        raise EvidenceDisplayDenied('Source dataset evidence is incomplete; disclosure cannot be authorised.') from exc
    return datasets


def assert_batch_display(c, tenant, batch):
    datasets=batch_datasets(batch)
    contexts=[]
    try:
        for item in batch['items']:
            for selection in item['evidence'].get('selections', []):
                contexts.append((UUID(str(selection['dataset_id'])),
                    UUID(str(selection['market_data_series_id'])) if selection.get('market_data_series_id') else None))
    except (KeyError,ValueError,TypeError) as exc:
        raise EvidenceDisplayDenied('Source coverage evidence is incomplete; disclosure cannot be authorised.') from exc
    assert_dataset_display(c,tenant,datasets,series_contexts=contexts)
