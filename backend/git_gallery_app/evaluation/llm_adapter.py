"""Single integration point for evaluation responses."""

from __future__ import annotations

import json
from typing import Protocol


class LLMAdapter(Protocol):
    """Interface implemented by mock and future real-model adapters."""

    mode: str

    def generate_response(self, case: dict, system_prompt: str) -> str:
        """Analyze the selected task with its repository data."""
        ...


class MockLLMAdapter:
    """Deterministic task-and-repository fixture; it does not call an LLM."""

    mode = "MOCK"

    def generate_response(self, case: dict, system_prompt: str) -> str:
        del system_prompt
        return json.dumps(case["expected_output"])


def build_adapter(mode: str) -> LLMAdapter:
    """Create the requested adapter without silently changing evaluation mode."""
    if mode == "mock":
        return MockLLMAdapter()
    if mode == "real":
        raise RuntimeError(
            "Real LLM evaluation was requested, but the project LLM integration "
            "is not available yet. Implement a real adapter here; mock responses "
            "will not be used as a fallback."
        )
    raise ValueError(f"Unknown adapter mode: {mode}")


# TODO: Once the team finalizes the LLM contract, implement an adapter that
# sends case["task"], case["repository_data"], and system_prompt to it.
# Keep credentials in the team's approved configuration, never in this file.