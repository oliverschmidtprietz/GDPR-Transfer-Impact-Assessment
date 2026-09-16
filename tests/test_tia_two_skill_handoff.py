"""Two-skill proof (standard §12 step 8): tia emits a FILE; a consumer
reads it back with no orchestrator and no tia import. The consumer rule
below is test-local — no skill ships one (§11 gap 6); what this proves
is the document contract, not a shipped reader."""
import json
import subprocess
import sys
from pathlib import Path

import jsonschema

TIA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
VALIDATE = TIA_ROOT / "validator" / "validate.py"
FIXTURE = TIA_ROOT / "validator" / "fixtures" / "must_pass" / "minimal-signed.json"
ARTEFACT_SCHEMA = json.loads(
    (REPO_ROOT / "docs" / "standards" / "schemas"
     / "skill-artefact-1.1.schema.json").read_text(encoding="utf-8"))

INSTALLED_SIBLINGS = {"ropa", "toms-art32"}     # consumer's own knowledge


def resolve_handoffs(artefact: dict) -> dict:
    """Test-local consumer rule: an uninstalled sibling degrades to a
    non-blocking unknown, never an error (standard §7)."""
    resolved, unknowns = [], list(artefact["unknowns"])
    for h in artefact["handoffs"]:
        if h["sibling_skill"] in INSTALLED_SIBLINGS:
            resolved.append(h)
        else:
            unknowns.append({"id": f"uninstalled-{h['sibling_skill']}",
                             "question": f"handoff to uninstalled sibling "
                                         f"{h['sibling_skill']}: {h['reason']}",
                             "blocking": False})
    return {"resolved": resolved, "unknowns": unknowns}


def _emit(tmp_path, sidecar_doc):
    src = tmp_path / "sidecar.json"
    src.write_text(json.dumps(sidecar_doc), encoding="utf-8")
    out = tmp_path / "core.json"
    proc = subprocess.run([sys.executable, str(VALIDATE), str(src),
                           "--emit-core-artefact", str(out)],
                          capture_output=True, text=True)
    assert proc.returncode in (0, 1), proc.stderr
    return json.loads(out.read_text(encoding="utf-8"))


def test_round_trip_file_is_schema_valid_and_typed(tmp_path):
    artefact = _emit(tmp_path, json.loads(FIXTURE.read_text(encoding="utf-8")))
    jsonschema.validate(artefact, ARTEFACT_SCHEMA,
                        format_checker=jsonschema.FormatChecker())
    assert artefact["artefact_schema_version"] == "1.1"
    assert artefact["subject"]["type"] == "transfer"
    assert artefact["subject"]["org"] == "acme-gmbh"


def test_known_sibling_handoff_resolves(tmp_path):
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc["ropa_delta"] = {"emitted": True, "delta_ref": "delta.json"}
    result = resolve_handoffs(_emit(tmp_path, doc))
    assert [h["sibling_skill"] for h in result["resolved"]] == ["ropa"]


def test_uninstalled_sibling_degrades_to_a_nonblocking_unknown(tmp_path):
    artefact = _emit(tmp_path, json.loads(FIXTURE.read_text(encoding="utf-8")))
    artefact["handoffs"] = [{"sibling_skill": "consent-eprivacy",
                             "reason": "staged: uninstalled sibling"}]
    result = resolve_handoffs(artefact)
    assert result["resolved"] == []
    entry = next(u for u in result["unknowns"]
                 if u["id"] == "uninstalled-consent-eprivacy")
    assert entry["blocking"] is False
