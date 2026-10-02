"""Synthetic option + cash/FX browser acceptance; never uses the live database."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.prepare_fx_signoff_fixture import main as prepare_fx
from tests.test_option_booking_api import listing,payload
from tests.test_fx_forward_booking_api import request

if __name__=='__main__':
    prepare_fx()
    listing_id=listing.__wrapped__()
    detail=request('GET',f'/v1/trades/option-listings/{listing_id}')
    assert detail.status_code==200,detail.text
    print(json.dumps({'option':detail.json()['data']}))
