"""Private operator configuration shared by launchers, never browser code."""
from pathlib import Path
import os
import re
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]


def private_settings(values,path):
    path=Path(path)
    existing=path.read_text(encoding='utf-8') if path.exists() else ''
    for name,value in values.items():
        pattern=rf'(?m)^\s*(?:export\s+)?{name}=[^\r\n]*$'
        line=f'{name}={value}'
        if re.search(pattern,existing):existing=re.sub(pattern,lambda _:line,existing)
        else:existing+=('' if not existing or existing.endswith('\n') else '\n')+line+'\n'
    private_write(path,existing)


def private_write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():raise ValueError('Private configuration cannot be a symlink')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w',encoding='utf-8',newline='') as stream:stream.write(value)
    if os.name!='nt':path.chmod(0o600)


def migration_url(root=ROOT,*,test_admin=False):
    value=(os.environ.get('TEST_DATABASE_ADMIN_URL') if test_admin else None) or os.environ.get('MIGRATION_DATABASE_URL')
    if not value:value=dotenv_values(Path(root)/'.env.migrations').get('MIGRATION_DATABASE_URL')
    if not value:raise RuntimeError('Set MIGRATION_DATABASE_URL or run scripts/configure_local_database.py')
    return value
