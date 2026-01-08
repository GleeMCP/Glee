"""Agent registry and management."""

from .base import AgentResult, BaseAgent
from .claude import ClaudeAgent
from .codex import CodexAgent
from .gemini import GeminiAgent


class AgentRegistry:
    """Registry of available agents."""

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._register_default_agents()

    def _register_default_agents(self):
        """Register the default agents."""
        self.register(ClaudeAgent())
        self.register(CodexAgent())
        self.register(GeminiAgent())

    def register(self, agent: BaseAgent):
        """Register an agent."""
        self._agents[agent.name] = agent

    def get(self, name: str) -> BaseAgent | None:
        """Get an agent by name."""
        return self._agents.get(name)

    @property
    def agents(self) -> dict[str, BaseAgent]:
        """Get all registered agents."""
        return self._agents

    def available_agents(self) -> list[BaseAgent]:
        """Get all available (installed) agents."""
        return [a for a in self._agents.values() if a.is_available()]


# Global registry instance
registry = AgentRegistry()

__all__ = [
    "AgentResult",
    "BaseAgent",
    "ClaudeAgent",
    "CodexAgent",
    "GeminiAgent",
    "AgentRegistry",
    "registry",
]
