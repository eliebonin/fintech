"""Explicit authorised reference publication and interrupted-run recovery.

No worker killing, price rewriting, policy reassignment or automatic recovery.
Use DATABASE_URL to select the intended environment before running.
"""
import argparse
from pathlib import Path
import sys
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='operation',required=True)
    publish=commands.add_parser('publish-reference-calendar')
    publish.add_argument('--calendar',type=UUID,required=True)
    recover=commands.add_parser('recover-attempt')
    recover.add_argument('--tenant',type=UUID,required=True)
    recover.add_argument('--attempt',type=UUID,required=True)
    recover.add_argument('--confirm-worker-stopped',action='store_true',required=True)
    for command in (publish,recover):
        command.add_argument('--actor',type=UUID,required=True)
        command.add_argument('--reason',required=True)
    args=parser.parse_args()
    from apps.reference_api.db import get_engine
    from apps.reference_api.config import Settings
    from apps.reference_api.resource_limits import configure_transaction_budget
    settings=Settings.from_environment(); engine=get_engine()
    def budget(c): configure_transaction_budget(c,settings)
    try:
        if args.operation=='publish-reference-calendar':
            from market_data.calendar_store import publish_reference_calendar
            with engine.begin() as c:
                budget(c)
                identifier=publish_reference_calendar(c,args.calendar,args.actor,args.reason)
            print(f'Published sealed reference calendar: {identifier}. Assign this version explicitly; existing policies are unchanged.')
        else:
            from valuation.runner import recover_attempt
            recover_attempt(engine,args.tenant,args.attempt,args.actor,args.reason,
                confirmed_worker_stopped=args.confirm_worker_stopped,configure_transaction=budget)
            print(f'Retained interrupted attempt {args.attempt} as FAILED. Retry using a new request key.')
    except (ValueError,PermissionError,LookupError) as exc:
        parser.exit(1,f'{exc}\n')
    finally:
        engine.dispose()


if __name__=='__main__':
    main()
