from pathlib import Path


def test_gitignore_excludes_logs_and_keeps_env_example_visible():
    lines = Path(".gitignore").read_text(encoding="utf-8").splitlines()

    assert "*.log" in lines
    assert "logs/" in lines
    assert "!.env.example" in lines


def test_example_environment_uses_only_placeholders():
    example = Path(".env.example").read_text(encoding="utf-8")

    assert "fortem_local_only" not in example
    assert "<local-password>" in example


def test_quality_workflow_is_read_only_and_pins_actions():
    workflow = Path(".github/workflows/quality.yml").read_text(encoding="utf-8")

    assert "contents: read" in workflow
    assert "pull_request_target" not in workflow
    assert "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803" in workflow
    assert "gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e" in workflow
