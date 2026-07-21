"""Executable contract between TIA delta output and RoPA transfer entries.

Merge semantics under inbound schema 2.0 (decided 2026-07-21):

* ``add`` **upserts** — it writes the value whether or not the leaf is already
  present, so a re-send is safe and the producer never has to read RoPA's
  sidecar to choose an operation. ``replace`` is accepted as an exact synonym.
* Determinism comes from ``expected_post_state``, not from leaf presence. If a
  delta declares one and the post-merge state does not match, the whole delta
  is rejected.
* A patch path outside the allowed-path set declared in
  ``interchange-inbound-schema.json`` rejects the whole delta. With ``add``
  permissive, this is the only guard stopping a stale producer from writing
  unrecognised fields into a user's sidecar.

Every assertion about what TIA emits is derived from the **documented example**
in ``references/interchange-delta.md`` — the artifact a model actually copies at
runtime — and that example is run through the applier. Assertions over test-only
fixtures would be a tautology over test data.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker


TIA_ROOT = Path(__file__).parents[1]
REPO_ROOT = TIA_ROOT.parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
TIA_DELTA_DOC = TIA_ROOT / "references" / "interchange-delta.md"
ROPA_ROOT = REPO_ROOT / "skills" / "ropa"
ROPA_OUTBOUND_SCHEMA = ROPA_ROOT / "references" / "interchange-schema.json"
ROPA_INBOUND_SCHEMA = ROPA_ROOT / "references" / "interchange-inbound-schema.json"
ROPA_INBOUND_DOC = ROPA_ROOT / "references" / "interchange-inbound-schema.md"

INBOUND_SCHEMA_VERSION = "2.0"

CANONICAL_TIA_PATHS = {"/transfers/0/tia_ref", "/transfers/0/tia_date"}

# Fields the shipped tia v1.1 delta used to write. RoPA must reject them.
RETIRED_TIA_PATHS = {
    "/transfers/0/tia_completed_date",
    "/transfers/0/tia_status",
    "/transfers/0/tia_review_date",
    "/transfers/0/supplementary_measures",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def inbound_schema() -> dict:
    return load_json(ROPA_INBOUND_SCHEMA)


def allowed_path_pattern() -> re.Pattern[str]:
    """The allowed-path set, read from the machine-readable contract.

    Deliberately not a constant in this file: CLAUDE.md designates the JSON
    Schema as *the* integration contract, so the guarantee has to live there,
    where an adapter validating against the .json also gets it.
    """
    return re.compile(inbound_schema()["$defs"]["Patch"]["properties"]["path"]["pattern"])


def emitted_delta() -> dict:
    """The canonical delta example a model copies out of interchange-delta.md."""
    text = TIA_DELTA_DOC.read_text(encoding="utf-8")
    match = re.search(
        r"## Delta File Structure.*?```json\n(?P<payload>.*?)\n```",
        text,
        flags=re.DOTALL,
    )
    assert match, "interchange-delta.md must contain a JSON delta example"
    return json.loads(match.group("payload"))


def emitted_paths() -> set[str]:
    return {patch["path"] for patch in emitted_delta()["patches"]}


def emitted_ops() -> list[str]:
    return [patch["op"] for patch in emitted_delta()["patches"]]


def _resolve_parent(document: dict, path: str) -> tuple[dict | list, str]:
    tokens = [
        token.replace("~1", "/").replace("~0", "~")
        for token in path.removeprefix("/").split("/")
    ]
    parent: dict | list = document
    for token in tokens[:-1]:
        if isinstance(parent, list):
            if not token.isdigit():
                raise ValueError(f"missing parent for path: {path}")
            index = int(token)
            if not 0 <= index < len(parent):
                raise ValueError(f"missing parent for path: {path}")
            parent = parent[index]
        else:
            if token not in parent:
                raise ValueError(f"missing parent for path: {path}")
            parent = parent[token]
    return parent, tokens[-1]


def _read_pointer(document: dict, path: str):
    parent, leaf = _resolve_parent(document, path)
    if isinstance(parent, list):
        index = int(leaf)
        if not 0 <= index < len(parent):
            raise ValueError(f"missing leaf for path: {path}")
        return parent[index]
    if leaf not in parent:
        raise ValueError(f"missing leaf for path: {path}")
    return parent[leaf]


def apply_delta(base: dict, delta: dict) -> dict:
    """Apply an inbound delta atomically to a cloned RoPA entry.

    Mirrors the merge rules in ropa/references/interchange-inbound-schema.md.
    Any rejection raises before the caller's ``base`` is touched, because every
    mutation happens on a deep copy.
    """
    allowed = allowed_path_pattern()
    result = copy.deepcopy(base)

    for patch in delta["patches"]:
        path = patch["path"]
        if not allowed.match(path):
            raise ValueError(f"path outside the allowed-path set: {path}")

        parent, leaf = _resolve_parent(result, path)
        op = patch["op"]

        if op in {"add", "replace"}:
            # add upserts; replace is an accepted synonym. Neither consults
            # leaf presence — determinism comes from expected_post_state.
            if isinstance(parent, list):
                if leaf == "-":
                    parent.append(patch["value"])
                else:
                    parent[int(leaf)] = patch["value"]
            else:
                parent[leaf] = patch["value"]
        elif op == "remove":
            if isinstance(parent, list):
                del parent[int(leaf)]
            else:
                parent.pop(leaf, None)
        else:
            raise ValueError(f"unsupported op: {op}")

    expected = (delta.get("expected_post_state") or {}).get("values", {})
    for pointer, wanted in expected.items():
        actual = _read_pointer(result, pointer)
        if actual != wanted:
            raise ValueError(
                f"precondition failed at {pointer}: expected {wanted!r}, got {actual!r}"
            )

    return result


# --------------------------------------------------------------------------
# The documented example is the contract surface
# --------------------------------------------------------------------------


def test_documented_example_validates_against_the_inbound_schema():
    """B4 — the artifact a model copies must itself be schema-valid."""
    validator = Draft202012Validator(inbound_schema(), format_checker=FormatChecker())
    validator.validate(emitted_delta())


def test_documented_example_declares_the_current_inbound_schema_version():
    assert emitted_delta()["schema_version"] == INBOUND_SCHEMA_VERSION


def test_documented_example_uses_only_canonical_transfer_paths():
    assert emitted_paths() == CANONICAL_TIA_PATHS
    assert not emitted_paths() & RETIRED_TIA_PATHS


def test_documented_example_emits_only_add_because_the_producer_is_stateless():
    """Section G — TIA never reads RoPA's sidecar to choose an operation."""
    assert emitted_ops() == ["add", "add"]


