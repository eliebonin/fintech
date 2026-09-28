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


database_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm")
project_root = Path(__file__).resolve().parents[1]
alembic_config = Config(str(project_root / "alembic.ini"))
alembic_config.set_main_option("script_location", str(project_root / "alembic"))
alembic_config.set_main_option("sqlalchemy.url", database_url)
command.upgrade(alembic_config, "head")
load_demo_data(create_engine(database_url))
print("Synthetic HSBC XLON mapping, EOD market-data, and Soft-NAV scenario loaded.")
