"""GitHub API client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from glee.github.auth import require_token


@dataclass
class Issue:
    """A GitHub issue."""

    number: int
    title: str
    body: str | None
    state: str  # open, closed
    html_url: str
    user: str
    labels: list[str]
    assignees: list[str]
    created_at: str
    updated_at: str
    closed_at: str | None


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
            token: GitHub token. If None, auto-resolves from glee connect.
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

    # -------------------------------------------------------------------------
    # Issues API
    # -------------------------------------------------------------------------

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: str | None = None,
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 30,
        page: int = 1,
    ) -> tuple[list[Issue], dict[str, Any]]:
        """List repository issues.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: Filter by state: open, closed, all.
            labels: Comma-separated list of label names.
            sort: Sort by: created, updated, comments.
            direction: Sort direction: asc, desc.
            per_page: Results per page (max 100).
            page: Page number.

        Returns:
            Tuple of (issues list, pagination info).
        """
        params: dict[str, Any] = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": min(per_page, 100),
            "page": page,
        }
        if labels:
            params["labels"] = labels

        resp = await self.client.get(f"/repos/{owner}/{repo}/issues", params=params)
        resp.raise_for_status()
        data = resp.json()

        # Filter out PRs (issues endpoint includes PRs)
        issues = [
            self._parse_issue(item)
            for item in data
            if "pull_request" not in item
        ]

        # Parse pagination from Link header
        pagination = self._parse_pagination(resp)

        return issues, pagination

    async def get_issue(self, owner: str, repo: str, number: int) -> Issue:
        """Get a single issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: Issue number.

        Returns:
            Issue details.
        """
        resp = await self.client.get(f"/repos/{owner}/{repo}/issues/{number}")
        resp.raise_for_status()
        return self._parse_issue(resp.json())

    async def search_issues(
        self,
        query: str,
        owner: str | None = None,
        repo: str | None = None,
        sort: str = "created",
        order: str = "desc",
        per_page: int = 30,
        page: int = 1,
    ) -> tuple[list[Issue], int, dict[str, Any]]:
        """Search issues across repositories.

        Args:
            query: Search query (GitHub search syntax).
            owner: Optional repository owner to scope search.
            repo: Optional repository name to scope search.
            sort: Sort by: created, updated, comments.
            order: Sort order: asc, desc.
            per_page: Results per page (max 100).
            page: Page number.

        Returns:
            Tuple of (issues list, total count, pagination info).
        """
        # Build search query
        q = query
        if owner and repo:
            q = f"repo:{owner}/{repo} {q}"
        # Exclude PRs from search
        q = f"{q} is:issue"

        params: dict[str, Any] = {
            "q": q,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100),
            "page": page,
        }

        resp = await self.client.get("/search/issues", params=params)
        resp.raise_for_status()
        data = resp.json()

        issues = [self._parse_issue(item) for item in data.get("items", [])]
        total_count = data.get("total_count", 0)
        pagination = self._parse_pagination(resp)

        return issues, total_count, pagination

    def _parse_issue(self, data: dict[str, Any]) -> Issue:
        """Parse issue data from API response."""
        return Issue(
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=data["state"],
            html_url=data["html_url"],
            user=data["user"]["login"],
            labels=[label["name"] for label in data.get("labels", [])],
            assignees=[a["login"] for a in data.get("assignees", [])],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            closed_at=data.get("closed_at"),
        )

    # -------------------------------------------------------------------------
    # Pull Requests API
    # -------------------------------------------------------------------------

    async def list_prs(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 30,
        page: int = 1,
    ) -> tuple[list[PR], dict[str, Any]]:
        """List repository pull requests.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: Filter by state: open, closed, all.
            sort: Sort by: created, updated, popularity, long-running.
            direction: Sort direction: asc, desc.
            per_page: Results per page (max 100).
            page: Page number.

        Returns:
            Tuple of (PRs list, pagination info).
        """
        params: dict[str, Any] = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": min(per_page, 100),
            "page": page,
        }

        resp = await self.client.get(f"/repos/{owner}/{repo}/pulls", params=params)
        resp.raise_for_status()
        data = resp.json()

        prs = [self._parse_pr(item) for item in data]
        pagination = self._parse_pagination(resp)

        return prs, pagination

    async def search_prs(
        self,
        query: str,
        owner: str | None = None,
        repo: str | None = None,
        sort: str = "created",
        order: str = "desc",
        per_page: int = 30,
        page: int = 1,
    ) -> tuple[list[PR], int, dict[str, Any]]:
        """Search pull requests across repositories.

        Args:
            query: Search query (GitHub search syntax).
            owner: Optional repository owner to scope search.
            repo: Optional repository name to scope search.
            sort: Sort by: created, updated, comments.
            order: Sort order: asc, desc.
            per_page: Results per page (max 100).
            page: Page number.

        Returns:
            Tuple of (PRs list, total count, pagination info).
        """
        # Build search query
        q = query
        if owner and repo:
            q = f"repo:{owner}/{repo} {q}"
        # Include only PRs
        q = f"{q} is:pr"

        params: dict[str, Any] = {
            "q": q,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100),
            "page": page,
        }

        resp = await self.client.get("/search/issues", params=params)
        resp.raise_for_status()
        data = resp.json()

        prs = [self._parse_pr_from_search(item) for item in data.get("items", [])]
        total_count = data.get("total_count", 0)
        pagination = self._parse_pagination(resp)

        return prs, total_count, pagination

    def _parse_pr(self, data: dict[str, Any]) -> PR:
        """Parse PR data from API response."""
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

    def _parse_pr_from_search(self, data: dict[str, Any]) -> PR:
        """Parse PR data from search API response (different format)."""
        # Search API doesn't include head/base refs, extract from html_url
        return PR(
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=data["state"],
            head_ref="",  # Not available in search results
            base_ref="",  # Not available in search results
            html_url=data["html_url"],
            user=data["user"]["login"],
        )

    async def merge_pr(
        self,
        owner: str,
        repo: str,
        number: int,
        merge_method: str = "merge",
        commit_title: str | None = None,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Merge a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: PR number.
            merge_method: Merge method: merge, squash, or rebase.
            commit_title: Custom commit title (for squash/merge).
            commit_message: Custom commit message (for squash/merge).

        Returns:
            Merge result with sha and merged status.

        Raises:
            httpx.HTTPStatusError: If merge fails (e.g., not mergeable).
        """
        payload: dict[str, Any] = {
            "merge_method": merge_method,
        }
        if commit_title:
            payload["commit_title"] = commit_title
        if commit_message:
            payload["commit_message"] = commit_message

        resp = await self.client.put(
            f"/repos/{owner}/{repo}/pulls/{number}/merge",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def _parse_pagination(self, resp: httpx.Response) -> dict[str, Any]:
        """Parse pagination info from Link header.

        Returns dict with:
            - has_next: bool
            - has_prev: bool
            - next_page: int | None
            - prev_page: int | None
            - last_page: int | None
        """
        pagination: dict[str, Any] = {
            "has_next": False,
            "has_prev": False,
            "next_page": None,
            "prev_page": None,
            "last_page": None,
        }

        link_header = resp.headers.get("Link", "")
        if not link_header:
            return pagination

        import re

        for part in link_header.split(","):
            match = re.search(r'<[^>]*[?&]page=(\d+)[^>]*>;\s*rel="(\w+)"', part)
            if match:
                page_num = int(match.group(1))
                rel = match.group(2)
                if rel == "next":
                    pagination["has_next"] = True
                    pagination["next_page"] = page_num
                elif rel == "prev":
                    pagination["has_prev"] = True
                    pagination["prev_page"] = page_num
                elif rel == "last":
                    pagination["last_page"] = page_num

        return pagination
