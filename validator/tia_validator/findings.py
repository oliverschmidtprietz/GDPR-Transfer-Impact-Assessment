"""Finding dataclass — a single validator output entry.

Severity is the GATE ("does this stop the job?"); priority is an optional risk
grading that never affects the gate (D-WS3-02). This axis is the deterministic
validator's own diagnostics ONLY. tia has no legacy severity vocabulary to
migrate (unlike toms-art32's SEVERITY_MIGRATION), so this module carries only
the Finding shape itself.
"""
from __future__ import annotations  # PEP 604 "|" unions below, on a requires-python >=3.9 file

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class Finding:
    rule_id: str
    category: str
    severity: str             # "rejection" | "warning" | "info"
    message: str
    spec_anchor: str
    priority: Optional[str] = None      # "high" | "medium" | "low"
    entry_type: Optional[str] = None
    entry_id: Optional[str] = None
    field: Optional[str] = None
    fix_hint: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}
