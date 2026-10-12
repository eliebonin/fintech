"""Last-line safety guard: tests must never connect to the operating DB."""
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine,'do_connect')
def reject_operating_database(dialect,connection_record,args,params):
    if params.get('dbname')=='fortem_secm' or params.get('database')=='fortem_secm':
        raise RuntimeError('Operating database connections are forbidden in pytest; set DATABASE_URL to an isolated database')