def test_every_documented_path_is_inside_the_contract_allowed_path_set():
    allowed = allowed_path_pattern()
    for path in emitted_paths():
        assert allowed.match(path), f"documented path not permitted by contract: {path}"


# --------------------------------------------------------------------------
# add upserts — the Section G decision
# --------------------------------------------------------------------------


def test_documented_example_applies_to_a_transfer_with_no_prior_tia():
    result = apply_delta(
        load_json(FIXTURES / "ropa-base-first-write.json"), emitted_delta()
    )
    transfer = result["transfers"][0]
    assert transfer["tia_ref"] == "TIA-US-2026-001"
    assert transfer["tia_date"] == "2026-05-28"


def test_documented_example_overwrites_an_existing_tia_because_add_upserts():
    """The whole point of the decision: no leaf-presence coupling."""
    result = apply_delta(
        load_json(FIXTURES / "ropa-base-existing-tia.json"), emitted_delta()
    )
    transfer = result["transfers"][0]
    assert transfer["tia_ref"] == "TIA-US-2026-001"
    assert transfer["tia_date"] == "2026-05-28"


def test_applying_the_documented_example_twice_is_idempotent():
    base = load_json(FIXTURES / "ropa-base-first-write.json")
    once = apply_delta(base, emitted_delta())
    twice = apply_delta(once, emitted_delta())
    assert once == twice


