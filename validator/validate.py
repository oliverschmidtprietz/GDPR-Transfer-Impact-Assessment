#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema>=4.21"]
# ///
"""tia validator CLI — portfolio standard §2 interface.

Exit codes: 0 = not blocked, 1 = blocked, 2 = unreadable/malformed input.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tia_validator.rules  # noqa: E402,F401  (populates the registry)
from tia_validator.runner import Context, validate, to_findings_json  # noqa: E402
from tia_validator.core_artefact import to_core_artefact  # noqa: E402

DEFAULT_SCHEMA = HERE.parent / "references" / "tia-sidecar-schema.json"
DEFAULT_REFS = HERE.parent / "references"


def _minimal_blocked_artefact(sidecar, exc: Exception, *, skill_version: str) -> dict:
    """Fallback artefact written when to_core_artefact() itself raises.

    Defense in depth for adversarial review finding 3 (3): to_core_artefact
    is guarded end-to-end (isinstance/.get chains, never raises on any
    dict-shaped input) and should never actually reach this, but a
    projection adapter must never be the reason emission is silently lost.
    The report on stdout and the exit code are computed from `result`
    before this ever runs, so they are untouched either way."""
    cover = sidecar.get("cover") if isinstance(sidecar, dict) else None
    cover = cover if isinstance(cover, dict) else {}
    tia_ref = cover.get("tia_ref")
    subject_id = (tia_ref if isinstance(tia_ref, str) and tia_ref.strip()
                 else "unknown-transfer")
    now = (datetime.now(timezone.utc)
           .isoformat(timespec="seconds").replace("+00:00", "Z"))
    return {
        "artefact_schema_version": "1.1",
        "skill": "tia",
        "skill_version": skill_version,
        "generated_at": now,
        "subject": {"id": subject_id, "label": subject_id, "type": "transfer"},
        "outcome": {
            "status": "blocked",
            "summary": f"Core artefact projection failed: {type(exc).__name__}: {exc}",
        },
        "gaps": [{
            "id": "CORE-ARTEFACT-CRASH",
            "severity": "rejection",
            "message": f"to_core_artefact raised {type(exc).__name__}: {exc}",
        }],
        "sources": [],
        "handoffs": [],
        "unknowns": [],
    }


def _skill_version() -> str:
    """Read the live version from SKILL.md frontmatter — never hard-code it
    (CLAUDE.md; note version: is indented under metadata:, hence .strip())."""
    skill_md = HERE.parent / "SKILL.md"
    for line in skill_md.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version:"):
            return line.split(":", 1)[1].strip()
    raise SystemExit("SKILL.md has no version: field")


def _load_json(path: Path, what: str, *, require_object: bool = True):
    """Load and parse `path` as JSON. Missing file, unreadable file, or
    invalid JSON syntax is always unreadable/malformed input: exit 2 with a
    clean stderr message. This guard lives in the read, not around
    validate(), so a genuine internal bug downstream still surfaces loudly
    rather than being reclassified as bad input.

    `require_object` additionally rejects (exit 2) syntactically valid JSON
    whose top-level shape isn't an object. It defaults True (used for the
    sidecar: `_valid_overrides(sidecar)` in runner.py runs outside any
    rule's never-raise net, so a non-object sidecar would otherwise crash
    before a single rule executes — there is no other place to catch it).
    The --delta caller passes require_object=False: rule 16 (DELTA-SHAPE)
    already absorbs a wrong-shaped delta inside the rule loop's safety net
    and reports it as a named finding, so a broken --delta must not abort
    an otherwise-sound TIA's whole findings report (round 2 fix, design
    spec §5.3 — a blocked/malformed-input result is still a legitimate,
    emitted signal)."""
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Error: {what} not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    except (OSError, json.JSONDecodeError, RecursionError) as exc:
        print(f"Error: {what} unreadable/malformed: {exc}", file=sys.stderr)
        raise SystemExit(2)
    if require_object and not isinstance(parsed, dict):
        print(f"Error: {what} must be a JSON object, got "
              f"{type(parsed).__name__}: {path}", file=sys.stderr)
        raise SystemExit(2)
    return parsed


def main(argv=None):
    p = argparse.ArgumentParser(prog="tia-validator")
    p.add_argument("sidecar", type=Path)
    p.add_argument("--mode", choices=["internal", "submission"], default="internal")
    p.add_argument("--format", choices=["human", "json"], default="human")
    p.add_argument("--schema-path", type=Path, default=DEFAULT_SCHEMA)
    p.add_argument("--references-dir", type=Path, default=DEFAULT_REFS)
    p.add_argument("--delta", type=Path, default=None,
                   help="Emitted interchange delta file for rules 6 and 16. "
                        "Required (rule 6, DELTA-FILE-REQUIRED, non-overridable) "
                        "whenever ropa_delta.emitted is true — the sidecar's "
                        "delta_ref must also resolve to this same file. Without "
                        "it, rule 16 (DELTA-SHAPE) does not evaluate.")
    p.add_argument(
        "--emit-core-artefact", type=Path, default=None, metavar="PATH",
        help=("After validation, write the portfolio core artefact "
              "(skill-artefact-1.1 schema) projection of THIS run's result to "
              "PATH. Built from the live validation result, never the "
              "sidecar's embedded validation block. Report and exit code "
              "unchanged."))
    args = p.parse_args(argv)

    sidecar = _load_json(args.sidecar, "sidecar")
    delta = (_load_json(args.delta, "delta", require_object=False)
             if args.delta is not None else None)

    ctx = Context(schema_path=args.schema_path,
                  references_dir=args.references_dir,
                  mode=args.mode,
                  artefact_path=str(args.sidecar),
                  delta=delta,
                  delta_provided=args.delta is not None,
                  delta_path=args.delta)
    result = validate(sidecar, ctx)

    if args.emit_core_artefact is not None:
        live_sidecar = {**sidecar, "validation": {
            "status": result.status,
            "findings": [f.to_dict() for f in result.findings],
        }}
        try:
            artefact = to_core_artefact(live_sidecar,
                                        skill_version=_skill_version())
        except Exception as exc:  # defense in depth — see _minimal_blocked_artefact
            artefact = _minimal_blocked_artefact(sidecar, exc,
                                                 skill_version=_skill_version())
        try:
            args.emit_core_artefact.write_text(
                json.dumps(artefact, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"Error: --emit-core-artefact path unwritable: {exc}",
                 file=sys.stderr)
            raise SystemExit(2)

    if args.format == "json":
        print(json.dumps(to_findings_json(result, skill_version=_skill_version()),
                         indent=2))
    else:
        print(f"status: {result.status}  ({len(result.findings)} findings)")
        for f in result.findings:
            print(f"  [{f.severity}] {f.rule_id}: {f.message}")
    return 1 if result.status == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
