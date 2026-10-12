"""Offline Alembic SQL generation must support schema-only migration review."""

from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_alembic_can_generate_offline_sql_for_head() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'CREATE SCHEMA IF NOT EXISTS "cfg"' in result.stdout
    assert "cfg.external_data_mapping_profile" in result.stdout
