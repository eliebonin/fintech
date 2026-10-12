"""The operator adapter must never become an accidental production downloader."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('environment,database', [('production', 'fortem_secm'), ('local', 'elsewhere')])
@pytest.mark.parametrize('entry', [('scripts/ingest_yahoo_market_data.py',), ('-m', 'apps.market_data_ingestor.yahoo')])
def test_cli_rejects_nonlocal_personal_targets_before_network(environment, database, entry):
    result = subprocess.run([sys.executable, *entry, '--apply',
        '--declaration', 'Local personal project', '--acknowledge-personal-access'],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        env=dict(os.environ, APP_ENV=environment,
                 DATABASE_URL=f'postgresql+psycopg://unused:unused@localhost:54329/{database}'))
    assert result.returncode == 2
    assert 'restricted to local fortem_secm' in result.stderr


@pytest.mark.parametrize('arguments,message', [
    (['--personal-research-exception'], 'requires --apply'),
    (['--apply', '--personal-research-exception'], 'requires --apply'),
    (['--start','2020-01-01','--through','2026-10-06'], 'at most 1830'),
    (['--start','2026-10-06','--through','2026-10-05'], 'ordered'),
    (['--start','2021-10-07','--days','14'], 'not allowed with argument'),
    (['--retry-gaps'], 'requires --start'),
    (['--retry-gaps','--start','2021-10-07','--audit-only'], 'cannot combine'),
    (['--request-spacing-seconds','0'], '1..60 seconds'),
    (['--request-spacing-seconds','nan'], '1..60 seconds'),
    (['--request-spacing-seconds','61'], '1..60 seconds'),
])
def test_exception_and_history_guards_precede_database_or_network(arguments, message):
    result = subprocess.run([sys.executable, '-m', 'apps.market_data_ingestor.yahoo',
        '--declaration', 'Owner personal research approval', *arguments],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        env=dict(os.environ, APP_ENV='local',
                 DATABASE_URL='postgresql+psycopg://unused:unused@localhost:54329/fortem_secm'))
    assert result.returncode == 2
    assert message in result.stderr
