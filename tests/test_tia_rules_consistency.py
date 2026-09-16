import json
import sys
from pathlib import Path

TIA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TIA_ROOT / "validator"))

import tia_validator.rules                                      # noqa: E402,F401
from tia_validator.runner import Context, validate              # noqa: E402

FIXTURES = TIA_ROOT / "validator" / "fixtures" / "must_pass"


def _ctx(**kw):
    return Context(schema_path=TIA_ROOT / "references" / "tia-sidecar-schema.json",
                   references_dir=TIA_ROOT / "references", **kw)


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def fired(result):
    return {f.rule_id for f in result.findings}


# ---------------------------------------------------------------------------
# MECH-ENUM
# ---------------------------------------------------------------------------

def test_mech_enum_fires_on_an_invalid_mechanism():
    doc = load_fixture("minimal-signed.json")
    doc["step2"]["mechanism"] = "handshake"
    assert "MECH-ENUM" in fired(validate(doc, _ctx()))


def test_mech_enum_does_not_fire_on_a_valid_mechanism():
    doc = load_fixture("minimal-signed.json")
    doc["step2"]["mechanism"] = "bcrs"       # valid but different from the fixture's "sccs"
    doc["step3"] = load_fixture("minimal-signed.json")["step3"]
    assert "MECH-ENUM" not in fired(validate(doc, _ctx()))


# ---------------------------------------------------------------------------
# STEP3-CONCLUSION
# ---------------------------------------------------------------------------

def test_step3_conclusion_fires_on_an_invalid_conclusion_value():
    doc = load_fixture("minimal-signed.json")
    doc["step3"]["conclusion"] = "4"
    assert "STEP3-CONCLUSION" in fired(validate(doc, _ctx()))


def test_step3_conclusion_fires_on_empty_justification():
    doc = load_fixture("minimal-signed.json")
    doc["step3"]["justification"] = ""
    assert "STEP3-CONCLUSION" in fired(validate(doc, _ctx()))


def test_step3_conclusion_does_not_fire_when_step3_absent():
    # A must-not-fire case that would catch an over-broad predicate: no step3
    # at all (not merely a valid one) must not trip a rule scoped to "step3
    # present and ...".
    doc = load_fixture("adequacy-fast-track.json")
    assert doc.get("step3") is None
    assert "STEP3-CONCLUSION" not in fired(validate(doc, _ctx()))


# ---------------------------------------------------------------------------
# BLOCKB-RATINGS
# ---------------------------------------------------------------------------

def test_blockb_ratings_fires_with_field_set_to_the_bad_key():
    doc = load_fixture("minimal-signed.json")
    doc["step3"]["block_b_guarantees"]["redress"] = "fine"
    result = validate(doc, _ctx())
    f = next(f for f in result.findings if f.rule_id == "BLOCKB-RATINGS")
    assert f.field == "redress"


def test_blockb_ratings_does_not_fire_when_all_four_keys_are_valid():
    # Must-not-fire that would catch an over-broad predicate: a fixture whose
    # four ratings use every valid enum value, not just repeats of "adequate".
    doc = load_fixture("minimal-signed.json")
    doc["step3"]["block_b_guarantees"] = {
        "legality_clarity": "adequate",
        "necessity_proportionality": "concerns",
        "oversight": "insufficient",
        "redress": "adequate",
    }
    assert "BLOCKB-RATINGS" not in fired(validate(doc, _ctx()))


# ---------------------------------------------------------------------------
# CONCL2-MEASURES
# ---------------------------------------------------------------------------

def test_concl2_measures_fires_when_step4_deleted_under_conclusion_2():
    doc = load_fixture("minimal-signed.json")
    assert doc["step3"]["conclusion"] == "2"
    del doc["step4"]
    assert "CONCL2-MEASURES" in fired(validate(doc, _ctx()))


def test_concl2_measures_does_not_fire_under_conclusion_1_even_without_step4():
    # Must-not-fire that would catch an over-broad predicate: step4 absent is
    # only a problem when conclusion == "2"; conclusion "1" must not trip it.
    doc = load_fixture("minimal-signed.json")
    doc["step3"]["conclusion"] = "1"
    del doc["step4"]
    assert "CONCL2-MEASURES" not in fired(validate(doc, _ctx()))


