"""Local maintenance uses a distinct private credential, never the API login."""
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.local_database_config import migration_url

if __name__=='__main__':
    url=migration_url()
    environment={**os.environ,'DATABASE_URL':url}
    arguments=sys.argv[1:] or ['upgrade','head']
    result=subprocess.call([sys.executable,'-m','alembic',*arguments],cwd=ROOT,env=environment)
    if result==0 and arguments[0]=='upgrade' and '--sql' not in arguments:
        from sqlalchemy import create_engine,text
        from security_master_schema.database_security import grant_runtime_access
        engine=create_engine(url,hide_parameters=True)
        try:
            with engine.begin() as c:
                if c.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='platform_runtime')")):
                    grant_runtime_access(c,'platform_runtime')
        finally:engine.dispose()
    raise SystemExit(result)
