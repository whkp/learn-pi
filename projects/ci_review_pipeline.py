"""Compose offline course checks into a small deterministic CI report."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewReport:
    passed: bool
    passed_checks: tuple[str, ...]
    failed_checks: tuple[str, ...]


def build_review_report(
    *,
    markdown_links_ok: bool,
    course_contract_ok: bool,
    unit_tests_ok: bool,
) -> ReviewReport:
    """Return check names in a stable order that a CI job can print."""
    checks = (
        ("course-contract", course_contract_ok),
        ("markdown-links", markdown_links_ok),
        ("unit-tests", unit_tests_ok),
    )
    passed = tuple(name for name, succeeded in checks if succeeded)
    failed = tuple(name for name, succeeded in checks if not succeeded)
    return ReviewReport(not failed, passed, failed)
