"""Compatibility launcher for the segregated Yahoo FX ingestor."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from apps.market_data_ingestor.yahoo_fx import main
if __name__=='__main__':raise SystemExit(main())