def test_concl2_measures_category_is_consistency_not_enum():
    # Brief + design spec (row 10) put CONCL2-MEASURES in category
    # "consistency" (it is a cross-field check between step3 and step4),
    # unlike the true enum rules 7-9. Pin it the same way rule 12's severity
    # is pinned, since category is part of the findings-report 2.0 contract.
    doc = load_fixture("minimal-signed.json")
    del doc["step4"]
    result = validate(doc, _ctx())
    f = next(f for f in result.findings if f.rule_id == "CONCL2-MEASURES")
    assert f.category == "consistency"


# ---------------------------------------------------------------------------
# EFFECT-BLOCKS-PROCEED
# ---------------------------------------------------------------------------

def test_effect_blocks_proceed_fires_on_the_contradiction():
    doc = load_fixture("minimal-signed.json")
    doc["step4"]["overall_effectiveness"] = "insufficient"   # decision stays "proceed"
    result = validate(doc, _ctx())
    assert "EFFECT-BLOCKS-PROCEED" in fired(result)
    assert result.status == "failed"


def test_effect_blocks_proceed_allows_insufficient_plus_suspend():
    doc = load_fixture("minimal-signed.json")
    doc["step4"]["overall_effectiveness"] = "insufficient"
    doc["step4"]["decision"] = "suspend"
    assert "EFFECT-BLOCKS-PROCEED" not in fired(validate(doc, _ctx()))


# ---------------------------------------------------------------------------
# ONWARD-CHILD
# ---------------------------------------------------------------------------

def test_onward_child_is_a_warning_not_a_rejection():
    doc = load_fixture("minimal-signed.json")
    doc["step1"]["onward_transfers"] = {"present": "yes", "child_assessment_ref": None}
    result = validate(doc, _ctx())
    f = next(f for f in result.findings if f.rule_id == "ONWARD-CHILD")
    assert f.severity == "warning"
    assert result.status == "passed_with_warnings"           # rule 12 never gates


def test_onward_child_does_not_fire_when_present_is_no():
    # Must-not-fire that would catch an over-broad predicate: a rule that
    # merely checked "child_assessment_ref empty" (ignoring "present") would
    # wrongly fire here, since the fixture's ref is already null when
    # onward_transfers.present == "no".
    doc = load_fixture("minimal-signed.json")
    assert doc["step1"]["onward_transfers"]["present"] == "no"
    assert doc["step1"]["onward_transfers"]["child_assessment_ref"] is None
    assert "ONWARD-CHILD" not in fired(validate(doc, _ctx()))


# ---------------------------------------------------------------------------
# DELTA-SHAPE
# ---------------------------------------------------------------------------

def _envelope(**patches_kw):
    """A delta carrying the five frozen envelope facts (amendment 2026-08-11);
    tests mutate one detail at a time so each fires for exactly one reason."""
    return {"schema_version": "2.0", "source_skill": "tia",
            "produced_at": "2026-08-01T00:00:00Z",
            "target_activity_id": "act-001", **patches_kw}


def test_delta_shape_rejects_a_retired_path():
    doc = load_fixture("minimal-signed.json")
    delta = _envelope(patches=[{"op": "add", "path": "/transfers/0/tia_status",
                                "value": "x"}])
    assert "DELTA-SHAPE" in fired(validate(doc, _ctx(delta=delta)))


def test_delta_shape_accepts_replace_as_synonym():
    doc = load_fixture("minimal-signed.json")
    delta = _envelope(patches=[
        {"op": "replace", "path": "/transfers/0/tia_ref", "value": "TIA-US-2026-001"},
        {"op": "add", "path": "/transfers/0/tia_date", "value": "2026-08-01"}])
    assert "DELTA-SHAPE" not in fired(validate(doc, _ctx(delta=delta)))