def test_add_and_replace_are_deliberately_equivalent():
    base = load_json(FIXTURES / "ropa-base-first-write.json")
    as_add = apply_delta(base, emitted_delta())

    as_replace = copy.deepcopy(emitted_delta())
    for patch in as_replace["patches"]:
        patch["op"] = "replace"

    assert apply_delta(base, as_replace) == as_add


def test_applied_result_still_satisfies_the_ropa_transfer_schema():
    result = apply_delta(
        load_json(FIXTURES / "ropa-base-first-write.json"), emitted_delta()
    )
    transfer_schema = load_json(ROPA_OUTBOUND_SCHEMA)["$defs"]["ActivityEntry"][
        "properties"
    ]["transfers"]["items"]
    Draft202012Validator(transfer_schema, format_checker=FormatChecker()).validate(
        result["transfers"][0]
    )


# --------------------------------------------------------------------------
# Unknown-path rejection — the primary guard now that add is permissive
# --------------------------------------------------------------------------


@pytest.mark.parametrize("retired_path", sorted(RETIRED_TIA_PATHS))
def test_retired_tia_v1_1_fields_are_rejected_by_the_machine_readable_contract(
    retired_path: str,
):
    """B2 — a delta from the shipped tia v1.1 must not reach a user's sidecar."""
    assert not allowed_path_pattern().match(retired_path)


def test_legacy_delta_is_rejected_atomically_without_partial_application():
    base = load_json(FIXTURES / "ropa-base-existing-tia.json")
    before = copy.deepcopy(base)
    legacy = load_json(FIXTURES / "tia-result-legacy-invalid.json")

    with pytest.raises(ValueError, match="outside the allowed-path set"):
        apply_delta(base, legacy)

    assert base == before


def test_legacy_delta_also_fails_schema_validation():
    """The rejection must live in the contract, not only in this applier."""
    validator = Draft202012Validator(inbound_schema(), format_checker=FormatChecker())
    legacy = load_json(FIXTURES / "tia-result-legacy-invalid.json")
    assert not validator.is_valid(legacy)


def test_unknown_path_rejects_the_whole_delta_including_earlier_valid_patches():
    base = load_json(FIXTURES / "ropa-base-first-write.json")
    before = copy.deepcopy(base)
    delta = {
        "patches": [
            {"op": "add", "path": "/transfers/0/tia_ref", "value": "TIA-VALID"},
            {"op": "add", "path": "/transfers/0/tia_status", "value": "green"},
        ]
    }

    with pytest.raises(ValueError, match="outside the allowed-path set"):
        apply_delta(base, delta)

    assert base == before


# --------------------------------------------------------------------------
# Preconditions carry determinism
# --------------------------------------------------------------------------


def test_failed_precondition_rejects_the_whole_delta():
    """Section G — determinism moved here from leaf presence."""
    base = load_json(FIXTURES / "ropa-base-first-write.json")
    before = copy.deepcopy(base)
    delta = copy.deepcopy(emitted_delta())
    delta["expected_post_state"] = {
        "values": {"/transfers/0/mechanism": "adequacy"}  # the fixture says sccs
    }

    with pytest.raises(ValueError, match="precondition failed"):
        apply_delta(base, delta)

    assert base == before


def test_precondition_detects_a_concurrent_edit_to_an_unpatched_field():
    base = load_json(FIXTURES / "ropa-base-first-write.json")
    delta = copy.deepcopy(emitted_delta())
    delta["expected_post_state"] = {"values": {"/transfers/0/mechanism": "sccs"}}

    apply_delta(base, delta)  # matches — no raise

    concurrently_edited = copy.deepcopy(base)
    concurrently_edited["transfers"][0]["mechanism"] = "art49"
    with pytest.raises(ValueError, match="precondition failed"):
        apply_delta(concurrently_edited, delta)


