"""GitHub API client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from glee.github.auth import require_token


@dataclass
class PRFile:
    """A file changed in a PR."""

    filename: str
    status: str  # added, removed, modified, renamed
    additions: int
    deletions: int
    patch: str | None  # Unified diff patch


@dataclass
class PR:
    """A GitHub pull request."""

    number: int
    title: str
    body: str | None
    state: str  # open, closed
    head_ref: str
    base_ref: str
    html_url: str
    user: str


@dataclass
class ReviewComment:
    """An inline review comment."""

    path: str
    line: int
    body: str
    side: str = "RIGHT"  # LEFT or RIGHT (RIGHT = new code)


@dataclass
class Review:
    """A PR review with inline comments."""

    body: str
    event: str  # COMMENT, APPROVE, REQUEST_CHANGES
    comments: list[ReviewComment]


class GitHubClient:
    """GitHub API client."""

    def __init__(self, token: str | None = None):
        """Initialize client.

        Args:
            token: GitHub token. If None, gets from glee connect.
        """
        self.token = token or require_token()
        self.base_url = "https://api.github.com"
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> GitHubClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with GitHubClient()'")
        return self._client

    async def get_pr(self, owner: str, repo: str, number: int) -> PR:
        """Get pull request details.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: PR number.

        Returns:
            Pull request details.
        """
        resp = await self.client.get(f"/repos/{owner}/{repo}/pulls/{number}")
        resp.raise_for_status()
        data = resp.json()

        return PR(
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=data["state"],
            head_ref=data["head"]["ref"],
            base_ref=data["base"]["ref"],
            html_url=data["html_url"],
            user=data["user"]["login"],
        )

    async def get_pr_files(self, owner: str, repo: str, number: int) -> list[PRFile]:
        """Get files changed in a PR.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: PR number.

        Returns:
            List of changed files with patches.
        """
        files: list[PRFile] = []
        page = 1

        while True:
            resp = await self.client.get(
                f"/repos/{owner}/{repo}/pulls/{number}/files",
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            data = resp.json()

            if not data:
                break

            for f in data:
                files.append(
                    PRFile(
                        filename=f["filename"],
                        status=f["status"],
                        additions=f["additions"],
                        deletions=f["deletions"],
                        patch=f.get("patch"),
                    )
                )

            if len(data) < 100:
                break
            page += 1

        return files

    async def post_comment(
        self,
        owner: str,
        repo: str,
        number: int,
        path: str,
        line: int,
        body: str,
        commit_id: str | None = None,
        side: str = "RIGHT",
    ) -> dict[str, Any]:
        """Post an inline comment on a PR.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: PR number.
            path: File path.
            line: Line number.
            body: Comment body.
            commit_id: Commit SHA (if None, fetches from PR).
            side: LEFT or RIGHT (RIGHT = new code).

        Returns:
            Created comment data.
        """
        if not commit_id:
            # Get the head commit
            resp = await self.client.get(f"/repos/{owner}/{repo}/pulls/{number}")
            resp.raise_for_status()
            commit_id = resp.json()["head"]["sha"]

        resp = await self.client.post(
            f"/repos/{owner}/{repo}/pulls/{number}/comments",
            json={
                "body": body,
                "commit_id": commit_id,
                "path": path,
                "line": line,
                "side": side,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def post_review(
        self,
        owner: str,
        repo: str,
        number: int,
        review: Review,
        commit_id: str | None = None,
    ) -> dict[str, Any]:
        """Post a full review with multiple comments.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: PR number.
            review: Review with body, event, and comments.
            commit_id: Commit SHA (if None, fetches from PR).

        Returns:
            Created review data.
        """
        if not commit_id:
            resp = await self.client.get(f"/repos/{owner}/{repo}/pulls/{number}")
            resp.raise_for_status()
            commit_id = resp.json()["head"]["sha"]

        comments = [
            {
                "path": c.path,
                "line": c.line,
                "body": c.body,
                "side": c.side,
            }
            for c in review.comments
        ]

        resp = await self.client.post(
            f"/repos/{owner}/{repo}/pulls/{number}/reviews",
            json={
                "commit_id": commit_id,
                "body": review.body,
                "event": review.event,
                "comments": comments,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def compare(
        self, owner: str, repo: str, base: str, head: str
    ) -> dict[str, Any]:
        """Compare two commits/branches.

        Args:
            owner: Repository owner.
            repo: Repository name.
            base: Base ref (branch/commit).
            head: Head ref (branch/commit).

        Returns:
            Comparison data including files and commits.
        """
        resp = await self.client.get(f"/repos/{owner}/{repo}/compare/{base}...{head}")
        resp.raise_for_status()
        return resp.json()
