"""Last-line safety guard: tests must never connect to the operating DB."""
from sqlalchemy import event
from sqlalchemy.engine import Engine
import re

@event.listens_for(Engine,'do_connect')
def reject_operating_database(dialect,connection_record,args,params):
    database = params.get('dbname') or params.get('database')
    # PostgreSQL's administration database is used only to create/drop owned
    # disposable databases. Application databases require an exact fixture shape.
    if database is not None and database != 'postgres' and not re.fullmatch(
        r'platform_(?:isolated_tests_(?:ci|(?:browser_)?[0-9a-f]{32})|(?:fx_signoff|index_migration|interest_migration|valuation_migration|choice_cleanup_test)_[0-9a-f]{32})',
        str(database),
    ):
        raise RuntimeError('Operating database connections are forbidden in pytest; set DATABASE_URL to an isolated database')
