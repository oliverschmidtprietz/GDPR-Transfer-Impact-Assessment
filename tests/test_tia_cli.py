import json
import subprocess
import sys
from pathlib import Path

import pytest

TIA_ROOT = Path(__file__).resolve().parents[1]
VALIDATE = TIA_ROOT / "validator" / "validate.py"
FIXTURE = TIA_ROOT / "validator" / "fixtures" / "must_pass" / "minimal-signed.json"


def run_cli(*argv):
    return subprocess.run([sys.executable, str(VALIDATE), *map(str, argv)],
                          capture_output=True, text=True)


def test_valid_sidecar_exits_0_with_a_2_0_envelope():
    proc = run_cli(FIXTURE, "--format", "json")
    assert proc.returncode == 0, proc.stderr
    envelope = json.loads(proc.stdout)
    assert envelope["report_schema_version"] == "2.0"
    assert envelope["skill"] == "tia"
    assert envelope["status"] == "passed"
    assert envelope["artefact_path"].endswith("minimal-signed.json")


def test_blocking_finding_exits_1(tmp_path):
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc["step4"]["overall_effectiveness"] = "insufficient"
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    proc = run_cli(p)
    assert proc.returncode == 1
    assert "EFFECT-BLOCKS-PROCEED" in proc.stdout


def test_missing_file_exits_2(tmp_path):
    proc = run_cli(tmp_path / "nope.json")
    assert proc.returncode == 2