def test_delta_shape_fires_on_missing_envelope_fields():
    doc = load_fixture("minimal-signed.json")
    delta = _envelope(patches=[
        {"op": "add", "path": "/transfers/0/tia_ref", "value": "TIA-US-2026-001"}])
    del delta["source_skill"]
    assert "DELTA-SHAPE" in fired(validate(doc, _ctx(delta=delta)))


def test_delta_shape_fires_on_empty_patches():
    doc = load_fixture("minimal-signed.json")
    assert "DELTA-SHAPE" in fired(validate(doc, _ctx(delta=_envelope(patches=[]))))


def test_delta_shape_fires_on_wrong_schema_version():
    doc = load_fixture("minimal-signed.json")
    delta = _envelope(patches=[
        {"op": "add", "path": "/transfers/0/tia_ref", "value": "TIA-US-2026-001"}])
    delta["schema_version"] = "1.0"
    assert "DELTA-SHAPE" in fired(validate(doc, _ctx(delta=delta)))


def test_delta_shape_fires_on_op_outside_add_replace():
    doc = load_fixture("minimal-signed.json")
    delta = _envelope(patches=[
        {"op": "remove", "path": "/transfers/0/tia_ref"}])
    assert "DELTA-SHAPE" in fired(validate(doc, _ctx(delta=delta)))


def test_delta_shape_is_skipped_without_a_delta():
    doc = load_fixture("minimal-signed.json")
    assert "DELTA-SHAPE" not in fired(validate(doc, _ctx()))


# ---------------------------------------------------------------------------
# MECHANISM-UNKNOWN (v1.1, adversarial review finding 11, ruling R-unknown)
# ---------------------------------------------------------------------------

def test_mechanism_unknown_is_a_warning_before_signoff():
    doc = load_fixture("minimal-signed.json")
    doc["step2"]["mechanism"] = "unknown"
    doc["step2"]["adequacy"] = None
    doc["step2"]["art49"] = None
    doc["step5_6"]["sign_off"]["dpo"] = {"name": None, "date": None}  # unsigned
    result = validate(doc, _ctx())
    f = next(f for f in result.findings if f.rule_id == "MECHANISM-UNKNOWN")
    assert f.severity == "warning"
    assert result.status != "failed"


def test_mechanism_unknown_is_a_rejection_once_signed_off():
    doc = load_fixture("minimal-signed.json")   # sign-off already complete
    doc["step2"]["mechanism"] = "unknown"
    doc["step2"]["adequacy"] = None
    doc["step2"]["art49"] = None
    result = validate(doc, _ctx())
    f = next(f for f in result.findings if f.rule_id == "MECHANISM-UNKNOWN")
    assert f.severity == "rejection"
    assert result.status == "failed"
    assert "sign-off" in f.message.lower() or "sign off" in f.message.lower()
    assert "chapter v" in f.message.lower()


def test_mechanism_unknown_does_not_fire_for_a_known_mechanism():
    doc = load_fixture("minimal-signed.json")
    assert "MECHANISM-UNKNOWN" not in fired(validate(doc, _ctx()))


def test_mech_enum_accepts_unknown_as_a_valid_value():
    # MECH-ENUM must not also reject "unknown" — that is MECHANISM-UNKNOWN's
    # job, at a severity MECH-ENUM (a flat rejection) cannot express.
    doc = load_fixture("minimal-signed.json")
    doc["step2"]["mechanism"] = "unknown"
    doc["step2"]["adequacy"] = None
    doc["step2"]["art49"] = None
    assert "MECH-ENUM" not in fired(validate(doc, _ctx()))


# ---------------------------------------------------------------------------
# DECISION-CONDITIONS (v1.1, adversarial review finding 12, ruling R-conditions)
# ---------------------------------------------------------------------------

def test_decision_conditions_rejects_proceed_with_a_planned_measure():
    doc = load_fixture("minimal-signed.json")
    assert doc["step4"]["decision"] == "proceed"
    doc["step4"]["measures"][0]["implementation_status"] = "planned"
    result = validate(doc, _ctx())
    f = next(f for f in result.findings if f.rule_id == "DECISION-CONDITIONS")
    assert f.severity == "rejection"
    assert result.status == "failed"
    assert "proceed_with_conditions" in f.message


