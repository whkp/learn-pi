"""A small, offline model registry for explaining provider selection.

This module is a Python teaching model. Pi's real model registry and provider
adapters are TypeScript code; see docs/pi-source-map.md for the pinned source
baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class DuplicateModel(ValueError):
    """Raised when a provider/model pair is registered more than once."""


class UnknownModel(LookupError):
    """Raised when a requested provider/model pair is absent."""


@dataclass(frozen=True)
class ModelSelection:
    """The minimum model metadata a caller needs to select a model safely."""

    provider_id: str
    model_id: str
    display_name: str
    context_window: int


class ProviderRegistry:
    """A deterministic registry that stores metadata, never credentials."""

    def __init__(self) -> None:
        self._models: dict[tuple[str, str], ModelSelection] = {}

    def register(
        self,
        provider_id: str,
        model_id: str,
        display_name: str,
        context_window: int,
    ) -> ModelSelection:
        _validate_identifier("provider id", provider_id)
        _validate_identifier("model id", model_id)
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("display name must be a non-empty string")
        if isinstance(context_window, bool) or not isinstance(context_window, int) or context_window <= 0:
            raise ValueError("context window must be a positive integer")

        key = (provider_id, model_id)
        if key in self._models:
            raise DuplicateModel(f"model already registered: {provider_id}/{model_id}")
        selection = ModelSelection(
            provider_id=provider_id,
            model_id=model_id,
            display_name=display_name.strip(),
            context_window=context_window,
        )
        self._models[key] = selection
        return selection

    def select(self, provider_id: str, model_id: str) -> ModelSelection:
        try:
            return self._models[(provider_id, model_id)]
        except KeyError as error:
            raise UnknownModel(f"unknown model: {provider_id}/{model_id}") from error

    def catalog(self) -> tuple[ModelSelection, ...]:
        """Return a stable immutable catalog for menus and tests."""
        return tuple(self._models[key] for key in sorted(self._models))


def _validate_identifier(label: str, value: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} must contain lowercase letters, digits, '.', '_' or '-'")
