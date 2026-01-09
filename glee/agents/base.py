"""Base agent interface for CLI agents."""

import shutil
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from glee.logging import get_agent_logger


@dataclass
class AgentResult:
    """Result from an agent invocation."""

    output: str
    error: str | None = None
    exit_code: int = 0
    run_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=lambda: {})

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and self.error is None


class BaseAgent(ABC):
    """Base class for CLI agent wrappers."""

    name: str
    command: str
    capabilities: list[str]

    def __init__(self, project_path: Path | None = None):
        self._available: bool | None = None
        self.project_path = project_path

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
    def run(self, prompt: str, **kwargs: Any) -> AgentResult:
        """Run the agent with a prompt."""
        pass

    @abstractmethod
    def run_review(
        self,
        target: str = ".",
        focus: list[str] | None = None,
        stream: bool = True,
        on_output: Callable[[str], None] | None = None,
    ) -> AgentResult:
        """Run a code review.

        Args:
            target: What to review. Can be a file path, directory, 'git:changes',
                    'git:staged', or a natural description.
            focus: Optional focus areas (security, performance, etc.)
            stream: If True, stream output in real-time.
            on_output: Optional callback for each line of output.
        """
        pass

    @abstractmethod
    def run_judge(
        self,
        code_context: str,
        review_item: str,
        coder_objection: str,
    ) -> AgentResult:
        """Arbitrate a dispute between coder and reviewer.

        Args:
            code_context: The relevant code being disputed
            review_item: The reviewer's feedback (MUST or HIGH item)
            coder_objection: The coder's reasoning for disagreeing

        Returns:
            AgentResult with decision: ENFORCE, DISMISS, or ESCALATE
        """
        pass

    @abstractmethod
    def run_process_feedback(self, review_feedback: str) -> AgentResult:
        """Process review feedback and decide whether to accept or dispute.

        Args:
            review_feedback: The structured review feedback from reviewer

        Returns:
            AgentResult with acceptance or objection for each item
        """
        pass

    def _run_subprocess(
        self,
        args: list[str],
        prompt: str = "",
        timeout: int = 300,
        cwd: str | None = None,
    ) -> AgentResult:
        """Run a subprocess and capture output.

        Args:
            args: Command arguments to run.
            prompt: The prompt sent to the agent (for logging).
            timeout: Timeout in seconds.
            cwd: Working directory.

        Returns:
            AgentResult with output, error, and run_id for log lookup.
        """
        start_time = time.time()
        run_id = None

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            duration_ms = int((time.time() - start_time) * 1000)

            # Log to SQLite
            agent_logger = get_agent_logger(self.project_path) if self.project_path else get_agent_logger()
            if agent_logger:
                run_id = agent_logger.log(
                    agent=self.name,
                    prompt=prompt,
                    output=result.stdout,
                    raw=result.stdout,
                    error=result.stderr if result.returncode != 0 else None,
                    exit_code=result.returncode,
                    duration_ms=duration_ms,
                )

            return AgentResult(
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                exit_code=result.returncode,
                run_id=run_id,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Command timed out after {timeout} seconds"

            agent_logger = get_agent_logger(self.project_path) if self.project_path else get_agent_logger()
            if agent_logger:
                run_id = agent_logger.log(
                    agent=self.name,
                    prompt=prompt,
                    error=error_msg,
                    exit_code=-1,
                    duration_ms=duration_ms,
                )

            return AgentResult(
                output="",
                error=error_msg,
                exit_code=-1,
                run_id=run_id,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            agent_logger = get_agent_logger(self.project_path) if self.project_path else get_agent_logger()
            if agent_logger:
                run_id = agent_logger.log(
                    agent=self.name,
                    prompt=prompt,
                    error=str(e),
                    exit_code=-1,
                    duration_ms=duration_ms,
                )

            return AgentResult(
                output="",
                error=str(e),
                exit_code=-1,
                run_id=run_id,
            )

    def _run_subprocess_streaming(
        self,
        args: list[str],
        prompt: str = "",
        timeout: int = 300,
        cwd: str | None = None,
        on_output: Callable[[str], None] | None = None,
    ) -> AgentResult:
        """Run a subprocess with real-time output streaming.

        This method streams output to stderr (visible to user) while capturing
        the full output for logging and MCP response.

        Args:
            args: Command arguments to run.
            prompt: The prompt sent to the agent (for logging).
            timeout: Timeout in seconds.
            cwd: Working directory.
            on_output: Optional callback for each line of output.

        Returns:
            AgentResult with output, error, and run_id for log lookup.
        """
        start_time = time.time()
        run_id = None
        output_lines: list[str] = []
        error_lines: list[str] = []

        # Default callback: stream to stderr AND log file so user can see reasoning
        def default_output_callback(line: str) -> None:
            # Write to stderr
            sys.stderr.write(line)
            sys.stderr.flush()
            # Also write to streaming log file for tail -f
            if self.project_path:
                stream_log = self.project_path / ".glee" / "stream.log"
                try:
                    with open(stream_log, "a") as f:
                        f.write(line)
                        f.flush()
                except Exception:
                    pass

        output_callback = on_output if on_output is not None else default_output_callback

        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                bufsize=1,  # Line buffered
            )

            import threading

            # Track if timeout occurred
            timed_out = False

            def read_stream(stream: Any, lines: list[str], is_stderr: bool = False) -> None:
                """Read from stream and collect lines."""
                try:
                    for line in iter(stream.readline, ""):
                        if line:
                            lines.append(line)
                            # Stream stdout to user (reviewer reasoning)
                            if not is_stderr:
                                output_callback(line)
                except Exception:
                    pass
                finally:
                    stream.close()

            # Start threads to read stdout and stderr
            stdout_thread = threading.Thread(
                target=read_stream,
                args=(process.stdout, output_lines, False),
            )
            stderr_thread = threading.Thread(
                target=read_stream,
                args=(process.stderr, error_lines, True),
            )
            stdout_thread.start()
            stderr_thread.start()

            # Wait for process with timeout
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                process.wait()

            # Wait for threads to finish reading
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)

            duration_ms = int((time.time() - start_time) * 1000)
            output = "".join(output_lines)
            error = "".join(error_lines)

            if timed_out:
                error = f"Command timed out after {timeout} seconds\n{error}"

            # Log to SQLite
            agent_logger = get_agent_logger(self.project_path) if self.project_path else get_agent_logger()
            if agent_logger:
                run_id = agent_logger.log(
                    agent=self.name,
                    prompt=prompt,
                    output=output,
                    raw=output,
                    error=error if (process.returncode != 0 or timed_out) else None,
                    exit_code=process.returncode if not timed_out else -1,
                    duration_ms=duration_ms,
                )

            return AgentResult(
                output=output,
                error=error if (process.returncode != 0 or timed_out) else None,
                exit_code=process.returncode if not timed_out else -1,
                run_id=run_id,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            agent_logger = get_agent_logger(self.project_path) if self.project_path else get_agent_logger()
            if agent_logger:
                run_id = agent_logger.log(
                    agent=self.name,
                    prompt=prompt,
                    error=str(e),
                    exit_code=-1,
                    duration_ms=duration_ms,
                )

            return AgentResult(
                output="",
                error=str(e),
                exit_code=-1,
                run_id=run_id,
            )
