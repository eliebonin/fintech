"""Measure historical scanning separately from the much smaller priced population."""
from datetime import timedelta
from time import perf_counter
import tracemalloc
import pytest
from tests.test_position_reconstruction import booked,request,OPEN
from positions.reconstruction import reconstruct
from valuation.position_calculation import required_marks

@pytest.mark.parametrize('closed_episodes',[100,1000,5000])
def test_historical_closed_episodes_do_not_grow_priced_population(closed_episodes):
    facts=[]
    for i in range(closed_episodes):
        facts.extend([booked(2*i+1,'1',OPEN-timedelta(days=2)),booked(2*i+2,'-1',OPEN-timedelta(days=1))])
    facts.append(booked(2*closed_episodes+1,'0.001',OPEN+timedelta(hours=1)))
    tracemalloc.start(); start=perf_counter()
    try:
        result=reconstruct(facts,request()); elapsed=perf_counter()-start
        _,peak=tracemalloc.get_traced_memory()
    finally: tracemalloc.stop()
    assert result.facts_scanned==closed_episodes*2+1
    assert len(result.buckets)==len(result.executions)==len(required_marks(result))==1
    print(f'facts={result.facts_scanned} positions=1 executions=1 marks=1 seconds={elapsed:.4f} peakMiB={peak/1048576:.2f}')
