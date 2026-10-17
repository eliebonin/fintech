"""Fixed synthetic history: identical evidence, fewer SQL reads and bounded rows."""
from datetime import timedelta
from uuid import uuid4
from time import perf_counter
from sqlalchemy import event, select, delete
from tests.test_valuation_service import valued
from tests.test_measure_inputs import preview
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def test_snapshot_scoped_reuse_preserves_result_and_reduces_queries(valued,request):
    c,r,_=valued
    owned_datasets=[]
    # Unrelated governed providers must not cause every instrument resolution
    # to rescan the same licence profiles. None grants rights to test prices.
    owner=c.scalar(select(m.tenant.c.owning_organisation_id).where(m.tenant.c.tenant_id==r.tenant_id))
    for _ in range(5):
        dataset=uuid4()
        owned_datasets.append(dataset)
        c.execute(m.dataset.insert().values(dataset_id=dataset,provider_product_id=ids['provider_product'],
            dataset_code='PERF_'+dataset.hex,display_name='Synthetic unrelated provider',data_domain='MARKET_DATA',
            valid_from=r.closing_cutoff.date()-timedelta(days=1000)))
        c.execute(m.dataset_access_profile.insert().values(dataset_id=dataset,licensee_organisation_id=owner,
            permitted_tenant_id=r.tenant_id,usage_scope='PERSONAL',provider_enabled=True,
            activation_reference='Synthetic benchmark only',status='ACTIVE'))
    source=dict(c.execute(select(m.market_data_observation).where(
        m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    history=[source|dict(market_data_observation_id=uuid4(),
        market_date=r.closing_cutoff.date()-timedelta(days=n+60),source_observation_key='PERF_'+uuid4().hex)
        for n in range(1000)]
    c.execute(m.market_data_observation.insert(),history)
    c.commit();c.execution_options(isolation_level='REPEATABLE READ')
    def cleanup_owned_benchmark():
        with c.engine.begin() as cleanup:
            cleanup.execute(delete(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id.in_(
                [row['market_data_observation_id'] for row in history])))
            cleanup.execute(delete(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id.in_(owned_datasets)))
            cleanup.execute(delete(m.dataset).where(m.dataset.c.dataset_id.in_(owned_datasets)))
    request.addfinalizer(cleanup_owned_benchmark)
    with c.begin():
        statements=[];candidates=[];candidate_queries=[]
        def measured(conn,cursor,statement,parameters,context,executemany):
            if conn is c:
                statements.append(statement)
                if 'FROM md.market_data_observation JOIN md.market_data_series' in statement:
                    candidates.append(cursor.rowcount)
                    candidate_queries.append((statement,parameters))
        event.listen(c.engine,'after_cursor_execute',measured)
        try:
            started=perf_counter();plain=[preview(c,r),preview(c,r)];plain_count=len(statements)
            print(f'uncached: sql={plain_count}, candidates={sum(candidates)}, seconds={perf_counter()-started:.3f}')
            statements.clear();candidates.clear()
            from market_data.read_scope import resolution_read_scope
            with resolution_read_scope(c,tenant=r.tenant_id,actor=ids['demo_user_account'],strategy=r.strategy_id,
                    policy=r.policy_id,information_cutoff=r.information_cutoff,economic_date=r.closing_cutoff.date()):
                started=perf_counter();cached=[preview(c,r),preview(c,r)]
                cached_count=len(statements)
                print(f'scoped: sql={cached_count}, candidates={sum(candidates)}, seconds={perf_counter()-started:.3f}')
            assert cached==plain
            assert cached_count<plain_count*0.8
            assert sum(candidates)<=4
        finally:event.remove(c.engine,'after_cursor_execute',measured)
        # Explain the actual emitted selection query, not a simplified surrogate.
        statement,parameters=candidate_queries[-1]
        explained=c.exec_driver_sql('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+statement,parameters).scalar_one()[0]
        plan=explained['Plan']
        print(f"selection plan: node={plan['Node Type']}, rows={plan['Actual Rows']}, milliseconds={explained['Execution Time']}, shared_hits={plan.get('Shared Hit Blocks',0)}")
