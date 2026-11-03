"""Scan only version-controlled/unignored source, including newly added files.

Local environments, secrets, dependencies, caches and reports are not copied.
The scanner output is redacted, and a sentinel proves default detectors work.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('scanner');args=parser.parse_args()
    binary=str(Path(args.scanner).resolve())
    config=str(ROOT/'.gitleaks.toml')
    with tempfile.TemporaryDirectory(prefix='source-secret-scan-') as folder:
        destination=Path(folder)
        # Deliberately synthetic high-entropy token shape, assembled at runtime.
        probe=destination/'probe';probe.mkdir()
        (probe/'sentinel.txt').write_text('github_token="'+'ghp_'+'aB7zH9mR4kT2pY5wC8nL6xQ3vJ1sD0fG9hK2'+'"\n')
        verified=subprocess.run([binary,'dir',str(probe),'--config',config,'--redact','--no-banner'],capture_output=True)
        if verified.returncode!=1:raise SystemExit('Secret detector sentinel failed')
        shutil.rmtree(probe)
        files=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
        for name in files:
            if not name:continue
            source=ROOT/name
            if not source.is_file() or source.is_symlink():continue
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        return subprocess.call([binary,'dir',str(destination),'--config',config,'--redact','--no-banner'],cwd=ROOT)


if __name__=='__main__':raise SystemExit(main())
