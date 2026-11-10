"""Reference sources are governed identities, not copied dropdown strings."""
from uuid import uuid4
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_governed_trade_configuration import engine,connection,catalogue,entry,field,TENANT,ACTOR
from security_master_schema.tenant_workspace import TenantActionForbidden
from tenant_reference.sources import list_sources,list_source_options,source_detail


def test_sources_include_canonical_roles_and_custom_catalogue_with_exact_counts(connection):
    cat=catalogue(connection);record=entry(connection,cat);field(connection,cat)
    result=list_sources(connection,TENANT,ACTOR,'',0,100)
    assert {r['sourceKey'] for r in result['items']} >= {f'catalogue:{cat}','standard:COUNTERPARTY','standard:EXECUTING_BROKER','standard:TRADER'}
    row=next(r for r in result['items'] if r['sourceKey']==f'catalogue:{cat}')
    assert row['activeEntryCount']==1 and row['fieldCount']==1
    assert result['total']==len(result['items'])
    found=list_sources(connection,TENANT,ACTOR,row['code'],0,1)
    assert found['total']==1 and found['items'][0]['sourceKey']==row['sourceKey']


def test_reference_options_retain_record_identity_and_off_page_selection(connection):
    cat=catalogue(connection);first=entry(connection,cat,'ALPHA')
    from tenant_reference.catalogues import create_record
    second=create_record(connection,TENANT,ACTOR,cat,dict(code='ZULU',label='Zulu allocation',reason='Synthetic source'))
    field(connection,cat)
    result=list_source_options(connection,TENANT,ACTOR,f'catalogue:{cat}',query='',offset=0,limit=1,selected_ids=[second['recordVersionId']])
    assert result['total']==2 and len(result['items'])==1
    assert result['selected'][0]['id']==second['recordVersionId']
    assert result['selected'][0]['recordId']==second['recordId']
    assert result['items'][0]['id']==first['recordVersionId']


def test_sources_never_reveal_a_foreign_catalogue(connection):
    cat=catalogue(connection)
    with pytest.raises((LookupError,TenantActionForbidden)):source_detail(connection,ids['second_tenant'],ACTOR,f'catalogue:{cat}')


def test_options_do_not_offer_retired_entries(connection):
    from tenant_reference import catalogues as g
    cat=catalogue(connection);record=entry(connection,cat);field(connection,cat)
    g.change_record(connection,TENANT,ACTOR,cat,record['recordVersionId'],None,'No longer eligible')
    result=list_source_options(connection,TENANT,ACTOR,f'catalogue:{cat}',selected_ids=[record['recordVersionId']])
    assert result['total']==0 and result['selected']==[]


def test_unknown_standard_source_is_rejected(connection):
    with pytest.raises(ValueError):list_source_options(connection,TENANT,ACTOR,'standard:UNKNOWN')


def test_entry_usage_and_history_reads_keep_the_source_scope_and_full_counts(connection):
    from tenant_reference.sources import source_entries,source_usage,source_history
    cat=catalogue(connection);record=entry(connection,cat);definition=field(connection,cat)
    other=catalogue(connection);entry(connection,other)
    entries=source_entries(connection,TENANT,ACTOR,f'catalogue:{cat}',limit=1)
    assert entries['total']==1 and entries['items'][0]['recordId']==record['recordId']
    usage=source_usage(connection,TENANT,ACTOR,f'catalogue:{cat}')
    assert usage['total']==1 and usage['items'][0]['definitionId']==definition['definitionId']
    history=source_history(connection,TENANT,ACTOR,f'catalogue:{cat}')
    assert history['total']>=3
    assert all(r['subjectId'] in {cat,record['recordId'],record['recordVersionId']} for r in history['items'])
