"""Same contract reused across two synthetic source integrations in one tenant."""
from datetime import date
from sqlalchemy import select,func
from .test_reconciliation_seed import connection


def test_standard_option_reuses_reviewed_listing_and_books_once(connection,tmp_path):
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from .test_reconciliation_option import option_bundle
    from tooling.reconciliation_csv.reconciliation import load_bundle
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from tooling.reconciliation_csv.reconciliation_products import seed_additional
    from tooling.reconciliation_csv.reconciliation_option import post_option
    from tooling.reconciliation_csv.reconciliation_postings import prepare_position_metadata
    from tooling.reconciliation_csv.fcpgf_option import book_standard_option
    c=connection;tenant=ids['tenant'];actor=ids['demo_user_account'];first=tmp_path/'one';first.mkdir()
    source=option_bundle(first);f=apply_foundation(c,source,tenant,actor,tmp_path/'evidence')
    seed_additional(c,source,tenant,actor,f);original=post_option(c,source,tenant,actor,f,{})
    second=tmp_path/'two';second.mkdir()
    for file in first.glob('SAMPLE-*.csv'):
        content=file.read_text()
        if file.name.endswith('-strategy_info.csv'):content=content.replace('SAMPLE','OTHER')
        (second/file.name.replace('SAMPLE-','OTHER-')).write_text(content)
    bundle=load_bundle(second,'OTHER',date(2026,10,20),excluded_trade_ids={'exclude'},amc_ids={'1857'})
    f2=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    _,parties=prepare_position_metadata(c,bundle,tenant,actor,f2,product_nodes={'20265':original['instrumentId']})
    before=c.scalar(select(func.count()).select_from(m.trade))
    result=book_standard_option(c,bundle,tenant,actor,f2,{},parties)
    assert result['instrumentId']==original['instrumentId']
    assert result['listingId']==original['listingId']
    assert result['tradeId']!=original['tradeId']
    assert result['quantity']=='20' and result['grossPremium']==original['grossPremium']
    assert book_standard_option(c,bundle,tenant,actor,f2,{},parties)==result
    assert c.scalar(select(func.count()).select_from(m.trade))==before+1
