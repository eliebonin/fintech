"""Repository content policy; excludes Git history and ignored local artifacts."""
from pathlib import Path
import subprocess
from hashlib import sha256


ROOT = Path(__file__).resolve().parents[1]
# Character codes keep this policy from containing the very name it prohibits.
# This is a scan rule, not an encoded runtime compatibility identifier.
RETIRED_OPERATOR = bytes((102, 111, 114, 116, 101, 109))


def test_repository_text_and_paths_are_provider_neutral():
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, check=True, capture_output=True,
    )
    violations = []
    for raw in sorted(set(result.stdout.split(b"\0")) - {b""}):
        path = ROOT / raw.decode("utf-8")
        if RETIRED_OPERATOR in raw.lower():
            violations.append(f"path: {path.relative_to(ROOT)}")
        if path.is_file() and RETIRED_OPERATOR in path.read_bytes().lower():
            violations.append(str(path.relative_to(ROOT)))
    assert not violations, "Non-neutral repository content:\n" + "\n".join(violations)


def test_anonymised_archive_current_hashes_match_files():
    archive = ROOT / 'docs/archive/2026-09-10-pre-reorganisation'
    rows = [line for line in (archive / 'manifest.md').read_text(encoding='utf-8').splitlines()
            if line.startswith('| `')]
    assert len(rows) == 91
    for row in rows:
        columns = [column.strip().strip('`') for column in row.strip('|').split('|')]
        assert len(columns) == 6, 'Archive must distinguish original and current hashes'
        assert len(columns[4]) == 64
        assert sha256((archive / columns[1]).read_bytes()).hexdigest() == columns[5], columns[1]
