"""CLI tests for --emit-core-artefact (adoption task 9).

Same contract as ropa's and toms-art32's flags: the emitted artefact is
built from the LIVE validation result, never the sidecar's embedded
validation block. Additionally closes the "no failed-status emission test"
deferred minor from the gap-5 reviews for tia's side: a genuinely blocked
document must still get a written artefact (outcome.status == "blocked")
and the process must still exit 1 — the emission never suppresses or alters
the exit code (design spec §5.3).
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[3]
TIA_ROOT = REPO_ROOT / "skills" / "tia"
VALIDATE = TIA_ROOT / "validator" / "validate.py"
FIXTURE = TIA_ROOT / "validator" / "fixtures" / "must_pass" / "minimal-signed.json"
ARTEFACT_SCHEMA = json.loads(
    (REPO_ROOT / "docs" / "standards" / "schemas"
     / "skill-artefact-1.1.schema.json").read_text(encoding="utf-8"))


def run_cli(*argv):
    return subprocess.run(
        [sys.executable, str(VALIDATE), *map(str, argv)],
        capture_output=True, text=True)


def _load_validate_module():
    """Load validate.py as an importable module (distinct from __main__), so
    a test can monkeypatch its `to_core_artefact` binding in-process — a
    subprocess CLI invocation cannot inject a forced exception."""
    spec = importlib.util.spec_from_file_location(
        "tia_validate_under_test", VALIDATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_emit_writes_schema_valid_core_artefact_and_leaves_report_unchanged(tmp_path):
    out = tmp_path / "core.json"
    proc = run_cli(FIXTURE, "--emit-core-artefact", out, "--format", "json")
    assert proc.returncode == 0, proc.stderr
    artefact = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(artefact, ARTEFACT_SCHEMA,
                        format_checker=jsonschema.FormatChecker())
    assert artefact["skill"] == "tia"
    assert artefact["artefact_schema_version"] == "1.1"
    # stdout still carries the normal findings report 2.0 envelope
    envelope = json.loads(proc.stdout)
    assert envelope["report_schema_version"] == "2.0"
    assert envelope["status"] == "passed"


def test_emit_reflects_live_result_not_embedded_validation_block(tmp_path):
    sidecar = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # Embedded block lies: claims the register failed. The live run passes.
    sidecar["validation"] = {"status": "failed", "findings": []}
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(sidecar), encoding="utf-8")
    out = tmp_path / "core.json"
    proc = run_cli(tampered, "--emit-core-artefact", out)
    assert proc.returncode == 0, proc.stderr
    artefact = json.loads(out.read_text(encoding="utf-8"))
    # "complete" (from the live "passed") proves the live result won;
    # "blocked" would mean the embedded "failed" leaked through.
    assert artefact["outcome"]["status"] == "complete"


def test_emit_blocked_document_still_writes_artefact_and_exits_1(tmp_path):
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # insufficient + proceed is a genuine, non-overridden contradiction
    # (EFFECT-BLOCKS-PROCEED) — the live run fails.
    doc["step4"]["overall_effectiveness"] = "insufficient"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(doc), encoding="utf-8")
    out = tmp_path / "core.json"
    proc = run_cli(bad, "--emit-core-artefact", out)
    assert proc.returncode == 1, proc.stderr
    assert out.exists(), "core artefact must still be written for a blocked document"
    artefact = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(artefact, ARTEFACT_SCHEMA,
                        format_checker=jsonschema.FormatChecker())
    assert artefact["outcome"]["status"] == "blocked"


def test_adapter_exception_falls_back_to_minimal_blocked_artefact(tmp_path, monkeypatch, capsys):
    # Adversarial review finding 3 requirement (3): validate.py must wrap
    # to_core_artefact() emission so that an adapter exception still leaves
    # stdout/exit unchanged and writes a minimal blocked artefact with one
    # rejection finding. to_core_artefact() is fully guarded and should
    # never actually raise — this is a defense-in-depth net, exercised here
    # by forcing a synthetic crash via monkeypatch.
    module = _load_validate_module()

    def boom(sidecar, *, skill_version):
        raise RuntimeError("synthetic adapter crash")

    monkeypatch.setattr(module, "to_core_artefact", boom)

    out = tmp_path / "core.json"
    exit_code = module.main([str(FIXTURE), "--emit-core-artefact", str(out),
                             "--format", "json"])
    captured = capsys.readouterr()

    # Report on stdout and the exit code are exactly what a plain run of the
    # (valid) fixture produces — untouched by the adapter crash.
    assert exit_code == 0
    envelope = json.loads(captured.out)
    assert envelope["status"] == "passed"

    assert out.exists(), "a minimal blocked artefact must still be written"
    artefact = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(artefact, ARTEFACT_SCHEMA,
                        format_checker=jsonschema.FormatChecker())
    assert artefact["skill"] == "tia"
    assert artefact["outcome"]["status"] == "blocked"
    rejections = [g for g in artefact["gaps"] if g["severity"] == "rejection"]
    assert len(rejections) == 1
    assert "synthetic adapter crash" in rejections[0]["message"]
