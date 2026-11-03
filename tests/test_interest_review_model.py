from datetime import date
from decimal import Decimal as D
from valuation.interest_review_model import benchmark,covered_days,review_warning


def test_monday_normally_covers_three_days_but_explicit_weekend_entries_are_not_counted_twice():
    assert covered_days(date(2026,11,2),set())==3
    assert covered_days(date(2026,11,2),{date(2026,11,1)})==1
    assert covered_days(date(2026,11,2),{date(2026,10,31)})==2


def test_five_calendar_day_benchmark_treats_monday_three_day_amount_as_one_daily_rate():
    rows=[(date(2026,10,26),D('30'),3),(date(2026,10,27),D('10'),1),(date(2026,10,28),D('10'),1)]
    result=benchmark(rows,date(2026,10,29),1)
    assert result['average']==D('10') and result['coveredDays']==5
    assert review_warning(D('10'),1,result)['status']=='IN_LINE'


def test_monday_current_amount_is_not_a_false_threefold_outlier():
    rows=[(date(2026,10,29),D('10'),1),(date(2026,10,30),D('10'),1)]
    result=benchmark(rows,date(2026,11,2),3)
    assert result['endDate']==date(2026,10,30)
    assert review_warning(D('30'),3,result)['status']=='IN_LINE'
    assert review_warning(D('60'),3,result)['status']=='CHECK'


def test_unknown_days_and_overlaps_are_not_zero_or_silently_averaged():
    result=benchmark([(date(2026,10,28),D('10'),1)],date(2026,10,29),1)
    assert result['coveredDays']==1 and result['average']==D('10')
    assert len(result['missingDates'])==4
    overlap=benchmark([(date(2026,10,26),D('30'),3),(date(2026,10,25),D('99'),1)],date(2026,10,27),1)
    assert date(2026,10,25) in overlap['overlappingDates']
    assert date(2026,10,25) in overlap['missingDates']
    empty=benchmark([],date(2026,10,29),1)
    assert empty['average'] is None
    assert review_warning(D('0'),1,empty)['status']=='NO_BASELINE'


def test_zero_and_negative_baselines_have_honest_informative_comparisons():
    zero=benchmark([(date(2026,10,28),D('0'),1)],date(2026,10,29),1)
    assert review_warning(D('5'),1,zero)['status']=='CHANGED_FROM_ZERO'
    negative=benchmark([(date(2026,10,28),D('-10'),1)],date(2026,10,29),1)
    assert review_warning(D('-10'),1,negative)['status']=='IN_LINE'
