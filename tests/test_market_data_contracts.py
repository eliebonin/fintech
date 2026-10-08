"""Generic guards must agree with inclusive request bounds before DB access."""
from datetime import date,datetime,timezone
import pytest


def test_generic_ingestion_rejects_one_day_over_inclusive_bound_before_db():
    from market_data.ingestion import ingest_delivery
    from market_data.contracts import ProviderSpec
    with pytest.raises(ValueError,match='bounded'):
        ingest_delivery(None,provider=ProviderSpec('TEST',('CLOSE',),1024,2),parser=None,
            dataset_id=None,namespace_id=None,symbol='A',raw_payload='{}',delivery_key='test',
            received_at=datetime(2026,10,7,tzinfo=timezone.utc),start=date(2026,10,1),end=date(2026,10,3))