def test_decision_conditions_allows_proceed_when_all_measures_implemented():
    doc = load_fixture("minimal-signed.json")
    assert doc["step4"]["decision"] == "proceed"
    assert doc["step4"]["measures"][0]["implementation_status"] == "implemented"
    assert "DECISION-CONDITIONS" not in fired(validate(doc, _ctx()))


def test_decision_conditions_rejects_proceed_with_conditions_and_no_conditions():
    doc = load_fixture("minimal-signed.json")
    doc["step4"]["decision"] = "proceed_with_conditions"
    result = validate(doc, _ctx())
    f = next(f for f in result.findings if f.rule_id == "DECISION-CONDITIONS")
    assert f.severity == "rejection"
    assert result.status == "failed"


def test_decision_conditions_rejects_proceed_with_conditions_and_empty_conditions_list():
    doc = load_fixture("minimal-signed.json")
    doc["step4"]["decision"] = "proceed_with_conditions"
    doc["conditions"] = []
    result = validate(doc, _ctx())
    assert "DECISION-CONDITIONS" in fired(result)
    assert result.status == "failed"


def test_decision_conditions_lists_open_conditions_without_rejecting():
    doc = load_fixture("minimal-signed.json")
    doc["step4"]["decision"] = "proceed_with_conditions"
    doc["conditions"] = [
        {"id": "C1", "text": "Rotate exporter-held keys quarterly.", "status": "open"},
    ]
    result = validate(doc, _ctx())
    f = next(f for f in result.findings if f.rule_id == "DECISION-CONDITIONS")
    assert f.severity in ("info", "warning")
    assert "C1" in f.message
    assert result.status != "failed"


def test_decision_conditions_suggests_finalising_when_all_conditions_met():
    doc = load_fixture("minimal-signed.json")
    doc["step4"]["decision"] = "proceed_with_conditions"
    doc["conditions"] = [
        {"id": "C1", "text": "Rotate exporter-held keys quarterly.", "status": "met",
         "met_evidence": "Rotation log entry 2026-09-10.", "met_date": "2026-09-10"},
    ]
    result = validate(doc, _ctx())
    f = next(f for f in result.findings if f.rule_id == "DECISION-CONDITIONS")
    assert f.severity == "warning"
    assert "proceed" in f.message
    assert result.status != "failed"


def test_decision_conditions_does_not_fire_for_restructure_or_suspend():
    doc = load_fixture("minimal-signed.json")
    doc["step4"]["measures"][0]["implementation_status"] = "planned"
    doc["step4"]["overall_effectiveness"] = "insufficient"
    doc["step4"]["decision"] = "suspend"
    assert "DECISION-CONDITIONS" not in fired(validate(doc, _ctx()))


def test_decision_conditions_tolerates_malformed_conditions_entries():
    doc = load_fixture("minimal-signed.json")
    doc["step4"]["decision"] = "proceed_with_conditions"
    doc["conditions"] = ["not-an-object", 42, None]
    result = validate(doc, _ctx())   # must not raise
    assert "DECISION-CONDITIONS" in fired(result)


# ---------------------------------------------------------------------------
# DELTA-REF-MISSING
# ---------------------------------------------------------------------------

def test_delta_ref_missing_warns_but_does_not_gate():
    doc = load_fixture("minimal-signed.json")          # sign-off complete
    doc["ropa_delta"] = {"emitted": True, "delta_ref": None}
    result = validate(doc, _ctx())
    f = next(f for f in result.findings if f.rule_id == "DELTA-REF-MISSING")
    assert f.severity == "warning"
    assert result.status == "passed_with_warnings"


def test_delta_ref_missing_does_not_fire_when_not_emitted():
    # Must-not-fire that would catch an over-broad predicate: a rule that
    # merely checked "delta_ref empty" (ignoring "emitted") would wrongly
    # fire on the fixture's default {"emitted": false, "delta_ref": null}.
    doc = load_fixture("minimal-signed.json")
    assert doc["ropa_delta"] == {"emitted": False, "delta_ref": None}
    assert "DELTA-REF-MISSING" not in fired(validate(doc, _ctx()))
