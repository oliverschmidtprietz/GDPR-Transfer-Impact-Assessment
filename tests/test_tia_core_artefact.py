"""Unit tests for tia_validator.core_artefact.to_core_artefact — the
projection adapter onto the portfolio skill-artefact 1.1 core (task 9).

tia is the first 1.1 emitter (typed subject) and the first adopter to
populate sources[]/handoffs[]/unknowns[] from day one (design spec §6,
task-9-brief.md) rather than inheriting the shipped adapters' empty-literal
gap.
"""
import json
import sys
from pathlib import Path

import jsonschema
import pytest

TIA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(TIA_ROOT / "validator"))

from tia_validator.core_artefact import to_core_artefact  # noqa: E402

FIXTURE_PATH = (TIA_ROOT / "validator" / "fixtures" / "must_pass"
                / "minimal-signed.json")
ARTEFACT_SCHEMA = json.loads(
    (REPO_ROOT / "docs" / "standards" / "schemas"
     / "skill-artefact-1.1.schema.json").read_text(encoding="utf-8"))


def _base_sidecar() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _validate_against_schema(doc: dict) -> None:
    jsonschema.validate(doc, ARTEFACT_SCHEMA,
                        format_checker=jsonschema.FormatChecker())


# ---------------------------------------------------------------------------
# Status mapping — all four asserted individually (WS-3 review lesson: an
# unasserted mapping is an unverified mapping).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("validation_status,expected_outcome", [
    ("passed", "complete"),
    ("passed_with_warnings", "provisional"),
    ("passed_with_override", "provisional"),
    ("failed", "blocked"),
])
def test_status_mapping(validation_status, expected_outcome):
    sidecar = _base_sidecar()
    sidecar["validation"] = {"status": validation_status, "findings": []}
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["outcome"]["status"] == expected_outcome
    _validate_against_schema(artefact)


def test_unknown_status_fails_closed_to_blocked():
    sidecar = _base_sidecar()
    sidecar["validation"] = {"status": "not-a-real-status", "findings": []}
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["outcome"]["status"] == "blocked"


def test_missing_validation_block_fails_closed_to_blocked():
    sidecar = _base_sidecar()
    del sidecar["validation"]
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["outcome"]["status"] == "blocked"


# ---------------------------------------------------------------------------
# Subject block
# ---------------------------------------------------------------------------

def test_subject_block_exact_from_fixture_cover():
    sidecar = _base_sidecar()
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["subject"] == {
        "id": "TIA-US-2026-001",
        "label": "US transfer — payroll processor",
        "type": "transfer",
        "org": "acme-gmbh",
    }


def test_org_key_omitted_when_org_slug_missing():
    sidecar = {
        "cover": {"tia_ref": "TIA-XX-2026-099", "title": "Some transfer"},
    }
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert "org" not in artefact["subject"]
    assert artefact["subject"]["id"] == "TIA-XX-2026-099"
    assert artefact["subject"]["label"] == "Some transfer"
    assert artefact["subject"]["type"] == "transfer"


def test_subject_falls_back_on_malformed_cover_without_crashing():
    sidecar = {"cover": "not-an-object"}
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["subject"]["id"] == "unknown-transfer"
    assert artefact["subject"]["label"] == "unknown-transfer"
    assert "org" not in artefact["subject"]


def test_org_slug_is_normalised_via_slugify_convention_and_still_validates():
    # I1: org_slug flows in verbatim from untrusted input — SCHEMA-0 may
    # already have rejected the sidecar, but the artefact must still be
    # schema-valid (the "blocked artefact is a legitimate handoff signal"
    # guarantee). Slugify: lowercase; runs of non-alphanumerics -> single
    # `-`; strip edge hyphens (same convention as toms-art32's _slugify).
    sidecar = _base_sidecar()
    sidecar["cover"]["org_slug"] = "Acme GmbH"
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["subject"]["org"] == "acme-gmbh"
    _validate_against_schema(artefact)


def test_org_slug_omitted_when_slugify_collapses_to_empty():
    sidecar = _base_sidecar()
    sidecar["cover"]["org_slug"] = "!!!"
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert "org" not in artefact["subject"]
    _validate_against_schema(artefact)


# ---------------------------------------------------------------------------
# sources[] — populated from day one (gap 8 must not be inherited)
# ---------------------------------------------------------------------------

def test_sources_nonempty_for_us_fixture_and_contains_expected_lock_keys():
    sidecar = _base_sidecar()  # US, dpf_reliance: null -> us-non-dpf
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    ids = {s["id"] for s in artefact["sources"]}
    assert artefact["sources"], "sources[] must not be empty for a resolvable fixture"
    assert "references/country-profiles/us-non-dpf.md" in ids
    assert "references/edpb-six-steps.md" in ids
    for s in artefact["sources"]:
        assert s["last_verified"]
        assert s["citation"]


