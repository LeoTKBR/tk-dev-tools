from __future__ import annotations

import importlib.metadata
import re
from dataclasses import dataclass


REQUIRED_REQUIREMENTS = (
    "Pillow>=10.0.0",
    "PySide6>=6.7.0",
)


@dataclass(frozen=True)
class RequirementStatus:
    requirement: str
    name: str
    operator: str
    version: str
    installed_version: str | None
    satisfied: bool


_REQUIREMENT_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*(>=|==|<=|>|<)?\s*([A-Za-z0-9_.-]+)?\s*$")
_VERSION_RE = re.compile(r"\d+")


def _normalize_version(version: str) -> tuple[int, ...]:
    parts = [int(part) for part in _VERSION_RE.findall(version)]
    return tuple(parts) if parts else (0,)


def _compare_versions(installed: str, operator: str, required: str) -> bool:
    installed_parts = _normalize_version(installed)
    required_parts = _normalize_version(required)

    max_len = max(len(installed_parts), len(required_parts))
    installed_parts = installed_parts + (0,) * (max_len - len(installed_parts))
    required_parts = required_parts + (0,) * (max_len - len(required_parts))

    if operator == "==":
        return installed_parts == required_parts
    if operator == ">=":
        return installed_parts >= required_parts
    if operator == "<=":
        return installed_parts <= required_parts
    if operator == ">":
        return installed_parts > required_parts
    if operator == "<":
        return installed_parts < required_parts
    return True


def parse_requirement(requirement: str) -> tuple[str, str, str]:
    match = _REQUIREMENT_RE.match(requirement)
    if not match:
        raise ValueError(f"Unsupported requirement format: {requirement}")

    name, operator, version = match.groups()
    operator = operator or ""
    version = version or ""
    return name, operator, version


def get_requirement_status(requirement: str) -> RequirementStatus:
    name, operator, version = parse_requirement(requirement)
    try:
        installed_version = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return RequirementStatus(requirement, name, operator, version, None, False)

    if not operator or not version:
        return RequirementStatus(requirement, name, operator, version, installed_version, True)

    satisfied = _compare_versions(installed_version, operator, version)
    return RequirementStatus(requirement, name, operator, version, installed_version, satisfied)


def get_missing_requirements(requirements: tuple[str, ...] = REQUIRED_REQUIREMENTS) -> list[RequirementStatus]:
    missing: list[RequirementStatus] = []
    for requirement in requirements:
        status = get_requirement_status(requirement)
        if not status.satisfied:
            missing.append(status)
    return missing
