"""Rule registry + @rule decorator. Import-time registration into RULES."""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RuleSpec:
    id: str
    severity: str
    category: str
    description: str
    spec_anchor: str


RULES: dict[str, tuple[RuleSpec, Callable]] = {}


def rule(*, id: str, severity: str, category: str, description: str, spec_anchor: str):
    def decorator(fn: Callable) -> Callable:
        spec = RuleSpec(id=id, severity=severity, category=category,
                        description=description, spec_anchor=spec_anchor)
        if id in RULES:
            raise ValueError(f"Duplicate rule id: {id}")
        RULES[id] = (spec, fn)
        return fn
    return decorator