def test_malformed_json_exits_2(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{not json", encoding="utf-8")
    assert run_cli(p).returncode == 2


def test_malformed_delta_exits_2(tmp_path):
    bad = tmp_path / "delta.json"
    bad.write_text("{not json", encoding="utf-8")
    assert run_cli(FIXTURE, "--delta", bad).returncode == 2


@pytest.mark.parametrize("payload", ["[]", '"x"', "null", "42"],
                         ids=["array", "string", "null", "number"])
def test_non_object_sidecar_exits_2_cleanly(tmp_path, payload):
    p = tmp_path / "not-an-object.json"
    p.write_text(payload, encoding="utf-8")
    proc = run_cli(p)
    assert proc.returncode == 2, proc.stderr
    assert "Traceback" not in proc.stderr
    assert proc.stderr.strip() != ""


@pytest.mark.parametrize("payload", ["[]", '"x"', "null", "42"],
                         ids=["array", "string", "null", "number"])
def test_non_object_delta_exits_1_with_delta_shape_naming_the_type(tmp_path, payload):
    # Round 2 ruling (spec §5.3): unlike the sidecar, a --delta file has a
    # rule (DELTA-SHAPE) that can absorb a bad top-level shape inside the
    # per-rule never-raise net, so a wrong-shaped --delta must not abort the
    # whole run before any rule executes — a sound TIA with a broken delta
    # file still gets a full findings report (exit 1), not a CLI-misuse
    # exit 2. Exit 2 is reserved for genuinely unreadable/unparseable input.
    delta = tmp_path / "not-an-object.json"
    delta.write_text(payload, encoding="utf-8")
    proc = run_cli(FIXTURE, "--delta", delta, "--format", "json")
    assert proc.returncode == 1, proc.stderr
    envelope = json.loads(proc.stdout)
    findings = [f for f in envelope["findings"] if f["rule_id"] == "DELTA-SHAPE"]
    assert findings, envelope["findings"]
    assert any("object" in f["message"] for f in findings), findings


def test_missing_delta_file_exits_2(tmp_path):
    proc = run_cli(FIXTURE, "--delta", tmp_path / "nope-delta.json")
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr


def test_valid_sidecar_and_valid_delta_exits_0(tmp_path):
    delta = tmp_path / "delta.json"
    delta.write_text(json.dumps({
        "schema_version": "2.0",
        "source_skill": "tia",
        "produced_at": "2026-08-01T00:00:00Z",
        "target_activity_id": "act-001",
        "patches": [
            {"op": "add", "path": "/transfers/0/tia_ref", "value": "TIA-US-2026-001"},
            {"op": "add", "path": "/transfers/0/tia_date", "value": "2026-08-02"},
        ],
    }), encoding="utf-8")
    proc = run_cli(FIXTURE, "--delta", delta, "--format", "json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    envelope = json.loads(proc.stdout)
    assert envelope["status"] == "passed"


def test_delta_flag_reaches_rule_16(tmp_path):
    delta = tmp_path / "delta.json"
    delta.write_text(json.dumps({"schema_version": "1.0", "patches": []}),
                     encoding="utf-8")
    proc = run_cli(FIXTURE, "--delta", delta, "--format", "json")
    assert proc.returncode == 1
    ids = {f["rule_id"] for f in json.loads(proc.stdout)["findings"]}
    assert "DELTA-SHAPE" in ids


def test_emit_core_artefact_to_missing_parent_exits_2_cleanly(tmp_path):
    # I2: the write in main() was unguarded — an unwritable output path
    # (here: a parent directory that doesn't exist) raised FileNotFoundError
    # after the Result was already computed, producing a traceback and
    # exit 1 (colliding with "blocked"). Must fail closed to exit 2, like
    # every other unreadable/unusable-input case, with no traceback and the
    # findings report never silently discarded.
    out = tmp_path / "no-such-dir" / "core.json"
    proc = run_cli(FIXTURE, "--emit-core-artefact", out, "--format", "json")
    assert proc.returncode == 2, proc.stderr
    assert "Traceback" not in proc.stderr
    assert proc.stderr.strip() != ""
    assert not out.exists()


def _deeply_nested_json_path(tmp_path, depth=10_000):
    p = tmp_path / "deep.json"
    p.write_text("[" * depth + "]" * depth, encoding="utf-8")
    return p


def test_deeply_nested_sidecar_exits_2_not_1(tmp_path):
    # I3: json.loads raises RecursionError on deeply nested input, which
    # _load_json's except clause did not catch — traceback + exit 1,
    # colliding with "blocked" and producing no findings document at all.
    p = _deeply_nested_json_path(tmp_path)
    proc = run_cli(p)
    assert proc.returncode == 2, proc.stderr
    assert "Traceback" not in proc.stderr


def test_deeply_nested_delta_exits_2_not_1(tmp_path):
    p = _deeply_nested_json_path(tmp_path)
    proc = run_cli(FIXTURE, "--delta", p)
    assert proc.returncode == 2, proc.stderr
    assert "Traceback" not in proc.stderr


def test_malformed_overrides_yields_findings_report_not_traceback(tmp_path):
    # Adversarial review finding 3 (tia's share): overrides: 42 (not a list)
    # raised TypeError inside runner.py's _valid_overrides, before any rule
    # ran — no findings report, no exit code, just a traceback. A malformed
    # top-level field must degrade to a normal findings report with a
    # rejection finding (SCHEMA-0 catches the shape) and the documented
    # exit code, never a crash.
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc["overrides"] = 42
    p = tmp_path / "bad-overrides.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    proc = run_cli(p, "--format", "json")
    assert proc.returncode == 1, proc.stderr
    assert "Traceback" not in proc.stderr
    envelope = json.loads(proc.stdout)
    assert envelope["status"] == "failed"
    assert any(f["rule_id"] == "SCHEMA-0" and "overrides" in f["message"]
               for f in envelope["findings"]), envelope["findings"]


@pytest.mark.parametrize("bad_overrides", [42, "not-a-list", {"rule_id": "x"}, 3.5, True],
                         ids=["int", "string", "dict", "float", "bool"])
def test_malformed_overrides_of_various_types_never_raise(tmp_path, bad_overrides):
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc["overrides"] = bad_overrides
    p = tmp_path / "bad-overrides.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    proc = run_cli(p, "--format", "json")
    assert "Traceback" not in proc.stderr
    assert proc.returncode in (0, 1), proc.stderr


def test_malformed_overrides_with_emit_core_artefact_still_writes_artefact(tmp_path):
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc["overrides"] = 42
    p = tmp_path / "bad-overrides.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    out = tmp_path / "core.json"
    proc = run_cli(p, "--emit-core-artefact", out, "--format", "json")
    assert proc.returncode == 1, proc.stderr
    assert "Traceback" not in proc.stderr
    assert out.exists(), "core artefact must still be written when a top-level field is malformed"
    artefact = json.loads(out.read_text(encoding="utf-8"))
    assert artefact["outcome"]["status"] == "blocked"


def test_skill_version_is_read_live_from_skill_md():
    proc = run_cli(FIXTURE, "--format", "json")
    reported = json.loads(proc.stdout)["skill_version"]
    skill_md = (TIA_ROOT / "SKILL.md").read_text(encoding="utf-8")
    line = next(l for l in skill_md.splitlines()
                if l.strip().startswith("version:"))
    assert reported == line.split(":", 1)[1].strip()   # no literal — survives the v1.4 bump


def test_validate_py_declares_its_own_dependencies():
    """F-12: validate.py must carry a PEP 723 inline-metadata header so
    `uv run skills/tia/validator/validate.py` works with zero prior setup,
    the way ropa's validate.py already does (skills/ropa/validator/validate.py:1-5)."""
    header = VALIDATE.read_text(encoding="utf-8").splitlines()[:6]
    assert header[0] == "#!/usr/bin/env -S uv run --script"
    assert header[1] == "# /// script"
    assert any("jsonschema" in line for line in header)
    assert "# ///" in header
