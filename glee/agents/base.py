"""Base agent interface for CLI agents."""

import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Result from an agent invocation."""

    output: str
    error: str | None = None
    exit_code: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and self.error is None


class BaseAgent(ABC):
    """Base class for CLI agent wrappers."""

    name: str
    command: str
    capabilities: list[str]

    def __init__(self):
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Check if the agent CLI is installed and available."""
        if self._available is None:
            self._available = shutil.which(self.command) is not None
        return self._available

    def get_version(self) -> str | None:
        """Get the agent's version."""
        if not self.is_available():
            return None
        try:
            result = subprocess.run(
                [self.command, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() or result.stderr.strip()
        except Exception:
            return None

    @abstractmethod
    def run(self, prompt: str, **kwargs) -> AgentResult:
        """Run the agent with a prompt."""
        pass

    @abstractmethod
    def run_review(self, files: list[str], focus: list[str] | None = None) -> AgentResult:
        """Run a code review."""
        pass

    def _run_subprocess(
        self,
        args: list[str],
        timeout: int = 300,
        cwd: str | None = None,
    ) -> AgentResult:
        """Run a subprocess and capture output."""
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            return AgentResult(
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return AgentResult(
                output="",
                error=f"Command timed out after {timeout} seconds",
                exit_code=-1,
            )
        except Exception as e:
            return AgentResult(
                output="",
                error=str(e),
                exit_code=-1,
            )
