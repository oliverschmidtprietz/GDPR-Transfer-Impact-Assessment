"""SCHEMA-0: JSON Schema conformance for the tia sidecar. Findings-based.

Ported from toms-art32's SCHEMA-1 (toms_validator/rules/schema_conformance.py)
with a FormatChecker (standard §9.1 — a new adopter must not repeat ropa's
bare-validator gap) and a guarded schema load: an unreadable or invalid
schema file must never raise inside a rule (runner.py's never-raise wrapper
would catch it anyway, but SCHEMA-0 is non-overridable and must fail loudly
and predictably on genuinely broken input, not rely on the catch).
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from ..findings import Finding
from ..registry import rule

SPEC = "references/tia-sidecar-schema.json"


def _load_schema(ctx) -> dict:
    return json.loads(Path(ctx.schema_path).read_text(encoding="utf-8"))


@rule(id="SCHEMA-0", severity="rejection", category="schema",
      description="Sidecar conforms to tia-sidecar-schema.json (Draft 2020-12, FormatChecker).",
      spec_anchor=SPEC)
def schema_conformance(sidecar, ctx):
    try:
        schema = _load_schema(ctx)
    except (OSError, json.JSONDecodeError) as exc:
        return [Finding(
            rule_id="SCHEMA-0", category="schema", severity="rejection",
            message=f"Could not load schema at {ctx.schema_path}: "
                    f"{type(exc).__name__}: {exc}",
            spec_anchor=SPEC)]

    out = []
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for err in sorted(validator.iter_errors(sidecar), key=lambda e: list(e.path)):
        out.append(Finding(
            rule_id="SCHEMA-0", category="schema", severity="rejection",
            message=f"Schema violation at /{'/'.join(map(str, err.path))}: {err.message}",
            spec_anchor=SPEC, field="/".join(map(str, err.path)) or None))
    return out
