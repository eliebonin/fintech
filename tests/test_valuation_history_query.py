"""Report filtering is a database predicate, not filtering a fetched page."""
from datetime import date
from uuid import uuid4
from sqlalchemy import literal
from sqlalchemy.dialects import postgresql

def test_filters_and_count_share_scope_before_limit():
    from valuation.history import history_queries
    tenant,strategy=uuid4(),uuid4()
    rows,count=history_queries(tenant,literal(True),strategy_id=strategy,
        from_date=date(2026,10,1),to_date=date(2026,10,7),calculation_status='COMPLETED',
        publication_status='STAGED',results_only=True,limit=25,offset=25)
    def sql(query):return str(query.compile(dialect=postgresql.dialect(),compile_kwargs={'literal_binds':True}))
    page,total=sql(rows),sql(count)
    for statement in (page,total):
        assert str(tenant) in statement and str(strategy) in statement
        assert '2026-10-01' in statement and '2026-10-07' in statement
        assert "'COMPLETED'" in statement and "'STAGED'" in statement
        assert 'pnl_review_batch' in statement
    assert 'LIMIT 25 OFFSET 25' in page and 'LIMIT 25' not in total

def test_default_history_retains_failed_attempts_without_results():
    from valuation.history import history_queries
    rows,_=history_queries(uuid4(),literal(False))
    sql=str(rows.compile(dialect=postgresql.dialect(),compile_kwargs={'literal_binds':True}))
    assert 'LEFT OUTER JOIN' in sql and 'false' in sql
    assert 'IS NOT NULL' not in sql.split('ORDER BY')[-1]