def test_sources_us_dpf_when_dpf_reliance_present():
    sidecar = _base_sidecar()
    sidecar["step2"]["dpf_reliance"] = {"verified_at": "2026-08-01"}
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    ids = {s["id"] for s in artefact["sources"]}
    assert "references/country-profiles/us-dpf.md" in ids
    assert "references/country-profiles/us-non-dpf.md" not in ids


def test_sources_art49_mechanism_selects_derogations_source():
    sidecar = _base_sidecar()
    sidecar["step1"]["destination_country"] = "IN"
    sidecar["step2"]["mechanism"] = "art49"
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    ids = {s["id"] for s in artefact["sources"]}
    assert "references/country-profiles/in.md" in ids
    assert "references/art49-derogations.md" in ids
    assert "references/edpb-six-steps.md" not in ids


def test_sources_unmapped_country_falls_back_to_generic_assessment():
    sidecar = _base_sidecar()
    sidecar["step1"]["destination_country"] = "ZZ"
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    ids = {s["id"] for s in artefact["sources"]}
    assert "references/country-profiles/generic-assessment.md" in ids


# ---------------------------------------------------------------------------
# handoffs[] — the no-reference-no-handoff amendment (2026-08-11), tested in
# both directions.
# ---------------------------------------------------------------------------

def test_handoffs_empty_when_not_emitted():
    sidecar = _base_sidecar()
    sidecar["ropa_delta"] = {"emitted": False, "delta_ref": None}
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["handoffs"] == []


def test_handoffs_empty_when_emitted_true_but_delta_ref_null():
    # The amendment: an emission claim with no reference is never advertised
    # as a handoff — it is now a DELTA-FILE-REQUIRED rejection instead.
    sidecar = _base_sidecar()
    sidecar["ropa_delta"] = {"emitted": True, "delta_ref": None}
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["handoffs"] == []


def test_handoffs_names_ropa_when_emitted_true_with_real_delta_ref():
    sidecar = _base_sidecar()
    sidecar["ropa_delta"] = {"emitted": True, "delta_ref": "deltas/TIA-US-2026-001.json"}
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["handoffs"] == [{
        "sibling_skill": "ropa",
        "reason": ("TIA outcome recorded against the RoPA transfer row via "
                   "the inbound-schema-2.0 delta."),
        "payload_ref": "deltas/TIA-US-2026-001.json",
    }]


# ---------------------------------------------------------------------------
# unknowns[]
# ---------------------------------------------------------------------------

def test_unknowns_entry_for_onward_present_yes_ref_null():
    sidecar = _base_sidecar()
    sidecar["step1"]["onward_transfers"] = {"present": "yes", "child_assessment_ref": None}
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["unknowns"] == [{
        "id": "onward-child-assessment",
        "question": ("Onward transfer declared but no child assessment ref "
                     "recorded — each hop needs its own Chapter V analysis."),
        "blocking": False,
    }]


def test_unknowns_empty_for_onward_present_yes_with_ref():
    sidecar = _base_sidecar()
    sidecar["step1"]["onward_transfers"] = {"present": "yes",
                                            "child_assessment_ref": "TIA-CHILD-001"}
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["unknowns"] == []


def test_unknowns_empty_for_onward_present_no():
    sidecar = _base_sidecar()
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["unknowns"] == []


# ---------------------------------------------------------------------------
# unknowns[] — v1.1 additions: "unknown" mechanism and open conditions
# (adversarial review findings 11/12, task 2c).
# ---------------------------------------------------------------------------

def test_unknowns_entry_for_unknown_mechanism():
    sidecar = _base_sidecar()
    sidecar["step2"]["mechanism"] = "unknown"
    artefact = to_core_artefact(sidecar, skill_version="1.6")
    ids = {u["id"] for u in artefact["unknowns"]}
    assert "mechanism-unknown" in ids
    entry = next(u for u in artefact["unknowns"] if u["id"] == "mechanism-unknown")
    assert entry["blocking"] is False
    _validate_against_schema(artefact)


def test_unknowns_no_mechanism_entry_when_mechanism_known():
    sidecar = _base_sidecar()
    artefact = to_core_artefact(sidecar, skill_version="1.6")
    ids = {u["id"] for u in artefact["unknowns"]}
    assert "mechanism-unknown" not in ids


