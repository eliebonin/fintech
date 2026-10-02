"""Create a separate synthetic browser fixture; never changes the live database."""
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import json
from sqlalchemy import create_engine,text

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    name="fortem_fx_signoff_"+uuid4().hex
    prefix="postgresql+psycopg://fortem:fortem_local_only@localhost:54329/"
    admin=create_engine(prefix+"postgres",isolation_level="AUTOCOMMIT")
    with admin.connect() as c:c.execute(text(f'CREATE DATABASE "{name}"'))
    os.environ["DATABASE_URL"]=prefix+name
    subprocess.run([sys.executable,"-m","alembic","upgrade","head"],cwd=ROOT,check=True)
    from apps.reference_api.db import get_engine
    from security_master_schema.demo_data import load_demo_data,DEMO_IDS
    from scripts.provision_trade_properties import provision_config
    from tests.test_fx_forward_booking_api import request
    load_demo_data(get_engine())
    with get_engine().begin() as c:
        provision_config(c,DEMO_IDS["tenant"],DEMO_IDS["demo_user_account"],{
            "catalogues":[{"code":"FX_SIGNOFF_BUCKETS","label":"FX acceptance buckets","description":"Synthetic only","records":[{"code":"HEDGE","label":"Acceptance hedge","description":"Synthetic hedge classification","status":"ACTIVE"}]}],
            "properties":[{"code":"FX_SIGNOFF_SCORE","label":"Acceptance score","description":"Synthetic numeric value","valueType":"DECIMAL","required":False},
                          {"code":"FX_SIGNOFF_BUCKET","label":"Acceptance bucket","description":"Synthetic governed value","valueType":"REFERENCE","catalogueCode":"FX_SIGNOFF_BUCKETS","required":False}],
            "tags":[{"code":"FX_SIGNOFF","label":"FX acceptance"}]})
    created=request("POST","/v1/fx-forward-proposals",{"canonicalName":"FX Signoff EUR USD December","effectiveFrom":"2026-09-01","baseCurrencyId":str(DEMO_IDS["eur_currency"]),"quoteCurrencyId":str(DEMO_IDS["usd_currency"]),"quoteConvention":"USD_PER_EUR","agreedForwardRate":"1.10","settlementType":"DELIVERABLE","maturityDate":"2026-12-15","submissionMode":"MANUAL"})
    assert created.status_code==201,created.text
    approved=request("POST",f"/v1/reference-data-proposals/{created.json()['data']['proposalId']}/decision",{"decision":"APPROVED","reason":"Synthetic browser acceptance fixture"})
    assert approved.status_code==200,approved.text
    print(json.dumps({"database":name,"instrumentId":approved.json()["data"]["referenceNodeId"],"tenantId":str(DEMO_IDS["tenant"])}))


if __name__=="__main__":main()
