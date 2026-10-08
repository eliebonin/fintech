from datetime import date
from market_data.calendar_composition import compose_day, reference_day

DAY = date(2026, 8, 31)

def test_all_open_closes_on_one_required_centre():
    result = compose_day(DAY, 'ALL_OPEN', [0,1,2,3,4], {'IE':'OPEN','UK':'CLOSED','US':'OPEN'}, None)
    assert result['status'] == 'CLOSED'
    assert result['components']['UK'] == 'CLOSED'

def test_unknown_never_defaults_to_open():
    assert compose_day(DAY,'ALL_OPEN',[0,1,2,3,4],{'IE':'OPEN','US':'UNKNOWN'},None)['status']=='UNKNOWN'
    assert compose_day(DAY,'ANY_OPEN',[0,1,2,3,4],{'IE':'CLOSED','US':'UNKNOWN'},None)['status']=='UNKNOWN'

def test_any_open_is_not_all_open():
    assert compose_day(DAY,'ANY_OPEN',[],{'UK':'CLOSED','US':'OPEN'},None)['status']=='OPEN'

def test_exception_can_reopen_weekend_with_evidence():
    result=compose_day(date(2026,8,30),'WEEKDAYS',[0,1,2,3,4],{},dict(status='OPEN',reason='Exceptional NAV',sourceReference='Administrator notice'))
    assert result['status']=='OPEN' and result['sourceReference']=='Administrator notice'

def test_explicit_schedule_omissions_are_unknown():
    assert compose_day(DAY,'EXPLICIT',[],{},None)['status']=='UNKNOWN'

def test_holiday_without_session_proves_only_closure():
    assert reference_day(None,'Bank holiday')=='CLOSED'
    assert reference_day(None,None)=='UNKNOWN'
    assert reference_day('OPEN','Bank holiday')=='UNKNOWN'
    assert reference_day('HALF_DAY',None)=='OPEN'
