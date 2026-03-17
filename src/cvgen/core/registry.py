"""Plugin registry for backends and agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cvgen.agents.base import BaseAgent
    from cvgen.backends.base import QuantumBackend


class Registry:
    """Central registry for quantum backends and agent types."""

    def __init__(self) -> None:
        self._backends: dict[str, QuantumBackend] = {}
        self._agent_types: dict[str, type[BaseAgent]] = {}

    def register_backend(self, name: str, backend: QuantumBackend) -> None:
        self._backends[name] = backend

    def get_backend(self, name: str) -> QuantumBackend:
        if name not in self._backends:
            available = list(self._backends.keys())
            raise KeyError(f"Backend '{name}' not found. Available: {available}")
        return self._backends[name]

    def list_backends(self) -> list[str]:
        return list(self._backends.keys())

    def register_agent_type(self, name: str, agent_cls: type[BaseAgent]) -> None:
        self._agent_types[name] = agent_cls

    def get_agent_type(self, name: str) -> type[BaseAgent]:
        if name not in self._agent_types:
            available = list(self._agent_types.keys())
            raise KeyError(f"Agent type '{name}' not found. Available: {available}")
        return self._agent_types[name]

    def list_agent_types(self) -> list[str]:
        return list(self._agent_types.keys())


# Global registry instance
default_registry = Registry()
