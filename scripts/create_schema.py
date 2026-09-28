"""Upgrade a local PostgreSQL Security Master database to the current schema revision."""

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

database_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm")
alembic_config = Config(str(project_root / "alembic.ini"))
alembic_config.set_main_option("sqlalchemy.url", database_url)
command.upgrade(alembic_config, "head")
print("Security Master database upgraded to the current migration revision.")
