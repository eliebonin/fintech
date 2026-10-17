"""Local database targeting, separate from application connection credentials."""
import os


def local_workspace_database() -> str:
    """Require an explicit operator target when reusing a named installation.

    DATABASE_URL alone must not silently authorize an arbitrary seed/import target.
    Callers still enforce local environment, host and port before any connection.
    """
    return os.environ.get('LOCAL_WORKSPACE_DATABASE', 'platform_secm')