def test_missing_parent_is_a_documented_rejection_not_a_crash():
    """B13 — _resolve_parent used to raise IndexError instead of rejecting."""
    with pytest.raises(ValueError, match="missing parent"):
        apply_delta({"transfers": []}, emitted_delta())


# --------------------------------------------------------------------------
# The machine-readable contract must agree with the prose
# --------------------------------------------------------------------------


def test_inbound_json_schema_states_upsert_semantics():
    """B3 — an adapter validating against the .json gets the real rules."""
    op_description = inbound_schema()["$defs"]["Patch"]["properties"]["op"][
        "description"
    ]
    assert "upsert" in op_description.lower()
    assert "regardless of whether" in op_description.lower()


def test_inbound_json_schema_accepts_only_the_current_schema_version():
    version_schema = inbound_schema()["properties"]["schema_version"]
    Draft202012Validator(version_schema).validate(INBOUND_SCHEMA_VERSION)
    assert not Draft202012Validator(version_schema).is_valid("1.0")


def test_inbound_json_schema_documents_the_precondition_rejection():
    described = json.dumps(inbound_schema()["properties"]["expected_post_state"])
    assert "reject" in described.lower()


def test_inbound_prose_and_json_agree_that_add_upserts():
    doc = ROPA_INBOUND_DOC.read_text(encoding="utf-8")
    assert "upsert" in doc.lower()
    assert "absent leaf under an existing parent" not in doc
    assert "add requires an absent leaf" not in doc


def test_inbound_prose_documents_the_unknown_path_rejection():
    doc = ROPA_INBOUND_DOC.read_text(encoding="utf-8")
    assert "allowed-path set" in doc


# --------------------------------------------------------------------------
# Cross-surface freeze
# --------------------------------------------------------------------------


def test_ropa_schema_exposes_only_the_canonical_tia_leaves():
    transfer_properties = load_json(ROPA_OUTBOUND_SCHEMA)["$defs"]["ActivityEntry"][
        "properties"
    ]["transfers"]["items"]["properties"]
    assert {"tia_ref", "tia_date"} <= transfer_properties.keys()
    assert not {
        "tia_completed_date",
        "tia_status",
        "tia_review_date",
        "supplementary_measures",
    } & transfer_properties.keys()
    assert "completed" in transfer_properties["tia_date"]["description"].lower()


def test_docs_and_evals_freeze_timestamp_leaf_and_transfer_name_semantics():
    tia_eval = next(
        item
        for item in load_json(TIA_ROOT / "evals" / "evals.json")["evals"]
        if item["id"] == 10
    )
    tia_eval_contract = " ".join(
        [tia_eval["expected_output"], *tia_eval["expectations"]]
    )
    assert "tia_ref" in tia_eval_contract
    assert "tia_date" in tia_eval_contract
    assert not any(
        retired.removeprefix("/transfers/0/") in tia_eval_contract
        for retired in RETIRED_TIA_PATHS
    )

    ropa_eval = next(
        item
        for item in load_json(ROPA_ROOT / "evals" / "evals.json")["evals"]
        if item["id"] == 23
    )
    ropa_transfer_contract = " ".join(
        [ropa_eval["expected_output"], *ropa_eval["expectations"]]
    )
    assert "mechanism=sccs" in ropa_transfer_contract
    assert "transfer_mechanism" not in ropa_transfer_contract

    provenance_surfaces = [
        ROPA_ROOT / "SKILL.md",
        ROPA_INBOUND_DOC,
        ROPA_ROOT / "references" / "lifecycle-operations.md",
        ROPA_ROOT / "evals" / "evals.json",
    ]
    provenance_contract = "\n".join(
        path.read_text(encoding="utf-8") for path in provenance_surfaces
    )
    assert "produced_at[0:10]" in provenance_contract
    assert "delta created_at" not in provenance_contract
