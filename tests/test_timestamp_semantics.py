import pytest

@pytest.mark.parametrize('semantics', ['SOURCE_DAILY_BAR', 'PROVIDER_DAILY_BAR_TIMESTAMP'])
def test_daily_bar_timestamp_is_not_an_intraday_instant(semantics):
    from market_data.policy_selection import is_daily_bar
    assert is_daily_bar({'TIMESTAMP_SEMANTICS': {semantics}})

def test_explicit_instant_is_not_misclassified():
    from market_data.policy_selection import is_daily_bar
    assert not is_daily_bar({'TIMESTAMP_SEMANTICS': {'OBSERVATION_INSTANT'}})
