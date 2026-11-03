"""Configure a private shared capability for local API/BFF session bootstrap.

Run once before the local launch commands. This never changes a database,
permissions or records, and never prints the generated capability.
"""
from pathlib import Path
import os
import re
from secrets import token_urlsafe
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]


def configure(root:Path=ROOT) -> None:
    root=root.resolve()
    paths=[root/'.env.local-access',root/'apps/ops-console/.env.local']
    if any(not path.resolve().is_relative_to(root) for path in paths):
        raise ValueError('Local configuration must stay inside the selected project')
    configs=[dotenv_values(path) if path.exists() else {} for path in paths]
    keys={config['LOCAL_ACCESS_OPERATOR_KEY'] for config in configs if config.get('LOCAL_ACCESS_OPERATOR_KEY')}
    operators={config['LOCAL_PLATFORM_OPERATOR_ID'] for config in configs if config.get('LOCAL_PLATFORM_OPERATOR_ID')}
    if len(keys)>1 or len(operators)>1:
        raise ValueError('Existing API and frontend local operator settings must match; no files were changed')
    key=next(iter(keys),None) or token_urlsafe(48)
    if len(key)<32 or any(c.isspace() for c in key):
        raise ValueError('Existing LOCAL_ACCESS_OPERATOR_KEY is invalid; no files were changed')
    operator=next(iter(operators),None) or '00000000-0000-7000-8000-000000000304'
    from uuid import UUID
    UUID(operator)
    settings={'APP_ENV':'local','LOCAL_ACCESS_OPERATOR_KEY':key,'LOCAL_PLATFORM_OPERATOR_ID':operator}
    for path in paths:
        existing=path.read_text(encoding='utf-8') if path.exists() else ''
        for name,value in settings.items():
            pattern=rf'(?m)^\s*(?:export\s+)?{name}=[^\r\n]*$'
            if re.search(pattern,existing):
                existing=re.sub(pattern,lambda _:f'{name}={value}',existing)
            else:
                existing+=('' if not existing or existing.endswith('\n') else '\n')+f'{name}={value}\n'
        path.parent.mkdir(parents=True,exist_ok=True)
        # New files are private on POSIX; Windows retains the user's folder ACL.
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(descriptor,'w',encoding='utf-8',newline='') as stream:
            stream.write(existing)
        if os.name!='nt': path.chmod(0o600)
    print('Local API and frontend identity configured. The private key was not printed. Restart both services.')


if __name__=='__main__':
    configure()
