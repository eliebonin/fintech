"""Prepare synthetic browser data; refuse the operator database."""
import json
import os
import sys
from pathlib import Path
from sqlalchemy.engine import make_url

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if not make_url(os.environ['DATABASE_URL']).database.startswith('fortem_fx_signoff_'):
    raise SystemExit('A retained isolated signoff database is required.')
from tests.test_product_booking_api import structured,future
print(json.dumps({'structuredInstrumentId':structured.__wrapped__(),'future':future.__wrapped__()}))
