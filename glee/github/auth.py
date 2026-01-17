"""GitHub authentication via glee connect."""

from glee.connect import storage


def _resolve_github_credential() -> storage.ServiceCredential | None:
    """Resolve which GitHub credential to use.

    Resolution order:
    1. Project config: credentials.github in .glee/config.yml
    2. Auto-detect: If only one GitHub service credential exists, use it

    Returns:
        ServiceCredential or None if not found/ambiguous.
    """
    from glee.config import get_project_config

    # 1. Check project config
    config = get_project_config()
    if config:
        creds_config = config.get("credentials", {})
        if "github" in creds_config:
            label = creds_config["github"]
            cred = storage.ConnectionStorage.get(label)
            if cred and isinstance(cred, storage.ServiceCredential):
                return cred

    # 2. Auto-detect: find all GitHub service credentials
    github_creds = [
        c for c in storage.ConnectionStorage.all()
        if c.vendor == "github" and isinstance(c, storage.ServiceCredential)
    ]

    if len(github_creds) == 1:
        return github_creds[0]

    return None


def get_token() -> str | None:
    """Get GitHub token from connections.

    Resolution order:
    1. Project config: credentials.github in .glee/config.yml
    2. Auto-detect: If only one GitHub service credential exists, use it

    Returns:
        GitHub personal access token, or None if not configured.
    """
    cred = _resolve_github_credential()
    return cred.key if cred else None


def require_token() -> str:
    """Get GitHub token, raising if not configured.

    Returns:
        GitHub personal access token.

    Raises:
        ValueError: If no GitHub credential found or multiple exist without config.
    """
    from glee.config import get_project_config

    cred = _resolve_github_credential()
    if cred:
        return cred.key

    # Provide helpful error message
    github_creds = [
        c for c in storage.ConnectionStorage.all()
        if c.vendor == "github" and isinstance(c, storage.ServiceCredential)
    ]

    if len(github_creds) == 0:
        raise ValueError("No GitHub credentials. Run: glee connect github")

    if len(github_creds) > 1:
        labels = ", ".join(c.label for c in github_creds)
        raise ValueError(
            f"Multiple GitHub credentials found ({labels}). "
            f"Set in .glee/config.yml:\n\ncredentials:\n  github: <label>"
        )

    raise ValueError("GitHub not configured")
