"""Regression: pytest must reject the operating DB before connecting."""
import pytest
from sqlalchemy import create_engine

def test_operating_database_connections_are_blocked_before_network_access():
    engine=create_engine('postgresql+psycopg://unused:unused@127.0.0.1:1/fortem_secm?connect_timeout=1')
    with pytest.raises(RuntimeError,match='Operating database'):
        engine.connect()
    engine.dispose()
