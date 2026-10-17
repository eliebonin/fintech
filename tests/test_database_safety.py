"""Regression: pytest must reject the operating DB before connecting."""
import pytest
from sqlalchemy import create_engine

@pytest.mark.parametrize('database', ['platform_secm', 'existing_workspace', 'customer_production', 'platform_isolated_tests_production'])
def test_operating_database_connections_are_blocked_before_network_access(database):
    engine=create_engine(f'postgresql+psycopg://unused:unused@127.0.0.1:1/{database}?connect_timeout=1')
    with pytest.raises(RuntimeError,match='Operating database'):
        engine.connect()
    engine.dispose()


@pytest.mark.parametrize('prefix', [
    'platform_isolated_tests_', 'platform_index_migration_',
    'platform_interest_migration_', 'platform_valuation_migration_',
    'platform_choice_cleanup_test_', 'platform_fx_signoff_',
])
def test_known_owned_fixture_names_remain_usable(prefix):
    from tests.conftest import reject_operating_database
    # Exercise the actual pre-connect validator without opening any socket.
    reject_operating_database(None, None, (), {'dbname': prefix + '0' * 32})
