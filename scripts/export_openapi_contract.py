"""Export the Reference Data API's deterministic v1 OpenAPI contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from apps.reference_api.main import create_app


DEFAULT_OUTPUT = Path("packages/api-contracts/openapi/reference-data-api.v1.json")


def export_contract(output: Path = DEFAULT_OUTPUT, *, check: bool = False) -> int:
    """Write the application schema, or report drift without modifying output."""

    serialized = (json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n").encode("utf-8")
    if check:
        if not output.exists() or output.read_bytes() != serialized:
            print(f"OpenAPI contract is stale: {output}")
            return 1
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(serialized)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return export_contract(args.output, check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
