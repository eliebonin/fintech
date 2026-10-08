"""Compatibility launcher for the standalone Yahoo EoD ingestor app."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.market_data_ingestor.yahoo import main


if __name__ == '__main__':
    raise SystemExit(main())
