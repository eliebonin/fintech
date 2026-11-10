"""Load deterministic synthetic scenarios into the local PostgreSQL Security Master database."""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from alembic import command
from alembic.config import Config

# Permit direct execution via ``python scripts/load_demo_scenarios.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from security_master_schema.demo_data import load_demo_data


from scripts.local_database_config import migration_url
database_url = migration_url()
os.environ['DATABASE_URL']=database_url
project_root = Path(__file__).resolve().parents[1]
alembic_config = Config(str(project_root / "alembic.ini"))
alembic_config.set_main_option("script_location", str(project_root / "alembic"))
alembic_config.set_main_option("sqlalchemy.url", database_url)
command.upgrade(alembic_config, "head")
engine=create_engine(database_url)
load_demo_data(engine)
from security_master_schema.demo_data import DEMO_IDS
from trading.profiles.migration import backfill_profiles
with engine.begin() as connection:
    for tenant in (DEMO_IDS['tenant'],DEMO_IDS['second_tenant']):
        backfill_profiles(connection,DEMO_IDS['demo_user_account'],tenant)
engine.dispose()
print("Synthetic HSBC XLON mapping, EOD market-data, and Soft-NAV scenario loaded.")
