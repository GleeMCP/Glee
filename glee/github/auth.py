"""GitHub authentication via glee connect."""

from glee.connect import storage


def get_token() -> str | None:
    """Get GitHub token from connections.

    Returns:
        GitHub personal access token, or None if not configured.
    """
    cred = storage.ConnectionStorage.find_one("github")
    if cred and isinstance(cred, storage.APICredential):
        return cred.key
    return None


def require_token() -> str:
    """Get GitHub token, raising if not configured.

    Returns:
        GitHub personal access token.

    Raises:
        ValueError: If GitHub is not connected.
    """
    token = get_token()
    if not token:
        raise ValueError("GitHub not connected. Run: glee connect")
    return token