def test_unknowns_entry_per_open_condition():
    sidecar = _base_sidecar()
    sidecar["conditions"] = [
        {"id": "C1", "text": "Rotate exporter-held keys.", "status": "open"},
        {"id": "C2", "text": "Sign updated Annex II.", "status": "met",
         "met_evidence": "Signed 2026-09-01.", "met_date": "2026-09-01"},
    ]
    artefact = to_core_artefact(sidecar, skill_version="1.6")
    open_entries = [u for u in artefact["unknowns"] if u["id"].startswith("condition-open-")]
    assert len(open_entries) == 1
    assert open_entries[0]["id"] == "condition-open-C1"
    assert "Rotate exporter-held keys." in open_entries[0]["question"]
    assert open_entries[0]["blocking"] is True
    _validate_against_schema(artefact)


def test_unknowns_no_condition_entries_when_all_met():
    sidecar = _base_sidecar()
    sidecar["conditions"] = [
        {"id": "C1", "text": "x", "status": "met"},
    ]
    artefact = to_core_artefact(sidecar, skill_version="1.6")
    assert not any(u["id"].startswith("condition-open-") for u in artefact["unknowns"])


def test_unknowns_tolerates_malformed_conditions_without_crashing():
    sidecar = _base_sidecar()
    sidecar["conditions"] = "not-a-list"
    artefact = to_core_artefact(sidecar, skill_version="1.6")
    assert not any(u["id"].startswith("condition-open-") for u in artefact["unknowns"])


# ---------------------------------------------------------------------------
# outcome.status — proceed_with_conditions with an open condition stays
# non-complete. skill-artefact-1.1's outcome.status enum is only
# {complete, provisional, blocked} — there is no dedicated "conditional"
# value, so this is achieved via the DECISION-CONDITIONS warning-severity
# finding driving the ordinary validation-status -> outcome mapping to
# "provisional" (the closest existing non-complete value), not via a
# special case here.
# ---------------------------------------------------------------------------

def test_outcome_stays_provisional_not_complete_with_open_conditions():
    sidecar = _base_sidecar()
    sidecar["step4"]["decision"] = "proceed_with_conditions"
    sidecar["conditions"] = [{"id": "C1", "text": "x", "status": "open"}]
    sidecar["validation"] = {
        "status": "passed_with_warnings",
        "findings": [{"rule_id": "DECISION-CONDITIONS", "category": "consistency",
                      "severity": "warning", "message": "1 open condition",
                      "spec_anchor": "x"}],
    }
    artefact = to_core_artefact(sidecar, skill_version="1.6")
    assert artefact["outcome"]["status"] == "provisional"


# ---------------------------------------------------------------------------
# gaps[]
# ---------------------------------------------------------------------------

def test_gaps_one_entry_per_finding_with_fix_hint_when_present():
    sidecar = _base_sidecar()
    sidecar["validation"] = {
        "status": "passed_with_warnings",
        "findings": [
            {"rule_id": "DELTA-FILE-REQUIRED", "category": "interchange",
             "severity": "rejection", "message": "ropa_delta.emitted is true "
             "but delta_ref is missing", "spec_anchor": "x"},
            {"rule_id": "ONWARD-CHILD", "category": "consistency",
             "severity": "warning", "message": "no child assessment ref",
             "spec_anchor": "y", "fix_hint": "Record the child TIA ref."},
        ],
    }
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["gaps"] == [
        {"id": "DELTA-FILE-REQUIRED", "severity": "rejection",
         "message": "ropa_delta.emitted is true but delta_ref is missing"},
        {"id": "ONWARD-CHILD", "severity": "warning",
         "message": "no child assessment ref",
         "fix_hint": "Record the child TIA ref."},
    ]


# ---------------------------------------------------------------------------
# Schema-level: every emitted document validates, across representative
# fixtures.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture_name", [
    "minimal-signed.json", "art49-derogation.json", "adequacy-fast-track.json",
    "proceed-with-conditions.json",
])
def test_every_emitted_document_validates_against_schema(fixture_name):
    path = TIA_ROOT / "validator" / "fixtures" / "must_pass" / fixture_name
    sidecar = json.loads(path.read_text(encoding="utf-8"))
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    _validate_against_schema(artefact)
    assert artefact["artefact_schema_version"] == "1.1"
    assert artefact["skill"] == "tia"


def test_skill_version_and_schema_version_and_generated_at():
    sidecar = _base_sidecar()
    artefact = to_core_artefact(sidecar, skill_version="1.4")
    assert artefact["skill_version"] == "1.4"
    assert artefact["artefact_schema_version"] == "1.1"
    assert artefact["skill"] == "tia"
    assert artefact["generated_at"].endswith("Z")
