"""Tests for the offline provider/model registry teaching model."""

from __future__ import annotations

import unittest

from learn_pi_lab.labs.provider_registry import (
    DuplicateModel,
    ModelSelection,
    ProviderRegistry,
    UnknownModel,
)


class ProviderRegistryTests(unittest.TestCase):
    def test_registry_selects_a_model_by_provider_and_id(self) -> None:
        registry = ProviderRegistry()
        registry.register(
            provider_id="openai-completions",
            model_id="demo-1",
            display_name="Demo One",
            context_window=128_000,
        )

        selection = registry.select("openai-completions", "demo-1")

        self.assertEqual(
            ModelSelection(
                provider_id="openai-completions",
                model_id="demo-1",
                display_name="Demo One",
                context_window=128_000,
            ),
            selection,
        )

    def test_registry_rejects_duplicate_and_unknown_models(self) -> None:
        registry = ProviderRegistry()
        registry.register("demo", "model", "Model", 8_192)

        with self.assertRaises(DuplicateModel):
            registry.register("demo", "model", "Model", 8_192)
        with self.assertRaises(UnknownModel):
            registry.select("demo", "missing")

    def test_registry_rejects_invalid_identifiers_and_nonpositive_context(self) -> None:
        registry = ProviderRegistry()

        for provider_id, model_id, context_window in (
            ("", "model", 1),
            ("demo provider", "model", 1),
            ("demo", "", 1),
            ("demo", "model id", 1),
            ("demo", "model", 0),
        ):
            with self.subTest(provider_id=provider_id, model_id=model_id):
                with self.assertRaises(ValueError):
                    registry.register(provider_id, model_id, "Demo", context_window)

    def test_catalog_is_sorted_and_immutable(self) -> None:
        registry = ProviderRegistry()
        registry.register("z-provider", "z-model", "Z", 1)
        registry.register("a-provider", "a-model", "A", 2)

        catalog = registry.catalog()

        self.assertEqual(
            [("a-provider", "a-model"), ("z-provider", "z-model")],
            [(entry.provider_id, entry.model_id) for entry in catalog],
        )
        self.assertIsInstance(catalog, tuple)


if __name__ == "__main__":
    unittest.main()
