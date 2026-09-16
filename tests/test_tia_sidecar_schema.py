"""tia-sidecar-schema.json shape tests (spec §4).

Required-field discipline: rejection-tier facts required, warning-tier
facts optional (next_review_date/rule 14 must NOT be schema-required).
"""
import json
from pathlib import Path

import jsonschema
import pytest

TIA_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((TIA_ROOT / "references" / "tia-sidecar-schema.json")
                    .read_text(encoding="utf-8"))
MUST_PASS = sorted((TIA_ROOT / "validator" / "fixtures" / "must_pass").glob("*.json"))
MUST_FAIL = sorted((TIA_ROOT / "validator" / "fixtures" / "must_fail").glob("*.json"))


def _validate(doc):
    jsonschema.validate(doc, SCHEMA,
                        format_checker=jsonschema.FormatChecker())


def load_valid():
    path = TIA_ROOT / "validator" / "fixtures" / "must_pass" / "minimal-signed.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_is_self_valid():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("path", MUST_PASS, ids=lambda p: p.stem)
def test_must_pass_fixtures_validate(path):
    _validate(json.loads(path.read_text(encoding="utf-8")))


def test_there_are_four_must_pass_fixtures():
    assert [p.stem for p in MUST_PASS] == [
        "adequacy-fast-track", "art49-derogation", "minimal-signed",
        "proceed-with-conditions"]


@pytest.mark.parametrize("path", MUST_FAIL, ids=lambda p: p.stem)
def test_must_fail_fixtures_are_still_schema_valid(path):
    # must_fail fixtures fail a validator rule, not JSON Schema conformance
    # (schema-invalid input is SCHEMA-0's job, tested separately).
    _validate(json.loads(path.read_text(encoding="utf-8")))


def test_there_is_one_must_fail_fixture():
    assert [p.stem for p in MUST_FAIL] == [
        "DECISION-CONDITIONS__proceed-with-planned-measures"]


@pytest.mark.parametrize("missing", ["tia_ref", "title", "org_slug", "assessor", "date"])
def test_cover_fields_are_required(missing):
    doc = load_valid()
    del doc["cover"][missing]
    with pytest.raises(jsonschema.ValidationError):
        _validate(doc)


def test_org_slug_pattern_rejects_non_slug():
    doc = load_valid()
    doc["cover"]["org_slug"] = "Acme GmbH"
    with pytest.raises(jsonschema.ValidationError):
        _validate(doc)


@pytest.mark.parametrize("missing", [
    "exporter", "importer", "roles", "destination_country", "importer_sector",
    "data_categories", "data_subjects", "purpose", "volume", "frequency",
    "formats", "onward_transfers"])
def test_step1_requires_all_twelve_fields(missing):
    doc = load_valid()
    del doc["step1"][missing]
    with pytest.raises(jsonschema.ValidationError):
        _validate(doc)


def test_step4_requires_the_split_effectiveness_and_decision_fields():
    # The template's one combined row is deliberately two fields (spec §4).
    for missing in ("overall_effectiveness", "decision"):
        doc = load_valid()
        del doc["step4"][missing]
        with pytest.raises(jsonschema.ValidationError):
            _validate(doc)


def test_next_review_date_is_optional_warning_tier_not_promoted():
    doc = load_valid()
    del doc["step5_6"]["next_review_date"]
    _validate(doc)  # must NOT raise — rule 14 is a warning, not schema conformance


def test_override_reason_is_mandatory():
    doc = load_valid()
    doc["overrides"] = [{"rule_id": "STEP1-COMPLETE", "recorded_by": "dpo",
                         "recorded_at": "2026-08-09"}]
    with pytest.raises(jsonschema.ValidationError):
        _validate(doc)


def test_retired_v11_interchange_fields_appear_nowhere_in_the_schema():
    text = json.dumps(SCHEMA)
    for retired in ("tia_status", "tia_completed_date", "tia_review_date",
                    "supplementary_measures"):
        assert retired not in text  # landmine 2, CHANGELOG.md:24


def test_mechanism_enum_is_the_rule7_closed_set():
    enum = SCHEMA["properties"]["step2"]["properties"]["mechanism"]["enum"]
    assert enum == ["adequacy", "sccs", "bcrs", "ad_hoc",
                    "code_of_conduct", "certification", "art49", "unknown"]


# ---------------------------------------------------------------------------
# v1.1 additions (2026-09-15, adversarial review findings 11/12, rulings
# R-unknown / R-conditions): "unknown" mechanism, "proceed_with_conditions"
# decision, and the conditions[] ledger.
# ---------------------------------------------------------------------------

def test_tia_schema_version_accepts_both_1_0_and_1_1():
    doc = load_valid()
    doc["tia_schema_version"] = "1.0"
    _validate(doc)
    doc["tia_schema_version"] = "1.1"
    _validate(doc)


def test_tia_schema_version_rejects_anything_else():
    doc = load_valid()
    doc["tia_schema_version"] = "2.0"
    with pytest.raises(jsonschema.ValidationError):
        _validate(doc)


def test_mechanism_unknown_is_schema_valid():
    doc = load_valid()
    doc["step2"]["mechanism"] = "unknown"
    doc["step2"]["adequacy"] = None
    doc["step2"]["art49"] = None
    _validate(doc)


def test_decision_enum_includes_proceed_with_conditions():
    enum = SCHEMA["properties"]["step4"]["properties"]["decision"]["enum"]
    assert enum == ["proceed", "restructure", "suspend", "proceed_with_conditions"]


def test_decision_proceed_with_conditions_is_schema_valid():
    doc = load_valid()
    doc["step4"]["decision"] = "proceed_with_conditions"
    doc["conditions"] = [
        {"id": "C1", "text": "Enable exporter-held key rotation.", "status": "open"},
    ]
    _validate(doc)


def test_conditions_entry_requires_id_text_status():
    doc = load_valid()
    doc["conditions"] = [{"text": "missing id and status"}]
    with pytest.raises(jsonschema.ValidationError):
        _validate(doc)


def test_conditions_status_is_closed_enum():
    doc = load_valid()
    doc["conditions"] = [{"id": "C1", "text": "x", "status": "pending"}]
    with pytest.raises(jsonschema.ValidationError):
        _validate(doc)


def test_conditions_met_evidence_and_met_date_are_optional_but_typed():
    doc = load_valid()
    doc["conditions"] = [{
        "id": "C1", "text": "x", "status": "met",
        "met_evidence": "Key rotation completed and logged 2026-09-10.",
        "met_date": "2026-09-10",
    }]
    _validate(doc)


def test_conditions_met_date_must_be_a_date():
    doc = load_valid()
    doc["conditions"] = [{
        "id": "C1", "text": "x", "status": "met", "met_date": "not-a-date",
    }]
    with pytest.raises(jsonschema.ValidationError):
        _validate(doc)


def test_conditions_field_is_optional():
    doc = load_valid()
    assert "conditions" not in doc
    _validate(doc)  # must not raise — conditions[] is optional
